import urllib.request
import csv
import io
import requests
import json
import os
import sys
import openpyxl
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()

SHEET_ID = "1RRb0PJB2EJv92SPHZ3_ahv2YYEn9bxjfC8JBPpTkuG4"
DEFAULT_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycby2MGloAdgCZYFZ6QkEmfVBMnIOWZ7ZdTZqREIHKLurjbSCB66ohuLnBoReUq4MWvc/exec"
WEBHOOK_URL = os.getenv("GOOGLE_SHEETS_WEBHOOK_URL") or DEFAULT_WEBHOOK_URL
# Tự động xuất CSV trực tiếp từ trang tính Task_Tracker chính thức (không phụ thuộc GID tĩnh tránh lỗi 400 khi đổi tab)
CSV_EXPORT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

session = requests.Session()

class TaskManager:
    def __init__(self, excel_path: str = "Zalo_Task_Tracker_Template.xlsx", webhook_url: str = None):
        self.excel_path = excel_path
        self.webhook_url = webhook_url or WEBHOOK_URL or DEFAULT_WEBHOOK_URL

    def get_all_tasks_from_sheet(self) -> list:
        """Đọc tức thì dữ liệu từ Google Sheets thời gian thực, tự động thích ứng cấu trúc 13 cột hoặc 15 cột."""
        # 1. Thử tải trực tiếp CSV từ Google Sheets (tốc độ cao và dữ liệu mới nhất)
        try:
            req = urllib.request.Request(CSV_EXPORT_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                content = resp.read().decode("utf-8")
                reader = csv.reader(io.StringIO(content))
                rows = list(reader)
                
                tasks = []
                if len(rows) > 6:
                    header_row = [c.strip().lower() for c in rows[6]]
                    has_project_col = "dự án" in header_row or (len(header_row) > 2 and "dự án" in header_row[2])
                    
                    for i in range(7, len(rows)):
                        row = rows[i]
                        if len(row) > 0 and row[0].strip():
                            if has_project_col:
                                # Cấu trúc 15 cột chuẩn
                                tasks.append({
                                    "taskId": row[0].strip(),
                                    "taskName": row[1].strip() if len(row) > 1 else "",
                                    "project": row[2].strip() if len(row) > 2 else "",
                                    "assignee": row[3].strip() if len(row) > 3 else "Chưa gán",
                                    "leader": row[4].strip() if len(row) > 4 else "",
                                    "deadline": row[5].strip() if len(row) > 5 else "",
                                    "priority": row[6].strip() if len(row) > 6 else "Bình thường",
                                    "status": row[7].strip() if len(row) > 7 else "Chưa bắt đầu",
                                    "deliverable": row[8].strip() if len(row) > 8 else "",
                                    "trichYeu": row[9].strip() if len(row) > 9 else "",
                                    "soKyHieu": row[10].strip() if len(row) > 10 else "",
                                    "ngayBanHanh": row[11].strip() if len(row) > 11 else "",
                                    "aiSummary": row[12].strip() if len(row) > 12 else "",
                                    "submittedAt": row[13].strip() if len(row) > 13 else "",
                                    "fileName": row[14].strip() if len(row) > 14 else ""
                                })
                            else:
                                # Cấu trúc 13 cột cũ
                                tasks.append({
                                    "taskId": row[0].strip(),
                                    "taskName": row[1].strip() if len(row) > 1 else "",
                                    "project": "",
                                    "assignee": row[2].strip() if len(row) > 2 else "Chưa gán",
                                    "leader": "",
                                    "deadline": row[3].strip() if len(row) > 3 else "",
                                    "priority": row[4].strip() if len(row) > 4 else "Bình thường",
                                    "status": row[5].strip() if len(row) > 5 else "Chưa bắt đầu",
                                    "deliverable": row[6].strip() if len(row) > 6 else "",
                                    "trichYeu": row[7].strip() if len(row) > 7 else "",
                                    "soKyHieu": row[8].strip() if len(row) > 8 else "",
                                    "ngayBanHanh": row[9].strip() if len(row) > 9 else "",
                                    "aiSummary": row[10].strip() if len(row) > 10 else "",
                                    "submittedAt": row[11].strip() if len(row) > 11 else "",
                                    "fileName": row[12].strip() if len(row) > 12 else ""
                                })
                if tasks:
                    return tasks
        except Exception as e_csv:
            sys.stderr.write(f"[WARN] Tải CSV Google Sheets lỗi: {e_csv}. Đang thử qua Webhook doGet...\n")

        # 2. Fallback thứ 2: Đọc qua Google Apps Script Webhook doGet
        webhook_url = self.webhook_url or os.getenv("GOOGLE_SHEETS_WEBHOOK_URL") or DEFAULT_WEBHOOK_URL
        if webhook_url:
            try:
                res = requests.get(webhook_url, timeout=12)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("success") and data.get("data"):
                        return data["data"]
            except Exception as e_hook:
                sys.stderr.write(f"[WARN] Đọc qua Webhook doGet thất bại: {e_hook}.\n")
        
        # 3. Fallback cuối cùng: File Excel lưu đệm
        return self._get_all_tasks_from_local_excel()

    def get_grouped_pending_tasks(self) -> dict:
        """
        Lấy danh sách các task chưa hoàn thành và GOM NHÓM THEO CHUYÊN VIÊN.
        Kèm tính toán số ngày còn lại và mức độ khẩn cấp:
        - 'overdue': Đã quá hạn 🔴
        - 'due_soon': Sắp đến hạn (hôm nay hoặc <= 2 ngày) ⚠️
        - 'normal': Còn xa hạn ⏳
        """
        tasks = self.get_all_tasks_from_sheet()
        today = date.today()
        
        grouped = {}
        for t in tasks:
            status = t.get("status", "")
            if status == "Đã hoàn thành":
                continue

            assignee = t.get("assignee", "Chưa phân công")
            deadline_str = t.get("deadline", "").strip()
            
            urgency_status = "normal"
            days_diff_text = ""
            
            # Phân tích ngày deadline
            if deadline_str:
                try:
                    # Hỗ trợ cả YYYY-MM-DD và DD/MM/YYYY
                    if "-" in deadline_str:
                        d_parts = [int(p) for p in deadline_str.split("-")]
                        if len(d_parts) == 3:
                            deadline_date = date(d_parts[0], d_parts[1], d_parts[2])
                    elif "/" in deadline_str:
                        d_parts = [int(p) for p in deadline_str.split("/")]
                        if len(d_parts) == 3:
                            deadline_date = date(d_parts[2], d_parts[1], d_parts[0])
                    else:
                        deadline_date = None
                        
                    if deadline_date:
                        delta = (deadline_date - today).days
                        if delta < 0:
                            urgency_status = "overdue"
                            days_diff_text = f"🔴 ĐÃ QUÁ HẠN {abs(delta)} ngày!"
                        elif delta == 0:
                            urgency_status = "due_today"
                            days_diff_text = "⚠️ HÔM NAY HẾT HẠN!"
                        elif delta <= 2:
                            urgency_status = "due_soon"
                            days_diff_text = f"⚠️ SẮP ĐẾN HẠN - Còn {delta} ngày"
                        else:
                            urgency_status = "normal"
                            days_diff_text = f"Còn {delta} ngày"
                except Exception:
                    days_diff_text = ""

            task_info = {
                "task_id": t.get("taskId"),
                "task_name": t.get("taskName"),
                "deadline": deadline_str,
                "days_diff_text": days_diff_text,
                "urgency_status": urgency_status,
                "priority": t.get("priority", "Bình thường"),
                "status": status,
                "deliverable": t.get("deliverable", ""),
                "trich_yeu": t.get("trichYeu", "")
            }

            if assignee not in grouped:
                grouped[assignee] = []
            grouped[assignee].append(task_info)

        return grouped

    def get_pending_tasks_for_user(self, user_name: str) -> list:
        """Lấy danh sách task chưa hoàn thành của 1 chuyên viên."""
        tasks = self.get_all_tasks_from_sheet()
        pending = []
        for t in tasks:
            assignee = t.get("assignee", "")
            status = t.get("status", "")
            if status != "Đã hoàn thành":
                if not user_name or (user_name.lower() in str(assignee).lower() or str(assignee).lower() in user_name.lower()):
                    pending.append({
                        "task_id": t.get("taskId"),
                        "task_name": t.get("taskName"),
                        "deadline": t.get("deadline", ""),
                        "status": status,
                        "deliverable": t.get("deliverable", ""),
                        "trich_yeu": t.get("trichYeu", "")
                    })
        return pending

    def update_task_status_and_metadata(self, task_id: str, status: str, summary: str, file_name: str, doc_number: str = "", doc_date: str = "", actual_summary: str = "", deliverable: str = "", project: str = "") -> bool:
        """
        Cập nhật kết quả thẩm định lên Google Sheets:
        - status: 'Đã hoàn thành' hoặc 'Đang sửa lại'
        - Điền: Dự án, Sản phẩm, Số ký hiệu, Ngày ban hành, Trích yếu thực tế, Tóm tắt AI, Thời gian nộp, Tên file.
        """
        webhook_url = self.webhook_url or os.getenv("GOOGLE_SHEETS_WEBHOOK_URL") or DEFAULT_WEBHOOK_URL
        if webhook_url:
            try:
                payload = {
                    "taskId": str(task_id).strip(),
                    "status": status,
                    "summary": summary,
                    "fileName": file_name,
                    "docNumber": doc_number,
                    "docDate": doc_date,
                    "actualSummary": actual_summary,
                    "deliverable": deliverable,
                    "project": project
                }
                res = requests.post(webhook_url, data=json.dumps(payload), headers={'Content-Type': 'application/json'}, allow_redirects=False, timeout=25)
                if res.status_code in [301, 302] and "Location" in res.headers:
                    echo_url = res.headers["Location"]
                    res = requests.get(echo_url, timeout=25)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("success"):
                        sys.stderr.write(f"[OK] Đã cập nhật Task {task_id} sang trạng thái [{status}] trên Google Sheets!\n")
                        return True
            except Exception as e:
                sys.stderr.write(f"[LỖI] Cập nhật Google Sheets thất bại: {e}\n")

        return False

    def scan_drive_folder(self, task_id: str) -> dict:
        """
        Quét Thư mục Google Drive công khai của Phòng (1j8C6PalsK_Z14-C88oKGy3u38OHuKRjL).
        Tìm tệp PDF theo định dạng '[task_id] - [Tên file] - [Tên chuyên viên].pdf'
        Tải trực tiếp về thư mục tạm và trả về {"success": True, "local_path": ..., "file_name": ..., "file_id": ...}.
        """
        import base64
        import tempfile
        import re
        
        target_id = str(task_id).strip()
        folder_url = "https://drive.google.com/drive/folders/1j8C6PalsK_Z14-C88oKGy3u38OHuKRjL?usp=sharing"

        # 1. Quét trực tiếp qua HTML Google Drive public folder (nhanh và chính xác tuyệt đối)
        try:
            req_folder = urllib.request.Request(folder_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req_folder, timeout=20) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                
                # Giải mã escape JSON của Google Drive: \x22 -> ", \x5b -> [, \x5d -> ], \/ -> /
                cleaned_html = html.replace('\\x22', '"').replace('\\x5b', '[').replace('\\x5d', ']').replace('\\/', '/')
                
                # Bóc tách cấu trúc: ["FILE_ID", ["FOLDER_ID"], "FILENAME.pdf"...]
                pattern = r'\["([a-zA-Z0-9_\-]{25,45})",\s*\["[^"]*"\],\s*"([^"]+?\.(?:pdf|PDF|docx?|xlsx?))"'
                drive_items = re.findall(pattern, cleaned_html)
                
                # Regex nhận diện số Task ID ở đầu tên tệp
                task_regex = re.compile(rf'^\s*(?:task\s*#?|nv\s*#?|t)?\s*{re.escape(target_id)}(?:[.\s\-_]|$)', re.IGNORECASE)
                
                matched = next(((fid, fn.strip()) for fid, fn in drive_items if task_regex.search(fn.strip())), None)
                if not matched:
                    # Fallback quét nếu có cấu trúc aria-label
                    alt_files = re.findall(r'aria-label="([^"]+?\.(?:pdf|PDF))\b[^"]*"[^>]*ssk=[\'"][^\'"]*?:([a-zA-Z0-9_\-]{28,35})', html)
                    matched = next(((fid.split('-')[0], fn.strip()) for fn, fid in alt_files if task_regex.search(fn.strip())), None)
                
                if matched:
                    clean_fid, f_name = matched
                    dl_url = f"https://drive.google.com/uc?export=download&id={clean_fid}"
                    req_dl = urllib.request.Request(dl_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req_dl, timeout=35) as dl_resp:
                        pdf_bytes = dl_resp.read()
                        if len(pdf_bytes) > 0:
                            local_dir = tempfile.gettempdir()
                            safe_fn = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', f_name)
                            local_path = os.path.join(local_dir, safe_fn)
                            with open(local_path, "wb") as f_out:
                                f_out.write(pdf_bytes)
                            return {
                                "success": True,
                                "local_path": local_path,
                                "file_name": f_name,
                                "file_id": clean_fid
                            }
        except Exception as e_direct:
            sys.stderr.write(f"[WARN] Quét trực tiếp Google Drive folder lỗi: {e_direct}. Chuyển sang Webhook fallback.\n")

        # 2. Fallback: Gửi yêu cầu qua Webhook Google Apps Script nếu quét trực tiếp không thành công
        webhook_url = self.webhook_url or os.getenv("GOOGLE_SHEETS_WEBHOOK_URL") or DEFAULT_WEBHOOK_URL
        if webhook_url:
            try:
                payload = {
                    "action": "scan_drive",
                    "taskId": target_id,
                    "folderId": "1j8C6PalsK_Z14-C88oKGy3u38OHuKRjL"
                }
                res = requests.post(webhook_url, data=json.dumps(payload), headers={'Content-Type': 'application/json'}, allow_redirects=False, timeout=35)
                if res.status_code in [301, 302] and "Location" in res.headers:
                    res = requests.get(res.headers["Location"], timeout=35)
                
                if res.status_code == 200:
                    data = res.json()
                    if data.get("success") and data.get("files"):
                        matching_file = data["files"][0]
                        f_name = matching_file.get("name", f"task_{target_id}.pdf")
                        f_id = matching_file.get("id")
                        
                        local_dir = tempfile.gettempdir()
                        safe_fn = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', f_name)
                        local_path = os.path.join(local_dir, safe_fn)
                        
                        if matching_file.get("base64"):
                            pdf_bytes = base64.b64decode(matching_file["base64"])
                            with open(local_path, "wb") as f_out:
                                f_out.write(pdf_bytes)
                            return {"success": True, "local_path": local_path, "file_name": f_name, "file_id": f_id}
                        
                        dl_url = matching_file.get("downloadUrl") or f"https://drive.google.com/uc?export=download&id={f_id}"
                        r_dl = requests.get(dl_url, timeout=35)
                        if r_dl.status_code == 200 and len(r_dl.content) > 0:
                            with open(local_path, "wb") as f_out:
                                f_out.write(r_dl.content)
                            return {"success": True, "local_path": local_path, "file_name": f_name, "file_id": f_id}
            except Exception as e_webhook:
                sys.stderr.write(f"[WARN] Fallback Webhook scan_drive lỗi: {e_webhook}\n")

        return {"success": False, "error": f"Không tìm thấy tệp PDF nào có định dạng '{target_id} - [Tên file] - [Tên chuyên viên]' trong Thư mục Google Drive."}

    def _get_all_tasks_from_local_excel(self) -> list:
        if not os.path.exists(self.excel_path):
            return []
        wb = openpyxl.load_workbook(self.excel_path, data_only=True)
        ws = wb.active
        tasks = []
        for row in range(8, ws.max_row + 1):
            task_id = ws.cell(row=row, column=1).value
            if task_id:
                tasks.append({
                    "taskId": str(task_id),
                    "taskName": str(ws.cell(row=row, column=2).value or ""),
                    "assignee": str(ws.cell(row=row, column=3).value or "Chưa gán"),
                    "deadline": str(ws.cell(row=row, column=4).value or ""),
                    "priority": str(ws.cell(row=row, column=5).value or "Bình thường"),
                    "status": str(ws.cell(row=row, column=6).value or "Chưa bắt đầu"),
                    "deliverable": str(ws.cell(row=row, column=7).value or ""),
                    "trichYeu": str(ws.cell(row=row, column=8).value or ""),
                    "soKyHieu": str(ws.cell(row=row, column=9).value or ""),
                    "ngayBanHanh": str(ws.cell(row=row, column=10).value or ""),
                    "aiSummary": str(ws.cell(row=row, column=11).value or ""),
                    "submittedAt": str(ws.cell(row=row, column=12).value or ""),
                    "fileName": str(ws.cell(row=row, column=13).value or "")
                })
        wb.close()
        return tasks
