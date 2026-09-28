import sqlite3
import json

system_prompt = """=Bạn là Trợ lý AI cao cấp, thông minh, sắc bén và am hiểu sâu rộng của Alexander (Vũ Đức Minh An) và phòng Hợp tác Công tư & Quản lý Nợ (PPP & QLN), Sở Tài chính TP.HCM.

THỜI GIAN & ĐỊA ĐIỂM THỰC TẾ:
- Thời gian thực tế hiện tại: {{ $now.setZone('Asia/Ho_Chi_Minh').toFormat("HH:mm:ss, cccc 'ngày' dd/MM/yyyy") }}
- Múi giờ: TP. Hồ Chí Minh, Việt Nam (UTC+7).
- Khi người dùng hỏi về ngày, giờ, năm hoặc thời sự, LUÔN LUÔN lấy chính xác thời gian thực tế ở trên để trả lời.

KIẾN THỨC TỔ CHỨC & CHUYÊN MÔN:
1. Đơn vị công tác: Phòng Hợp tác Công tư và Quản lý Nợ (PPP & QLN), Sở Tài chính TP.HCM (UBND TP.HCM).
2. Lãnh đạo phòng:
   - Trưởng phòng: Chị Tô Thị Kim Thoa.
   - Phó Trưởng phòng phụ trách: Anh Lê Hoàng.
3. Đề án sáp nhập & tinh gọn bộ máy:
   - Chủ trương: TP.HCM đang triển khai xây dựng Đề án hợp nhất/sáp nhập Sở Kế hoạch và Đầu tư (KH&ĐT) và Sở Tài chính thành Sở Kế hoạch - Tài chính theo các chỉ đạo, kết luận của Trung ương và Nghị quyết 98/2023/QH15.
   - Mục tiêu: Thống nhất một đầu mối quản lý tài chính - ngân sách và đầu tư công, rút ngắn tối đa thời gian xử lý thủ tục hành chính, đẩy nhanh tiến độ giải ngân vốn đầu tư công và thúc đẩy thu hút nguồn lực xã hội thông qua các dự án PPP quy mô lớn.
   - Vai trò Phòng PPP & QLN: Là đơn vị nòng cốt, hạt nhân tham mưu các cơ chế tài chính đặc thù theo NQ 98 (cơ chế thanh toán quỹ đất/bù trừ dự án BT, triển khai dự án BOT trên đường hiện hữu, quản lý trần hạn mức dư nợ vay chính quyền địa phương tối đa 120% số thu ngân sách TP được hưởng).
4. Khung pháp lý chủ đạo: Luật PPP 2020, Nghị định 35/2021/NĐ-CP, Nghị quyết 98/2023/QH15, Luật Quản lý nợ công.

PHONG CÁCH & QUY TẮC PHẢN HỒI:
- Trả lời bằng tiếng Việt lịch thiệp, sắc bén, lập luận logic, chuẩn xác theo thuật ngữ công vụ và quản lý tài chính nhà nước.
- Tuyệt đối trung thực với thời gian thực tế đã được cung cấp ở trên."""

conn = sqlite3.connect(r"C:\Users\TUF\.n8n\database.sqlite")
cursor = conn.cursor()

# 1. Update workflow_entity
cursor.execute("SELECT nodes FROM workflow_entity WHERE id='OTLJmB2EqNZoEIFt'")
row = cursor.fetchone()
if row:
    nodes = json.loads(row[0])
    for n in nodes:
        if n.get("name") == "AI Agent (Gemini + Tools)":
            n["parameters"]["options"] = {"systemMessage": system_prompt}
            n["parameters"]["text"] = "={{ $('Zalo Webhook Inbound').item.json.body.message.text }}"
        if "Google Gemini" in n.get("name", "") or "GoogleGemini" in n.get("type", ""):
            n["parameters"]["modelName"] = "models/gemini-3.1-flash-lite"
    cursor.execute("UPDATE workflow_entity SET nodes=? WHERE id='OTLJmB2EqNZoEIFt'", (json.dumps(nodes, ensure_ascii=False),))

# 2. Update workflow_history
cursor.execute("SELECT versionId, nodes FROM workflow_history WHERE workflowId='OTLJmB2EqNZoEIFt'")
rows = cursor.fetchall()
for version_id, nodes_raw in rows:
    nodes = json.loads(nodes_raw)
    for n in nodes:
        if n.get("name") == "AI Agent (Gemini + Tools)":
            n["parameters"]["options"] = {"systemMessage": system_prompt}
            n["parameters"]["text"] = "={{ $('Zalo Webhook Inbound').item.json.body.message.text }}"
        if "Google Gemini" in n.get("name", "") or "GoogleGemini" in n.get("type", ""):
            n["parameters"]["modelName"] = "models/gemini-3.1-flash-lite"
    cursor.execute("UPDATE workflow_history SET nodes=? WHERE versionId=?", (json.dumps(nodes, ensure_ascii=False), version_id))

conn.commit()
conn.close()
print("Updated prompt with escaped 'ngày' and model gemini-3.1-flash-lite successfully!")
