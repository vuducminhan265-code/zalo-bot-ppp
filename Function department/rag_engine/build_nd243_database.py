# Function department/rag_engine/build_nd243_database.py
import docx
import re
import json
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

docx_path = r"D:\Personal\Công việc\PPP - Sở Tài Chính\Luật liên quan\Luật liên quan hiện hành\Luật PPP\Van_ban_hop_nhat_PPP_180_243_cap_nhat_377 ve ppp.docx"
output_json = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nd243_full_consolidated_database.json")

amend_map = {
    5: 11, 6: 12, 7: 13, 10: 14, 26: 15, 27: 16, 28: 17, 29: 18,
    34: 19, 36: 20, 42: 21, 43: 22, 57: 23, 62: 24, 64: 25, 68: 26,
    72: 27, 75: 28, 80: 29, 82: 30
}

doc = docx.Document(docx_path)

articles_raw = {}
cur_dieu = None
cur_paras = []

# Range of Nghị định 243 is strictly paragraphs 344 to 1600
for idx in range(344, 1600):
    p = doc.paragraphs[idx]
    t = p.text.strip()
    if not t:
        continue
    m = re.match(r'^(Điều\s+(\d+)\.?[^\n]*)', t)
    if m:
        dnum = int(m.group(2))
        if cur_dieu is None and dnum == 1:
            cur_dieu = dnum
            cur_paras = [p]
        elif cur_dieu is not None and dnum == cur_dieu + 1:
            articles_raw[cur_dieu] = cur_paras
            cur_dieu = dnum
            cur_paras = [p]
        elif cur_dieu is not None:
            cur_paras.append(p)
    else:
        if cur_dieu is not None:
            cur_paras.append(p)

if cur_dieu is not None:
    articles_raw[cur_dieu] = cur_paras

print(f"Collected {len(articles_raw)} articles from NĐ 243.")

database = {}

for dnum, paras in articles_raw.items():
    title = paras[0].text.strip()
    amending_art = amend_map.get(dnum)
    
    # We parse into clauses (Khoản 1, 2, ... or un-numbered text)
    clauses = []
    current_clause_num = None
    current_clause_lines = []
    current_clause_highlight = False
    
    for p in paras[1:]:
        t = p.text.strip()
        if not t:
            continue
        # Check yellow highlight in runs (7 = yellow)
        p_highlight = any(r.font.highlight_color == 7 for r in p.runs)
        
        km = re.match(r'^(\d+)\.\s+(.*)', t)
        if km:
            if current_clause_lines:
                clauses.append((current_clause_num, current_clause_lines, current_clause_highlight))
            current_clause_num = int(km.group(1))
            current_clause_lines = [t]
            current_clause_highlight = p_highlight
        else:
            if current_clause_lines:
                current_clause_lines.append(t)
                if p_highlight:
                    current_clause_highlight = True
            else:
                current_clause_lines.append(t)
                if p_highlight:
                    current_clause_highlight = True
                    
    if current_clause_lines:
        clauses.append((current_clause_num, current_clause_lines, current_clause_highlight))
        
    # Build formatted consolidated text with citations
    out_parts = [title]
    for knum, lines, is_hl in clauses:
        clause_body = "\n".join(lines)
        if knum is not None:
            if is_hl and amending_art:
                cit = f"(Căn cứ: Khoản {knum} Điều {dnum} Nghị định 243/2025/NĐ-CP; được sửa đổi, bổ sung bởi Điều {amending_art} Nghị định 377/2026/NĐ-CP ngày 01/10/2026, có hiệu lực từ ngày 01/10/2026)"
            else:
                cit = f"(Căn cứ: Khoản {knum} Điều {dnum} Nghị định 243/2025/NĐ-CP)"
        else:
            if is_hl and amending_art:
                cit = f"(Căn cứ: Điều {dnum} Nghị định 243/2025/NĐ-CP; được sửa đổi, bổ sung bởi Điều {amending_art} Nghị định 377/2026/NĐ-CP ngày 01/10/2026, có hiệu lực từ ngày 01/10/2026)"
            else:
                cit = f"(Căn cứ: Điều {dnum} Nghị định 243/2025/NĐ-CP)"
        out_parts.append(f"{clause_body}\n{cit}")
        
    database[str(dnum)] = {
        "title": title,
        "has_yellow_highlight": any(any(r.font.highlight_color == 7 for r in p.runs) for p in paras),
        "nd377_amending_article": amending_art,
        "full_consolidated_text": "\n\n".join(out_parts)
    }

# Also ensure specific precision for Điều 28 (Điểm d is amended):
# In Điều 28, Khoản 2 has điểm a, b, c, d, đ, e where điểm d has highlight
if "28" in database:
    d28_text = (
        "Điều 28. Lập, thẩm định báo cáo nghiên cứu khả thi, phê duyệt dự án áp dụng loại hợp đồng BT không yêu cầu thanh toán\n\n"
        "1. Điều kiện đối với dự án áp dụng loại hợp đồng BT không yêu cầu thanh toán do nhà đầu tư đề xuất:\n"
        "a) Phù hợp với điều kiện lựa chọn dự án để đầu tư theo phương thức PPP quy định tại các điểm a, b và c khoản 1 Điều 14 của Luật PPP.\n"
        "b) Không trùng với dự án PPP đang được cơ quan có thẩm quyền tổ chức lập báo cáo nghiên cứu tiền khả thi, báo cáo nghiên cứu khả thi hoặc đã chấp thuận nhà đầu tư khác lập báo cáo nghiên cứu tiền khả thi, báo cáo nghiên cứu khả thi.\n"
        "c) Phù hợp với kế hoạch phát triển kinh tế - xã hội và quy hoạch có liên quan theo quy định của pháp luật về quy hoạch đã được cấp có thẩm quyền quyết định hoặc phê duyệt.\n"
        "(Căn cứ: Khoản 1 Điều 28 Nghị định 243/2025/NĐ-CP)\n\n"
        "2. Trình tự đề xuất, thẩm định, phê duyệt dự án:\n"
        "a) Nhà đầu tư gửi văn bản đề xuất thực hiện dự án đến cơ quan có thẩm quyền theo hình thức trực tiếp hoặc trực tuyến.\n"
        "(Căn cứ: Điểm a Khoản 2 Điều 28 Nghị định 243/2025/NĐ-CP)\n"
        "b) Cơ quan có thẩm quyền xem xét, trả lời bằng văn bản chấp thuận hoặc không chấp thuận việc nhà đầu tư lập báo cáo nghiên cứu khả thi và dự thảo hợp đồng trong thời hạn 05 ngày làm việc kể từ ngày nhận được văn bản đề xuất. Văn bản chấp thuận gồm các nội dung theo quy định tại khoản 2 Điều 26 của Nghị định này.\n"
        "(Căn cứ: Điểm b Khoản 2 Điều 28 Nghị định 243/2025/NĐ-CP)\n"
        "c) Trường hợp được chấp thuận, nhà đầu tư lập hồ sơ đề xuất dự án gồm: dự thảo báo cáo nghiên cứu khả thi theo quy định của pháp luật về xây dựng và pháp luật có liên quan, dự thảo hợp đồng, hồ sơ về tư cách pháp lý của nhà đầu tư và gửi cơ quan có thẩm quyền. Trường hợp không được chấp thuận thì nhà đầu tư chịu mọi chi phí, rủi ro.\n"
        "(Căn cứ: Điểm c Khoản 2 Điều 28 Nghị định 243/2025/NĐ-CP)\n"
        "d) Cơ quan có thẩm quyền tổ chức thẩm định hồ sơ đề xuất dự án theo quy định tại các điểm a, b và đ khoản 1 và khoản 3 Điều 22 Nghị định này. Số lượng hồ sơ thẩm định được quy định tại khoản 2 Điều 21 của Nghị định này;\n"
        "(Căn cứ: Điểm d Khoản 2 Điều 28 Nghị định 243/2025/NĐ-CP; được sửa đổi, bổ sung bởi Điều 17 Nghị định 377/2026/NĐ-CP có hiệu lực từ ngày 01/10/2026)\n"
        "đ) Cơ quan có thẩm quyền phê duyệt dự án kèm theo dự thảo hợp đồng theo quy định tại khoản 1 Điều 24 của Nghị định này và Mẫu số 04 Phụ lục II kèm theo Nghị định này.\n"
        "(Căn cứ: Điểm đ Khoản 2 Điều 28 Nghị định 243/2025/NĐ-CP)\n"
        "e) Đối với dự án thuộc trường hợp chỉ cần lập báo cáo kinh tế - kỹ thuật đầu tư xây dựng, nhà đầu tư lập báo cáo kinh tế - kỹ thuật gửi cơ quan có thẩm quyền kèm văn bản đề xuất. Khi được chấp thuận, cơ quan có thẩm quyền tổ chức thẩm định, phê duyệt và thực hiện theo pháp luật về xây dựng mà không cần thực hiện các điểm c, d và đ khoản này.\n"
        "(Căn cứ: Điểm e Khoản 2 Điều 28 Nghị định 243/2025/NĐ-CP)"
    )
    database["28"]["full_consolidated_text"] = d28_text

# Also ensure specific precision for Điều 43 (Khoản 1 is amended):
if "43" in database:
    d43_text = (
        "Điều 43. Phương pháp và tiêu chuẩn đánh giá về tài chính - thương mại\n\n"
        "1. Việc đánh giá về tài chính - thương mại căn cứ theo phương pháp so sánh, xếp hạng quy định trong hồ sơ mời thầu. Hồ sơ mời thầu phải xác định một, một số hoặc kết hợp các tiêu chuẩn về giá, phí sản phẩm, dịch vụ công; vốn nhà nước hỗ trợ xây dựng công trình, hệ thống cơ sở hạ tầng; lợi ích xã hội, lợi ích nhà nước quy định tại các điểm a, b và c khoản 3 Điều 42 của Luật PPP để so sánh, xếp hạng nhà đầu tư đáp ứng yêu cầu về tài chính - thương mại.\n"
        "Đối với dự án áp dụng loại hợp đồng hỗn hợp, hồ sơ mời thầu xác định một, một số hoặc kết hợp các tiêu chuẩn đánh giá, bảo đảm phù hợp với loại hợp đồng, phương án tài chính, phương án thu hồi vốn của nhà đầu tư.\n"
        "(Căn cứ: Khoản 1 Điều 43 Nghị định 243/2025/NĐ-CP; được sửa đổi, bổ sung bởi Điều 22 Nghị định 377/2026/NĐ-CP ngày 01/10/2026, có hiệu lực từ ngày 01/10/2026)\n\n"
        "2. Sau khi đánh giá về tài chính - thương mại, trường hợp có từ hai nhà đầu tư trở lên có đề xuất về tài chính - thương mại ngang nhau thì nhà đầu tư có kinh nghiệm thực hiện dự án tương tự cao hơn được xếp thứ nhất.\n"
        "(Căn cứ: Khoản 2 Điều 43 Nghị định 243/2025/NĐ-CP)\n\n"
        "3. Nhà đầu tư được xếp thứ nhất và được đề nghị lựa chọn khi đáp ứng các điều kiện sau đây:\n"
        "a) Hồ sơ dự thầu hợp lệ;\n"
        "b) Đáp ứng yêu cầu về năng lực;\n"
        "c) Đáp ứng yêu cầu về kỹ thuật;\n"
        "d) Đáp ứng yêu cầu về tài chính - thương mại;\n"
        "đ) Có đề xuất về tài chính - thương mại trong hồ sơ dự thầu không thấp hơn mức tối thiểu và cao nhất hoặc không cao hơn mức tối đa và thấp nhất căn cứ tiêu chuẩn đánh giá trong hồ sơ mời thầu.\n"
        "(Căn cứ: Khoản 3 Điều 43 Nghị định 243/2025/NĐ-CP)"
    )
    database["43"]["full_consolidated_text"] = d43_text

# Also ensure specific precision for Điều 72 (Khoản 2, 3, 4 amended/added):
if "72" in database:
    d72_text = (
        "Điều 72. Giám sát hoạt động đầu tư theo phương thức PPP\n\n"
        "1. Cơ quan quản lý nhà nước về đầu tư theo phương thức PPP, cơ quan quản lý nhà nước chuyên ngành, cơ quan có thẩm quyền, cơ quan ký kết hợp đồng thực hiện giám sát hoạt động đầu tư theo phương thức PPP theo quy định của Chính phủ về giám sát, đánh giá đầu tư.\n"
        "(Căn cứ: Khoản 1 Điều 72 Nghị định 243/2025/NĐ-CP)\n\n"
        "2. Ngoài trách nhiệm giám sát quy định tại khoản 1 Điều này, cơ quan ký kết hợp đồng có trách nhiệm bảo đảm nhà đầu tư, doanh nghiệp dự án (nếu có) thực hiện đầy đủ nghĩa vụ, trách nhiệm theo hợp đồng đã ký kết đáp ứng yêu cầu về tiến độ, chất lượng, hiệu quả đầu tư của dự án như sau:\n"
        "a) Giám sát chất lượng công trình, hệ thống cơ sở hạ tầng trong quá trình thi công xây dựng theo quy định tại khoản 2 Điều 59 của Luật PPP;\n"
        "b) Giám sát chất lượng sản phẩm, dịch vụ công do nhà đầu tư, doanh nghiệp dự án cung cấp theo quy định tại khoản 2 và khoản 3 Điều 66 của Luật PPP;\n"
        "c) Giám sát tình hình thực hiện huy động vốn đầu tư để thực hiện dự án gồm vốn nhà nước, vốn chủ sở hữu, vốn vay của nhà đầu tư, doanh nghiệp dự án PPP. Trường hợp cần thiết, cơ quan có thẩm quyền thống nhất với nhà đầu tư, doanh nghiệp dự án PPP về việc thuê đơn vị kiểm toán độc lập thực hiện kiểm toán báo cáo tài chính của nhà đầu tư, doanh nghiệp dự án. Chi phí thuê đơn vị kiểm toán độc lập quy định tại điểm này thực hiện tương tự như chi phí thuê tư vấn kiểm định chất lượng quy định tại khoản 4 Điều 59 Luật PPP.\n"
        "(Căn cứ: Khoản 2 Điều 72 Nghị định 243/2025/NĐ-CP; được sửa đổi, bổ sung bởi Điều 27 Nghị định 377/2026/NĐ-CP ngày 01/10/2026, có hiệu lực từ ngày 01/10/2026)\n\n"
        "3. Sở Tài chính hoặc cơ quan, tổ chức, đơn vị được Bộ trưởng, người đứng đầu cơ quan trung ương, cơ quan khác giao thực hiện nhiệm vụ quản lý về hoạt động đầu tư theo phương thức PPP (độc lập với bên mời thầu, tổ chuyên gia) thực hiện giám sát hoạt động lựa chọn nhà đầu tư đối với các dự án sau đây:\n"
        "a) Dự án thuộc trường hợp chỉ định nhà đầu tư quy định tại Điều 55 của Nghị định này;\n"
        "b) Dự án thuộc trường hợp lựa chọn nhà đầu tư trong trường hợp đặc biệt quy định tại Điều 57 của Nghị định này;\n"
        "c) Dự án không thuộc trường hợp quy định tại các điểm a và điểm b khoản này nhưng người đứng đầu cơ quan có thẩm quyền quyết định thực hiện giám sát (nếu cần thiết).\n"
        "(Căn cứ: Khoản 3 Điều 72 Nghị định 243/2025/NĐ-CP; được sửa đổi, bổ sung bởi Điều 27 Nghị định 377/2026/NĐ-CP ngày 01/10/2026, có hiệu lực từ ngày 01/10/2026)\n\n"
        "4. Đối với dự án thuộc trường hợp quy định tại khoản 3 Điều này, ngoài các nội dung giám sát theo quy định của Chính phủ về trình tự, thủ tục thẩm định dự án quan trọng quốc gia và giám sát, đánh giá đầu tư, nội dung giám sát gồm:\n"
        "a) Tình hình, tiến độ, kết quả của việc áp dụng các hình thức lựa chọn nhà đầu tư;\n"
        "b) Đánh giá kết quả việc áp dụng hình thức chỉ định nhà đầu tư, lựa chọn nhà đầu tư trong trường hợp đặc biệt;\n"
        "c) Đánh giá quá trình triển khai dự án của nhà đầu tư, doanh nghiệp dự án (nếu có), bảo đảm tuân thủ các cam kết theo hợp đồng dự án.\n"
        "(Căn cứ: Khoản 4 Điều 72 Nghị định 243/2025/NĐ-CP; được sửa đổi, bổ sung bởi Điều 27 Nghị định 377/2026/NĐ-CP ngày 01/10/2026, có hiệu lực từ ngày 01/10/2026)"
    )
    database["72"]["full_consolidated_text"] = d72_text

with open(output_json, "w", encoding="utf-8") as f:
    json.dump(database, f, ensure_ascii=False, indent=2)

print(f"Successfully generated database with {len(database)} articles at {output_json}")
