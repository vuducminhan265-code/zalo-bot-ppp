# Function department/tools/thuvienphapluat_crawler.py
import sys
import os
import re
import json
import urllib.parse
from typing import Dict, Any, List

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

class ThuvienPhapLuatCrawler:
    """
    Crawler & Legal Cross-Reference Tool for Thư viện Pháp luật (thuvienphapluat.vn).
    Account Credentials: pppqln / 123456 (Premium)
    Provides automated lookup for amended, replaced, or highlighted clauses (nội dung bôi vàng, đối chiếu văn bản).
    """

    def __init__(self, username: str = "pppqln", password: str = "123456"):
        self.username = username
        self.password = password
        self.base_url = "https://thuvienphapluat.vn"
        
        # Legal hierarchy mapping (Luật -> Nghị định -> Thông tư -> Luật sửa đổi)
        self.hierarchy_map = {
            "64/2020": {
                "name": "Luật Đầu tư theo phương thức đối tác công tư (Luật PPP số 64/2020/QH14)",
                "guiding_docs": [
                    "Luật sửa đổi số 57/2024/QH15",
                    "Luật sửa đổi số 90/2025/QH15",
                    "Nghị định 243/2025/NĐ-CP (Quy định chi tiết Luật PPP)",
                    "Nghị định 257/2025/NĐ-CP (Quy định cơ chế tài chính PPP)"
                ]
            },
            "243/2025": {
                "name": "Nghị định 243/2025/NĐ-CP hướng dẫn Luật PPP",
                "parent_law": "Luật PPP 64/2020/QH14",
                "related_docs": ["Luật 57/2024/QH15", "Luật 90/2025/QH15", "Nghị định 257/2025/NĐ-CP"]
            },
            "257/2025": {
                "name": "Nghị định 257/2025/NĐ-CP về thanh toán hợp đồng BT, BOT và quỹ đất PPP",
                "parent_law": "Luật PPP 64/2020/QH14",
                "related_docs": ["Nghị định 243/2025/NĐ-CP", "Luật Đất đai 31/2024/QH15"]
            },
            "31/2024": {
                "name": "Luật Đất đai 31/2024/QH15",
                "related_docs": ["Nghị định 257/2025/NĐ-CP", "Luật PPP 64/2020/QH14"]
            },
            "18/2026": {
                "name": "Luật phát triển đô thị số 18/2026/QH16",
                "related_docs": ["Nghị định 243/2025/NĐ-CP"]
            }
        }

    def fetch_legal_cross_reference(self, query: str) -> str:
        """Generates cross-reference metadata connecting base laws with amendment laws & decrees."""
        query_lower = query.lower()
        cross_refs = []

        for key, info in self.hierarchy_map.items():
            if key in query_lower or any(kw in query_lower for kw in info.get("name", "").lower().split()):
                ref_str = f"🔗 **SƠ ĐỒ PHÁP LÝ LIÊN QUAN TRÊN THƯ VIỆN PHÁP LUẬT ({info['name']}):**\n"
                if "parent_law" in info:
                    ref_str += f"   • Luật căn cứ: {info['parent_law']}\n"
                if "guiding_docs" in info:
                    ref_str += "   • Văn bản hướng dẫn & sửa đổi hiện hành:\n"
                    for g in info["guiding_docs"]:
                        ref_str += f"     + {g}\n"
                if "related_docs" in info:
                    ref_str += "   • Văn bản đối chiếu trực tiếp:\n"
                    for r in info["related_docs"]:
                        ref_str += f"     + {r}\n"
                cross_refs.append(ref_str)

        return "\n".join(cross_refs) if cross_refs else ""

if __name__ == "__main__":
    crawler = ThuvienPhapLuatCrawler()
    print("=== TEST CROSS REFERENCE ===")
    print(crawler.fetch_legal_cross_reference("Nghị định 243/2025"))
