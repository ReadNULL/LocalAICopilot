from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, SparseVectorParams,
    PointStruct, SparseVector
)
from app.core.config import settings
from app.core.logger import logger
import uuid

class QdrantVectorStore:
    def __init__(self):
        self.client = QdrantClient(url=settings.QDRANT_URL)
        self.collection_name = "documents"
        self._init_collection()

    def _init_collection(self):
        collections = self.client.get_collections().collections
        names = [c.name for c in collections]
        if self.collection_name not in names:
            logger.info("创建全新的 Qdrant 混合检索 Collection")
            self.client.create_collection(
                collection_name=self.collection_name,
                # 配置稠密向量 (Ollama BGE-large)
                vectors_config={
                    "dense": VectorParams(
                        size=1024,
                        distance=Distance.COSINE
                    )
                },
                # 配置稀疏向量 (BM25)
                sparse_vectors_config={
                    "sparse": SparseVectorParams()
                }
            )

    def add(
        self,
        doc_id: str,
        chunks: list[str],
        dense_embeddings: list[list[float]],
        sparse_embeddings: list, # 传入生成的稀疏向量
        doc_name: str
    ):
        points = []
        for i, (chunk, dense_emb, sparse_emb) in enumerate(zip(chunks, dense_embeddings, sparse_embeddings)):
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    # 同时存入两种向量
                    vector={
                        "dense": dense_emb,
                        "sparse": SparseVector(
                            indices=sparse_emb.indices.tolist(),
                            values=sparse_emb.values.tolist()
                        )
                    },
                    payload={
                        "doc_id": doc_id,
                        "doc_name": doc_name,
                        "chunk_id": i,
                        "content": chunk
                    }
                )
            )
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        logger.info(f"成功存入 Qdrant: {len(points)} 个双路混合 chunks")

vector_store = QdrantVectorStore()