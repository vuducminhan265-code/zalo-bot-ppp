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
    from tools.thuvienphapluat_crawler import ThuvienPhapLuatCrawler
except Exception as e:
    print(f"Notice: ThuvienPhapLuatCrawler fallback -> {e}")
    ThuvienPhapLuatCrawler = None

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

def is_task_reminder_intent(text: str) -> bool:
    """Nhận diện linh hoạt mọi biến thể truy vấn nhắc việc, tiến độ, task (nv, nhắc việc, tiến độ, /nhacviec...)."""
    if not text:
        return False
    t = text.lower().strip()
    # Loại bỏ tiền tố ký hiệu và xưng hô
    t = re.sub(r'^[/!@#\s]+', '', t)
    t = re.sub(r'^(bot|zalo\s*bot|ơi|em\s*ơi|ad\s*ơi|anh\s*ơi|chị\s*ơi)\s*,?\s*', '', t).strip()
    
    # Khớp chính xác các từ viết tắt / mã lệnh ngắn
    exact_matches = {
        "nv", "tasks", "task", "tiendo", "nhacviec", "nhac_viec", "tiến độ", "tien do",
        "nhắc việc", "nhac viec", "bảng giao việc", "bang giao viec", "giao việc", "giao viec"
    }
    if t in exact_matches:
        return True
        
    # Khớp regex cho các cụm từ yêu cầu báo cáo tiến độ / nhắc việc
    patterns = [
        r'^(xem|check|coi|kt|kiểm tra|báo cáo|thông báo|gửi|cập nhật|cho xem|cho coi|load)?\s*(nv|nhắc việc|nhac viec|tiến độ|tien do|bảng giao việc|bang giao viec|danh sách task|ds task|danh sách nhiệm vụ|ds nhiệm vụ)(\s*(nào|đi|với|hôm nay|tuần này|hiện tại|mới nhất|phòng|\?))*$',
        r'^(nhắc việc|nhac viec|tiến độ|tien do|bảng giao việc|bang giao viec)(\s*(hôm nay|tuần này|hiện tại|mới nhất|phòng|\?))*$',
        r'^(báo cáo|tình hình|tiến độ|trạng thái)\s*(công việc|nhiệm vụ|task|tasks|bảng giao việc)(\s*(hôm nay|tuần này|hiện tại|\?))*$',
        r'^/(nhacviec|nv|tasks?|tiendo)$'
    ]
    for p in patterns:
        if re.search(p, t):
            return True
            
    # Khớp ngữ nghĩa khi có cụm từ nổi bật và không phải câu hỏi văn bản quy phạm pháp luật
    prominent_phrases = [
        "nhắc việc", "nhac viec", "bảng giao việc", "bang giao viec", "báo cáo tiến độ", "bao cao tien do"
    ]
    if any(phrase in t for phrase in prominent_phrases) and not any(kw in t for kw in ["luật", "nghị định", "thông tư", "điều", "khoản"]):
        return True
        
    return False

class IntegratedZaloBotAgent:
    """Master AI Agent integrating OpenClaw Gateway, Real-time Context, Web Search Grounding, Google Workspace, RAG, TVPL Intelligence, and File Review."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.tvpl_crawler = ThuvienPhapLuatCrawler() if ThuvienPhapLuatCrawler else None
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
                    deliverable = review_res.get("deliverable", "Công văn")
                    assigned_staff = review_res.get("assigned_staff", "Chưa phân công")
                    recipient_initials = review_res.get("recipient_initials", "")
                    validation_errors = review_res.get("validation_errors", [])
                    resolution_options = review_res.get("resolution_options", [])
                    ai_comment = review_res.get("ai_review_comment", "")
                    discrepancy = review_res.get("discrepancy_reason", "")
                    file_name = os.path.basename(file_attachment_path)

                    if status_decision == "completed":
                        # Tự động cập nhật Google Sheets: Đã hoàn thành
                        sheets_updated = False
                        if self.task_manager and task_id:
                            try:
                                sheets_updated = self.task_manager.update_task_status_and_metadata(
                                    task_id=task_id,
                                    status="Đã hoàn thành",
                                    summary=ai_comment or f"{deliverable} số {doc_number} ngày {doc_date}: {actual_summary}",
                                    file_name=file_name,
                                    doc_number=doc_number,
                                    doc_date=doc_date,
                                    actual_summary=actual_summary,
                                    deliverable=deliverable
                                )
                            except Exception as e:
                                print(f"⚠️ Lỗi update Google Sheets: {e}", flush=True)

                        sheets_status_text = 'ĐÃ TỰ ĐỘNG CẬP NHẬT TRẠNG THÁI "ĐÃ HOÀN THÀNH" 🟢' if sheets_updated else 'Đã thẩm định hoàn thành đạt chuẩn 🟢'
                        initials_text = f"{recipient_initials} (Khớp chuyên viên: {assigned_staff})" if recipient_initials else f"Khớp chuyên viên: {assigned_staff}"
                        resp = [
                            "✅ [KẾT QUẢ THẨM ĐỊNH & NGHIỆM THU TỰ ĐỘNG - PHÒNG PPP]",
                            f"👤 Người nộp: {sender_name}",
                            f"📄 Tệp văn bản: {file_name}",
                            f"🔢 Đối soát: Khớp chuẩn Task #{task_id} (Phụ trách: {assigned_staff})",
                            f"📦 Sản phẩm: {deliverable}",
                            f"📑 Thể thức: Số {doc_number if doc_number else 'Văn bản nội bộ'} | Ngày {doc_date if doc_date else 'Hiện hành'}",
                            f"✍️ Ký lưu nơi nhận: {initials_text}",
                            f"📌 Trích yếu bóc tách: {actual_summary}",
                            f"💡 Đánh giá của AI: {ai_comment}",
                            "────────────────────────────",
                            f"📊 Bảng giao việc Google Sheets: {sheets_status_text}",
                            "🎉 Chúc mừng đồng chí đã hoàn thành xuất sắc nhiệm vụ được giao!"
                        ]
                        return "\n".join(resp)
                    else:
                        # Tự động cập nhật Google Sheets: Đang sửa lại (nếu có task_id)
                        sheets_updated = False
                        if self.task_manager and task_id:
                            try:
                                err_brief = "; ".join([e.replace('❌ ', '') for e in validation_errors[:2]]) if validation_errors else (discrepancy or "Cần hoàn thiện thể thức")
                                sheets_updated = self.task_manager.update_task_status_and_metadata(
                                    task_id=task_id,
                                    status="Đang sửa lại",
                                    summary=f"CẢNH BÁO SAI LỆCH: {err_brief}",
                                    file_name=file_name,
                                    doc_number=doc_number,
                                    doc_date=doc_date,
                                    actual_summary=actual_summary,
                                    deliverable=deliverable
                                )
                            except Exception as e:
                                print(f"⚠️ Lỗi update Google Sheets: {e}", flush=True)

                        sheets_warning_text = 'ĐÃ GHI NHẬN CẢNH BÁO "ĐANG SỬA LẠI" 🔴' if sheets_updated else 'Trạng thái: Đang sửa lại 🔴'
                        
                        err_items = []
                        if validation_errors:
                            for err in validation_errors:
                                err_items.append(f"• {err}")
                        elif discrepancy:
                            err_items.append(f"• {discrepancy}")
                        else:
                            err_items.append("• Nội dung hoặc trích yếu văn bản chưa khớp với sản phẩm yêu cầu của nhiệm vụ.")

                        res_items = []
                        if resolution_options:
                            for opt in resolution_options:
                                res_items.append(f"• {opt}")
                        else:
                            res_items.append("• Đề nghị chuyên viên rà soát lại văn bản trước khi nộp lại hoặc báo cáo Lãnh đạo.")

                        initials_display = recipient_initials if recipient_initials else "Không tìm thấy"
                        if assigned_staff and recipient_initials and not review_res.get("initials_match", True):
                            initials_display += f" (Khác chuyên viên phụ trách: {assigned_staff})"

                        resp = [
                            "⚠️ [CẢNH BÁO THẨM ĐỊNH AI: TỆP NỘP CHƯA ĐẠT CHUẨN CÔNG VỤ]",
                            f"👤 Người nộp: {sender_name}",
                            f"📄 Tệp văn bản: {file_name}",
                            f"🔢 Đối soát: Task #{task_id if task_id else 'Không xác định'}",
                            f"📦 Sản phẩm phát hiện: {deliverable}",
                            f"📑 Thể thức bóc tách: Số {doc_number if doc_number else 'Chưa có'} | Ngày {doc_date if doc_date else 'Chưa có'}",
                            f"✍️ Ký hiệu nơi nhận: {initials_display}",
                            f"📌 Trích yếu trong file: {actual_summary}",
                            f"💡 Nhận xét AI: {ai_comment}",
                            "",
                            "🚨 CÁC VẤN ĐỀ CẦN ĐIỀU CHỈNH / KHẮC PHỤC:",
                            "\n".join(err_items),
                            "",
                            "💡 HƯỚNG DẪN DÀNH CHO CHUYÊN VIÊN:",
                            "\n".join(res_items),
                            "────────────────────────────",
                            f"📊 Bảng giao việc Google Sheets: {sheets_warning_text}",
                            "👉 Đề nghị chuyên viên chỉnh sửa hoàn thiện và nộp lại tệp văn bản."
                        ]
                        return "\n".join(resp)

        # 2. Google Workspace Task Query Workflow (Flexible triggers: nv, nhắc việc, tiến độ, /nhacviec...)
        if is_task_reminder_intent(user_text):
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

        # B. Multi-Engine Web Search Grounding (Live Internet Search with Context Memory)
        search_target = user_text
        if chat_history and len(user_text.split()) <= 4:
            for past in reversed(chat_history):
                if past.get("role") == "user":
                    past_txt = past.get("parts", [{}])[0].get("text", "")
                    if len(past_txt.split()) > 3:
                        search_target = f"{past_txt} {user_text}"
                        break

        search_res = self.web_grounder.ground_query(search_target) if self.web_grounder else {"has_results": False}
        if search_res.get("has_results"):
            web_context += f"\n\n--- DỮ LIỆU TÌM KIẾM WEB THỰC TẾ TRỰC TUYẾN (GROUNDING) ---\n{search_res['grounded_context']}\n"

        # C. Thư Viện Pháp Luật & Real-Time Legal Grounding (Nghị định mới & Điểm bôi vàng sửa đổi)
        legal_keywords = [
            "luật", "nghị định", "thông tư", "nghị quyết", "pháp luật", "quy định",
            "điều", "khoản", "điểm", "nhóm a", "nhóm b", "nhóm c", "quan trọng quốc gia",
            "bcnctkt", "nghiên cứu tiền khả thi", "nghiên cứu khả thi", "chủ trương đầu tư",
            "hồ sơ cần lập", "loại hồ sơ", "tiêu chí", "tổng mức", "377", "243", "257", "312",
            "58/2024", "64/2020", "31/2024", "hợp đồng bt", "hợp đồng bot", "o&m", "thẩm định",
            "bôi vàng", "sửa đổi", "bãi bỏ", "thay thế", "phân loại dự án", "căn cứ",
            "môi trường", "chứng khoán", "đất đai", "nhà ở", "xây dựng", "bất động sản",
            "doanh nghiệp", "đầu tư", "đấu thầu", "thuế", "lao động", "ngân sách", "giá",
            "tài chính", "kinh doanh", "cổ phiếu", "trái phiếu", "đtm", "đánh giá tác động", "giấy phép"
        ]
        is_legal_query = any(k in text_lower for k in legal_keywords)
        if self.tvpl_crawler and is_legal_query:
            try:
                tvpl_data = self.tvpl_crawler.fetch_legal_cross_reference(user_text)
                if tvpl_data:
                    web_context += f"\n\n--- THƯ VIỆN PHÁP LUẬT & NỘI DUNG BÔI VÀNG MỚI NHẤT (TVPL INTELLIGENCE) ---\n{tvpl_data}\n"
            except Exception as e:
                print(f"Notice: TVPL crawler error -> {e}")

        # D. Internal Department & Administrative Knowledge Base & Google Drive Legal Repository
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

        # E. Local Document RAG Retrieval
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

        # F. Conversation History Memory Context
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
Bạn là Trợ lý AI Thông minh Cấp cao (Zalo Bot AI Giáo sư PPP) của Phòng Hợp tác Công tư và Quản lý Nợ - Sở Tài chính TP.HCM.
Xưng hô chuẩn công vụ: Bắt đầu câu trả lời bằng "Dạ chào Anh/Chị chuyên viên,".
Thành viên: {sender_name} hỏi: "{user_text}"
{web_context}

Yêu cầu trả lời BẮT BUỘC:
1. ĐỊNH DẠNG ZALO CHUẨN: Giao diện Zalo KHÔNG hỗ trợ định dạng Markdown (như **in đậm**, *in nghiêng*, ### tiêu đề). BẮT BUỘC KHÔNG DÙNG các ký tự `**`, `*`, `###` trong toàn bộ câu trả lời.
2. ĐI THẲNG VÀO CÂU TRẢ LỜI NGAY DÒNG ĐẦU TIÊN: Trả lời trực tiếp kết quả/nội dung điều luật/sự kiện ngay ở câu đầu tiên. Tuyệt đối KHÔNG viết các câu dẫn dài dòng, câu xin lỗi hay câu từ chối né tránh.
3. ĐỐI VỚI CÁC CÂU HỎI TIN TỨC, THỜI SỰ, THỂ THAO, LỊCH THI ĐẤU, SỰ KIỆN:
- BẮT BUỘC TRÍCH XUẤT CÁC CẶP ĐẤU, ĐỘI TUYỂN, THỜI GIAN, TỶ SỐ CỤ THỂ từ 'DỮ LIỆU TÌM KIẾM WEB THỰC TẾ TRỰC TUYẾN' để trả lời trực diện ngay lập tức.
- TUYỆT ĐỐI NGHIÊM CẤM đưa ra các câu trả lời né tránh, thoái thác như: "Quý chuyên viên vui lòng truy cập các trang...", "vui lòng theo dõi trên báo...", "vui lòng kiểm tra lịch trình của ban tổ chức...". BẮT BUỘC liệt kê rõ ràng các trận đấu, đội tuyển và khung giờ diễn ra tìm thấy trong dữ liệu!
- TUYỆT ĐỐI KHÔNG sử dụng các từ giữ chỗ trong ngoặc vuông (placeholder brackets) như [Tên đội đối thủ], [Giờ thi đấu], [Thời gian cụ thể]! Hãy đưa ra tên đối thủ cụ thể, giờ thi đấu cụ thể đã tìm thấy từ dữ liệu web (ví dụ: Leeds vs MU lúc 20:00 ngày 18/10). Nếu thực sự không có thì thông báo rõ ràng là chưa có thông tin chứ không điền ngoặc vuông giả định.
4. ĐỐI VỚI CÁC CÂU HỎI VỀ TIẾN ĐỘ, TASK CHUYÊN VIÊN: Đọc và trích dẫn trực tiếp từ 'DỮ LIỆU BẢNG GIAO VIỆC GOOGLE WORKSPACE'.
5. BẢO TỒN NGUYÊN VẸN 100% CẤU TRÚC ĐIỀU KHOẢN QUY PHẠM PHÁP LUẬT (QPPL) - TUYỆT ĐỐI QUAN TRỌNG:
- Khi trích xuất hoặc trình bày bất kỳ Điều luật nào, BẮT BUỘC giữ nguyên cấu trúc số thứ tự và phân cấp chính thống của văn bản QPPL:
  Điều ... [Tên Điều]
  1. [Nội dung Khoản 1]
     (Căn cứ: Khoản 1 Điều ...)
  2. [Nội dung Khoản 2]
     (Căn cứ: Khoản 2 Điều ...)
  3. [Nội dung Khoản 3]
     a) [Nội dung Điểm a]
     b) [Nội dung Điểm b]
     c) [Nội dung Điểm c]
     (Căn cứ: Khoản 3 Điều ...)
- TUYỆT ĐỐI KHÔNG BIẾN CÁC KHOẢN 1, 2, 3 HOẶC CÁC ĐIỂM a), b), c) THÀNH DẤU CHẤM TRÒN `•` HAY GẠCH ĐẦU DÒNG `-`! Người dùng cần kiểm tra, đối chiếu chính xác từng Điểm, từng Khoản trên Thư viện Pháp luật nên việc thay bằng dấu `•` là hoàn toàn sai chuẩn thể thức.
- Dấu `•` chỉ dùng khi liệt kê các nội dung tổng hợp ngoài lề (ví dụ: danh mục tiêu chuẩn dự án, các lưu ý tổng quát không thuộc phân cấp điều luật).
6. NGUYÊN TẮC HỢP NHẤT VĂN BẢN TRỰC TIẾP TẠI CHỖ (IN-PLACE CONSOLIDATION CHO NỘI DUNG BÔI VÀNG):
- Khi trả lời về một Điều luật có nội dung bôi vàng sửa đổi (như Điều 28, Điều 43, Điều 72... Nghị định 243/2025/NĐ-CP được sửa đổi bởi Nghị định 377/2026/NĐ-CP):
  + Đối với các điểm, khoản KHÔNG bị sửa đổi (như Khoản 1 Điều 72, Khoản 2 Điều 43): Giữ nguyên nội dung quy định gốc còn hiệu lực và ghi rõ (Căn cứ: Khoản ... Điều ... Nghị định 243/2025/NĐ-CP).
  + Đối với các điểm, khoản ĐÃ ĐƯỢC BÔI VÀNG SỬA ĐỔI / THAY THẾ / BỔ SUNG (như Khoản 2, Khoản 3, Khoản 4 Điều 72 được sửa đổi, bổ sung bởi Điều 27 Nghị định 377/2026/NĐ-CP; hay Khoản 1 Điều 43; Điểm d Khoản 2 Điều 28): BẮT BUỘC TRÌNH BÀY ĐẦY ĐỦ CÂU VĂN QUY ĐỊNH MỚI NHẤT ĐÃ ĐƯỢC HỢP NHẤT TẠI CHỖ, TUYỆT ĐỐI KHÔNG BỎ SÓT KHOẢN MỚI BỔ SUNG!
  + TUYỆT ĐỐI KHÔNG đưa ra văn bản cũ chưa cập nhật.
  + Đính kèm dòng căn cứ chi tiết ngay bên dưới mỗi khoản/điểm đó:
    (Căn cứ: Khoản ... Điều ... Nghị định 243/2025/NĐ-CP; được sửa đổi, bổ sung bởi Điều ... Nghị định 377/2026/NĐ-CP ngày 01/10/2026, có hiệu lực từ ngày 01/10/2026)
- ĐẶC BIỆT LƯU Ý VỀ CẤP ĐIỀU KHOẢN (ĐIỀU CHỈ CÓ KHOẢN, KHÔNG CÓ ĐIỂM):
  + Nếu điều luật chỉ phân chia thành các KHOẢN mà không có Điểm (ví dụ: Điều 10 Luật Đầu tư công chỉ có 4 Khoản: Khoản 1, Khoản 2, Khoản 3, Khoản 4): Dòng căn cứ BẮT BUỘC CHỈ GHI CẤP KHOẢN, ví dụ: "(Căn cứ: Khoản 1 Điều 10 (tham chiếu lĩnh vực tại Khoản 2 Điều 9) Luật Đầu tư công 2024)". TUYỆT ĐỐI CẤM TỰ BỊA RA "Điểm a Khoản 1", "Điểm b Khoản 1"...
7. Kết thúc bằng câu ngắn gọn: "Trân trọng." hoặc "Kính báo Anh/Chị chuyên viên."."""

        def sanitize_zalo_text(raw_txt: str) -> str:
            if not raw_txt: return ""
            # Strip markdown bold/italics symbols
            t = re.sub(r'\*\*(.*?)\*\*', r'\1', raw_txt)
            t = re.sub(r'\*(.*?)\*', r'\1', t)
            t = re.sub(r'_(.*?)_', r'\1', t)
            t = re.sub(r'^#{1,6}\s*(.*)', r'📌 \1', t, flags=re.MULTILINE)
            # Preserve official QPPL statutory numbering (1., 2., a), b)...)
            t = re.sub(r'^\s*[\-\*]\s+(?=[0-9]+\.|\b[a-zđ]\))', '', t, flags=re.MULTILINE)
            t = re.sub(r'^\s*[\-\*]\s+', '• ', t, flags=re.MULTILINE)
            t = re.sub(r'`(.*?)`', r'\1', t)
            t = re.sub(r'\n{3,}', '\n\n', t)
            return t.strip()

        # 5. Gemini Synthesis Engine with Low-Temperature (0.0) Zero-Hallucination Config (Optimized Flash Models)
        gen_config = types.GenerateContentConfig(
            temperature=0.0,
            top_p=0.8,
        )
        models_to_try = ['gemini-3.5-flash', 'gemini-3.5-flash-lite', 'gemini-3-flash-preview']
        refusal_phrases = [
            "hệ thống bot không thể đồng bộ", "bạn có thể tự tìm", "do dữ liệu biến động từng giây",
            "em xin phép sẽ cập nhật", "vui lòng truy cập", "truy cập trực tiếp", "để nắm bắt khung giờ",
            "vui lòng theo dõi tại", "vui lòng tra cứu trên", "vui lòng vào các trang"
        ]
        if self.client:
            for m in models_to_try:
                try:
                    resp = self.client.models.generate_content(model=m, contents=prompt, config=gen_config)

                    if resp.text and resp.text.strip():
                        ans = resp.text.strip()
                        if not any(refusal in ans.lower() for refusal in refusal_phrases):
                            return sanitize_zalo_text(ans)
                except Exception as e:
                    continue

        # 6. Fallback Execution
        openclaw_ans = self.call_openclaw_agent(user_text)
        if openclaw_ans and not any(refusal in openclaw_ans.lower() for refusal in refusal_phrases):
            return sanitize_zalo_text(openclaw_ans)

        return sanitize_zalo_text(f"Dạ chào Anh/Chị chuyên viên, hiện tại hệ thống chưa tìm thấy dữ liệu chính thức cho thông tin '{user_text}'. Anh/Chị vui lòng cung cấp thêm số hiệu hoặc trích yếu văn bản để hệ thống tra cứu chính xác ạ.")

if __name__ == "__main__":
    agent = IntegratedZaloBotAgent()
    print("=== TEST 1: TIME QUERY ===")
    print(agent.process_message("Bây giờ là mấy giờ và hôm nay là ngày mấy?"))
    print("\n=== TEST 2: TASK QUERY ===")
    print(agent.process_message("Cho tui xem danh sách nhắc việc mới nhất"))

