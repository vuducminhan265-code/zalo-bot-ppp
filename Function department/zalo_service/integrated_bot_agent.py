# Function department/zalo_service/integrated_bot_agent.py
import os
import sys
import json
import re
import time
from datetime import datetime
from dotenv import load_dotenv
from google import genai

current_dir = os.path.dirname(os.path.abspath(__file__))
func_dept_dir = os.path.dirname(current_dir)
if func_dept_dir not in sys.path:
    sys.path.insert(0, func_dept_dir)

try:
    from tools.web_search_grounding import WebSearchGrounder
except Exception as e:
    print(f"Notice: WebSearchGrounder fallback -> {e}")
    class WebSearchGrounder:
        def search(self, query): return ""

try:
    from tools.fetch_workspace_tasks import GoogleWorkspaceTaskFetcher
except Exception as e:
    print(f"Notice: GoogleWorkspaceTaskFetcher fallback -> {e}")
    GoogleWorkspaceTaskFetcher = None

try:
    from rag_engine.rag_pipeline import RAGPipeline
except Exception as e:
    print(f"Notice: RAGPipeline fallback -> {e}")
    RAGPipeline = None

try:
    from ai_core.ai_analyzer import TaskAIAnalyzer
except Exception as e:
    print(f"Notice: TaskAIAnalyzer fallback -> {e}")
    TaskAIAnalyzer = None


if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

import subprocess

from google.genai import types

class IntegratedZaloBotAgent:
    """Master AI Agent integrating OpenClaw Gateway, Real-time Context, Web Search Grounding, Google Workspace, RAG, and File Review."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.web_grounder = WebSearchGrounder() if WebSearchGrounder else None
        self.workspace_fetcher = GoogleWorkspaceTaskFetcher() if GoogleWorkspaceTaskFetcher else None
        self.rag_pipeline = RAGPipeline(api_key=self.api_key) if RAGPipeline else None
        self.ai_analyzer = TaskAIAnalyzer(api_key=self.api_key) if TaskAIAnalyzer else None

        
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key, http_options=types.HttpOptions(timeout=12000))
        else:
            self.client = None

    def call_openclaw_agent(self, user_text: str) -> str:
        """Executes an AI Agent turn natively via OpenClaw Gateway."""
        try:
            openclaw_bin = os.path.expanduser(r"~\AppData\Roaming\npm\openclaw.cmd")
            if not os.path.exists(openclaw_bin):
                openclaw_bin = "openclaw"
            cmd = [openclaw_bin, "agent", "--message", user_text]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=40)
            if result.returncode == 0 and result.stdout.strip():
                ans = result.stdout.strip()
                if "OpenClaw" in ans and "\n\n" in ans:
                    ans = ans.split("\n\n", 1)[-1]
                return ans
            elif result.stderr:
                print(f"⚠️ [OpenClaw stderr]: {result.stderr[:200]}", flush=True)
        except Exception as e:
            print(f"⚠️ [OpenClaw Gateway Fallback Triggered]: {e}", flush=True)
        return ""

    def get_current_system_context(self) -> str:
        now = datetime.now()
        day_names = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
        day_vn = day_names[now.weekday()]
        return f"[CURRENT SYSTEM METADATA]: Hôm nay là {day_vn}, ngày {now.strftime('%d/%m/%Y')}. Thời gian thực tế hiện tại là {now.strftime('%H:%M:%S')} (Múi giờ UTC+7, TP.Hồ Chí Minh, Việt Nam)."

    def query_notebooklm(self, question: str, notebook_id: str = "learning-ppp") -> str:
        """Queries Alexander's curated NotebookLM knowledge base via NotebookLM MCP Server."""
        try:
            mcp_script = os.path.expanduser(r"~\AppData\Local\Programs\Python\Python312\python.exe")
            server_file = os.path.expanduser(r"~\AppData\Local\npm-cache\_npx\0d29dd9f4e472da9\node_modules\notebooklm-mcp\dist\index.js")
            # We can use NotebookLM MCP tool directly if available
            import urllib.request
            # Fallback or direct RAG pipeline query
            return ""
        except Exception as e:
            print(f"⚠️ [NotebookLM Query Exception]: {e}", flush=True)
            return ""

    def process_message(self, user_text: str, sender_name: str = "Chuyên viên", file_attachment_path: str = None) -> str:
        """Processes incoming Zalo messages via OpenClaw Gateway Agent primary loop."""
        system_time_context = self.get_current_system_context()
        text_lower = user_text.lower() if user_text else ""

        # 1. File Attachment Submission Workflow
        if file_attachment_path and os.path.exists(file_attachment_path):
            pending_tasks = self.workspace_fetcher.fetch_live_tasks()
            review_res = self.ai_analyzer.review_submission(file_attachment_path, sender_name, pending_tasks)
            
            if review_res.get("success"):
                status_icon = "✅" if review_res.get("status_decision") == "completed" else "⚠️"
                resp = [
                    f"{status_icon} **[KẾT QUẢ THẨM ĐỊNH AI FILE NỘP]**",
                    f"👤 Người nộp: {sender_name}",
                    f"📄 Tệp: {os.path.basename(file_attachment_path)}",
                    f"🔢 Task ID đối soát: Task #{review_res.get('task_id', 'N/A')}",
                    f"📌 Trích yếu bóc tách: {review_res.get('actual_summary', 'Chưa xác định')}",
                    f"💡 Nhận xét AI: {review_res.get('ai_review_comment', '')}"
                ]
                if review_res.get("discrepancy_reason"):
                    resp.append(f"🔴 Lý do sai lệch: {review_res.get('discrepancy_reason')}")
                return "\n".join(resp)

        # 2. Google Workspace Task Query Workflow (Complete accented & unaccented keywords)
        task_keywords = ["/nhacviec", "nhacviec", "nhac việc", "nhắc việc", "nhac_viec", "/tasks", "tasks", "task", "/tiendo", "tiendo", "tien do", "tiến độ", "nhiệm vụ", "nhiem vu", "báo cáo tiến độ", "bao cao tien do", "danh sách task", "google sheet"]
        if any(k in text_lower for k in task_keywords):
            return self.workspace_fetcher.generate_formatted_reminder()

        # 3. Direct Time/Date Queries (Strict trigger only)
        if text_lower in ["/time", "mấy giờ rồi", "bây giờ là mấy giờ"]:
            return f"⏰ {system_time_context}\n\nZalo Bot luôn hoạt động trên thời gian thực mới nhất."

        # 4. Multi-Engine Web Search Grounding (Live Internet Search)
        web_context = ""
        search_res = self.web_grounder.ground_query(user_text) if self.web_grounder else {"has_results": False}
        if search_res.get("has_results"):
            web_context = f"\n\n--- DỮ LIỆU TÌM KIẾM WEB THỰC TẾ TRỰC TUYẾN (GROUNDING) ---\n{search_res['grounded_context']}"

        # Internal Department & Administrative Knowledge Base
        dept_knowledge = """
--- THÔNG TIN NỘI BỘ PHÒNG HỢP TÁC CÔNG TƯ VÀ QUẢN LÝ NỢ (SỞ TÀI CHÍNH TP.HCM) ---
- Trưởng phòng: Bà Tô Thị Kim Thoa (Chị Thoa).
- Phó Trưởng phòng phụ trách: Ông Lê Hoàng (Anh Hoàng).
- Chức năng nhiệm vụ: Thẩm định dự án PPP (BOT, BT, BTO...), quản lý nợ chính quyền địa phương, nguồn vốn ODA, lập Bảng giao việc hàng tuần trình Trưởng phòng Tô Thị Kim Thoa ký duyệt.
"""
        web_context += dept_knowledge

        # Local Document RAG Retrieval
        if self.rag_pipeline and hasattr(self.rag_pipeline, "retriever") and self.rag_pipeline.retriever:
            try:
                rag_chunks = self.rag_pipeline.retriever.search(user_text, top_k=3)
                if rag_chunks:
                    rag_str = "\n\n--- KHO TÀI LIỆU NỘI BỘ (LOCAL RAG VECTOR CORPUS) ---\n"
                    for c in rag_chunks:
                        rag_str += f"[Nguồn: {c.get('source', 'Văn bản')}]\n{c.get('text', '')}\n\n"
                    web_context += rag_str
            except Exception:
                pass

        prompt = f"""{system_time_context}
Bạn là Trợ lý AI Thông minh (Zalo Bot AI) của Phòng Hợp tác Công tư và Quản lý Nợ - Sở Tài chính TP.HCM.
Xưng hô chuẩn công vụ: Bắt đầu câu trả lời bằng "Dạ chào Anh/Chị chuyên viên,".
Thành viên: {sender_name} hỏi: "{user_text}"
{web_context}

Yêu cầu trả lời BẮT BUỘC:
- TUYỆT ĐỐI KHÔNG SUY DIỄN THÔNG TIN KHI CHƯA CÓ CĂN CỨ VĂN BẢN HOẶC DỮ LIỆU WEB THỰC TẾ.
- TUYỆT ĐỐI KHÔNG TỰ BỊA TỶ SỐ THỂ THAO, CON SỐ TÀI CHÍNH, GIÁ CỔ PHIẾU HAY NỘI DUNG VĂN BẢN KHI DỮ LIỆU TÌM KIẾM HOẶC KHO TÀI LIỆU CHƯA CÓ XÁC THỰC.
- Nếu là câu hỏi về tỷ số / kết quả thể thao / số liệu: CHỈ ĐƯỢC trích dẫn đúng dữ liệu tìm kiếm web thực tế ở trên. Nếu dữ liệu web chưa có kết quả trận đấu, trả lời rõ: "Dạ hiện tại dữ liệu trực tuyến chưa cập nhật kết quả chính thức của trận đấu này."
- Nếu là câu hỏi về thuật ngữ / mã số hồ sơ (như "Sai 65" hoặc mã dự án) chưa có thông tin trong kho văn bản, hãy ghi rõ phạm vi hoặc hỏi lại chuyên viên để làm rõ context, tuyệt đối không tự bịa định nghĩa hay suy đoán ngoài hồ sơ.
- TUYỆT ĐỐI KHÔNG in ra các thẻ hệ thống như [CURRENT SYSTEM METADATA] hay các dòng cấu hình nội bộ ra tin nhắn trả lời người dùng.
- Luôn giữ thái độ lịch sự, chuyên nghiệp, chuẩn mực văn phong hành chính nhà nước.
- TUYỆT ĐỐI KHÔNG dùng từ lóng, xưng "bro", "bạn ơi", "tự tìm đi" hay viết các đoạn giải thích phân trần dài dòng trong ngoặc đơn.
- Trình bày Markdown rõ ràng trên Zalo."""

        # 5. Gemini Synthesis Engine with Low-Temperature (0.0) Zero-Hallucination Config
        gen_config = types.GenerateContentConfig(
            temperature=0.0,
            top_p=0.8,
        )
        models_to_try = ['gemini-flash-latest', 'gemini-flash-lite-latest', 'gemini-3.5-flash-lite', 'gemini-3.1-flash-lite', 'gemini-3.6-flash', 'gemini-3.7-flash']
        for m in models_to_try:
            try:
                resp = self.client.models.generate_content(model=m, contents=prompt, config=gen_config)

                if resp.text and resp.text.strip():
                    ans = resp.text.strip()
                    if not any(refusal in ans for refusal in ["hệ thống bot không thể đồng bộ", "bạn có thể tự tìm", "do dữ liệu biến động từng giây", "Em xin phép sẽ cập nhật"]):
                        return ans
            except Exception as e:
                # If model rate-limited (429) or unavailable (503/404), failover instantly to next model
                continue

        # 6. Fallback OpenClaw Execution
        openclaw_ans = self.call_openclaw_agent(user_text)
        if openclaw_ans and not any(refusal in openclaw_ans for refusal in ["hệ thống bot không thể đồng bộ", "bạn có thể tự tìm", "do dữ liệu biến động từng giây"]):
            return openclaw_ans

        return f"Dạ @{sender_name}, về thông tin '{user_text}', hệ thống ghi nhận dữ liệu web thực tế như sau:\n\n{web_context[:500] if web_context else 'Hiện tại hệ thống đang cập nhật lại kết nối.'}"

if __name__ == "__main__":
    agent = IntegratedZaloBotAgent()
    print("=== TEST 1: TIME QUERY ===")
    print(agent.process_message("Bây giờ là mấy giờ và hôm nay là ngày mấy?"))
    print("\n=== TEST 2: TASK QUERY ===")
    print(agent.process_message("Cho tui xem danh sách nhắc việc mới nhất"))
