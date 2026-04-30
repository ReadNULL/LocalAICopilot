import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.rag.ingest import SemanticChunker
from app.rag.embedding import VectorDBManager

router = APIRouter()

# 初始化 RAG 处理模块
chunker = SemanticChunker()
vdb_manager = VectorDBManager()

# 确保本地数据目录存在，符合 README 的目录规划[cite: 2]
DOCS_DIR = os.path.join(os.getcwd(), "data", "docs")
os.makedirs(DOCS_DIR, exist_ok=True)


class UploadResponse(BaseModel):
    filename: str
    message: str
    chunks_count: int


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    上传文档端点：自动执行 [保存 -> 格式转换 -> 语义分块 -> 向量化 -> 入库] 全流程
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="没有提供文件")

    file_path = os.path.join(DOCS_DIR, file.filename)

    try:
        # 1. 保存上传的文件到本地 `data/docs/` 目录
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"\n📄 [RAG API] 文件已成功保存至本地: {file_path}")

        # 2. 调用 MarkItDown 和 SemanticChunker 进行语义分块
        print("✂️ [RAG API] 正在调用底层模型进行文档解析与语义分块...")
        chunks = chunker.process_document(file_path)

        if not chunks:
            raise HTTPException(status_code=400, detail="未能从文档中提取到有效的文本内容。")

        # 3. 调用本地大模型计算 Embeddings 并写入 Qdrant
        print(f"🧠 [RAG API] 解析成功！准备将 {len(chunks)} 个 Chunk 向量化并存入数据库...")
        vdb_manager.store_chunks(chunks)

        print("✅ [RAG API] 知识库录入全流程完成！")
        return UploadResponse(
            filename=file.filename,
            message="文件上传、解析并向量化入库成功！",
            chunks_count=len(chunks)
        )

    except Exception as e:
        print(f"❌ [RAG API] 文档处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"文档处理失败: {str(e)}")
    finally:
        # 释放文件指针
        file.file.close()