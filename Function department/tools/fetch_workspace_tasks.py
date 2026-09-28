# Function department/tools/fetch_workspace_tasks.py
import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
try:
    from .task_manager import TaskManager
except ImportError:
    from task_manager import TaskManager

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

class GoogleWorkspaceTaskFetcher:
    """Queries live Google Workspace Sheets tasks via TaskManager integration."""

    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.local_excel = os.path.join(base_dir, "data", "database", "Zalo_Task_Tracker_Template.xlsx")
        self.task_manager = TaskManager(self.local_excel)

    def fetch_live_tasks(self) -> list:
        """Fetches all tasks live from Google Sheets."""
        all_tasks = self.task_manager.get_all_tasks_from_sheet()
        return [t for t in all_tasks if t.get("status") != "Đã hoàn thành"]

    def generate_formatted_reminder(self) -> str:
        all_tasks = self.task_manager.get_all_tasks_from_sheet()
        completed_tasks = [t for t in all_tasks if t.get("status") == "Đã hoàn thành"]
        count_completed = len(completed_tasks)

        assignee_completed = {}
        for t in completed_tasks:
            ass = t.get("assignee", "Chưa phân công")
            assignee_completed[ass] = assignee_completed.get(ass, 0) + 1

        grouped = self.task_manager.get_grouped_pending_tasks()
        now_str = datetime.now().strftime("%H:%M ngày %d/%m/%Y")

        if not grouped:
            return f"🎉 **[ZALO BOT - GOOGLE WORKSPACE]** ({now_str})\n\nTất cả các nhiệm vụ trên Google Sheets hiện tại đã HOÀN THÀNH!"

        lines = [
            "📢 **[NHẮC VIỆC TỰ ĐỘNG - GOOGLE WORKSPACE]**",
            f"⏰ Thời gian cập nhật: {now_str}",
            "📋 Danh sách nhiệm vụ đang chờ theo Chuyên viên:\n"
        ]

        total_pending = 0
        count_overdue = 0
        count_today = 0
        count_upcoming = 0
        assignee_stats = {}

        for assignee, tasks in grouped.items():
            lines.append(f"👤 **{assignee.upper()}** ({len(tasks)} nhiệm vụ chưa xong):")
            assignee_stats[assignee] = {
                "pending": len(tasks),
                "completed": assignee_completed.get(assignee, 0),
                "overdue": 0,
                "today": 0,
                "upcoming": 0
            }
            for t in tasks:
                total_pending += 1
                urg = t.get('urgency_status')
                if urg == 'overdue':
                    count_overdue += 1
                    assignee_stats[assignee]["overdue"] += 1
                    prio_icon = "🔴 [Quá hạn]"
                elif urg in ['due_today', 'due_soon']:
                    count_today += 1
                    assignee_stats[assignee]["today"] += 1
                    prio_icon = "⚠️ [Hôm nay/Sắp hạn]"
                else:
                    count_upcoming += 1
                    assignee_stats[assignee]["upcoming"] += 1
                    prio_icon = "🔹 [Trong hạn]"

                lines.append(f"   • {prio_icon} [{t.get('task_id')}] {t.get('task_name')}")
                lines.append(f"     ⏳ Deadline: {t.get('deadline')} ({t.get('days_diff_text')}) | Trạng thái: {t.get('status')}")
            lines.append("")

        lines.append("📊 **[THỐNG KÊ CHI TIẾT TỔNG HỢP TIẾN ĐỘ]**")
        lines.append(f"• ✅ **Nhiệm vụ Đã hoàn thành:** {count_completed} nhiệm vụ")
        lines.append(f"• 🔴 **Nhiệm vụ Quá hạn:** {count_overdue} nhiệm vụ ({(count_overdue/total_pending*100):.1f}%/chưa xong)")
        lines.append(f"• ⚠️ **Nhiệm vụ Hạn hôm nay / Sắp hạn:** {count_today} nhiệm vụ ({(count_today/total_pending*100):.1f}%/chưa xong)")
        lines.append(f"• 🔹 **Nhiệm vụ Đang trong hạn:** {count_upcoming} nhiệm vụ ({(count_upcoming/total_pending*100):.1f}%/chưa xong)")
        lines.append(f"📈 **TỔNG SỐ TASK CHƯA HOÀN THÀNH:** {total_pending} nhiệm vụ")
        lines.append("")
        lines.append("👥 **Phân bổ theo Chuyên viên phụ trách:**")
        for idx, (ass, st) in enumerate(assignee_stats.items(), 1):
            lines.append(f"  {idx}️⃣ **{ass}**: {st['pending']} task chưa xong ({st['completed']} đã hoàn thành, {st['overdue']} quá hạn, {st['today']} đến hạn)")
        lines.append("")

        sheet_url = "https://docs.google.com/spreadsheets/d/1RRb0PJB2EJv92SPHZ3_ahv2YYEn9bxjfC8JBPpTkuG4/edit?usp=sharing"
        lines.append("🔗 **ĐƯỜNG DẪN TRUY CẬP GOOGLE SHEETS:**")
        lines.append("👉 **Link trực tiếp:**")
        lines.append(sheet_url)
        lines.append("")
        lines.append("📥 **HƯỚNG DẪN NỘP FILE TỰ ĐỘNG NGHIỆM THU:**")
        lines.append("• **Cách nộp:** Nộp file đính kèm trực tiếp vào Zalo Group để tự động nghiệm thu.")
        lines.append("• **Cấu trúc đặt tên tệp (Format):**")
        lines.append("  `[Số thứ tự ID] - [Nội dung ngắn gọn] - [Tên Chuyên viên]`")
        lines.append("  *(Lưu ý: Số thứ tự ID ở đầu tên tệp là bắt buộc để hệ thống AI tự động quét đối soát đúng Task ID, số ký hiệu, trích yếu và ngày tháng. Phần nội dung và tên chuyên viên có thể viết ngắn gọn hoặc viết tắt như Hận, hận, han, An...)*")
        lines.append("")
        lines.append("📌 **Ví dụ cụ thể:**")
        lines.append("  1️⃣ `1 - Thẩm định phương án tài chính BOT Cầu Cần Giờ - Hận.pdf`")
        lines.append("  2️⃣ `4 - Báo cáo rà soát ODA - An.docx`")
        return "\n".join(lines)

if __name__ == "__main__":
    fetcher = GoogleWorkspaceTaskFetcher()
    print("=== LIVE GOOGLE WORKSPACE TASK REMINDER REPORT ===")
    print(fetcher.generate_formatted_reminder())
