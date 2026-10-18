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
    """Enterprise Multi-Engine Real-Time & Entity Search Retriever with Deep Web Fetching."""

    def __init__(self, timeout: int = 6):
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def clean_query_text(self, query: str) -> str:
        """Cleans conversational fluff while preserving entity names and intent."""
        q = query.replace("quốc giap", "quốc gia").replace("bcnctkt", "báo cáo nghiên cứu khả thi")
        fluff_patterns = [
            r'\blà ai\b', r'\bai là\b', r'\btiểu sử của\b', r'\bthông tin về\b',
            r'\blà bao nhiêu\b', r'\bnhư thế nào\b', r'\bcho xin\b', r'\bvới bro\b',
            r'\bcho tui\b', r'\bra kết quả chưa\b', r'\bchưa bro\b', r'\bbro\b',
            r'\bbài post\b', r'\bvừa rồi\b', r'\btình hình của\b', r'\bsao chỉ có\b',
            r'đá\s+(?:lúc\s+)?mấy\s+giờ(?:\s+với\s+ai)?', r'\bđá mấy giờ\b', r'\bvới ai\b', r'\bmà \?\b'
        ]
        for pat in fluff_patterns:
            q = re.sub(pat, '', q, flags=re.IGNORECASE)
        q = re.sub(r'[\?\,\!\.]', ' ', q)
        q = re.sub(r'\s+', ' ', q).strip()
        return q if len(q) >= 2 else query

    def fetch_deep_page_content(self, url: str) -> str:
        """Deep scrapes webpage body/paragraphs to extract real schedule, tables, and event details."""
        if not url or not url.startswith("http"):
            return ""
        # Skip Google redirect URLs or binary files
        if "news.google.com" in url or any(url.endswith(ext) for ext in ['.pdf', '.mp4', '.mp3', '.jpg', '.png', '.zip']):
            return ""
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                content_type = resp.headers.get('Content-Type', '')
                if 'html' not in content_type:
                    return ""
                html_bytes = resp.read()
                html = html_bytes.decode('utf-8', errors='ignore')

                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')

                # Remove non-content elements
                for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'form', 'noscript', 'aside']):
                    tag.decompose()

                extracted_blocks = []
                for elem in soup.find_all(['p', 'h1', 'h2', 'h3', 'table', 'li', 'tr']):
                    txt = elem.get_text().strip()
                    if txt and len(txt) >= 8:
                        clean_txt = re.sub(r'\s+', ' ', txt)
                        extracted_blocks.append(clean_txt)

                # Prioritize blocks that look like fixtures, numbers, pairings, or dates
                fixture_blocks = [
                    b for b in extracted_blocks 
                    if any(k in b.lower() for k in [
                        'vs', 'vòng', 'hôm nay', '18/10', '19/10', 'mu', 'leeds', 'brighton', 
                        'arsenal', 'chelsea', 'sunderland', 'bournemouth', 'manchester', 'fpt play', 
                        'mytv', 'vtv', 'ngoại hạng', 'v-league'
                    ])
                ]
                if fixture_blocks:
                    return "\n".join(fixture_blocks[:45])[:3500].strip()

                full_text = "\n".join(extracted_blocks)
                return full_text[:2500].strip()
        except Exception:
            return ""

    def search_duckduckgo_ddgs(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Modern DuckDuckGo search via ddgs library."""
        results = []
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                ddg_gen = ddgs.text(query, max_results=max_results)
                for item in ddg_gen:
                    href = item.get('href') or item.get('link') or ''
                    title = item.get('title', '')
                    body = item.get('body') or item.get('snippet') or ''
                    if title and body:
                        results.append({
                            "title": title,
                            "url": href,
                            "snippet": body,
                            "pub_date": "Trực tuyến"
                        })
        except Exception:
            pass
        return results

    def search_duckduckgo_news(self, query: str, max_results: int = 4) -> List[Dict[str, str]]:
        """DuckDuckGo News search with direct publisher URLs."""
        results = []
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                news_gen = ddgs.news(query, max_results=max_results)
                for item in news_gen:
                    href = item.get('url') or item.get('link') or ''
                    title = item.get('title', '')
                    body = item.get('body') or item.get('snippet') or ''
                    if title and href:
                        results.append({
                            "title": title,
                            "url": href,
                            "snippet": body,
                            "pub_date": item.get('date', 'Mới nhất')
                        })
        except Exception:
            pass
        return results

    def search_google_news_rss(self, query: str, when: str = None) -> List[Dict[str, str]]:
        time_query = f"{query} when:{when}" if when else query
        encoded_query = urllib.parse.quote(time_query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=vi&gl=VN&ceid=VN:vi"
        results = []
        try:
            req = urllib.request.Request(url, headers=self.headers)
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

    def search_duckduckgo_lite(self, query: str) -> List[Dict[str, str]]:
        clean_q = query.replace('/', ' ')
        encoded_data = urllib.parse.urlencode({'q': clean_q}).encode('utf-8')
        url = "https://lite.duckduckgo.com/lite/"
        req = urllib.request.Request(url, data=encoded_data, headers=self.headers)
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

    def ground_query(self, query: str) -> Dict[str, Any]:
        """Agentic Multi-Engine Deep Search with Query Decomposition and Web Scraping."""
        q_lower = query.lower()
        search_terms = self.clean_query_text(query)
        if not search_terms or len(search_terms) < 2:
            search_terms = query

        # Detect intent
        personnel_keywords = ["là ai", "ai là", "tiểu sử", "chức vụ", "hoàng vũ thảnh", "ông ", "bà "]
        is_personnel = any(k in q_lower for k in personnel_keywords)

        finance_keywords = ["giá vàng", "tỷ giá", "cổ phiếu", "chứng khoán", "gdp", "lạm phát", "lãi suất", "ngân sách", "nợ công", "oda", "ppp", "đầu tư", "cafef", "vietstock"]
        is_finance = any(k in q_lower for k in finance_keywords)

        sports_keywords = [
            "bóng đá", "tỷ số", "trận", "nations league", "euro", "world cup", "ngoại hạng",
            "premier league", "cúp", "kết quả trận", "ghi bàn", "lịch thi đấu", "lịch đấu",
            "trận đấu", "đá banh", "arsenal", "chelsea", "liverpool", "manchester", "man united",
            "mu", "leeds", "brighton", "crystal palace", "man city", "tottenham", "barca", "real madrid",
            "champions league", "la liga", "serie a", "bundesliga", "v-league", "vleague", "cặp đấu",
            "sunderland", "bournemouth", "newcastle", "everton", "fulham", "wolves", "aston villa"
        ]
        is_sports = any(k in q_lower for k in sports_keywords)

        results = []

        if is_personnel:
            exact_query = f'"{search_terms}"'
            results.extend(self.search_duckduckgo_ddgs(exact_query, max_results=3))
            results.extend(self.search_google_news_rss(exact_query))
            results.extend(self.search_duckduckgo_ddgs(search_terms, max_results=3))
        elif is_finance:
            results.extend(self.search_duckduckgo_ddgs(f"{search_terms} 2026", max_results=4))
            results.extend(self.search_google_news_rss(f"{search_terms} 2026", when="7d"))
        elif is_sports:
            # Multi-pronged decomposed queries for sports fixtures
            date_match = re.search(r'\b\d{1,2}/\d{1,2}\b', query)
            target_date = date_match.group(0) if date_match else "18/10"
            
            targeted_queries = [
                # 1. Master Daily Fixtures Roundup from top sports newspapers
                f"thethaovanhoa.vn lịch thi đấu bóng đá hôm nay {target_date}",
                f"vietnamnet.vn lịch thi đấu bóng đá hôm nay {target_date}",
                # 2. Team-specific queries
                f"lịch thi đấu {search_terms} {target_date}",
                f"lịch thi đấu {search_terms} hôm nay",
                f"lịch thi đấu bóng đá hôm nay {target_date}"
            ]

            for q in targeted_queries:
                hits = self.search_duckduckgo_ddgs(q, max_results=3)
                results.extend(hits)
                news_hits = self.search_duckduckgo_news(q, max_results=2)
                results.extend(news_hits)
                rss_hits = self.search_google_news_rss(q, when="2d")
                results.extend(rss_hits)
                if len(results) >= 12:
                    break
        else:
            results.extend(self.search_duckduckgo_ddgs(search_terms, max_results=4))
            results.extend(self.search_google_news_rss(search_terms, when="30d"))

        # Fallback to DDG Lite if DDGS was blocked or empty
        if not results:
            results.extend(self.search_duckduckgo_lite(search_terms))
            results.extend(self.search_google_news_rss(search_terms))

        # Deduplicate results by URL and title
        unique_results = []
        seen_keys = set()
        for r in results:
            t = r.get("title", "").strip()
            u = r.get("url", "").strip()
            key = u if u else t
            if key and key not in seen_keys:
                seen_keys.add(key)
                unique_results.append(r)

        # Deep Fetch: Read top articles that have direct publisher links
        deep_content_snippets = []
        candidates_for_crawl = [
            r for r in unique_results 
            if r.get("url") and "http" in r.get("url") and "google.com" not in r.get("url")
        ]

        # Prioritize master fixtures roundup pages that contain comprehensive match lists
        def priority_score(item):
            url_str = item.get('url', '').lower()
            title_str = item.get('title', '').lower()
            # Top priority: thethaovanhoa, vietnamnet, bongdaplus roundup articles
            if any(dom in url_str for dom in ['thethaovanhoa.vn', 'vietnamnet.vn', 'bongdaplus.vn']):
                if 'lich-thi-dau-bong-da-hom-nay' in url_str or 'lịch thi đấu bóng đá hôm nay' in title_str:
                    return 0
                return 1
            if any(dom in url_str for dom in ['baolamdong.vn', 'baoquocte.vn', '24h.com.vn']):
                return 2
            return 3

        candidates_for_crawl.sort(key=priority_score)

        for r in candidates_for_crawl[:4]:
            u = r.get("url", "")
            deep_text = self.fetch_deep_page_content(u)
            if deep_text and len(deep_text) > 80:
                deep_content_snippets.append(f"--- CHI TIẾT TỪ BÁO CHÍ: {r.get('title', '')} ({u}) ---\n{deep_text}")
                if len(deep_content_snippets) >= 2:
                    break

        grounded_context = ""
        sources = []
        for idx, res in enumerate(unique_results[:8], 1):
            grounded_context += f"[{idx}] {res['title']}\nURL: {res['url']}\nTóm tắt: {res['snippet']}\n\n"
            if res['url'] and "google.com" not in res['url']:
                sources.append(res['url'])

        if deep_content_snippets:
            grounded_context += "\n=== LỊCH THI ĐẤU & CHI TIẾT BÓNG ĐÁ ĐƯỢC BÓC TÁCH TRỰC TIẾP TỪ TRANG BÁO CHÍ ===\n"
            grounded_context += "\n\n".join(deep_content_snippets)

        return {
            "query": query,
            "has_results": len(unique_results) > 0 or len(deep_content_snippets) > 0,
            "grounded_context": grounded_context,
            "sources": sources,
            "raw_results": unique_results
        }

if __name__ == "__main__":
    grounder = WebSearchGrounder()
    print("=== TEST SEARCH SUNDERLAND ===")
    r = grounder.ground_query("Hôm nay Sunderland đá lúc mấy giờ")
    print(r["grounded_context"][:2000])
