# Function department/tools/run_rag.py
import sys
import os
import json

current_dir = os.path.dirname(os.path.abspath(__file__))
func_dept_dir = os.path.dirname(current_dir)
if func_dept_dir not in sys.path:
    sys.path.insert(0, func_dept_dir)

from rag_engine.rag_retriever import RAGRetriever

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else ""
    retriever = RAGRetriever()
    hits = retriever.search(query, top_k=3)
    
    if not hits:
        print("Không tìm thấy tài liệu phù hợp trong kho RAG.")
    else:
        context_parts = []
        for c in hits:
            source = c.get('source', 'Văn bản')
            title = c.get('dieu_title', '')
            text = c.get('text', '')
            header = f"[Nguồn: {source}]"
            if title:
                header += f" - {title}"
            
            part = f"{header}\n{text}"
            if "cross_reference" in c:
                part += f"\n\n{c['cross_reference']}"
            context_parts.append(part)

        print("\n\n---\n\n".join(context_parts))
