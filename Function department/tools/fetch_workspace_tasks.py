# Function department/tools/fetch_workspace_tasks.py
import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
from .task_manager import TaskManager

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
        grouped = self.task_manager.get_grouped_pending_tasks()
        now_str = datetime.now().strftime("%H:%M ngày %d/%m/%Y")

        if not grouped:
            return f"🎉 **[ZALO BOT - GOOGLE WORKSPACE]** ({now_str})\n\nTất cả các nhiệm vụ trên Google Sheets hiện tại đã HOÀN THÀNH!"

        lines = [
            "📢 ═════ [NHẮC VIỆC TỰ ĐỘNG - GOOGLE WORKSPACE] ═════",
            f"⏰ Thời gian cập nhật: {now_str}",
            "📋 Danh sách nhiệm vụ đang chờ theo Chuyên viên:\n"
        ]

        total_pending = 0
        for assignee, tasks in grouped.items():
            lines.append(f"👤 **{assignee.upper()}** ({len(tasks)} nhiệm vụ):")
            for t in tasks:
                total_pending += 1
                urg = t.get('urgency_status')
                prio_icon = "🔴 [Quá hạn]" if urg == 'overdue' else ("⚠️ [Sắp hạn]" if urg == 'due_soon' else ("⚠️ [Hôm nay]" if urg == 'due_today' else "🔹"))
                lines.append(f"   • {prio_icon} [{t.get('task_id')}] {t.get('task_name')}")
                lines.append(f"     ⏳ Deadline: {t.get('deadline')} ({t.get('days_diff_text')}) | Trạng thái: {t.get('status')}")
            lines.append("")

        lines.append(f"📊 **Tổng số task chưa hoàn thành**: {total_pending}")
        lines.append("💡 Ghi chú: Đã đồng bộ trực tiếp với Google Sheets (ID: 1RRb0PJB2EJv...). Nộp file đính kèm vào Zalo Group để tự động nghiệm thu.")
        return "\n".join(lines)

if __name__ == "__main__":
    fetcher = GoogleWorkspaceTaskFetcher()
    print("=== LIVE GOOGLE WORKSPACE TASK REMINDER REPORT ===")
    print(fetcher.generate_formatted_reminder())
