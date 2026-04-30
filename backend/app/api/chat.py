from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.agent.graph import app_graph

router = APIRouter()


# 定义接收前端数据的格式
class ChatRequest(BaseModel):
    query: str
    # 这里预留了 history 字段，未来如果你想实现多轮记住上下文的对话，
    # 可以在这里接收前端传来的历史消息，并塞入 State 的 messages 中
    # history: list = []


# 定义返回给前端的数据格式
class ChatResponse(BaseModel):
    answer: str
    is_hallucinated: bool


@router.post("/", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """
    与 Local AI Copilot 交互的核心端点
    """
    try:
        print(f"\n📥 收到 API 请求，用户提问: {request.query}")

        # 1. 初始化 LangGraph 的初始状态 (State)
        initial_state = {
            "query": request.query,
            "messages": []
        }

        # 2. 触发工作流！invoke 会同步等待整个图走到 END 节点
        print("⚙️ 正在启动 Agent 思考链路...")
        final_state = app_graph.invoke(initial_state)

        # 3. 解析图流转完毕后的最终状态
        # 情况 A：如果走了 RAG 知识库检索路线，答案会被 ResponderNode 写入 'final_answer'
        answer = final_state.get("final_answer")

        # 情况 B：如果是闲聊或者工具调用路线，Planner 或 Tool 会把答案写在 messages 的最后一条
        if not answer and final_state.get("messages"):
            answer = final_state["messages"][-1].content

        is_hallucinated = final_state.get("is_hallucinated", False)

        print("📤 API 请求处理完毕，准备返回给前端。")

        return ChatResponse(
            answer=answer,
            is_hallucinated=is_hallucinated
        )

    except Exception as e:
        print(f"❌ 运行工作流时发生致命错误: {e}")
        # 给前端返回标准的 500 报错格式
        raise HTTPException(status_code=500, detail=f"Agent 内部执行错误: {str(e)}")