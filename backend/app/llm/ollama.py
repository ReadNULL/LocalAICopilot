import httpx
from typing import Dict, List, Optional
from ..core.config import settings


class OllamaManager:
    """
    负责直接与本地 Ollama 服务的原生 API 进行交互，
    用于状态监控、模型检查以及底层的原生调用。
    """

    def __init__(self):
        # 确保 baseUrl 格式正确，去除末尾斜杠
        self.base_url = settings.OLLAMA_BASE_URL.rstrip('/')
        self.llm_model = settings.LLM_MODEL_NAME
        self.embedding_model = settings.EMBEDDING_MODEL_NAME

    async def check_health(self) -> bool:
        """检查 Ollama 服务是否正在运行"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
                return response.status_code == 200
        except httpx.RequestError:
            return False

    async def get_downloaded_models(self) -> List[str]:
        """获取本地已安装的所有模型列表"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    return [model["name"] for model in data.get("models", [])]
        except Exception:
            return []
        return []

    async def verify_required_models(self) -> Dict[str, dict]:
        """校验我们在 config.py 中配置的模型是否已经存在于本地"""
        models = await self.get_downloaded_models()

        # 简单匹配模型名前缀，例如 "qwen2.5" 能匹配到 "qwen2.5:latest"
        is_llm_installed = any(self.llm_model in m for m in models)
        is_embedding_installed = any(self.embedding_model in m for m in models)

        return {
            "llm": {
                "name": self.llm_model,
                "installed": is_llm_installed
            },
            "embedding": {
                "name": self.embedding_model,
                "installed": is_embedding_installed
            }
        }

    async def generate_text(self, prompt: str, temperature: float = 0.7) -> Optional[str]:
        """
        提供一个原生的文本生成方法，供 LangChain 以外的轻量级场景使用
        """
        payload = {
            "model": self.llm_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload, timeout=60.0)
                if response.status_code == 200:
                    return response.json().get("response", "")
        except Exception as e:
            from app.core.logger import logger
            logger.error(f"Ollama 原生调用失败: {e}")
            return None


# 导出单例对象
ollama_manager = OllamaManager()