import shutil
import json
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.core.config import settings
from app.core.logger import logger
from app.rag.ingest import ingest_document

router = APIRouter()


# =========================
# 工具函数
# =========================
def load_documents():
    meta_file = settings.DATA_DIR / "documents.json"
    if not meta_file.exists():
        return []

    with open(meta_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_documents(docs):
    meta_file = settings.DATA_DIR / "documents.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)


# =========================
# 1️⃣ 上传文档
# =========================
@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        file_path = settings.DOCS_DIR / file.filename

        # 保存文件
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        logger.info(f"文件已保存: {file.filename}")

        # 处理文档（同步版本）
        meta = ingest_document(file_path)

        return {
            "id": meta["id"],
            "filename": meta["name"],
            "chunks_count": meta["chunks"],
            "status": meta["status"]
        }

    except Exception as e:
        logger.error(f"上传失败: {e}")
        raise HTTPException(status_code=500, detail="文件上传失败")


# =========================
# 2️⃣ 获取文档列表
# =========================
@router.get("/documents")
def get_documents():
    docs = load_documents()
    return docs


# =========================
# 3️⃣ 启用 / 禁用文档
# =========================
@router.patch("/document/{doc_id}")
def toggle_document(doc_id: str, payload: dict):
    docs = load_documents()

    found = False
    for d in docs:
        if d["id"] == doc_id:
            d["enabled"] = payload.get("enabled", True)
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="文档不存在")

    save_documents(docs)

    return {"message": "updated"}


# =========================
# 4️⃣ 删除文档
# =========================
@router.delete("/document/{doc_id}")
def delete_document(doc_id: str):
    docs = load_documents()

    new_docs = [d for d in docs if d["id"] != doc_id]

    if len(new_docs) == len(docs):
        raise HTTPException(status_code=404, detail="文档不存在")

    # 删除向量文件
    vector_path = settings.VECTOR_STORE_DIR / f"{doc_id}.json"
    if vector_path.exists():
        vector_path.unlink()

    save_documents(new_docs)

    return {"message": "deleted"}