import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DOCS_DIR: Path = DATA_DIR / "docs"
    VECTOR_STORE_DIR: Path = DATA_DIR / "vector_store"

    # 大模型配置
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "qwen2.5")
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "bge-large-zh-v1.5")
    RERANK_MODEL_NAME: str = os.getenv("RERANK_MODEL_NAME", "BAAI/bge-reranker-v2-m3")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")

    # RAG 参数
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", 256))
    CHUNK_OVERLAP_PERCENT: float = float(os.getenv("CHUNK_OVERLAP_PERCENT", 0.15))
    RETRIEVER_TOP_K: int = int(os.getenv("RETRIEVER_TOP_K", 20))
    RERANK_TOP_K: int = int(os.getenv("RERANK_TOP_K", 5))

    # 幻觉控制温度
    TEMPERATURE: float = 0.1

    class Config:
        env_file = ".env"


settings = Settings()

# 初始化目录
for d in [settings.DATA_DIR, settings.DOCS_DIR, settings.VECTOR_STORE_DIR]:
    d.mkdir(parents=True, exist_ok=True)