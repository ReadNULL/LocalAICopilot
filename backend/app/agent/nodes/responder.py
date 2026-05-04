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

    def _self_check(self, draft_answer: str, docs: list) -> str:
        if not docs:
            return ""

        context_snippets = "\n\n".join([
            f"[Source {d.metadata.get('chunk_id', i)}] {d.page_content[:300]}"
            for i, d in enumerate(docs[:5])
        ])

        check_prompt = f"""你是一个严格的事实核查员。请逐条检查以下【AI回答】中的每个关键陈述，判断是否有【背景资料】作为依据。

对每个陈述标注:
✅ 有依据 - 该陈述可以在背景资料中找到直接或间接支持
❌ 无依据 - 该陈述在背景资料中完全找不到支持
⚠️ 部分依据 - 该陈述部分有支持，但包含背景资料中没有的额外信息

【背景资料】
{context_snippets}

【AI回答】
{draft_answer[:2000]}

请输出核查报告:"""
        try:
            check_llm = ChatOllama(
                model=settings.LLM_MODEL_NAME,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=0.0
            )
            result = check_llm.invoke([SystemMessage(content=check_prompt)])
            return result.content
        except Exception:
            return ""

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        docs = state.get("retrieved_docs", [])
        mode = state.get("mode", "rag")
        messages = state.get("messages", [])

        if mode == "rag" and not docs:
            return {
                "final_answer": "未找到相关信息，知识库中没有支持回答的内容。",
                "is_hallucinated": False,
                "validity_check": ""
            }

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

        final_messages = [SystemMessage(content=system_content)] + list(messages)
        draft_message = self.llm.invoke(final_messages, config={"tags": ["draft_llm"]})
        draft_answer = draft_message.content

        is_hallucinated = "未找到" not in draft_answer and len(docs) == 0 and mode == "rag"
        validity_check = ""
        if mode == "rag" and docs:
            validity_check = self._self_check(draft_answer, docs)

        return {
            "final_answer": draft_answer,
            "is_hallucinated": is_hallucinated,
            "validity_check": validity_check
        }
