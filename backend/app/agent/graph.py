from typing import TypedDict, Annotated, Sequence, Any, Literal
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from app.rag.retriever import AdvancedRetriever
from app.rag.reranker import AdvancedReranker
from app.agent.nodes.planner import PlannerNode
from app.agent.nodes.tool_node import ToolExecutionNode
from app.agent.nodes.responder import ResponderNode


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    query: str
    mode: str
    doc_ids: list[str]
    retrieved_docs: list
    final_answer: str
    is_hallucinated: bool
    validity_check: str
    needs_rag: bool


retriever = AdvancedRetriever()
reranker = AdvancedReranker()
planner_node = PlannerNode()
tool_node = ToolExecutionNode()
responder_node = ResponderNode()


async def retrieve_action(state: AgentState) -> dict:
    print("📚 [Retrieve Node] 开始检索文档...")
    query = state.get("query", "")
    doc_ids = state.get("doc_ids", [])

    raw_docs = retriever.retrieve(query, doc_ids=doc_ids)
    print(f"   => 检索到 {len(raw_docs)} 条文档")
    reranked_docs = reranker.rerank(query, raw_docs)
    print(f"   => 重排序后保留 {len(reranked_docs)} 条文档")
    return {"retrieved_docs": reranked_docs}


async def planner_action(state: AgentState) -> dict:
    result = await planner_node.process(state)
    messages = result.get("messages", [])

    needs_rag = False
    if messages:
        last_msg = messages[-1] if isinstance(messages, list) else messages
        if hasattr(last_msg, "content") and "<NEED_RAG_SEARCH>" in (last_msg.content or ""):
            needs_rag = True

    if state.get("mode", "") == "rag":
        needs_rag = True

    result["needs_rag"] = needs_rag
    return result


def route_after_planner(state: AgentState) -> Literal["tools", "retrieve", "responder"]:
    messages = state.get("messages", [])
    if not messages:
        return "responder"

    last_msg = messages[-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"

    if state.get("needs_rag", False):
        return "retrieve"

    return "responder"


def route_after_tools(state: AgentState) -> Literal["planner", "responder"]:
    messages = state.get("messages", [])
    if not messages:
        return "responder"

    for msg in reversed(messages):
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            return "planner"

    return "responder"


workflow = StateGraph(AgentState)
workflow.add_node("planner", planner_action)
workflow.add_node("tools", tool_node.process)
workflow.add_node("retrieve", retrieve_action)
workflow.add_node("responder", responder_node.process)

workflow.set_entry_point("planner")

workflow.add_conditional_edges(
    "planner",
    route_after_planner,
    {
        "tools": "tools",
        "retrieve": "retrieve",
        "responder": "responder"
    }
)

workflow.add_conditional_edges(
    "tools",
    route_after_tools,
    {
        "planner": "planner",
        "responder": "responder"
    }
)

workflow.add_edge("retrieve", "responder")
workflow.add_edge("responder", END)

app_graph = workflow.compile()
