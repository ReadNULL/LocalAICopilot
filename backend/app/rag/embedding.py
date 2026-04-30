import uuid
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_community.embeddings import OllamaEmbeddings
from app.core.config import settings


class VectorDBManager:
    def __init__(self):
        # 初始化 Qdrant 客户端
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None
        )

        # 初始化本地 Embedding 模型[cite: 1]
        self.embeddings = OllamaEmbeddings(
            model=settings.EMBEDDING_MODEL_NAME,
            base_url=settings.OLLAMA_BASE_URL
        )

        # README 指定的 bge-large-zh-v1.5 的向量维度固定为 1024[cite: 1]
        self.vector_size = 1024

    def ensure_collection(self, collection_name: str = "local_kb"):
        """确保指定的集合存在，如果不存在则按照指定维度创建"""
        collections = self.client.get_collections().collections
        exists = any(col.name == collection_name for col in collections)

        if not exists:
            print(f"检测到集合 {collection_name} 不存在，正在创建...")
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_size,
                    distance=models.Distance.COSINE  # 文本检索最常用的余弦相似度
                )
            )
        return collection_name

    def store_chunks(self, chunks: List[Dict[str, Any]], collection_name: str = "local_kb"):
        """
        核心流：将处理好的 Chunks 向量化并批量存入 Qdrant 向量数据库[cite: 1]
        """
        if not chunks:
            print("没有收到需要入库的 Chunks 数据。")
            return

        self.ensure_collection(collection_name)

        # 1. 拆分文本和元数据
        texts = [chunk["content"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]

        print(f"正在调用大模型对 {len(texts)} 个文本块进行向量化 (根据本地显卡算力，可能需要一些时间)...")

        # 2. 调用本地 Ollama 进行批量 Embedding 计算
        vectors = self.embeddings.embed_documents(texts)

        # 3. 构造 Qdrant 的 Point 数据 (整合向量与 Payload 负载)
        points = []
        for text, vector, meta in zip(texts, vectors, metadatas):
            # 为每个 chunk 生成唯一的 UUID
            point_id = str(uuid.uuid4())

            # 整合文本内容和原有的 metadata 作为 payload 存入数据库
            payload = {
                "page_content": text,
                **meta
            }

            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
            )

        # 4. 批量插入 Qdrant
        print(f"正在写入 Qdrant 数据库...")
        self.client.upsert(
            collection_name=collection_name,
            points=points
        )
        print("向量入库完成！")


# ---------------------------------------------------------
# 本地联调测试示例：
# 如果你想跑通数据流，可以结合上一步的 ingest.py 一起测试：
# ---------------------------------------------------------
if __name__ == "__main__":
    # from ingest import SemanticChunker
    # chunker = SemanticChunker()
    # chunks = chunker.process_document("path/to/test.md")

    # manager = VectorDBManager()
    # manager.store_chunks(chunks)
    pass