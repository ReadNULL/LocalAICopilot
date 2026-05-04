import httpx
from typing import List

from app.core.config import settings
from app.core.logger import logger


class OllamaEmbedding:
    """
    基于 Ollama 的 Embedding 封装
    """

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.EMBEDDING_MODEL_NAME

    def embed(self, text: str) -> List[float]:
        try:
            with httpx.Client(timeout=60) as client:
                response = client.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": self.model,
                        "prompt": text
                    }
                )
                response.raise_for_status()
                return response.json()["embedding"]
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            embeddings.append(self.embed(text))
        return embeddings


# =========================
# 全局实例（单例）
# =========================
embedding_model = OllamaEmbedding()