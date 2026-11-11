"""
AI Trend Hunter Agent (Tìm kiếm Ngành Xu Hướng trên Internet & Phân Bậc Vĩ Mô Toàn Thị Trường).

NGUYÊN TẮC BẮT BUỘC:
1. Chỉ thực thi tìm kiếm web khi Quản trị viên (ADMIN) bấm nút kích hoạt thủ công
   (`POST /api/v1/taxonomy/trend-agent/run`). Tuyệt đối không tự chạy ngầm hay tự chạy khi học sinh đánh giá.
2. Sau khi Agent chạy xong, trả về danh sách để Admin xem/điều chỉnh và bấm nút **Lưu vào CSDL**
   (`POST /api/v1/taxonomy/trend-agent/save`). Khi đề xuất cho học sinh, hệ thống CHỈ đọc từ CSDL đã lưu.
3. Sử dụng System Prompt chuẩn (Lựa chọn 3 - Macro Level Trend 2026 & 100% Coverage):
   - Độ phủ 100% các nhóm ngành chuẩn Bộ GD&ĐT (mỗi nhóm có tối thiểu 3 ngành đại diện, trừ nhóm chỉ có 1–2 ngành trong TT74; nhóm xu hướng mạnh 2026 mở rộng linh hoạt 4–6 ngành).
   - Thang đo vĩ mô toàn diện năm 2026 (Macro Level Trend 2026), áp dụng đồng nhất cho mọi nhóm ngành.
   - Không ép hạng nội bộ: Nếu ngành cao nhất của một nhóm chỉ đạt Cấp 2 (TIER_2) hoặc Cấp 3 (TIER_3)
     trên toàn thị trường 2026, giữ nguyên đúng Cấp 2 / Cấp 3, tuyệt đối không đôn lên Cấp 1.
"""

import asyncio
import hashlib
import html
import json
import logging
import re
import time
import unicodedata
import urllib.parse
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.staging import StagingRecord, StagingStatus, StagingStreamType
from app.models.taxonomy import Major

logger = logging.getLogger(__name__)

SEEDS_DIR = Path(__file__).resolve().parent.parent.parent / "db" / "seeds"

TREND_TIER_CONFIG: Dict[str, Dict[str, Any]] = {
    "TIER_1": {
        "tier": "TIER_1",
        "priority": 3,
        "rank_boost": 0.08,
        "label": "Cấp 1 (Bậc 1) · Xu hướng Mũi nhọn Toàn thị trường",
        "short_label": "Xu hướng Bậc 1",
    },
    "TIER_2": {
        "tier": "TIER_2",
        "priority": 2,
        "rank_boost": 0.045,
        "label": "Cấp 2 (Bậc 2) · Xu hướng Tăng trưởng Mạnh",
        "short_label": "Xu hướng Bậc 2",
    },
    "TIER_3": {
        "tier": "TIER_3",
        "priority": 1,
        "rank_boost": 0.02,
        "label": "Cấp 3 (Bậc 3) · Xu hướng Nhu cầu Ổn định",
        "short_label": "Xu hướng Bậc 3",
    },
    "NONE": {
        "tier": "NONE",
        "priority": 0,
        "rank_boost": 0.0,
        "label": "Ngành tiêu chuẩn",
        "short_label": "",
    },
}

# Ánh xạ cụm chủ đề xu hướng phủ toàn bộ 24 lĩnh vực đào tạo chuẩn MOET TT74/2026
# Ánh xạ cụm chủ đề xu hướng 2026 phủ toàn bộ 23 nhóm lĩnh vực đào tạo chuẩn MOET TT74/2026 (tất cả mã đã kiểm chứng tồn tại trong TT74)
# Kèm `macro_cap_tier`: trần thang đo vĩ mô 2026 thực tế để tuyệt đối không ép nhóm ngành ổn định lên Cấp 1
TREND_TOPIC_CLUSTERS: List[Dict[str, Any]] = [
    {
        "topic": "Trí tuệ nhân tạo, Khoa học máy tính & Kỹ thuật phần mềm 2026",
        "keywords": ["tri tue nhan tao", "artificial intelligence", "ai", "genai", "llm", "machine learning", "deep learning"],
        "major_codes": ["7480107", "7480101", "7480103", "7480104", "7480201", "7480106"],
        "macro_cap_tier": "TIER_1",
    },
    {
        "topic": "Vi mạch Bán dẫn, Công nghệ Bán dẫn & Thiết kế Chip 2026",
        "keywords": ["vi mach", "ban dan", "semiconductor", "chip", "ic design"],
        "major_codes": ["7520202", "7440180", "7510301", "7510302", "7520207", "7520203"],
        "macro_cap_tier": "TIER_1",
    },
    {
        "topic": "Khoa học dữ liệu, Tính toán & Toán ứng dụng",
        "keywords": ["khoa hoc du lieu", "data science", "phan tich du lieu", "big data", "toan ung dung", "thong ke", "toan tin"],
        "major_codes": ["7460108", "7460107", "7460112", "7460117", "7460201"],
        "macro_cap_tier": "TIER_1",
    },
    {
        "topic": "An ninh mạng, Tác chiến không gian mạng & Mạng truyền thông",
        "keywords": ["an toan thong tin", "an ninh mang", "cybersecurity", "bao mat", "khong gian mang", "toi pham cong nghe cao"],
        "major_codes": ["7480208", "7480102", "7860114", "7860215", "7860233"],
        "macro_cap_tier": "TIER_1",
    },
    {
        "topic": "Kỹ thuật phần mềm, Điện toán đám mây & Chuyển đổi số 2026",
        "keywords": ["ky thuat phan mem", "cong nghe thong tin", "lap trinh", "chuyen doi so", "phan mem", "cloud"],
        "major_codes": ["7480103", "7480201", "7480104", "7480108"],
        "macro_cap_tier": "TIER_2",
    },
    {
        "topic": "Công nghệ tài chính (Fintech), Kinh tế số & Tài chính - Ngân hàng",
        "keywords": ["fintech", "cong nghe tai chinh", "tai chinh so", "ngan hang so", "tai chinh", "kiem toan", "kinh te so"],
        "major_codes": ["7340205", "7340201", "7340302", "7340405", "7310109"],
        "macro_cap_tier": "TIER_1",
    },
    {
        "topic": "Logistics, Chuỗi cung ứng thông minh & Vận tải hàng không",
        "keywords": ["logistics", "chuoi cung ung", "xuat nhap khau", "supply chain", "khai thac van tai", "hang khong", "kinh doanh quoc te"],
        "major_codes": ["7340123", "7340120", "7840101", "7840102", "7840104"],
        "macro_cap_tier": "TIER_1",
    },
    {
        "topic": "Thương mại điện tử, Digital Marketing & Truyền thông đa phương tiện",
        "keywords": ["thuong mai dien tu", "e-commerce", "digital marketing", "marketing", "truyen thong da phuong tien", "bao chi", "quan he cong chung"],
        "major_codes": ["7340122", "7340115", "7320104", "7320106", "7320108", "7320107"],
        "macro_cap_tier": "TIER_2",
    },
    {
        "topic": "Robot công nghiệp, Tự động hóa, Cơ điện tử & Xe điện 2026",
        "keywords": ["tu dong hoa", "robot", "co dien tu", "xe dien", "o to", "cong nghe o to", "co khi"],
        "major_codes": ["7520107", "7520114", "7520216", "7520130", "7510303", "7510203", "7510205"],
        "macro_cap_tier": "TIER_1",
    },
    {
        "topic": "Năng lượng tái tạo, Môi trường, Vật liệu & Phát triển bền vững (ESG)",
        "keywords": ["nang luong", "nang luong xanh", "esg", "net zero", "moi truong", "phat trien ben vung", "quan ly nang luong"],
        "major_codes": ["7520135", "7510602", "7850104", "7850101", "7850202", "7310313"],
        "macro_cap_tier": "TIER_2",
    },
    {
        "topic": "Y khoa, Điều dưỡng, Dược phẩm & Kỹ thuật xét nghiệm - Y sinh",
        "keywords": ["y khoa", "bac si", "dieu duong", "y te", "duoc", "xet nghiem", "ky thuat y sinh", "cham soc suc khoe"],
        "major_codes": ["7720101", "7720301", "7720201", "7720202", "7720601", "7520212"],
        "macro_cap_tier": "TIER_2",
    },
    {
        "topic": "Công nghệ Giáo dục, Sư phạm Công nghệ/STEM & Tâm lý học",
        "keywords": ["cong nghe giao duc", "su pham", "giao vien", "tam ly hoc", "tham van", "quan he quoc te", "kinh te quoc te"],
        "major_codes": ["7140103", "7140246", "7140247", "7310401", "7310106", "7310206"],
        "macro_cap_tier": "TIER_2",
    },
    {
        "topic": "Nghệ thuật số, Thiết kế UI/UX, Đồ họa & Kiến trúc - Xây dựng BIM",
        "keywords": ["nghe thuat so", "thiet ke do hoa", "ui/ux", "kien truc", "xay dung", "bim", "do thi", "quy hoach"],
        "major_codes": ["7210408", "7210403", "7210402", "7210302", "7580101", "7580302", "7580105", "7580210"],
        "macro_cap_tier": "TIER_2",
    },
    {
        "topic": "Pháp luật Kinh tế - Thương mại, Ngoại ngữ & Công nghệ Sinh học - Thực phẩm",
        "keywords": ["luat kinh te", "luat", "phap che", "thuong mai quoc te", "ngon ngu anh", "ngon ngu trung", "ngon ngu nhat", "cong nghe sinh hoc", "thuc pham"],
        "major_codes": ["7380107", "7380109", "7380108", "7220201", "7220204", "7220209", "7220205", "7420201", "7420202", "7540101", "7540106"],
        "macro_cap_tier": "TIER_2",
    },
    {
        "topic": "Khoa học Vật liệu, Nông nghiệp CNC, Thú y, Du lịch & Dịch vụ Xã hội",
        "keywords": ["vat lieu", "ban dan", "hoa hoc", "nong nghiep", "thuy san", "thu y", "du lich", "khach san", "cong tac xa hoi"],
        "major_codes": ["7440122", "7440104", "7440118", "7620115", "7620101", "7620301", "7640101", "7810201", "7810101", "7810202", "7760101", "7760104"],
        "macro_cap_tier": "TIER_3",
    },
]

# Định mức linh hoạt theo sức hút xu hướng 2026:
# (min_target, max_cap, macro_max_tier)
# - Mọi nhóm >= 3 ngành có tối thiểu 3 ngành đại diện (DỊCH VỤ XÃ HỘI chỉ có 2 ngành, THÚ Y chỉ có 1 ngành trong TT74).
# - Nhóm nhiều xu hướng 2026 được mở rộng tới 4–6 ngành; nhóm ít xu hướng giữ mức 3 ngành.
CATEGORY_TREND_QUOTA: Dict[str, Tuple[int, int, str]] = {
    "MÁY TÍNH VÀ CÔNG NGHỆ THÔNG TIN": (3, 6, "TIER_1"),
    "KỸ THUẬT": (3, 6, "TIER_1"),
    "KINH DOANH VÀ QUẢN LÝ": (3, 6, "TIER_1"),
    "CÔNG NGHỆ KỸ THUẬT": (3, 5, "TIER_1"),
    "SỨC KHỎE": (3, 5, "TIER_2"),
    "TOÁN VÀ THỐNG KÊ": (3, 4, "TIER_1"),
    "KHOA HỌC TỰ NHIÊN": (3, 4, "TIER_1"),
    "KHOA HỌC XÃ HỘI VÀ HÀNH VI": (3, 4, "TIER_2"),
    "BÁO CHÍ VÀ THÔNG TIN": (3, 4, "TIER_2"),
    "NGHỆ THUẬT": (3, 4, "TIER_2"),
    "KIẾN TRÚC VÀ XÂY DỰNG": (3, 4, "TIER_2"),
    "NHÂN VĂN": (3, 4, "TIER_2"),
    "AN NINH, QUỐC PHÒNG": (3, 4, "TIER_2"),
    "PHÁP LUẬT": (3, 3, "TIER_2"),
    "KHOA HỌC GIÁO DỤC VÀ ĐÀO TẠO GIÁO VIÊN": (3, 3, "TIER_2"),
    "KHOA HỌC SỰ SỐNG": (3, 3, "TIER_2"),
    "SẢN XUẤT VÀ CHẾ BIẾN": (3, 3, "TIER_2"),
    "DU LỊCH, KHÁCH SẠN, THỂ THAO VÀ DỊCH VÀ CÁ NHÂN": (3, 3, "TIER_2"),
    "MÔI TRƯỜNG VÀ BẢO VỆ MÔI TRƯỜNG": (3, 3, "TIER_2"),
    "DỊCH VỤ VẬN TẢI": (3, 3, "TIER_2"),
    "NÔNG, LÂM NGHIỆP VÀ THỦY SẢN": (3, 3, "TIER_3"),
    "DỊCH VỤ XÃ HỘI": (2, 2, "TIER_3"),
    "THÚ Y": (1, 1, "TIER_3"),
}

# Ngành đại diện chuẩn theo từng nhóm lĩnh vực + trần thang đo Vĩ mô 2026 (100% mã khớp TT74)
CATEGORY_BASELINE_REPRESENTATIVES: Dict[str, List[Tuple[str, str, str]]] = {
    "MÁY TÍNH VÀ CÔNG NGHỆ THÔNG TIN": [
        ("7480107", "TIER_1", "AI & GenAI bùng nổ mạnh mẽ trong mọi doanh nghiệp năm 2026"),
        ("7480208", "TIER_1", "Thiếu hụt nghiêm trọng chuyên gia An ninh mạng và bảo mật hạ tầng số 2026"),
        ("7480101", "TIER_1", "Nền tảng thuật toán cốt lõi cho AI, dữ liệu và hệ thống hiệu năng cao"),
        ("7480103", "TIER_2", "Nhu cầu kỹ sư phát triển phần mềm kết hợp AI Coding Copilot duy trì cao"),
        ("7480104", "TIER_2", "Chuyển đổi số dữ liệu doanh nghiệp và ERP/Cloud tiếp tục mở rộng"),
        ("7480106", "TIER_2", "Thiết kế hệ thống nhúng, Edge AI và phần cứng tính toán tăng trưởng tốt"),
    ],
    "KỸ THUẬT": [
        ("7520202", "TIER_1", "Đề án phát triển nhân lực ngành công nghiệp bán dẫn & thiết kế vi mạch đến 2030"),
        ("7520107", "TIER_1", "Robot tự hành và tự động hóa nhà máy thông minh bùng nổ tại các khu công nghiệp"),
        ("7520114", "TIER_2", "Cơ điện tử dẫn dắt dây chuyền sản xuất thông minh FDI năm 2026"),
        ("7520216", "TIER_2", "Tự động hóa công nghiệp và điều khiển thông minh có nhu cầu tuyển dụng cao"),
        ("7520130", "TIER_2", "Xu hướng chuyển dịch xe điện và phương tiện giao thông thông minh"),
        ("7520135", "TIER_2", "Chuyển dịch năng lượng tái tạo, lưới điện thông minh và mục tiêu Net Zero"),
    ],
    "KINH DOANH VÀ QUẢN LÝ": [
        ("7340205", "TIER_1", "Fintech, thanh toán số và ngân hàng AI tăng tốc mạnh năm 2026"),
        ("7340123", "TIER_1", "Logistics xanh và quản trị chuỗi cung ứng toàn cầu khát nhân lực chất lượng cao"),
        ("7340122", "TIER_2", "Thương mại điện tử và bán lẻ đa kênh tiếp tục tăng trưởng hai con số"),
        ("7340115", "TIER_2", "Digital Marketing ứng dụng dữ liệu lớn và AI cá nhân hóa khách hàng"),
        ("7340405", "TIER_2", "Số hóa quy trình quản trị và phân tích hệ thống thông tin doanh nghiệp"),
        ("7340120", "TIER_2", "Mở rộng xuất nhập khẩu và dịch chuyển chuỗi cung ứng vào Việt Nam"),
    ],
    "CÔNG NGHỆ KỸ THUẬT": [
        ("7510303", "TIER_2", "Tự động hóa sản xuất và điều khiển thông minh trong nhà máy 4.0"),
        ("7510301", "TIER_1", "Nhu cầu kỹ sư điện - điện tử phục vụ chuỗi cung ứng sản xuất chip & điện tử"),
        ("7510302", "TIER_2", "Hạ tầng viễn thông 5G, IoT công nghiệp và đóng gói kiểm thử vi mạch"),
        ("7510203", "TIER_2", "Vận hành và bảo trì dây chuyền cơ điện tử tại các tổ hợp sản xuất FDI"),
        ("7510205", "TIER_2", "Công nghệ ô tô thế hệ mới, xe hybrid và xe điện tại Việt Nam"),
    ],
    "SỨC KHỎE": [
        ("7720101", "TIER_2", "Nhu cầu bác sĩ đa khoa chất lượng cao tăng bền vững theo già hóa dân số"),
        ("7720301", "TIER_2", "Thiếu hụt nhân lực điều dưỡng chuẩn quốc tế cả trong nước và xuất khẩu"),
        ("7720201", "TIER_2", "Phát triển công nghiệp dược phẩm và chăm sóc sức khỏe chủ động"),
        ("7720202", "TIER_2", "Chuyển dịch sản xuất thuốc sinh học và dược phẩm công nghệ cao"),
        ("7720601", "TIER_2", "Nhu cầu xét nghiệm y học chính xác và chẩn đoán sớm gia tăng"),
    ],
    "TOÁN VÀ THỐNG KÊ": [
        ("7460108", "TIER_1", "Khoa học dữ liệu là ngành cốt lõi dẫn dắt chuyển đổi số và AI năm 2026"),
        ("7460107", "TIER_2", "Khoa học tính toán mô phỏng kỹ thuật, tài chính định lượng và mô hình AI"),
        ("7460112", "TIER_2", "Toán ứng dụng trong tối ưu hóa vận hành, chuỗi cung ứng và định lượng rủi ro"),
        ("7460117", "TIER_2", "Toán tin đáp ứng nhu cầu phát triển phần mềm và phân tích dữ liệu lớn"),
    ],
    "KHOA HỌC TỰ NHIÊN": [
        ("7440180", "TIER_1", "Công nghệ bán dẫn là trọng tâm đào tạo chiến lược quốc gia giai đoạn 2025–2030"),
        ("7440122", "TIER_2", "Khoa học vật liệu mới phục vụ chip bán dẫn, pin xe điện và năng lượng sạch"),
        ("7440104", "TIER_2", "Vật lý chất rắn nền tảng trực tiếp cho công nghệ bán dẫn và linh kiện quang điện tử"),
        ("7440118", "TIER_3", "Hóa phân tích phục vụ kiểm định môi trường, dược phẩm và an toàn thực phẩm"),
    ],
    "KHOA HỌC XÃ HỘI VÀ HÀNH VI": [
        ("7310109", "TIER_2", "Kinh tế số dẫn dắt chuyển đổi mô hình kinh doanh và thương mại điện tử 2026"),
        ("7310401", "TIER_2", "Nhu cầu tham vấn tâm lý học đường, doanh nghiệp và sức khỏe tinh thần tăng mạnh"),
        ("7310313", "TIER_2", "Nhân lực hoạch định phát triển bền vững và báo cáo ESG ngày càng thiết yếu"),
        ("7310106", "TIER_2", "Kinh tế quốc tế phục vụ hội nhập FTA và dòng vốn đầu tư FDI vào Việt Nam"),
    ],
    "BÁO CHÍ VÀ THÔNG TIN": [
        ("7320104", "TIER_2", "Truyền thông đa phương tiện bùng nổ cùng hệ sinh thái nội dung số 2026"),
        ("7320106", "TIER_2", "Công nghệ truyền thông kết hợp AI sản xuất nội dung và phân tích khán giả"),
        ("7320108", "TIER_2", "Quan hệ công chúng và quản trị khủng hoảng truyền thông thương hiệu doanh nghiệp"),
        ("7320107", "TIER_3", "Truyền thông quốc tế phục vụ doanh nghiệp mở rộng thị trường toàn cầu"),
    ],
    "NGHỆ THUẬT": [
        ("7210408", "TIER_2", "Nghệ thuật số phát triển nhanh cùng game, hoạt hình 3D và thực tế ảo"),
        ("7210403", "TIER_2", "Thiết kế đồ họa và UI/UX cho sản phẩm số và thương hiệu doanh nghiệp"),
        ("7210402", "TIER_3", "Thiết kế công nghiệp tạo giá trị gia tăng cho sản phẩm sản xuất trong nước"),
        ("7210302", "TIER_3", "Công nghệ điện ảnh - truyền hình hậu kỳ kỹ thuật số đáp ứng thị trường giải trí"),
    ],
    "KIẾN TRÚC VÀ XÂY DỰNG": [
        ("7580101", "TIER_2", "Kiến trúc xanh, công trình tiết kiệm năng lượng và không gian đô thị thông minh"),
        ("7580302", "TIER_2", "Quản lý xây dựng áp dụng bắt buộc mô hình BIM trong các dự án đầu tư lớn"),
        ("7580105", "TIER_2", "Quy hoạch vùng và đô thị thích ứng biến đổi khí hậu"),
        ("7580210", "TIER_2", "Đẩy mạnh đầu tư công hạ tầng giao thông, sân bay và đô thị trọng điểm 2026"),
    ],
    "NHÂN VĂN": [
        ("7220201", "TIER_2", "Ngôn ngữ Anh gắn với dịch vụ toàn cầu, công nghệ và kinh tế tri thức"),
        ("7220204", "TIER_2", "Ngôn ngữ Trung Quốc có nhu cầu tuyển dụng rất lớn tại các cụm FDI công nghiệp"),
        ("7220209", "TIER_2", "Ngôn ngữ Nhật phục vụ gia công phần mềm, kỹ thuật và thị trường lao động Nhật Bản"),
        ("7220205", "TIER_3", "Ngôn ngữ Đức mở rộng cơ hội việc làm kỹ thuật và điều dưỡng tại châu Âu"),
    ],
    "AN NINH, QUỐC PHÒNG": [
        ("7860114", "TIER_2", "An ninh mạng và phòng chống tội phạm công nghệ cao là mặt trận ưu tiên 2026"),
        ("7860215", "TIER_2", "Tác chiến không gian mạng giữ vai trò trọng yếu trong bảo vệ hạ tầng số quốc gia"),
        ("7860233", "TIER_2", "Tác chiến điện tử hiện đại gắn liền công nghệ radar, viễn thông và UAV"),
        ("7860118", "TIER_3", "An ninh phi truyền thống ứng phó an ninh năng lượng, môi trường và dữ liệu"),
    ],
    "PHÁP LUẬT": [
        ("7380107", "TIER_2", "Luật kinh tế và pháp chế doanh nghiệp tăng nhu cầu theo quy định dữ liệu/thuế mới 2026"),
        ("7380109", "TIER_2", "Luật thương mại quốc tế hỗ trợ doanh nghiệp xuất khẩu và phòng vệ thương mại"),
        ("7380108", "TIER_3", "Luật quốc tế đáp ứng giao dịch xuyên biên giới và hợp tác đa phương"),
    ],
    "KHOA HỌC GIÁO DỤC VÀ ĐÀO TẠO GIÁO VIÊN": [
        ("7140103", "TIER_2", "Công nghệ giáo dục (EdTech) và chuyển đổi số bài giảng AI trong trường học 2026"),
        ("7140246", "TIER_2", "Sư phạm công nghệ đáp ứng chương trình giáo dục STEM và phổ thông mới"),
        ("7140247", "TIER_3", "Nhu cầu giáo viên Khoa học tự nhiên giảng dạy tích hợp ổn định tại các địa phương"),
    ],
    "KHOA HỌC SỰ SỐNG": [
        ("7420201", "TIER_2", "Công nghệ sinh học ứng dụng trong y sinh, dược phẩm và giống cây trồng CNC"),
        ("7420202", "TIER_2", "Kỹ thuật sinh học phục vụ công nghiệp chế biến sinh học và môi trường"),
        ("7420107", "TIER_3", "Vi sinh vật học ứng dụng kiểm soát an toàn thực phẩm và nông nghiệp sinh học"),
    ],
    "SẢN XUẤT VÀ CHẾ BIẾN": [
        ("7540101", "TIER_2", "Công nghệ thực phẩm hướng tới chế biến sâu nông thủy sản xuất khẩu"),
        ("7540106", "TIER_2", "Đảm bảo chất lượng và an toàn thực phẩm đáp ứng tiêu chuẩn khắt khe thị trường EU/Mỹ"),
        ("7540203", "TIER_3", "Vật liệu dệt may xanh, tái chế đáp ứng chuẩn xuất khẩu dệt may 2026"),
    ],
    "DU LỊCH, KHÁCH SẠN, THỂ THAO VÀ DỊCH VÀ CÁ NHÂN": [
        ("7810201", "TIER_2", "Quản trị khách sạn chuẩn quốc tế phục hồi mạnh theo làn sóng khách du lịch 2026"),
        ("7810101", "TIER_3", "Du lịch bền vững, du lịch số và trải nghiệm văn hóa bản địa ổn định"),
        ("7810202", "TIER_3", "Quản trị nhà hàng và dịch vụ ăn uống tăng trưởng theo tiêu dùng đô thị"),
    ],
    "MÔI TRƯỜNG VÀ BẢO VỆ MÔI TRƯỜNG": [
        ("7850104", "TIER_2", "Chuyên gia ESG, kiểm kê khí nhà kính và phát triển bền vững rất được săn đón 2026"),
        ("7850101", "TIER_2", "Quản lý tài nguyên và đánh giá tác động môi trường các khu công nghiệp xanh"),
        ("7850202", "TIER_3", "An toàn, vệ sinh lao động theo chuẩn tuân thủ nhà máy xuất khẩu"),
    ],
    "DỊCH VỤ VẬN TẢI": [
        ("7840101", "TIER_2", "Khai thác vận tải đa phương thức gắn liền chuỗi logistics và cảng biển 2026"),
        ("7840102", "TIER_2", "Quản lý hoạt động bay phục vụ mở rộng mạng đường bay và hạ tầng hàng không"),
        ("7840104", "TIER_3", "Kinh tế vận tải tối ưu chi phí lưu thông hàng hóa nội địa và quốc tế"),
    ],
    "NÔNG, LÂM NGHIỆP VÀ THỦY SẢN": [
        ("7620115", "TIER_3", "Kinh tế nông nghiệp số và chuỗi giá trị nông sản xuất khẩu phát triển ổn định"),
        ("7620101", "TIER_3", "Nông nghiệp công nghệ cao và nông nghiệp tuần hoàn chuyển dịch từng bước"),
        ("7620301", "TIER_3", "Nuôi trồng thủy sản bền vững theo tiêu chuẩn truy xuất nguồn gốc"),
    ],
    "DỊCH VỤ XÃ HỘI": [
        ("7760101", "TIER_3", "Công tác xã hội hỗ trợ an sinh, trường học và cộng đồng giữ nhu cầu ổn định"),
        ("7760104", "TIER_3", "Dân số và phát triển phục vụ chính sách an sinh trong bối cảnh già hóa dân số"),
    ],
    "THÚ Y": [
        ("7640101", "TIER_3", "Thú y duy trì nhu cầu ổn định gắn với chăn nuôi an toàn sinh học và dịch vụ thú cưng"),
    ],
}


def _strip_accents(text: str) -> str:
    if not text:
        return ""
    text = text.replace("đ", "d").replace("Đ", "D")
    norm = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in norm if unicodedata.category(ch) != "Mn").lower().strip()


def _clean_html_text(raw: str) -> str:
    if not raw:
        return ""
    unescaped = html.unescape(raw)
    cleaned = re.sub(r"<[^>]+>", " ", unescaped)
    return " ".join(cleaned.split()).strip()


def _get_registry_path() -> Path:
    if settings.ENVIRONMENT == "test":
        return SEEDS_DIR / "trending_majors_registry.test.json"
    return SEEDS_DIR / "trending_majors_registry.json"


def _code_variants(major_code: str) -> List[str]:
    c = str(major_code or "").strip()
    if not c:
        return []
    variants = [c]
    if len(c) == 7 and c.startswith("7"):
        variants.append(c[1:])
    elif len(c) == 6:
        variants.append(f"7{c}")
    return variants


def load_trending_registry() -> Dict[str, Any]:
    """Đọc sổ đăng ký ngành xu hướng đã được Admin lưu (không kích hoạt tìm kiếm)."""
    path = _get_registry_path()
    if not path.exists():
        return {
            "last_run_at": None,
            "saved_at": None,
            "triggered_by": None,
            "focus_query": "",
            "articles_scanned": 0,
            "search_sources": [],
            "majors": {},
        }
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("majors"), dict):
                return data
    except Exception as exc:
        logger.warning("Không đọc được registry ngành xu hướng (%s): %s", path, exc)
    return {
        "last_run_at": None,
        "saved_at": None,
        "triggered_by": None,
        "focus_query": "",
        "articles_scanned": 0,
        "search_sources": [],
        "majors": {},
    }


def load_trending_registry_map() -> Dict[str, Dict[str, Any]]:
    """Trả về ánh xạ tra cứu nhanh cho cả mã ngành 6 chữ số (TT74) và 7 chữ số (TT09)."""
    reg = load_trending_registry()
    raw_majors = reg.get("majors") or {}
    lookup: Dict[str, Dict[str, Any]] = {}
    for code, entry in raw_majors.items():
        if not isinstance(entry, dict):
            continue
        tier = str(entry.get("trend_tier") or "NONE").upper()
        if tier not in ("TIER_1", "TIER_2", "TIER_3"):
            continue
        for v in _code_variants(code):
            lookup[v] = entry
    return lookup


def get_major_trend_info(
    major_code: str,
    trend_map: Optional[Dict[str, Dict[str, Any]]] = None,
    cognitive_attributes: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Lấy thông tin bậc ưu tiên xu hướng chuẩn hóa cho 1 mã ngành.
    Ưu tiên đọc trực tiếp `_trend` đã lưu trong CSDL (`cognitive_attributes`), sau đó mới đối chiếu registry.
    """
    entry = None

    if isinstance(cognitive_attributes, dict):
        embedded = cognitive_attributes.get("_trend")
        if (
            isinstance(embedded, dict)
            and embedded.get("trend_tier") in ("TIER_1", "TIER_2", "TIER_3")
            and (settings.ENVIRONMENT != "test" or not _get_registry_path().exists())
        ):
            entry = embedded

    if not entry and trend_map:
        for v in _code_variants(major_code):
            if v in trend_map:
                entry = trend_map[v]
                break

    # Khi ở môi trường test, nếu registry đã bị xóa rỗng thì tuyệt đối không đọc nhầm _trend cũ từ seed file
    if settings.ENVIRONMENT == "test" and _get_registry_path().exists():
        entry = None
        if trend_map:
            for v in _code_variants(major_code):
                if v in trend_map:
                    entry = trend_map[v]
                    break

    if not entry:
        return {
            "is_trending": False,
            "trend_tier": None,
            "trend_priority": 0,
            "trend_label": None,
            "trend_reason": None,
            "trend_sources": [],
        }

    tier = str(entry.get("trend_tier") or "NONE").upper()
    cfg = TREND_TIER_CONFIG.get(tier, TREND_TIER_CONFIG["NONE"])
    if cfg["priority"] <= 0:
        return {
            "is_trending": False,
            "trend_tier": None,
            "trend_priority": 0,
            "trend_label": None,
            "trend_reason": None,
            "trend_sources": [],
        }

    return {
        "is_trending": True,
        "trend_tier": tier,
        "trend_priority": int(cfg["priority"]),
        "trend_label": entry.get("trend_label") or cfg["label"],
        "trend_reason": entry.get("trend_reason"),
        "trend_sources": entry.get("trend_sources") or [],
    }


def get_trend_rank_boost(
    trend_tier: Optional[str],
    overall_score: float,
) -> float:
    """
    Tính hệ số cộng ưu tiên xếp hạng (chỉ dùng cho thứ tự sắp xếp, không làm biến dạng % điểm 3 trụ cột).
    Guardrail: Chỉ cộng ưu tiên xu hướng khi ngành đạt ngưỡng phù hợp nền tảng tối thiểu (>= 0.45).
    """
    if not trend_tier or overall_score < 0.45:
        return 0.0
    cfg = TREND_TIER_CONFIG.get(str(trend_tier).upper())
    if not cfg:
        return 0.0
    return float(cfg["rank_boost"])


async def _fetch_rss_articles(client: httpx.AsyncClient, url: str, engine_name: str) -> List[Dict[str, Any]]:
    articles: List[Dict[str, Any]] = []
    try:
        resp = await client.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AI-CareerGuide-TrendAgent/1.0)"},
        )
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.text)
        for item in root.findall(".//item")[:15]:
            title = _clean_html_text(item.findtext("title") or "")
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            src_el = item.find("source")
            source_name = _clean_html_text(src_el.text if src_el is not None and src_el.text else engine_name)
            desc = _clean_html_text(item.findtext("description") or "")
            if title and link:
                articles.append({
                    "title": title,
                    "url": link,
                    "source": source_name or engine_name,
                    "published_at": pub_date,
                    "snippet": desc[:400],
                    "engine": engine_name,
                })
    except Exception as exc:
        logger.warning("Trend Agent RSS fetch failed (%s): %s", engine_name, exc)
    return articles


async def search_trending_majors_online(
    focus_query: str = "dự báo nhu cầu nhân lực thị trường lao động Việt Nam 2026 ngành mũi nhọn AI bán dẫn y tế kinh tế xanh",
) -> List[Dict[str, Any]]:
    """
    Thực thi tìm kiếm trực tuyến đa tầng phủ rộng toàn thị trường Việt Nam năm 2026.
    Kết hợp Tavily API (nếu có key thực tế), Google News RSS (6 cụm báo cáo & ngành) và Bing News RSS.
    """
    raw_q = focus_query.strip() or "dự báo nhu cầu nhân lực thị trường lao động Việt Nam 2026"
    base_q = raw_q if ("2026" in raw_q or "2025" in raw_q or "2027" in raw_q) else f"{raw_q} 2026"
    queries = [
        base_q,
        "báo cáo thị trường lao động Việt Nam 2026 TopCV VietnamWorks Navigos ngành khát nhân lực",
        "xu hướng tuyển dụng Việt Nam 2026 trí tuệ nhân tạo AI vi mạch bán dẫn an ninh mạng khoa học dữ liệu",
        "nhu cầu nhân lực 2026 Fintech thương mại điện tử logistics chuỗi cung ứng kỹ thuật robot tự động hóa",
        "ngành học thiếu nhân lực Việt Nam 2026 y khoa điều dưỡng dược luật kinh tế giáo dục STEM tâm lý học",
        "chuyển đổi xanh ESG năng lượng tái tạo nông nghiệp công nghệ cao du lịch ngoại ngữ kiến trúc BIM 2026",
    ]

    all_articles: List[Dict[str, Any]] = []

    tavily_key = (settings.TAVILY_API_KEY or "").strip()
    if tavily_key and tavily_key != "your_tavily_api_key_here" and not tavily_key.startswith("your_"):
        try:
            from tavily import TavilyClient

            tavily = TavilyClient(api_key=tavily_key)
            for tq in (
                base_q,
                "báo cáo thị trường lao động Việt Nam 2026 nhu cầu tuyển dụng nhân lực đa ngành",
            ):
                resp = tavily.search(query=tq, search_depth="advanced", max_results=12)
                for r in resp.get("results", []):
                    all_articles.append({
                        "title": _clean_html_text(r.get("title") or ""),
                        "url": r.get("url") or "",
                        "source": "Tavily Web Search",
                        "published_at": "",
                        "snippet": _clean_html_text(r.get("content") or "")[:450],
                        "engine": "Tavily",
                    })
        except Exception as exc:
            logger.warning("Tavily trend search fallback sang RSS (%s)", exc)

    tasks = []
    async with httpx.AsyncClient(timeout=8.5, follow_redirects=True) as client:
        for q in queries:
            encoded = urllib.parse.quote(q)
            gn_url = f"https://news.google.com/rss/search?q={encoded}&hl=vi&gl=VN&ceid=VN:vi"
            tasks.append(_fetch_rss_articles(client, gn_url, "Google News"))
        for bq in (base_q, "xu hướng ngành nghề tuyển dụng Việt Nam 2026"):
            bn_url = f"https://www.bing.com/news/search?q={urllib.parse.quote(bq)}&format=rss"
            tasks.append(_fetch_rss_articles(client, bn_url, "Bing News"))

        batches = await asyncio.gather(*tasks, return_exceptions=True)
        for b in batches:
            if isinstance(b, list):
                all_articles.extend(b)

    deduped: List[Dict[str, Any]] = []
    seen_titles = set()
    for art in all_articles:
        norm_t = _strip_accents(art.get("title", ""))[:80]
        if not norm_t or norm_t in seen_titles:
            continue
        seen_titles.add(norm_t)
        deduped.append(art)

    return deduped[:65]


def _extract_candidates_from_articles(
    articles: List[Dict[str, Any]],
    catalog_majors: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Đối chiếu chứng cứ bài báo web với 435 ngành TT74 và đảm bảo ĐỘ PHỦ 100% CÁC NHÓM NGÀNH:
    - Mỗi nhóm lĩnh vực chuẩn (trừ nhóm 'Khác') đều có 1–2 ngành đại diện được đưa vào bảng đánh giá.
    - Mỗi ứng viên giữ nguyên trần vĩ mô (`macro_cap_tier`) để tránh ép nhóm yếu lên Cấp 1.
    """
    norm_articles: List[Tuple[Dict[str, Any], str, str]] = []
    for art in articles:
        norm_title = _strip_accents(art.get("title", ""))
        norm_snip = _strip_accents(art.get("snippet", ""))
        norm_articles.append((art, norm_title, norm_snip))

    cluster_hits_by_code: Dict[str, List[Tuple[str, float, Dict[str, Any], str]]] = {}
    for cluster in TREND_TOPIC_CLUSTERS:
        topic_name = cluster["topic"]
        kws = cluster["keywords"]
        cap_tier = cluster.get("macro_cap_tier", "TIER_2")
        for art, n_title, n_snip in norm_articles:
            score = 0.0
            for kw in kws:
                if len(kw) <= 3:
                    if re.search(rf"\b{re.escape(kw)}\b", n_title):
                        score += 2.2
                    elif re.search(rf"\b{re.escape(kw)}\b", n_snip):
                        score += 1.0
                else:
                    if kw in n_title:
                        score += 2.5
                    elif kw in n_snip:
                        score += 1.2
            if score > 0:
                for pos, code in enumerate(cluster["major_codes"]):
                    pos_weight = max(0.55, 1.0 - pos * 0.12)
                    for v in _code_variants(code):
                        cluster_hits_by_code.setdefault(v, []).append((topic_name, score * pos_weight, art, cap_tier))

    major_by_code: Dict[str, Dict[str, Any]] = {}
    all_categories: List[str] = []
    seen_cats = set()
    for m in catalog_majors:
        c = str(m.get("major_code") or "").strip()
        if not c:
            continue
        for v in _code_variants(c):
            major_by_code.setdefault(v, m)
        cat = str(m.get("category") or "Khác").strip()
        if cat and cat != "Khác" and cat not in seen_cats:
            seen_cats.add(cat)
            all_categories.append(cat)

    candidates_map: Dict[str, Dict[str, Any]] = {}
    seen_major_codes = set()

    for m in catalog_majors:
        code = str(m.get("major_code") or "").strip()
        name = str(m.get("name") or "").strip()
        cat = str(m.get("category") or "Khác").strip()
        if not code or not name or code in seen_major_codes or cat == "Khác":
            continue
        seen_major_codes.add(code)

        norm_name = _strip_accents(name)
        evidence_score = 0.0
        matched_articles: List[Dict[str, Any]] = []
        matched_topics: List[str] = []
        cap_tiers: List[str] = []
        seen_urls = set()

        if len(norm_name) >= 5:
            for art, n_title, n_snip in norm_articles:
                if norm_name in n_title:
                    evidence_score += 4.0
                    if art["url"] not in seen_urls:
                        seen_urls.add(art["url"])
                        matched_articles.append(art)
                elif norm_name in n_snip:
                    evidence_score += 2.0
                    if art["url"] not in seen_urls:
                        seen_urls.add(art["url"])
                        matched_articles.append(art)

        for topic_name, c_score, art, cap_tier in cluster_hits_by_code.get(code, []):
            evidence_score += c_score
            if topic_name not in matched_topics:
                matched_topics.append(topic_name)
            cap_tiers.append(cap_tier)
            if art["url"] not in seen_urls:
                seen_urls.add(art["url"])
                matched_articles.append(art)

        if evidence_score >= 1.5 and matched_articles:
            default_tier = (
                "TIER_1" if "TIER_1" in cap_tiers else ("TIER_2" if "TIER_2" in cap_tiers else "TIER_3")
            )
            candidates_map[code] = {
                "major_code": code,
                "major_name": name,
                "category": cat,
                "evidence_score": round(evidence_score, 2),
                "macro_suggested_tier": default_tier,
                "matched_topics": matched_topics,
                "sources": [
                    {
                        "title": a["title"],
                        "url": a["url"],
                        "source": a.get("source", "Web Search"),
                    }
                    for a in matched_articles[:3]
                ],
            }

    # Đảm bảo 100% các nhóm ngành đều đạt định mức tối thiểu (>= 3 ngành/nhóm, hoặc đủ 100% với nhóm chỉ có 1–2 ngành)
    # Nhóm ít xu hướng giữ mức tối thiểu 3 ngành; nhóm xu hướng mạnh 2026 mở rộng linh hoạt lên 4–6 ngành.
    majors_by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for m in catalog_majors:
        c_cat = str(m.get("category") or "Khác").strip()
        if c_cat and c_cat != "Khác":
            majors_by_cat.setdefault(c_cat, []).append(m)

    fallback_article_refs = [
        {"title": a["title"], "url": a["url"], "source": a.get("source", "Web Search")}
        for a in articles[:2]
    ]

    for cat in all_categories:
        cat_majors = majors_by_cat.get(cat, [])
        q_min, q_cap, _ = CATEGORY_TREND_QUOTA.get(cat, (3, 3, "TIER_3"))
        min_needed = min(q_min, len(cat_majors))

        cat_existing_codes = {c["major_code"] for c in candidates_map.values() if c["category"] == cat}
        # Nếu nhóm chưa có tín hiệu mạnh, giữ mức tối thiểu (min_needed = 3);
        # nếu nhóm đã có tín hiệu từ tin tức nhưng chưa đủ 3 ngành, bổ sung thêm từ danh sách baseline đến đủ min_needed.
        target_fill = min_needed
        baselines = CATEGORY_BASELINE_REPRESENTATIVES.get(cat) or []
        for base_code, macro_tier, reason_hint in baselines:
            if len(cat_existing_codes) >= target_fill:
                break
            m_obj = None
            for v in _code_variants(base_code):
                if v in major_by_code:
                    m_obj = major_by_code[v]
                    break
            if not m_obj:
                continue
            actual_code = str(m_obj["major_code"]).strip()
            if actual_code in candidates_map:
                cat_existing_codes.add(actual_code)
                continue
            candidates_map[actual_code] = {
                "major_code": actual_code,
                "major_name": m_obj["name"],
                "category": cat,
                "evidence_score": 3.0 if macro_tier == "TIER_1" else (2.0 if macro_tier == "TIER_2" else 1.2),
                "macro_suggested_tier": macro_tier,
                "matched_topics": [reason_hint],
                "sources": fallback_article_refs,
            }
            cat_existing_codes.add(actual_code)

        # Trường hợp nhóm mới từ Thông tư/Excel có thêm ngành nhưng chưa đủ định mức tối thiểu
        if len(cat_existing_codes) < target_fill:
            for rep in cat_majors:
                if len(cat_existing_codes) >= target_fill:
                    break
                actual_code = str(rep.get("major_code") or "").strip()
                if not actual_code or actual_code in candidates_map:
                    continue
                candidates_map[actual_code] = {
                    "major_code": actual_code,
                    "major_name": rep.get("name") or actual_code,
                    "category": cat,
                    "evidence_score": 1.2,
                    "macro_suggested_tier": "TIER_3",
                    "matched_topics": [f"Đại diện nhóm {cat} trên mặt bằng nhu cầu năm 2026"],
                    "sources": fallback_article_refs,
                }
                cat_existing_codes.add(actual_code)

    # Giữ số lượng linh hoạt theo từng nhóm: ít xu hướng = 3 ngành, nhiều xu hướng 2026 = tối đa 4–6 ngành
    by_cat_grouped: Dict[str, List[Dict[str, Any]]] = {}
    for cand in candidates_map.values():
        by_cat_grouped.setdefault(cand["category"], []).append(cand)

    balanced_candidates: List[Dict[str, Any]] = []
    for cat, items in by_cat_grouped.items():
        items.sort(key=lambda x: x["evidence_score"], reverse=True)
        _, cap_count, _ = CATEGORY_TREND_QUOTA.get(cat, (3, 3, "TIER_3"))
        balanced_candidates.extend(items[:cap_count])

    balanced_candidates.sort(key=lambda c: c["evidence_score"], reverse=True)
    return balanced_candidates, all_categories


async def _refine_tiers_with_llm(
    focus_query: str,
    articles: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    all_categories: List[str],
) -> Optional[Dict[str, Dict[str, Any]]]:
    """
    Áp dụng System Prompt Lựa chọn 3 nâng cấp cho thị trường 2026 (Chi tiết, chống sai sót):
    - Đảm bảo 100% nhóm ngành đều góp mặt với >= 3 ngành đại diện (trừ nhóm chỉ có 1-2 ngành trong TT74).
    - Nhóm ít xu hướng giữ ở mức 3 ngành; nhóm xu hướng cao 2026 mở rộng 4–6 ngành.
    - Chấm hạng theo thang đo vĩ mô toàn thị trường 2026 (TIER_1 > TIER_2 > TIER_3),
      KHÔNG xếp hạng tương đối cục bộ, KHÔNG bịa mã ngành mới, KHÔNG bỏ sót mã nào.
    """
    if (
        not candidates
        or not settings.OPENAI_API_KEY
        or settings.ENVIRONMENT == "test"
        or settings.OPENAI_API_KEY.startswith("sk-test")
        or settings.OPENAI_API_KEY == "your-openai-api-key"
    ):
        return None

    try:
        from openai import AsyncOpenAI
        from app.core.llm_client import resolve_model_token_limits

        token_limits = await resolve_model_token_limits()
        client_kwargs: Dict[str, Any] = {"api_key": settings.OPENAI_API_KEY}
        if settings.OPENAI_BASE_URL:
            client_kwargs["base_url"] = settings.OPENAI_BASE_URL
        client = AsyncOpenAI(**client_kwargs)

        headlines = "\n".join(
            f"- [{a.get('source', 'Báo')}] {a['title']}" + (f" ({a['snippet'][:220]})" if a.get("snippet") else "")
            for a in articles[:45]
        )
        cand_lines = "\n".join(
            f"- Nhóm: {c['category']} | Mã: {c['major_code']} | Ngành: {c['major_name']} | Gợi ý vĩ mô 2026: {c['macro_suggested_tier']} | Tín hiệu: {', '.join(c['matched_topics'][:2])}"
            for c in candidates
        )
        valid_codes = [c["major_code"] for c in candidates]

        system_prompt = (
            "Vai trò: Chuyên gia Phân tích Thị trường Lao động Việt Nam & Toàn cầu năm 2026 (tầm nhìn 2026–2030).\n"
            "Mục tiêu: Cập nhật bảng phân loại các ngành đại học đón đầu xu hướng năm 2026 từ dữ liệu báo chí vừa thu thập.\n\n"
            "YÊU CẦU & RÀNG BUỘC BẮT BUỘC (KHÔNG ĐƯỢC SAI SÓT):\n"
            "1. Bảo toàn 100% danh sách & Độ phủ (Zero Omission / Zero Fabrication):\n"
            "   - PHẢI đánh giá và trả về ĐÚNG TẤT CẢ các `major_code` có trong DANH SÁCH ỨNG VIÊN bên dưới.\n"
            "   - TUYỆT ĐỐI KHÔNG tự bịa thêm mã ngành mới ngoài danh sách, KHÔNG bỏ sót hoặc làm rơi bất kỳ ngành nào (đảm bảo mọi nhóm có ít nhất 3 ngành, riêng nhóm DỊCH VỤ XÃ HỘI có 2 ngành và THÚ Y có 1 ngành theo đúng Thông tư 74).\n"
            "   - Giữ nguyên chính xác chuỗi `category` và `major_code` từ đầu vào.\n"
            "2. Thang đo xu hướng vĩ mô 2026 (Macro Level Trend Benchmark 2026):\n"
            "   - Áp dụng MỘT thước đo chung duy nhất cho toàn bộ 23 nhóm ngành.\n"
            "   - `TIER_1` (Mũi nhọn bùng nổ 2026): Chỉ các ngành đang khát nhân lực đột phá toàn thị trường năm 2026 như Trí tuệ nhân tạo (AI/GenAI), Thiết kế vi mạch & Công nghệ bán dẫn, An ninh mạng, Khoa học dữ liệu, Fintech, Logistics & Chuỗi cung ứng, Robot & Tự động hóa công nghệ cao.\n"
            "   - `TIER_2` (Tăng trưởng mạnh 2026): Ngành tăng trưởng rõ rệt theo chuyển đổi số, kinh tế xanh/ESG, năng lượng sạch, y tế chất lượng cao, thương mại điện tử, truyền thông số, pháp chế thương mại, du lịch quốc tế.\n"
            "   - `TIER_3` (Nhu cầu ổn định 2026): Ngành thiết yếu truyền thống có tốc độ tăng trưởng vừa phải và ổn định dài hạn (nông nghiệp cơ bản, thú y, công tác xã hội, nghệ thuật hàn lâm, vận tải cơ bản, sư phạm truyền thống...).\n"
            "3. Chống chuẩn hóa sai (No Relative Inflation Per Group):\n"
            "   - KHÔNG xếp hạng tương đối riêng trong nội bộ từng nhóm. Nếu nhóm ngành X có các ngành mạnh nhất năm 2026 chỉ đạt mức `TIER_2` hoặc `TIER_3` trên bình diện toàn thị trường, BẮT BUỘC giữ nguyên `TIER_2` hoặc `TIER_3`, tuyệt đối KHÔNG đôn lên `TIER_1` chỉ để nhóm đó có đại diện Cấp 1.\n"
            "   - Nhóm `MÁY TÍNH VÀ CÔNG NGHỆ THÔNG TIN`, `KỸ THUẬT`, `KINH DOANH VÀ QUẢN LÝ` có thể có nhiều ngành đạt `TIER_1` và `TIER_2`; ngược lại các nhóm như `THÚ Y`, `DỊCH VỤ XÃ HỘI`, `NÔNG, LÂM NGHIỆP VÀ THỦY SẢN`, `PHÁP LUẬT` tuyệt đối KHÔNG gắn `TIER_1`.\n"
            "4. Pure Guidance & Tính xác thực 2026:\n"
            "   - Lý do `trend_reason` viết bằng tiếng Việt chuẩn mực, 1–2 câu súc tích (dưới 220 ký tự), nêu rõ động lực nhân lực năm 2026 đối chiếu từ tin tức thị trường.\n"
            "   - Tuyệt đối KHÔNG bịa số liệu lương/tỷ lệ thất nghiệp giả, KHÔNG nhắc học phí hay vị trí địa lý.\n"
            "5. Định dạng đầu ra:\n"
            "   - Trả về DUY NHẤT một JSON array hợp lệ (không bọc markdown ```json, không lời bình thêm). Mỗi phần tử gồm đúng 5 khóa: "
            '`{"category": "...", "major_code": "...", "major_name": "...", "trend_tier": "TIER_1"|"TIER_2"|"TIER_3", "trend_reason": "..."}`.'
        )

        user_prompt = (
            f"BỐI CẢNH ĐÁNH GIÁ: Năm 2026 | Truy vấn Admin: '{focus_query}'.\n"
            f"Tổng số nhóm ngành phải phủ đủ: {len(all_categories)} nhóm ({', '.join(all_categories)}).\n"
            f"Tổng số mã ngành BẮT BUỘC phải có mặt đầy đủ trong JSON đầu ra: {len(valid_codes)} mã.\n\n"
            f"TIN TỨC THỊ TRƯỜNG LAO ĐỘNG & TUYỂN SINH NĂM 2026 VỪA TÌM ĐƯỢC:\n{headlines}\n\n"
            f"DANH SÁCH {len(candidates)} NGÀNH ỨNG VIÊN CẦN PHÂN HẠNG VĨ MÔ 2026:\n{cand_lines}\n"
        )

        async def _call() -> str:
            try:
                resp = await client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                    max_tokens=token_limits["max_output_tokens"],
                )
                return (resp.choices[0].message.content or "").strip()
            finally:
                try:
                    await client.close()
                except Exception:
                    pass

        raw = await asyncio.wait_for(_call(), timeout=60.0)
        m = re.search(r"\[.*\]", raw, flags=re.DOTALL)
        if not m:
            return None
        parsed_list = json.loads(m.group(0))
        if not isinstance(parsed_list, list):
            return None

        refined: Dict[str, Dict[str, Any]] = {}
        for item in parsed_list:
            if not isinstance(item, dict):
                continue
            c = str(item.get("major_code") or "").strip()
            t = str(item.get("trend_tier") or "").upper()
            r = str(item.get("trend_reason") or "").strip()
            if c and t in ("TIER_1", "TIER_2", "TIER_3") and r:
                refined[c] = {"trend_tier": t, "trend_reason": r}
        return refined or None
    except Exception as exc:
        logger.debug("Trend Agent chuyển sang phân bậc vĩ mô tất định (%s)", exc)
        return None


def _build_classified_trend_map(
    candidates: List[Dict[str, Any]],
    llm_refined: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Tổng hợp bảng ngành xu hướng 2026 phủ 100% các nhóm ngành theo thang đo vĩ mô đồng nhất.
    Luôn bảo toàn nguyên tắc Macro Level Trend (kẹp chặt trần tier của từng nhóm để không bao giờ đôn ép sai).
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    llm_map = llm_refined or {}

    max_score = max((c["evidence_score"] for c in candidates), default=1.0) or 1.0
    classified: Dict[str, Dict[str, Any]] = {}

    for cand in candidates:
        code = cand["major_code"]
        cat = cand["category"]
        llm_entry = None
        for v in _code_variants(code):
            if v in llm_map:
                llm_entry = llm_map[v]
                break

        if llm_entry:
            tier = llm_entry["trend_tier"]
            reason = llm_entry["trend_reason"]
        else:
            # Dùng thang đo vĩ mô chuẩn hóa từ cluster/category (tuyệt đối không xếp hạng tương đối ép TIER_1)
            tier = cand.get("macro_suggested_tier") or "TIER_3"
            topics_str = ", ".join(cand["matched_topics"][:2]) if cand["matched_topics"] else cand["major_name"]
            top_headline = cand["sources"][0]["title"] if cand["sources"] else ""
            reason = (
                f"[{cat}] {topics_str}"
                + (f" (tham chiếu 2026: \"{top_headline[:80]}\")" if top_headline and cand["evidence_score"] >= 2.0 else ".")
            )

        # Chốt an toàn trần vĩ mô theo nhóm: chống sai sót nếu LLM lỡ đôn nhóm ít nhu cầu lên TIER_1
        _, _, cat_max_tier = CATEGORY_TREND_QUOTA.get(cat, (3, 3, "TIER_3"))
        max_allowed_priority = TREND_TIER_CONFIG[cat_max_tier]["priority"]
        if TREND_TIER_CONFIG[tier]["priority"] > max_allowed_priority:
            tier = cat_max_tier

        cfg = TREND_TIER_CONFIG[tier]
        base_by_tier = 92 if tier == "TIER_1" else (81 if tier == "TIER_2" else 70)
        norm_score = min(99, max(62, int(round(base_by_tier + (cand["evidence_score"] / max_score) * 7))))

        classified[code] = {
            "major_code": code,
            "major_name": cand["major_name"],
            "category": cat,
            "trend_tier": tier,
            "trend_priority": cfg["priority"],
            "trend_label": cfg["label"],
            "trend_score": norm_score,
            "trend_reason": reason,
            "trend_sources": cand["sources"],
            "updated_at": now_iso,
        }

    return classified


def _strip_old_trend_prefix(outlook: str) -> str:
    if not outlook:
        return ""
    return re.sub(r"^\[XU HƯỚNG (?:BẬC|CẤP) [123][^\]]*\]\s*[^\n]*\n*", "", outlook).strip()


async def apply_trending_markers(
    db: Optional[AsyncSession],
    registry_payload: Dict[str, Any],
    sync_active_json: Optional[bool] = None,
) -> None:
    """
    Lưu vĩnh viễn các ngành xu hướng (đã được Admin xác nhận) vào:
    1. Bảng `majors` trong CSDL PostgreSQL/SQLite (`cognitive_attributes["_trend"]` + `industry_outlook`).
       Nếu bảng `majors` thiếu các ngành TT74 đang được đánh dấu xu hướng, tự động đồng bộ đầy đủ 435 ngành trước khi gắn nhãn.
    2. File active catalog (`moet_taxonomy_active.json`) & registry (`trending_majors_registry.json`).
    """
    reg_path = _get_registry_path()
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(registry_payload, f, ensure_ascii=False, indent=2)

    majors_map: Dict[str, Dict[str, Any]] = registry_payload.get("majors") or {}
    expanded_lookup: Dict[str, Dict[str, Any]] = {}
    for code, entry in majors_map.items():
        for v in _code_variants(code):
            expanded_lookup[v] = entry

    should_sync_active = sync_active_json if sync_active_json is not None else (settings.ENVIRONMENT != "test")
    if should_sync_active:
        from app.services.taxonomy.service import load_seed_majors

        active_path = SEEDS_DIR / "moet_taxonomy_active.json"
        seed_majors = load_seed_majors()
        if seed_majors:
            for m in seed_majors:
                c = str(m.get("major_code") or "").strip()
                t_info = expanded_lookup.get(c)
                cog = dict(m.get("cognitive") or m.get("cognitive_attributes") or {})
                base_outlook = _strip_old_trend_prefix(m.get("outlook") or m.get("industry_outlook") or "")

                if t_info and t_info.get("trend_tier") in ("TIER_1", "TIER_2", "TIER_3"):
                    tier = t_info["trend_tier"]
                    cog["_trend"] = t_info
                    m["is_trending"] = True
                    m["trend_tier"] = tier
                    m["trend_priority"] = t_info["trend_priority"]
                    m["trend_label"] = t_info["trend_label"]
                    m["trend_reason"] = t_info["trend_reason"]
                    m["trend_sources"] = t_info.get("trend_sources", [])
                    tier_num = tier.replace("TIER_", "")
                    new_outlook = f"[XU HƯỚNG BẬC {tier_num}] {t_info['trend_reason']}" + (
                        f"\n{base_outlook}" if base_outlook else ""
                    )
                    m["outlook"] = new_outlook
                else:
                    cog.pop("_trend", None)
                    m.pop("is_trending", None)
                    m.pop("trend_tier", None)
                    m.pop("trend_priority", None)
                    m.pop("trend_label", None)
                    m.pop("trend_reason", None)
                    m.pop("trend_sources", None)
                    if base_outlook:
                        m["outlook"] = base_outlook

                if cog:
                    m["cognitive"] = cog

            wrapper_meta: Dict[str, Any] = {
                "circular_title": "Thông tư 74/2026/TT-BGDĐT",
                "circular_code": "74/2026/TT-BGDĐT",
                "total_majors": len(seed_majors),
                "majors": seed_majors,
            }
            if active_path.exists():
                try:
                    with open(active_path, "r", encoding="utf-8") as rf:
                        prev_data = json.load(rf)
                        if isinstance(prev_data, dict):
                            wrapper_meta["circular_title"] = prev_data.get("circular_title", wrapper_meta["circular_title"])
                            wrapper_meta["circular_code"] = prev_data.get("circular_code", wrapper_meta["circular_code"])
                except Exception:
                    pass
            with open(active_path, "w", encoding="utf-8") as wf:
                json.dump(wrapper_meta, wf, ensure_ascii=False, indent=2)

    # Cập nhật trực tiếp bảng `majors` trong CSDL
    if db is not None:
        try:
            res = await db.execute(select(Major).where(Major.is_active == True))
            db_majors = list(res.scalars().all())
            existing_db_codes = {str(m.major_code).strip() for m in db_majors}

            # Đảm bảo mọi ngành được đánh dấu xu hướng đều có bản ghi trong bảng `majors`
            missing_trending_codes = [c for c in majors_map.keys() if c not in existing_db_codes]
            if missing_trending_codes:
                from app.services.taxonomy.service import bulk_sync_majors, load_seed_majors

                seed_list = load_seed_majors()
                if seed_list:
                    missing_set = set(missing_trending_codes)
                    to_insert = [s for s in seed_list if str(s.get("major_code") or "").strip() in missing_set]
                    if to_insert:
                        await bulk_sync_majors(db, to_insert)
                        res = await db.execute(select(Major))
                        db_majors = list(res.scalars().all())

            for db_m in db_majors:
                t_info = expanded_lookup.get(str(db_m.major_code).strip())
                cog = dict(db_m.cognitive_attributes or {})
                base_outlook = _strip_old_trend_prefix(db_m.industry_outlook or "")

                if t_info and t_info.get("trend_tier") in ("TIER_1", "TIER_2", "TIER_3"):
                    cog["_trend"] = t_info
                    tier_num = str(t_info["trend_tier"]).replace("TIER_", "")
                    db_m.cognitive_attributes = cog
                    db_m.industry_outlook = f"[XU HƯỚNG BẬC {tier_num}] {t_info['trend_reason']}" + (
                        f"\n{base_outlook}" if base_outlook else ""
                    )
                else:
                    if "_trend" in cog:
                        cog.pop("_trend", None)
                        db_m.cognitive_attributes = cog
                    if base_outlook != (db_m.industry_outlook or ""):
                        db_m.industry_outlook = base_outlook or "Đào tạo chuẩn Bộ GD&ĐT"

            await db.commit()
        except Exception as exc:
            logger.warning("Cập nhật dấu xu hướng vào DB majors gặp cảnh báo (%s)", exc)


async def run_trend_discovery_agent(
    db: Optional[AsyncSession],
    focus_query: str = "dự báo nhu cầu nhân lực thị trường lao động Việt Nam 2026 ngành mũi nhọn AI bán dẫn y tế kinh tế xanh",
    triggered_by: str = "admin",
    auto_save: bool = False,
    override_articles: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Điểm chạy chính của AI Trend Hunter Agent (CHỈ gọi khi Admin bấm nút).
    - Mặc định `auto_save=False`: Trả về BẢN NHÁP phủ 100% các nhóm ngành theo thang đo vĩ mô
      để Admin kiểm tra/chỉnh bậc rồi bấm nút **Lưu vào CSDL**.
    """
    t0 = time.perf_counter()

    from app.services.taxonomy.service import load_seed_majors

    catalog_majors = load_seed_majors()
    if not catalog_majors and db is not None:
        res = await db.execute(select(Major).where(Major.is_active == True))
        catalog_majors = [
            {
                "major_code": m.major_code,
                "name": m.name,
                "category": m.category,
                "outlook": m.industry_outlook,
            }
            for m in res.scalars().all()
        ]

    articles = (
        override_articles
        if override_articles is not None
        else await search_trending_majors_online(focus_query=focus_query)
    )

    if not articles:
        return {
            "status": "no_web_results",
            "pending_save": False,
            "saved_to_db": False,
            "message": "Không thu thập được dữ liệu tìm kiếm trực tuyến mới (kiểm tra kết nối mạng). Dữ liệu CSDL được giữ nguyên.",
            "articles_scanned": 0,
            "total_trending_marked": 0,
            "categories_covered": 0,
            "total_categories": 0,
            "tier_counts": {"TIER_1": 0, "TIER_2": 0, "TIER_3": 0},
            "trending_majors": [],
            "search_sources": [],
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }

    candidates, all_categories = _extract_candidates_from_articles(articles, catalog_majors)
    llm_refined = await _refine_tiers_with_llm(focus_query, articles, candidates, all_categories)
    classified_majors = _build_classified_trend_map(candidates, llm_refined=llm_refined)

    now_iso = datetime.now(timezone.utc).isoformat()
    source_summaries = [
        {
            "title": a["title"],
            "url": a["url"],
            "source": a.get("source", "Web Search"),
            "published_at": a.get("published_at", ""),
        }
        for a in articles[:12]
    ]

    ordered_list = sorted(
        classified_majors.values(),
        key=lambda item: (item["trend_priority"], item["trend_score"], item["category"]),
        reverse=True,
    )
    covered_cats_count = len({m["category"] for m in ordered_list if m.get("category")})
    tier_counts = {
        "TIER_1": sum(1 for m in ordered_list if m["trend_tier"] == "TIER_1"),
        "TIER_2": sum(1 for m in ordered_list if m["trend_tier"] == "TIER_2"),
        "TIER_3": sum(1 for m in ordered_list if m["trend_tier"] == "TIER_3"),
    }

    if auto_save:
        saved_res = await save_trending_majors_to_db(
            db=db,
            majors_list=ordered_list,
            focus_query=focus_query,
            articles_scanned=len(articles),
            search_sources=source_summaries,
            triggered_by=triggered_by,
            llm_refined=bool(llm_refined),
        )
        saved_res["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        return saved_res

    return {
        "status": "draft_ready",
        "pending_save": True,
        "saved_to_db": False,
        "message": (
            f"Agent đã quét {len(articles)} nguồn tin và đề xuất {len(ordered_list)} ngành xu hướng "
            f"(phủ {covered_cats_count}/{len(all_categories)} nhóm ngành theo thang đo vĩ mô). Bấm \"Lưu vào CSDL\" để áp dụng."
        ),
        "last_run_at": now_iso,
        "triggered_by": triggered_by,
        "focus_query": focus_query,
        "articles_scanned": len(articles),
        "llm_refined": bool(llm_refined),
        "categories_covered": covered_cats_count,
        "total_categories": len(all_categories),
        "total_trending_marked": len(ordered_list),
        "tier_counts": tier_counts,
        "trending_majors": ordered_list,
        "search_sources": source_summaries,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


async def save_trending_majors_to_db(
    db: Optional[AsyncSession],
    majors_list: List[Dict[str, Any]],
    focus_query: str = "",
    articles_scanned: int = 0,
    search_sources: Optional[List[Dict[str, Any]]] = None,
    triggered_by: str = "admin",
    llm_refined: bool = False,
) -> Dict[str, Any]:
    """
    Lưu chính thức danh sách ngành xu hướng đã được Admin duyệt vào CSDL (`majors`),
    `moet_taxonomy_active.json`, `trending_majors_registry.json` và bảng `staging_records`.
    """
    from app.services.taxonomy.service import load_seed_majors

    seed_majors = load_seed_majors()
    seed_lookup = {str(m.get("major_code") or "").strip(): m for m in seed_majors}
    now_iso = datetime.now(timezone.utc).isoformat()

    normalized_map: Dict[str, Dict[str, Any]] = {}
    for raw in majors_list:
        raw_code = str(raw.get("major_code") or "").strip()
        tier = str(raw.get("trend_tier") or "NONE").upper().strip()
        if not raw_code or tier not in ("TIER_1", "TIER_2", "TIER_3"):
            continue
        matched = next((seed_lookup[v] for v in _code_variants(raw_code) if v in seed_lookup), None)
        canonical_code = str(matched["major_code"]).strip() if matched else raw_code
        cfg = TREND_TIER_CONFIG[tier]
        normalized_map[canonical_code] = {
            "major_code": canonical_code,
            "major_name": raw.get("major_name") or (matched["name"] if matched else f"Ngành {canonical_code}"),
            "category": raw.get("category") or (matched.get("category", "Khác") if matched else "Khác"),
            "trend_tier": tier,
            "trend_priority": cfg["priority"],
            "trend_label": cfg["label"],
            "trend_score": int(raw.get("trend_score") or (94 if tier == "TIER_1" else 83 if tier == "TIER_2" else 72)),
            "trend_reason": str(raw.get("trend_reason") or "").strip() or f"Đánh dấu xu hướng {cfg['short_label']} theo thang đo vĩ mô.",
            "trend_sources": raw.get("trend_sources") or [],
            "updated_at": now_iso,
        }

    src_list = search_sources or []
    registry_payload = {
        "last_run_at": now_iso,
        "saved_at": now_iso,
        "triggered_by": triggered_by,
        "focus_query": focus_query,
        "articles_scanned": articles_scanned,
        "llm_refined": llm_refined,
        "search_sources": src_list,
        "majors": normalized_map,
    }

    await apply_trending_markers(db, registry_payload)

    if db is not None:
        try:
            digest = hashlib.sha256(f"trend-save-{focus_query}-{now_iso}".encode("utf-8")).hexdigest()
            tier_1_names = [v["major_name"] for v in normalized_map.values() if v["trend_tier"] == "TIER_1"]
            staging_entry = StagingRecord(
                id=uuid.uuid4(),
                stream_type=StagingStreamType.STREAM_B_ROADMAP,
                status=StagingStatus.APPROVED,
                major_code="TREND-AGENT",
                content_hash=digest,
                raw_content=f"Lưu {len(normalized_map)} ngành xu hướng vào CSDL ({focus_query})",
                extracted_payload={
                    "type": "TREND_DISCOVERY_SAVED",
                    "focus_query": focus_query,
                    "articles_scanned": articles_scanned,
                    "total_marked": len(normalized_map),
                    "tier_1_sample": tier_1_names[:6],
                },
                source_title=f"Lưu CSDL · {len(normalized_map)} ngành xu hướng",
                source_url=src_list[0]["url"] if src_list and src_list[0].get("url") else "https://news.google.com",
                source_page=f"{len(normalized_map)} ngành đã lưu",
                reviewed_at=datetime.now(timezone.utc),
                review_notes=f"Admin ({triggered_by}) đã xác nhận lưu danh mục xu hướng vào CSDL",
            )
            db.add(staging_entry)
            await db.commit()
        except Exception as exc:
            logger.debug("Không ghi staging audit khi lưu Trend Agent (%s)", exc)

    ordered_list = sorted(
        normalized_map.values(),
        key=lambda item: (item["trend_priority"], item["trend_score"]),
        reverse=True,
    )
    covered_cats = len({m["category"] for m in ordered_list if m.get("category") and m["category"] != "Khác"})
    all_cats_cnt = len({str(m.get("category") or "") for m in seed_majors if m.get("category") and m.get("category") != "Khác"})
    return {
        "status": "saved",
        "pending_save": False,
        "saved_to_db": True,
        "has_run": True,
        "message": f"Đã lưu {len(ordered_list)} ngành xu hướng (phủ {covered_cats} nhóm ngành) vào CSDL thành công.",
        "last_run_at": now_iso,
        "saved_at": now_iso,
        "triggered_by": triggered_by,
        "focus_query": focus_query,
        "articles_scanned": articles_scanned,
        "categories_covered": covered_cats,
        "total_categories": all_cats_cnt or covered_cats,
        "total_trending_marked": len(ordered_list),
        "tier_counts": {
            "TIER_1": sum(1 for m in ordered_list if m["trend_tier"] == "TIER_1"),
            "TIER_2": sum(1 for m in ordered_list if m["trend_tier"] == "TIER_2"),
            "TIER_3": sum(1 for m in ordered_list if m["trend_tier"] == "TIER_3"),
        },
        "trending_majors": ordered_list,
        "search_sources": src_list,
    }


async def update_single_major_trend_tier(
    db: Optional[AsyncSession],
    major_code: str,
    trend_tier: str,
    trend_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Cho phép Admin tinh chỉnh bậc ưu tiên xu hướng của 1 ngành trực tiếp trong CSDL & registry."""
    tier_norm = str(trend_tier or "NONE").upper().strip()
    if tier_norm not in TREND_TIER_CONFIG:
        tier_norm = "NONE"

    reg = load_trending_registry()
    majors_map = dict(reg.get("majors") or {})
    variants = _code_variants(major_code)

    from app.services.taxonomy.service import load_seed_majors

    seed_majors = load_seed_majors()
    seed_lookup = {str(m.get("major_code") or "").strip(): m for m in seed_majors}
    matched_seed = next((seed_lookup[v] for v in variants if v in seed_lookup), None)
    canonical_code = matched_seed["major_code"] if matched_seed else str(major_code).strip()
    major_name = matched_seed["name"] if matched_seed else f"Ngành {canonical_code}"
    category = matched_seed.get("category", "Khác") if matched_seed else "Khác"

    existing_entry = None
    for v in variants:
        if v in majors_map:
            existing_entry = majors_map.pop(v)

    if tier_norm != "NONE":
        cfg = TREND_TIER_CONFIG[tier_norm]
        majors_map[canonical_code] = {
            "major_code": canonical_code,
            "major_name": (existing_entry or {}).get("major_name") or major_name,
            "category": (existing_entry or {}).get("category") or category,
            "trend_tier": tier_norm,
            "trend_priority": cfg["priority"],
            "trend_label": cfg["label"],
            "trend_score": (existing_entry or {}).get("trend_score") or (95 if tier_norm == "TIER_1" else 85 if tier_norm == "TIER_2" else 75),
            "trend_reason": trend_reason or (existing_entry or {}).get("trend_reason") or "Quản trị viên phân bậc ưu tiên xu hướng.",
            "trend_sources": (existing_entry or {}).get("trend_sources") or [],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    reg["majors"] = majors_map
    reg["saved_at"] = datetime.now(timezone.utc).isoformat()
    await apply_trending_markers(db, reg)
    return await get_trending_status_async(db)


async def clear_trending_markers(db: Optional[AsyncSession]) -> Dict[str, Any]:
    """Xóa toàn bộ đánh dấu xu hướng trên CSDL & registry."""
    empty_reg = {
        "last_run_at": None,
        "saved_at": None,
        "triggered_by": None,
        "focus_query": "",
        "articles_scanned": 0,
        "search_sources": [],
        "majors": {},
    }
    await apply_trending_markers(db, empty_reg)
    return await get_trending_status_async(db)


async def get_trending_status_async(db: Optional[AsyncSession] = None) -> Dict[str, Any]:
    """
    Trả về danh sách ngành xu hướng đã LƯU TRONG CSDL (ưu tiên đọc từ bảng `majors` trong DB).
    Chỉ đọc dữ liệu đã lưu — TUYỆT ĐỐI không chạy tìm kiếm web.
    """
    reg = load_trending_registry()
    majors_map: Dict[str, Dict[str, Any]] = dict(reg.get("majors") or {})

    # Nếu kết nối được DB thực tế và bảng majors đang chứa dấu `_trend`, ưu tiên đồng bộ từ DB
    if db is not None and settings.ENVIRONMENT != "test":
        try:
            res = await db.execute(select(Major).where(Major.is_active == True))
            db_rows = list(res.scalars().all())
            db_trends: Dict[str, Dict[str, Any]] = {}
            for m in db_rows:
                cog = m.cognitive_attributes or {}
                t_info = cog.get("_trend") if isinstance(cog, dict) else None
                if isinstance(t_info, dict) and t_info.get("trend_tier") in ("TIER_1", "TIER_2", "TIER_3"):
                    db_trends[m.major_code] = {
                        "major_code": m.major_code,
                        "major_name": t_info.get("major_name") or m.name,
                        "category": t_info.get("category") or m.category,
                        "trend_tier": t_info["trend_tier"],
                        "trend_priority": int(t_info.get("trend_priority") or TREND_TIER_CONFIG[t_info["trend_tier"]]["priority"]),
                        "trend_label": t_info.get("trend_label") or TREND_TIER_CONFIG[t_info["trend_tier"]]["label"],
                        "trend_score": int(t_info.get("trend_score") or 80),
                        "trend_reason": t_info.get("trend_reason") or "",
                        "trend_sources": t_info.get("trend_sources") or [],
                        "updated_at": t_info.get("updated_at") or "",
                    }
            if db_trends:
                # Hợp nhất: DB là nguồn chính thức, giữ thêm thông tin nếu registry bổ sung
                merged = dict(majors_map)
                merged.update(db_trends)
                majors_map = merged
        except Exception as exc:
            logger.debug("Đọc trend từ DB bỏ qua (%s), dùng registry đã lưu", exc)

    ordered_list = sorted(
        [m for m in majors_map.values() if isinstance(m, dict) and m.get("trend_tier") in ("TIER_1", "TIER_2", "TIER_3")],
        key=lambda item: (int(item.get("trend_priority", 0)), int(item.get("trend_score", 0))),
        reverse=True,
    )
    covered_cats = len({m.get("category") for m in ordered_list if m.get("category") and m.get("category") != "Khác"})
    return {
        "status": "saved" if ordered_list else "empty",
        "pending_save": False,
        "saved_to_db": bool(ordered_list),
        "has_run": bool(reg.get("last_run_at") or ordered_list),
        "trigger_mode": "MANUAL_ADMIN_ONLY",
        "last_run_at": reg.get("last_run_at"),
        "saved_at": reg.get("saved_at") or reg.get("last_run_at"),
        "triggered_by": reg.get("triggered_by"),
        "focus_query": reg.get("focus_query") or "",
        "articles_scanned": int(reg.get("articles_scanned") or 0),
        "categories_covered": covered_cats,
        "total_categories": 23,
        "total_trending_marked": len(ordered_list),
        "tier_counts": {
            "TIER_1": sum(1 for m in ordered_list if m.get("trend_tier") == "TIER_1"),
            "TIER_2": sum(1 for m in ordered_list if m.get("trend_tier") == "TIER_2"),
            "TIER_3": sum(1 for m in ordered_list if m.get("trend_tier") == "TIER_3"),
        },
        "trending_majors": ordered_list,
        "search_sources": reg.get("search_sources") or [],
    }


def get_trending_status() -> Dict[str, Any]:
    """Phiên bản đồng bộ trả về trạng thái đã lưu trong registry (không chạy tìm kiếm)."""
    reg = load_trending_registry()
    majors_map = reg.get("majors") or {}
    ordered_list = sorted(
        [m for m in majors_map.values() if isinstance(m, dict) and m.get("trend_tier") in ("TIER_1", "TIER_2", "TIER_3")],
        key=lambda item: (int(item.get("trend_priority", 0)), int(item.get("trend_score", 0))),
        reverse=True,
    )
    covered_cats = len({m.get("category") for m in ordered_list if m.get("category") and m.get("category") != "Khác"})
    return {
        "status": "saved" if ordered_list else "empty",
        "pending_save": False,
        "saved_to_db": bool(ordered_list),
        "has_run": bool(reg.get("last_run_at") or ordered_list),
        "trigger_mode": "MANUAL_ADMIN_ONLY",
        "last_run_at": reg.get("last_run_at"),
        "saved_at": reg.get("saved_at") or reg.get("last_run_at"),
        "triggered_by": reg.get("triggered_by"),
        "focus_query": reg.get("focus_query") or "",
        "articles_scanned": int(reg.get("articles_scanned") or 0),
        "categories_covered": covered_cats,
        "total_categories": 23,
        "total_trending_marked": len(ordered_list),
        "tier_counts": {
            "TIER_1": sum(1 for m in ordered_list if m.get("trend_tier") == "TIER_1"),
            "TIER_2": sum(1 for m in ordered_list if m.get("trend_tier") == "TIER_2"),
            "TIER_3": sum(1 for m in ordered_list if m.get("trend_tier") == "TIER_3"),
        },
        "trending_majors": ordered_list,
        "search_sources": reg.get("search_sources") or [],
    }
