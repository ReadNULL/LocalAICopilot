import requests
from typing import List

from app.core.config import settings
from app.core.logger import logger


class OllamaEmbedding:
    """
    基于 Ollama 的 Embedding 封装
    """

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.EMBEDDING_MODEL

    def embed(self, text: str) -> List[float]:
        """
        单条文本 embedding
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text
                },
                timeout=60
            )

            response.raise_for_status()
            data = response.json()

            return data["embedding"]

        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量 embedding（简单循环版本）
        """
        embeddings = []
        for text in texts:
            embeddings.append(self.embed(text))
        return embeddings


# =========================
# 全局实例（单例）
# =========================
embedding_model = OllamaEmbedding()