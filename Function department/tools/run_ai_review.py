import sys
import argparse
import json
import os

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from ai_analyzer import TaskAIAnalyzer
from task_manager import TaskManager

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", "-f", default="", help="Path to the uploaded file")
    parser.add_argument("--user", "-u", default="Thành viên", help="Sender name / Zalo name")
    parser.add_argument("positional_file", nargs="?", default="", help="Positional file path")
    args = parser.parse_args()

    file_path = args.file or args.positional_file
    user_name = args.user or "Thành viên"

    if not file_path or not os.path.exists(file_path):
        print(json.dumps({"success": False, "error": f"Không tìm thấy file: {file_path}"}, ensure_ascii=False))
        return

    manager = TaskManager()
    
    # 1. Trích xuất gợi ý Task ID từ tên file nếu có (Ví dụ: '1. 23920...pdf' -> '1')
    analyzer = TaskAIAnalyzer()
    hint_task_id = analyzer.extract_task_number_from_filename(file_path)

    # 2. Lấy danh sách nhiệm vụ đang chờ (tất cả hoặc theo user)
    all_pending = manager.get_all_tasks_from_sheet()
    pending_tasks = [t for t in all_pending if t.get("status") != "Đã hoàn thành"]

    if not pending_tasks:
        print(json.dumps({
            "success": False,
            "message": "Hiện không có nhiệm vụ nào đang chờ xử lý trên hệ thống."
        }, ensure_ascii=False))
        return

    # 3. Gọi AI Gemini để đọc file, bóc tách thể thức và đối chiếu trích yếu
    ai_result = analyzer.review_submission(
        file_path=file_path,
        assignee_name=user_name,
        pending_tasks=pending_tasks
    )

    if not ai_result.get("success"):
        print(json.dumps(ai_result, ensure_ascii=False))
        return

    # Quyết định Task ID mục tiêu: ưu tiên hint_task_id từ tên file nếu AI tìm thấy hoặc hint_task_id hợp lệ
    task_id = str(ai_result.get("task_id", "")).strip() or hint_task_id
    status_decision = ai_result.get("status_decision", "needs_revision")
    file_name = os.path.basename(file_path)
    
    doc_number = ai_result.get("document_number", "")
    doc_date = ai_result.get("document_date", "")
    actual_summary = ai_result.get("actual_summary", "")
    ai_review = ai_result.get("ai_review_comment", "") or ai_result.get("ai_review", "")

    if status_decision == "completed" and task_id:
        # Trường hợp 1: Khớp đúng trích yếu -> Đã hoàn thành
        update_ok = manager.update_task_status_and_metadata(
            task_id=task_id,
            status="Đã hoàn thành",
            summary=ai_review,
            file_name=file_name,
            doc_number=doc_number,
            doc_date=doc_date,
            actual_summary=actual_summary
        )
        ai_result["sheet_updated"] = update_ok
        ai_result["final_status"] = "Đã hoàn thành"
    else:
        # Trường hợp 2: Lệch nội dung hoặc chưa khớp -> Đang sửa lại
        if task_id:
            update_ok = manager.update_task_status_and_metadata(
                task_id=task_id,
                status="Đang sửa lại",
                summary=f"[Cần sửa] {ai_review}",
                file_name=file_name,
                doc_number=doc_number,
                doc_date=doc_date,
                actual_summary=actual_summary
            )
            ai_result["sheet_updated"] = update_ok
        ai_result["final_status"] = "Đang sửa lại"

    ai_result["task_id"] = task_id
    print(json.dumps(ai_result, ensure_ascii=False))

if __name__ == "__main__":
    main()
