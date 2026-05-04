import json
import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from langchain_core.messages import HumanMessage, AIMessage
from app.agent.graph import app_graph
from app.core.logger import logger

router = APIRouter()


class MessageItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    query: str
    mode: str = "rag"
    doc_ids: Optional[List[str]] = None
    history: Optional[List[MessageItem]] = []  # 历史消息


@router.post("/")
async def chat_stream_endpoint(req: ChatRequest):
    logger.info(f"收到提问: {req.query}, 模式: {req.mode}, 携带历史轮数: {len(req.history)}")

    # 将前端的历史记录转换为 LangChain 的消息对象
    langchain_messages = []
    if req.history:
        for msg in req.history:
            if msg.role == "user":
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                langchain_messages.append(AIMessage(content=msg.content))

    # 把当前的提问追加到最后
    langchain_messages.append(HumanMessage(content=req.query))

    initial_state = {
        "query": req.query,
        "mode": req.mode,
        "doc_ids": req.doc_ids or [],
        "messages": langchain_messages
    }

    async def event_generator():
        try:
            async for event in app_graph.astream_events(initial_state, version="v2"):
                kind = event["event"]
                name = event["name"]
                tags = event.get("tags", [])

                if kind == "on_chain_start" and name == "planner":
                    yield f"data: {json.dumps({'type': 'status', 'message': '正在分析请求...'})}\n\n"

                elif kind == "on_chain_end" and name == "planner":
                    output = event["data"]["output"]
                    needs_rag = output.get("needs_rag", False)
                    messages = output.get("messages", [])
                    decision = "chat"
                    if messages:
                        last_msg = messages[-1] if isinstance(messages, list) else messages
                        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                            decision = "tools"
                        elif needs_rag:
                            decision = "rag"
                    yield f"data: {json.dumps({'type': 'status', 'message': f'决策: {decision}'})}\n\n"

                elif kind == "on_chain_start" and name == "retrieve":
                    yield f"data: {json.dumps({'type': 'status', 'message': '正在检索知识库...'})}\n\n"

                elif kind == "on_chain_end" and name == "retrieve":
                    raw_docs = event["data"]["output"].get("retrieved_docs", [])
                    sources = [
                        {
                            "docName": doc.metadata.get("doc_name", "未知文档"),
                            "chunkId": doc.metadata.get("chunk_id", 0),
                            "score": doc.metadata.get("rerank_score", 0.0),
                            "content": doc.page_content
                        } for doc in raw_docs
                    ]
                    yield f"data: {json.dumps({'type': 'sources', 'data': sources})}\n\n"

                elif kind == "on_chain_start" and name == "tools":
                    yield f"data: {json.dumps({'type': 'status', 'message': '正在执行工具...'})}\n\n"

                elif kind == "on_chain_end" and name == "tools":
                    yield f"data: {json.dumps({'type': 'status', 'message': '工具执行完成'})}\n\n"

                elif kind == "on_chat_model_stream" and "draft_llm" in tags:
                    chunk = event["data"]["chunk"].content
                    if chunk:
                        yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

                elif kind == "on_chain_end" and name == "responder":
                    output = event["data"]["output"]
                    is_hallucinated = output.get("is_hallucinated", False)
                    validity_check = output.get("validity_check", "")
                    yield f"data: {json.dumps({'type': 'verification', 'is_hallucinated': is_hallucinated, 'validity_check': validity_check})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except asyncio.CancelledError:
            logger.info("客户端断开连接，流式输出已终止")
        except Exception as e:
            logger.error(f"流式输出异常: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")