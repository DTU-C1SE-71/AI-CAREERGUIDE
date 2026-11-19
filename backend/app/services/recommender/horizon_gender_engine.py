"""
backend/app/services/recommender/horizon_gender_engine.py

HA-GAE v3.1 (Horizon-Adaptive & Gender-Aware Ergonomic Career Recommendation Engine)
Designed for AI_CAREERGUIDE.
Fully compliant with:
- Circular 74/2026/TT-BGDĐT (435 National Major Taxonomy, 23 Broad Disciplines)
- Law on Gender Equality No. 73/2006/QH11 & Labor Code No. 45/2019/QH14
- Circular 10/2020/TT-BLĐTBXH on special occupational safety and hygiene conditions
"""

import math
import re
from typing import Dict, Any, List, Optional, Tuple, Set
from app.schemas.recommender import MajorRecommendationItem


# =========================================================================
# 1. HỆ SỐ THỜI GIAN VÀ CẤU HÌNH PHỄU THEO KHỐI LỚP (SIMPLEX HARMONIZATION)
# =========================================================================
HORIZON_CONFIG: Dict[str, Dict[str, Any]] = {
    "Lớp 10": {
        "tau": 1.00,
        "label": "Giai đoạn Định hướng Sớm & Tích lũy (Lớp 10)",
        "w_riasec": 0.500,
        "w_academic": 0.250,
        "w_preference": 0.250,
        "delta_reach_max": 3.5,
        "quota_reach": 0.40,
        "quota_target": 0.40,
        "quota_safety": 0.20,
    },
    "Lớp 11": {
        "tau": 0.65,
        "label": "Giai đoạn Tăng tốc & Thu hẹp Trọng tâm (Lớp 11)",
        "w_riasec": 0.465,
        "w_academic": 0.320,
        "w_preference": 0.215,
        "delta_reach_max": 2.6,
        "quota_reach": 0.30,
        "quota_target": 0.50,
        "quota_safety": 0.20,
    },
    "Lớp 12": {
        "tau": 0.25,
        "label": "Giai đoạn Nước rút Thực chiến (Lớp 12)",
        "w_riasec": 0.425,
        "w_academic": 0.400,
        "w_preference": 0.175,
        "delta_reach_max": 1.2,
        "quota_reach": 0.15,
        "quota_target": 0.65,
        "quota_safety": 0.20,
    },
    "Đã tốt nghiệp cấp 3": {
        "tau": 0.15,
        "label": "Thí sinh Tự do & Hướng nghiệp Thực tế",
        "w_riasec": 0.415,
        "w_academic": 0.420,
        "w_preference": 0.165,
        "delta_reach_max": 1.0,
        "quota_reach": 0.10,
        "quota_target": 0.60,
        "quota_safety": 0.30,
    },
}

DEFAULT_HORIZON = HORIZON_CONFIG["Lớp 12"]


# =========================================================================
# 2. MA TRẬN CÔNG THÁI HỌC 4D & QUY CHUẨN LAO ĐỘNG PHÁP LÝ (Circular 74 & TT 10/2020)
# Vector 4D: (phys_intensity, hazard_exposure, mobility_intensity, stem_gender_gap)
# =========================================================================
BROAD_DISCIPLINE_ERGONOMICS: Dict[str, Dict[str, Any]] = {
    "714": {"name": "Khoa học giáo dục và đào tạo giáo viên", "phys": 0.3, "haz": 0.1, "mob": 0.1, "gap": -0.75},
    "722": {"name": "Nhân văn", "phys": 0.1, "haz": 0.1, "mob": 0.2, "gap": -0.30},
    "731": {"name": "Khoa học xã hội và hành vi", "phys": 0.1, "haz": 0.1, "mob": 0.2, "gap": -0.20},
    "734": {"name": "Kinh doanh và quản lý", "phys": 0.1, "haz": 0.1, "mob": 0.3, "gap": -0.10},
    "738": {"name": "Pháp luật", "phys": 0.1, "haz": 0.1, "mob": 0.2, "gap": 0.00},
    "742": {"name": "Khoa học sự sống", "phys": 0.3, "haz": 0.2, "mob": 0.2, "gap": 0.20},
    "744": {"name": "Khoa học tự nhiên", "phys": 0.3, "haz": 0.3, "mob": 0.3, "gap": 0.35},
    "746": {"name": "Toán và thống kê", "phys": 0.1, "haz": 0.1, "mob": 0.2, "gap": 0.40},
    "748": {"name": "Máy tính và công nghệ thông tin", "phys": 0.1, "haz": 0.1, "mob": 0.2, "gap": 0.70},
    "751": {"name": "Công nghệ kỹ thuật", "phys": 0.5, "haz": 0.4, "mob": 0.4, "gap": 0.65},
    "752": {"name": "Kỹ thuật", "phys": 0.6, "haz": 0.5, "mob": 0.5, "gap": 0.70},
    "754": {"name": "Sản xuất và chế biến", "phys": 0.5, "haz": 0.4, "mob": 0.3, "gap": 0.30},
    "758": {"name": "Kiến trúc và xây dựng", "phys": 0.6, "haz": 0.4, "mob": 0.5, "gap": 0.55},
    "762": {"name": "Nông, lâm nghiệp và thủy sản", "phys": 0.6, "haz": 0.4, "mob": 0.4, "gap": 0.30},
    "764": {"name": "Thú y", "phys": 0.5, "haz": 0.3, "mob": 0.3, "gap": 0.10},
    "772": {"name": "Sức khỏe", "phys": 0.5, "haz": 0.3, "mob": 0.4, "gap": -0.60},
    "776": {"name": "Dịch vụ xã hội", "phys": 0.3, "haz": 0.1, "mob": 0.3, "gap": -0.50},
    "781": {"name": "Du lịch, khách sạn, thể thao và dịch vụ cá nhân", "phys": 0.4, "haz": 0.1, "mob": 0.5, "gap": -0.20},
    "784": {"name": "Dịch vụ vận tải", "phys": 0.7, "haz": 0.5, "mob": 0.8, "gap": 0.60},
    "785": {"name": "Môi trường và bảo vệ môi trường", "phys": 0.4, "haz": 0.3, "mob": 0.4, "gap": 0.20},
}

STATUTORY_HEAVY_HAZARDS: Dict[str, Dict[str, Any]] = {
    "7520601": {
        "title": "Kỹ thuật Mỏ",
        "universal_advisory": "Ngành có điều kiện hầm lò đặc thù theo Thông tư 10/2020/TT-BLĐTBXH yêu cầu quy chuẩn an toàn lao động nghiêm ngặt.",
        "female_pathway": "Khuyến nghị ưu tiên chuyên sâu về Thiết kế mỏ, Trắc địa mỏ, Công nghệ mỏ sạch và Giám định môi trường mỏ để phát huy tối đa tư duy phân tích mà không phụ thuộc thể trạng.",
    },
    "7840101": {
        "title": "Điều khiển tàu biển / Hàng hải",
        "universal_advisory": "Nghề nghiệp đòi hỏi thể lực bền bỉ và di chuyển viễn dương dài ngày theo quy chuẩn an toàn hàng hải.",
        "female_pathway": "Khuyến nghị định hướng chuyên sâu về Quản trị logistics cảng biển, Điều độ hoa tiêu luồng hàng hải và Giám sát vận hành đội tàu viễn thông bờ.",
    },
    "7520301": {
        "title": "Kỹ thuật Hóa học / Lọc hóa dầu",
        "universal_advisory": "Môi trường công xưởng hóa chất có quy chuẩn nghiêm ngặt về hơi khí độc và bảo hộ lao động theo Thông tư 10/2020.",
        "female_pathway": "Khuyến nghị hướng tới các vị trí Nghiên cứu phát triển vật liệu mới (R&D), Quản lý chất lượng (QA/QC) và Phân tích kiểm nghiệm phòng thí nghiệm.",
    },
}

STEM_BROAD_CATEGORIES = {"Máy tính và công nghệ thông tin", "Kỹ thuật", "Công nghệ kỹ thuật", "Khoa học tự nhiên", "Toán và thống kê"}
STEM_KEYWORDS = ("trí tuệ nhân tạo", "khoa học máy tính", "phần mềm", "vi mạch", "bán dẫn", "robot", "tự động hóa", "dữ liệu", "hệ thống thông tin")

CARE_BROAD_CATEGORIES = {"Khoa học giáo dục và đào tạo giáo viên", "Sức khỏe", "Dịch vụ xã hội"}
CARE_KEYWORDS = ("mầm non", "tiểu học", "điều dưỡng", "y tế", "hộ sinh", "dược", "công tác xã hội")


def get_grade_horizon_config(grade_level: Optional[str]) -> Dict[str, Any]:
    """Lấy cấu hình thời gian và hạn ngạch thích ứng từ khối lớp của học sinh."""
    if not grade_level:
        return DEFAULT_HORIZON
    norm_grade = str(grade_level).strip()
    if "10" in norm_grade:
        return HORIZON_CONFIG["Lớp 10"]
    if "11" in norm_grade:
        return HORIZON_CONFIG["Lớp 11"]
    if "12" in norm_grade:
        return HORIZON_CONFIG["Lớp 12"]
    if "tốt nghiệp" in norm_grade.lower() or "tot nghiep" in norm_grade.lower():
        return HORIZON_CONFIG["Đã tốt nghiệp cấp 3"]
    return HORIZON_CONFIG.get(norm_grade, DEFAULT_HORIZON)


def compute_gender_ergonomic_adjustment(
    gender: Optional[str],
    major_code: str,
    major_name: str,
    major_category: str,
    score_riasec: float,
    score_academic: float,
    riasec_dict: Optional[Dict[str, float]] = None,
    grade_level: Optional[str] = None,
) -> Tuple[float, Optional[str], Optional[str], Dict[str, Any]]:
    """
    Tính toán hệ số công thái học kết hợp ma trận 4D BROAD_DISCIPLINE_ERGONOMICS,
    độ tương thích thể chất S_ergo_match = 1.0 - 0.20 * |e_phys - R_user|,
    và quy chuẩn an toàn lao động Thông tư 10/2020.
    BẢO TỒN NGUYÊN LÝ ZERO-PENALTY: delta_boost >= 0.0.
    Trả về: (delta_boost, advisory_note, nudge_badge, ergo_debug_dict)
    """
    g = str(gender or "").strip()
    delta_boost = 0.0
    advisory_note = None
    nudge_badge = None

    code_prefix = major_code[:3] if len(major_code) >= 3 else ""
    norm_name = major_name.lower()
    norm_cat = major_category.strip()

    ergo_profile = BROAD_DISCIPLINE_ERGONOMICS.get(code_prefix, {"phys": 0.3, "haz": 0.2, "mob": 0.3, "gap": 0.0})
    e_phys = float(ergo_profile.get("phys", 0.3))
    e_haz = float(ergo_profile.get("haz", 0.2))
    e_mob = float(ergo_profile.get("mob", 0.3))
    stem_gender_gap = float(ergo_profile.get("gap", 0.0))

    # 1. TÍNH TOÁN ĐỘ TƯƠNG THÍCH THỂ CHẤT - SỞ THÍCH THỰC TẾ (4D ERGONOMIC RUNTIME)
    r_user = 0.5
    if riasec_dict:
        r_user = float(riasec_dict.get("R", 0.5))
    s_ergo_match = round(1.0 - 0.20 * abs(e_phys - r_user), 4)

    # Vi điều chỉnh công thái học tích cực (Zero-Penalty Invariant)
    delta_ergo = round(max(0.0, 0.01 * (s_ergo_match - 0.70)), 4)
    delta_boost += delta_ergo

    # 2. Cảnh báo an toàn lao động Thông tư 10/2020 hoặc môi trường nặng nhọc/phơi nhiễm
    if major_code in STATUTORY_HEAVY_HAZARDS:
        haz_info = STATUTORY_HEAVY_HAZARDS[major_code]
        if g == "Nữ":
            advisory_note = f"{haz_info['universal_advisory']} {haz_info['female_pathway']}"
        else:
            advisory_note = haz_info["universal_advisory"]
    elif e_haz >= 0.4 or e_mob >= 0.5:
        advisory_note = f"Môi trường nghề nghiệp có cường độ di chuyển ({e_mob:.1f}) hoặc phơi nhiễm hiện trường ({e_haz:.1f}), yêu cầu thể lực và tính chủ động cao."

    # 3. Tính toán Nudge công thái học & Bình đẳng cơ hội
    delta_affirmative = 0.0
    if g == "Nữ":
        if (
            stem_gender_gap > 0.2
            or norm_cat in STEM_BROAD_CATEGORIES
            or code_prefix in ("748", "752", "751", "746")
            or any(k in norm_name for k in STEM_KEYWORDS)
        ):
            if score_riasec >= 0.60 or score_academic >= 0.60:
                affinity = 0.70 * score_riasec + 0.30 * score_academic
                delta_affirmative = round(min(0.04, 0.04 * affinity), 4)
                nudge_badge = "Khuyến khích Nữ sinh STEM & Công nghệ"
    elif g == "Nam":
        if (
            stem_gender_gap < -0.2
            or norm_cat in CARE_BROAD_CATEGORIES
            or code_prefix in ("714", "772", "776")
            or any(k in norm_name for k in CARE_KEYWORDS)
        ):
            if score_riasec >= 0.60:
                affinity = score_riasec
                delta_affirmative = round(min(0.04, 0.04 * affinity), 4)
                nudge_badge = "Khuyến khích Nam sinh Giáo dục & Y tế"
    elif g == "Khác":
        delta_affirmative = 0.02
        nudge_badge = "Môi trường Đa dạng & Cởi mở"

    delta_boost += delta_affirmative

    # 4. Ưu tiên Thực hành cho Thí sinh Đã tốt nghiệp cấp 3
    is_applied_track = (
        code_prefix == "751"
        or "thực hành" in norm_name
        or "ứng dụng" in norm_name
        or "công nghệ kỹ thuật" in norm_name
    )
    if grade_level == "Đã tốt nghiệp cấp 3" and is_applied_track:
        delta_boost += 0.03
        if not nudge_badge:
            nudge_badge = "Chương trình Kỹ thuật Thực hành Ưu tiên"

    delta_boost = round(min(0.05, max(0.0, delta_boost)), 4)
    ergo_debug = {
        "e_phys": e_phys,
        "e_haz": e_haz,
        "e_mob": e_mob,
        "r_user": r_user,
        "s_ergo_match": s_ergo_match,
        "delta_ergo": delta_ergo,
        "delta_affirmative": delta_affirmative,
    }
    return delta_boost, advisory_note, nudge_badge, ergo_debug


def _replace_item(
    assembled: List[MajorRecommendationItem],
    target_idx: int,
    new_cand: MajorRecommendationItem,
    seen_codes: Set[str],
    category_counts: Dict[str, int],
) -> None:
    """Hàm hoán đổi nguyên tử đồng bộ hai chiều seen_codes và category_counts."""
    old_item = assembled[target_idx]
    old_cat = old_item.category or "Khác"
    new_cat = new_cand.category or "Khác"

    seen_codes.remove(old_item.major_code)
    seen_codes.add(new_cand.major_code)

    category_counts[old_cat] = max(0, category_counts.get(old_cat, 1) - 1)
    category_counts[new_cat] = category_counts.get(new_cat, 0) + 1

    assembled[target_idx] = new_cand


def apply_horizon_gender_reranking(
    scored_items: List[MajorRecommendationItem],
    grade_level: Optional[str] = None,
    gender: Optional[str] = None,
    top_k: int = 10,
    has_academic_scores: bool = True,
    target_trending_top5: int = 1,
    target_trending_top10: int = 2,
    student_riasec_dict: Optional[Dict[str, float]] = None,
) -> List[MajorRecommendationItem]:
    """
    Bộ điều phối Tái xếp hạng HA-GAE v3.1:
    - Decoupled Deficit Active Gatekeeper: Cách ly vĩnh viễn mọi ngành thiếu hụt > delta_reach_max.
    - Graceful Fallback for No-Grade Users: Đầy đủ Trending Quota và Affirmative Nudge cho học sinh sớm.
    - Score-Ordered Quota Assembly: Loại bỏ hoàn toàn hiện tượng Ranking Inversion cho Lớp 12.
    - Atomic Replacement: Giữ vững trần nhóm ngành 40% và bảo vệ quota an toàn.
    - Dedicated Applied Practical Track Quota cho Thí sinh Đã tốt nghiệp.
    """
    if not scored_items or top_k <= 0:
        return []

    cfg = get_grade_horizon_config(grade_level)
    q_reach = cfg["quota_reach"]
    q_target = cfg["quota_target"]
    q_safety = cfg["quota_safety"]
    delta_reach_max = cfg["delta_reach_max"]
    tau = cfg["tau"]

    # 1. Cập nhật boost công thái học & Phân tầng Decoupled Deficit
    pool_reach: List[MajorRecommendationItem] = []
    pool_target: List[MajorRecommendationItem] = []
    pool_safety: List[MajorRecommendationItem] = []
    pool_unrealistic: List[MajorRecommendationItem] = []
    pool_other: List[MajorRecommendationItem] = []

    for item in scored_items:
        is_strong_veto = (
            (item.score_breakdown or {}).get("subfacet_gate", {}).get("status") == "STRONG_VETO"
        )
        if is_strong_veto:
            # STRICT VETO ISOLATION: Học sinh chọn "Rất không thích" (1/5) hoạt động đặc thù của ngành
            # -> không áp dụng gender nudge, cách ly khỏi các vị trí đầu bảng & quota đề xuất.
            pool_unrealistic.append(item)
            continue

        d_boost, adv_note, n_badge, ergo_debug = compute_gender_ergonomic_adjustment(
            gender=gender,
            major_code=item.major_code,
            major_name=item.major_name,
            major_category=item.category or "Khác",
            score_riasec=item.score_riasec,
            score_academic=item.score_academic,
            riasec_dict=student_riasec_dict,
            grade_level=grade_level,
        )
        if d_boost > 0.0:
            item.overall_score = round(min(1.0, item.overall_score + d_boost), 4)
            if item.score_breakdown is not None:
                item.score_breakdown["gender_ergonomic_boost"] = d_boost
                item.score_breakdown.update(ergo_debug)
                if n_badge:
                    item.score_breakdown["nudge_badge"] = n_badge
            if n_badge:
                item.nudge_badge = n_badge

        if adv_note:
            item.advisory_note = adv_note
            if item.score_breakdown is not None:
                item.score_breakdown["advisory_note"] = adv_note
            if adv_note not in item.top_supporting_factors:
                item.top_supporting_factors.append(adv_note)

        gap = item.score_gap
        tier = (item.feasibility_tier or "").upper()

        # DECOUPLED ACTIVE GATEKEEPER: Chặn cứng dựa trên độ thiếu hụt toán học, không phụ thuộc tier
        if gap is not None:
            if gap < 0.0:
                deficit = abs(gap)
                if deficit > delta_reach_max:
                    # STRICT ISOLATION: Cách ly khỏi các vị trí khuyến nghị đầu bảng
                    item.feasibility_tier = "REACH"
                    item.feasibility_label = f"Nguy cơ cao (Thiếu ~{deficit:.1f}đ)".replace(".", ",")
                    item.admission_tactic = "Nguy cơ cao"
                    pool_unrealistic.append(item)
                else:
                    item.feasibility_tier = "REACH"
                    if tau >= 0.65:
                        item.feasibility_label = f"Mục tiêu Bứt phá dài hạn (Thiếu ~{deficit:.1f}đ)".replace(".", ",")
                    else:
                        item.feasibility_label = f"Thử thách thực chiến (Thiếu ~{deficit:.1f}đ)".replace(".", ",")
                    item.admission_tactic = "NV1-2 (Bứt phá)"
                    pool_reach.append(item)
            elif gap >= 2.0:
                item.feasibility_tier = "TARGET"
                item.feasibility_label = f"An toàn cao (Vượt chuẩn +{gap:.1f}đ)".replace(".", ",")
                item.admission_tactic = "NV6+ (Dự phòng)"
                pool_safety.append(item)
            else:
                item.feasibility_tier = "TARGET"
                item.feasibility_label = f"Vừa sức an toàn (+{gap:.1f}đ)".replace(".", ",")
                item.admission_tactic = "NV3-5 (Vừa sức)"
                pool_target.append(item)
        else:
            if tier in ("SAFE", "SAFETY"):
                item.admission_tactic = "NV6+ (Dự phòng)"
                pool_safety.append(item)
            elif tier in ("TARGET", "MATCH"):
                item.admission_tactic = "NV3-5 (Vừa sức)"
                pool_target.append(item)
            elif tier == "REACH":
                item.admission_tactic = "NV1-2 (Bứt phá)"
                pool_reach.append(item)
            else:
                item.admission_tactic = "Định hướng sở thích"
                pool_other.append(item)

    # Sắp xếp từng pool
    pool_reach.sort(key=lambda x: (x.overall_score, x.score_riasec), reverse=True)
    pool_target.sort(key=lambda x: (x.overall_score, x.score_riasec), reverse=True)
    pool_safety.sort(key=lambda x: (x.overall_score, x.score_riasec), reverse=True)
    pool_other.sort(key=lambda x: (x.overall_score, x.score_riasec), reverse=True)

    unrealistic_codes = {it.major_code for it in pool_unrealistic}

    # 2. Xử lý Quota & Graceful Fallback
    target_k_reach = int(round(top_k * q_reach))
    target_k_target = int(round(top_k * q_target))
    target_k_safety = top_k - target_k_reach - target_k_target

    has_academic_pools = bool(pool_target or pool_safety or pool_reach)
    candidates_ordered: List[MajorRecommendationItem] = []

    if has_academic_pools:
        selected_reach = pool_reach[:target_k_reach]
        selected_target = pool_target[:target_k_target]
        selected_safety = pool_safety[:target_k_safety]

        # SCORE-ORDERED QUOTA ASSEMBLY:
        # Nếu là Lớp 10/11 (tau >= 0.65), học sinh có nhiều thời gian ôn thi -> có thể đề xuất ngành khó hơn (REACH bứt phá) ngay trong Top 5.
        # Nếu là Lớp 12 / Nước rút thực chiến (tau < 0.65), ưu tiên tuyệt đối ngành TARGET an toàn trước REACH để bảo đảm tỷ lệ trúng tuyển.
        if tau >= 0.65:
            candidates_ordered = sorted(
                selected_target + selected_reach + selected_safety,
                key=lambda x: (x.overall_score, x.score_riasec),
                reverse=True,
            )
        else:
            candidates_ordered = sorted(
                selected_target + selected_reach + selected_safety,
                key=lambda x: (
                    1 if x.feasibility_tier == "TARGET" else 0,
                    x.overall_score,
                    x.score_riasec,
                ),
                reverse=True,
            )
        fallback_pool = (
            pool_target[target_k_target:]
            + pool_safety[target_k_safety:]
            + pool_reach[target_k_reach:]
            + pool_other
        )
    else:
        # Graceful fallback: Khi học sinh chưa có điểm thi, toàn bộ pool_other được kích hoạt
        candidates_ordered = list(pool_other)
        fallback_pool = []

    # 3. Lắp ráp có Ràng buộc Đa dạng Khối ngành (Constrained Diversity Gate: Max 40%)
    max_per_category_top5 = 2   # 40% của 5
    max_per_category_top10 = 4  # 40% của 10

    assembled: List[MajorRecommendationItem] = []
    seen_codes: Set[str] = set()
    category_counts: Dict[str, int] = {}

    def _can_add_item(item: MajorRecommendationItem, current_len: int) -> bool:
        if item.major_code in unrealistic_codes:
            return False
        if item.feasibility_tier == "REACH":
            gap_def = abs(item.score_gap) if item.score_gap is not None else 0.0
            if gap_def > delta_reach_max:
                return False
            # Giai đoạn nước rút (tau < 0.65): giữ Top 5 hoàn toàn là TARGET vừa sức nếu có đủ TARGET
            if tau < 0.65 and current_len < 5 and len(pool_target) >= 5:
                return False

        cat = item.category or "Khác"
        current_cat_count = category_counts.get(cat, 0)
        if current_len < 5 and current_cat_count >= max_per_category_top5:
            return False
        if current_len < 10 and current_cat_count >= max_per_category_top10:
            return False
        return True

    for cand in candidates_ordered + fallback_pool:
        if len(assembled) >= top_k:
            break
        if cand.major_code not in seen_codes and _can_add_item(cand, len(assembled)):
            assembled.append(cand)
            seen_codes.add(cand.major_code)
            cat = cand.category or "Khác"
            category_counts[cat] = category_counts.get(cat, 0) + 1

    # Vét bổ sung nếu chưa đủ top_k nhưng tuyệt đối không lọt unrealistic
    if len(assembled) < top_k:
        for cand in fallback_pool + pool_other:
            if len(assembled) >= top_k:
                break
            if cand.major_code not in seen_codes and cand.major_code not in unrealistic_codes:
                if cand.feasibility_tier == "REACH":
                    gap_def = abs(cand.score_gap) if cand.score_gap is not None else 0.0
                    if gap_def > delta_reach_max:
                        continue
                assembled.append(cand)
                seen_codes.add(cand.major_code)
                cat = cand.category or "Khác"
                category_counts[cat] = category_counts.get(cat, 0) + 1

    # Nếu người dùng yêu cầu top_k lớn (ví dụ đánh giá toàn bộ 435 ngành), bổ sung các ngành nguy cơ cao ở cuối danh sách
    if len(assembled) < top_k:
        for cand in pool_unrealistic:
            if len(assembled) >= top_k:
                break
            if cand.major_code not in seen_codes:
                assembled.append(cand)
                seen_codes.add(cand.major_code)
                cat = cand.category or "Khác"
                category_counts[cat] = category_counts.get(cat, 0) + 1

    # 4. BẢO ĐẢM HẠN NGẠCH NGÀNH XU HƯỚNG (Market Trending Quotas)
    all_searchable_pool = pool_target + pool_safety + pool_reach + pool_other

    def _find_best_trending(exclude: Set[str], require_target: bool = False) -> Optional[MajorRecommendationItem]:
        best_cand = None
        best_score = -1.0
        for c in all_searchable_pool:
            if not getattr(c, "is_trending", False) or c.major_code in exclude or c.major_code in unrealistic_codes:
                continue
            if require_target and c.feasibility_tier != "TARGET":
                continue
            if c.overall_score > best_score:
                best_score = c.overall_score
                best_cand = c
        return best_cand

    if top_k >= 5 and target_trending_top5 > 0 and assembled:
        current_trending_top5 = sum(1 for it in assembled[:5] if getattr(it, "is_trending", False))
        if current_trending_top5 < target_trending_top5:
            trend_cand = _find_best_trending(seen_codes, require_target=(tau < 0.65 and len(pool_target) >= 5))
            if trend_cand is not None:
                cand_cat = trend_cand.category or "Khác"
                # Tìm vị trí thích hợp trong top 5 để hoán đổi
                replaceable_idx = None
                for idx in range(min(5, len(assembled)) - 1, -1, -1):
                    item_at = assembled[idx]
                    old_cat = item_at.category or "Khác"
                    # Không phá hủy ngành an toàn nếu đang ở mức tối thiểu
                    if item_at.feasibility_tier == "SAFETY" and target_k_safety > 0:
                        safety_in_assembled = sum(1 for x in assembled if x.feasibility_tier == "SAFETY")
                        if safety_in_assembled <= target_k_safety:
                            continue
                    # Kiểm tra trần đa dạng sau khi thay
                    projected_count = category_counts.get(cand_cat, 0) + (1 if cand_cat != old_cat else 0)
                    if projected_count <= max_per_category_top5:
                        replaceable_idx = idx
                        break

                if replaceable_idx is not None:
                    _replace_item(assembled, replaceable_idx, trend_cand, seen_codes, category_counts)

    # 5. RÀO CHẮN ĐẠO ĐỨC BÌNH ĐẲNG CƠ HỘI (Affirmative Nudge with Atomic Replacement)
    if student_riasec_dict and assembled:
        i_score = float(student_riasec_dict.get("I", 0.5))
        r_score = float(student_riasec_dict.get("R", 0.5))
        s_score = float(student_riasec_dict.get("S", 0.5))

        if gender == "Nữ" and (i_score >= 0.60 or r_score >= 0.60):
            stem_in_top = sum(
                1 for it in assembled
                if it.major_code[:3] in ("748", "752", "751", "746") or (it.category or "") in STEM_BROAD_CATEGORIES
            )
            if stem_in_top == 0:
                for cand in all_searchable_pool:
                    if (
                        cand.major_code[:3] in ("748", "752", "751", "746")
                        or (cand.category or "") in STEM_BROAD_CATEGORIES
                    ) and cand.major_code not in seen_codes and cand.major_code not in unrealistic_codes:
                        cand_cat = cand.category or "Khác"
                        rep_idx = None
                        for idx in range(len(assembled) - 1, -1, -1):
                            item_at = assembled[idx]
                            old_cat = item_at.category or "Khác"
                            if getattr(item_at, "is_trending", False):
                                continue
                            if item_at.feasibility_tier == "SAFETY" and target_k_safety > 0:
                                safety_in_assembled = sum(1 for x in assembled if x.feasibility_tier == "SAFETY")
                                if safety_in_assembled <= target_k_safety:
                                    continue
                            cap_to_check = max_per_category_top5 if idx < 5 else max_per_category_top10
                            projected_count = category_counts.get(cand_cat, 0) + (1 if cand_cat != old_cat else 0)
                            if projected_count <= cap_to_check:
                                rep_idx = idx
                                break

                        if rep_idx is not None:
                            _replace_item(assembled, rep_idx, cand, seen_codes, category_counts)
                            break

        elif gender == "Nam" and s_score >= 0.60:
            care_in_top = sum(
                1 for it in assembled
                if it.major_code[:3] in ("714", "772", "776") or (it.category or "") in CARE_BROAD_CATEGORIES
            )
            if care_in_top == 0:
                for cand in all_searchable_pool:
                    if (
                        cand.major_code[:3] in ("714", "772", "776")
                        or (cand.category or "") in CARE_BROAD_CATEGORIES
                    ) and cand.major_code not in seen_codes and cand.major_code not in unrealistic_codes:
                        cand_cat = cand.category or "Khác"
                        rep_idx = None
                        for idx in range(len(assembled) - 1, -1, -1):
                            item_at = assembled[idx]
                            old_cat = item_at.category or "Khác"
                            if getattr(item_at, "is_trending", False):
                                continue
                            if item_at.feasibility_tier == "SAFETY" and target_k_safety > 0:
                                safety_in_assembled = sum(1 for x in assembled if x.feasibility_tier == "SAFETY")
                                if safety_in_assembled <= target_k_safety:
                                    continue
                            cap_to_check = max_per_category_top5 if idx < 5 else max_per_category_top10
                            projected_count = category_counts.get(cand_cat, 0) + (1 if cand_cat != old_cat else 0)
                            if projected_count <= cap_to_check:
                                rep_idx = idx
                                break

                        if rep_idx is not None:
                            _replace_item(assembled, rep_idx, cand, seen_codes, category_counts)
                            break

    # 6. Gán thứ hạng Rank 1-based
    for rank_idx, item in enumerate(assembled[:top_k], start=1):
        item.rank = rank_idx

    return assembled[:top_k]


def build_horizon_gender_xai_explanation(
    major_name: str,
    major_code: str,
    category: str,
    score_riasec: float,
    score_academic: float,
    score_pref: float,
    feasibility_tier: str,
    grade_level: Optional[str] = None,
    gender: Optional[str] = None,
    best_matching_block: Optional[str] = None,
    score_gap: Optional[float] = None,
) -> str:
    """
    Sinh giải thích XAI ĐÚNG 3 CÂU thích ứng theo Khối lớp và Môi trường Giới tính.
    Sử dụng chuẩn tiếng Việt rõ ràng, giải thích cụ thể tổ hợp môn kèm tên môn học chi tiết.
    """
    from app.services.recommender.engine import format_block_with_subjects

    cfg = get_grade_horizon_config(grade_level)
    tau = cfg["tau"]
    g = str(gender or "").strip()

    # CÂU 1: Sở thích & Tư duy
    c1 = f"Ngành {major_name} rất phù hợp với thiên hướng nghề nghiệp (Holland {score_riasec*100:.0f}%) và phong cách tư duy của bạn."

    # CÂU 2: Tuyển sinh & Môi trường thích ứng / Pháp lý an toàn lao động
    tier = (feasibility_tier or "UNKNOWN").upper()
    block_fmt = format_block_with_subjects(best_matching_block) if best_matching_block else ""
    block_str = f" theo {block_fmt}" if block_fmt else ""
    gap_val = abs(score_gap) if score_gap is not None else 0.0
    gap_str = f"~{gap_val:.1f}đ"

    if tier in ("TARGET", "MATCH"):
        c2_adm = f"Khả năng trúng tuyển{block_str} đang ở mức vừa sức rất thuận lợi"
    elif tier in ("SAFE", "SAFETY"):
        c2_adm = f"Khả năng trúng tuyển{block_str} ở mức an toàn cao vượt ngưỡng điểm chuẩn tham chiếu"
    elif tier == "REACH":
        if tau >= 0.65:
            c2_adm = f"Mức điểm hiện tại cần bứt phá thêm {gap_str}, nhưng với thời gian dài của {cfg['label']} đây là mục tiêu rất xứng đáng để phấn đấu"
        else:
            c2_adm = f"Ngành có mức cạnh tranh cao (thiếu {gap_str}), đòi hỏi chiến thuật tập trung cao độ trong giai đoạn nước rút"
    else:
        c2_adm = "Dữ liệu tuyển sinh đang được đồng bộ theo tổ hợp thế mạnh"

    code_prefix = major_code[:3] if len(major_code) >= 3 else ""
    norm_cat = category.strip()
    norm_name = major_name.lower()

    is_stem = norm_cat in STEM_BROAD_CATEGORIES or code_prefix in ("748", "752", "751") or any(k in norm_name for k in STEM_KEYWORDS)
    is_care = norm_cat in CARE_BROAD_CATEGORIES or code_prefix in ("714", "772") or any(k in norm_name for k in CARE_KEYWORDS)

    if major_code in STATUTORY_HEAVY_HAZARDS:
        haz_info = STATUTORY_HEAVY_HAZARDS[major_code]
        if g == "Nữ":
            c2_env = f"đặc biệt lưu ý {haz_info['female_pathway']}"
        else:
            c2_env = f"đặc biệt lưu ý {haz_info['universal_advisory']}"
    elif g == "Nữ" and is_stem:
        c2_env = "đây là ngành công nghệ trọng điểm đang có nhiều chính sách thu hút và học bổng dành riêng cho nữ sinh tài năng"
    elif g == "Nam" and is_care:
        c2_env = "môi trường làm việc nhân văn đang mở rộng cơ hội cho nhân sự nam có năng lực giao tiếp và quản lý"
    else:
        c2_env = "môi trường học tập và phát triển nghề nghiệp rất năng động"

    c2 = f"{c2_adm}, đồng thời {c2_env}."

    # CÂU 3: Lộ trình hành động & Chiến thuật Nguyện vọng thích ứng khối lớp
    if tau >= 0.80:  # Lớp 10
        c3 = "Với lợi thế Lớp 10, bạn hãy chủ động xây dựng lộ trình học tập vững chắc các môn chủ lực và rèn luyện kỹ năng thực tế từ sớm."
    elif tau >= 0.50:  # Lớp 11
        c3 = "Bước sang Lớp 11, bạn nên tập trung bồi dưỡng dứt điểm các phần kiến thức còn thiếu của khối thi mục tiêu để tạo đà bứt phá."
    elif tau >= 0.20:  # Lớp 12
        if tier == "REACH":
            c3 = "Trong giai đoạn Lớp 12 nước rút, bạn nên đặt ngành này ở Nguyện vọng 1 - 2 để thử sức bứt phá và lót các nguyện vọng vừa sức ở phía sau."
        else:
            c3 = "Trong giai đoạn Lớp 12 nước rút, bạn nên đặt ngành này ở Nguyện vọng 3 - 5 để nắm chắc suất đỗ vào đại học."
    else:  # Đã tốt nghiệp
        c3 = "Bạn nên sớm hoàn thiện hồ sơ đăng ký theo phương thức điểm thực tế hoặc tham gia các chương trình đào tạo kỹ sư thực hành gắn liền việc làm."

    return f"{c1} {c2} {c3}"


def audit_cohort_gender_fairness(recommendation_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Kiểm toán Đạo đức AI theo Quy tắc Bốn phần năm (Four-Fifths Rule: 0.80 <= DIR <= 1.25).
    Chạy định kỳ trên nhật ký dữ liệu đoàn hệ (Cohort-level) trong CI/CD.
    """
    female_total = 0
    female_stem_count = 0
    male_total = 0
    male_stem_count = 0

    for log in recommendation_logs:
        g = log.get("gender")
        top_recs = log.get("top_recommendations", [])
        has_stem = any(
            rec.get("major_code", "")[:3] in ("748", "752", "751", "746")
            or rec.get("category", "") in STEM_BROAD_CATEGORIES
            for rec in top_recs
        )
        if g == "Nữ":
            female_total += 1
            if has_stem:
                female_stem_count += 1
        elif g == "Nam":
            male_total += 1
            if has_stem:
                male_stem_count += 1

    rate_female = (female_stem_count / female_total) if female_total > 0 else 0.0
    rate_male = (male_stem_count / male_total) if male_total > 0 else 0.0

    dir_metric = (rate_female / rate_male) if rate_male > 0 else 1.0

    return {
        "female_total": female_total,
        "female_stem_rate": round(rate_female, 4),
        "male_total": male_total,
        "male_stem_rate": round(rate_male, 4),
        "disparate_impact_ratio": round(dir_metric, 4),
        "is_fair": 0.80 <= dir_metric <= 1.25,
        "status": "PASS" if (0.80 <= dir_metric <= 1.25) else "NEEDS_CALIBRATION",
    }
