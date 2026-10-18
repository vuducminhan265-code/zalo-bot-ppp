# Function department/tools/thuvienphapluat_crawler.py
import sys
import os
import re
import json
import urllib.parse
import urllib.request
from typing import Dict, Any, List

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

class ThuvienPhapLuatCrawler:
    """
    Crawler & Legal Cross-Reference Tool for Thư viện Pháp luật (thuvienphapluat.vn).
    Account Credentials: pppqln / 123456 (Premium)
    Provides automated lookup for:
    1. Newly issued decrees and guiding regulations (e.g., Nghị định 377/2026/NĐ-CP).
    2. Yellow-highlighted amendment clauses (nội dung bôi vàng: sửa đổi, bổ sung, bãi bỏ).
    3. Cross-law synthesis mapping (Luật PPP 64/2020 + NĐ 243/2025 + NĐ 257/2025 + Luật Đầu tư công 58/2024).
    """

    def __init__(self, username: str = "pppqln", password: str = "123456"):
        self.username = username
        self.password = password
        self.base_url = "https://thuvienphapluat.vn"
        
        # Load Full 82-Article In-Place Consolidated Database for NĐ 243/2025
        json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rag_engine", "nd243_full_consolidated_database.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    self.nd243_db = json.load(f)
            except Exception:
                self.nd243_db = {}
        else:
            self.nd243_db = {}

        # Comprehensive Legal Knowledge Graph & Amendment Registry
        self.hierarchy_map = {
            "377/2026": {
                "name": "Nghị định 377/2026/NĐ-CP (ban hành 01/10/2026, có hiệu lực từ 01/10/2026)",
                "description": "Nghị định sửa đổi, bổ sung một số điều của các Nghị định quy định chi tiết một số điều của Luật Đầu tư theo phương thức đối tác công tư (sửa đổi NĐ 243/2025/NĐ-CP, NĐ 257/2025/NĐ-CP, NĐ 312/2025/NĐ-CP).",
                "yellow_highlight_amendments": [
                    {
                        "target_doc": "Nghị định 243/2025/NĐ-CP",
                        "article": "Điểm d Khoản 3 Điều 5",
                        "type": "Bổ sung",
                        "content": "Bổ sung điểm d vào sau điểm c khoản 3 Điều 5: Trường hợp thuê tư vấn nước ngoài, liên danh tư vấn trong nước và tư vấn nước ngoài hoặc không có định mức thì dự toán chi phí thẩm tra được lập theo quy định về trình tự, thủ tục thẩm định dự án quan trọng quốc gia và giám sát, đánh giá đầu tư.",
                        "citation": "Điểm d Khoản 3 Điều 5 Nghị định 243/2025/NĐ-CP (bổ sung bởi Nghị định 377/2026/NĐ-CP có hiệu lực từ 01/10/2026)"
                    },
                    {
                        "target_doc": "Nghị định 243/2025/NĐ-CP",
                        "article": "Khoản 2 Điều 6",
                        "type": "Sửa đổi",
                        "content": "Phân cấp thẩm quyền quyết định cho cơ quan, tổ chức, đơn vị trực thuộc, UBND cấp xã, đơn vị sự nghiệp công lập làm cơ quan có thẩm quyền đối với: (a) Dự án PPP có TMĐT tương đương nhóm B, nhóm C; (b) Dự án áp dụng loại hợp đồng O&M.",
                        "citation": "Khoản 2 Điều 6 Nghị định 243/2025/NĐ-CP (sửa đổi bởi Nghị định 377/2026/NĐ-CP có hiệu lực từ 01/10/2026)"
                    },
                    {
                        "target_doc": "Nghị định 243/2025/NĐ-CP",
                        "article": "Khoản 4 Điều 7",
                        "type": "Sửa đổi",
                        "content": "Thẩm quyền quyết định chủ trương đầu tư dự án PPP quy định tại Khoản 3 Điều 11 Luật PPP thuộc Bộ trưởng, người đứng đầu cơ quan trung ương, HĐND cấp tỉnh, UBND cấp tỉnh theo quy định tại các khoản 3, 4 và 5 Điều 12 Luật PPP.",
                        "citation": "Khoản 4 Điều 7 Nghị định 243/2025/NĐ-CP (sửa đổi bởi Nghị định 377/2026/NĐ-CP có hiệu lực từ 01/10/2026)"
                    },
                    {
                        "target_doc": "Nghị định 243/2025/NĐ-CP",
                        "article": "Khoản 6 Điều 10",
                        "type": "Bổ sung",
                        "content": "Trường hợp thành lập Hội đồng thẩm định, cơ quan thường trực của Hội đồng thẩm định thực hiện trách nhiệm của đơn vị thẩm định dự án quy định tại khoản 4 và khoản 5 Điều 10.",
                        "citation": "Khoản 6 Điều 10 Nghị định 243/2025/NĐ-CP (bổ sung bởi Nghị định 377/2026/NĐ-CP có hiệu lực từ 01/10/2026)"
                    },
                    {
                        "target_doc": "Nghị định 243/2025/NĐ-CP",
                        "article": "Điểm d Khoản 2 Điều 28",
                        "type": "Sửa đổi, bổ sung trực tiếp",
                        "replacement_text": "d) Cơ quan có thẩm quyền tổ chức thẩm định hồ sơ đề xuất dự án theo quy định tại các điểm a, b và đ khoản 1 và khoản 3 Điều 22 Nghị định này. Số lượng hồ sơ thẩm định được quy định tại khoản 2 Điều 21 của Nghị định này;",
                        "content": "Thay thế câu văn quy định cũ bằng: “d) Cơ quan có thẩm quyền tổ chức thẩm định hồ sơ đề xuất dự án theo quy định tại các điểm a, b và đ khoản 1 và khoản 3 Điều 22 Nghị định này. Số lượng hồ sơ thẩm định được quy định tại khoản 2 Điều 21 của Nghị định này;”.",
                        "citation": "Điểm d Khoản 2 Điều 28 Nghị định 243/2025/NĐ-CP; được sửa đổi, bổ sung bởi Điều 17 Nghị định 377/2026/NĐ-CP có hiệu lực từ ngày 01/10/2026"
                    },
                    {
                        "target_doc": "Nghị định 243/2025/NĐ-CP",
                        "article": "Điều 26",
                        "type": "Sửa đổi",
                        "content": "Nhà đầu tư nộp văn bản đề xuất dự án PPP trên Hệ thống mạng đấu thầu quốc gia. Khi chưa thực hiện qua mạng, nộp qua Trung tâm Phục vụ hành chính công cấp tỉnh (Sở Tài chính tiếp nhận hồ sơ trong 02 ngày làm việc). Cơ quan có thẩm quyền xem xét sơ bộ và trả lời chấp thuận/không chấp thuận trong thời hạn 10 ngày làm việc.",
                        "citation": "Khoản 1 và Khoản 2 Điều 26 Nghị định 243/2025/NĐ-CP (sửa đổi bởi Nghị định 377/2026/NĐ-CP có hiệu lực từ 01/10/2026)"
                    },
                    {
                        "target_doc": "Nghị định 243/2025/NĐ-CP",
                        "article": "Điểm c Khoản 1 Điều 42",
                        "type": "Sửa đổi, bổ sung",
                        "content": "c) Tiêu chuẩn về môi trường và an toàn, gồm: Yêu cầu về phương án bảo vệ môi trường và an toàn mà nhà đầu tư phải bảo đảm theo quy định của pháp luật về môi trường; ưu tiên cho nhà đầu tư đề xuất giải pháp giảm phát sinh chất thải, thúc đẩy sản phẩm, dịch vụ thân thiện môi trường, nhà đầu tư huy động vốn vay từ nguồn tài chính xanh hoặc nguồn vốn hợp pháp khác phục vụ mục tiêu bảo vệ môi trường, chuyển đổi xanh theo quy định của pháp luật; ưu tiên chuyển giao và áp dụng công nghệ chiến lược, tiên tiến, công nghệ cao, công nghệ mới, công nghệ thân thiện môi trường, kỹ thuật hiện có tốt nhất (đối với dự án thuộc nhóm có nguy cơ tác động xấu đến môi trường mức độ cao theo quy định của pháp luật về bảo vệ môi trường);",
                        "citation": "Điểm c Khoản 1 Điều 42 Nghị định 243/2025/NĐ-CP; được sửa đổi, bổ sung bởi Điều 21 Nghị định 377/2026/NĐ-CP có hiệu lực từ ngày 01/10/2026"
                    },
                    {
                        "target_doc": "Nghị định 243/2025/NĐ-CP",
                        "article": "Khoản 1 Điều 43",
                        "type": "Sửa đổi, bổ sung trực tiếp (Nội dung bôi vàng trên TVPL)",
                        "replacement_text": "1. Việc đánh giá về tài chính - thương mại căn cứ theo phương pháp so sánh, xếp hạng quy định trong hồ sơ mời thầu. Hồ sơ mời thầu phải xác định một, một số hoặc kết hợp các tiêu chuẩn về giá, phí sản phẩm, dịch vụ công; vốn nhà nước hỗ trợ xây dựng công trình, hệ thống cơ sở hạ tầng; lợi ích xã hội, lợi ích nhà nước quy định tại các điểm a, b và c khoản 3 Điều 42 của Luật PPP để so sánh, xếp hạng nhà đầu tư đáp ứng yêu cầu về tài chính - thương mại.\nĐối với dự án áp dụng loại hợp đồng hỗn hợp, hồ sơ mời thầu xác định một, một số hoặc kết hợp các tiêu chuẩn đánh giá, bảo đảm phù hợp với loại hợp đồng, phương án tài chính, phương án thu hồi vốn của nhà đầu tư.",
                        "content": "Sửa đổi, bổ sung Khoản 1 Điều 43: Bổ sung quy định đối với dự án áp dụng loại hợp đồng hỗn hợp, hồ sơ mời thầu xác định một, một số hoặc kết hợp các tiêu chuẩn đánh giá phù hợp với loại hợp đồng, phương án tài chính, phương án thu hồi vốn.",
                        "citation": "Khoản 1 Điều 43 Nghị định 243/2025/NĐ-CP; được sửa đổi, bổ sung bởi Điều 22 Nghị định 377/2026/NĐ-CP có hiệu lực từ ngày 01/10/2026"
                    },
                    {
                        "target_doc": "Nghị định 243/2025/NĐ-CP",
                        "article": "Điều 36",
                        "type": "Sửa đổi, bổ sung",
                        "content": "Lộ trình áp dụng lựa chọn nhà đầu tư qua mạng trên Hệ thống mạng đấu thầu quốc gia (thực hiện từ 01/01/2027 đối với thủ tục nộp văn bản đề xuất dự án quy định tại điểm a khoản 1 Điều 26 và khoản 1 Điều 27).",
                        "citation": "Điều 36 Nghị định 243/2025/NĐ-CP; được sửa đổi, bổ sung bởi Điều 20 Nghị định 377/2026/NĐ-CP có hiệu lực từ ngày 01/10/2026"
                    },
                    {
                        "target_doc": "Nghị định 257/2025/NĐ-CP",
                        "article": "Cơ chế tài chính & thanh toán hợp đồng BT",
                        "type": "Sửa đổi",
                        "content": "Quy định nguyên tắc xác định giá trị quỹ đất thanh toán hợp đồng BT, cơ chế bù trừ và quyết toán vốn đầu tư dự án BT hoàn thành.",
                        "citation": "Nghị định 257/2025/NĐ-CP (sửa đổi, bổ sung bởi Nghị định 377/2026/NĐ-CP có hiệu lực từ 01/10/2026)"
                    }
                ]
            },
            "243/2025": {
                "name": "Nghị định 243/2025/NĐ-CP hướng dẫn thi hành Luật PPP",
                "parent_law": "Luật Đầu tư theo phương thức đối tác công tư (Luật PPP số 64/2020/QH14)",
                "amended_by": "Được sửa đổi, bổ sung bởi Nghị định 377/2026/NĐ-CP ngày 01/10/2026",
                "dieu_28_consolidated": {
                    "title": "Điều 28. Lập, thẩm định báo cáo nghiên cứu khả thi, phê duyệt dự án áp dụng loại hợp đồng BT không yêu cầu thanh toán",
                    "khoan_1": [
                        "Phù hợp với điều kiện lựa chọn dự án để đầu tư theo phương thức PPP quy định tại các điểm a, b và c khoản 1 Điều 14 của Luật PPP.",
                        "Không trùng với dự án PPP đang được cơ quan có thẩm quyền tổ chức lập báo cáo nghiên cứu tiền khả thi, báo cáo nghiên cứu khả thi hoặc đã chấp thuận nhà đầu tư khác lập báo cáo nghiên cứu tiền khả thi, báo cáo nghiên cứu khả thi.",
                        "Phù hợp với kế hoạch phát triển kinh tế - xã hội và quy hoạch có liên quan theo quy định của pháp luật về quy hoạch đã được cấp có thẩm quyền quyết định hoặc phê duyệt."
                    ],
                    "khoan_2": {
                        "diem_a": "Nhà đầu tư gửi văn bản đề xuất thực hiện dự án đến cơ quan có thẩm quyền theo hình thức trực tiếp hoặc trực tuyến.",
                        "diem_b": "Cơ quan có thẩm quyền xem xét, trả lời bằng văn bản chấp thuận hoặc không chấp thuận việc nhà đầu tư lập báo cáo nghiên cứu khả thi và dự thảo hợp đồng trong thời hạn 05 ngày làm việc kể từ ngày nhận được văn bản đề xuất. Văn bản chấp thuận gồm các nội dung theo quy định tại khoản 2 Điều 26 của Nghị định này.",
                        "diem_c": "Trường hợp được chấp thuận, nhà đầu tư lập hồ sơ đề xuất dự án gồm: dự thảo báo cáo nghiên cứu khả thi theo quy định của pháp luật về xây dựng và pháp luật có liên quan, dự thảo hợp đồng, hồ sơ về tư cách pháp lý của nhà đầu tư và gửi cơ quan có thẩm quyền. Trường hợp không được chấp thuận thì nhà đầu tư chịu mọi chi phí, rủi ro.",
                        "diem_d_amended": "Cơ quan có thẩm quyền tổ chức thẩm định hồ sơ đề xuất dự án theo quy định tại các điểm a, b và đ khoản 1 và khoản 3 Điều 22 Nghị định này. Số lượng hồ sơ thẩm định được quy định tại khoản 2 Điều 21 của Nghị định này.",
                        "diem_d_citation": "Điểm d Khoản 2 Điều 28 Nghị định 243/2025/NĐ-CP (được sửa đổi, bổ sung bởi Điều 17 Nghị định 377/2026/NĐ-CP có hiệu lực từ ngày 01/10/2026)",
                        "diem_dd": "Cơ quan có thẩm quyền phê duyệt dự án kèm theo dự thảo hợp đồng theo quy định tại khoản 1 Điều 24 của Nghị định này và Mẫu số 04 Phụ lục II kèm theo Nghị định này.",
                        "diem_e": "Đối với dự án thuộc trường hợp chỉ cần lập báo cáo kinh tế - kỹ thuật đầu tư xây dựng, nhà đầu tư lập báo cáo kinh tế - kỹ thuật gửi cơ quan có thẩm quyền kèm văn bản đề xuất. Khi được chấp thuận, cơ quan có thẩm quyền tổ chức thẩm định, phê duyệt và thực hiện theo pháp luật về xây dựng mà không cần thực hiện các điểm c, d và đ khoản này."
                    }
                },
                "dieu_43_consolidated": {
                    "title": "Điều 43. Phương pháp và tiêu chuẩn đánh giá về tài chính - thương mại",
                    "intro": "VĂN BẢN HỢP NHẤT HIỆN HÀNH ĐIỀU 43 NGHỊ ĐỊNH 243/2025/NĐ-CP (ĐÃ CẬP NHẬT CÂU VĂN BÔI VÀNG SỬA ĐỔI, BỔ SUNG THEO ĐIỀU 22 NGHỊ ĐỊNH 377/2026/NĐ-CP):",
                    "khoan_1": "1. Việc đánh giá về tài chính - thương mại căn cứ theo phương pháp so sánh, xếp hạng quy định trong hồ sơ mời thầu. Hồ sơ mời thầu phải xác định một, một số hoặc kết hợp các tiêu chuẩn về giá, phí sản phẩm, dịch vụ công; vốn nhà nước hỗ trợ xây dựng công trình, hệ thống cơ sở hạ tầng; lợi ích xã hội, lợi ích nhà nước quy định tại các điểm a, b và c khoản 3 Điều 42 của Luật PPP để so sánh, xếp hạng nhà đầu tư đáp ứng yêu cầu về tài chính - thương mại.\nĐối với dự án áp dụng loại hợp đồng hỗn hợp, hồ sơ mời thầu xác định một, một số hoặc kết hợp các tiêu chuẩn đánh giá, bảo đảm phù hợp với loại hợp đồng, phương án tài chính, phương án thu hồi vốn của nhà đầu tư.\n(Căn cứ: Khoản 1 Điều 43 Nghị định 243/2025/NĐ-CP; được sửa đổi, bổ sung bởi Điều 22 Nghị định 377/2026/NĐ-CP ngày 01/10/2026, có hiệu lực từ ngày 01/10/2026)",
                    "khoan_2": "2. Sau khi đánh giá về tài chính - thương mại, trường hợp có từ hai nhà đầu tư trở lên có đề xuất về tài chính - thương mại ngang nhau thì nhà đầu tư có kinh nghiệm thực hiện dự án tương tự cao hơn được xếp thứ nhất.\n(Căn cứ: Khoản 2 Điều 43 Nghị định 243/2025/NĐ-CP)",
                    "khoan_3": "3. Nhà đầu tư được xếp thứ nhất và được đề nghị lựa chọn khi đáp ứng các điều kiện sau đây:\na) Hồ sơ dự thầu hợp lệ;\nb) Đáp ứng yêu cầu về năng lực;\nc) Đáp ứng yêu cầu về kỹ thuật;\nd) Đáp ứng yêu cầu về tài chính - thương mại;\nđ) Có đề xuất về tài chính - thương mại trong hồ sơ dự thầu không thấp hơn mức tối thiểu và cao nhất hoặc không cao hơn mức tối đa và thấp nhất căn cứ tiêu chuẩn đánh giá trong hồ sơ mời thầu.\n(Căn cứ: Khoản 3 Điều 43 Nghị định 243/2025/NĐ-CP)"
                },
                "hồ_sơ_cần_lập": [
                    {
                        "loai_du_an": "Dự án Quan trọng quốc gia, Dự án Nhóm A, Dự án ứng dụng công nghệ cao hoặc năng lượng hạt nhân",
                        "hồ_sơ": "Báo cáo nghiên cứu tiền khả thi (BCNCTKT) theo Mẫu số 01 Phụ lục I ban hành kèm theo Nghị định 243/2025/NĐ-CP.",
                        "citation": "Khoản 1 Điều 14 Luật PPP số 64/2020/QH14; Khoản 1 Điều 8 Nghị định 243/2025/NĐ-CP"
                    },
                    {
                        "loai_du_an": "Dự án Nhóm B, Dự án Nhóm C còn lại",
                        "hồ_sơ": "Báo cáo đề xuất chủ trương đầu tư theo Mẫu số 02 Phụ lục I ban hành kèm theo Nghị định 243/2025/NĐ-CP.",
                        "citation": "Khoản 2 Điều 14 Luật PPP số 64/2020/QH14; Khoản 2 Điều 8 Nghị định 243/2025/NĐ-CP"
                    }
                ]
            },
            "58/2024": {
                "name": "Luật Đầu tư công số 58/2024/QH15 (có hiệu lực từ 01/01/2025, thay thế toàn diện Luật 39/2019/QH14)",
                "tieu_chi_nhom_a": [
                    {
                        "lĩnh_vực": "Không phân biệt tổng mức đầu tư",
                        "chi_tiết": "Dự án thuộc địa bàn có di tích quốc gia đặc biệt; Dự án thuộc địa bàn có ý nghĩa quan trọng đối với quốc gia về quốc phòng, an ninh hoặc địa bàn có vị trí chiến lược về quốc phòng, an ninh; Dự án thuộc lĩnh vực bảo vệ tài nguyên, khoáng sản, môi trường có nguy cơ ô nhiễm môi trường cao; Dự án hạ tầng khu công nghiệp, khu chế xuất, khu công nghệ cao.",
                        "citation": "Khoản 1 Điều 9 Luật Đầu tư công số 58/2024/QH15"
                    },
                    {
                        "lĩnh_vực": "Tổng mức đầu tư từ 4.600 tỷ đồng trở lên",
                        "chi_tiết": "Giao thông (bao gồm cầu, cảng biển, cảng sông, sân bay, đường sắt, đường quốc lộ); Công nghiệp điện; Khai thác dầu khí; Hóa chất, phân bón, xi măng; Chế tạo máy, luyện kim; Khai thác, chế biến khoáng sản; Xây dựng khu nhà ở.",
                        "citation": "Khoản 2 Điều 9 Luật Đầu tư công số 58/2024/QH15"
                    },
                    {
                        "lĩnh_vực": "Tổng mức đầu tư từ 3.000 tỷ đồng trở lên",
                        "chi_tiết": "Giao thông, trừ dự án quy định tại điểm a khoản 2 Điều này; Thủy lợi; Cấp nước, thoát nước, xử lý rác thải và các công trình hạ tầng kỹ thuật khác; Kỹ thuật điện; Sản xuất thiết bị thông tin, điện tử; Hóa dược; Sản xuất vật liệu, trừ dự án quy định tại điểm d khoản 2 Điều này; Công trình cơ khí, trừ dự án quy định tại điểm đ khoản 2 Điều này; Khai thác, chế biến khoáng sản, trừ dự án quy định tại điểm e khoản 2 Điều này; Xây dựng công trình kỹ thuật khác.",
                        "citation": "Khoản 3 Điều 9 Luật Đầu tư công số 58/2024/QH15"
                    },
                    {
                        "lĩnh_vực": "Tổng mức đầu tư từ 2.000 tỷ đồng trở lên",
                        "chi_tiết": "Sản xuất nông nghiệp, lâm nghiệp, nuôi trồng thủy sản; Khu bảo tồn thiên nhiên; Hạ tầng kỹ thuật khu đô thị mới; Công nghiệp, trừ dự án quy định tại các khoản 2 và 3 Điều này.",
                        "citation": "Khoản 4 Điều 9 Luật Đầu tư công số 58/2024/QH15"
                    },
                    {
                        "lĩnh_vực": "Tổng mức đầu tư từ 1.600 tỷ đồng trở lên",
                        "chi_tiết": "a) Y tế, văn hóa, xã hội, thông tin, giáo dục;\nb) Nghiên cứu khoa học, môi trường, công nghệ thông tin, phát thanh, truyền hình, tài chính, ngân hàng (Nội dung bôi vàng trên Thư viện Pháp luật);\nc) Kho tàng;\nd) Du lịch, thể dục, thể thao;\nđ) Xây dựng dân dụng, trừ xây dựng khu nhà ở quy định tại điểm g khoản 2 Điều này;\ne) Dự án thuộc lĩnh vực quốc phòng, an ninh, trừ dự án quy định tại các khoản 1, 2, 3 và 4 Điều này.",
                        "citation": "Khoản 5 Điều 9 Luật Đầu tư công số 58/2024/QH15"
                    }
                ],
                "tieu_chi_nhom_b": [
                    {
                        "khoan": "Khoản 1",
                        "lĩnh_vực": "Dự án thuộc lĩnh vực quy định tại khoản 2 Điều 9 của Luật này (Giao thông gồm cầu, cảng biển, cảng sông, sân bay, đường sắt, quốc lộ; Công nghiệp điện; Khai thác dầu khí; Hóa chất, phân bón, xi măng; Chế tạo máy, luyện kim; Khai thác chế biến khoáng sản; Xây dựng khu nhà ở)",
                        "mức_tổng_mức_đầu_tư": "Từ 240 tỷ đồng đến dưới 4.600 tỷ đồng",
                        "citation": "Khoản 1 Điều 10 (tham chiếu lĩnh vực tại Khoản 2 Điều 9) Luật Đầu tư công số 58/2024/QH15"
                    },
                    {
                        "khoan": "Khoản 2",
                        "lĩnh_vực": "Dự án thuộc lĩnh vực quy định tại khoản 3 Điều 9 của Luật này (Giao thông khác; Thủy lợi; Cấp thoát nước, xử lý rác thải và hạ tầng kỹ thuật khác; Kỹ thuật điện; Sản xuất thiết bị thông tin, điện tử; Hóa dược; Sản xuất vật liệu; Cơ khí; Khai thác chế biến khoáng sản khác; Công trình kỹ thuật khác)",
                        "mức_tổng_mức_đầu_tư": "Từ 160 tỷ đồng đến dưới 3.000 tỷ đồng",
                        "citation": "Khoản 2 Điều 10 (tham chiếu lĩnh vực tại Khoản 3 Điều 9) Luật Đầu tư công số 58/2024/QH15"
                    },
                    {
                        "khoan": "Khoản 3",
                        "lĩnh_vực": "Dự án thuộc lĩnh vực quy định tại khoản 4 Điều 9 của Luật này (Sản xuất nông nghiệp, lâm nghiệp, nuôi trồng thủy sản; Khu bảo tồn thiên nhiên; Hạ tầng kỹ thuật khu đô thị mới; Công nghiệp khác)",
                        "mức_tổng_mức_đầu_tư": "Từ 120 tỷ đồng đến dưới 2.000 tỷ đồng",
                        "citation": "Khoản 3 Điều 10 (tham chiếu lĩnh vực tại Khoản 4 Điều 9) Luật Đầu tư công số 58/2024/QH15"
                    },
                    {
                        "khoan": "Khoản 4",
                        "lĩnh_vực": "Dự án thuộc lĩnh vực quy định tại khoản 5 Điều 9 của Luật này (a. Y tế, văn hóa, xã hội, thông tin, giáo dục; b. Nghiên cứu khoa học, môi trường, công nghệ thông tin, phát thanh, truyền hình, tài chính, ngân hàng [Nội dung bôi vàng trên Thư viện Pháp luật]; c. Kho tàng; d. Du lịch, thể dục, thể thao; đ. Xây dựng dân dụng, trừ xây dựng khu nhà ở quy định tại điểm g khoản 2 Điều 9; e. Dự án thuộc lĩnh vực quốc phòng, an ninh trừ các khoản 1, 2, 3 và 4 Điều 9)",
                        "mức_tổng_mức_đầu_tư": "Từ 90 tỷ đồng đến dưới 1.600 tỷ đồng",
                        "citation": "Khoản 4 Điều 10 (tham chiếu lĩnh vực tại Khoản 5 Điều 9) Luật Đầu tư công số 58/2024/QH15"
                    }
                ],
                "tieu_chi_nhom_c": [
                    {
                        "lĩnh_vực": "Dự án thuộc lĩnh vực quy định tại khoản 2 Điều 9",
                        "hạn_mức": "Tổng mức đầu tư dưới 240 tỷ đồng.",
                        "citation": "Khoản 1 Điều 11 Luật Đầu tư công số 58/2024/QH15"
                    },
                    {
                        "lĩnh_vực": "Dự án thuộc lĩnh vực quy định tại khoản 3 Điều 9",
                        "hạn_mức": "Tổng mức đầu tư dưới 160 tỷ đồng.",
                        "citation": "Khoản 2 Điều 11 Luật Đầu tư công số 58/2024/QH15"
                    },
                    {
                        "lĩnh_vực": "Dự án thuộc lĩnh vực quy định tại khoản 4 Điều 9",
                        "hạn_mức": "Tổng mức đầu tư dưới 120 tỷ đồng.",
                        "citation": "Khoản 3 Điều 11 Luật Đầu tư công số 58/2024/QH15"
                    },
                    {
                        "lĩnh_vực": "Dự án thuộc lĩnh vực quy định tại khoản 5 Điều 9",
                        "hạn_mức": "Tổng mức đầu tư dưới 90 tỷ đồng.",
                        "citation": "Khoản 4 Điều 11 Luật Đầu tư công số 58/2024/QH15"
                    }
                ]
            },
            "257/2025": {
                "name": "Nghị định 257/2025/NĐ-CP về thanh toán hợp đồng BT, BOT và quỹ đất PPP",
                "parent_law": "Luật Đầu tư theo phương thức đối tác công tư số 64/2020/QH14 và Luật Đất đai số 31/2024/QH15",
                "amended_by": "Nghị định 377/2026/NĐ-CP có hiệu lực từ 01/10/2026"
            }
        }

    def search_tvpl_live(self, query: str) -> List[Dict[str, str]]:
        """Active Search on Thư viện Pháp luật via DuckDuckGo Lite & HTML targeting thuvienphapluat.vn."""
        clean_q = query.replace('/', ' ')
        tvpl_query = f"site:thuvienphapluat.vn {clean_q}"
        encoded_data = urllib.parse.urlencode({'q': tvpl_query}).encode('utf-8')
        url = "https://lite.duckduckgo.com/lite/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        req = urllib.request.Request(url, data=encoded_data, headers=headers)
        results = []
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                snippets = re.findall(r'result-snippet[^>]*>(.*?)</td>', html, re.DOTALL)
                titles = re.findall(r'result-link[^>]*>(.*?)</a>', html, re.DOTALL)
                urls = re.findall(r'href=["\'](https?://[^"\']+)["\']', html)
                for idx in range(min(len(snippets), 6)):
                    clean_snip = re.sub(r'<[^>]+>', '', snippets[idx]).strip()
                    clean_title = re.sub(r'<[^>]+>', '', titles[idx]).strip() if idx < len(titles) else "Thư viện Pháp luật"
                    res_url = urls[idx] if idx < len(urls) else ""
                    if clean_snip:
                        results.append({
                            "title": clean_title,
                            "url": res_url,
                            "snippet": clean_snip,
                            "source": "Thư viện Pháp luật"
                        })
        except Exception as e:
            pass
        return results

    def search_tvpl_native(self, query: str) -> str:
        """Dynamic multi-domain search across all 23 fields of law (Môi trường, Chứng khoán, Đất đai, Thuế, Doanh nghiệp...)."""
        clean_q = re.sub(r'\b(cho tui|hỏi về|quy định về|chi tiết|như thế nào|với bro|hả bro|nhé)\b', '', query, flags=re.I).strip()
        encoded = urllib.parse.quote(clean_q)
        url = f"https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword={encoded}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://thuvienphapluat.vn/'
        }
        docs = []
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                for a in soup.find_all('a', href=re.compile(r'/van-ban/')):
                    href = a.get('href', '')
                    if 'tab=' not in href and 'step=' not in href and 'javascript' not in href:
                        title = a.get_text().strip()
                        if title and len(title) > 10:
                            doc_url = href if href.startswith('http') else f"https://thuvienphapluat.vn{href}"
                            if doc_url not in [d['url'] for d in docs]:
                                docs.append({"title": title, "url": doc_url})
        except Exception:
            pass

        if not docs:
            return ""

        res_str = "🌐 [TRA CỨU VĂN BẢN QUY PHẠM PHÁP LUẬT & NGHỊ ĐỊNH MỚI TRÊN THƯ VIỆN PHÁP LUẬT]:\n"
        for idx, d in enumerate(docs[:4], 1):
            res_str += f"{idx}. {d['title']}\n   - URL Thư viện Pháp luật: {d['url']}\n"
            # Inspect Tab 4 (Liên quan hiệu lực & Nội dung bôi vàng sửa đổi) for the top 2 documents
            if idx <= 2:
                try:
                    tab4_url = d['url'] + "?tab=4"
                    r_tab = urllib.request.Request(tab4_url, headers=headers)
                    with urllib.request.urlopen(r_tab, timeout=6) as resp_tab:
                        html_tab = resp_tab.read().decode('utf-8', errors='ignore')
                        soup_tab = BeautifulSoup(html_tab, 'html.parser')
                        text_tab = soup_tab.get_text(separator='\n')
                        lines = [l.strip() for l in text_tab.split('\n') if l.strip()]
                        changes = [l for l in lines if any(k in l.lower() for k in ['sửa đổi', 'thay thế', 'bổ sung', 'hướng dẫn thi hành', 'bãi bỏ'])]
                        if changes:
                            filtered_changes = []
                            for c in changes:
                                if len(c) > 20 and c not in filtered_changes and not any(skip in c.lower() for skip in ['hướng dẫn sử dụng', 'bản dịch này', 'đăng ký']):
                                    filtered_changes.append(c)
                            if filtered_changes:
                                res_str += "   ⚡ Điểm liên quan sửa đổi, bổ sung (nội dung bôi vàng):\n"
                                for fc in filtered_changes[:4]:
                                    res_str += f"     + {fc}\n"
                except Exception:
                    pass
            res_str += "\n"
        return res_str

    def fetch_legal_cross_reference(self, query: str) -> str:
        """
        Universal Master Legal Synthesis:
        1. Checks verified Knowledge Graph for exact matches (NĐ 377/2026, NĐ 243/2025, Luật 58/2024, etc.).
        2. Dynamically searches Thư viện Pháp luật natively across ANY legal domain (Môi trường, Chứng khoán, Đất đai, Đầu tư...).
        3. Detects yellow-highlighted amendment clauses (sửa đổi, bổ sung, bãi bỏ) via Tab 4.
        """
        q_lower = query.lower()
        cross_refs = []

        # 1. Match Yellow-Highlight & Decree Knowledge Graph
        for key, info in self.hierarchy_map.items():
            key_in_q = key in q_lower
            
            # Special context matches
            is_group_a_query = any(k in q_lower for k in ["nhóm a", "nhom a", "tiêu chí dự án nhóm a", "điều 9", "dieu 9"])
            is_group_b_query = any(k in q_lower for k in ["nhóm b", "nhom b", "tiêu chí dự án nhóm b", "điều 10", "dieu 10"])
            is_group_c_query = any(k in q_lower for k in ["nhóm c", "nhom c", "tiêu chí dự án nhóm c", "điều 11", "dieu 11"])
            is_dossier_query = any(k in q_lower for k in ["loại hồ sơ", "hồ sơ cần lập", "ho so can lap", "bcnctkt", "nghiên cứu tiền khả thi", "đề xuất chủ trương"])
            is_amendment_query = any(k in q_lower for k in ["377", "sửa đổi", "sua doi", "bôi vàng", "thay đổi", "mới nhất"])

            if key == "58/2024" and (key_in_q or is_group_a_query or is_group_b_query or is_group_c_query or "tổng mức" in q_lower or "tong muc" in q_lower):
                ref_str = "🏛️ [THƯ VIỆN PHÁP LUẬT & CƠ SỞ DỮ LIỆU LUẬT ĐẦU TƯ CÔNG SỐ 58/2024/QH15]\n"
                if is_group_b_query:
                    ref_str += "📌 TIÊU CHÍ PHÂN LOẠI DỰ ÁN NHÓM B (ĐIỀU 10 LUẬT ĐẦU TƯ CÔNG 58/2024/QH15 - CHỈ CÓ KHOẢN, KHÔNG CÓ ĐIỂM):\n"
                    for t in info.get("tieu_chi_nhom_b", []):
                        ref_str += f"• {t['khoan']}:\n  - Lĩnh vực: {t['lĩnh_vực']}\n  - Mức tổng mức đầu tư: {t['mức_tổng_mức_đầu_tư']}\n  (Căn cứ: {t['citation']})\n"
                if is_group_a_query or (key_in_q and not is_group_b_query and not is_group_c_query):
                    ref_str += "📌 TIÊU CHÍ PHÂN LOẠI DỰ ÁN NHÓM A (Điều 8 & Điều 9 Luật Đầu tư công 58/2024/QH15):\n"
                    for t in info.get("tieu_chi_nhom_a", []):
                        ref_str += f"• Lĩnh vực: {t['lĩnh_vực']}\n  - Chi tiết: {t['chi_tiết']}\n  (Căn cứ: {t['citation']})\n"
                if is_group_c_query:
                    ref_str += "📌 TIÊU CHÍ PHÂN LOẠI DỰ ÁN NHÓM C (Điều 11 Luật Đầu tư công 58/2024/QH15):\n"
                    for t in info.get("tieu_chi_nhom_c", []):
                        ref_str += f"• Lĩnh vực: {t['lĩnh_vực']}\n  - Hạn mức: {t['hạn_mức']}\n  (Căn cứ: {t['citation']})\n"
                cross_refs.append(ref_str)

            if key == "243/2025" and (key_in_q or is_dossier_query or "243" in q_lower or "bt" in q_lower or "ppp" in q_lower):
                ref_str = "🏛️ [THƯ VIỆN PHÁP LUẬT & NGHỊ ĐỊNH 243/2025/NĐ-CP - HƯỚNG DẪN LUẬT PPP]\n"
                
                # Check for specific article requested from full 82-article database
                dieu_m = re.search(r'điều\s*(\d+)', q_lower)
                if dieu_m and str(dieu_m.group(1)) in self.nd243_db:
                    dnum_str = str(dieu_m.group(1))
                    d_item = self.nd243_db[dnum_str]
                    amend_str = f" (ĐÃ CẬP NHẬT CÂU VĂN BÔI VÀNG SỬA ĐỔI, BỔ SUNG THEO ĐIỀU {d_item['nd377_amending_article']} NGHỊ ĐỊNH 377/2026/NĐ-CP)" if d_item.get("nd377_amending_article") else ""
                    ref_str += f"📌 VĂN BẢN HỢP NHẤT HIỆN HÀNH {d_item['title'].upper()}{amend_str}:\n\n"
                    ref_str += d_item['full_consolidated_text'] + "\n\n"
                elif "43" in q_lower or "tài chính - thương mại" in q_lower:
                    d43 = self.nd243_db.get("43", {})
                    if d43:
                        ref_str += f"📌 VĂN BẢN HỢP NHẤT HIỆN HÀNH {d43['title'].upper()} (ĐÃ CẬP NHẬT THEO ĐIỀU 22 NGHỊ ĐỊNH 377/2026/NĐ-CP):\n\n{d43['full_consolidated_text']}\n\n"
                elif "28" in q_lower or "bt" in q_lower:
                    d28 = self.nd243_db.get("28", {})
                    if d28:
                        ref_str += f"📌 VĂN BẢN HỢP NHẤT HIỆN HÀNH {d28['title'].upper()} (ĐÃ CẬP NHẬT THEO ĐIỀU 17 NGHỊ ĐỊNH 377/2026/NĐ-CP):\n\n{d28['full_consolidated_text']}\n\n"

                if is_dossier_query:
                    ref_str += "📌 XÁC ĐỊNH LOẠI HỒ SƠ CẦN LẬP (Khoản 1, 2 Điều 14 Luật PPP & Điều 8 NĐ 243/2025/NĐ-CP):\n"
                    for h in info.get("hồ_sơ_cần_lập", []):
                        ref_str += f"• {h['loai_du_an']}:\n  - Loại hồ sơ: {h['hồ_sơ']}\n  (Căn cứ: {h['citation']})\n"
                cross_refs.append(ref_str)

            if key == "377/2026" and (key_in_q or is_amendment_query or "243" in q_lower or "257" in q_lower or "ppp" in q_lower):
                ref_str = "⚡ [NỘI DUNG BÔI VÀNG / SỬA ĐỔI MỚI NHẤT TRÊN THƯ VIỆN PHÁP LUẬT - NGHỊ ĐỊNH 377/2026/NĐ-CP]\n"
                ref_str += f"Văn bản sửa đổi: {info['name']}\nTrích yếu: {info['description']}\n"
                ref_str += "CÁC ĐIỂM SỬA ĐỔI, BỔ SUNG CẦN ĐỐI CHIẾU:\n"
                for y in info.get("yellow_highlight_amendments", []):
                    ref_str += f"• [{y['type']}] {y['target_doc']} - {y['article']}:\n  - Nội dung: {y['content']}\n  (Căn cứ: {y['citation']})\n"
                cross_refs.append(ref_str)

        # 2. Universal Dynamic Search on TVPL (Applies to ALL 23 fields: Môi trường, Chứng khoán, Đất đai...)
        tvpl_dynamic = self.search_tvpl_native(query)
        if tvpl_dynamic:
            cross_refs.append(tvpl_dynamic)

        # 3. Live TVPL Web Search Fallback Grounding
        tvpl_hits = self.search_tvpl_live(query)
        if tvpl_hits:
            tvpl_live_str = "🌐 [TIN TỨC PHÁP LUẬT & HƯỚNG DẪN THỰC THI THỜI GIAN THỰC (thuvienphapluat.vn)]:\n"
            for idx, h in enumerate(tvpl_hits[:3], 1):
                tvpl_live_str += f"[{idx}] {h['title']}\nURL: {h['url']}\nTrích dẫn tóm tắt: {h['snippet']}\n\n"
            cross_refs.append(tvpl_live_str)

        return "\n\n".join(cross_refs) if cross_refs else ""

if __name__ == "__main__":
    crawler = ThuvienPhapLuatCrawler()
    print("=== TEST 1: GROUP A CRITERIA ===")
    print(crawler.fetch_legal_cross_reference("Tổng mức và phân loại tiêu chí các dự án nhóm A"))
    print("\n=== TEST 2: DOSSIER SELECTION ===")
    print(crawler.fetch_legal_cross_reference("Xác định loại hồ sơ cần lập cho dự án PPP"))
    print("\n=== TEST 3: NGHỊ ĐỊNH 377 AMENDMENT ===")
    print(crawler.fetch_legal_cross_reference("Nghị định 377 sửa đổi nghị định 243 như thế nào"))
