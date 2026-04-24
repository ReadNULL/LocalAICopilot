

## 项目结构

<detail>
```text
local-ai-copilot/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI入口
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── logger.py
│   │
│   │   ├── llm/
│   │   │   ├── ollama.py        # LLM调用
│   │
│   │   ├── rag/
│   │   │   ├── ingest.py        # 文档导入
│   │   │   ├── retriever.py     # 检索
│   │   │   ├── embedding.py
│   │
│   │   ├── agent/
│   │   │   ├── graph.py         # LangGraph核心
│   │   │   ├── nodes/
│   │   │   │   ├── planner.py
│   │   │   │   ├── tool_node.py
│   │   │   │   ├── responder.py
│   │
│   │   ├── tools/
│   │   │   ├── python_tool.py
│   │   │   ├── file_tool.py
│   │
│   │   ├── api/
│   │   │   ├── chat.py
│   │   │   ├── rag.py
│   │
│   ├── requirements.txt
│
├── frontend/
│   ├── web-ui/ (React / Vue)
│
├── docker/
│   ├── docker-compose.yml
│
├── data/
│   ├── docs/
│   ├── vector_store/
│
├── tests/
│
├── README.md
```
</detail>