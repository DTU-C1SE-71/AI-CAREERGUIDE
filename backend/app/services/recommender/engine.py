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
