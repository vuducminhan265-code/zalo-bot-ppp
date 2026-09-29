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
    """Multi-engine search retriever for live web grounding."""

    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def search_duckduckgo_json(self, query: str) -> List[Dict[str, str]]:
        encoded_query = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1&skip_disambig=1"
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        results = []
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get("AbstractText"):
                    results.append({
                        "title": data.get("Heading", "Kết quả tổng hợp"),
                        "url": data.get("AbstractURL", ""),
                        "snippet": data.get("AbstractText")
                    })
                for topic in data.get("RelatedTopics", [])[:3]:
                    if isinstance(topic, dict) and "Text" in topic:
                        results.append({
                            "title": topic.get("Text", "")[:60],
                            "url": topic.get("FirstURL", ""),
                            "snippet": topic.get("Text", "")
                        })
        except Exception as e:
            pass
        return results

    def search_google_news_rss(self, query: str) -> List[Dict[str, str]]:
        encoded_query = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=vi&gl=VN&ceid=VN:vi"
        headers = {'User-Agent': 'Mozilla/5.0'}
        results = []
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                xml_data = resp.read().decode('utf-8', errors='ignore')
                import xml.etree.ElementTree as ET
                root = ET.fromstring(xml_data)
                items = root.findall('.//item')[:4]
                for item in items:
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    pub_elem = item.find('pubDate')
                    if title_elem is not None and title_elem.text:
                        results.append({
                            "title": f"[Google News] {title_elem.text}",
                            "url": link_elem.text if link_elem is not None else "",
                            "snippet": f"Tin tức trực tuyến: {title_elem.text} (Thời gian: {pub_elem.text if pub_elem is not None else 'mới nhất'})"
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
                        "snippet": clean_snippet
                    })
        except Exception:
            pass
        return results

    def search_duckduckgo_lite(self, query: str) -> List[Dict[str, str]]:
        clean_q = query.replace('/', ' ')
        encoded_data = urllib.parse.urlencode({'q': clean_q}).encode('utf-8')
        url = "https://lite.duckduckgo.com/lite/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        req = urllib.request.Request(url, data=encoded_data, headers=headers)
        results = []
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                snippets = re.findall(r'result-snippet[^>]*>(.*?)</td>', html, re.DOTALL)
                titles = re.findall(r'result-link[^>]*>(.*?)</a>', html, re.DOTALL)
                urls = re.findall(r'href=["\'](https?://[^"\']+)["\']', html)
                for idx in range(min(len(snippets), 4)):
                    clean_snip = re.sub(r'<[^>]+>', '', snippets[idx]).strip()
                    clean_title = re.sub(r'<[^>]+>', '', titles[idx]).strip() if idx < len(titles) else "Kết quả tìm kiếm"
                    res_url = urls[idx] if idx < len(urls) else ""
                    if clean_snip:
                        results.append({
                            "title": clean_title,
                            "url": res_url,
                            "snippet": clean_snip
                        })
        except Exception:
            pass
        return results

    def ground_query(self, query: str) -> Dict[str, Any]:
        """Grounds query across multiple search engines with automatic stock & legal query enrichment."""
        q_lower = query.lower()
        stock_keywords = ["cổ phiếu", "giá cổ phiếu", "mã cổ phiếu", "chứng khoán", "hose", "hnx"]
        legal_keywords = ["điều", "nghị định", "luật", "thông tư", "nghị quyết", "quyết định", "243/2025", "luật ppp", "văn bản"]
        sports_keywords = ["tỷ số", "bóng đá", "kết quả", "trận", "nations league", "euro", "cúp", "ngoại hạng", "champions league"]
        is_specialized = False

        # Clean conversational filler noise (keep temporal anchors like 'hôm nay')
        clean_q = re.sub(r'(\blà bao nhiêu\b|\bnhư thế nào\b|\bcho xin\b|\bvới bro\b|\bcho tui\b|\blà ai\b|\bbao nhiêu\b|\bcủa\b)', '', query, flags=re.IGNORECASE)
        clean_q = re.sub(r'\s+', ' ', clean_q).strip()

        if any(k in q_lower for k in legal_keywords):
            is_specialized = True
            legal_q = clean_q.replace('/', ' ')
            results = self.search_google_news_rss(f"{legal_q} thuvienphapluat")
            ddg_res = self.search_duckduckgo_lite(f"{legal_q} site:thuvienphapluat.vn")
            if ddg_res:
                results.extend(ddg_res)
            if not results:
                results = self.search_duckduckgo_lite(f"{legal_q} chinhphu.vn")
        elif any(k in q_lower for k in stock_keywords):
            is_specialized = True
            rss_q = clean_q if "giá cổ phiếu" in clean_q.lower() else f"giá cổ phiếu {clean_q}"
            results = self.search_google_news_rss(rss_q)
            ddg_q = f"{clean_q} CafeF Vietstock" if "giá cổ phiếu" in clean_q.lower() else f"giá cổ phiếu {clean_q} CafeF Vietstock"
            ddg_res = self.search_duckduckgo_lite(ddg_q)
            if ddg_res:
                results.extend(ddg_res)
        elif any(k in q_lower for k in sports_keywords) or any(k in q_lower for k in ["inter miami", "messi", "ronaldo", "man utd", "real madrid", "barcelona"]):
            is_specialized = True
            results = self.search_google_news_rss(clean_q)
            ddg_res = self.search_duckduckgo_lite(f"{clean_q} match result score")
            if ddg_res:
                results.extend(ddg_res)
            if not results:
                results = self.search_duckduckgo_lite(f"{clean_q} tỷ số kết quả")
        else:
            results = self.search_google_news_rss(clean_q)
            ddg_res = self.search_duckduckgo_lite(clean_q)
            if ddg_res:
                results.extend(ddg_res)

        if not results:
            results = self.search_duckduckgo_json(clean_q)
        if not results and not is_specialized:
            results = self.search_wikipedia_vi(clean_q)

        grounded_context = ""
        sources = []

        for idx, res in enumerate(results, 1):
            grounded_context += f"[{idx}] {res['title']}\nURL: {res['url']}\nTóm tắt: {res['snippet']}\n\n"
            if res['url']:
                sources.append(res['url'])

        return {
            "query": query,
            "has_results": len(results) > 0,
            "grounded_context": grounded_context,
            "sources": sources,
            "raw_results": results
        }

if __name__ == "__main__":
    grounder = WebSearchGrounder()
    res = grounder.ground_query("Sở Tài Chính Thành phố Hồ Chí Minh PPP")
    print("=== WEB SEARCH GROUNDING RESULT ===")
    print(res["grounded_context"])
