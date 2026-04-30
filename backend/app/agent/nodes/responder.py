from typing import List, Dict, Any
from langchain_community.llms import Ollama
from app.core.config import settings
from app.rag.retriever import Document


class ResponderNode:
    def __init__(self):
        # 严格控制温度 0.1-0.3，降低 LLM 的随机性，减少“编造”倾向[cite: 1]
        self.llm = Ollama(
            model=settings.LLM_MODEL_NAME,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.1
        )

    def format_context(self, docs: List[Document]) -> str:
        """格式化上下文并加入引用标记，方便 LLM 标注出处[cite: 1]"""
        context_str = ""
        for i, doc in enumerate(docs):
            # 尝试从元数据中提取文档层级信息
            source = doc.metadata.get("source", "未知文档")
            h1 = doc.metadata.get("Header 1", "")
            h2 = doc.metadata.get("Header 2", "")
            location = f"《{source}》 -> {h1} -> {h2}".strip(" ->")

            context_str += f"[参考资料 {i + 1}] 出处：{location}\n内容：{doc.content}\n\n"
        return context_str

    def generate_draft_answer(self, query: str, docs: List[Document]) -> str:
        """生成初版回答"""
        # 1. 兜底策略：当检索结果为空或低于阈值时，直接拒绝编造[cite: 1]
        if not docs:
            return "未找到相关信息。"

        context_str = self.format_context(docs)

        # 2. Prompt 约束：明确要求只能基于检索结果回答[cite: 1]
        prompt = f"""
        你是一个严谨的 AI 智能体。请基于以下【参考资料】回答用户的问题。

        严格遵守以下规则：
        1. 只能基于参考资料回答，检索结果没有的信息绝对不要编造。
        2. 在回答的每一句话后面，必须标注信息来源的编号（例如：[参考资料 1]）。
        3. 如果参考资料无法完全回答问题，请只回答你能确定的部分。

        用户问题：{query}

        【参考资料】
        {context_str}

        请回答：
        """
        return self.llm.invoke(prompt)

    def verify_answer(self, answer: str, docs: List[Document]) -> str:
        """输出自校验：大模型交叉检查生成的回答[cite: 1]"""
        if "未找到相关信息" in answer:
            return answer

        context_str = "\n".join([d.content for d in docs])

        # 3. 输出自校验 Prompt[cite: 1]
        verification_prompt = f"""
        请检查以下回答是否每一条都能在参考资料中找到依据。
        对于每条声明，标注：✅ 有依据 / ❌ 无依据 / ⚠️ 部分依据

        回答：{answer}

        参考资料：{context_str}

        请输出校验结果：
        """

        verification_result = self.llm.invoke(verification_prompt)
        return verification_result

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph 节点的执行入口"""
        query = state.get("query")
        docs = state.get("retrieved_docs", [])

        # 步骤 1：生成初步回答
        draft_answer = self.generate_draft_answer(query, docs)

        # 步骤 2：对初步回答进行幻觉校验[cite: 1]
        verification_report = self.verify_answer(draft_answer, docs)

        # 步骤 3：组合最终输出给用户 (可根据实际业务决定是否向用户展示校验报告)
        final_output = f"{draft_answer}\n\n---\n**自我校验报告**：\n{verification_report}"

        return {
            "final_answer": final_output,
            "is_hallucinated": "❌ 无依据" in verification_report
        }


# ==========================================
# 本地联调测试示例：
# ==========================================
# if __name__ == "__main__":
#     # responder = ResponderNode()
#     # state = {"query": "项目使用的向量数据库是什么？", "retrieved_docs": [...]}
#     # result = responder.process(state)
#     # print(result["final_answer"])
#     pass