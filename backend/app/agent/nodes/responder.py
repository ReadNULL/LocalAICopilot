import time
from typing import Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.core.config import settings


class ResponderNode:
    def __init__(self):
        self.llm = ChatOllama(
            model=settings.LLM_MODEL_NAME,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.TEMPERATURE
        )
        self.executor = ThreadPoolExecutor(max_workers=2)

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

    def _call_llm(self, messages):
        draft_message = self.llm.invoke(messages)
        return draft_message.content or ""

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        print("📝 [Responder Node] 正在生成回复...")
        docs = state.get("retrieved_docs", [])
        mode = state.get("mode", "rag")
        messages = state.get("messages", [])

        filtered_messages = []
        for msg in messages:
            if isinstance(msg, AIMessage):
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    filtered_messages.append(msg)
                else:
                    filtered_messages.append(msg)
            else:
                filtered_messages.append(msg)

        human_only = [m for m in filtered_messages if isinstance(m, HumanMessage)]
        if human_only:
            context_messages = human_only
        else:
            context_messages = filtered_messages

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

        final_messages = [SystemMessage(content=system_content)] + context_messages
        
        print(f"   => 构建的消息列表 (共 {len(final_messages)} 条):")
        for i, msg in enumerate(final_messages):
            msg_type = type(msg).__name__
            content_preview = (msg.content or "")[:100].replace('\n', ' ') if hasattr(msg, 'content') else "[NO CONTENT]"
            print(f"      [{i}] {msg_type}: {content_preview}")
        
        print(f"   => 正在调用 LLM 生成回复 (model={self.llm.model})...")
        
        draft_answer = ""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"   => 第 {attempt + 1} 次尝试 (模型冷启动重试)...")
                    time.sleep(1)
                
                loop = asyncio.get_event_loop()
                draft_answer = await loop.run_in_executor(
                    self.executor,
                    self._call_llm,
                    final_messages
                )
                
                print(f"   => LLM 返回 content: {repr(draft_answer[:200])}")
                if draft_answer:
                    break
                print(f"   => ⚠️ 第 {attempt + 1} 次尝试返回空内容")
            except Exception as e:
                print(f"   => ❌ LLM 调用异常 (第 {attempt + 1} 次): {e}")
                import traceback
                traceback.print_exc()
        
        print(f"   => 回复生成完成 ({len(draft_answer)} 字符)")

        if not draft_answer:
            print("   => ⚠️ 警告: LLM 多次尝试后仍返回内容为空")

        is_hallucinated = "未找到" not in draft_answer and len(docs) == 0 and mode == "rag"
        validity_check = ""
        if mode == "rag" and docs:
            validity_check = self._self_check(draft_answer, docs)

        return {
            "final_answer": draft_answer,
            "is_hallucinated": is_hallucinated,
            "validity_check": validity_check
        }
