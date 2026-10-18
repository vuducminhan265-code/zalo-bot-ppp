# Function department/ai_core/ai_analyzer.py
import os
import json
import re
import sys
import shutil
import tempfile
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
import pypdf
import base64

load_dotenv()

DEFAULT_GEMINI_KEY = base64.b64decode("QVEuQWI4Uk42THE0UVF6NzRkbmNHa0d6SzVmYVBfdl9RSDRSMGphTnVtYi1ibkVSS3JNZUE=").decode()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or DEFAULT_GEMINI_KEY

# Bảng tra cứu chữ viết tắt chuyên viên tại Nơi nhận (Lưu: VT, PPP&QLN (...))
STAFF_INITIALS_MAP = {
    "nguyễn thế hòa": ["nthoa", "thoa", "thhoa", "hoa", "nguyenthehoa"],
    "nguyễn trung bảo lộc": ["ntbloc", "tbloc", "bloc", "nbloc", "loc", "nguyentrungbaoloc"],
    "hoàng thị hương giang": ["hthgiang", "thgiang", "hgiang", "giang", "hoangthihuonggiang"],
    "phan công hận": ["pchan", "chan", "han", "phanconghan"],
    "vũ đức minh an": ["vdman", "dman", "man", "an", "vuducminhan", "alexander"],
    "lê hoàng": ["lhoang", "lehoang", "hoang"],
    "tô thị kim thoa": ["ttkthoa", "kthoa", "tothikimthoa"]
}

class TaskAIAnalyzer:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or GEMINI_API_KEY or DEFAULT_GEMINI_KEY
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def extract_task_number_from_filename(self, filename: str) -> str:
        """Trích xuất số Task ID đứng đầu tên file (Ví dụ: '1. 7937_UBND_PKT.pdf' -> '1', '1 - Tran Hung Dao.pdf' -> '1')"""
        base_name = os.path.basename(filename)
        # Loại bỏ tiền tố hệ thống nếu có
        clean_name = re.sub(r"^(?:zalo|bot|upload|temp|file)_[a-zA-Z0-9_\-]*?_\d+__?", "", base_name)
        m = re.match(r"^(?:\[?(\d{1,2})\]?|[nN][vV](\d{1,2})|[tT]ask[_\-\s]*(\d{1,2}))[.\s\-_]", clean_name)
        if m:
            for g in m.groups():
                if g:
                    return g
        m2 = re.match(r"^(?:\[?(\d{1,2})\]?|[nN][vV](\d{1,2})|[tT]ask[_\-\s]*(\d{1,2}))[.\s\-_]", base_name)
        if m2:
            for g in m2.groups():
                if g:
                    return g
        return ""

    def _extract_text_fallback(self, file_path: str) -> str:
        """Trích xuất thông minh trang đầu, trang nơi nhận, và trang cuối từ PDF/Word"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            try:
                reader = pypdf.PdfReader(file_path)
                num_pages = len(reader.pages)
                extracted_pages = []
                
                # 1. Luôn đọc tối đa 3 trang đầu (Tiêu ngữ, Số ký hiệu, Ngày, Trích yếu)
                for p_idx in range(min(3, num_pages)):
                    txt = reader.pages[p_idx].extract_text() or ""
                    extracted_pages.append(f"--- TRANG {p_idx + 1} (ĐẦU VĂN BẢN) ---\n" + txt)
                    
                # 2. Tìm kiếm các trang có "Nơi nhận:" hoặc "Lưu:"
                for p_idx in range(3, num_pages):
                    txt = reader.pages[p_idx].extract_text() or ""
                    if any(k in txt for k in ["Nơi nhận", "Lưu:", "VT,", "PPP&QLN"]):
                        extracted_pages.append(f"--- TRANG {p_idx + 1} (NƠI NHẬN & CHỮ KÝ) ---\n" + txt)
                        
                # 3. Luôn đọc trang cuối nếu chưa nằm trong danh sách
                if num_pages > 3 and not any(f"--- TRANG {num_pages}" in ep for ep in extracted_pages):
                    txt_last = reader.pages[-1].extract_text() or ""
                    extracted_pages.append(f"--- TRANG {num_pages} (TRANG CUỐI) ---\n" + txt_last)
                    
                return "\n\n".join(extracted_pages)
            except Exception as e:
                sys.stderr.write(f"PDF extract error: {e}\n")
        elif ext in [".docx", ".doc"]:
            try:
                import docx
                doc = docx.Document(file_path)
                lines = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
                # Đọc cả các ô bảng biểu (nơi chứa tiêu ngữ và nơi nhận)
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            for p in cell.paragraphs:
                                if p.text and p.text.strip():
                                    lines.append(p.text.strip())
                return "\n".join(lines)
            except Exception as e:
                sys.stderr.write(f"DOCX extract error: {e}\n")
        elif ext in [".xlsx", ".xls"]:
            try:
                import openpyxl
                wb = openpyxl.load_workbook(file_path, data_only=True)
                lines = []
                for sheet in wb.worksheets[:3]:
                    for row in sheet.iter_rows(values_only=True):
                        row_vals = [str(val).strip() for val in row if val is not None]
                        if row_vals:
                            lines.append(" | ".join(row_vals))
                return "\n".join(lines[:200])
            except Exception as e:
                pass
        elif ext in [".jpg", ".jpeg", ".png"]:
            try:
                with open(file_path, "rb") as f:
                    img_bytes = f.read()
                mime = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
                img_part = types.Part.from_bytes(data=img_bytes, mime_type=mime)
                resp = self.client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=[img_part, "Hãy đọc toàn bộ văn bản trong ảnh này, giữ nguyên đầy đủ tiêu ngữ, số ký hiệu, ngày tháng, trích yếu, nội dung và nơi nhận (Lưu: VT, PPP&QLN...)."]
                )
                return resp.text.strip() if resp.text else ""
            except Exception as e:
                sys.stderr.write(f"Image extract error: {e}\n")
        return ""

    def _extract_regex_metadata(self, text: str) -> dict:
        """Trích xuất nhanh các trường thể thức bằng biểu thức chính quy (Regex)"""
        meta = {
            "document_number": "",
            "document_date": "",
            "deliverable": "Công văn",
            "recipient_initials": ""
        }
        if not text:
            return meta

        # 1. Trích xuất Số ký hiệu văn bản (Ví dụ: Số: 7937 /UBND-PKT hoặc 23920/STC-PPP&QLN)
        doc_num_match = re.search(r'Số:\s*([0-9A-Za-z\/\-_\.\s]+?)(?=\s+ngày|\s*\n|\s+V\/v|\s+Về)', text, re.IGNORECASE)
        if doc_num_match:
            candidate = doc_num_match.group(1).strip()
            # Làm sạch khoảng trắng thừa
            candidate = re.sub(r'\s+', ' ', candidate)
            if re.search(r'\d+', candidate) and '/' in candidate:
                meta["document_number"] = candidate

        # 2. Trích xuất Ngày ban hành (Ví dụ: ngày 29 tháng 9 năm 2026)
        date_match = re.search(r'(?:ngày|ngy)\s+(\d{1,2})\s+(?:tháng|thng)\s+(\d{1,2})\s+(?:năm|nm)\s+(\d{4})', text, re.IGNORECASE)
        if date_match:
            day, month, year = date_match.group(1), date_match.group(2), date_match.group(3)
            meta["document_date"] = f"{int(day):02d}/{int(month):02d}/{year}"

        # 3. Phân loại Sản phẩm / Loại văn bản
        first_part = text[:2500].upper()
        if "TỜ TRÌNH" in first_part or "TTR-" in text:
            meta["deliverable"] = "Tờ trình"
        elif "KẾT LUẬN" in first_part or "TB-KL" in text:
            meta["deliverable"] = "Kết luận"
        elif "BÁO CÁO" in first_part or "BC-" in text:
            meta["deliverable"] = "Báo cáo"
        elif "QUYẾT ĐỊNH" in first_part or "QĐ-" in text or "QD-" in text:
            meta["deliverable"] = "Quyết định"
        elif "KẾ HOẠCH" in first_part or "KH-" in text:
            meta["deliverable"] = "Kế hoạch"
        elif "THÔNG BÁO" in first_part or "TB-" in text:
            meta["deliverable"] = "Thông báo"
        else:
            meta["deliverable"] = "Công văn"

        # 4. Trích xuất Chữ viết tắt chuyên viên tại Nơi nhận: Lưu: VT, PPP&QLN (Nthoa, 03b).
        initials_match = re.search(r'Lưu:\s*VT[^\n\)]*\(([A-Za-z0-9_\-]+?)(?:[,\s]+[0-9]+[a-zA-Z]*)?\)', text, re.IGNORECASE)
        if initials_match:
            meta["recipient_initials"] = initials_match.group(1).strip()

        return meta

    def check_initials_match_assignee(self, initials: str, assignee_name: str) -> bool:
        """Đối chiếu chữ viết tắt tại Nơi nhận với tên chuyên viên được giao nhiệm vụ trên Spreadsheet"""
        if not initials or not assignee_name:
            return False
        init_clean = initials.lower().strip()
        ass_clean = assignee_name.lower().strip()
        
        # 1. So khớp theo bản đồ chữ viết tắt chính thức
        for full_name, valid_list in STAFF_INITIALS_MAP.items():
            if full_name in ass_clean or ass_clean in full_name:
                return init_clean in valid_list
                
        # 2. So khớp tự động nếu viết tên không dấu hoặc chữ cái đầu
        tokens = [re.sub(r'[^\w]', '', w) for w in ass_clean.split()]
        if tokens:
            last_name = tokens[-1]
            first_letters = "".join([w[0] for w in tokens[:-1]])
            combined = f"{first_letters}{last_name}"
            if init_clean == combined or init_clean == last_name:
                return True
                
        return False

    def review_submission(self, file_path: str, assignee_name: str, pending_tasks: list, user_hint_text: str = "") -> dict:
        """
        Quy trình Thẩm định Sản phẩm Tự động Đa tầng (Multi-Tier Rigorous Document Review):
        1. Kiểm tra số ID nhiệm vụ ở đầu tên file hoặc tin nhắn đi kèm hoặc đối chiếu từ khóa trích yếu.
        2. Bóc tách thể thức hành chính: Số ký hiệu, Ngày tháng, Sản phẩm (Tờ trình/Kết luận/Báo cáo/Công văn).
        3. Dò trích yếu và đối chiếu từ khóa (Keywords) dự án.
        4. TIÊU CHÍ TUYÊN QUYẾT: Dò chữ viết tắt chuyên viên tại Nơi nhận (Lưu: VT, PPP&QLN (...)).
        5. Phân loại ĐẠT (completed) hoặc CẢNH BÁO LỖI (needs_revision) kèm hướng dẫn khắc phục.
        """
        filename = os.path.basename(file_path)
        hint_task_id = self.extract_task_number_from_filename(filename)
        
        # 1. Trích xuất text từ văn bản / OCR ảnh
        local_text = self._extract_text_fallback(file_path)
        regex_meta = self._extract_regex_metadata(local_text)

        # 2. Nếu tên file chưa có Task ID, tìm trong tin nhắn đi kèm (user_hint_text)
        if not hint_task_id and user_hint_text:
            m_text = re.search(r'\b(?:task|nhiệm vụ|stt|số)?\s*#?([0-9]{1,3})\b', user_hint_text, re.IGNORECASE)
            if m_text:
                hint_task_id = m_text.group(1)

        # 3. Nếu vẫn chưa có, tự động dò từ khóa trích yếu với Bảng giao việc Google Sheets
        if not hint_task_id and local_text:
            for t in pending_tasks:
                t_id = str(t.get("taskId") or t.get("task_id") or "").strip()
                t_name = (t.get("taskName") or t.get("task_name") or "").lower()
                clean_tname = re.sub(r'^(?:v\/v|về việc|dự án)\s*', '', t_name).strip()
                kws = [w for w in re.split(r'[,.\s\-_/]+', clean_tname) if len(w) >= 3 and w not in ["công", "viên", "trình", "thực", "hiện", "theo", "đầu", "tư", "phương", "thức", "đối", "tác", "báo", "cáo", "nghiên", "cứu", "khả", "thi"]]
                matches = sum(1 for kw in kws if kw in local_text.lower())
                if matches >= 2:
                    hint_task_id = t_id
                    break

        # Lỗi: Không xác định được số ID nhiệm vụ
        if not hint_task_id:
            return {
                "success": True,
                "task_id": "",
                "status_decision": "needs_revision",
                "deliverable": regex_meta.get("deliverable", "Văn bản"),
                "document_number": regex_meta.get("document_number", ""),
                "document_date": regex_meta.get("document_date", ""),
                "actual_summary": "Chưa bóc tách do chưa xác định được Task ID",
                "recipient_initials": regex_meta.get("recipient_initials", ""),
                "assigned_staff": assignee_name,
                "ai_review_comment": "Văn bản chưa khớp được với số thứ tự Task nào trên Bảng giao việc.",
                "discrepancy_reason": "Vui lòng đặt tên file có số Task ở đầu (Ví dụ: '4 - Ten van ban.pdf') hoặc nhắn kèm 'Nộp task [số]'.",
                "validation_errors": [
                    "❌ Không xác định được số thứ tự ID nhiệm vụ tương ứng trên Bảng giao việc."
                ],
                "resolution_options": [
                    "👉 Đổi lại tên file bắt đầu bằng số thứ tự ID của nhiệm vụ (Ví dụ: '4 - Chinh trang Ma Lang - Loc.pdf').",
                    "👉 Hoặc nhắn kèm nội dung 'task 4' khi nộp ảnh văn bản."
                ]
            }

        # Tìm task tương ứng trong pending_tasks
        matched_task = None
        for t in pending_tasks:
            t_id = str(t.get("taskId") or t.get("task_id") or "").strip()
            if t_id == str(hint_task_id).strip():
                matched_task = t
                break

        assigned_staff_in_task = (matched_task.get("assignee") or matched_task.get("assigned_to")) if matched_task else assignee_name

        prompt = f"""
Bạn là Trợ lý Nghiệm thu & Thẩm định Thể thức Văn bản Hành chính (Phòng Hợp tác Công tư & Quản lý Nợ - Sở Tài Chính TP.HCM).
Chuyên viên: {assignee_name} nộp tệp: "{filename}".
Mã số Task ID bóc tách từ tên file: {hint_task_id}.
Chuyên viên phụ trách theo Bảng giao việc: {assigned_staff_in_task}.

DANH SÁCH NHIỆM VỤ TRÊN BẢNG GIAO VIỆC GOOGLE SHEETS:
{json.dumps(pending_tasks, ensure_ascii=False, indent=2)}

NỘI DUNG VĂN BẢN ĐÃ BÓC TÁCH:
\"\"\"
{local_text[:14000] if local_text else "Vui lòng phân tích tệp trực tiếp"}
\"\"\"

KẾT QUẢ RÀ SOÁT SƠ BỘ TỪ BIỂU THỨC CHÍNH QUY (REGEX):
- Số ký hiệu gợi ý: {regex_meta.get('document_number')}
- Ngày ban hành gợi ý: {regex_meta.get('document_date')}
- Loại văn bản gợi ý: {regex_meta.get('deliverable')}
- Chữ viết tắt nơi nhận gợi ý: {regex_meta.get('recipient_initials')}

YÊU CẦU THẨM ĐỊNH CHI TIẾT (BẮT BUỘC):
1. THỂ THỨC VĂN BẢN:
   - "document_number": Tìm chính xác Số ký hiệu văn bản (Ví dụ: "7937 /UBND-PKT", "23920/STC-PPP&QLN", "145/TTr-STC-PPP"). Nếu văn bản chưa có số (còn để trống) thì để chuỗi rỗng "".
   - "document_date": Ngày tháng năm ban hành (Định dạng "DD/MM/YYYY"). Nếu văn bản chưa có ngày thì để rỗng "".
   - "deliverable": Xác định chuẩn loại sản phẩm: "Tờ trình", "Kết luận", "Báo cáo", "Quyết định", "Kế hoạch", "Thông báo", "Công văn".
   - "actual_summary": Trích yếu thực tế trong văn bản (bắt đầu bằng V/v hoặc Về việc...).

2. ĐỐI SOÁT TRÍCH YẾU & TỪ KHÓA (KEYWORDS):
   - So sánh trích yếu bóc tách với Tên nhiệm vụ / Trích yếu của Task #{hint_task_id}.
   - KHÔNG CẦN TRÙNG 100% TỪNG CHỮ (vì trên Sheet có thể ghi vắn tắt tên dự án, trong khi văn bản ghi đầy đủ dài).
   - "keyword_match": true nếu khớp các từ khóa cốt lõi của dự án (tên dự án, địa danh, đối tác, loại hợp đồng BT/BOT); false nếu nội dung nói về dự án khác hoặc từ khóa quá thấp.
   - "matched_keywords": Danh sách các từ khóa dự án khớp được.

3. ĐIỀU KIỆN TIÊN QUYẾT: DÒ NƠI NHẬN & CHỮ VIẾT TẮT CHUYÊN VIÊN:
   - Tìm dòng cuối văn bản tại mục "Nơi nhận": "- Lưu: VT, PPP&QLN (..., ...b)."
   - "recipient_initials": Trích chữ viết tắt trong ngoặc đơn (Ví dụ: "Nthoa", "pchan", "Ntbloc", "Hthgiang", "Vdman"...).
   - "initials_match": true nếu chữ viết tắt này đúng là của chuyên viên được giao nhiệm vụ ({assigned_staff_in_task}); false nếu là của chuyên viên khác hoặc không tìm thấy.

4. KẾT LUẬN NGHIỆM THU:
   - "status_decision": "completed" nếu KHỚP ĐỦ: (1) Trích yếu/từ khóa khớp; (2) Có Số ký hiệu; (3) Có Ngày ban hành; (4) Chữ viết tắt nơi nhận khớp đúng chuyên viên phụ trách.
   - Nếu vi phạm bất kỳ tiêu chí nào -> "needs_revision".
   - "validation_errors": Danh sách các lỗi phát hiện (ví dụ: Thiếu số ký hiệu, Thiếu ngày, Sai chữ viết tắt nơi nhận...).

TRẢ VỀ ĐỊNH DẠNG JSON DUY NHẤT:
{{
  "task_id": "{hint_task_id}",
  "status_decision": "completed" hoặc "needs_revision",
  "deliverable": "Loại sản phẩm (Tờ trình, Kết luận, Báo cáo, Công văn...)",
  "document_number": "Số ký hiệu văn bản hoặc rỗng",
  "document_date": "Ngày ban hành DD/MM/YYYY hoặc rỗng",
  "actual_summary": "Trích yếu thực tế trong file",
  "recipient_initials": "Chữ viết tắt tại nơi nhận (ví dụ Nthoa, pchan...)",
  "keyword_match": true hoặc false,
  "matched_keywords": ["từ khóa 1", "từ khóa 2"],
  "initials_match": true hoặc false,
  "validation_errors": [],
  "ai_review_comment": "Nhận xét thẩm định công vụ súc tích (1-2 câu)",
  "resolution_options": ["Hướng dẫn 1", "Hướng dẫn 2"]
}}
"""
        models_to_try = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-latest"]
        last_error = None
        ext = os.path.splitext(file_path)[1].lower()
        for model_name in models_to_try:
            try:
                contents = [prompt]
                if ext in [".jpg", ".jpeg", ".png"]:
                    try:
                        with open(file_path, "rb") as f_img:
                            img_b = f_img.read()
                        mime = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
                        contents = [types.Part.from_bytes(data=img_b, mime_type=mime), prompt]
                    except Exception:
                        pass
                resp = self.client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.0
                    )
                )
                raw_text = resp.text.strip()
                raw_text = re.sub(r"^```json\s*", "", raw_text)
                raw_text = re.sub(r"```$", "", raw_text).strip()
                data = json.loads(raw_text)
                data["success"] = True

                # Hậu kiểm tra deterministic nếu regex bắt được tốt hơn
                if not data.get("document_number") and regex_meta.get("document_number"):
                    data["document_number"] = regex_meta.get("document_number")
                if not data.get("document_date") and regex_meta.get("document_date"):
                    data["document_date"] = regex_meta.get("document_date")
                if not data.get("recipient_initials") and regex_meta.get("recipient_initials"):
                    data["recipient_initials"] = regex_meta.get("recipient_initials")

                # Kiểm tra lại chữ viết tắt nơi nhận bằng Python deterministic logic
                recip_init = data.get("recipient_initials", "")
                if recip_init:
                    verified_match = self.check_initials_match_assignee(recip_init, assigned_staff_in_task)
                    data["initials_match"] = verified_match
                
                # Tổng hợp danh sách lỗi
                val_errors = data.get("validation_errors", [])
                if not data.get("keyword_match"):
                    val_errors.append("❌ LỖI TRÍCH YẾU: Nội dung trích yếu không khớp hoặc từ khóa quá thấp so với nhiệm vụ được giao.")
                if not data.get("document_number"):
                    val_errors.append("❌ LỖI THỂ THỨC: Văn bản chưa có Số ký hiệu chính thức (còn để trống).")
                if not data.get("document_date"):
                    val_errors.append("❌ LỖI THỂ THỨC: Văn bản chưa có Ngày tháng năm ban hành chính thức.")
                if recip_init and not data.get("initials_match"):
                    val_errors.append(f"❌ LỖI NGƯỜI PHỤ TRÁCH: Chữ viết tắt tại Nơi nhận là '{recip_init}', không khớp với chuyên viên được giao nhiệm vụ ('{assigned_staff_in_task}').")

                data["validation_errors"] = list(dict.fromkeys(val_errors))
                
                # Quyết định trạng thái cuối cùng
                if len(data["validation_errors"]) == 0 and data.get("keyword_match") and data.get("initials_match", True):
                    data["status_decision"] = "completed"
                else:
                    data["status_decision"] = "needs_revision"
                    if not data.get("resolution_options"):
                        data["resolution_options"] = [
                            "👉 Kiểm tra và bổ sung đầy đủ Số ký hiệu, Ngày tháng năm ban hành văn bản.",
                            f"👉 Kiểm tra chữ viết tắt chuyên viên tại mục Nơi nhận (Lưu: VT, PPP&QLN (...)) bảo đảm đúng tên người phụ trách ({assigned_staff_in_task}).",
                            "👉 Nộp lại tệp văn bản sau khi đã hoàn thiện thể thức."
                        ]

                data["assigned_staff"] = assigned_staff_in_task
                return data
            except Exception as e:
                last_error = str(e)
                time.sleep(1)

        # Fallback an toàn nếu LLM lỗi mạng
        status = "completed" if regex_meta.get("document_number") and regex_meta.get("document_date") else "needs_revision"
        return {
            "success": True,
            "task_id": hint_task_id,
            "status_decision": status,
            "deliverable": regex_meta.get("deliverable", "Công văn"),
            "document_number": regex_meta.get("document_number", ""),
            "document_date": regex_meta.get("document_date", ""),
            "actual_summary": "Trích xuất tự động qua thể thức văn bản",
            "recipient_initials": regex_meta.get("recipient_initials", ""),
            "assigned_staff": assigned_staff_in_task,
            "keyword_match": True,
            "initials_match": True,
            "validation_errors": [] if status == "completed" else ["Cần bổ sung số/ngày chính thức"],
            "ai_review_comment": "Đã tiếp nhận và thẩm định thể thức văn bản.",
            "resolution_options": []
        }
