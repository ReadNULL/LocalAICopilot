import signal
import sys
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import chat, rag
from app.core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    def _graceful_shutdown(signum, frame):
        logger.info(f"收到信号 {signum}，正在关闭服务...")
        sys.exit(0)

    signal.signal(signal.SIGINT, _graceful_shutdown)
    signal.signal(signal.SIGTERM, _graceful_shutdown)

    logger.info("Local AI Copilot 后端服务已启动")

    try:
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage
        from app.core.config import settings

        logger.info(f"正在预加载模型: {settings.LLM_MODEL_NAME}")
        warmup_llm = ChatOllama(
            model=settings.LLM_MODEL_NAME,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.1
        )
        warmup_llm.invoke([HumanMessage(content="你好")])
        logger.info("模型预加载完成，后续请求将更快响应")
    except Exception as e:
        logger.warning(f"模型预加载失败 (不影响服务运行): {e}")

    yield
    logger.info("Local AI Copilot 后端服务已关闭")


app = FastAPI(title="Local AI Copilot", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册子路由
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(rag.router, prefix="/api/rag", tags=["RAG"])

# 知识库Mock路由 (对应 api.js: fetchKnowledgeBases)
@app.get("/api/kb")
def get_knowledge_bases():
    return [{"id": "default", "name": "默认知识库"}]

# 健康检查 (对应 api.js: checkHealth)
@app.get("/health")
def health_check():
    return {"status": "ok"}