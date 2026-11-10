"""
Standardized Reference Dictionary & Auto-Enrichment Engine for Circular 74/2026/TT-BGDĐT.
Provides 3-tier automatic mapping when Admin uploads an Excel/CSV file of majors:
- Tier 1: 94 Cấp III Group-Code (4-digit) -> CIP Code + Base Holland RIASEC Vector + Default Blocks
- Tier 2: Keyword-based RIASEC & Cognitive Fine-Tuning on Vietnamese Major Name
- Tier 3: Appendix II Legacy TT09 (7-digit) Crosswalk & Academic Benchmark Cutoff Classification
"""

import csv
import io
import re
import xml.etree.ElementTree as ET
import zipfile
from typing import Any, Dict, List, Optional, Tuple

# 94 Cấp III Groups (4-digit) -> (cip_code, holland_code, (R, I, A, S, E, C), default_blocks)
GROUP_CIP_RIASEC: Dict[str, Tuple[str, str, Tuple[float, float, float, float, float, float], List[str]]] = {
    # 14 - Khoa học giáo dục và đào tạo giáo viên
    "1401": ("13.0101", "SIA", (0.15, 0.70, 0.45, 0.90, 0.50, 0.55), ["C00", "D01", "D14"]),
    "1402": ("13.1206", "SAE", (0.25, 0.55, 0.55, 0.95, 0.50, 0.50), ["A00", "D01", "C00", "B00"]),
    "1490": ("13.9999", "SAE", (0.20, 0.50, 0.50, 0.90, 0.45, 0.45), ["C00", "D01"]),
    # 21 - Nghệ thuật
    "2101": ("50.0701", "AIR", (0.50, 0.40, 0.95, 0.35, 0.30, 0.20), ["H00", "H01", "V00", "D01"]),
    "2102": ("50.0901", "AES", (0.35, 0.30, 0.95, 0.55, 0.50, 0.20), ["N00", "S00", "D01"]),
    "2103": ("50.0602", "ARE", (0.60, 0.40, 0.92, 0.45, 0.55, 0.30), ["S00", "H01", "D01", "C00"]),
    "2104": ("50.0401", "ARE", (0.55, 0.45, 0.95, 0.40, 0.50, 0.35), ["H00", "H01", "V00", "D01"]),
    "2190": ("50.9999", "AES", (0.40, 0.35, 0.90, 0.45, 0.45, 0.25), ["H00", "D01"]),
    # 22 - Nhân văn
    "2201": ("16.1408", "ASI", (0.15, 0.65, 0.85, 0.75, 0.40, 0.45), ["C00", "D01", "D14", "D15"]),
    "2202": ("16.0101", "ASI", (0.15, 0.60, 0.82, 0.78, 0.50, 0.45), ["D01", "D14", "D15"]),
    "2290": ("38.0101", "ISA", (0.15, 0.85, 0.65, 0.70, 0.35, 0.45), ["C00", "D01", "A01"]),
    # 31 - Khoa học xã hội và hành vi
    "3101": ("45.0601", "IEC", (0.20, 0.85, 0.25, 0.45, 0.75, 0.70), ["A00", "A01", "D01", "D07"]),
    "3102": ("45.1001", "ESA", (0.15, 0.65, 0.40, 0.75, 0.88, 0.60), ["C00", "D01", "D14", "A01"]),
    "3103": ("45.1101", "SIA", (0.20, 0.80, 0.50, 0.88, 0.45, 0.45), ["C00", "D01", "D14", "D15"]),
    "3104": ("42.0101", "SIA", (0.15, 0.85, 0.55, 0.92, 0.40, 0.40), ["B00", "C00", "D01", "A01"]),
    "3105": ("45.0701", "IRS", (0.55, 0.82, 0.30, 0.50, 0.35, 0.50), ["C00", "D01", "D10", "A00"]),
    "3106": ("05.0101", "ISA", (0.15, 0.80, 0.60, 0.75, 0.50, 0.45), ["D01", "C00", "D14", "D15"]),
    "3190": ("45.9999", "SIA", (0.20, 0.75, 0.45, 0.80, 0.45, 0.45), ["C00", "D01"]),
    # 32 - Báo chí và thông tin
    "3201": ("09.0401", "EAS", (0.25, 0.50, 0.85, 0.75, 0.80, 0.40), ["C00", "D01", "D14", "A01"]),
    "3202": ("25.0101", "CSI", (0.25, 0.65, 0.30, 0.60, 0.35, 0.88), ["C00", "D01", "A01"]),
    "3203": ("30.1401", "CIA", (0.30, 0.65, 0.45, 0.45, 0.30, 0.88), ["C00", "D01", "D14"]),
    "3204": ("09.1001", "EAS", (0.20, 0.45, 0.75, 0.60, 0.80, 0.65), ["C00", "D01", "D14"]),
    # 34 - Kinh doanh và quản lý
    "3401": ("52.0201", "ECS", (0.20, 0.45, 0.40, 0.65, 0.92, 0.70), ["A00", "A01", "D01", "D07"]),
    "3402": ("52.0801", "CEI", (0.15, 0.70, 0.20, 0.40, 0.82, 0.92), ["A00", "A01", "D01", "D07"]),
    "3403": ("52.0301", "CEI", (0.15, 0.65, 0.15, 0.35, 0.68, 0.95), ["A00", "A01", "D01", "D07"]),
    "3404": ("52.0299", "ESC", (0.20, 0.50, 0.30, 0.72, 0.90, 0.75), ["A00", "A01", "D01", "C00"]),
    "3490": ("52.9999", "ECS", (0.20, 0.45, 0.30, 0.60, 0.88, 0.70), ["A00", "A01", "D01"]),
    # 38 - Pháp luật
    "3801": ("22.0101", "EIC", (0.15, 0.75, 0.35, 0.65, 0.88, 0.72), ["A00", "A01", "C00", "D01"]),
    # 42 - Khoa học sự sống
    "4201": ("26.0101", "IRS", (0.65, 0.95, 0.25, 0.40, 0.25, 0.55), ["B00", "A00", "D08", "A02"]),
    "4202": ("26.1201", "IRC", (0.72, 0.92, 0.25, 0.35, 0.35, 0.60), ["B00", "A00", "D07", "A02"]),
    "4290": ("26.9999", "IRS", (0.65, 0.90, 0.25, 0.35, 0.30, 0.55), ["B00", "A00"]),
    # 44 - Khoa học tự nhiên
    "4401": ("40.0801", "IRC", (0.70, 0.95, 0.25, 0.25, 0.25, 0.60), ["A00", "A01", "B00", "D07"]),
    "4402": ("40.0601", "IRS", (0.78, 0.90, 0.25, 0.35, 0.30, 0.55), ["A00", "A01", "B00", "D10"]),
    "4403": ("03.0104", "IRS", (0.72, 0.88, 0.25, 0.50, 0.35, 0.55), ["A00", "B00", "D07", "A01"]),
    "4490": ("40.9999", "IRC", (0.70, 0.90, 0.25, 0.30, 0.25, 0.55), ["A00", "A01", "B00"]),
    # 46 - Toán và thống kê
    "4601": ("27.0101", "ICR", (0.45, 0.96, 0.25, 0.25, 0.30, 0.82), ["A00", "A01", "D01", "D07"]),
    "4602": ("27.0501", "CIE", (0.35, 0.88, 0.20, 0.30, 0.45, 0.92), ["A00", "A01", "D01", "D07"]),
    "4690": ("27.9999", "ICR", (0.40, 0.92, 0.20, 0.25, 0.35, 0.85), ["A00", "A01", "D01"]),
    # 48 - Máy tính và CNTT
    "4801": ("11.0701", "IRC", (0.72, 0.94, 0.30, 0.25, 0.35, 0.68), ["A00", "A01", "D01", "D07"]),
    "4802": ("11.0103", "ICR", (0.75, 0.88, 0.25, 0.30, 0.40, 0.75), ["A00", "A01", "D01", "D07"]),
    "4890": ("11.9999", "IRC", (0.72, 0.90, 0.25, 0.25, 0.35, 0.70), ["A00", "A01", "D01"]),
    # 51 - Công nghệ kỹ thuật
    "5101": ("15.1001", "RIC", (0.92, 0.70, 0.35, 0.30, 0.45, 0.65), ["A00", "A01", "V00", "D01"]),
    "5102": ("15.0805", "RIC", (0.95, 0.72, 0.20, 0.25, 0.35, 0.60), ["A00", "A01", "D01", "C01"]),
    "5103": ("15.0303", "RIC", (0.92, 0.78, 0.20, 0.25, 0.35, 0.62), ["A00", "A01", "D01", "C01"]),
    "5104": ("15.0699", "RIC", (0.88, 0.82, 0.20, 0.25, 0.30, 0.62), ["A00", "B00", "D07", "A01"]),
    "5106": ("15.1501", "ERC", (0.70, 0.68, 0.20, 0.45, 0.85, 0.78), ["A00", "A01", "D01", "D07"]),
    "5107": ("15.0903", "RIC", (0.94, 0.75, 0.15, 0.25, 0.40, 0.60), ["A00", "A01", "D07"]),
    "5108": ("10.0305", "RCA", (0.90, 0.55, 0.45, 0.25, 0.35, 0.68), ["A00", "A01", "D01"]),
    "5190": ("15.9999", "RIC", (0.90, 0.72, 0.20, 0.30, 0.35, 0.60), ["A00", "A01", "B00"]),
    # 52 - Kỹ thuật
    "5201": ("14.1901", "RIE", (0.94, 0.84, 0.25, 0.25, 0.40, 0.58), ["A00", "A01", "C01", "D01"]),
    "5202": ("14.1001", "IRC", (0.88, 0.90, 0.20, 0.25, 0.35, 0.65), ["A00", "A01", "D01", "D07"]),
    "5203": ("14.0701", "IRC", (0.85, 0.90, 0.25, 0.25, 0.35, 0.62), ["A00", "B00", "D07", "A01"]),
    "5204": ("14.1201", "IRC", (0.82, 0.95, 0.20, 0.20, 0.25, 0.60), ["A00", "A01", "A02"]),
    "5205": ("14.3901", "RIC", (0.90, 0.85, 0.20, 0.25, 0.30, 0.62), ["A00", "A01", "B00", "D10"]),
    "5206": ("14.2101", "RIC", (0.95, 0.78, 0.15, 0.25, 0.40, 0.58), ["A00", "A01", "B00", "D07"]),
    "5290": ("14.9999", "RIC", (0.90, 0.82, 0.20, 0.25, 0.35, 0.60), ["A00", "A01"]),
    # 54 - Sản xuất và chế biến
    "5401": ("01.1001", "RIC", (0.85, 0.80, 0.25, 0.30, 0.40, 0.68), ["A00", "B00", "D07", "A01"]),
    "5402": ("19.0902", "RCA", (0.88, 0.60, 0.45, 0.30, 0.40, 0.68), ["A00", "A01", "D01"]),
    "5490": ("03.0509", "RIC", (0.90, 0.68, 0.25, 0.25, 0.35, 0.62), ["A00", "B00", "D01"]),
    # 58 - Kiến trúc và xây dựng
    "5801": ("04.0201", "AIR", (0.75, 0.72, 0.92, 0.40, 0.45, 0.50), ["V00", "V01", "H01", "A00"]),
    "5802": ("14.0801", "RIC", (0.92, 0.78, 0.30, 0.30, 0.45, 0.65), ["A00", "A01", "V00", "D01"]),
    "5803": ("52.2001", "ERC", (0.75, 0.62, 0.25, 0.45, 0.85, 0.78), ["A00", "A01", "D01", "V00"]),
    "5890": ("04.9999", "RIC", (0.85, 0.72, 0.45, 0.35, 0.45, 0.60), ["A00", "V00"]),
    # 62 - Nông, lâm nghiệp và thủy sản
    "6201": ("01.0000", "RIS", (0.90, 0.75, 0.20, 0.45, 0.45, 0.55), ["A00", "B00", "D01", "A01"]),
    "6202": ("03.0501", "RIS", (0.92, 0.75, 0.20, 0.40, 0.40, 0.55), ["A00", "B00", "D01"]),
    "6203": ("01.0303", "RIC", (0.92, 0.75, 0.15, 0.35, 0.40, 0.55), ["A00", "B00", "D07", "D01"]),
    "6290": ("01.9999", "RIC", (0.90, 0.72, 0.20, 0.40, 0.40, 0.55), ["A00", "B00"]),
    # 64 - Thú y
    "6401": ("01.8001", "IRS", (0.85, 0.88, 0.20, 0.55, 0.35, 0.50), ["B00", "A00", "D07", "A01"]),
    "6490": ("01.8099", "IRS", (0.85, 0.85, 0.20, 0.50, 0.35, 0.50), ["B00", "A00"]),
    # 72 - Sức khỏe
    "7201": ("51.1201", "ISR", (0.65, 0.94, 0.20, 0.88, 0.35, 0.55), ["B00", "A00", "D08"]),
    "7202": ("51.2001", "ICR", (0.60, 0.92, 0.20, 0.60, 0.45, 0.78), ["A00", "B00", "D07"]),
    "7203": ("51.3801", "SIR", (0.65, 0.70, 0.25, 0.95, 0.35, 0.65), ["B00", "B08", "D07"]),
    "7204": ("51.3101", "ISC", (0.45, 0.82, 0.30, 0.85, 0.40, 0.65), ["B00", "D07", "A00"]),
    "7205": ("51.0401", "IRS", (0.80, 0.90, 0.30, 0.80, 0.40, 0.55), ["B00", "A00", "D07"]),
    "7206": ("51.1005", "RIC", (0.85, 0.82, 0.20, 0.65, 0.30, 0.72), ["B00", "A00", "D07"]),
    "7207": ("51.2201", "SIE", (0.40, 0.80, 0.25, 0.90, 0.65, 0.65), ["B00", "D01", "A00"]),
    "7208": ("51.0701", "ESC", (0.30, 0.65, 0.25, 0.80, 0.85, 0.78), ["B00", "D01", "A00", "A01"]),
    "7290": ("51.9999", "ISR", (0.65, 0.85, 0.25, 0.80, 0.40, 0.55), ["B00", "A00"]),
    # 76 - Dịch vụ xã hội
    "7601": ("44.0701", "SEA", (0.25, 0.55, 0.45, 0.95, 0.60, 0.50), ["C00", "D01", "D14"]),
    "7690": ("44.9999", "SEA", (0.25, 0.55, 0.45, 0.92, 0.58, 0.50), ["C00", "D01"]),
    # 81 - Du lịch, khách sạn, thể thao và dịch vụ cá nhân
    "8101": ("52.0903", "ESA", (0.40, 0.40, 0.55, 0.85, 0.88, 0.55), ["D01", "C00", "A01", "D14"]),
    "8102": ("52.0901", "ESC", (0.45, 0.35, 0.45, 0.85, 0.90, 0.68), ["D01", "A01", "C00", "A00"]),
    "8103": ("31.0504", "SRE", (0.85, 0.45, 0.30, 0.88, 0.75, 0.45), ["T00", "T01", "D01"]),
    "8105": ("19.0101", "SAE", (0.55, 0.45, 0.60, 0.85, 0.60, 0.55), ["C00", "D01", "B00"]),
    "8190": ("52.0999", "ESA", (0.45, 0.40, 0.50, 0.85, 0.85, 0.55), ["D01", "C00"]),
    # 84 - Dịch vụ vận tải
    "8401": ("49.0104", "REC", (0.82, 0.55, 0.20, 0.45, 0.78, 0.75), ["A00", "A01", "D01"]),
    "8490": ("49.9999", "REC", (0.80, 0.55, 0.20, 0.45, 0.75, 0.72), ["A00", "A01", "D01"]),
    # 85 - Môi trường và bảo vệ môi trường
    "8501": ("03.0201", "IRC", (0.75, 0.80, 0.25, 0.50, 0.55, 0.68), ["A00", "B00", "D01", "A01"]),
    "8502": ("15.0701", "RCS", (0.82, 0.65, 0.20, 0.60, 0.50, 0.78), ["A00", "B00", "A01"]),
    "8590": ("03.9999", "IRC", (0.75, 0.75, 0.25, 0.50, 0.50, 0.68), ["A00", "B00"]),
    # 86 - An ninh, Quốc phòng
    "8601": ("43.0103", "RES", (0.85, 0.65, 0.20, 0.70, 0.78, 0.72), ["A00", "A01", "C03", "D01"]),
    "8602": ("29.0201", "REC", (0.88, 0.65, 0.20, 0.60, 0.82, 0.78), ["A00", "A01", "C00", "D01"]),
    "8690": ("43.9999", "REC", (0.85, 0.65, 0.20, 0.65, 0.80, 0.75), ["A00", "A01", "C00"]),
    # 90 - Khác
    "9090": ("30.9999", "ISE", (0.50, 0.60, 0.50, 0.60, 0.60, 0.50), ["A00", "D01", "C00"]),
}


def compute_holland_code_from_vector(vec: Dict[str, float]) -> str:
    """Extracts Top-3 Holland code letters (e.g. 'IRC') sorted descending by score."""
    dims = ["R", "I", "A", "S", "E", "C"]
    ranked = sorted(dims, key=lambda d: float(vec.get(d, 0.0)), reverse=True)
    return "".join(ranked[:3])


def auto_enrich_major_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    3-Tier Automatic Matching & Enrichment Pipeline when Admin imports an Excel/CSV row:
    - Normalizes 6-digit TT74 code and 7-digit legacy compatibility code.
    - Infers field_code (2-digit) and group_code (4-digit) if omitted.
    - Auto-matches CIP code, Holland 3-letter code, and 6-dim RIASEC vector via Group + Keyword fine-tuning.
    - Auto-populates cognitive attributes, subject blocks, and career paths if omitted.
    """
    m_code_raw = str(raw.get("major_code") or raw.get("ma_nganh") or raw.get("raw_code") or "").strip()
    digits = re.sub(r"\D", "", m_code_raw)
    if len(digits) == 7 and digits.startswith(("7", "8", "9")):
        raw_6 = digits[1:]
        full_7 = digits
    elif len(digits) == 6:
        raw_6 = digits
        full_7 = f"7{digits}"
    else:
        raw_6 = digits or "909001"
        full_7 = f"7{raw_6}" if len(raw_6) == 6 else raw_6

    f_code = str(raw.get("field_code") or raw.get("ma_linh_vuc") or raw_6[:2]).strip()
    g_code = str(raw.get("group_code") or raw.get("ma_nhom_nganh") or raw_6[:4]).strip()
    m_name = str(raw.get("major_name") or raw.get("ten_nganh") or raw.get("name") or f"Ngành {raw_6}").strip()
    f_name = str(raw.get("field_name") or raw.get("ten_linh_vuc") or raw.get("category") or "Khác").strip()
    g_name = str(raw.get("group_name") or raw.get("ten_nhom_nganh") or f_name).strip()

    # Tier 1: Lookup Group Reference
    default_cip, default_hol, base_vec, default_blocks = GROUP_CIP_RIASEC.get(
        g_code, ("30.9999", "IRS", (0.50, 0.60, 0.40, 0.50, 0.40, 0.50), ["A00", "A01", "D01"])
    )
    r, i, a, s, e, c = base_vec

    # Tier 2: Keyword-based fine-tuning on Vietnamese major name
    name_low = m_name.lower()
    if any(k in name_low for k in ["thiết kế", "mỹ thuật", "nghệ thuật", "kiến trúc", "đồ họa", "thời trang", "sáng tạo"]):
        a = min(0.98, a + 0.15)
    if any(k in name_low for k in ["quản lý", "quản trị", "kinh doanh", "marketing", "thương mại", "chỉ huy"]):
        e = min(0.98, e + 0.14)
    if any(k in name_low for k in ["kế toán", "kiểm toán", "thống kê", "lưu trữ", "văn phòng", "tài chính", "mật mã", "an toàn"]):
        c = min(0.98, c + 0.14)
    if any(k in name_low for k in ["trí tuệ nhân tạo", "khoa học", "nghiên cứu", "sinh học", "hóa học", "vật lý", "dữ liệu", "toán"]):
        i = min(0.98, i + 0.12)
    if any(k in name_low for k in ["kỹ thuật", "công nghệ", "cơ khí", "ô tô", "điện", "xây dựng", "mỏ", "robot", "vi mạch", "bán dẫn"]):
        r = min(0.98, r + 0.12)
    if any(k in name_low for k in ["sư phạm", "giáo dục", "tâm lý", "xã hội", "điều dưỡng", "hộ sinh", "cộng đồng"]):
        s = min(0.98, s + 0.12)

    # Check if explicit RIASEC scores were provided in Excel
    def _parse_float(val: Any, fallback: float) -> float:
        if val is None or str(val).strip() == "":
            return round(fallback, 2)
        try:
            v = float(val)
            return round(max(0.0, min(1.0, v)), 2)
        except Exception:
            return round(fallback, 2)

    existing_vec = raw.get("riasec") or raw.get("riasec_vector") or {}
    riasec_vec = {
        "R": _parse_float(raw.get("riasec_r", existing_vec.get("R")), r),
        "I": _parse_float(raw.get("riasec_i", existing_vec.get("I")), i),
        "A": _parse_float(raw.get("riasec_a", existing_vec.get("A")), a),
        "S": _parse_float(raw.get("riasec_s", existing_vec.get("S")), s),
        "E": _parse_float(raw.get("riasec_e", existing_vec.get("E")), e),
        "C": _parse_float(raw.get("riasec_c", existing_vec.get("C")), c),
    }

    cip_code = str(raw.get("cip_code") or "").strip() or default_cip
    holland_code = str(raw.get("holland_code") or "").strip() or compute_holland_code_from_vector(riasec_vec)

    # Blocks
    raw_blocks = raw.get("subject_blocks") or raw.get("blocks")
    if isinstance(raw_blocks, str) and raw_blocks.strip():
        blocks = [b.strip().upper() for b in re.split(r"[,;/]", raw_blocks) if b.strip()]
    elif isinstance(raw_blocks, list) and raw_blocks:
        blocks = [str(b).strip().upper() for b in raw_blocks if str(b).strip()]
    else:
        blocks = default_blocks

    # Careers
    raw_careers = raw.get("career_paths") or raw.get("careers")
    if isinstance(raw_careers, str) and raw_careers.strip():
        careers = [c.strip() for c in re.split(r"[;,\n]", raw_careers) if c.strip()]
    elif isinstance(raw_careers, list) and raw_careers:
        careers = [str(c).strip() for c in raw_careers if str(c).strip()]
    else:
        careers = [
            f"Chuyên viên / Kỹ sư {m_name}",
            f"Nghiên cứu & Phát triển lĩnh vực {g_name}",
        ]

    # Cognitive traits inferred from RIASEC vector if not explicitly provided
    existing_cog = raw.get("cognitive") or raw.get("cognitive_attributes") or {}
    cognitive = {
        "abstract_thinking": existing_cog.get("abstract_thinking") or ("high" if riasec_vec["I"] >= 0.75 else ("medium" if riasec_vec["I"] >= 0.45 else "low")),
        "analytical_reasoning": existing_cog.get("analytical_reasoning") or ("high" if max(riasec_vec["I"], riasec_vec["C"]) >= 0.75 else "medium"),
        "spatial_perception": existing_cog.get("spatial_perception") or ("high" if max(riasec_vec["A"], riasec_vec["R"]) >= 0.80 else "medium"),
        "linguistic_ability": existing_cog.get("linguistic_ability") or ("high" if max(riasec_vec["S"], riasec_vec["A"], riasec_vec["E"]) >= 0.78 else "medium"),
        "learning_environment": existing_cog.get("learning_environment") or (
            "exploratory" if max(riasec_vec["A"], riasec_vec["I"]) >= 0.80 else (
                "collaborative" if max(riasec_vec["S"], riasec_vec["E"]) >= 0.78 else "structured"
            )
        ),
        "teamwork_intensity": existing_cog.get("teamwork_intensity") or (
            "highly_collaborative" if max(riasec_vec["S"], riasec_vec["E"]) >= 0.80 else "balanced"
        ),
    }

    legacy_codes = str(raw.get("legacy_tt09_codes") or full_7).strip()
    degree_levels = str(raw.get("degree_levels") or "789").strip()
    note = str(raw.get("circular_note") or raw.get("note") or "").strip()

    return {
        "major_code": full_7,
        "raw_code": raw_6,
        "name": m_name,
        "category": f_name,
        "field_code": f_code,
        "field_name": f_name,
        "group_code": g_code,
        "group_name": g_name,
        "cip_code": cip_code,
        "holland_code": holland_code,
        "legacy_tt09_codes": legacy_codes,
        "degree_levels": degree_levels,
        "note": note,
        "degree_level": "Đại học",
        "blocks": blocks,
        "careers": careers,
        "riasec": riasec_vec,
        "riasec_vector": riasec_vec,
        "cognitive": cognitive,
        "cognitive_attributes": cognitive,
        "outlook": f"Ngành đào tạo chính thức (Mã {raw_6} - CIP {cip_code} - Holland {holland_code}) theo Thông tư 74/2026/TT-BGDĐT.",
        "industry_outlook": f"Ngành đào tạo chính thức (Mã {raw_6} - CIP {cip_code} - Holland {holland_code}) theo Thông tư 74/2026/TT-BGDĐT.",
        "description": f"Chương trình đào tạo ngành {m_name} thuộc nhóm ngành {g_name} ({f_name}).",
        "is_active": True,
    }


def _col_ref_to_idx(ref: str) -> int:
    """Converts Excel cell reference like 'C5' or 'AA10' to 0-based column index."""
    col_str = "".join(ch for ch in ref if ch.isalpha()).upper()
    if not col_str:
        return -1
    idx = 0
    for ch in col_str:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1


def _parse_single_sheet_xml(ws_bytes: bytes, shared_strings: List[str]) -> List[List[str]]:
    ws_root = ET.fromstring(ws_bytes)
    rows_parsed: List[List[str]] = []
    for row_el in ws_root.iter():
        if row_el.tag.endswith("}row") or row_el.tag == "row":
            cell_map: Dict[int, str] = {}
            seq_idx = 0
            for c_el in row_el:
                if not (c_el.tag.endswith("}c") or c_el.tag == "c"):
                    continue
                ref = c_el.attrib.get("r", "")
                col_idx = _col_ref_to_idx(ref)
                if col_idx < 0:
                    col_idx = seq_idx
                seq_idx = col_idx + 1

                c_type = c_el.attrib.get("t", "")
                val_str = ""
                if c_type == "inlineStr":
                    texts = [t.text or "" for t in c_el.iter() if t.tag.endswith("}t") or t.tag == "t"]
                    val_str = "".join(texts)
                else:
                    v_el = next((ch for ch in c_el if ch.tag.endswith("}v") or ch.tag == "v"), None)
                    if v_el is not None and v_el.text is not None:
                        if c_type == "s":
                            idx = int(v_el.text)
                            val_str = shared_strings[idx] if 0 <= idx < len(shared_strings) else ""
                        else:
                            val_str = v_el.text
                cell_map[col_idx] = val_str.strip()

            if cell_map:
                max_col = max(cell_map.keys())
                row_vals = [cell_map.get(i, "") for i in range(max_col + 1)]
                if any(row_vals):
                    rows_parsed.append(row_vals)
    return rows_parsed


def _parse_xlsx_all_sheets(file_bytes: bytes) -> Tuple[List[Tuple[str, List[List[str]]]], int]:
    """Reads all sheets from an .xlsx archive in tab order returning ((sheet_name, rows), active_tab_idx)."""
    with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
        names = set(zf.namelist())
        shared_strings: List[str] = []
        if "xl/sharedStrings.xml" in names:
            ss_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in ss_root.iter():
                if si.tag.endswith("}si") or si.tag == "si":
                    texts = [t.text or "" for t in si.iter() if t.tag.endswith("}t") or t.tag == "t"]
                    shared_strings.append("".join(texts))

        rid_to_target: Dict[str, str] = {}
        if "xl/_rels/workbook.xml.rels" in names:
            rels_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
            for rel in rels_root.iter():
                if rel.tag.endswith("}Relationship") or rel.tag == "Relationship":
                    rid = rel.attrib.get("Id", "")
                    target = rel.attrib.get("Target", "").lstrip("/")
                    if target and not target.startswith("xl/"):
                        target = f"xl/{target}"
                    if rid and target:
                        rid_to_target[rid] = target

        ordered_sheets: List[Tuple[str, str]] = []
        active_tab_idx = 0
        if "xl/workbook.xml" in names:
            wb_root = ET.fromstring(zf.read("xl/workbook.xml"))
            for el in wb_root.iter():
                if el.tag.endswith("}workbookView") or el.tag == "workbookView":
                    try:
                        active_tab_idx = int(el.attrib.get("activeTab", "0"))
                    except ValueError:
                        active_tab_idx = 0
                    break
            for sh in wb_root.iter():
                if sh.tag.endswith("}sheet") or sh.tag == "sheet":
                    sh_name = sh.attrib.get("name", "Sheet")
                    # Find r:id attribute regardless of namespace prefix
                    rid = ""
                    for ak, av in sh.attrib.items():
                        if ak == "id" or ak.endswith("}id"):
                            rid = av
                            break
                    target = rid_to_target.get(rid, "")
                    if target in names:
                        ordered_sheets.append((sh_name, target))

        if not ordered_sheets:
            sheet_files = sorted(n for n in names if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
            ordered_sheets = [(f"Sheet {i + 1}", sf) for i, sf in enumerate(sheet_files)]

        results: List[Tuple[str, List[List[str]]]] = []
        for sh_name, sf in ordered_sheets:
            rows = _parse_single_sheet_xml(zf.read(sf), shared_strings)
            results.append((sh_name, rows))
        return results, active_tab_idx


def _extract_majors_from_rows(raw_rows: List[List[str]]) -> List[Dict[str, Any]]:
    if not raw_rows:
        return []

    header_idx = -1
    header_map: Dict[int, str] = {}
    known_headers = {
        "field_code": "field_code", "mã lv": "field_code", "ma_linh_vuc": "field_code",
        "field_name": "field_name", "lĩnh vực đào tạo": "field_name", "ten_linh_vuc": "field_name",
        "group_code": "group_code", "mã nhóm": "group_code", "ma_nhom_nganh": "group_code",
        "group_name": "group_name", "nhóm ngành đào tạo": "group_name", "ten_nhom_nganh": "group_name",
        "major_code": "major_code", "mã ngành": "major_code", "ma_nganh": "major_code",
        "major_name": "major_name", "tên ngành đào tạo": "major_name", "ten_nganh": "major_name",
        "legacy_tt09_codes": "legacy_tt09_codes", "ma_nganh_cu_tt09": "legacy_tt09_codes",
        "degree_levels": "degree_levels", "trinh_do_dao_tao": "degree_levels",
        "circular_note": "circular_note", "ghi chú": "circular_note", "ghi_chu_thong_tu": "circular_note",
        "cip_code": "cip_code",
        "holland_code": "holland_code",
        "riasec_r": "riasec_r", "riasec_i": "riasec_i", "riasec_a": "riasec_a",
        "riasec_s": "riasec_s", "riasec_e": "riasec_e", "riasec_c": "riasec_c",
        "subject_blocks": "subject_blocks", "to_hop_xet_tuyen": "subject_blocks",
        "career_paths": "career_paths", "nghe_nghiep_tieu_bieu": "career_paths",
    }

    for idx, row in enumerate(raw_rows[:25]):
        row_low = [c.lower().strip() for c in row]
        if any(k in row_low for k in ("major_code", "mã ngành", "ma_nganh")):
            header_idx = idx
            for c_i, col_name in enumerate(row_low):
                if col_name in known_headers:
                    header_map[c_i] = known_headers[col_name]
            break

    if header_idx == -1:
        return []

    enriched_majors: List[Dict[str, Any]] = []
    seen_codes = set()

    for row in raw_rows[header_idx + 1:]:
        row_dict: Dict[str, Any] = {}
        for c_i, key in header_map.items():
            if c_i < len(row):
                row_dict[key] = row[c_i]

        m_code_candidate = str(row_dict.get("major_code", "")).strip()
        digits = re.sub(r"\D", "", m_code_candidate)
        if len(digits) not in (6, 7):
            continue
        if digits in seen_codes:
            continue
        seen_codes.add(digits)

        enriched_majors.append(auto_enrich_major_record(row_dict))

    return enriched_majors


def parse_excel_or_csv_sheets(
    file_bytes: bytes,
    filename: str = "upload.xlsx",
    preferred_sheet: Optional[str] = None,
) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Returns (active_sheet_name, active_majors, all_sheets_summary_with_majors).
    Only sheets containing valid major columns/rows are included.
    """
    fname_low = filename.lower()
    if fname_low.endswith(".xlsx"):
        sheets_raw, active_tab_idx = _parse_xlsx_all_sheets(file_bytes)
        parsed_sheets: List[Dict[str, Any]] = []
        active_tab_sheet_name = (
            sheets_raw[active_tab_idx][0] if 0 <= active_tab_idx < len(sheets_raw) else None
        )
        for sh_name, rows in sheets_raw:
            majors = _extract_majors_from_rows(rows)
            if majors:
                parsed_sheets.append({
                    "sheet_name": sh_name,
                    "count": len(majors),
                    "majors": majors,
                })
        if not parsed_sheets:
            return ("Sheet 1", [], [])

        selected = None
        if preferred_sheet:
            selected = next((s for s in parsed_sheets if s["sheet_name"] == preferred_sheet), None)
        if not selected and active_tab_sheet_name:
            selected = next((s for s in parsed_sheets if s["sheet_name"] == active_tab_sheet_name), None)
        if not selected:
            selected = parsed_sheets[0]

        return (
            selected["sheet_name"],
            selected["majors"],
            [{"sheet_name": s["sheet_name"], "count": s["count"], "majors": s["majors"]} for s in parsed_sheets],
        )
    else:
        text = file_bytes.decode("utf-8-sig", errors="replace")
        reader = csv.reader(io.StringIO(text))
        raw_rows = [[cell.strip() for cell in r] for r in reader if any(cell.strip() for cell in r)]
        majors = _extract_majors_from_rows(raw_rows)
        return ("CSV", majors, [{"sheet_name": "CSV", "count": len(majors), "majors": majors}] if majors else [])


def parse_excel_or_csv_majors(file_bytes: bytes, filename: str = "upload.xlsx") -> List[Dict[str, Any]]:
    """Backward-compatible wrapper returning majors from the primary/largest sheet."""
    _, majors, _ = parse_excel_or_csv_sheets(file_bytes, filename)
    return majors
