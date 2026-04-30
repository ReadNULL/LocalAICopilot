from typing import TypedDict, Annotated, Sequence, Any
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

# 导入我们之前写好的节点和组件
from app.agent.nodes.planner import PlannerNode
from app.agent.nodes.tool_node import ToolExecutionNode
from app.agent.nodes.responder import ResponderNode
from app.rag.retriever import AdvancedRetriever
from app.rag.reranker import AdvancedReranker


# ==========================================
# 1. 定义全局状态 (State)
# ==========================================
class AgentState(TypedDict):
    # add_messages 会自动将新消息追加到列表中，而不是覆盖
    messages: Annotated[Sequence[BaseMessage], add_messages]
    query: str
    retrieved_docs: list
    final_answer: str
    is_hallucinated: bool


# ==========================================
# 2. 实例化各个节点和依赖
# ==========================================
planner_node = PlannerNode()
tool_node = ToolExecutionNode()
responder_node = ResponderNode()

# 初始化检索器和重排器
retriever = AdvancedRetriever()
reranker = AdvancedReranker()


def retrieve_action(state: AgentState) -> dict:
    """包装检索与重排逻辑为 LangGraph 节点"""
    query = state.get("query", "")
    print(f"🔎 [Retrieve Node] 正在从向量数据库检索相关信息: {query}")

    # 混合检索 Top-20
    raw_docs = retriever.retrieve(query)
    # 重排提纯 Top-5
    reranked_docs = reranker.rerank(query, raw_docs)

    return {"retrieved_docs": reranked_docs}


def route_after_planner(state: AgentState) -> str:
    """条件路由逻辑：决定 Planner 之后去哪个节点"""
    messages = state.get("messages", [])
    if not messages:
        return END

    last_message = messages[-1]

    # 情况 A: 大模型决定调用工具
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    # 情况 B: 大模型判断需要 RAG 知识库检索
    if "<NEED_RAG_SEARCH>" in last_message.content:
        return "retrieve"

    # 情况 C: 普通对话，大模型已经直接回答了
    return "end"


# ==========================================
# 3. 构建工作流图
# ==========================================
workflow = StateGraph(AgentState)

# 添加节点到图中
workflow.add_node("planner", planner_node.process)
workflow.add_node("tools", tool_node.process)
workflow.add_node("retrieve", retrieve_action)
workflow.add_node("responder", responder_node.process)

# 设定图的入口节点
workflow.set_entry_point("planner")

# 添加条件边（根据大模型的判断，动态决定流向）
workflow.add_conditional_edges(
    "planner",
    route_after_planner,
    {
        "tools": "tools",
        "retrieve": "retrieve",
        "end": END
    }
)

# 闭环：工具执行完毕后，必须回到 Planner 重新思考下一步
workflow.add_edge("tools", "planner")

# 单向：检索完毕后，将文档交给 Responder 生成最终回答和防幻觉校验
workflow.add_edge("retrieve", "responder")
workflow.add_edge("responder", END)

# 编译图 (产生可运行的 application)
app_graph = workflow.compile()

# ==========================================
# 本地联调测试示例：
# ==========================================
if __name__ == "__main__":
    print("🚀 LangGraph 工作流图已成功编译！")
    # 你可以取消以下注释来模拟一次完整的请求流转：
    # initial_state = {"query": "请帮我列出当前目录下的文件", "messages": []}
    # for output in app_graph.stream(initial_state):
    #     for key, value in output.items():
    #         print(f"✅ 节点 '{key}' 运行完毕.")