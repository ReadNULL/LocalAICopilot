from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import chat, rag

app = FastAPI(title="Local AI Copilot", version="0.1.0")

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