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
SHEET_GID = "735957328"
WEBHOOK_URL = os.getenv("GOOGLE_SHEETS_WEBHOOK_URL")
CSV_EXPORT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"

session = requests.Session()

class TaskManager:
    def __init__(self, excel_path: str = "Zalo_Task_Tracker_Template.xlsx", webhook_url: str = None):
        self.excel_path = excel_path
        self.webhook_url = webhook_url or WEBHOOK_URL

    def get_all_tasks_from_sheet(self) -> list:
        """Đọc tức thì toàn bộ 13 cột từ Google Sheets (gid=735957328)."""
        try:
            req = urllib.request.Request(CSV_EXPORT_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read().decode("utf-8")
                reader = csv.reader(io.StringIO(content))
                rows = list(reader)
                
                tasks = []
                for i in range(7, len(rows)):
                    row = rows[i]
                    if len(row) > 0 and row[0].strip():
                        tasks.append({
                            "taskId": row[0].strip(),
                            "taskName": row[1].strip() if len(row) > 1 else "",
                            "assignee": row[2].strip() if len(row) > 2 else "Chưa gán",
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
                return tasks
        except Exception as e:
            sys.stderr.write(f"[CẢNH BÁO] Không thể đọc Google Sheets: {e}. Chuyển sang đọc file local.\n")
        
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

    def update_task_status_and_metadata(self, task_id: str, status: str, summary: str, file_name: str, doc_number: str = "", doc_date: str = "", actual_summary: str = "") -> bool:
        """
        Cập nhật kết quả thẩm định lên Google Sheets:
        - status: 'Đã hoàn thành' hoặc 'Đang sửa lại'
        - Điền: Số ký hiệu, Ngày ban hành, Trích yếu thực tế, Tóm tắt AI, Thời gian nộp, Tên file.
        """
        if self.webhook_url:
            try:
                payload = {
                    "taskId": str(task_id).strip(),
                    "status": status,
                    "summary": summary,
                    "fileName": file_name,
                    "docNumber": doc_number,
                    "docDate": doc_date,
                    "actualSummary": actual_summary
                }
                res = session.post(self.webhook_url, json=payload, allow_redirects=True, timeout=25)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("success"):
                        sys.stderr.write(f"[OK] Đã cập nhật Task {task_id} sang trạng thái [{status}] trên Google Sheets!\n")
                        return True
            except Exception as e:
                sys.stderr.write(f"[LỖI] Cập nhật Google Sheets thất bại: {e}\n")

        return False

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
