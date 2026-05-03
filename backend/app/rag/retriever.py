from langchain_core.documents import Document
from qdrant_client.models import Prefetch, FusionQuery, Fusion, SparseVector, Filter, FieldCondition, MatchAny
from app.core.config import settings
from app.rag.embedding import embedding_model
from app.rag.vector_store import vector_store
from app.rag.ingest import sparse_model

class AdvancedRetriever:
    def retrieve(self, query: str, doc_ids: list[str] = None) -> list[Document]:
        # 1. 生成查询的稠密与稀疏向量
        query_dense_vec = embedding_model.embed(query)
        query_sparse_vec = list(sparse_model.embed([query]))[0]

        # 2. 构造文档过滤条件（如果选中了特定文档）
        query_filter = None
        if doc_ids:
            query_filter = Filter(
                must=[FieldCondition(key="doc_id", match=MatchAny(any=doc_ids))]
            )

        # 3. 让 Qdrant 底层极速执行双路检索与 RRF 融合
        results = vector_store.client.query_points(
            collection_name=vector_store.collection_name,
            prefetch=[
                # 稠密检索预抓取
                Prefetch(
                    query=query_dense_vec,
                    using="dense",
                    limit=settings.RETRIEVER_TOP_K,
                    filter=query_filter
                ),
                # 稀疏检索(BM25)预抓取
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
            # 告诉 Qdrant 自动执行 RRF 融合
            query=FusionQuery(fusion=Fusion.RRF),
            limit=settings.RETRIEVER_TOP_K,
        )

        # 4. 转化为 LangChain Document 格式供下游使用
        return [
            Document(
                page_content=res.payload["content"],
                metadata={
                    "doc_name": res.payload["doc_name"],
                    "chunk_id": res.payload["chunk_id"]
                }
            ) for res in results.points
        ]