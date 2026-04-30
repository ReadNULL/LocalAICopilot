import json
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from rank_bm25 import BM25Okapi

from app.core.config import settings


class Document:
    def __init__(self, doc_id: str, content: str, metadata: dict = None):
        self.id = doc_id
        self.content = content
        self.metadata = metadata or {}


def rrf_merge(vector_results: List[Document], bm25_results: List[Document], k: int = 60) -> List[Document]:
    """RRF (Reciprocal Rank Fusion) 检索合并策略"""
    scores = {}
    docs_map = {}

    for rank, doc in enumerate(vector_results):
        scores[doc.id] = scores.get(doc.id, 0) + 1 / (k + rank + 1)
        docs_map[doc.id] = doc

    for rank, doc in enumerate(bm25_results):
        scores[doc.id] = scores.get(doc.id, 0) + 1 / (k + rank + 1)
        docs_map[doc.id] = doc

    # 根据 RRF 分数倒序排序
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # 组装合并后的 Document 列表
    return [docs_map[doc_id] for doc_id, score in sorted_scores]


class AdvancedRetriever:
    def __init__(self, collection_name: str = "local_kb"):
        self.collection_name = collection_name

        # 初始化 Qdrant 客户端
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None
        )

        # 初始化向量模型[cite: 1]
        self.embeddings = OllamaEmbeddings(
            model=settings.EMBEDDING_MODEL_NAME,
            base_url=settings.OLLAMA_BASE_URL
        )

        # 初始化用于扩展提问和生成假设答案的 LLM[cite: 1]
        self.llm = Ollama(
            model=settings.LLM_MODEL_NAME,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.3  # 降低温度以保证生成的扩展词准确性[cite: 1]
        )

        # BM25 语料库缓存 (用于关键字精确匹配)
        self.bm25_corpus = []
        self.bm25_docs = []
        self.bm25_model = None
        self._init_bm25()

    def _tokenize(self, text: str) -> List[str]:
        """简单的中文分字 token 化 (若生产环境可替换为 jieba)"""
        return list(text.lower())

    def _init_bm25(self):
        """初始化加载 Qdrant 中的所有文档用于构建 BM25 索引[cite: 1]"""
        try:
            records, _ = self.client.scroll(
                collection_name=self.collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=False
            )
            if records:
                for record in records:
                    content = record.payload.get("page_content", "")
                    doc = Document(doc_id=str(record.id), content=content, metadata=record.payload)
                    self.bm25_docs.append(doc)
                    self.bm25_corpus.append(self._tokenize(content))

                self.bm25_model = BM25Okapi(self.bm25_corpus)
                print(f"BM25 索引初始化完成，共加载 {len(self.bm25_docs)} 条数据。")
        except Exception as e:
            print(f"BM25 初始化失败 (可能是集合不存在): {e}")

    def _expand_query_hyde(self, original_query: str) -> List[str]:
        """MQE + HyDE: 生成多样化问题和假设性答案[cite: 1]"""
        prompt = f"""
        请你扮演一个专业的检索助手。为了提高在数据库中的检索召回率，请针对以下用户问题：
        1. 生成2个语义等价的不同问法。
        2. 尝试推测该问题可能的一个简短答案（重点包含可能出现的专业名词和关键字）。

        请直接输出结果，用换行符分隔每一条，不要有任何多余的解释。

        用户问题：{original_query}
        """
        try:
            response = self.llm.invoke(prompt)
            expanded_queries = [q.strip() for q in response.split('\n') if q.strip()]
            # 将原问题也加入检索列表
            expanded_queries.insert(0, original_query)
            return expanded_queries
        except Exception as e:
            print(f"HyDE 扩展查询失败，降级使用原问题: {e}")
            return [original_query]

    def _vector_search(self, query_texts: List[str], top_k: int = 20) -> List[Document]:
        """多路向量检索 (HNSW)[cite: 1]"""
        results_map = {}

        for q in query_texts:
            query_vector = self.embeddings.embed_query(q)
            hits = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k
            )
            for hit in hits:
                doc_id = str(hit.id)
                if doc_id not in results_map:
                    results_map[doc_id] = Document(
                        doc_id=doc_id,
                        content=hit.payload.get("page_content", ""),
                        metadata=hit.payload
                    )

        return list(results_map.values())

    def _bm25_search(self, query_texts: List[str], top_k: int = 20) -> List[Document]:
        """BM25 关键字检索[cite: 1]"""
        if not self.bm25_model:
            return []

        # 将所有扩展查询合并成一个大的关键词集合进行 BM25 匹配
        combined_query = " ".join(query_texts)
        tokenized_query = self._tokenize(combined_query)

        # 获取 Top-K 文档
        docs = self.bm25_model.get_top_n(tokenized_query, self.bm25_docs, n=top_k)
        return docs

    def retrieve(self, user_query: str) -> List[Document]:
        """完整的混合检索流水线[cite: 1]"""
        print(f"1. 正在对问题进行 MQE + HyDE 扩展...")
        expanded_queries = self._expand_query_hyde(user_query)
        print(f"扩展结果: {expanded_queries}")

        # 定义单路召回的数量，确保合并后能筛选出 Top-20[cite: 1]
        recall_k = settings.RETRIEVER_TOP_K * 2

        print(f"2. 正在执行多路向量检索...")
        vector_results = self._vector_search(expanded_queries, top_k=recall_k)

        print(f"3. 正在执行 BM25 关键字检索...")
        bm25_results = self._bm25_search(expanded_queries, top_k=recall_k)

        print(f"4. 使用 RRF 合并策略融合结果...")
        merged_results = rrf_merge(vector_results, bm25_results)

        # 截断只保留 Top-20 相关数据[cite: 1]
        final_top_k = merged_results[:settings.RETRIEVER_TOP_K]

        print(f"检索完成，最终召回 {len(final_top_k)} 条文档片段。")
        return final_top_k


# ==========================================
# 测试用例
# ==========================================
# if __name__ == "__main__":
    # 确保 config.py 中已经配置好了模型信息并启动了 Qdrant
    # retriever = AdvancedRetriever()
    # results = retriever.retrieve("如何配置本地大模型？")
    # for r in results:
    #     print(f"ID: {r.id} \n内容: {r.content[:50]}...\n")