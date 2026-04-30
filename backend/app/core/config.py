from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Local AI Copilot"

    # ==========================================
    # 模型本地部署配置 (请在 .env 文件中自行配置)
    # ==========================================
    OLLAMA_BASE_URL: str = ""  # 示例: "http://localhost:11434"
    LLM_MODEL_NAME: str = ""  # 示例: "qwen2.5" 或 "llama3"
    EMBEDDING_MODEL_NAME: str = ""  # README指定: "bge-large-zh-v1.5"
    RERANK_MODEL_NAME: str = ""  # README指定: "bge-reranker-v2-m3"

    # ==========================================
    # 向量数据库配置 (Qdrant)
    # ==========================================
    QDRANT_URL: str = ""  # 示例: "http://localhost:6333"
    QDRANT_API_KEY: str = ""  # 如果没有设置鉴权可留空

    # ==========================================
    # RAG Chunking 策略配置 (基于 README)
    # ==========================================
    CHUNK_SIZE: int = 256  # 最大 Chunk 大小
    CHUNK_OVERLAP_PERCENT: float = 0.15  # 重叠部分 15%

    # 检索配置
    RETRIEVER_TOP_K: int = 20  # 最终只检索 Top-20 的相关数据
    RERANK_TOP_K: int = 5  # 重排 Top-5 的检索数据
    MAX_RETRIES: int = 3  # 最大检索重试次数

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'


settings = Settings()