import re
import numpy as np
import tiktoken
from typing import List, Dict
from markitdown import MarkItDown
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from app.core.config import settings


class SemanticChunker:
    def __init__(self):
        # 初始化 MarkItDown (处理 PDF/Word/Excel 等转 Markdown)
        self.md_parser = MarkItDown()

        # 初始化本地 Embedding 模型
        self.embeddings = OllamaEmbeddings(
            model=settings.EMBEDDING_MODEL_NAME,
            base_url=settings.OLLAMA_BASE_URL
        )

        # Token 计数器 (使用通用的 cl100k_base 估算 Token)
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.max_tokens = settings.CHUNK_SIZE
        self.overlap_tokens = int(settings.CHUNK_SIZE * settings.CHUNK_OVERLAP_PERCENT)

        # Markdown 标题切割器
        self.headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        self.md_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on,
            strip_headers=False
        )

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算两个向量的余弦相似度"""
        dot_product = np.dot(vec1, vec2)
        norm_a = np.linalg.norm(vec1)
        norm_b = np.linalg.norm(vec2)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def split_into_sentences(self, text: str) -> List[str]:
        """按标点符号进行分句（支持中英文）"""
        # 简单正则：按句号、问号、叹号、换行符分割，并保留标点
        sentences = re.split(r'(?<=[。！？.!?\n])', text)
        return [s.strip() for s in sentences if s.strip()]

    def merge_sentences_semantically(self, sentences: List[str], metadata: Dict) -> List[Dict]:
        """基于语义相似度和 Token 限制合并句子"""
        if not sentences:
            return []

        # 1. 批量获取句子的 Embedding
        sentence_embeddings = self.embeddings.embed_documents(sentences)

        chunks = []
        current_chunk = sentences[0]
        current_tokens = self.count_tokens(current_chunk)

        # 记录用于 overlap 的句子缓存
        sentence_buffer = [sentences[0]]

        for i in range(1, len(sentences)):
            next_sentence = sentences[i]
            next_tokens = self.count_tokens(next_sentence)

            # 计算相邻句子的语义连贯性
            similarity = self.cosine_similarity(sentence_embeddings[i - 1], sentence_embeddings[i])

            # 设定相似度阈值 (可根据 bge-large-zh 的特性微调，这里暂定 0.6)
            is_semantically_connected = similarity > 0.60
            is_size_allowed = (current_tokens + next_tokens) <= self.max_tokens

            if is_semantically_connected and is_size_allowed:
                # 语义连贯且未超长，继续合并
                current_chunk += " " + next_sentence
                current_tokens += next_tokens
                sentence_buffer.append(next_sentence)
            else:
                # 语义断层 或 达到最大 Token，进行截断并保存当前 Chunk
                chunks.append({
                    "content": current_chunk,
                    "metadata": {**metadata, "tokens": current_tokens}
                })

                # 处理 Overlap: 从上一个 Chunk 的尾部捞取部分句子作为新 Chunk 的开头
                overlap_text = ""
                overlap_tokens = 0
                for s in reversed(sentence_buffer):
                    s_tokens = self.count_tokens(s)
                    if overlap_tokens + s_tokens <= self.overlap_tokens:
                        overlap_text = s + " " + overlap_text
                        overlap_tokens += s_tokens
                    else:
                        break

                # 开启新 Chunk
                current_chunk = (overlap_text + next_sentence).strip()
                current_tokens = self.count_tokens(current_chunk)
                sentence_buffer = [next_sentence]  # 重新收集当前块的句子

        # 保存最后一个 Chunk
        if current_chunk:
            chunks.append({
                "content": current_chunk,
                "metadata": {**metadata, "tokens": current_tokens}
            })

        return chunks

    def process_document(self, file_path: str) -> List[Dict]:
        """完整处理流程：文档 -> Markdown -> 结构拆解 -> 语义分块"""
        final_chunks = []

        # 1. MarkItDown 读取并转换
        try:
            md_result = self.md_parser.convert(file_path)
            markdown_text = md_result.text_content
        except Exception as e:
            raise RuntimeError(f"MarkItDown 解析失败: {e}")

        # 2. 按 Markdown 标题层级初步切分 (保留文档层级结构)
        md_splits = self.md_splitter.split_text(markdown_text)

        for split in md_splits:
            content = split.page_content
            metadata = split.metadata  # 包含了 H1, H2 等层级信息

            # 3. 针对代码块的特殊处理：提取代码块不拆分
            code_blocks = re.findall(r'```.*?```', content, re.DOTALL)
            text_without_code = re.sub(r'```.*?```', ' [CODE_BLOCK] ', content, flags=re.DOTALL)

            # 4. 对普通文本进行句子级语义切分
            sentences = self.split_into_sentences(text_without_code)
            semantic_chunks = self.merge_sentences_semantically(sentences, metadata)

            # 5. 将代码块作为独立的高优 Chunk 加回 (代码块不强制 256 Token 限制，以保全逻辑)
            for code in code_blocks:
                semantic_chunks.append({
                    "content": code,
                    "metadata": {**metadata, "type": "code", "tokens": self.count_tokens(code)}
                })

            final_chunks.extend(semantic_chunks)

        return final_chunks


# 测试使用示例
# if __name__ == "__main__":
#     chunker = SemanticChunker()
#     # chunks = chunker.process_document("path/to/your/test_doc.pdf")
#     # print(f"一共切分出 {len(chunks)} 个片段")