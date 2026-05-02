# Local AI Copilot

> 本地部署的多 Agent 智能体 RAG 项目，使用 LangGraph 框架控制核心大脑与工作流，前后端采用 FastAPI + Next.js 构建，实现数据 100% 本地隐私安全。

---

[核心特性](#核心特性 ) · [🚀快速开始 - 本地部署指南](#快速开始) · [项目结构](#项目结构) · [技术亮点](#技术亮点)

##   核心特性 

- **🧠 智能规划大脑 (Planner Agent)**：基于 LangGraph 构建的状态机工作流。大模型能够自主判断用户的意图，智能路由到“工具执行”、“知识库检索”或“日常对话”。 

- **🛠️ 强大的本地工具链 (Tools)**：Agent 拥有读取本地文件、写入文件以及执行 Python 代码（沙盒内计算/处理）的能力，突破了传统 LLM 只能“动嘴”的限制。 

-  **📚 满血版混合检索 RAG**：集成了语义分块、MQE 多查询扩展、HyDE 假设文档嵌入、HNSW 向量 + BM25 关键字双路召回、RRF 合并以及 BGE 交叉重排的工业级 RAG 流水线。 

- **🛡️ 严格的防幻觉机制**：通过 Prompt 强约束、低温度采样、强制引用来源以及 LLM 结果后置校验，最大程度杜绝大模型的“胡说八道”。 

- **💻 现代化全栈 UI**：基于 Next.js + Tailwind CSS 打造的沉浸式聊天与本地文件管理界面，支持 Markdown 实时渲染与流式加载状态。
  
 ![img.png](https://github.com/ReadNULL/LocalAICopilot/blob/main/images/demo_png1.png?raw=true)

---

##  快速开始

### 1. 环境准备 
- 安装 **Docker** & **Docker Compose**
- 安装 **Node.js** (v18+) 
-  安装 **Python** (3.10+) 
- 安装 **Ollama** 并启动服务 
### 2. 拉取本地大模型 
在终端中执行以下命令，使用 Ollama 拉取模型： 
```bash 
# 1. 拉取对话大模型 (可替换为你喜欢的模型如 llama3) 
ollama pull qwen2.5 
# 2. 拉取 Embedding 模型 
ollama pull bge-large
```

### 3. 启动向量数据库 (Qdrant)

进入项目根目录，通过 Docker 启动数据库：

```bash
cd docker
docker-compose up -d
```

### 4. 后端服务部署

```bash
# 进入后端目录
cd backend

# 创建并激活虚拟环境 (可选但强烈推荐)
python -m venv .venv
source .venv/bin/activate  # Windows 用户使用: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量 (请复制 .env 模板并填写你的模型名)
# 首次启动会自动从 HuggingFace 下载 BGE-Reranker 权重，请保持网络畅通
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 5. 前端界面启动

```bash
# 另起一个终端，进入前端目录
cd frontend

# 安装前端依赖
npm install

# 配置环境变量
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > .env.local

# 启动开发服务器
npm run dev
```

打开浏览器访问 `http://localhost:3000`，开始享受你的专属 Local AI Copilot！

----

## 项目结构

<details>
<summary><strong>目录结构</strong> （点击展开）</summary>

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

</details>

-----

## 技术亮点

以下模块严格遵循系统初期设计的 RAG 策略实现：

### 1. 文档解析与处理

主要解析 PDF/Word/Markdown 等主要文档，提取信息。 整体流程如下：任意格式文档 → MarkItDown 转换 → Markdown 文本 → 智能分块 → 向量化 → 存储检索。  

- **Markdown 处理**：先按标题的层级结构划分，再按段落二次切分，最后按照句子和语意进行切分。如果碰到图片或者表格，会先解析成文本类型再进一步处理。  
- **PDF 处理**：先解析 PDF 中的所有表格和图片，转为 Markdown 文档类型再按 Markdown 处理的方式进行切分。  
- **代码块处理**：按类或函数进行切分，保留完整的代码块（不受 Token 长度强制限制）。  
- **问答对处理**：每个问答对作为一个独立 chunk，不进行二次切分。  

### 2. Chunk 语义切分策略

- **大小限制**：为防止信息稀释或截断，设定最大 ChunkSize 为 256 个 token，重叠部分 overlap 为 15%。  
- **语义切分**：使用 Embedding 模型计算相邻句子的语义相似度，确保文本块的上下文连贯性。  

### 3. 多模态与向量模型

- **Embedding 模型**：采用本地 Ollama 部署的 `bge-large-zh-v1.5`（1024维度），对中文支持极佳。  
- **向量数据库**：采用 Qdrant，轻量级且运维成本低。  

### 4. 混合检索策略 (Hybrid Search)

- **检索流程**：
  1. 大模型运用 **MQE** 生成等价的扩展提问，并运用 **HyDE** 推测假设性答案。  
  2. 携带扩展后的词袋进行 **HNSW 向量检索** + **BM25 关键字精确匹配**。  
- **合并与重排**：
  - 使用 **RRF (Reciprocal Rank Fusion)** 公式对双路结果合并排序：$RRF\_score(d)=\sum1/(k+rank_i(d))$，其中 k 设为 60。  
  - 提取 Top-20 后，使用本地部署的交叉编码器 `bge-reranker-v2-m3` 进行深度重排，最终提纯为 Top-5 供大模型阅读。  

### 5. RAG 幻觉处理策略 (Anti-Hallucination)

- **Prompt 约束**：明确要求大模型"只能基于检索结果回答，检索结果没有的信息不要编造"。  
- **引用标注**：要求大模型在回答时标注每条信息的来源 chunk，方便追溯。  
- **温度调低**：Temperature 设为 0.1，极大降低 LLM 生成的随机性。  
- **兜底回答**：检索结果相似度极低或为空时，强制回答"未找到相关信息"，阻断编造路径。  
- **输出自校验**：大模型生成初版回答后，进行二次自我检查（标注 ✅ 有依据 / ❌ 无依据 / ⚠️ 部分依据），并将报告一并展示给用户。

