import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from task_manager import TaskManager
from datetime import datetime

def generate_reminder_message():
    manager = TaskManager("Zalo_Task_Tracker_Template.xlsx")
    grouped = manager.get_grouped_pending_tasks()
    
    msg = [
        "📢 ═════ [BÁO CÁO TIẾN ĐỘ NHIỆM VỤ THEO CHUYÊN VIÊN] ═════",
        f"⏰ Cập nhật lúc: {datetime.now().strftime('%H:%M %d/%m/%Y')}\n"
    ]
    
    if not grouped:
        msg.append("🎉 Tuyệt vời! Hiện tại tất cả nhiệm vụ đã hoàn thành 100%.")
    else:
        for assignee, task_list in grouped.items():
            msg.append(f"👤 CHUYÊN VIÊN: @{assignee} ({len(task_list)} nhiệm vụ)")
            for t in task_list:
                prio_icon = "🔥" if t['priority'] == "Gấp" else ("⭐" if t['priority'] == "Quan trọng" else "🔹")
                
                # Biểu tượng cảnh báo hạn chót
                if t['urgency_status'] == 'overdue':
                    urgency_icon = "🚨"
                elif t['urgency_status'] in ['due_today', 'due_soon']:
                    urgency_icon = "⚠️"
                else:
                    urgency_icon = "⏳"
                
                deadline_info = f"{t['deadline']}"
                if t['days_diff_text']:
                    deadline_info += f" ({t['days_diff_text']})"

                msg.append(f"  • {prio_icon} [Nhiệm vụ {t['task_id']}] {t['task_name']}")
                msg.append(f"    {urgency_icon} Hạn: {deadline_info} | Mức độ: {t['priority']}")
                
                # Hiển thị Sản phẩm yêu cầu kèm định dạng
                deliverable = t['deliverable'] or "Chưa ghi định dạng"
                msg.append(f"    📦 Sản phẩm: {deliverable} | Trạng thái: {t['status']}")
                
                # Nếu có Trích yếu quy định
                if t.get('trich_yeu'):
                    msg.append(f"    📄 Trích yếu: {t['trich_yeu']}")
                    
                msg.append("") # Dòng trống ngăn cách các task

    msg.append("💡 QUY ĐỊNH NỘP FILE: Chuyên viên đặt tên file có số thứ tự đứng đầu (Ví dụ: '1. To_trinh_Cau_vuot_bien.docx') để AI tự động đối chiếu Trích yếu, bóc tách Số ký hiệu và hoàn tất nghiệm thu.")
    return "\n".join(msg)

if __name__ == "__main__":
    print(generate_reminder_message())
