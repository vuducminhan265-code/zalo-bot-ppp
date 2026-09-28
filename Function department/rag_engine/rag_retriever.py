# Function department/rag_engine/rag_retriever.py
import os
import sys
import json
import sqlite3
import math
from typing import List, Dict, Any

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

class RAGRetriever:
    """Hybrid BM25/TF-IDF retriever over indexed document chunks in SQLite."""

    def __init__(self, db_path: str = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.db_path = db_path or os.path.join(base_dir, "data", "database", "rag_index.db")

    def tokenize(self, text: str) -> List[str]:
        words = [w.lower() for w in text.split()]
        clean_words = []
        for w in words:
            clean = "".join([c for c in w if c.isalnum()])
            if len(clean) > 1:
                clean_words.append(clean)
        return clean_words

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        query_terms = self.tokenize(query)
        if not query_terms:
            return []

        if not os.path.exists(self.db_path):
            return []

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT chunk_id, source, text, terms_json FROM chunks")
        rows = cur.fetchall()
        conn.close()

        results = []
        for chunk_id, source, text, terms_json in rows:
            terms = json.loads(terms_json)
            if not terms:
                continue

            # Calculate BM25/TF-IDF-like match score
            score = 0
            for qt in query_terms:
                tf = terms.count(qt)
                if tf > 0:
                    score += (1 + math.log(tf)) * (1.0 + (10.0 if qt in text.lower() else 1.0))

            if score > 0:
                results.append({
                    "chunk_id": chunk_id,
                    "source": source,
                    "text": text,
                    "score": round(score, 3)
                })

        # Sort by relevance score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

if __name__ == "__main__":
    retriever = RAGRetriever()
    hits = retriever.search("nhắc việc Zalo Bot", top_k=2)
    print("Search Results:", json.dumps(hits, ensure_ascii=False, indent=2))
