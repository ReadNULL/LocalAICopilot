import json
from typing import Dict, Any
from langchain_core.messages import ToolMessage
from app.tools import TOOLS

# 建立工具映射表，方便通过名称快速调用对应的工具函数
TOOL_MAP = {tool.name: tool for tool in TOOLS}

class ToolExecutionNode:
    def __init__(self):
        print("🔧 ToolExecutionNode 已初始化，已挂载工具:", list(TOOL_MAP.keys()))

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangGraph 节点入口：负责解析并执行大模型发出的工具调用请求
        """
        messages = state.get("messages", [])
        if not messages:
            return {"messages": []}

        # 获取对话历史的最后一条消息（预期是大模型发出的 AIMessage）
        last_message = messages[-1]

        # 如果大模型没有要求调用工具，直接返回空，状态不发生更新
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return {"messages": []}

        tool_messages = []

        # 遍历所有的工具调用（大模型可能会一次性并行提出多个工具调用请求）
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call["id"]

            print(f"🛠️ [Tool Node] 正在执行工具: {tool_name}")
            print(f"   传入参数: {json.dumps(tool_args, ensure_ascii=False)}")

            try:
                if tool_name in TOOL_MAP:
                    tool_func = TOOL_MAP[tool_name]
                    # invoke 是 LangChain Tool 对象的标准调用方法，它会自动处理参数映射
                    result = tool_func.invoke(tool_args)
                    content = str(result)
                else:
                    content = f"执行失败：智能体尝试调用未注册的工具 '{tool_name}'"
            except Exception as e:
                content = f"执行失败：工具运行环境发生异常: {str(e)}"

            print(f"   执行结果: {content[:200]}...\n")

            # 必须将执行结果打包为 ToolMessage 格式，并将 tool_call_id 一致地传回去
            # 这样大模型才知道这是针对它哪个请求的反馈
            tool_message = ToolMessage(
                content=content,
                name=tool_name,
                tool_call_id=tool_call_id
            )
            tool_messages.append(tool_message)

        # 返回的结果字典中包含的 messages 会被 LangGraph 框架通过 reducer 自动追加到全局状态中
        return {"messages": tool_messages}