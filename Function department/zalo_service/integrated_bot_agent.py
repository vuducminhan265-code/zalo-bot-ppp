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
    from tools.task_manager import TaskManager
except Exception as e:
    print(f"Notice: TaskManager fallback -> {e}")
    TaskManager = None

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
        self.task_manager = TaskManager() if TaskManager else None
        self.rag_pipeline = RAGPipeline(api_key=self.api_key) if RAGPipeline else None
        self.ai_analyzer = TaskAIAnalyzer(api_key=self.api_key) if TaskAIAnalyzer else None

        
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key, http_options=types.HttpOptions(timeout=12000))
        else:
            self.client = None

    def call_openclaw_agent(self, user_text: str) -> str:
        """Fallback Agent turn using standard Gemini model when primary attempt fails."""
        try:
            if not self.client:
                return ""
            prompt = f"{self.get_current_system_context()}\nTrả lời ngắn gọn, chuẩn công vụ, tuyệt đối không suy diễn:\n{user_text}"
            resp = self.client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.0)
            )
            if resp.text and resp.text.strip():
                return resp.text.strip()
        except Exception as e:
            print(f"⚠️ [Cloud Fallback Exception]: {e}", flush=True)
        return ""

    def get_current_system_context(self) -> str:
        from datetime import datetime, timezone, timedelta
        vn_tz = timezone(timedelta(hours=7))
        now = datetime.now(vn_tz)
        day_names = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
        day_vn = day_names[now.weekday()]
        return f"Hôm nay là {day_vn}, ngày {now.strftime('%d/%m/%Y')}. Thời gian thực tế hiện tại là {now.strftime('%H:%M:%S')} (Múi giờ UTC+7, TP.Hồ Chí Minh, Việt Nam)."

    def query_notebooklm(self, question: str, notebook_id: str = "learning-ppp") -> str:
        """Cloud-native knowledge base query fallback."""
        if self.rag_pipeline and hasattr(self.rag_pipeline, "retriever") and self.rag_pipeline.retriever:
            try:
                rag_chunks = self.rag_pipeline.retriever.search(question, top_k=3)
                if rag_chunks:
                    return "\n".join([c.get('text', '') for c in rag_chunks])
            except Exception as e:
                print(f"⚠️ [RAG Query Exception]: {e}", flush=True)
        return ""

    def process_message(self, user_text: str, sender_name: str = "Chuyên viên", file_attachment_path: str = None, chat_history: list = None) -> str:
        """Processes incoming Zalo messages via 100% Cloud-Native Agent pipeline with stateful context."""
        system_time_context = self.get_current_system_context()
        text_lower = user_text.lower() if user_text else ""

        # 1. File Attachment Submission Workflow with Automatic Google Sheets Sync
        if file_attachment_path and os.path.exists(file_attachment_path):
            if self.workspace_fetcher and self.ai_analyzer:
                pending_tasks = self.workspace_fetcher.fetch_live_tasks()
                review_res = self.ai_analyzer.review_submission(file_attachment_path, sender_name, pending_tasks)
                
                if review_res.get("success"):
                    status_decision = review_res.get("status_decision")
                    task_id = str(review_res.get("task_id", "")).strip()
                    actual_summary = review_res.get("actual_summary", "Chưa xác định")
                    doc_number = review_res.get("document_number", "")
                    doc_date = review_res.get("document_date", "")
                    ai_comment = review_res.get("ai_review_comment", "")
                    discrepancy = review_res.get("discrepancy_reason")
                    file_name = os.path.basename(file_attachment_path)

                    # Tự động cập nhật Google Sheets
                    sheets_status = "Đã hoàn thành" if status_decision == "completed" else "Đang sửa lại"
                    sheets_updated = False
                    if self.task_manager and task_id:
                        try:
                            sheets_updated = self.task_manager.update_task_status_and_metadata(
                                task_id=task_id,
                                status=sheets_status,
                                summary=ai_comment if status_decision == "completed" else f"CẢNH BÁO SAI LỆCH: {discrepancy}",
                                file_name=file_name,
                                doc_number=doc_number,
                                doc_date=doc_date,
                                actual_summary=actual_summary
                            )
                        except Exception as e:
                            print(f"⚠️ Lỗi update Google Sheets: {e}", flush=True)

                        sheets_status_text = 'ĐÃ TỰ ĐỘNG CẬP NHẬT TRẠNG THÁI "ĐÃ HOÀN THÀNH" 🟢' if sheets_updated else 'Đã thẩm định hoàn thành 🟢'
                        resp = [
                            "✅ **[KẾT QUẢ THẨM ĐỊNH & NGHIỆM THU TỰ ĐỘNG - PHÒNG PPP]**",
                            f"👤 Người nộp: **{sender_name}**",
                            f"📄 Tệp văn bản: `{file_name}`",
                            f"🔢 Đối soát: **Khớp chuẩn Task #{task_id}**",
                            f"📌 Trích yếu bóc tách: {actual_summary}",
                            f"📑 Thể thức: Số {doc_number if doc_number else 'Văn bản nội bộ'} | Ngày {doc_date if doc_date else 'Hiện hành'}",
                            f"💡 Đánh giá của AI: {ai_comment}",
                            "────────────────────────────",
                            f"📊 **Bảng giao việc Google Sheets:** {sheets_status_text}"
                        ]
                        return "\n".join(resp)
                    else:
                        sheets_warning_text = 'ĐÃ GHI NHẬN CẢNH BÁO "ĐANG SỬA LẠI" 🔴' if sheets_updated else 'Trạng thái: Đang sửa lại 🔴'
                        resp = [
                            "⚠️ **[CẢNH BÁO THẨM ĐỊNH AI: TỆP NỘP CHƯA KHỚP NỘI DUNG]**",
                            f"👤 Người nộp: **{sender_name}**",
                            f"📄 Tệp văn bản: `{file_name}`",
                            f"🔢 Đối soát: **Task #{task_id if task_id else 'Không xác định'}**",
                            f"📌 Trích yếu thực tế trong file: {actual_summary}",
                            f"🔴 **Lý do sai lệch:** {discrepancy if discrepancy else 'Nội dung hoặc trích yếu văn bản chưa khớp với sản phẩm yêu cầu của nhiệm vụ'}",
                            f"💡 Nhận xét AI: {ai_comment}",
                            "────────────────────────────",
                            f"📊 **Bảng giao việc Google Sheets:** {sheets_warning_text}",
                            "👉 Đề nghị chuyên viên rà soát lại văn bản trước khi nộp lại hoặc báo cáo Lãnh đạo nếu có chỉ đạo thay đổi."
                        ]
                        return "\n".join(resp)

        # 2. Google Workspace Task Query Workflow (Strict template triggers)
        task_template_triggers = ["/nhacviec", "nhacviec", "nhac việc", "/tasks", "/tiendo", "danh sách task", "báo cáo tiến độ", "bao cao tien do"]
        if any(k in text_lower for k in task_template_triggers):
            if self.workspace_fetcher:
                return self.workspace_fetcher.generate_formatted_reminder()

        # 3. Direct Time/Date Queries (Strict trigger only)
        if text_lower in ["/time", "mấy giờ rồi", "bây giờ là mấy giờ"]:
            return f"⏰ {system_time_context}\n\nZalo Bot luôn hoạt động trên thời gian thực mới nhất."

        # 4. Context Grounding Assembly
        web_context = ""

        # A. Inject Live Google Workspace Tasks Context ONLY when query explicitly asks about work tasks/personnel
        task_query_keywords = ["task", "nhiệm vụ", "giao việc", "tiến độ", "nhắc việc", "hận", "hòa", "thoa", "hoàng", "chuyên viên", "deadline", "quá hạn"]
        if self.workspace_fetcher and any(k in text_lower for k in task_query_keywords):
            try:
                live_tasks_summary = self.workspace_fetcher.generate_formatted_reminder()
                web_context += f"\n\n--- DỮ LIỆU BẢNG GIAO VIỆC GOOGLE WORKSPACE (LIVE TASKS DATA) ---\n{live_tasks_summary}\n"
            except Exception as e:
                print(f"Notice: Live tasks injection error -> {e}")

        # B. Multi-Engine Web Search Grounding (Live Internet Search)
        search_res = self.web_grounder.ground_query(user_text) if self.web_grounder else {"has_results": False}
        if search_res.get("has_results"):
            web_context += f"\n\n--- DỮ LIỆU TÌM KIẾM WEB THỰC TẾ TRỰC TUYẾN (GROUNDING) ---\n{search_res['grounded_context']}\n"

        # C. Internal Department & Administrative Knowledge Base & Google Drive Legal Repository
        GDRIVE_LEGAL_FOLDER_ID = "1U39AY2NEkQm0eBXONId03QQGP2x_SALI"
        GDRIVE_LEGAL_FOLDER_URL = "https://drive.google.com/drive/folders/1U39AY2NEkQm0eBXONId03QQGP2x_SALI?usp=sharing"
        dept_knowledge = f"""
--- THÔNG TIN NỘI BỘ PHÒNG HỢP TÁC CÔNG TƯ VÀ QUẢN LÝ NỢ (SỞ TÀI CHÍNH TP.HCM) ---
- Trưởng phòng: Bà Tô Thị Kim Thoa (Chị Thoa).
- Phó Trưởng phòng phụ trách: Ông Lê Hoàng (Anh Hoàng).
- Chức năng nhiệm vụ: Thẩm định dự án PPP (BOT, BT, BTO...), quản lý nợ chính quyền địa phương, nguồn vốn ODA, lập Bảng giao việc hàng tuần trình Trưởng phòng Tô Thị Kim Thoa ký duyệt.
- Kho dữ liệu pháp lý Đám mây (24/7 Google Drive Repository): Folder ID `{GDRIVE_LEGAL_FOLDER_ID}` ({GDRIVE_LEGAL_FOLDER_URL}) chứa 23 lĩnh vực văn bản quy phạm pháp luật (Luật PPP 64/2020, NĐ 243/2025, NĐ 257/2025, NĐ 312/2025, TT 128/2025, TT 142/2025, NQ 98/2023, NQ 188/2025, NQ 260/2025, Luật Đất đai 31/2024, Luật Đấu thầu 22/2023, Luật Xây dựng, Đầu tư công...).
"""
        web_context += dept_knowledge

        # D. Local Document RAG Retrieval
        if self.rag_pipeline and hasattr(self.rag_pipeline, "retriever") and self.rag_pipeline.retriever:
            try:
                rag_chunks = self.rag_pipeline.retriever.search(user_text, top_k=3)
                if rag_chunks:
                    rag_str = "\n\n--- KHO TÀI LIỆU NỘI BỘ (RAG VECTOR CORPUS) ---\n"
                    for c in rag_chunks:
                        rag_str += f"[Nguồn: {c.get('source', 'Văn bản')}]\n{c.get('text', '')}\n\n"
                    web_context += rag_str
            except Exception:
                pass

        # E. Conversation History Memory Context
        if chat_history:
            history_str = "\n\n--- LỊCH SỬ HỘI THOẠI GẦN ĐÂY --- \n"
            for item in chat_history[-6:]:
                role = "Chuyên viên" if item.get("role") == "user" else "Zalo Bot"
                parts = item.get("parts", [{}])
                txt = parts[0].get("text", "") if parts else ""
                if txt:
                    history_str += f"{role}: {txt[:300]}\n"
            web_context += history_str

        prompt = f"""{system_time_context}
Bạn là Trợ lý AI Thông minh (Zalo Bot AI) của Phòng Hợp tác Công tư và Quản lý Nợ - Sở Tài chính TP.HCM.
Xưng hô chuẩn công vụ: Bắt đầu câu trả lời bằng "Dạ chào Anh/Chị chuyên viên,".
Thành viên: {sender_name} hỏi: "{user_text}"
{web_context}

Yêu cầu trả lời BẮT BUỘC:
- ĐỐI VỚI CÁC CÂU HỎI VỀ TIẾN ĐỘ, CON SỐ, HOẶC NHIỆM VỤ CỦA CHUYÊN VIÊN (như "anh Hận còn mấy cái chưa xong", "anh Hòa có task gì"): BẮT BUỘC đọc và trích dẫn trực tiếp dữ liệu từ mục 'DỮ LIỆU BẢNG GIAO VIỆC GOOGLE WORKSPACE (LIVE TASKS DATA)' ở trên để trả lời chính xác số lượng, tên nhiệm vụ và hạn hoàn thành.
- TUYỆT ĐỐI KHÔNG SUY DIỄN THÔNG TIN KHI CHƯA CÓ CĂN CỨ VĂN BẢN HOẶC DỮ LIỆU THỰC TẾ.
- TUYỆT ĐỐI KHÔNG TỰ BỊA TỶ SỐ THỂ THAO, CON SỐ TÀI CHÍNH HAY NỘI DUNG VĂN BẢN KHI DỮ LIỆU TÌM KIẾM CHƯA CÓ KẾT QUẢ CỤ THỂ. Nếu thông tin trận đấu/tin tức chưa có trong dữ liệu tìm kiếm web ở trên, BẮT BUỘC trả lời: "Dạ chào Anh/Chị chuyên viên, hiện tại dữ liệu trực tuyến chưa cập nhật kết quả chính thức cho thông tin này. Anh/Chị có thể thử lại sau hoặc cung cấp thêm thông tin chi tiết ạ."
- TUYỆT ĐỐI KHÔNG in ra các thẻ hệ thống hay dòng cấu hình nội bộ.
- Luôn giữ thái độ lịch sự, chuyên nghiệp, chuẩn mực văn phong hành chính nhà nước.
- TUYỆT ĐỐI KHÔNG dùng từ lóng, xưng "bro", "bạn ơi", "tự tìm đi" hay viết các đoạn giải thích phân trần dài dòng trong ngoặc đơn.
- Trình bày Markdown rõ ràng trên Zalo."""

        # 5. Gemini Synthesis Engine with Low-Temperature (0.0) Zero-Hallucination Config (Optimized Lite Models Only)
        gen_config = types.GenerateContentConfig(
            temperature=0.0,
            top_p=0.8,
        )
        models_to_try = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite', 'gemini-flash-lite-latest', 'gemini-3.5-flash']
        if self.client:
            for m in models_to_try:
                try:
                    resp = self.client.models.generate_content(model=m, contents=prompt, config=gen_config)

                    if resp.text and resp.text.strip():
                        ans = resp.text.strip()
                        if not any(refusal in ans for refusal in ["hệ thống bot không thể đồng bộ", "bạn có thể tự tìm", "do dữ liệu biến động từng giây", "Em xin phép sẽ cập nhật"]):
                            return ans
                except Exception as e:
                    continue

        # 6. Fallback Execution
        openclaw_ans = self.call_openclaw_agent(user_text)
        if openclaw_ans and not any(refusal in openclaw_ans for refusal in ["hệ thống bot không thể đồng bộ", "bạn có thể tự tìm", "do dữ liệu biến động từng giây"]):
            return openclaw_ans

        return f"Dạ chào Anh/Chị chuyên viên, hiện tại hệ thống chưa tìm thấy dữ liệu chính thức cho thông tin '{user_text}'. Anh/Chị vui lòng cung cấp thêm số hiệu hoặc trích yếu văn bản để hệ thống tra cứu chính xác ạ."

if __name__ == "__main__":
    agent = IntegratedZaloBotAgent()
    print("=== TEST 1: TIME QUERY ===")
    print(agent.process_message("Bây giờ là mấy giờ và hôm nay là ngày mấy?"))
    print("\n=== TEST 2: TASK QUERY ===")
    print(agent.process_message("Cho tui xem danh sách nhắc việc mới nhất"))

