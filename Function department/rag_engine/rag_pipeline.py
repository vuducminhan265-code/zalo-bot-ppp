# Function department/rag_engine/rag_pipeline.py
import os
from dotenv import load_dotenv
from google import genai
from .rag_indexer import RAGIndexer
from .rag_retriever import RAGRetriever

load_dotenv()

class RAGPipeline:
    """Unified RAG Pipeline combining indexing, retrieval, and Gemini AI synthesis."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.indexer = RAGIndexer()
        self.retriever = RAGRetriever()
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def refresh_index(self) -> int:
        return self.indexer.index_documents()

    def query(self, user_query: str, top_k: int = 3) -> dict:
        """Retrieves relevant chunks and generates an AI answer grounded in the knowledge base."""
        chunks = self.retriever.search(user_query, top_k=top_k)
        
        if not chunks:
            return {
                "query": user_query,
                "answer": "Không tìm thấy tài liệu liên quan trong bộ tri thức (data/documents).",
                "sources": []
            }

        context_str = "\n\n---\n\n".join([f"[Nguồn: {c['source']}]\n{c['text']}" for c in chunks])
        sources = list(set([c['source'] for c in chunks]))

        if not self.client:
            return {
                "query": user_query,
                "answer": f"Đã tìm thấy {len(chunks)} đoạn tài liệu liên quan. (Chưa cấu hình GEMINI_API_KEY để tổng hợp câu trả lời).\n\n" + context_str,
                "sources": sources,
                "raw_chunks": chunks
            }

        prompt = f"""Bạn là Trợ lý AI Quản lý Tri thức cho Dự án Zalo Bot và PPP.
Dựa TRỰC TIẾP và CHÍNH XÁC vào bộ tri thức được trích xuất dưới đây để trả lời câu hỏi của Alexander.

--- BỘ TRI THỨC TRÍCH XUẤT ---
{context_str}

--- CÂU HỎI ---
{user_query}

--- HƯỚNG DẪN TRẢ LỜI ---
1. Trả lời rõ ràng, chính xác, nêu rõ căn cứ từ nguồn tài liệu.
2. Nếu bộ tri thức không có đủ thông tin, hãy ghi rõ "Tài liệu hiện tại chưa đề cập đến nội dung này".
3. Trích dẫn tên file nguồn ở cuối câu trả lời.
"""

        models_to_try = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite', 'gemini-flash-lite-latest', 'gemini-3.5-flash']
        last_err = None
        for model_name in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                answer_text = response.text
                last_err = None
                break
            except Exception as e:
                last_err = str(e)

        if last_err:
            answer_text = f"Nội dung trích xuất RAG:\n{context_str}\n\n(Lưu ý: Không gọi được AI synthesis: {last_err})"

        return {
            "query": user_query,
            "answer": answer_text,
            "sources": sources,
            "raw_chunks": chunks
        }

if __name__ == "__main__":
    rag = RAGPipeline()
    rag.refresh_index()
    res = rag.query("Quy trình Zalo bot hoạt động như thế nào?")
    print("=== RAG QUERY RESULT ===")
    print(res["answer"])
