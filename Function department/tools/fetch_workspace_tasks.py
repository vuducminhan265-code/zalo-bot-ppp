# Function department/tools/fetch_workspace_tasks.py
import os
import sys
import re
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

    def generate_reminder_parts(self) -> tuple:
        from datetime import datetime, timezone, timedelta
        tz_vn = timezone(timedelta(hours=7))
        now_vn = datetime.now(tz_vn)
        now_time = now_vn.strftime("%H:%M")
        now_date = now_vn.strftime("%d/%m/%Y")

        all_tasks = self.task_manager.get_all_tasks_from_sheet()
        completed_tasks = [t for t in all_tasks if t.get("status") == "Đã hoàn thành"]
        count_completed = len(completed_tasks)

        assignee_completed = {}
        for t in completed_tasks:
            ass = t.get("assignee", "Chưa phân công")
            assignee_completed[ass] = assignee_completed.get(ass, 0) + 1

        grouped = self.task_manager.get_grouped_pending_tasks()

        if not grouped:
            report_empty = (
                f"🎉 **[ZALO BOT - GOOGLE WORKSPACE]**\n"
                f"⏰ Thời gian: {now_time} ngày {now_date}\n\n"
                f"Tất cả các nhiệm vụ trên Bảng giao việc hiện tại đã HOÀN THÀNH!"
            )
            return report_empty, self.generate_guide_message()

        lines = [
            "📢 **[NHẮC VIỆC TỰ ĐỘNG - GOOGLE WORKSPACE]**",
            f"⏰ Thời gian: {now_time} ngày {now_date}",
            "📋 Danh sách nhiệm vụ đang chờ theo Chuyên viên:\n"
        ]

        total_pending = 0
        count_overdue = 0
        count_today = 0
        count_upcoming = 0
        assignee_stats = {}

        for assignee, tasks in grouped.items():
            lines.append(f"👤 {assignee.upper()} ({len(tasks)} nhiệm vụ chưa xong):")
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

                # Làm sạch triệt để các ký tự xuống dòng / tab
                raw_name = str(t.get('task_name') or "")
                clean_name = re.sub(r'[\r\n\t]+', ' ', raw_name)
                clean_name = re.sub(r'\s{2,}', ' ', clean_name).strip()

                # Format ngày deadline (DD/MM/YYYY)
                raw_dl = str(t.get('deadline') or "").strip()
                fmt_dl = raw_dl
                if re.match(r'^\d{4}-\d{2}-\d{2}$', raw_dl):
                    parts = raw_dl.split('-')
                    fmt_dl = f"{parts[2]}/{parts[1]}/{parts[0]}"

                diff_text = t.get('days_diff_text', '')
                deadline_display = f"{fmt_dl} ({diff_text})" if diff_text else fmt_dl

                # Thông tin bổ trợ (Dự án, Lãnh đạo, Trạng thái)
                detail_parts = []
                if t.get('project'):
                    detail_parts.append(f"Dự án: {t.get('project')}")
                if t.get('leader'):
                    detail_parts.append(f"Lãnh đạo: {t.get('leader')}")
                detail_parts.append(f"Hạn: {deadline_display}")
                detail_parts.append(f"Trạng thái: {t.get('status')}")

                lines.append(f"• {prio_icon} [{t.get('task_id')}] {clean_name}")
                lines.append(f"  ⏳ {' | '.join(detail_parts)}")
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

        sheet_url = "https://docs.google.com/spreadsheets/d/1RRb0PJB2EJv92SPHZ3_ahv2YYEn9bxjfC8JBPpTkuG4/edit?gid=735957328"
        lines.append("🔗 **ĐƯỜNG DẪN TRUY CẬP GOOGLE SHEETS:**")
        lines.append("👉 **Link trực tiếp:**")
        lines.append(sheet_url)
        
        report_msg = "\n".join(lines)
        guide_msg = self.generate_guide_message()

        return report_msg, guide_msg

    def generate_guide_message(self) -> str:
        drive_folder_url = "https://drive.google.com/drive/folders/1j8C6PalsK_Z14-C88oKGy3u38OHuKRjL?usp=drive_link"
        guide_lines = [
            "📥 **HƯỚNG DẪN NỘP SẢN PHẨM & NGHIỆM THU TỰ ĐỘNG:**",
            "*(Hệ thống AI tự động đối soát thể thức Nghị định 30/2020/NĐ-CP, kiểm tra Tiêu ngữ, Số ký hiệu, Trích yếu, Chữ ký lưu và cập nhật trực tiếp lên Google Sheets)*",
            "",
            "1️⃣ **CÁCH 1: NỘP BẰNG HÌNH ẢNH QUA ZALO (HỖ TRỢ 2 TÙY CHỌN LINH HOẠT)**",
            "• **Bước 1**: Nhắn tin vào nhóm: `Nộp task [số]` (Ví dụ: `Nộp task 4`, `Nộp task 2`).",
            "• **Bước 2**: Chuyên viên lựa chọn 1 trong 2 hình thức gửi ảnh thuận tiện:",
            "   🔹 **Tùy chọn 1A - Nộp từng ảnh rời (An toàn, chống sót trang)**: Gửi ảnh Trang 1 (có Tiêu ngữ, Số ký hiệu, Trích yếu) ➔ Hệ thống lập tức phản hồi đã nhận và đệm chờ 6 giây để Anh/Chị gửi tiếp Trang cuối (có Nơi nhận, Ký hiệu lưu vết, Chữ ký). Sau khi nhận đủ sẽ tự động tổng hợp đối soát.",
            "   🔹 **Tùy chọn 1B - Nộp gom một thể (Nhanh gọn)**: Chọn và gửi cùng lúc tất cả các trang ảnh văn bản (Album / Multi-select). Hệ thống tự động gom toàn bộ ảnh nhận được trong một lượt, tự phân định đâu là trang đầu, đâu là trang cuối để thẩm định.",
            "",
            "2️⃣ **CÁCH 2: NỘP VĂN BẢN PDF CHẤT LƯỢNG CAO QUA GOOGLE DRIVE**",
            "• **Bước 1**: Tải tệp PDF sản phẩm vào Thư mục Google Drive dùng chung của Phòng:",
            f"  🔗 {drive_folder_url}",
            "• **Đặt tên tệp chuẩn**: `[Số Task] - [Tên file / Loại văn bản] - [Tên chuyên viên].pdf` (Ví dụ: `4 - Tờ trình Mả Lạng - Nguyễn Trung Bảo Lộc.pdf` hoặc `4 - File - Tên chuyên viên.pdf`).",
            "• **Bước 2**: Nhắn vào chat Zalo cú pháp: `nộp task [số] pdf` (Ví dụ: `nộp task 4 pdf`).",
            "  *(AI sẽ tự động quét Google Drive, tải PDF về đối soát thể thức Nghị định 30/2020/NĐ-CP và cập nhật Bảng giao việc)*.",
            "",
            "📌 **Tra cứu nhanh nhiệm vụ:**",
            "  👉 Gõ `task [số]` (Ví dụ: `task 4` hoặc `xem task 4`) để xem đầy đủ thông tin nhiệm vụ, dự án, hạn hoàn thành và kết quả thẩm định."
        ]
        return "\n".join(guide_lines)

    def generate_evening_review_summary(self) -> str:
        """
        Bản tin Tổng kết cuối ngày (17:30):
        Liệt kê các task chuyên viên đã nộp/hoàn thành trong ngày:
        Chuyên viên, Lãnh đạo phòng, Dự án, Trích yếu, Số ký hiệu, Ngày ban hành.
        Nếu không có sản phẩm nào thì ghi rõ 0 sản phẩm.
        """
        from datetime import datetime, timezone, timedelta
        tz_vn = timezone(timedelta(hours=7))
        now_vn = datetime.now(tz_vn)
        now_time = now_vn.strftime("%H:%M")
        now_date = now_vn.strftime("%d/%m/%Y")

        all_tasks = self.task_manager.get_all_tasks_from_sheet()
        
        # Lọc các task đã hoàn thành trong ngày hôm nay (dựa trên submittedAt hoặc status)
        # submittedAt thường có dạng "2026-10-19 14:30:00" hoặc "19/10/2026"
        today_date_str = now_vn.strftime("%Y-%m-%d")
        today_vn_fmt = now_vn.strftime("%d/%m/%Y")
        
        completed_today = []
        for t in all_tasks:
            status = str(t.get("status") or "").strip()
            submitted = str(t.get("submittedAt") or "").strip()
            
            # Kiểm tra xem có nộp hôm nay không
            if status == "Đã hoàn thành":
                if today_date_str in submitted or today_vn_fmt in submitted:
                    completed_today.append(t)
                elif not submitted:
                    # Nếu không có ngày nộp nhưng là task đã hoàn thành mới nhất
                    pass

        lines = [
            "📋 **[TỔNG KẾT TIẾN ĐỘ CUỐI NGÀY - PHÒNG PPP & QUẢN LÝ NỢ]**",
            f"⏰ Thời gian: {now_time} ngày {now_date}",
            "🏛️ **Sở Tài chính TP.Hồ Chí Minh**",
            "────────────────────────────"
        ]

        if not completed_today:
            lines.append("📊 **KẾT QUẢ NGHIỆM THU HÔM NAY:**")
            lines.append("• **Số lượng sản phẩm văn bản đã nộp hôm nay**: 0 sản phẩm.")
            lines.append("• Hôm nay chưa ghi nhận thêm sản phẩm văn bản mới nào được nộp qua hệ thống Zalo Bot / Drive.")
            lines.append("")
            lines.append("💡 **Nhắc nhở công vụ**: Các đồng chí chuyên viên còn nhiệm vụ đến hạn hoặc quá hạn vui lòng khẩn trương hoàn thiện văn bản và nộp nghiệm thu.")
        else:
            lines.append(f"🎉 **KẾT QUẢ NGHIỆM THU HÔM NAY ({len(completed_today)} SẢN PHẨM HOÀN THÀNH):**\n")
            for idx, t in enumerate(completed_today, 1):
                t_id = t.get("taskId") or t.get("task_id")
                t_name = t.get("taskName") or t.get("task_name")
                assignee = t.get("assignee", "Chưa phân công")
                leader = t.get("leader", "Lãnh đạo phòng")
                proj = t.get("project") or "Dự án liên quan"
                trich_yeu = t.get("trichYeu") or t.get("aiSummary") or t_name
                so_kh = t.get("soKyHieu") or "Văn bản nội bộ"
                ngay_bh = t.get("ngayBanHanh") or now_date
                deliv = t.get("deliverable") or "Công văn"

                lines.append(f"**{idx}. [Task #{t_id}] {t_name}**")
                lines.append(f"   • 👤 **Chuyên viên**: {assignee}")
                lines.append(f"   • 👔 **Lãnh đạo phòng**: {leader}")
                lines.append(f"   • 🏢 **Dự án**: {proj}")
                lines.append(f"   • 📦 **Sản phẩm**: {deliv} (Số: {so_kh} | Ngày: {ngay_bh})")
                lines.append(f"   • 📌 **Trích yếu**: {trich_yeu}")
                lines.append(f"   • 🟢 **Tình trạng**: Đã nghiệm thu chuẩn thể thức & Cập nhật Google Sheets.")
                lines.append("")

        lines.append("────────────────────────────")
        lines.append("🔗 **BẢNG GIAO VIỆC GOOGLE SHEETS:**")
        lines.append("https://docs.google.com/spreadsheets/d/1RRb0PJB2EJv92SPHZ3_ahv2YYEn9bxjfC8JBPpTkuG4/edit?gid=735957328")
        
        return "\n".join(lines)

    def generate_formatted_reminder(self) -> str:
        report_msg, guide_msg = self.generate_reminder_parts()
        return f"{report_msg}\n\n---\n\n{guide_msg}"

if __name__ == "__main__":
    fetcher = GoogleWorkspaceTaskFetcher()
    print("=== LIVE GOOGLE WORKSPACE TASK REMINDER REPORT ===")
    print(fetcher.generate_formatted_reminder())
    print("\n=== EVENING REVIEW SUMMARY ===")
    print(fetcher.generate_evening_review_summary())
