# Function department/rag_engine/rag_retriever.py
import os
import sys
import json
import sqlite3
import re
import math
from typing import List, Dict, Any

current_dir = os.path.dirname(os.path.abspath(__file__))
func_dept_dir = os.path.dirname(current_dir)
if func_dept_dir not in sys.path:
    sys.path.insert(0, func_dept_dir)

try:
    from tools.thuvienphapluat_crawler import ThuvienPhapLuatCrawler
except Exception:
    ThuvienPhapLuatCrawler = None

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

class RAGRetriever:
    """Master Legal RAG Retriever supporting exact structured legal article parsing, cross-referencing, and BM25 fallback."""

    def __init__(self, db_path: str = None):
        self.tvpl_crawler = ThuvienPhapLuatCrawler() if ThuvienPhapLuatCrawler else None
        
        if db_path:
            self.db_path = db_path
        else:
            # Locate master legal database under PPP - Sở Tài Chính project root
            zalo_bot_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            ppp_root = os.path.dirname(os.path.dirname(zalo_bot_dir))
            
            master_db1 = os.path.join(ppp_root, "data", "database", "rag_index.db")
            master_db2 = os.path.join(zalo_bot_dir, "data", "database", "rag_index.db")
            
            if os.path.exists(master_db1) and os.path.getsize(master_db1) > 100000:
                self.db_path = master_db1
            elif os.path.exists(master_db2) and os.path.getsize(master_db2) > 100000:
                self.db_path = master_db2
            else:
                self.db_path = master_db1

    def search_article(self, query: str) -> List[Dict[str, Any]]:
        """Performs exact structured article retrieval from indexed legal database."""
        if not os.path.exists(self.db_path):
            return []

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='legal_articles'")
        if not cur.fetchone():
            conn.close()
            return []

        # Parse Article Number (Điều X)
        dieu_match = re.search(r'Điều\s+(\d+)', query, re.IGNORECASE)
        dieu_num = int(dieu_match.group(1)) if dieu_match else 0

        # Extract document keywords
        doc_keywords = []
        known_kws = [
            "243", "257", "312", "128", "142", "64", "90", "57", "98", "188", "260", "31", "18",
            "phát triển đô thị", "ppp", "đất đai", "đầu tư công", "đấu thầu", "xây dựng", "giá"
        ]
        query_lower = query.lower()
        for kw in known_kws:
            if kw in query_lower:
                doc_keywords.append(kw)

        results = []
        if dieu_num > 0 and doc_keywords:
            sql = "SELECT source, doc_number, chuong, dieu_num, dieu_title, full_text FROM legal_articles WHERE dieu_num = ? AND source NOT LIKE '%.md' ORDER BY LENGTH(full_text) DESC"
            cur.execute(sql, (dieu_num,))
            rows = cur.fetchall()
            for src, doc_num, chuong, dnum, dtitle, ftext in rows:
                if any(kw in src.lower() or kw in doc_num.lower() for kw in doc_keywords):
                    results.append({
                        "source": src,
                        "doc_number": doc_num,
                        "dieu_num": dnum,
                        "dieu_title": dtitle,
                        "text": ftext,
                        "score": 100.0
                    })

        if not results and dieu_num > 0:
            cur.execute("SELECT source, doc_number, chuong, dieu_num, dieu_title, full_text FROM legal_articles WHERE dieu_num = ? AND source NOT LIKE '%.md' ORDER BY LENGTH(full_text) DESC LIMIT 5", (dieu_num,))
            rows = cur.fetchall()
            for src, doc_num, chuong, dnum, dtitle, ftext in rows:
                results.append({
                    "source": src,
                    "doc_number": doc_num,
                    "dieu_num": dnum,
                    "dieu_title": dtitle,
                    "text": ftext,
                    "score": 80.0
                })

        conn.close()

        # Attach Legal Cross-Reference Metadata if available
        if results and self.tvpl_crawler:
            cross_ref = self.tvpl_crawler.fetch_legal_cross_reference(query)
            if cross_ref:
                results[0]["cross_reference"] = cross_ref

        return results

    def tokenize(self, text: str) -> List[str]:
        words = [w.lower() for w in text.split()]
        clean_words = []
        for w in words:
            clean = "".join([c for c in w if c.isalnum()])
            if len(clean) > 1:
                clean_words.append(clean)
        return clean_words

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        # 1. Try Exact Article Structured Search
        article_results = self.search_article(query)
        if article_results:
            return article_results[:top_k]

        # 2. Hybrid BM25 Search Fallback
        if not os.path.exists(self.db_path):
            return []

        query_terms = self.tokenize(query)
        if not query_terms:
            return []

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT chunk_id, source, text, terms_json FROM chunks WHERE source NOT LIKE '%.md'")
        rows = cur.fetchall()
        conn.close()

        results = []
        for chunk_id, source, text, terms_json in rows:
            try:
                terms = json.loads(terms_json)
            except Exception:
                terms = []

            if not terms:
                continue

            score = 0
            text_lower = text.lower()
            for qt in query_terms:
                tf = terms.count(qt)
                if tf > 0:
                    score += (1 + math.log(tf)) * (10.0 if qt in text_lower else 1.0)

            if score > 0:
                results.append({
                    "chunk_id": chunk_id,
                    "source": source,
                    "text": text,
                    "score": round(score, 3)
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

if __name__ == "__main__":
    retriever = RAGRetriever()
    print(f"Using DB Path: {retriever.db_path}")

    print("\n=== TEST 1: Điều 65 Nghị định 243 ===")
    res1 = retriever.search("Điều 65 của Nghị định 243", top_k=1)
    if res1:
        print("Source:", res1[0]["source"])
        print("Title:", res1[0].get("dieu_title"))
        print("Text Snippet:\n", res1[0]["text"][:400])
        if "cross_reference" in res1[0]:
            print("\n" + res1[0]["cross_reference"])

    print("\n=== TEST 2: Điều 19 Luật phát triển đô thị ===")
    res2 = retriever.search("Điều 19 của Luật phát triển đô thị", top_k=1)
    if res2:
        print("Source:", res2[0]["source"])
        print("Title:", res2[0].get("dieu_title"))
        print("Text Snippet:\n", res2[0]["text"][:400])
