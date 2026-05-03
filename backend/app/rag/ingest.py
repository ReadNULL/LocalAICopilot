import uuid
import json
from datetime import datetime
from pathlib import Path
from markitdown import MarkItDown
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings
from app.core.logger import logger
from app.rag.embedding import embedding_model
from app.rag.vector_store import vector_store
from fastembed import SparseTextEmbedding

# 初始化原生 BM25 模型（第一次运行会自动下载几MB的词表文件）
sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")

md_parser = MarkItDown()


def process_document_to_chunks(file_path: Path) -> list[str]:
    """使用 MarkItDown 将各类文件转为 Markdown，并执行分块"""
    # 1. 解析为 Markdown 文本
    conversion_result = md_parser.convert(str(file_path))
    full_text = conversion_result.text_content

    # 2. 按照 Markdown 层级和句子进行递归切分
    overlap_size = int(settings.CHUNK_SIZE * settings.CHUNK_OVERLAP_PERCENT)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=overlap_size,
        separators=["\n## ", "\n### ", "\n\n", "\n", "。", "！", "？", " ", ""]
    )

    return text_splitter.split_text(full_text)


def save_document_meta(meta: dict):
    meta_file = settings.DATA_DIR / "documents.json"
    docs = []
    if meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            docs = json.load(f)
    docs.insert(0, meta)  # 新文档在最前
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)


def ingest_document(file_path: Path) -> dict:
    doc_id = str(uuid.uuid4())
    filename = file_path.name
    logger.info(f"开始解析文档: {filename}")

    try:
        chunks = process_document_to_chunks(file_path)
        logger.info(f"切分完成: 共 {len(chunks)} 个 chunks")

        # 3. 向量化: 同时生成稠密和稀疏向量
        # 稠密向量 (Ollama BGE-large)
        dense_embeddings = embedding_model.embed_batch(chunks)
        # 稀疏向量 (FastEmbed BM25)
        sparse_embeddings = list(sparse_model.embed(chunks))

        # 4. 存入双路向量数据库
        vector_store.add(
            doc_id=doc_id,
            chunks=chunks,
            dense_embeddings=dense_embeddings,
            sparse_embeddings=sparse_embeddings,
            doc_name=file_path.name
        )

        meta = {
            "id": doc_id,
            "name": filename,
            "chunks": len(chunks),
            "status": "ready",
            "enabled": True,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        save_document_meta(meta)
        return meta
    except Exception as e:
        logger.error(f"解析失败: {e}")
        meta = {"id": doc_id, "name": filename, "chunks": 0, "status": "error", "enabled": False,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")}
        save_document_meta(meta)
        return meta