from typing import List
from sentence_transformers import CrossEncoder
from app.core.config import settings
from app.rag.retriever import Document


class AdvancedReranker:
    def __init__(self):
        # 使用 sentence-transformers 本地加载重排模型
        # 首次运行会自动从 HuggingFace/ModelScope 下载 bge-reranker-v2-m3
        print(f"正在加载本地重排模型 {settings.RERANK_MODEL_NAME} ...")
        self.model = CrossEncoder(settings.RERANK_MODEL_NAME, max_length=512)

    def rerank(self, query: str, docs: List[Document], top_k: int = None) -> List[Document]:
        """
        对检索到的 Top-20 结果进行交叉编码重排，提取 Top-5
        """
        if not docs:
            return []

        top_k = top_k or settings.RERANK_TOP_K

        # 1. 构造模型输入对: [[query, doc1_content], [query, doc2_content], ...]
        pairs = [[query, doc.content] for doc in docs]

        # 2. 模型打分 (CrossEncoder 直接输出相关性 logit 分数)
        scores = self.model.predict(pairs)

        # 3. 将分数绑定回 Document 的 metadata 中
        for doc, score in zip(docs, scores):
            doc.metadata["rerank_score"] = float(score)

        # 4. 根据重排分数倒序排序
        reranked_docs = sorted(docs, key=lambda x: x.metadata["rerank_score"], reverse=True)

        print(f"重排完成，已从 {len(docs)} 条过滤至 Top-{top_k}")

        # 5. 截取 Top-K 返回[cite: 1]
        return reranked_docs[:top_k]