# backend/app/agent/nodes/responder.py
from typing import Dict, Any
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import SystemMessage
from app.core.config import settings


class ResponderNode:
    def __init__(self):
        self.llm = ChatOllama(
            model=settings.LLM_MODEL_NAME,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.TEMPERATURE
        )

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        docs = state.get("retrieved_docs", [])
        mode = state.get("mode", "rag")
        messages = state.get("messages", [])  # 提取完整的消息上下文

        if mode == "rag" and not docs:
            return {
                "final_answer": "未找到相关信息，知识库中没有支持回答的内容。",
                "is_hallucinated": False
            }

        # 动态构建系统提示词 (System Prompt)
        system_content = "你是一个智能的 Local AI Copilot。请结合前文语境，用自然专业的口吻与用户对话。\n"

        if mode == "rag":
            context_str = "\n".join([f"[Source {d.metadata.get('chunk_id', 0)}] {d.page_content}" for d in docs])
            system_content += f"""
            【强制约束】
            1. 必须基于以下【背景信息】回答问题，绝不能编造。
            2. 必须在引用的信息后标注来源，例如 [Source 1]。
            
            【背景信息】
            {context_str}
            """

        #  将 System Prompt 放在数组最前面，后面跟着前端传来的 user/assistant 历史记录和当前问题
        final_messages = [SystemMessage(content=system_content)] + list(messages)

        # 将整个对话流直接喂给大模型
        draft_message = await self.llm.ainvoke(final_messages, config={"tags": ["draft_llm"]})
        draft_answer = draft_message.content

        # 幻觉校验判断
        is_hallucinated = "未找到" not in draft_answer and len(docs) == 0 and mode == "rag"

        return {
            "final_answer": draft_answer,
            "is_hallucinated": is_hallucinated
        }