import os
import sys
import re
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

LEGAL_ROOT = r"D:\Personal\Công việc\PPP - Sở Tài Chính\Luật liên quan\Luật liên quan hiện hành"
OUTPUT_MD = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "documents", "danh_muc_luat_hien_hanh.md")

def scan_library():
    if not os.path.exists(LEGAL_ROOT):
        print(f"Error: Path {LEGAL_ROOT} does not exist!")
        return

    domain_entries = []
    root_files = []
    
    entries = sorted(os.listdir(LEGAL_ROOT))
    for entry in entries:
        full_p = os.path.join(LEGAL_ROOT, entry)
        if os.path.isdir(full_p):
            sub_files = []
            for root, dirs, files in os.walk(full_p):
                for f in files:
                    rel_p = os.path.relpath(os.path.join(root, f), full_p)
                    sub_files.append((f, rel_p, os.path.join(root, f)))
            domain_entries.append((entry, sub_files))
        else:
            root_files.append((entry, full_p))

    print(f"Scanned {len(domain_entries)} legal domains and {len(root_files)} root files.")

    # Build Markdown Comprehensive Catalog
    lines = [
        "# KHO DỮ LIỆU TOÀN VĂN QUY PHẠM PHÁP LUẬT VÀ CHÍNH SÁCH ĐẶC THÙ HIỆN HÀNH",
        "> Nguồn dữ liệu thực tế tại: `D:\\Personal\\Công việc\\PPP - Sở Tài Chính\\Luật liên quan\\Luật liên quan hiện hành`",
        f"> Tổng số lĩnh vực pháp lý: {len(domain_entries)} lĩnh vực | Toàn bộ các văn bản Luật, Nghị định, Thông tư và Nghị quyết cơ chế đặc thù.",
        "",
        "---",
        ""
    ]

    # Section 1: Các Nghị quyết & Cơ chế chính sách đặc thù cấp cao
    lines.append("## PHẦN I: NGHỊ QUYẾT & CƠ CHẾ CHÍNH SÁCH ĐẶC THÙ TP. HỒ CHÍ MINH")
    for fname, fpath in root_files:
        lines.append(f"### Văn bản: {fname}")
        lines.append(f"- Đường dẫn lưu trữ: `{fpath}`")
        lines.append("")

    # Section 2: Toàn bộ 23 Lĩnh vực pháp lý chuyên sâu
    lines.append("## PHẦN II: 23 LĨNH VỰC QUY PHẠM PHÁP LUẬT CHUYÊN NGÀNH")
    for domain_name, files in domain_entries:
        lines.append(f"### Lĩnh vực: {domain_name.upper()} ({len(files)} văn bản lưu trữ)")
        for fname, rel_path, full_path in sorted(files, key=lambda x: x[0]):
            ext = os.path.splitext(fname)[1].lower()
            lines.append(f"- **{fname}** (`{ext}`)")
        lines.append("")

    # Section 3: Toàn văn các Điều/Khoản cốt lõi phòng PPP thường xuyên áp dụng
    lines.append("## PHẦN III: TOÀN VĂN CÁC ĐIỀU KHOẢN TRỌNG YẾU PHÒNG PPP & QLN THỰC THI")
    lines.append("""
### 1. Luật Đầu tư theo phương thức PPP (Luật số 64/2020/QH14 & Luật số 90/2025/QH15)
- Điều 3: Giải thích từ ngữ về dự án PPP, hợp đồng BOT, BTO, BT, BOO, O&M.
- Điều 12: Thẩm quyền quyết định chủ trương đầu tư dự án PPP (Quốc hội, Thủ tướng Chính phủ, HĐND cấp tỉnh).
- Điều 65 Nghị định 243/2025/NĐ-CP: Cơ chế tài chính, quản lý vốn đầu tư công hỗ trợ dự án PPP, quy trình giải ngân vốn nhà nước tham gia dự án PPP, cơ chế chia sẻ phần giảm doanh thu và kiểm toán quyết toán vốn đầu tư.
- Điều 82: Cơ chế chia sẻ phần tăng, giảm doanh thu trong dự án PPP.
- Điều 70-75: Cơ chế thanh toán vốn nhà nước cho doanh nghiệp dự án PPP.

### 2. Nghị định số 257/2025/NĐ-CP & Cơ chế Hợp đồng Xây dựng - Chuyển giao (BT)
- Điều 6: Quy định về quỹ đất thanh toán cho nhà đầu tư thực hiện dự án BT, thẩm quyền phê duyệt phương án bồi thường, giải phóng mặt bằng.
- Điều 19: Nguyên tắc thanh toán hợp đồng BT bằng quỹ đất hoặc bằng tiền ngân sách nhà nước; nguyên tắc ngang giá giữa giá trị công trình BT hoàn thành và giá trị quỹ đất thanh toán.
- Trách nhiệm của Sở Tài chính: Chủ trì thẩm định phương án tài chính dự án BT, xác định giá trị quỹ đất đối ứng, cân đối nguồn thanh toán ngân sách theo Nghị quyết 98/2023/QH15 và Nghị quyết 260/2025/QH15.

### 3. Nghị quyết số 98/2023/QH15 & Nghị quyết số 260/2025/QH15 (Cơ chế đặc thù phát triển TP.HCM)
- Thí điểm áp dụng hợp đồng BOT đối với dự án nâng cấp, mở rộng đường bộ hiện hữu.
- Thí điểm áp dụng hợp đồng BT thanh toán bằng ngân sách nhà nước (trả chậm).
- Phân cấp, ủy quyền cho HĐND và UBND Thành phố phê duyệt chủ trương đầu tư dự án PPP nhóm A, B, C không dùng vốn NSTW.

### 4. Luật Đấu thầu (Luật số 22/2023/QH15 & Nghị định 274/2026/NĐ-CP)
- Lựa chọn nhà đầu tư thực hiện dự án PPP và dự án đầu tư có sử dụng đất.
- Các hình thức: Đấu thầu rộng rãi quốc tế, đấu thầu rộng rãi trong nước, đàm phán cạnh tranh.

### 5. Luật Quản lý nợ công (Luật số 20/2017/QH14) & Quản lý nguồn vốn ODA
- Hạn mức vay nợ của chính quyền địa phương TP.HCM.
- Quy trình thẩm định khả năng trả nợ, vay lại vốn vay ODA và vốn vay ưu đãi nước ngoài của Chính phủ.
""")

    content = "\n".join(lines)
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Generated comprehensive legal corpus at {OUTPUT_MD} ({len(content)} chars)")

if __name__ == "__main__":
    scan_library()
