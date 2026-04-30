from typing import Dict, Any
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings
from app.tools import TOOLS


class PlannerNode:
    def __init__(self):
        # 1. 初始化聊天大模型 (必须使用支持 Function Calling / Tool Binding 的 Chat 模型)
        self.llm = ChatOllama(
            model=settings.LLM_MODEL_NAME,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.1  # 规划节点需要极度冷静和逻辑严密，温度设低
        )

        # 2. 将本地工具绑定到大模型上，告诉它“你有这些手脚可用”
        self.llm_with_tools = self.llm.bind_tools(TOOLS)

        # 3. 设定 Agent 的“人设”和行为准则
        self.system_prompt = """
        你是 Local AI Copilot，一个强大的本地智能助手。
        你的核心任务是分析用户的请求，并决定如何最好地完成它。

        你拥有以下能力选项：
        1. 【直接回答】：如果用户的请求是普通的闲聊，或者依靠你的常识就能直接解答，请直接回答。
        2. 【调用工具】：如果你需要进行复杂的数学计算、运行代码，或者需要读取、写入本地文件，请果断调用你绑定的工具。
        3. 【知识库检索】：如果用户的问题明显涉及特定的项目文档、私人数据或专业知识（比如“根据文档…”、“帮我查一下…”），请不要强行编造，直接回复一个包含特定关键词的指令：<NEED_RAG_SEARCH>。

        请仔细思考并做出选择。
        """

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangGraph 节点入口：决定下一步的行动路径
        """
        messages = state.get("messages", [])
        query = state.get("query", "")

        print("🧠 [Planner Node] 正在思考用户的请求...")

        # 如果 state 里的 messages 是空的，说明是第一轮对话，我们帮它组装
        if not messages:
            # 加入系统人设和用户的提问
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=query)
            ]

        # 让绑定了工具的大模型进行推理
        # 模型会返回一个 AIMessage：
        # - 如果它决定用工具，这个 message 里会包含 tool_calls 字段
        # - 如果它决定直接回答或触发 RAG，它就只是一段文本
        response = self.llm_with_tools.invoke(messages)

        # 打印一下大模型的决策状态，方便你本地调试
        if hasattr(response, "tool_calls") and response.tool_calls:
            print(f"   => 💡 决策结果：决定调用工具 {response.tool_calls[0]['name']}")
        elif "<NEED_RAG_SEARCH>" in response.content:
            print("   => 💡 决策结果：判断为知识库查询，准备路由到 RAG 模块")
        else:
            print("   => 💡 决策结果：直接进行对话回复")

        # 返回的结果会由 LangGraph 自动合并到全局 State 的 messages 列表中
        return {"messages": [response]}