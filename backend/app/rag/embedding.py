import httpx
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.core.config import settings
from app.core.logger import logger

EMBED_MAX_WORKERS = 4


class OllamaEmbedding:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.EMBEDDING_MODEL_NAME

    def _try_new_api(self, text: str) -> List[float]:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{self.base_url}/api/embed",
                json={
                    "model": self.model,
                    "input": text
                }
            )
            response.raise_for_status()
            return response.json()["embeddings"][0]

    def embed(self, text: str) -> List[float]:
        try:
            return self._try_new_api(text)
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (404, 400):
                return self._legacy_embed(text)
            raise
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise

    def _legacy_embed(self, text: str) -> List[float]:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text
                }
            )
            response.raise_for_status()
            return response.json()["embedding"]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        try:
            result = self._batch_embed(texts)
            if result:
                return result
        except Exception as e:
            logger.warning(f"批量 embedding 失败，回退到并发模式: {e}")

        results = [None] * len(texts)

        def _embed_one(idx: int, text: str):
            return idx, self.embed(text)

        with ThreadPoolExecutor(max_workers=min(EMBED_MAX_WORKERS, len(texts))) as pool:
            futures = {pool.submit(_embed_one, i, t): i for i, t in enumerate(texts)}
            for future in as_completed(futures):
                idx, emb = future.result()
                results[idx] = emb

        return results

    def _batch_embed(self, texts: List[str]) -> List[List[float]]:
        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{self.base_url}/api/embed",
                json={
                    "model": self.model,
                    "input": texts
                }
            )
            response.raise_for_status()
            return response.json()["embeddings"]


embedding_model = OllamaEmbedding()
