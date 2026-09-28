# QUY TRÌNH HỆ THỐNG ZALO BOT & AI REVIEW TASK AUTOMATION

## 1. MỤC TIÊU & KIẾN TRÚC TỔNG THỂ
Hệ thống Zalo Bot tự động hóa 3 công việc chính:
1. **Nhắc việc định kỳ (Automated Task Reminders)**: Quét danh sách task trong bảng Excel/Google Sheets và gửi báo cáo tiến độ vào nhóm Zalo lúc 08:30 và 16:30 hằng ngày.
2. **Nghiệm thu sản phẩm tự động (AI File Inspection)**: Khi thành viên nộp file đính kèm (Docx, PDF, Xlsx, Ảnh) vào nhóm Zalo, Zalo Bot tự động chuyển file đến Gemini AI để đọc, so khớp yêu cầu và xác nhận hoàn thành task.
3. **Tra cứu tri thức RAG (Retrieval-Augmented Generation)**: Hỗ trợ tra cứu quy trình, biểu mẫu, văn bản pháp luật ngay trong nhóm Zalo.

---

## 2. CẤU TRÚC THƯ MỤC CHUẨN (`Function department`)
Toàn bộ mã nguồn và công cụ được phân lập trong thư mục `Function department`:
- `Function department/ai_core`: Chứa module Gemini Flash (`ai_analyzer.py`), cấu hình AI models.
- `Function department/zalo_service`: Chứa Zalo bot listener (`zalo_bot_service.py`), Google Apps Script (`GoogleAppsScript_Code.js`), n8n workflows (`zalo_n8n_workflow_template.json`).
- `Function department/tools`: Chứa các script quản lý dữ liệu (`task_manager.py`), tạo mẫu Excel (`generate_sheet.py`), kiểm thử kịch bản.
- `Function department/rag_engine`: Bộ máy RAG phục vụ tra cứu tri thức (`rag_indexer.py`, `rag_retriever.py`, `rag_pipeline.py`).
- `Function department/skills`: Chứa các quy chuẩn vận hành và tài liệu kỹ năng.

---

## 3. NƠI LƯU TRỮ DỮ LIỆU (`data/`)
- `data/database`: Chứa file `Zalo_Task_Tracker_Template.xlsx` và cơ sở dữ liệu `rag_index.db`.
- `data/documents`: Bộ tài liệu tri thức làm đầu vào cho cơ chế RAG.
- `data/uploads`: Lưu trữ tạm thời các file tải về từ Zalo trước khi đưa qua AI thẩm định.
