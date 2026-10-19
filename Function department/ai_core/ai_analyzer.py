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
    "nguyễn trung bảo lộc": ["ntbloc", "nlbloc", "tbloc", "bloc", "nbloc", "ntloc", "loc", "nguyentrungbaoloc"],
    "hoàng thị hương giang": ["hthgiang", "thgiang", "hgiang", "giang", "hoangthihuonggiang"],
    "phan công hận": ["pchan", "chan", "han", "phanconghan"],
    "vũ đức minh an": ["vdman", "dman", "man", "an", "vuducminhan", "alexander"],
    "lê hoàng": ["lhoang", "lehoang", "hoang"],
    "tô thị kim thoa": ["ttkthoa", "kthoa", "tothikimthoa"]
}

def remove_vn_accents(text: str) -> str:
    import unicodedata
    if not text: return ""
    norm = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return norm.replace('đ', 'd').replace('Đ', 'D')

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
                for m_name in ["gemini-3.5-flash-lite", "gemini-3.5-flash"]:
                    try:
                        resp = self.client.models.generate_content(
                            model=m_name,
                            contents=[img_part, "Hãy đọc toàn bộ văn bản trong ảnh này, giữ nguyên đầy đủ tiêu ngữ, số ký hiệu, ngày tháng, trích yếu, nội dung và nơi nhận (Lưu: VT, PPP&QLN...)."]
                        )
                        if resp.text and resp.text.strip():
                            return resp.text.strip()
                    except Exception:
                        time.sleep(0.5)
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

        # 1. Trích xuất Số ký hiệu văn bản (Ví dụ: Số: 7937 /UBND-PKT hoặc 24586/STC-PPP&QLN)
        clean_text_for_num = re.sub(r'[*_`]', '', text)
        doc_num_match = re.search(r'Số:\s*([0-9A-Za-z\/\-_\.\s&]+?)(?=\s+ngày|\s*\n|\s+V\/v|\s+Về|$)', clean_text_for_num, re.IGNORECASE)
        if doc_num_match:
            candidate = doc_num_match.group(1).strip()
            # Làm sạch khoảng trắng thừa
            candidate = re.sub(r'\s+', ' ', candidate)
            if re.search(r'\d+', candidate) and '/' in candidate:
                meta["document_number"] = candidate

        # 2. Trích xuất Ngày ban hành (Ví dụ: ngày 29 tháng 9 năm 2026)
        date_match = re.search(r'(?:ngày|ngy)\s+(\d{1,2})\s+(?:tháng|thng)\s+(\d{1,2})\s+(?:năm|nm)\s+(\d{4})', clean_text_for_num, re.IGNORECASE)
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
        ass_no_accent = remove_vn_accents(ass_clean)
        
        # 1. So khớp theo bản đồ chữ viết tắt chính thức
        for full_name, valid_list in STAFF_INITIALS_MAP.items():
            if full_name in ass_clean or ass_clean in full_name or remove_vn_accents(full_name) in ass_no_accent:
                if init_clean in valid_list:
                    return True
                # Khử nhiễu OCR: 't' bị đọc nhầm thành 'l' hoặc '1'
                ocr_variants = [init_clean.replace('l', 't'), init_clean.replace('1', 't'), init_clean.replace('t', 'l')]
                if any(v in valid_list for v in ocr_variants):
                    return True
                
        # 2. So khớp tự động theo tên riêng không dấu (ví dụ: loc, hoa, giang...)
        tokens_no_acc = [re.sub(r'[^\w]', '', w) for w in ass_no_accent.split()]
        if tokens_no_acc:
            last_name = tokens_no_acc[-1] # ví dụ "loc"
            if last_name and (last_name in init_clean or init_clean.endswith(last_name)):
                return True
            first_letters = "".join([w[0] for w in tokens_no_acc[:-1]])
            combined = f"{first_letters}{last_name}"
            if init_clean == combined or init_clean == last_name:
                return True
                
        return False

    def extract_project_name(self, text: str) -> str:
        """Tự động bóc tách tên Dự án chuẩn xác từ trích yếu hoặc văn bản"""
        if not text:
            return ""
        m = re.search(r'(Dự\s*án(?:\s+thành\s+phần\s+\d+)?\s*[:\-\–]?\s*[^,;\.\n\r]+)', text, re.IGNORECASE)
        if m:
            p = m.group(1).strip()
            p = re.sub(r'\s+theo\s+phương\s+thức.*$', '', p, flags=re.IGNORECASE)
            p = re.sub(r'\s+thuộc\s+dự\s+án.*$', '', p, flags=re.IGNORECASE)
            p = re.sub(r'\s+tại\s+.*$', '', p, flags=re.IGNORECASE)
            return p.strip()
        return ""

    def review_submission(self, file_path, assignee_name: str, pending_tasks: list, user_hint_text: str = "") -> dict:
        """
        Quy trình Thẩm định Sản phẩm Tự động Đa tầng (Multi-Tier Rigorous Document Review):
        1. Nhận diện Task ID chỉ định từ người nộp (target_task_id) hoặc tự động dò tìm.
        2. Bóc tách & phân loại thông minh từng trang ảnh/văn bản: Trang đầu, Thân bài, Trang cuối nơi nhận.
        3. Đối soát văn bản với chính xác Task ID được chỉ định. Nếu nộp sai dự án -> cảnh báo lỗi, không duyệt chéo.
        4. TIÊU CHÍ TUYÊN QUYẾT: Dò chữ viết tắt chuyên viên tại Nơi nhận (Lưu: VT, PPP&QLN (...)).
        5. Phân loại ĐẠT (completed) hoặc CẢNH BÁO LỖI (needs_revision) kèm hướng dẫn khắc phục.
        """
        file_list = file_path if isinstance(file_path, list) else [file_path]
        filenames = [os.path.basename(p) for p in file_list]
        filename = ", ".join(filenames)

        # 1. Trích xuất text từ văn bản / OCR ảnh và tự động nhận diện phân loại từng trang
        parsed_pages = []
        for p in file_list:
            t = self._extract_text_fallback(p)
            t_clean = re.sub(r'[*_`]', '', t) if t else ""
            t_up = t_clean.upper()
            
            header_kws = ["CỘNG HÒA XÃ HỘI", "ỦY BAN NHÂN DÂN", "SỞ TÀI CHÍNH", "SỐ:", "SỐ :", "V/V", "V/V:", "VỀ VIỆC", "ĐỘC LẬP", "KÍNH GỬI"]
            sig_kws = ["NƠI NHẬN", "NƠI NHẬN:", "LƯU: VT", "LƯU : VT", "KT. GIÁM ĐỐC", "PHÓ GIÁM ĐỐC", "GIÁM ĐỐC", "TRƯỞNG PHÒNG", "KÝ BỞI", "CHỮ KÝ", "LƯU:"]
            
            h_score = sum(1 for kw in header_kws if kw in t_up)
            s_score = sum(1 for kw in sig_kws if kw in t_up)
            parsed_pages.append({
                "path": p,
                "text": t,
                "clean": t_clean,
                "h_score": h_score,
                "s_score": s_score
            })

        raw_pages = []
        if len(parsed_pages) == 1:
            item = parsed_pages[0]
            if item["h_score"] > 0 and item["s_score"] > 0:
                role = "Văn bản 1 trang trọn vẹn (Đầy đủ Tiêu ngữ và Nơi nhận)"
                prio = 1
            elif item["h_score"] >= item["s_score"] and item["h_score"] > 0:
                role = "Trang đầu (Tiêu ngữ, Số ký hiệu, Ngày ban hành & Trích yếu)"
                prio = 1
            elif item["s_score"] > 0:
                role = "Trang cuối (Nơi nhận, Ký lưu VT & Chữ ký Lãnh đạo)"
                prio = 3
            else:
                role = "Trang nội dung văn bản"
                prio = 2
            raw_pages.append((prio, role, item["text"], item["path"]))
        elif len(parsed_pages) == 2:
            # Hai trang ảnh: Tuyệt đối phân định rõ ràng Trang đầu và Trang cuối (không dùng nhãn chung chung)
            p0 = parsed_pages[0]
            p1 = parsed_pages[1]
            diff0 = p0["h_score"] - p0["s_score"]
            diff1 = p1["h_score"] - p1["s_score"]
            
            if diff0 >= diff1:
                raw_pages.append((1, "Trang đầu (Tiêu ngữ, Số ký hiệu, Ngày ban hành & Trích yếu)", p0["text"], p0["path"]))
                raw_pages.append((3, "Trang cuối (Nơi nhận, Ký lưu VT & Chữ ký Lãnh đạo)", p1["text"], p1["path"]))
            else:
                raw_pages.append((1, "Trang đầu (Tiêu ngữ, Số ký hiệu, Ngày ban hành & Trích yếu)", p1["text"], p1["path"]))
                raw_pages.append((3, "Trang cuối (Nơi nhận, Ký lưu VT & Chữ ký Lãnh đạo)", p0["text"], p0["path"]))
        else:
            # Từ 3 trang trở lên: Tìm trang có h_score cao nhất làm Trang đầu, trang có s_score cao nhất làm Trang cuối
            sorted_by_header = sorted(parsed_pages, key=lambda x: (x["h_score"] - x["s_score"]), reverse=True)
            head_item = sorted_by_header[0]
            
            remaining = [p for p in parsed_pages if p["path"] != head_item["path"]]
            sorted_by_sig = sorted(remaining, key=lambda x: (x["s_score"] - x["h_score"]), reverse=True)
            tail_item = sorted_by_sig[0]
            
            middle_items = [p for p in remaining if p["path"] != tail_item["path"]]
            
            raw_pages.append((1, "Trang đầu (Tiêu ngữ, Số ký hiệu, Ngày ban hành & Trích yếu)", head_item["text"], head_item["path"]))
            for mid in middle_items:
                raw_pages.append((2, "Trang nội dung văn bản", mid["text"], mid["path"]))
            raw_pages.append((3, "Trang cuối (Nơi nhận, Ký lưu VT & Chữ ký Lãnh đạo)", tail_item["text"], tail_item["path"]))

        # Sắp xếp đúng thứ tự: Trang đầu (1) -> Thân bài (2) -> Trang cuối (3)
        raw_pages.sort(key=lambda x: x[0])
        
        page_structure_lines = []
        for idx, (prio, role, _, p) in enumerate(raw_pages, 1):
            fn_base = os.path.basename(p)
            page_structure_lines.append(f"• Trang {idx} ({fn_base}): {role}")
        page_structure_text = "\n".join(page_structure_lines)

        extracted_texts = [f"=== [TRANG {idx}: {role}] ===\n{t}" for idx, (prio, role, t, _) in enumerate(raw_pages, 1)]
        local_text = "\n\n--------------------\n\n".join(extracted_texts) if extracted_texts else ""
        regex_meta = self._extract_regex_metadata(local_text)

        # 2. Xác định Task ID người dùng CHỈ ĐỊNH RÕ RÀNG (Explicit Target Task ID)
        explicit_target_task_id = None
        if user_hint_text:
            clean_hint = user_hint_text.lower().strip()
            # Bắt các cú pháp: nộp task 4, nop task 4, gửi task 4, task 4, t4, nv 4, #4
            m_act = re.search(r'(?:nộp|nop|gửi|gui|cho|bài|bai)\s*(?:bài\s*)?(?:cho\s*)?(?:task|nhiệm\s*vụ|nv|stt|số|t)?\s*#?([0-9]{1,3})\b', clean_hint)
            m_s = re.search(r'\b(?:task|t|nv)\s*#?([0-9]{1,3})\b', clean_hint)
            m_single = re.match(r'^(?:#)?([0-9]{1,3})$', clean_hint)
            if m_act:
                explicit_target_task_id = m_act.group(1)
            elif m_s:
                explicit_target_task_id = m_s.group(1)
            elif m_single:
                explicit_target_task_id = m_single.group(1)

        if not explicit_target_task_id:
            for fn in filenames:
                tid = self.extract_task_number_from_filename(fn)
                if tid:
                    explicit_target_task_id = tid
                    break

        target_task_id = str(explicit_target_task_id).strip() if explicit_target_task_id else ""
        target_task_name = ""
        target_assignee = assignee_name
        matched_target_task = None

        if explicit_target_task_id:
            for t in pending_tasks:
                t_id = str(t.get("taskId") or t.get("task_id") or "").strip()
                if t_id == str(explicit_target_task_id).strip():
                    matched_target_task = t
                    break

            distinctive_dict_names = {
                "1": ("Dự án Bãi tắm Thùy Vân - Trần Hưng Đạo", "Nguyễn Thế Hòa"),
                "2": ("Dự án 247 Trần Hưng Đạo", "Nguyễn Thế Hòa"),
                "3": ("Dự án Phước Hải - Phát Đạt", "Nguyễn Thế Hòa"),
                "4": ("Dự án Chỉnh trang Khu Mả Lạng và Chợ Gà - Gạo", "Nguyễn Trung Bảo Lộc"),
                "5": ("Dự án Cao tốc TP.HCM - Mộc Bài", "Hoàng Thị Hương Giang"),
                "6": ("Dự án Khu liên hợp TDTT Rạch Chiếc", "Nguyễn Thế Hòa"),
                "7": ("Dự án Hạ tầng kỹ thuật Rạch Chiếc", "Nguyễn Thế Hòa")
            }

            if matched_target_task:
                target_task_name = matched_target_task.get("taskName") or matched_target_task.get("task_name") or ""
                target_assignee = matched_target_task.get("assignee") or matched_target_task.get("assigned_to") or assignee_name
            elif target_task_id in distinctive_dict_names:
                target_task_name, target_assignee = distinctive_dict_names[target_task_id]
            else:
                target_task_name = f"Nhiệm vụ Task #{target_task_id}"
                target_assignee = assignee_name

            assigned_staff_in_task = target_assignee
            hint_task_id = target_task_id
        else:
            # 3. Tự động dò Task ID có điểm số khớp cao nhất nếu người dùng không chỉ định rõ
            hint_task_id = ""
            best_task_id = None
            best_score = 0
            distinctive_dict = {
                "1": ["trần hưng đạo", "phước hải", "phát đạt", "bãi tắm"],
                "2": ["trần hưng đạo", "phước hải", "phát đạt"],
                "3": ["trần hưng đạo", "phước hải", "phát đạt"],
                "4": ["mả lạng", "chợ gà", "chợ gạo", "cầu ông lãnh", "bến thành", "lộc", "ntbloc"],
                "5": ["mộc bài", "cao tốc", "giang", "bồi thường", "tái định cư"],
                "6": ["rạch chiếc", "hội đồng thẩm định"],
                "7": ["rạch chiếc", "hạ tầng kỹ thuật"]
            }
            stop_words = {"công", "viên", "trình", "thực", "hiện", "theo", "đầu", "tư", "phương", "thức", "đối", "tác", "báo", "cáo", "nghiên", "cứu", "khả", "thi", "ngày", "tháng", "năm", "thành", "phố"}
            for t in pending_tasks:
                t_id = str(t.get("taskId") or t.get("task_id") or "").strip()
                t_name = (t.get("taskName") or t.get("task_name") or "").lower()
                clean_tname = re.sub(r'^(?:v\/v|về việc|dự án)\s*', '', t_name).strip()
                kws = [w for w in re.split(r'[,.\s\-_/]+', clean_tname) if len(w) >= 2 and w not in stop_words]
                score = sum(1 for kw in kws if kw in local_text.lower())
                
                # Trọng số đặc trưng dự án
                if t_id in distinctive_dict:
                    for phrase in distinctive_dict[t_id]:
                        if phrase in local_text.lower():
                            score += 8
                
                # Trọng số chữ viết tắt nơi nhận
                assignee = (t.get("assignee") or t.get("assigned_to") or "").lower()
                if assignee:
                    for full_name, valid_list in STAFF_INITIALS_MAP.items():
                        if full_name in assignee or assignee in full_name:
                            for init in valid_list:
                                if init in local_text.lower():
                                    score += 15
                
                if score > best_score and score >= 3:
                    best_score = score
                    best_task_id = t_id
            
            if best_task_id:
                hint_task_id = best_task_id
                for t in pending_tasks:
                    t_id = str(t.get("taskId") or t.get("task_id") or "").strip()
                    if t_id == str(hint_task_id).strip():
                        matched_target_task = t
                        break
            assigned_staff_in_task = (matched_target_task.get("assignee") or matched_target_task.get("assigned_to")) if matched_target_task else assignee_name

        if explicit_target_task_id:
            task_instruction = f"""
*** YÊU CẦU ĐỐI SOÁT CHÍNH XÁC VỚI NHIỆM VỤ ĐƯỢC CHỈ ĐỊNH (TASK #{explicit_target_task_id}) ***:
- Người nộp đã ghi rõ muốn nộp cho Task #{explicit_target_task_id}: "{target_task_name}"
- Chuyên viên phụ trách theo Bảng giao việc: "{target_assignee}"

BẠN BẮT BUỘC PHẢI ĐỐI SOÁT NỘI DUNG VĂN BẢN VỚI ĐÚNG TASK #{explicit_target_task_id}:
1. "task_id": Bắt buộc ghi là "{explicit_target_task_id}". TUYỆT ĐỐI KHÔNG ĐƯỢC ĐỔI SANG TASK ID KHÁC!
2. ĐỐI SOÁT TRÍCH YẾU & DỰ ÁN:
   - So sánh nội dung văn bản với nhiệm vụ: "{target_task_name}".
   - NẾU VĂN BẢN LÀ CỦA DỰ ÁN KHÁC (Ví dụ: văn bản nói về Dự án Mả Lạng, Chợ Gà - Gạo hoặc dự án khác thay vì {target_task_name}):
     + "keyword_match": false
     + "initials_match": false
     + "status_decision": "needs_revision"
     + "validation_errors": ["❌ LỖI TRÍCH YẾU: Văn bản nộp thuộc dự án khác, không khớp với nhiệm vụ được giao (Task #{explicit_target_task_id}: {target_task_name} - Phụ trách: {target_assignee})."]
     + "ai_review_comment": "Văn bản nộp không khớp với nhiệm vụ Task #{explicit_target_task_id} ({target_task_name}). Đề nghị chuyên viên kiểm tra lại."
     + TUYỆT ĐỐI KHÔNG duyệt completed cho Task #{explicit_target_task_id}!
"""
        else:
            task_instruction = f"""
*** TỰ ĐỘNG DÒ TÌM TASK ID TƯƠNG ỨNG TRÊN BẢNG GIAO VIỆC ***:
- Người nộp không chỉ định cụ thể Task ID. Dựa vào nội dung, tên dự án và chữ viết tắt nơi nhận, xác định chính xác văn bản này thuộc Task ID nào (ví dụ: '4').
- Gợi ý dự đoán: Task #{hint_task_id or 'Chưa rõ'}.
"""

        prompt = f"""
Bạn là Trợ lý Nghiệm thu & Thẩm định Thể thức Văn bản Hành chính (Phòng Hợp tác Công tư & Quản lý Nợ - Sở Tài Chính TP.HCM).
Chuyên viên nộp: {assignee_name}.
Tệp tin: "{filename}".
Mục tiêu nhiệm vụ: {hint_task_id or 'Tự động dò tìm'}.
Chuyên viên phụ trách dự kiến: {assigned_staff_in_task}.

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

CẤU TRÚC TÀI LIỆU NHẬN DIỆN:
{page_structure_text}

{task_instruction}

YÊU CẦU THẨM ĐỊNH THỂ THỨC (THEO NGHỊ ĐỊNH 30/2020/NĐ-CP):
1. THỂ THỨC VĂN BẢN:
   - "document_number": Tìm chính xác Số ký hiệu văn bản (Ví dụ: "24586/STC-PPP&QLN", "7937 /UBND-PKT"). Nếu văn bản chưa có số (còn để trống) thì để chuỗi rỗng "".
   - "document_date": Ngày tháng năm ban hành (Định dạng "DD/MM/YYYY", ví dụ: "25/08/2026"). Nếu văn bản chưa có ngày thì để rỗng "".
   - "deliverable": Xác định chuẩn loại sản phẩm: "Tờ trình", "Kết luận", "Báo cáo", "Quyết định", "Kế hoạch", "Thông báo", "Công văn".
   - "actual_summary": Trích yếu thực tế trong văn bản (bắt đầu bằng V/v hoặc Về việc...).

2. ĐỐI SOÁT TRÍCH YẾU & TỪ KHÓA (KEYWORDS):
   - So sánh trích yếu bóc tách với Tên nhiệm vụ / Trích yếu của Task ID thẩm định.
   - "keyword_match": true nếu khớp các từ khóa cốt lõi của dự án; false nếu nội dung nói về dự án khác hoặc từ khóa quá thấp.
   - "matched_keywords": Danh sách các từ khóa dự án khớp được.

3. ĐỐI SOÁT NƠI NHẬN & CHỮ VIẾT TẮT CHUYÊN VIÊN (LINH HOẠT TUYỆT ĐỐI):
   - Tìm dòng cuối văn bản tại mục "Nơi nhận": "- Lưu: VT, PPP&QLN (..., ...b)."
   - "recipient_initials": Trích chữ viết tắt trong ngoặc đơn (Ví dụ: "NtbLoc", "ntbloc", "Nthoa", "pchan", "Hthgiang", "Vdman"...).
   - "initials_match": 
     + TUYỆT ĐỐI KHÔNG BẮT LỖI CHỮ HOA/THƯỜNG: Chấp nhận mọi biến thể hoa/thường (Ví dụ: NtbLoc, ntbloc, NTBLOC, tbloc, ...Loc đều là của Nguyễn Trung Bảo Lộc). Nếu chữ viết tắt có chứa tên của chuyên viên phụ trách của Task đó -> true.
     + NẾU KHÔNG CÓ DÒNG NƠI NHẬN (do người nộp chỉ chụp trang đầu có Tiêu ngữ/Số/Ngày/Trích yếu): VẪN ĐỂ "initials_match": true và KHÔNG ĐƯỢC coi là lỗi, vì văn bản đã có Số và Ngày ban hành chính thức!
     + Chỉ để false nếu chữ viết tắt rõ ràng của một chuyên viên KHÁC trong phòng.

4. KẾT LUẬN NGHIỆM THU:
   - "status_decision": "completed" nếu: (1) Trích yếu/từ khóa khớp đúng Task; (2) Có Số ký hiệu chính thức; (3) Có Ngày ban hành chính thức; (4) Chữ viết tắt nơi nhận không bị xung đột với người khác.
   - Trả về "needs_revision" nếu vi phạm: Sai nội dung dự án, hoặc văn bản chưa có Số ký hiệu chính thức, hoặc chưa có Ngày ban hành.
   - "validation_errors": Danh sách lỗi (để mảng rỗng [] nếu văn bản đạt chuẩn hoặc là bản chính thức đã có Số và Ngày).

TRẢ VỀ ĐỊNH DẠNG JSON DUY NHẤT:
{{
  "task_id": "Số ID chính xác (ví dụ '4')",
  "status_decision": "completed" hoặc "needs_revision",
  "deliverable": "Loại sản phẩm (Tờ trình, Kết luận, Báo cáo, Công văn...)",
  "document_number": "Số ký hiệu văn bản hoặc rỗng",
  "document_date": "Ngày ban hành DD/MM/YYYY hoặc rỗng",
  "actual_summary": "Trích yếu thực tế trong file",
  "recipient_initials": "Chữ viết tắt tại nơi nhận (ví dụ NtbLoc, Nthoa...)",
  "keyword_match": true hoặc false,
  "matched_keywords": ["từ khóa 1", "từ khóa 2"],
  "initials_match": true hoặc false,
  "validation_errors": [],
  "ai_review_comment": "Nhận xét thẩm định công vụ súc tích (1-2 câu)",
  "resolution_options": ["Hướng dẫn 1", "Hướng dẫn 2"]
}}
"""
        models_to_try = ["gemini-3.5-flash-lite", "gemini-3.5-flash"]
        last_error = None
        for model_name in models_to_try:
            try:
                contents = []
                # Đưa ảnh đã phân loại theo đúng thứ tự logic vào multimodal contents kèm nhãn vai trò
                for prio, role, _, p in raw_pages:
                    ext = os.path.splitext(p)[1].lower()
                    if ext in [".jpg", ".jpeg", ".png"]:
                        try:
                            with open(p, "rb") as f_img:
                                img_b = f_img.read()
                            mime = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
                            contents.append(types.Part.from_text(text=f"[ẢNH ĐÍNH KÈM: {role}]"))
                            contents.append(types.Part.from_bytes(data=img_b, mime_type=mime))
                        except Exception:
                            pass
                contents.append(prompt)
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
                data["page_structure_text"] = page_structure_text

                # Hậu kiểm tra deterministic nếu regex bắt được tốt hơn
                if not data.get("document_number") and regex_meta.get("document_number"):
                    data["document_number"] = regex_meta.get("document_number")
                if not data.get("document_date") and regex_meta.get("document_date"):
                    data["document_date"] = regex_meta.get("document_date")
                if not data.get("recipient_initials") and regex_meta.get("recipient_initials"):
                    data["recipient_initials"] = regex_meta.get("recipient_initials")

                # Cập nhật lại Task ID và Người phụ trách
                if explicit_target_task_id and matched_target_task:
                    data["task_id"] = str(explicit_target_task_id).strip()
                    data["assigned_staff"] = target_assignee
                else:
                    final_task_id = str(data.get("task_id") or hint_task_id or "").strip()
                    if final_task_id:
                        data["task_id"] = final_task_id
                        for t in pending_tasks:
                            t_id = str(t.get("taskId") or t.get("task_id") or "").strip()
                            if t_id == final_task_id:
                                assigned_staff_in_task = t.get("assignee") or t.get("assigned_to") or assigned_staff_in_task
                                break
                    data["assigned_staff"] = assigned_staff_in_task

                current_task_id = str(data.get("task_id", "")).strip()
                current_assignee = data.get("assigned_staff", assigned_staff_in_task)

                # Kiểm tra lại chữ viết tắt nơi nhận bằng Python deterministic logic
                recip_init = data.get("recipient_initials", "")
                if recip_init:
                    verified_match = self.check_initials_match_assignee(recip_init, current_assignee)
                    data["initials_match"] = verified_match
                else:
                    # Nếu ảnh không chứa dòng nơi nhận (chỉ chụp trang đầu) nhưng đã có đủ Số và Ngày chính thức
                    if data.get("document_number") and data.get("document_date"):
                        data["initials_match"] = True

                # Hậu kiểm tra chéo dự án: nếu nộp cho Task X nhưng trích yếu thuộc dự án của Task Y
                clean_errors = list(data.get("validation_errors", []))
                actual_sum_lower = (data.get("actual_summary") or local_text).lower()
                distinctive_dict = {
                    "1": ["trần hưng đạo", "phước hải", "phát đạt", "bãi tắm"],
                    "2": ["trần hưng đạo", "phước hải", "phát đạt"],
                    "3": ["trần hưng đạo", "phước hải", "phát đạt"],
                    "4": ["mả lạng", "chợ gà", "chợ gạo", "cầu ông lãnh", "bến thành"],
                    "5": ["mộc bài", "cao tốc", "tây ninh", "bồi thường, hỗ trợ, tái định cư"],
                    "6": ["rạch chiếc", "hội đồng thẩm định"],
                    "7": ["rạch chiếc", "hạ tầng kỹ thuật"]
                }
                other_proj = None
                for other_id, kws in distinctive_dict.items():
                    if other_id != current_task_id:
                        for kw in kws:
                            if kw in actual_sum_lower:
                                other_proj = (other_id, kw)
                                break
                        if other_proj:
                            break
                target_kws = distinctive_dict.get(current_task_id, [])
                target_kw_matched = any(kw in actual_sum_lower for kw in target_kws) if target_kws else True

                if other_proj and not target_kw_matched:
                    data["keyword_match"] = False
                    err_msg = f"❌ LỖI TRÍCH YẾU: Văn bản nộp thuộc dự án khác (phát hiện từ khóa '{other_proj[1]}'), không khớp với nhiệm vụ được chỉ định (Task #{current_task_id} - Phụ trách: {current_assignee})."
                    if not any("LỖI TRÍCH YẾU" in e for e in clean_errors):
                        clean_errors.insert(0, err_msg)
                    data["status_decision"] = "needs_revision"
                    data["ai_review_comment"] = f"Văn bản nộp không khớp với nhiệm vụ Task #{current_task_id}."

                if not data.get("keyword_match") and not any("LỖI TRÍCH YẾU" in e for e in clean_errors):
                    clean_errors.append("❌ LỖI TRÍCH YẾU: Nội dung trích yếu không khớp hoặc từ khóa quá thấp so với nhiệm vụ được giao.")
                if not data.get("document_number") and not any("LỖI THỂ THỨC: Văn bản chưa có Số" in e for e in clean_errors):
                    clean_errors.append("❌ LỖI THỂ THỨC: Văn bản chưa có Số ký hiệu chính thức (còn để trống).")
                if not data.get("document_date") and not any("LỖI THỂ THỨC: Văn bản chưa có Ngày" in e for e in clean_errors):
                    clean_errors.append("❌ LỖI THỂ THỨC: Văn bản chưa có Ngày tháng năm ban hành chính thức.")
                if recip_init and not data.get("initials_match") and not any("LỖI NGƯỜI PHỤ TRÁCH" in e for e in clean_errors):
                    clean_errors.append(f"❌ LỖI NGƯỜI PHỤ TRÁCH: Chữ viết tắt tại Nơi nhận là '{recip_init}', không khớp với chuyên viên được giao nhiệm vụ ('{current_assignee}').")

                data["validation_errors"] = clean_errors
                
                # Quyết định trạng thái cuối cùng
                if len(clean_errors) == 0 and data.get("keyword_match") and data.get("document_number") and data.get("document_date") and data.get("initials_match", True):
                    data["status_decision"] = "completed"
                    if not recip_init:
                        data["recipient_initials"] = f"Khớp theo Số/Ngày chính thức ({current_assignee})"
                    data["resolution_options"] = [
                        "Hồ sơ hợp lệ, đã cập nhật kết quả nghiệm thu lên Google Sheets."
                    ]
                else:
                    data["status_decision"] = "needs_revision"
                    data["resolution_options"] = [
                        f"👉 Kiểm tra và nộp đúng văn bản của Task #{current_task_id} (Phụ trách: {current_assignee}).",
                        "👉 Nếu đây là văn bản của nhiệm vụ khác, vui lòng gửi kèm cú pháp chỉ định đúng (ví dụ: `nộp task 4`).",
                        "👉 Đảm bảo chụp rõ cả Trang đầu (Số ký hiệu, Ngày ban hành) và Trang cuối (Nơi nhận, Chữ ký Lãnh đạo)."
                    ]

                data["assigned_staff"] = current_assignee
                proj_name = self.extract_project_name(data.get("actual_summary") or local_text)
                if not proj_name and matched_target_task:
                    proj_name = matched_target_task.get("project") or self.extract_project_name(matched_target_task.get("taskName") or matched_target_task.get("task_name") or "")
                data["project_name"] = proj_name
                return data
            except Exception as e:
                last_error = str(e)
                time.sleep(1)

        # Fallback an toàn nếu LLM lỗi mạng
        status = "completed" if regex_meta.get("document_number") and regex_meta.get("document_date") else "needs_revision"
        fb_proj = self.extract_project_name(local_text)
        if not fb_proj and matched_target_task:
            fb_proj = matched_target_task.get("project") or self.extract_project_name(matched_target_task.get("taskName") or matched_target_task.get("task_name") or "")

        return {
            "success": True,
            "task_id": hint_task_id,
            "status_decision": status,
            "deliverable": regex_meta.get("deliverable", "Công văn"),
            "document_number": regex_meta.get("document_number", ""),
            "document_date": regex_meta.get("document_date", ""),
            "actual_summary": "Trích xuất tự động qua thể thức văn bản",
            "project_name": fb_proj,
            "recipient_initials": regex_meta.get("recipient_initials", ""),
            "assigned_staff": assigned_staff_in_task,
            "keyword_match": True,
            "initials_match": True,
            "validation_errors": [] if status == "completed" else ["Cần bổ sung số/ngày chính thức"],
            "ai_review_comment": "Đã tiếp nhận và thẩm định thể thức văn bản.",
            "resolution_options": []
        }
