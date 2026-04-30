from fastapi import FastAPI
from app.core.config import settings
import uvicorn

app = FastAPI(title=settings.PROJECT_NAME)

# 路由注册
from app.api.chat import router as chat_router
from app.api.rag import router as rag_router

app.include_router(chat_router, prefix="/api/chat", tags=["Chat Agent"])
app.include_router(rag_router, prefix="/api/rag", tags=["Knowledge Base"])

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "llm_model": settings.LLM_MODEL_NAME,
        "embedding_model": settings.EMBEDDING_MODEL_NAME
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)