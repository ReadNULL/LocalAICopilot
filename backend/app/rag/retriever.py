import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_core.documents import Document
from qdrant_client.models import Prefetch, FusionQuery, Fusion, SparseVector, Filter, FieldCondition, MatchAny
from app.core.config import settings
from app.rag.embedding import embedding_model
from app.rag.vector_store import vector_store
from app.rag.ingest import sparse_model


class AdvancedRetriever:
    def __init__(self):
        self.ollama_url = settings.OLLAMA_BASE_URL.rstrip('/')
        self.llm_model = settings.LLM_MODEL_NAME

    def _generate_expanded_queries(self, query: str) -> list[str]:
        prompt = f"""你是一个查询扩展助手。针对以下用户问题，生成 3 个不同角度、不同措辞的等价查询，用于提高检索召回率。
只输出查询本身，每行一个，不要编号，不要解释。

用户问题: {query}

等价查询:"""
        try:
            payload = {"model": self.llm_model, "prompt": prompt, "stream": False, "options": {"temperature": 0.3}}
            with httpx.Client(timeout=15) as client:
                resp = client.post(f"{self.ollama_url}/api/generate", json=payload)
                if resp.status_code == 200:
                    lines = [l.strip() for l in resp.json().get("response", "").split('\n') if l.strip()]
                    return lines[:3]
        except Exception:
            pass
        return []

    def _generate_hyde_answer(self, query: str) -> str:
        prompt = f"""你是一个知识助手。请针对以下问题生成一段假设性的回答（不需要真实准确，只是为了辅助文档检索）。
回答应包含与问题相关的关键概念和术语。

问题: {query}

假设性回答:"""
        try:
            payload = {"model": self.llm_model, "prompt": prompt, "stream": False, "options": {"temperature": 0.5}}
            with httpx.Client(timeout=15) as client:
                resp = client.post(f"{self.ollama_url}/api/generate", json=payload)
                if resp.status_code == 200:
                    return resp.json().get("response", "")
        except Exception:
            pass
        return ""

    def _single_retrieve(self, query_text: str, query_filter, doc_ids: list[str] = None) -> list[Document]:
        query_dense_vec = embedding_model.embed(query_text)
        query_sparse_vec = list(sparse_model.embed([query_text]))[0]

        results = vector_store.client.query_points(
            collection_name=vector_store.collection_name,
            prefetch=[
                Prefetch(
                    query=query_dense_vec,
                    using="dense",
                    limit=settings.RETRIEVER_TOP_K,
                    filter=query_filter
                ),
                Prefetch(
                    query=SparseVector(
                        indices=query_sparse_vec.indices.tolist(),
                        values=query_sparse_vec.values.tolist()
                    ),
                    using="sparse",
                    limit=settings.RETRIEVER_TOP_K,
                    filter=query_filter
                )
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=settings.RETRIEVER_TOP_K,
        )

        return [
            Document(
                page_content=res.payload["content"],
                metadata={
                    "doc_name": res.payload["doc_name"],
                    "chunk_id": res.payload["chunk_id"]
                }
            ) for res in results.points
        ]

    def retrieve(self, query: str, doc_ids: list[str] = None) -> list[Document]:
        query_filter = None
        if doc_ids:
            query_filter = Filter(
                must=[FieldCondition(key="doc_id", match=MatchAny(any=doc_ids))]
            )

        all_docs = []
        seen = set()

        queries_to_search = [query]

        expanded = []
        hyde_answer = ""

        with ThreadPoolExecutor(max_workers=2) as pool:
            mqe_future = pool.submit(self._generate_expanded_queries, query)
            hyde_future = pool.submit(self._generate_hyde_answer, query)

            expanded = mqe_future.result(timeout=20)
            hyde_answer = hyde_future.result(timeout=20)

        queries_to_search.extend(expanded)
        if hyde_answer:
            queries_to_search.append(hyde_answer)

        for q_text in queries_to_search:
            docs = self._single_retrieve(q_text, query_filter, doc_ids)
            for doc in docs:
                key = doc.page_content[:100]
                if key not in seen:
                    seen.add(key)
                    all_docs.append(doc)

        return all_docs[:settings.RETRIEVER_TOP_K]
