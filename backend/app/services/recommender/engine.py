import math
from typing import Dict, Any, List, Tuple, Optional

# Standard RIASEC Holland dimensions
RIASEC_DIMENSIONS = ["R", "I", "A", "S", "E", "C"]

RIASEC_NAMES_VI = {
    "R": "Kỹ thuật / Thực tế (Realistic)",
    "I": "Nghiên cứu / Khám phá (Investigative)",
    "A": "Nghệ thuật / Sáng tạo (Artistic)",
    "S": "Xã hội / Giúp đỡ (Social)",
    "E": "Quản lý / Khởi nghiệp (Enterprising)",
    "C": "Nghiệp vụ / Quy củ (Conventional)"
}


def normal_cdf(z: float) -> float:
    """
    Computes Cumulative Distribution Function (CDF) for standard normal distribution N(0, 1).
    CDF(z) = 0.5 * (1 + erf(z / sqrt(2)))
    Guaranteed bounded in [0.0, 1.0].
    """
    if math.isnan(z):
        return 0.5
    return max(0.0, min(1.0, 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))))


def calculate_riasec_cosine_similarity(
    student_vector: Dict[str, float],
    major_vector: Dict[str, float]
) -> float:
    """
    Pillar 1: Holland RIASEC vocational interest fit via Cosine Similarity.
    Score = (V_student . V_major) / (||V_student|| * ||V_major||)
    
    EDGE CASES HANDLED:
    - Zero vector: returns 0.0 (prevents ZeroDivisionError)
    - Missing keys: defaults to 0.0
    - Clamped strictly between 0.0 and 1.0
    """
    if not student_vector or not major_vector:
        return 0.0

    dot_product = 0.0
    norm_sq_s = 0.0
    norm_sq_m = 0.0

    for dim in RIASEC_DIMENSIONS:
        s_val = float(student_vector.get(dim, 0.0))
        m_val = float(major_vector.get(dim, 0.0))
        # Ensure non-negative bounds
        s_val = max(0.0, s_val)
        m_val = max(0.0, m_val)

        dot_product += s_val * m_val
        norm_sq_s += s_val * s_val
        norm_sq_m += m_val * m_val

    if norm_sq_s <= 0.0 or norm_sq_m <= 0.0:
        return 0.0

    denominator = math.sqrt(norm_sq_s) * math.sqrt(norm_sq_m)
    similarity = dot_product / denominator
    return max(0.0, min(1.0, similarity))


def calculate_z_score_and_cdf(
    raw_total: float,
    national_mean: float,
    national_std: float
) -> Tuple[float, float]:
    """
    Calculates standardized Z-score and cumulative normal probability CDF(Z).
    Z = (X - mu) / sigma
    Score = Clamp(CDF(Z), 0.0, 1.0)
    
    EDGE CASES HANDLED:
    - sigma <= 0: safely falls back to standard dev = 1.0
    - Extremely large / small Z values clamped within bounds
    """
    sigma = float(national_std) if national_std and national_std > 0 else 1.0
    z = (float(raw_total) - float(national_mean)) / sigma
    cdf = normal_cdf(z)
    return round(z, 4), round(cdf, 4)


def evaluate_academic_readiness_for_major(
    admitted_block_codes: List[str],
    student_block_results: Dict[str, Any],
    default_score: float = 0.5
) -> Tuple[float, Optional[str], Dict[str, Any]]:
    """
    Pillar 2: Academic Readiness via Z-Score Normalization across admitted subject blocks.
    Identifies the best matching block among those accepted by the major.
    
    Returns:
    - best_score: float in [0.0, 1.0]
    - best_block: block code string, e.g. "A00"
    - breakdown: dictionary of all evaluated admitted blocks
    """
    if not admitted_block_codes or not student_block_results:
        return default_score, (admitted_block_codes[0] if admitted_block_codes else None), {
            "status": "DEFAULT_NEUTRAL",
            "message": "Học sinh chưa nhập điểm các khối xét tuyển của ngành này."
        }

    best_score = -1.0
    best_block = None
    block_evaluations: Dict[str, Any] = {}

    for block_code in admitted_block_codes:
        if block_code in student_block_results:
            b_data = student_block_results[block_code]
            score_acad = float(b_data.get("score_academic", 0.5))
            z_score = float(b_data.get("z_score", 0.0))
            raw_sum = float(b_data.get("raw_sum", 0.0))

            block_evaluations[block_code] = {
                "raw_sum": raw_sum,
                "z_score": z_score,
                "score_academic": score_acad
            }

            if score_acad > best_score:
                best_score = score_acad
                best_block = block_code

    if best_block is None or best_score < 0.0:
        return default_score, (admitted_block_codes[0] if admitted_block_codes else None), {
            "status": "NO_ADMITTED_BLOCK_MATCH",
            "message": "Các khối đã nhập không thuộc tổ hợp xét tuyển của ngành."
        }

    return round(best_score, 4), best_block, block_evaluations


def calculate_cognitive_preference_match(
    student_traits: Dict[str, Any],
    major_attributes: Dict[str, Any]
) -> float:
    """
    Pillar 3: Deterministic Rule-Based Cognitive Preference Matching.
    Evaluates alignment between student learning styles (Gardner/MBTI) and major learning environment:
    - Ordinal traits (abstract_thinking, analytical_reasoning, spatial_perception, linguistic_ability):
        * Exact match: 1.0
        * Adjacent match: 0.5 (e.g. high vs medium)
        * Opposite match: 0.0 (high vs low)
    - Categorical traits:
        * learning_environment (structured, exploratory, collaborative):
            Exact: 1.0, adjacent: 0.5, divergent: 0.0
        * teamwork_intensity (independent, balanced, highly_collaborative):
            Exact: 1.0, adjacent: 0.5, divergent: 0.0
    """
    if not major_attributes:
        return 0.5
    if not student_traits:
        student_traits = {}

    ordinal_traits = [
        "abstract_thinking",
        "analytical_reasoning",
        "spatial_perception",
        "linguistic_ability"
    ]
    level_scale = {"low": 1, "medium": 2, "high": 3}
    match_scores: List[float] = []

    for trait in ordinal_traits:
        s_val = str(student_traits.get(trait, "medium")).lower().strip()
        m_val = str(major_attributes.get(trait, "medium")).lower().strip()

        s_num = level_scale.get(s_val, 2)
        m_num = level_scale.get(m_val, 2)
        diff = abs(s_num - m_num)

        if diff == 0:
            match_scores.append(1.0)
        elif diff == 1:
            match_scores.append(0.5)
        else:
            match_scores.append(0.0)

    # Learning Environment Match
    s_env = str(student_traits.get("learning_environment", "structured")).lower().strip()
    m_env = str(major_attributes.get("learning_environment", "structured")).lower().strip()
    if s_env == m_env:
        match_scores.append(1.0)
    elif (s_env in ("structured", "exploratory") and m_env in ("structured", "exploratory")) or \
         (s_env in ("collaborative", "exploratory") and m_env in ("collaborative", "exploratory")):
        match_scores.append(0.5)
    else:
        match_scores.append(0.2)

    # Teamwork Intensity Match
    s_team = str(student_traits.get("teamwork_intensity", "balanced")).lower().strip()
    m_team = str(major_attributes.get("teamwork_intensity", "balanced")).lower().strip()
    team_scale = {"independent": 1, "balanced": 2, "highly_collaborative": 3}
    s_t_num = team_scale.get(s_team, 2)
    m_t_num = team_scale.get(m_team, 2)
    t_diff = abs(s_t_num - m_t_num)
    if t_diff == 0:
        match_scores.append(1.0)
    elif t_diff == 1:
        match_scores.append(0.5)
    else:
        match_scores.append(0.0)

    score = sum(match_scores) / len(match_scores) if match_scores else 0.5
    return round(max(0.0, min(1.0, score)), 4)


def calculate_3pillar_hybrid_score(
    score_riasec: float,
    score_academic: float,
    score_preference: float,
    w_riasec: float = 0.45,
    w_academic: float = 0.35,
    w_preference: float = 0.20
) -> Tuple[float, Dict[str, float]]:
    """
    Holistic 3-Pillar Weighted Hybrid Model:
    Score_Major = w_RIASEC * Score_RIASEC + w_Academic * Score_Academic + w_Preference * Score_Preference
    Constraint: w_RIASEC + w_Academic + w_Preference = 1.0 (auto-normalized if needed)
    """
    total_w = w_riasec + w_academic + w_preference
    if total_w <= 0.0 or abs(total_w - 1.0) > 1e-6:
        # Normalize weights to sum exactly to 1.0
        norm_factor = total_w if total_w > 0 else 1.0
        w_riasec = w_riasec / norm_factor
        w_academic = w_academic / norm_factor
        w_preference = w_preference / norm_factor

    score = (
        w_riasec * score_riasec +
        w_academic * score_academic +
        w_preference * score_preference
    )
    score_clamped = max(0.0, min(1.0, score))

    weights_dict = {
        "w_riasec": round(w_riasec, 4),
        "w_academic": round(w_academic, 4),
        "w_preference": round(w_preference, 4)
    }
    return round(score_clamped, 4), weights_dict


def generate_xai_top_supporting_factors(
    major_name: str,
    score_riasec: float,
    student_riasec: Dict[str, float],
    major_riasec: Dict[str, float],
    score_academic: float,
    best_block: Optional[str],
    score_pref: float,
    student_pref: Dict[str, Any],
    major_attr: Dict[str, Any]
) -> Tuple[List[str], str]:
    """
    Generates deterministic, explainable AI (XAI) top supporting factors
    WITHOUT ANY NON-DETERMINISTIC LLM.
    Identifies top matching dimensions and returns structured insights.
    """
    supporting_factors: List[str] = []

    # 1. RIASEC Analysis
    top_student_dims = sorted(
        RIASEC_DIMENSIONS,
        key=lambda d: float(student_riasec.get(d, 0.0)),
        reverse=True
    )[:2]
    top_major_dims = sorted(
        RIASEC_DIMENSIONS,
        key=lambda d: float(major_riasec.get(d, 0.0)),
        reverse=True
    )[:2]
    overlap_dims = set(top_student_dims).intersection(set(top_major_dims))

    if score_riasec >= 0.75:
        if overlap_dims:
            names = [RIASEC_NAMES_VI.get(d, d) for d in overlap_dims]
            supporting_factors.append(
                f"Sở thích nghề nghiệp xuất sắc: Điểm tương đồng Holland đạt {round(score_riasec * 100, 1)}%, nổi bật ở nhóm {', '.join(names)}."
            )
        else:
            supporting_factors.append(
                f"Sở thích nghề nghiệp phù hợp cao: Độ tương quan tổng thể đạt {round(score_riasec * 100, 1)}%."
            )
    elif score_riasec >= 0.50:
        supporting_factors.append(
            f"Sở thích nghề nghiệp tương đồng mức trung bình khá: Đạt {round(score_riasec * 100, 1)}%."
        )

    # 2. Academic Analysis
    if score_academic >= 0.75:
        supporting_factors.append(
            f"Năng lực học thuật vượt trội: Khối xét tuyển {best_block or 'thế mạnh'} đạt phân vị {round(score_academic * 100, 1)}% chuẩn hóa toàn quốc."
        )
    elif score_academic >= 0.50:
        supporting_factors.append(
            f"Năng lực học thuật đáp ứng tốt: Khối {best_block or 'xét tuyển'} đạt mức {round(score_academic * 100, 1)}% so với phổ điểm quốc gia."
        )
    else:
        supporting_factors.append(
            f"Điểm học thuật khối {best_block or 'xét tuyển'} ({round(score_academic * 100, 1)}%) cần bổ sung lộ trình rèn luyện để nâng cao khả năng trúng tuyển."
        )

    # 3. Cognitive Environment Match
    s_env = student_pref.get("learning_environment", "structured")
    m_env = major_attr.get("learning_environment", "structured")
    if s_env == m_env:
        supporting_factors.append(
            f"Môi trường học tập tương thích tối ưu: Bạn có xu hướng học tập '{s_env}' phù hợp trọn vẹn với mô hình đào tạo của ngành."
        )
    elif score_pref >= 0.70:
        supporting_factors.append(
            f"Độ thích ứng phong cách tư duy đạt {round(score_pref * 100, 1)}% qua các tiêu chí tư duy logic và giải quyết vấn đề."
        )

    summary_explanation = (
        f"Ngành {major_name} được đề xuất dựa trên mô hình lai 3 trụ cột tất định: "
        f"Sở thích Holland ({round(score_riasec * 100, 1)}%), "
        f"Năng lực khối thi {best_block or 'xét tuyển'} ({round(score_academic * 100, 1)}%) "
        f"và Độ hòa hợp nhận thức ({round(score_pref * 100, 1)}%)."
    )

    return supporting_factors, summary_explanation


# ==========================================
# SOLUTION B: DYNAMIC ACADEMIC CLUSTERING & ADMISSION FEASIBILITY
# ==========================================

def classify_major_academic_benchmark(
    major_code: str,
    major_name: str,
    category: str = ""
) -> Dict[str, Any]:
    """
    Evaluates dynamic admission benchmark and competition tier for any Level-IV major.
    Handles any Circular (TT09, TT74/2026, or future circulars).
    """
    name_lower = (major_name or "").lower()
    cat_lower = (category or "").lower()

    # Tier 1: Extreme / High Competition (Cutoff typically >= 24.5 - 28.5)
    high_keywords = [
        "y khoa", "y đa khoa", "răng hàm mặt", "răng - hàm - mặt", "dược học",
        "y học cổ truyền", "khoa học máy tính", "trí tuệ nhân tạo", "khoa học dữ liệu",
        "vi mạch", "bán dẫn", "kinh tế quốc tế", "kinh doanh quốc tế", "luật kinh tế",
        "logistics"
    ]
    if any(k in name_lower for k in high_keywords):
        return {
            "tier": "HIGH_COMPETITION",
            "tier_label": "Cạnh tranh cực cao (≥ 24.5đ)",
            "benchmark_cutoff": 25.5,
            "min_recommended": 23.5,
            "description": "Ngành mũi nhọn với điểm chuẩn đại học thuộc top đầu cả nước."
        }

    # Tier 2: Medium / Solid Competition (Cutoff typically 19.5 - 23.5)
    medium_keywords = [
        "kỹ thuật xét nghiệm", "kỹ thuật hình ảnh", "phục hồi chức năng", "điều dưỡng",
        "công nghệ thông tin", "an toàn thông tin", "kỹ thuật phần mềm", "hệ thống thông tin",
        "tài chính", "ngân hàng", "kế toán", "kiểm toán", "marketing", "truyền thông",
        "thương mại điện tử", "luật", "sư phạm", "ngôn ngữ anh", "ngôn ngữ trung"
    ]
    if any(k in name_lower for k in medium_keywords):
        return {
            "tier": "MEDIUM_COMPETITION",
            "tier_label": "Cạnh tranh khá (≥ 19.5đ)",
            "benchmark_cutoff": 21.0,
            "min_recommended": 19.0,
            "description": "Ngành học có tính cạnh tranh khá tại các trường đại học công lập uy tín."
        }

    # Tier 3: Standard / Accessible Competition (Cutoff typically 15.0 - 18.5)
    standard_keywords = [
        "công nghệ sinh học", "sinh học", "y tế công cộng", "dinh dưỡng", "thú y",
        "chăn nuôi", "nông nghiệp", "cây trồng", "lâm nghiệp", "thủy sản", "môi trường",
        "đất đai", "thực phẩm", "vật liệu", "dệt may", "văn phòng", "công tác xã hội",
        "xã hội học", "triết học", "lịch sử", "địa lý", "thống kê", "phát triển", "quản lý nhà nước"
    ]
    if any(k in name_lower for k in standard_keywords) or any(k in cat_lower for k in standard_keywords):
        return {
            "tier": "STANDARD_COMPETITION",
            "tier_label": "Vừa sức / Tiêu chuẩn (≥ 15.0đ)",
            "benchmark_cutoff": 16.5,
            "min_recommended": 15.0,
            "description": "Ngành đào tạo ứng dụng thực tế, điểm chuẩn phù hợp với mặt bằng phổ thông."
        }

    # Default fallback
    return {
        "tier": "STANDARD_COMPETITION",
        "tier_label": "Phổ thông (≥ 16.0đ)",
        "benchmark_cutoff": 18.0,
        "min_recommended": 15.5,
        "description": "Ngành học có phổ điểm tuyển sinh đa dạng theo phân khúc trường."
    }


def evaluate_admission_feasibility(
    raw_block_sum: float,
    major_code: str,
    major_name: str,
    category: str = ""
) -> Dict[str, Any]:
    """
    Computes feasibility tier (TARGET, REACH, ALTERNATIVE) and score gap.
    Prevents unrealistic recommendations (e.g. 15 points recommending Medicine as safe).
    """
    bm = classify_major_academic_benchmark(major_code, major_name, category)
    cutoff = bm["benchmark_cutoff"]
    min_rec = bm["min_recommended"]
    score_gap = round(raw_block_sum - cutoff, 1)

    if raw_block_sum >= min_rec - 1.0:
        feasibility_tier = "TARGET"
        feasibility_label = "Vừa sức / Khả thi cao"
        advice = f"Điểm khối thi của bạn ({raw_block_sum}đ) nằm trong vùng trúng tuyển an toàn so với điểm sàn tham chiếu (~{cutoff}đ)."
    else:
        feasibility_tier = "REACH"
        gap_abs = abs(score_gap)
        feasibility_label = f"Thử thách cao (Thiếu ~{gap_abs}đ)"
        advice = (
            f"Điểm khối thi ({raw_block_sum}đ) thấp hơn khoảng {gap_abs} điểm so với điểm chuẩn trung bình (~{cutoff}đ). "
            f"Đây là nguyện vọng mơ ước, cần bứt phá điểm số lớn để cạnh tranh trúng tuyển."
        )

    return {
        "feasibility_tier": feasibility_tier,
        "feasibility_label": feasibility_label,
        "benchmark_cutoff": cutoff,
        "min_recommended": min_rec,
        "score_gap": score_gap,
        "admission_advice": advice,
        "academic_tier": bm["tier"],
        "academic_tier_label": bm["tier_label"]
    }


# ==========================================
# OPTIMIZED 3-PILLAR FUNCTIONS & SMART SUBSTITUTION ENGINE
# ==========================================

HEXAGON_OPPOSITES = {
    "R": "S", "S": "R",
    "I": "E", "E": "I",
    "A": "C", "C": "A",
}

HEXAGON_ADJACENT = {
    "R": {"I", "C"},
    "I": {"R", "A"},
    "A": {"I", "S"},
    "S": {"A", "E"},
    "E": {"S", "C"},
    "C": {"E", "R"},
}


def calculate_enhanced_riasec_fit(
    student_vector: Dict[str, float],
    major_vector: Dict[str, float]
) -> float:
    """
    Optimized Pillar 1 (45%):
    Combines Cosine Similarity (75%) + Top-2 Holland Peak & Hexagonal Alignment (25%)
    with Flat-Profile differentiation adjustment.
    """
    base_cos = calculate_riasec_cosine_similarity(student_vector, major_vector)
    if base_cos <= 0.0:
        return 0.0

    s_ranked = sorted(RIASEC_DIMENSIONS, key=lambda d: float(student_vector.get(d, 0.0)), reverse=True)
    m_ranked = sorted(RIASEC_DIMENSIONS, key=lambda d: float(major_vector.get(d, 0.0)), reverse=True)

    s_top1, s_top2 = s_ranked[0], s_ranked[1]
    m_top1, m_top2 = m_ranked[0], m_ranked[1]

    # Hexagonal Peak Alignment Score
    if s_top1 == m_top1 and s_top2 == m_top2:
        peak_score = 1.0
    elif s_top1 == m_top1 or (s_top1 == m_top2 and s_top2 == m_top1):
        peak_score = 0.92
    elif s_top1 in (m_top1, m_top2) or s_top2 in (m_top1, m_top2):
        peak_score = 0.78
    elif m_top1 in HEXAGON_ADJACENT.get(s_top1, set()):
        peak_score = 0.65
    elif HEXAGON_OPPOSITES.get(s_top1) == m_top1:
        peak_score = 0.25
    else:
        peak_score = 0.50

    combined = 0.75 * base_cos + 0.25 * peak_score

    # Flat-profile check: dampen artificially inflated scores if student vector has near-zero differentiation
    s_vals = [max(0.0, float(student_vector.get(d, 0.0))) for d in RIASEC_DIMENSIONS]
    diff = max(s_vals) - min(s_vals) if s_vals else 0.0
    if diff < 0.08:
        combined = 0.65 * combined + 0.35 * 0.60

    return round(max(0.0, min(1.0, combined)), 4)


def evaluate_target_anchored_academic_fit(
    admitted_block_codes: List[str],
    student_block_results: Dict[str, Any],
    benchmark_cutoff: float = 18.0,
    min_recommended: float = 15.5,
    default_score: float = 0.5
) -> Tuple[float, Optional[str], Dict[str, Any]]:
    """
    Optimized Pillar 2 (35%):
    Target-Anchored Academic Fit combining national Z-Score CDF with Major Cutoff Alignment.
    Rewards majors whose admission benchmark matches the student's actual competency zone,
    and penalizes majors whose cutoff exceeds the student's score.
    """
    base_acad, best_block, breakdown = evaluate_academic_readiness_for_major(
        admitted_block_codes, student_block_results, default_score=default_score
    )
    if not best_block or not isinstance(breakdown, dict) or best_block not in breakdown:
        return base_acad, best_block, breakdown

    raw_sum = float(breakdown[best_block].get("raw_sum", 18.0))
    gap_to_cutoff = raw_sum - benchmark_cutoff
    gap_to_min = raw_sum - min_recommended

    if gap_to_min >= -0.5:
        # Student meets or exceeds the minimum recommended threshold for this major
        if -1.0 <= gap_to_cutoff <= 3.5:
            # Sweet spot: major difficulty aligns closely with student's score
            anchored_score = min(1.0, max(base_acad, 0.82 + 0.04 * max(0.0, gap_to_cutoff + 1.0)))
        elif gap_to_cutoff > 3.5:
            # Student is well above cutoff (safe match, slight taper so high-tier majors still shine for top students)
            anchored_score = min(1.0, 0.65 * base_acad + 0.35 * 0.86)
        else:
            anchored_score = max(0.60, base_acad)
    else:
        # Student is below minimum threshold -> sharp reduction
        deficit = abs(gap_to_min)
        penalty_factor = max(0.10, 1.0 - (deficit / 10.0) * 0.85)
        anchored_score = max(0.05, base_acad * penalty_factor)

    if raw_sum < min_recommended - 1.0:
        breakdown["safety_tier"] = "REACH"
    elif raw_sum >= benchmark_cutoff + 1.0:
        breakdown["safety_tier"] = "SAFETY"
    else:
        breakdown["safety_tier"] = "TARGET"
    breakdown["gap_to_cutoff"] = round(gap_to_cutoff, 2)

    return round(anchored_score, 4), best_block, breakdown


def normalize_student_cognitive_traits(
    raw_traits: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Deterministically maps the 8 Cognitive Assessment answers (COG_1..COG_8 /
    learning_style..team_role) into the 6 canonical cognitive attributes used
    by Pillar 3 (abstract_thinking, analytical_reasoning, spatial_perception,
    linguistic_ability, learning_environment, teamwork_intensity).
    Preserves any explicit canonical keys already provided.
    """
    if not raw_traits:
        return {}

    canonical_keys = {
        "abstract_thinking",
        "analytical_reasoning",
        "spatial_perception",
        "linguistic_ability",
        "learning_environment",
        "teamwork_intensity",
    }
    # If caller already supplied canonical keys and no COG_1..8 keys, return as-is
    cog_keys = {
        "COG_1", "COG_2", "COG_3", "COG_4", "COG_5", "COG_6", "COG_7", "COG_8",
        "learning_style", "work_environment", "problem_solving", "interaction_target",
        "gardner_intelligence", "pressure_tolerance", "output_preference", "team_role",
    }
    if not any(k in raw_traits for k in cog_keys):
        return dict(raw_traits)

    def _pick(code_key: str, dim_key: str) -> str:
        val = str(raw_traits.get(code_key) or raw_traits.get(dim_key) or "").upper().strip()
        if val in ("A", "B", "C", "D"):
            return val
        if "VISUAL" in val or "LAB_DIGITAL" in val or "QUANTITATIVE" in val or "SYSTEMS" in val or "LOGICAL_MATH" in val or "HIGH_STAKES" in val or "TANGIBLE_TECH" in val or "TECHNICAL_SPECIALIST" in val:
            return "A"
        if "THEORETICAL" in val or "DYNAMIC_CORPORATE" in val or "CREATIVE_DIVERGENT" in val or "DATA_FINANCE" in val or "LINGUISTIC" in val or "MARKET_DEADLINE" in val or "ECONOMIC_LEGAL" in val or "STRATEGIC_LEADER" in val:
            return "B"
        if "HANDS_ON" in val or "FIELD_INDUSTRIAL" in val or "HUMAN_EMPATHY" in val or "PEOPLE_COMMUNITY" in val or "SPATIAL_MUSICAL" in val or "DEEP_RND" in val or "HUMAN_WELLBEING" in val or "CREATIVE_COMMUNICATOR" in val:
            return "C"
        if "INTERACTIVE" in val or "INSTITUTIONAL" in val or "PROCEDURAL" in val or "NATURE_BIO" in val or "NATURALIST" in val or "STABLE_SUSTAINABLE" in val or "CREATIVE_SCIENTIFIC" in val or "QUALITY_CONTROLLER" in val:
            return "D"
        return ""

    c1 = _pick("COG_1", "learning_style")
    c2 = _pick("COG_2", "work_environment")
    c3 = _pick("COG_3", "problem_solving")
    c4 = _pick("COG_4", "interaction_target")
    c5 = _pick("COG_5", "gardner_intelligence")
    c6 = _pick("COG_6", "pressure_tolerance")
    c7 = _pick("COG_7", "output_preference")
    c8 = _pick("COG_8", "team_role")

    # 1. Analytical Reasoning score
    analytical_pts = (
        (2 if c1 == "B" else 0)
        + (2 if c3 in ("A", "D") else 0)
        + (1 if c4 in ("A", "B") else 0)
        + (2 if c5 == "A" else 0)
        + (2 if c6 == "C" else 0)
        + (1 if c8 in ("A", "D") else 0)
    )
    # 2. Abstract Thinking score
    abstract_pts = (
        (2 if c1 in ("A", "B") else 0)
        + (2 if c3 in ("A", "B") else 0)
        + (2 if c5 in ("A", "C") else 0)
        + (2 if c6 == "C" else 0)
        + (2 if c7 in ("A", "D") else 0)
    )
    # 3. Spatial Perception score
    spatial_pts = (
        (2 if c1 in ("A", "C") else 0)
        + (1 if c2 == "C" else 0)
        + (2 if c3 == "B" else 0)
        + (1 if c4 in ("A", "D") else 0)
        + (2 if c5 in ("C", "D") else 0)
        + (2 if c7 == "A" else 0)
    )
    # 4. Linguistic & Interpersonal score
    linguistic_pts = (
        (2 if c1 in ("B", "D") else 0)
        + (2 if c3 in ("C", "D") else 0)
        + (2 if c4 in ("B", "C") else 0)
        + (2 if c5 == "B" else 0)
        + (1 if c7 in ("B", "C") else 0)
        + (1 if c8 in ("B", "C") else 0)
    )

    def _to_level(pts: int) -> str:
        if pts >= 4:
            return "high"
        if pts >= 2:
            return "medium"
        return "low"

    # 5. Learning Environment
    if c2 == "B" or c1 == "D":
        learn_env = "collaborative"
    elif c2 == "A" and c3 == "B":
        learn_env = "exploratory"
    elif c2 == "C" or c1 == "C":
        learn_env = "exploratory"
    elif c2 == "A":
        learn_env = "independent"
    else:
        learn_env = "structured"

    # 6. Teamwork Intensity
    if c8 == "A":
        team_int = "independent"
    elif c8 in ("B", "C") or c4 == "C":
        team_int = "highly_collaborative"
    else:
        team_int = "balanced"

    derived = dict(raw_traits)
    derived.setdefault("analytical_reasoning", _to_level(analytical_pts))
    derived.setdefault("abstract_thinking", _to_level(abstract_pts))
    derived.setdefault("spatial_perception", _to_level(spatial_pts))
    derived.setdefault("linguistic_ability", _to_level(linguistic_pts))
    derived.setdefault("learning_environment", learn_env)
    derived.setdefault("teamwork_intensity", team_int)
    return derived


def calculate_asymmetric_cognitive_fit(
    student_traits: Dict[str, Any],
    major_attributes: Dict[str, Any]
) -> float:
    """
    Optimized Pillar 3 (20%):
    Asymmetric Competency Matrix for ability dimensions (student >= required -> 1.0)
    combined with Symmetric Cultural Fit for learning environment & teamwork.
    """
    if not major_attributes:
        return 0.5
    student_traits = normalize_student_cognitive_traits(student_traits)

    ordinal_traits = [
        "abstract_thinking",
        "analytical_reasoning",
        "spatial_perception",
        "linguistic_ability",
    ]
    level_scale = {"low": 1, "medium": 2, "high": 3}
    match_scores: List[float] = []

    for trait in ordinal_traits:
        s_val = str(student_traits.get(trait, "medium")).lower().strip()
        m_val = str(major_attributes.get(trait, "medium")).lower().strip()
        s_num = level_scale.get(s_val, 2)
        m_num = level_scale.get(m_val, 2)

        if s_num >= m_num:
            # Student meets or exceeds the cognitive requirement of the major -> full credit
            match_scores.append(1.0)
        elif m_num - s_num == 1:
            match_scores.append(0.55)
        else:
            match_scores.append(0.10)

    # Symmetric Learning Environment Match
    s_env = str(student_traits.get("learning_environment", "structured")).lower().strip()
    m_env = str(major_attributes.get("learning_environment", "structured")).lower().strip()
    if s_env == m_env:
        match_scores.append(1.0)
    elif (s_env in ("structured", "exploratory") and m_env in ("structured", "exploratory")) or \
         (s_env in ("collaborative", "exploratory") and m_env in ("collaborative", "exploratory")):
        match_scores.append(0.6)
    else:
        match_scores.append(0.25)

    # Symmetric Teamwork Intensity Match
    s_team = str(student_traits.get("teamwork_intensity", "balanced")).lower().strip()
    m_team = str(major_attributes.get("teamwork_intensity", "balanced")).lower().strip()
    team_scale = {"independent": 1, "balanced": 2, "highly_collaborative": 3}
    t_diff = abs(team_scale.get(s_team, 2) - team_scale.get(m_team, 2))
    if t_diff == 0:
        match_scores.append(1.0)
    elif t_diff == 1:
        match_scores.append(0.6)
    else:
        match_scores.append(0.2)

    score = sum(match_scores) / len(match_scores) if match_scores else 0.5
    return round(max(0.0, min(1.0, score)), 4)


def extract_6digit_code(major_code: str) -> str:
    """Normalizes 7-digit (7480101) or 6-digit (480101) code to 6-digit TT74 format."""
    digits = "".join(ch for ch in str(major_code or "") if ch.isdigit())
    if len(digits) == 7 and digits.startswith(("7", "8", "9")):
        return digits[1:]
    return digits


# Cross-field practical substitution pathways (High-cutoff Field -> Accessible Sibling Field)
CROSS_FIELD_SUBSTITUTION_MAP = {
    "48": {"48", "46", "51", "34", "32"},  # Máy tính/CNTT -> CNTT ứng dụng, CNKT Điện tử, HTTT quản lý, CN truyền thông
    "52": {"51", "52", "58", "54"},        # Kỹ thuật hàn lâm (52) -> Công nghệ kỹ thuật ứng dụng (51)
    "72": {"72", "42", "64", "76", "54"},  # Y Dược điểm cao -> Kỹ thuật Y học, Điều dưỡng, Dinh dưỡng, CN sinh học
    "34": {"34", "31", "51", "81", "84"},  # Kinh doanh quốc tế/Logistics -> QTKD, Kinh tế, Quản lý công nghiệp, Vận tải
    "14": {"14", "22", "31", "76"},        # Sư phạm điểm cao -> Khoa học giáo dục, Công nghệ giáo dục, Ngôn ngữ
    "38": {"38", "31", "34", "76"},        # Luật kinh tế -> Luật, Quản lý nhà nước, Công tác xã hội
}


def are_majors_related_pathway(code_high: str, code_sub: str) -> int:
    """
    Returns similarity tier between a blocked high-cutoff major and a candidate substitute major:
    - 3: Same 4-digit Group (e.g. 480107 AI -> 480104 Hệ thống thông tin)
    - 2: Same 2-digit Field or Engineering 52 -> 51 sibling (e.g. 520114 KT Cơ điện tử -> 510203 CNKT Cơ điện tử)
    - 1: Mapped cross-field practical pathway (e.g. 720101 Y khoa -> 420201 Công nghệ sinh học)
    - 0: Unrelated field
    """
    c_h = extract_6digit_code(code_high)
    c_s = extract_6digit_code(code_sub)
    if len(c_h) < 4 or len(c_s) < 4:
        return 0
    if c_h[:4] == c_s[:4]:
        return 3
    if c_h[:2] == c_s[:2] or (c_h[:2] == "52" and c_s[:2] == "51"):
        return 2
    if c_s[:2] in CROSS_FIELD_SUBSTITUTION_MAP.get(c_h[:2], set()):
        return 1
    return 0

