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

        # Load Full 82-Article Consolidated In-Place Database for Nghị định 243/2025/NĐ-CP
        db_json_path = os.path.join(current_dir, "nd243_full_consolidated_database.json")
        if os.path.exists(db_json_path):
            try:
                with open(db_json_path, "r", encoding="utf-8") as f:
                    self.nd243_consolidated_db = json.load(f)
            except Exception:
                self.nd243_consolidated_db = {}
        else:
            self.nd243_consolidated_db = {}

    def search_article(self, query: str) -> List[Dict[str, Any]]:
        """Performs dynamic multi-article structured retrieval from indexed legal database across ALL laws."""
        if not os.path.exists(self.db_path):
            return []

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='legal_articles'")
        if not cur.fetchone():
            conn.close()
            return []

        query_lower = query.lower()

        # 1. Parse Article Numbers (Điều X, Điều X-Y, Điều X và Y)
        dieu_nums = []
        # Pattern 1: Range "Điều 8 - 9" or "Điều 8 đến 9"
        range_match = re.search(r'Điều\s+(\d+)\s*(?:-|đến)\s*(\d+)', query, re.IGNORECASE)
        if range_match:
            start_num, end_num = int(range_match.group(1)), int(range_match.group(2))
            dieu_nums.extend(list(range(start_num, end_num + 1)))
        
        # Pattern 2: List "Điều 8, Điều 9" or "Điều 8 và 9" or single "Điều 9"
        dieu_matches = re.findall(r'Điều\s+(\d+)', query, re.IGNORECASE)
        for dm in dieu_matches:
            num = int(dm)
            if num not in dieu_nums:
                dieu_nums.append(num)

        # Special synthesis trigger: If user asks about "dự án nhóm A/B/C" without explicit article numbers
        if not dieu_nums:
            if any(k in query_lower for k in ["nhóm a", "dự án nhóm a", "quan trọng quốc gia"]):
                dieu_nums = [8, 9]
            elif any(k in query_lower for k in ["nhóm b", "dự án nhóm b"]):
                dieu_nums = [9, 10]
            elif any(k in query_lower for k in ["nhóm c", "dự án nhóm c"]):
                dieu_nums = [9, 11]

        # 2. Dynamic Document Tokenization (Extract numbers and legal domain terms from query)
        num_tokens = re.findall(r'\b\d{2,4}\b', query) # e.g. ["58", "2024", "243"]
        legal_terms = [
            "đầu tư công", "ppp", "đất đai", "đấu thầu", "xây dựng", "giá", "quy hoạch",
            "ngân sách", "quản lý nợ", "oda", "thuế", "tài sản công", "phát triển đô thị",
            "nhà ở", "kinh doanh bất động sản", "doanh nghiệp", "tín dụng", "môi trường"
        ]
        doc_keywords = [term for term in legal_terms if term in query_lower]
        if any(k in query_lower for k in ["nhóm a", "nhóm b", "nhóm c", "dự án nhóm"]):
            if "đầu tư công" not in doc_keywords:
                doc_keywords.append("đầu tư công")

        results = []
        if dieu_nums:
            placeholders = ",".join(["?"] * len(dieu_nums))
            sql = f"SELECT source, doc_number, chuong, dieu_num, dieu_title, full_text FROM legal_articles WHERE dieu_num IN ({placeholders}) AND source NOT LIKE '%.md'"
            cur.execute(sql, dieu_nums)
            rows = cur.fetchall()

            scored_rows = []
            for src, doc_num, chuong, dnum, dtitle, ftext in rows:
                score = 100.0 # Base score for matching requested article
                src_lower = src.lower()
                doc_num_lower = doc_num.lower()
                dtitle_lower = (dtitle or "").lower()
                ftext_full_lower = ftext.lower()

                # 1. Exact Article Title Match Boost (Super High Relevance)
                title_words = [w for w in ["nhóm a", "nhóm b", "nhóm c", "quan trọng quốc gia", "tiêu chí", "phân loại", "thẩm định", "hợp đồng bt", "hợp đồng bot"] if w in query_lower]
                for tw in title_words:
                    if tw in dtitle_lower:
                        score += 1500.0

                # 2. Dynamic scoring against extracted numbers in query (exact token/boundary match)
                for num_tok in num_tokens:
                    pattern = r'(?:^|[_\/\-\.\s])' + re.escape(num_tok) + r'(?:[_\/\-\.\s]|$)'
                    if re.search(pattern, src_lower) or re.search(pattern, doc_num_lower):
                        score += 800.0

                # 3. Dynamic domain keyword matching across full text & source
                for kw in doc_keywords:
                    if kw in src_lower or kw in doc_num_lower:
                        score += 500.0
                    elif kw in ftext_full_lower:
                        score += 200.0

                # 4. Investment Group A/B/C Priority Boost for Law 58/2024
                if any(k in query_lower for k in ["nhóm a", "nhóm b", "nhóm c", "dự án nhóm"]):
                    if "58" in src_lower or "58" in doc_num_lower or "đầu tư công" in src_lower:
                        score += 2000.0

                # 5. In-Place Statutory Consolidation for Yellow-Highlighted Amendments in NĐ 243/2025
                if str(dnum) in self.nd243_consolidated_db and ("243" in doc_num_lower or "243" in src_lower):
                    ftext = self.nd243_consolidated_db[str(dnum)]["full_consolidated_text"]
                    dtitle = self.nd243_consolidated_db[str(dnum)]["title"]
                    if "243" in query_lower:
                        score += 3000.0

                scored_rows.append((score, src, doc_num, chuong, dnum, dtitle, ftext))

            # Direct Injection: Guarantee 100% updated consolidated text for NĐ 243 if query references 243 or PPP
            if "243" in query_lower or "ppp" in query_lower:
                for dn in dieu_nums:
                    str_dn = str(dn)
                    if str_dn in self.nd243_consolidated_db:
                        c_info = self.nd243_consolidated_db[str_dn]
                        inject_score = 5000.0 if "243" in query_lower else 1800.0
                        scored_rows.append((
                            inject_score,
                            "Nghị định 243/2025/NĐ-CP (Văn bản hợp nhất cập nhật NĐ 377/2026/NĐ-CP)",
                            "243/2025/NĐ-CP",
                            "Nghị định 243",
                            dn,
                            c_info["title"],
                            c_info["full_consolidated_text"]
                        ))

            scored_rows.sort(key=lambda x: (x[0], int(x[4]) if isinstance(x[4], int) or str(x[4]).isdigit() else 0), reverse=True)

            seen_articles = set()
            for score, src, doc_num, chuong, dnum, dtitle, ftext in scored_rows:
                art_key = (str(doc_num).strip().lower(), str(dnum))
                if art_key in seen_articles:
                    continue
                seen_articles.add(art_key)
                results.append({
                    "source": src,
                    "doc_number": doc_num,
                    "dieu_num": dnum,
                    "dieu_title": dtitle,
                    "text": ftext,
                    "score": float(score)
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

    print("\n=== TEST LAW 58 ARTICLE 9 ===")
    res = retriever.search("Điều 9 Luật đầu tư công 58", top_k=1)
    if res:
        print("Source:", res[0]["source"])
        print("Title:", res[0].get("dieu_title"))
        print("Text Snippet:\n", res[0]["text"][:600])
        if "cross_reference" in res[0]:
            print("\n" + res[0]["cross_reference"])
