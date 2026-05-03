from typing import TypedDict, Annotated, Sequence, Any
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from app.rag.retriever import AdvancedRetriever
from app.rag.reranker import AdvancedReranker
from app.agent.nodes.responder import ResponderNode


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    query: str
    mode: str
    doc_ids: list[str]
    retrieved_docs: list
    final_answer: str
    is_hallucinated: bool


retriever = AdvancedRetriever()
reranker = AdvancedReranker()
responder_node = ResponderNode()


def retrieve_action(state: AgentState) -> dict:
    """混合检索与重排序节点"""
    query = state.get("query", "")
    doc_ids = state.get("doc_ids", [])

    # 抽取 Top-20 (融合后)
    raw_docs = retriever.retrieve(query, doc_ids=doc_ids)

    # BGE-Reranker 二次重排提纯至 Top-5
    reranked_docs = reranker.rerank(query, raw_docs)
    return {"retrieved_docs": reranked_docs}


def route_request(state: AgentState) -> str:
    """路由网关"""
    mode = state.get("mode", "rag")
    if mode == "rag":
        return "retrieve"
    return "responder"  # 普通聊天模式跳过检索


# 构建状态机
workflow = StateGraph(AgentState)
workflow.add_node("retrieve", retrieve_action)
workflow.add_node("responder", responder_node.process)

workflow.set_conditional_entry_point(
    route_request,
    {
        "retrieve": "retrieve",
        "responder": "responder"
    }
)

workflow.add_edge("retrieve", "responder")
workflow.add_edge("responder", END)

app_graph = workflow.compile()