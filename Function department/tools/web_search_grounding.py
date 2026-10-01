# Function department/tools/web_search_grounding.py
import os
import sys
import json
import urllib.parse
import urllib.request
import re
from typing import List, Dict, Any

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

class WebSearchGrounder:
    """Enterprise Multi-Engine Real-Time & Entity Search Retriever."""

    def __init__(self, timeout: int = 12):
        self.timeout = timeout

    def clean_query_text(self, query: str) -> str:
        """Cleans conversational fluff while preserving entity names and intent."""
        q = query.replace("quốc giap", "quốc gia").replace("bcnctkt", "báo cáo nghiên cứu khả thi")
        fluff_patterns = [
            r'\blà ai\b', r'\bai là\b', r'\btiểu sử của\b', r'\bthông tin về\b',
            r'\blà bao nhiêu\b', r'\bnhư thế nào\b', r'\bcho xin\b', r'\bvới bro\b',
            r'\bcho tui\b', r'\bra kết quả chưa\b', r'\bchưa bro\b', r'\bbro\b',
            r'\bbài post\b', r'\bvừa rồi\b', r'\btình hình của\b'
        ]
        for pat in fluff_patterns:
            q = re.sub(pat, '', q, flags=re.IGNORECASE)
        q = re.sub(r'\s+', ' ', q).strip()
        return q if len(q) >= 2 else query

    def search_google_news_rss(self, query: str, when: str = None) -> List[Dict[str, str]]:
        time_query = f"{query} when:{when}" if when else query
        encoded_query = urllib.parse.quote(time_query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=vi&gl=VN&ceid=VN:vi"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        results = []
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                xml_data = resp.read().decode('utf-8', errors='ignore')
                import xml.etree.ElementTree as ET
                root = ET.fromstring(xml_data)
                items = root.findall('.//item')[:6]
                for item in items:
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    pub_elem = item.find('pubDate')
                    if title_elem is not None and title_elem.text:
                        pub_str = pub_elem.text if pub_elem is not None else ""
                        results.append({
                            "title": f"[Tin tức] {title_elem.text}",
                            "url": link_elem.text if link_elem is not None else "",
                            "snippet": f"{title_elem.text} (Thời gian: {pub_str if pub_str else 'Báo chí'})",
                            "pub_date": pub_str
                        })
        except Exception:
            pass
        return results

    def search_duckduckgo_html(self, query: str) -> List[Dict[str, str]]:
        clean_q = query.replace('/', ' ')
        encoded_data = urllib.parse.urlencode({'q': clean_q}).encode('utf-8')
        url = "https://html.duckduckgo.com/html/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        req = urllib.request.Request(url, data=encoded_data, headers=headers)
        results = []
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                snippets = re.findall(r'<a class="result__snippet[^"]*"[^>]*>(.*?)</a>', html, re.DOTALL)
                titles = re.findall(r'<a class="result__url[^"]*"[^>]*>(.*?)</a>', html, re.DOTALL)
                urls = re.findall(r'href=["\'](https?://[^"\']+)["\']', html)
                for idx in range(min(len(snippets), 6)):
                    clean_snip = re.sub(r'<[^>]+>', '', snippets[idx]).strip()
                    clean_title = re.sub(r'<[^>]+>', '', titles[idx]).strip() if idx < len(titles) else "Bản tin Web"
                    res_url = urls[idx] if idx < len(urls) else ""
                    if clean_snip:
                        results.append({
                            "title": clean_title,
                            "url": res_url,
                            "snippet": clean_snip,
                            "pub_date": "Trực tuyến"
                        })
        except Exception:
            pass
        return results

    def search_duckduckgo_lite(self, query: str) -> List[Dict[str, str]]:
        clean_q = query.replace('/', ' ')
        encoded_data = urllib.parse.urlencode({'q': clean_q}).encode('utf-8')
        url = "https://lite.duckduckgo.com/lite/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        req = urllib.request.Request(url, data=encoded_data, headers=headers)
        results = []
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                snippets = re.findall(r'result-snippet[^>]*>(.*?)</td>', html, re.DOTALL)
                titles = re.findall(r'result-link[^>]*>(.*?)</a>', html, re.DOTALL)
                urls = re.findall(r'href=["\'](https?://[^"\']+)["\']', html)
                for idx in range(min(len(snippets), 6)):
                    clean_snip = re.sub(r'<[^>]+>', '', snippets[idx]).strip()
                    clean_title = re.sub(r'<[^>]+>', '', titles[idx]).strip() if idx < len(titles) else "Trích xuất Web"
                    res_url = urls[idx] if idx < len(urls) else ""
                    if clean_snip:
                        results.append({
                            "title": clean_title,
                            "url": res_url,
                            "snippet": clean_snip,
                            "pub_date": "Trực tuyến"
                        })
        except Exception:
            pass
        return results

    def search_wikipedia_vi(self, query: str) -> List[Dict[str, str]]:
        encoded_query = urllib.parse.quote(query)
        url = f"https://vi.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded_query}&format=json"
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        results = []
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                search_hits = data.get("query", {}).get("search", [])[:3]
                for hit in search_hits:
                    clean_snippet = re.sub(r'<[^>]+>', '', hit.get("snippet", "")).strip()
                    title = hit.get("title", "")
                    page_url = f"https://vi.wikipedia.org/wiki/{urllib.parse.quote(title)}"
                    results.append({
                        "title": f"[Wikipedia] {title}",
                        "url": page_url,
                        "snippet": clean_snippet,
                        "pub_date": "Bách khoa toàn thư"
                    })
        except Exception:
            pass
        return results

    def ground_query(self, query: str) -> Dict[str, Any]:
        """Smart Query Grounding with intent-based temporal routing."""
        q_lower = query.lower()
        search_terms = self.clean_query_text(query)
        if not search_terms or len(search_terms) < 2:
            search_terms = query

        # Detect intent
        personnel_keywords = ["là ai", "ai là", "tiểu sử", "chức vụ", "hoàng vũ thảnh", "ông ", "bà "]
        is_personnel = any(k in q_lower for k in personnel_keywords)

        finance_keywords = ["giá vàng", "tỷ giá", "cổ phiếu", "chứng khoán", "gdp", "lạm phát", "lãi suất", "ngân sách", "nợ công", "oda", "ppp", "đầu tư", "vic", "hpg", "vhm", "cafef", "vietstock"]
        is_finance = any(k in q_lower for k in finance_keywords)

        sports_keywords = ["bóng đá", "tỷ số", "trận", "nations league", "euro", "world cup", "ngoại hạng", "cúp", "kết quả trận", "séc", "anh", "tây ban nha", "croatia", "ghi bàn"]
        is_sports = any(k in q_lower for k in sports_keywords)

        results = []

        if is_personnel:
            # Personnel / Entity Intent: Search exact entity with quotes to prevent fuzzy name mixing
            exact_query = f'"{search_terms}"'
            results.extend(self.search_duckduckgo_html(exact_query))
            results.extend(self.search_google_news_rss(exact_query))
            results.extend(self.search_duckduckgo_html(search_terms))
            results.extend(self.search_duckduckgo_lite(search_terms))
            results.extend(self.search_google_news_rss(search_terms))
            results.extend(self.search_wikipedia_vi(search_terms))
        elif is_finance:
            # Financial Intent: Time anchored 7d/30d
            results.extend(self.search_duckduckgo_html(f"{search_terms} 2026"))
            results.extend(self.search_google_news_rss(f"{search_terms} 2026", when="7d"))
            results.extend(self.search_duckduckgo_lite(f"{search_terms} mới nhất 2026"))
        elif is_sports:
            # Sports Intent: Clean entity search first, then news
            results.extend(self.search_duckduckgo_html(search_terms))
            results.extend(self.search_google_news_rss(f"{search_terms} 2026", when="7d"))
            results.extend(self.search_duckduckgo_html(f"{search_terms} 2026"))
            results.extend(self.search_duckduckgo_lite(search_terms))
        else:
            # General Intent: Combine general DDG + Google News
            results.extend(self.search_duckduckgo_html(search_terms))
            results.extend(self.search_duckduckgo_lite(search_terms))
            results.extend(self.search_google_news_rss(search_terms, when="30d"))

        # Fallback if empty
        if not results:
            results.extend(self.search_duckduckgo_lite(search_terms))
            results.extend(self.search_google_news_rss(search_terms))

        # Deduplicate results by title
        unique_results = []
        seen_titles = set()
        for r in results:
            t = r.get("title", "").strip()
            if t and t not in seen_titles:
                seen_titles.add(t)
                unique_results.append(r)

        grounded_context = ""
        sources = []
        for idx, res in enumerate(unique_results[:6], 1):
            grounded_context += f"[{idx}] {res['title']}\nURL: {res['url']}\nTóm tắt: {res['snippet']}\n\n"
            if res['url']:
                sources.append(res['url'])

        return {
            "query": query,
            "has_results": len(unique_results) > 0,
            "grounded_context": grounded_context,
            "sources": sources,
            "raw_results": unique_results
        }

if __name__ == "__main__":
    grounder = WebSearchGrounder()
    print("=== TEST PERSONNEL: Hoàng Vũ Thảnh ===")
    r = grounder.ground_query("Hoàng Vũ Thảnh là ai")
    print(r["grounded_context"])
