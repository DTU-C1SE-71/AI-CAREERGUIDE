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


def normalize_subject_name(name: str) -> str:
    """
    Chuẩn hóa tên môn học THPT về dạng thống nhất để khớp chính xác giữa Frontend và Database
    (vd: 'Vật lí' <-> 'Vật lý', 'Địa lí' <-> 'Địa lý', 'Văn' -> 'Ngữ văn').
    """
    raw = " ".join(str(name or "").strip().split())
    if not raw:
        return ""
    low = raw.lower()
    canonical_aliases = {
        "toán": "Toán",
        "toán học": "Toán",
        "ngữ văn": "Ngữ văn",
        "văn": "Ngữ văn",
        "tiếng anh": "Tiếng Anh",
        "anh": "Tiếng Anh",
        "anh văn": "Tiếng Anh",
        "ngoại ngữ": "Tiếng Anh",
        "vật lý": "Vật lý",
        "vật lí": "Vật lý",
        "lý": "Vật lý",
        "lí": "Vật lý",
        "hóa học": "Hóa học",
        "hoá học": "Hóa học",
        "hóa": "Hóa học",
        "hoá": "Hóa học",
        "sinh học": "Sinh học",
        "sinh": "Sinh học",
        "lịch sử": "Lịch sử",
        "sử": "Lịch sử",
        "địa lý": "Địa lý",
        "địa lí": "Địa lý",
        "địa": "Địa lý",
        "gdkt & pháp luật": "GDKT & Pháp luật",
        "gdkt&pl": "GDKT & Pháp luật",
        "gdcd": "GDKT & Pháp luật",
        "giáo dục công dân": "GDKT & Pháp luật",
        "tin học / công nghệ": "Tin học / Công nghệ",
        "tin học": "Tin học / Công nghệ",
        "công nghệ": "Tin học / Công nghệ",
    }
    return canonical_aliases.get(low, raw)


def normalize_grades_dict(grades: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """Chuẩn hóa từ điển điểm môn học (kẹp về khoảng [0.0, 10.0] và thống nhất tên môn)."""
    normalized: Dict[str, float] = {}
    if not grades:
        return normalized
    for k, v in grades.items():
        canon = normalize_subject_name(str(k))
        if not canon:
            continue
        try:
            score_val = float(v)
        except (TypeError, ValueError):
            continue
        if math.isnan(score_val) or math.isinf(score_val):
            continue
        clamped = round(max(0.0, min(10.0, score_val)), 2)
        # Nếu trùng tên gốc (vd cả 'Vật lý' và 'Vật lí'), giữ giá trị sau cùng hoặc lớn hơn
        normalized[canon] = clamped
    return normalized


# Danh mục các tổ hợp môn xét tuyển chuẩn quốc gia kèm tham số chuẩn hóa Z-Score (mu, sigma)
STANDARD_SUBJECT_BLOCKS: Dict[str, Dict[str, Any]] = {
    "A00": {"name": "Toán, Vật lý, Hóa học", "subjects": ["Toán", "Vật lý", "Hóa học"], "national_mean": 20.85, "national_std": 3.25},
    "A01": {"name": "Toán, Vật lý, Tiếng Anh", "subjects": ["Toán", "Vật lý", "Tiếng Anh"], "national_mean": 20.15, "national_std": 3.10},
    "A02": {"name": "Toán, Vật lý, Sinh học", "subjects": ["Toán", "Vật lý", "Sinh học"], "national_mean": 19.50, "national_std": 3.20},
    "B00": {"name": "Toán, Hóa học, Sinh học", "subjects": ["Toán", "Hóa học", "Sinh học"], "national_mean": 19.80, "national_std": 3.40},
    "B08": {"name": "Toán, Sinh học, Tiếng Anh", "subjects": ["Toán", "Sinh học", "Tiếng Anh"], "national_mean": 19.40, "national_std": 3.25},
    "C00": {"name": "Ngữ văn, Lịch sử, Địa lý", "subjects": ["Ngữ văn", "Lịch sử", "Địa lý"], "national_mean": 21.50, "national_std": 3.35},
    "C01": {"name": "Ngữ văn, Toán, Vật lý", "subjects": ["Ngữ văn", "Toán", "Vật lý"], "national_mean": 20.30, "national_std": 3.15},
    "C03": {"name": "Ngữ văn, Toán, Lịch sử", "subjects": ["Ngữ văn", "Toán", "Lịch sử"], "national_mean": 20.40, "national_std": 3.20},
    "C04": {"name": "Ngữ văn, Toán, Địa lý", "subjects": ["Ngữ văn", "Toán", "Địa lý"], "national_mean": 20.60, "national_std": 3.15},
    "D01": {"name": "Toán, Ngữ văn, Tiếng Anh", "subjects": ["Toán", "Ngữ văn", "Tiếng Anh"], "national_mean": 19.20, "national_std": 3.15},
    "D07": {"name": "Toán, Hóa học, Tiếng Anh", "subjects": ["Toán", "Hóa học", "Tiếng Anh"], "national_mean": 20.40, "national_std": 3.20},
    "D08": {"name": "Toán, Sinh học, Tiếng Anh", "subjects": ["Toán", "Sinh học", "Tiếng Anh"], "national_mean": 19.90, "national_std": 3.30},
    "D10": {"name": "Toán, Địa lý, Tiếng Anh", "subjects": ["Toán", "Địa lý", "Tiếng Anh"], "national_mean": 19.60, "national_std": 3.15},
    "D14": {"name": "Ngữ văn, Lịch sử, Tiếng Anh", "subjects": ["Ngữ văn", "Lịch sử", "Tiếng Anh"], "national_mean": 20.50, "national_std": 3.25},
    "D15": {"name": "Ngữ văn, Địa lý, Tiếng Anh", "subjects": ["Ngữ văn", "Địa lý", "Tiếng Anh"], "national_mean": 20.45, "national_std": 3.20},
    "H00": {"name": "Ngữ văn, Hình họa mỹ thuật, Bố cục màu", "subjects": ["Ngữ văn", "Hình họa mỹ thuật", "Bố cục màu"], "national_mean": 21.00, "national_std": 3.00},
    "V00": {"name": "Toán, Vật lý, Vẽ mỹ thuật", "subjects": ["Toán", "Vật lý", "Vẽ mỹ thuật"], "national_mean": 20.50, "national_std": 3.00},
    "V01": {"name": "Toán, Ngữ văn, Vẽ mỹ thuật", "subjects": ["Toán", "Ngữ văn", "Vẽ mỹ thuật"], "national_mean": 20.20, "national_std": 3.00},
}

# Các khối có môn thi năng khiếu riêng không có trong bảng 10 môn THPT thông thường
APTITUDE_BLOCKS = {"H00", "H01", "M00", "N00", "S00", "T00", "T01", "V00", "V01"}

FAILING_SUBJECT_THRESHOLD = 1.0  # Điểm liệt quốc gia (<= 1.0đ)
MIN_UNIVERSITY_SUBJECT_FLOOR = 3.5  # Ngưỡng tối thiểu cho từng môn trong khối xét tuyển


def compute_block_zscores_from_grades(
    grades: Optional[Dict[str, Any]],
    db_blocks: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """
    Tính điểm tổng 3 môn, Z-Score và phân vị CDF(Z) cho mọi khối xét tuyển có đủ điểm.
    Hỗ trợ đồng thời khối từ DB và bộ khối chuẩn quốc gia (chuẩn hóa Vật lý/Vật lí, Địa lý/Địa lí).
    """
    norm_grades = normalize_grades_dict(grades)
    if not norm_grades:
        return {}

    blocks_catalog: Dict[str, Dict[str, Any]] = {
        code: dict(info) for code, info in STANDARD_SUBJECT_BLOCKS.items()
    }
    if db_blocks:
        for blk in db_blocks:
            b_code = getattr(blk, "block_code", None) if not isinstance(blk, dict) else blk.get("block_code")
            b_subjs = getattr(blk, "subjects", None) if not isinstance(blk, dict) else blk.get("subjects")
            b_mean = getattr(blk, "national_mean", None) if not isinstance(blk, dict) else blk.get("national_mean")
            b_std = getattr(blk, "national_std", None) if not isinstance(blk, dict) else blk.get("national_std")
            if b_code and b_subjs:
                blocks_catalog[str(b_code).upper()] = {
                    "subjects": [normalize_subject_name(s) for s in b_subjs],
                    "national_mean": float(b_mean or 20.0),
                    "national_std": float(b_std or 3.1),
                }

    computed_blocks: Dict[str, Any] = {}
    for b_code, info in blocks_catalog.items():
        req_subjects = [normalize_subject_name(s) for s in info.get("subjects", [])]
        if not req_subjects:
            continue
        if all(sub in norm_grades and norm_grades[sub] is not None for sub in req_subjects):
            subj_scores = {sub: round(float(norm_grades[sub]), 2) for sub in req_subjects}
            raw_sum = sum(subj_scores.values())
            z_val, cdf_val = calculate_z_score_and_cdf(
                raw_total=raw_sum,
                national_mean=float(info.get("national_mean", 20.0)),
                national_std=float(info.get("national_std", 3.1)),
            )
            computed_blocks[b_code] = {
                "block_code": b_code,
                "subjects_used": req_subjects,
                "subject_scores": subj_scores,
                "raw_sum": round(raw_sum, 2),
                "national_mean": float(info.get("national_mean", 20.0)),
                "national_std": float(info.get("national_std", 3.1)),
                "z_score": z_val,
                "score_academic": cdf_val,
            }
    return computed_blocks


def get_major_subject_requirements(
    major_code: str,
    major_name: str,
    category: str = "",
) -> Tuple[float, Dict[str, float]]:
    """
    Trả về ràng buộc điểm tối thiểu cho từng môn theo nhóm ngành đặc thù (TT74/2026):
    - Trả về (min_any_block_subject, {tên_môn_chuẩn: ngưỡng_tối_thiểu}).
    """
    code6 = extract_6digit_code(major_code)
    name_low = (major_name or "").lower()
    min_any = MIN_UNIVERSITY_SUBJECT_FLOOR
    req_subjects: Dict[str, float] = {}

    # 1. Nhóm Sức khỏe (72) - Sàn chất lượng đầu vào Y Dược
    if code6.startswith(("7201", "7202", "7205")) or any(
        k in name_low for k in ("y khoa", "y đa khoa", "răng hàm mặt", "răng - hàm - mặt", "dược học", "y học cổ truyền")
    ):
        min_any = 6.0
        req_subjects["Sinh học"] = 6.0
        req_subjects["Hóa học"] = 6.0
    elif code6.startswith("72"):
        min_any = 5.0

    # 2. Nhóm Đào tạo Giáo viên / Sư phạm (1402 hoặc chứa 'sư phạm')
    elif code6.startswith("1402") or "sư phạm" in name_low or "giáo dục tiểu học" in name_low or "giáo dục mầm non" in name_low:
        min_any = 5.0
        if "toán" in name_low or "tin học" in name_low:
            req_subjects["Toán"] = 6.5
        elif "vật lý" in name_low or "vật lí" in name_low:
            req_subjects["Vật lý"] = 6.5
        elif "hóa học" in name_low:
            req_subjects["Hóa học"] = 6.5
        elif "sinh học" in name_low or "khoa học tự nhiên" in name_low:
            req_subjects["Sinh học"] = 6.0
        elif "ngữ văn" in name_low:
            req_subjects["Ngữ văn"] = 6.5
        elif "lịch sử" in name_low:
            req_subjects["Lịch sử"] = 6.0
        elif "địa lý" in name_low or "địa lí" in name_low:
            req_subjects["Địa lý"] = 6.0
        elif "tiếng anh" in name_low or "ngoại ngữ" in name_low:
            req_subjects["Tiếng Anh"] = 6.5

    # 3. Nhóm Máy tính, Toán học & Kỹ thuật mũi nhọn
    elif any(k in name_low for k in ("khoa học máy tính", "trí tuệ nhân tạo", "khoa học dữ liệu", "vi mạch", "bán dẫn", "toán học", "toán tin")):
        min_any = 4.5
        req_subjects["Toán"] = 6.5
    elif code6.startswith(("48", "46", "5201", "5202")):
        min_any = 4.0
        req_subjects["Toán"] = 5.5

    # 4. Nhóm Ngôn ngữ nước ngoài (2202)
    elif code6.startswith("2202") or name_low.startswith("ngôn ngữ ") or "phiên dịch" in name_low:
        min_any = 4.5
        req_subjects["Tiếng Anh"] = 6.0

    return min_any, req_subjects


def evaluate_subject_constraints_for_block(
    block_code: Optional[str],
    subject_scores: Dict[str, float],
    major_code: str,
    major_name: str,
    category: str = "",
    block_subjects: Optional[List[str]] = None,
) -> List[str]:
    """
    Kiểm tra ràng buộc điểm liệt (<= 1.0đ) và ngưỡng tối thiểu từng môn tiên quyết trên khối thi đã chọn.
    Chỉ kiểm tra các môn thực tế nằm trong khối thi của ngành.
    """
    violations: List[str] = []
    norm_scores = normalize_grades_dict(subject_scores)
    if not norm_scores:
        return violations

    if block_subjects:
        block_subjs = [normalize_subject_name(s) for s in block_subjects]
    elif block_code and block_code in STANDARD_SUBJECT_BLOCKS:
        block_subjs = STANDARD_SUBJECT_BLOCKS[block_code]["subjects"]
    else:
        block_subjs = list(norm_scores.keys())

    min_any, req_subjects = get_major_subject_requirements(major_code, major_name, category)

    # Chỉ kiểm tra điểm liệt (<= 1.0đ) và ngưỡng tối thiểu trên các môn thuộc khối xét tuyển đang xét
    for subj in block_subjs:
        if subj not in norm_scores:
            continue
        sc = float(norm_scores[subj])
        if sc <= FAILING_SUBJECT_THRESHOLD:
            violations.append(f"Vướng điểm liệt môn {subj} ({sc:.1f}đ ≤ 1.0đ)")
        else:
            req_val = max(min_any, req_subjects.get(subj, 0.0))
            if sc < req_val:
                violations.append(f"Môn {subj} ({sc:.1f}đ) chưa đạt ngưỡng tối thiểu {req_val:.1f}đ")

    return violations


def evaluate_academic_readiness_for_major(
    admitted_block_codes: List[str],
    student_block_results: Dict[str, Any],
    default_score: float = 0.5
) -> Tuple[float, Optional[str], Dict[str, Any]]:
    """
    Trụ cột 2: Năng lực học thuật chuẩn hóa Z-Score theo các khối xét tuyển hợp lệ của ngành.
    Tuyệt đối chỉ xét trong danh sách admitted_block_codes, không lấy khối ngoài ngành thay thế.
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
                "score_academic": score_acad,
                "subjects_used": b_data.get("subjects_used", []),
                "subject_scores": b_data.get("subject_scores", {}),
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


# ==========================================
# SOLUTION A: ADAPTIVE DYNAMIC WEIGHTING & COMPACT XAI
# ==========================================

GROUPS = ("riasec", "academic", "cognitive")
BASE_WEIGHTS = {"riasec": 0.45, "academic": 0.35, "cognitive": 0.20}
STRATEGY_MULTIPLIERS = {
    "balanced": {"riasec": 1.0, "academic": 1.0, "cognitive": 1.0},
    "safe_admission": {"riasec": 0.90, "academic": 1.25, "cognitive": 0.95},
    "passion": {"riasec": 1.25, "academic": 0.90, "cognitive": 0.95},
}


def compute_adaptive_weights(
    has_academic_scores: bool = True,
    strategy: str = "balanced",
    category: str = "",
    custom_weights: Optional[Dict[str, float]] = None,
    base_riasec: float = 0.45,
    base_academic: float = 0.35,
    base_preference: float = 0.20,
) -> Dict[str, float]:
    """
    Tính toán trọng số thích ứng tự động (Adaptive Dynamic Weighting):
    1. Khi học sinh chưa có điểm (has_academic_scores=False):
       - Loại bỏ hoàn toàn trụ cột academic khỏi tử số và mẫu số.
       - Tự động tái chuẩn hóa: w_riasec ≈ 0.6923, w_preference ≈ 0.3077 (tổng luôn = 1.0).
       - Ngăn chặn hoàn toàn việc sinh điểm học thuật giả hay suy đoán bừa bãi.
    2. Khi có điểm học tập:
       - Áp dụng hệ số điều chỉnh chiến lược (an toàn đậu đại học vs đam mê bứt phá).
       - Tinh chỉnh theo đặc thù nhóm ngành (Y Dược/Kỹ thuật tăng học thuật; Nghệ thuật/Thiết kế tăng sở thích).
    3. Ràng buộc bảo toàn: Tổng 3 trọng số luôn được chuẩn hóa đúng 1.0.
    """
    if custom_weights:
        total = sum(custom_weights.values())
        if total > 0:
            return {
                "w_riasec": round(custom_weights.get("w_riasec", base_riasec) / total, 4),
                "w_academic": round(custom_weights.get("w_academic", base_academic) / total, 4),
                "w_preference": round(custom_weights.get("w_preference", base_preference) / total, 4),
            }

    strat_key = (strategy or "balanced").lower().strip()
    if any(k in strat_key for k in ("an toàn", "safe", "target")):
        strat = STRATEGY_MULTIPLIERS["safe_admission"]
    elif any(k in strat_key for k in ("đam mê", "bứt phá", "passion", "reach")):
        strat = STRATEGY_MULTIPLIERS["passion"]
    else:
        strat = STRATEGY_MULTIPLIERS.get(strat_key, STRATEGY_MULTIPLIERS["balanced"])

    cat_low = (category or "").lower()
    p_riasec = 1.0
    p_academic = 1.0
    p_pref = 1.0

    if any(k in cat_low for k in ("sức khỏe", "y dược", "máy tính", "bán dẫn", "kỹ thuật")):
        p_academic = 1.15
    elif any(k in cat_low for k in ("nghệ thuật", "thiết kế", "báo chí", "ngôn ngữ", "nhân văn")):
        p_riasec = 1.15

    raw: Dict[str, float] = {}
    raw["riasec"] = base_riasec * strat["riasec"] * p_riasec
    if has_academic_scores:
        raw["academic"] = base_academic * strat["academic"] * p_academic
    else:
        raw["academic"] = 0.0
    raw["cognitive"] = base_preference * strat["cognitive"] * p_pref

    total = sum(raw.values())
    if total <= 0:
        return {"w_riasec": 0.45, "w_academic": 0.35, "w_preference": 0.20}

    return {
        "w_riasec": round(raw["riasec"] / total, 4),
        "w_academic": round(raw["academic"] / total, 4),
        "w_preference": round(raw["cognitive"] / total, 4),
    }


def calculate_3pillar_hybrid_score(
    score_riasec: float,
    score_academic: float,
    score_preference: float,
    w_riasec: float = 0.45,
    w_academic: float = 0.35,
    w_preference: float = 0.20,
    has_academic_scores: Optional[bool] = None,
    strategy: str = "balanced",
    category: str = "",
) -> Tuple[float, Dict[str, float]]:
    """
    Holistic 3-Pillar Adaptive Hybrid Model:
    Score_Major = w_RIASEC * Score_RIASEC + w_Academic * Score_Academic + w_Preference * Score_Preference
    
    Hỗ trợ cả trọng số cố định truyền thống và cơ chế trọng số thích ứng tự động:
    - Khi has_academic_scores=False: Tự động tính adaptive weights (loại bỏ academic, tái chuẩn hóa tổng 1.0).
    - Luôn bảo toàn ràng buộc: w_RIASEC + w_Academic + w_Preference = 1.0 tuyệt đối.
    """
    if has_academic_scores is False:
        adaptive = compute_adaptive_weights(
            has_academic_scores=False,
            strategy=strategy,
            category=category,
            base_riasec=w_riasec,
            base_academic=w_academic,
            base_preference=w_preference,
        )
        w_riasec = adaptive["w_riasec"]
        w_academic = adaptive["w_academic"]
        w_preference = adaptive["w_preference"]
    else:
        total_w = w_riasec + w_academic + w_preference
        if total_w <= 0.0 or abs(total_w - 1.0) > 1e-6:
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


def build_compact_xai_explanation(
    major_name: str,
    score_riasec: float,
    score_academic: float,
    score_pref: float,
    best_block: Optional[str] = None,
    admission_band: str = "UNKNOWN",
    has_academic_scores: bool = True,
) -> str:
    """
    Tạo đoạn giải thích XAI súc tích đúng 3 câu, thân thiện và dễ hiểu cho học sinh THPT:
    1. Vì sao hợp: Nêu bật trụ cột mạnh nhất (Sở thích Holland, Năng lực học tập, hay Tư duy nhận thức).
    2. Khả năng trúng tuyển: Phân tầng tuyển sinh theo khối thi (hoặc nhắc chưa có điểm).
    3. Cần chú ý / Lời khuyên: Chỉ ra trụ cột/môn cần cải thiện để nâng cao cơ hội.
    """
    components = {
        "riasec": score_riasec,
        "academic": score_academic if has_academic_scores else 0.0,
        "cognitive": score_pref,
    }
    labels = {
        "riasec": "thiên hướng sở thích và tính cách nghề nghiệp",
        "academic": f"nền tảng điểm số học tập khối {best_block or 'xét tuyển'}",
        "cognitive": "năng lực tư duy và phong cách học tập",
    }

    eval_comps = {k: v for k, v in components.items() if (has_academic_scores or k != "academic")}
    best_pillar = max(eval_comps, key=eval_comps.get)
    why = f"Ngành {major_name} rất phù hợp với bạn nhờ {labels[best_pillar]} nổi bật."

    if not has_academic_scores or admission_band == "UNKNOWN":
        chance = f"Khả năng trúng tuyển khối {best_block or 'xét tuyển'}: Chưa đủ dữ liệu điểm để ước lượng."
    elif admission_band == "SAFE":
        chance = f"Khả năng trúng tuyển khối {best_block or 'xét tuyển'}: Tương đối an toàn dựa trên điểm chuẩn tham chiếu."
    elif admission_band in ("MATCH", "TARGET"):
        chance = f"Khả năng trúng tuyển khối {best_block or 'xét tuyển'}: Vừa sức trong tầm điểm của bạn."
    elif admission_band == "REACH":
        chance = f"Khả năng trúng tuyển khối {best_block or 'xét tuyển'}: Cần bứt phá thêm điểm số để chắc suất."
    else:
        chance = f"Khả năng trúng tuyển khối {best_block or 'xét tuyển'}: Đang được phân tích."

    if not has_academic_scores:
        advice = "Bạn hãy nhập điểm học bạ hoặc điểm thi thử để nhận đánh giá khả năng trúng tuyển chính xác hơn."
    else:
        weakest_pillar = min(components, key=components.get)
        if components[weakest_pillar] < 0.65:
            advice = f"Bạn nên tập trung cải thiện thêm {labels[weakest_pillar]} để nâng cao cơ hội."
        else:
            advice = "Bạn đang có nền tảng rất vững để tự tin theo đuổi ngành này."

    return f"{why} {chance} {advice}"


def generate_xai_top_supporting_factors(
    major_name: str,
    score_riasec: float,
    student_riasec: Dict[str, float],
    major_riasec: Dict[str, float],
    score_academic: float,
    best_block: Optional[str],
    score_pref: float,
    student_pref: Dict[str, Any],
    major_attr: Dict[str, Any],
    admission_band: str = "UNKNOWN",
    has_academic_scores: bool = True,
) -> Tuple[List[str], str]:
    """
    Generates deterministic, explainable AI (XAI) top supporting factors
    WITHOUT ANY NON-DETERMINISTIC LLM.
    Returns:
    - supporting_factors: Detailed bullet points for breakdown cards.
    - summary_explanation: Compact, 3-sentence user-friendly explanation.
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
    if not has_academic_scores:
        supporting_factors.append(
            "Chưa có dữ liệu điểm học thuật: Đề xuất ưu tiên dựa trên thiên hướng sở thích và tư duy logic."
        )
    elif score_academic >= 0.75:
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

    summary_explanation = build_compact_xai_explanation(
        major_name=major_name,
        score_riasec=score_riasec,
        score_academic=score_academic,
        score_pref=score_pref,
        best_block=best_block,
        admission_band=admission_band,
        has_academic_scores=has_academic_scores,
    )

    return supporting_factors, summary_explanation


# ==========================================
# SOLUTION B: DYNAMIC ACADEMIC CLUSTERING & ADMISSION FEASIBILITY
# ==========================================

def classify_major_academic_benchmark(
    major_code: str,
    major_name: str,
    category: str = "",
    benchmark_override: Optional[float] = None,
    min_recommended_override: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Đánh giá ngưỡng điểm chuẩn tham chiếu và phân tầng cạnh tranh cho từng ngành cấp IV (TT74/2026).
    Hỗ trợ ghi đè nếu ngành có sẵn thông số điểm chuẩn riêng từ CSDL/Excel.
    """
    if benchmark_override is not None and benchmark_override > 0:
        cutoff = round(float(benchmark_override), 2)
        min_rec = round(
            float(min_recommended_override) if min_recommended_override else max(14.0, cutoff - 2.0),
            2,
        )
        tier = "HIGH_COMPETITION" if cutoff >= 24.0 else ("MEDIUM_COMPETITION" if cutoff >= 19.5 else "STANDARD_COMPETITION")
        return {
            "tier": tier,
            "tier_label": f"Điểm chuẩn tham chiếu (~{cutoff}đ)",
            "benchmark_cutoff": cutoff,
            "min_recommended": min_rec,
            "description": "Ngưỡng điểm chuẩn cấu hình trực tiếp theo dữ liệu ngành.",
        }

    name_lower = (major_name or "").lower()
    cat_lower = (category or "").lower()

    # Tầng 1: Cạnh tranh cực cao (Điểm chuẩn thường >= 24.5 - 28.5đ)
    high_keywords = [
        "y khoa", "y đa khoa", "bác sĩ", "răng hàm mặt", "răng - hàm - mặt", "dược học",
        "y học cổ truyền", "khoa học máy tính", "trí tuệ nhân tạo", "khoa học dữ liệu",
        "vi mạch", "bán dẫn", "kinh tế quốc tế", "kinh doanh quốc tế", "tài chính quốc tế",
        "quan hệ quốc tế", "luật kinh tế", "logistics", "chuỗi cung ứng", "truyền thông đa phương tiện",
        "sư phạm toán", "sư phạm ngữ văn", "sư phạm tiếng anh", "sư phạm lịch sử",
        "sư phạm địa lý", "sư phạm địa lí", "sư phạm vật lý", "sư phạm vật lí", "sư phạm hóa học"
    ]
    if any(k in name_lower for k in high_keywords):
        return {
            "tier": "HIGH_COMPETITION",
            "tier_label": "Cạnh tranh cao (~25.5đ)",
            "benchmark_cutoff": 25.5,
            "min_recommended": 23.5,
            "description": "Ngành mũi nhọn với điểm chuẩn đại học thuộc top đầu cả nước."
        }

    # Tầng 2: Cạnh tranh khá (Điểm chuẩn thường 19.5 - 23.5đ)
    medium_keywords = [
        "kỹ thuật xét nghiệm", "kỹ thuật hình ảnh", "phục hồi chức năng", "điều dưỡng",
        "hộ sinh", "dinh dưỡng", "y tế công cộng",
        "công nghệ thông tin", "an toàn thông tin", "kỹ thuật phần mềm", "hệ thống thông tin",
        "mạng máy tính", "kỹ thuật máy tính", "công nghệ tài chính", "fintech",
        "tài chính", "ngân hàng", "kế toán", "kiểm toán", "quản trị kinh doanh",
        "marketing", "thương mại điện tử", "luật", "sư phạm", "giáo dục tiểu học",
        "giáo dục mầm non", "ngôn ngữ anh", "ngôn ngữ trung", "ngôn ngữ nhật",
        "ngôn ngữ hàn", "tâm lý học", "kiến trúc", "thiết kế đồ họa", "quan hệ công chúng"
    ]
    if any(k in name_lower for k in medium_keywords):
        return {
            "tier": "MEDIUM_COMPETITION",
            "tier_label": "Cạnh tranh khá (~21.0đ)",
            "benchmark_cutoff": 21.0,
            "min_recommended": 19.0,
            "description": "Ngành học có tính cạnh tranh khá tại các trường đại học uy tín."
        }

    # Tầng 3: Tiêu chuẩn / Vừa sức (Điểm chuẩn thường 15.0 - 18.5đ)
    standard_keywords = [
        "công nghệ sinh học", "sinh học", "thú y", "chăn nuôi", "nông nghiệp",
        "cây trồng", "lâm nghiệp", "thủy sản", "môi trường", "đất đai", "thực phẩm",
        "vật liệu", "dệt may", "văn phòng", "công tác xã hội", "xã hội học",
        "triết học", "lịch sử", "địa lý", "địa lí", "thống kê", "phát triển",
        "quản lý nhà nước", "công nghệ kỹ thuật"
    ]
    if any(k in name_lower for k in standard_keywords) or any(k in cat_lower for k in standard_keywords):
        return {
            "tier": "STANDARD_COMPETITION",
            "tier_label": "Vừa sức / Tiêu chuẩn (~16.5đ)",
            "benchmark_cutoff": 16.5,
            "min_recommended": 15.0,
            "description": "Ngành đào tạo ứng dụng thực tế, điểm chuẩn phù hợp với mặt bằng phổ thông."
        }

    # Mặc định phổ thông
    return {
        "tier": "STANDARD_COMPETITION",
        "tier_label": "Phổ thông (~18.0đ)",
        "benchmark_cutoff": 18.0,
        "min_recommended": 15.5,
        "description": "Ngành học có phổ điểm tuyển sinh đa dạng theo phân khúc trường."
    }


def evaluate_admission_feasibility(
    raw_block_sum: Optional[float],
    major_code: str,
    major_name: str,
    category: str = "",
    has_matched_block: bool = True,
    best_block: Optional[str] = None,
    raw_grades: Optional[Dict[str, float]] = None,
    admitted_blocks: Optional[List[str]] = None,
    block_subjects: Optional[List[str]] = None,
    benchmark_override: Optional[float] = None,
    min_recommended_override: Optional[float] = None,
    has_academic_data: bool = True,
) -> Dict[str, Any]:
    """
    Đánh giá toàn diện tính khả thi (TARGET / REACH / UNKNOWN) dựa trên 3 tầng ràng buộc:
    1) Không dùng điểm chéo khối xét tuyển (chỉ chấp nhận khối trong admitted_blocks).
    2) Chặn điểm liệt (<= 1.0đ) và ngưỡng tối thiểu từng môn tiên quyết theo nhóm ngành.
    3) Đối chiếu tổng điểm khối hợp lệ với ngưỡng tối thiểu (min_recommended) và điểm chuẩn tham chiếu.

    QUY TẮC CHỐNG BỊA ĐIỂM: nếu học sinh chưa nhập bất kỳ điểm học lực nào
    (has_academic_data=False) thì TUYỆT ĐỐI không suy ra điểm khối, không kết luận
    TARGET/REACH — trả về tier UNKNOWN để giao diện hiển thị "chưa đủ dữ liệu".
    """
    bm = classify_major_academic_benchmark(
        major_code,
        major_name,
        category,
        benchmark_override=benchmark_override,
        min_recommended_override=min_recommended_override,
    )
    cutoff = bm["benchmark_cutoff"]
    min_rec = bm["min_recommended"]

    violations: List[str] = []

    if not has_academic_data:
        return {
            "feasibility_tier": "UNKNOWN",
            "feasibility_label": "Chưa có điểm học lực",
            "benchmark_cutoff": cutoff,
            "min_recommended": min_rec,
            "best_block_score": None,
            "score_gap": None,
            "constraint_passed": False,
            "constraint_violations": [
                "Chưa nhập điểm học lực nên hệ thống không thể xác nhận ngành này đạt hay thiếu điểm chuẩn."
            ],
            "admission_advice": (
                f"Ngành này có điểm chuẩn tham chiếu ~{cutoff}đ. "
                "Hãy nhập điểm các môn học để nhận kết luận TARGET/REACH thay vì phỏng đoán."
            ),
            "academic_tier": bm["tier"],
            "academic_tier_label": bm["tier_label"],
            "has_academic_data": False,
        }

    if not has_matched_block:
        blocks_str = ", ".join(admitted_blocks) if admitted_blocks else "chuyên ngành"
        violations.append(
            f"Chưa có điểm tổ hợp xét tuyển của ngành ({blocks_str}); không lấy điểm khối khác thay thế."
        )
        return {
            "feasibility_tier": "REACH",
            "feasibility_label": "Thiếu tổ hợp xét tuyển",
            "benchmark_cutoff": cutoff,
            "min_recommended": min_rec,
            "best_block_score": None,
            "score_gap": round(-cutoff, 1),
            "constraint_passed": False,
            "constraint_violations": violations,
            "admission_advice": violations[0],
            "academic_tier": bm["tier"],
            "academic_tier_label": bm["tier_label"],
            "has_academic_data": True,
        }

    block_sum = round(float(raw_block_sum if raw_block_sum is not None else 0.0), 2)
    score_gap = round(block_sum - cutoff, 1)

    if raw_grades:
        subj_violations = evaluate_subject_constraints_for_block(
            block_code=best_block,
            subject_scores=raw_grades,
            major_code=major_code,
            major_name=major_name,
            category=category,
            block_subjects=block_subjects,
        )
        violations.extend(subj_violations)

    if block_sum < min_rec:
        deficit = round(min_rec - block_sum, 1)
        violations.append(
            f"Tổng điểm khối {best_block or ''} ({block_sum:.1f}đ) thấp hơn ngưỡng tối thiểu ({min_rec:.1f}đ)."
        )

    constraint_passed = len(violations) == 0

    if not constraint_passed:
        feasibility_tier = "REACH"
        if any("điểm liệt" in v.lower() for v in violations):
            feasibility_label = "Vướng điểm liệt"
        elif any("ngưỡng tối thiểu" in v.lower() or "chuyên ngành" in v.lower() for v in violations) and block_sum >= min_rec:
            feasibility_label = "Chưa đạt môn bắt buộc"
        else:
            gap_abs = abs(score_gap) if score_gap < 0 else round(min_rec - block_sum, 1)
            feasibility_label = f"Thử thách (Thiếu ~{gap_abs}đ)"
        advice = " ".join(violations)
    else:
        feasibility_tier = "TARGET"
        if block_sum >= cutoff:
            feasibility_label = "An toàn / Khả thi cao"
            advice = f"Khối {best_block or 'xét tuyển'} ({block_sum:.1f}đ) vượt điểm chuẩn tham chiếu (~{cutoff}đ) và đạt mọi ngưỡng môn."
        else:
            feasibility_label = "Vừa sức / Khả thi"
            advice = f"Khối {best_block or 'xét tuyển'} ({block_sum:.1f}đ) đạt ngưỡng an toàn tối thiểu (≥ {min_rec}đ, chuẩn ~{cutoff}đ)."

    return {
        "feasibility_tier": feasibility_tier,
        "feasibility_label": feasibility_label,
        "benchmark_cutoff": cutoff,
        "min_recommended": min_rec,
        "best_block_score": block_sum,
        "score_gap": score_gap,
        "constraint_passed": constraint_passed,
        "constraint_violations": violations,
        "admission_advice": advice,
        "academic_tier": bm["tier"],
        "academic_tier_label": bm["tier_label"],
        "has_academic_data": True,
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
    default_score: float = 0.5,
    raw_grades: Optional[Dict[str, float]] = None,
    major_code: str = "",
    major_name: str = "",
    category: str = "",
) -> Tuple[float, Optional[str], Dict[str, Any]]:
    """
    Trụ cột 2 (35%):
    Đánh giá năng lực học thuật theo Z-Score kết hợp ràng buộc ngưỡng điểm chuẩn & môn tiên quyết.
    - Chỉ chấm điểm trên các khối thuộc admitted_block_codes (tuyệt đối không lấy khối ngoài ngành thay thế).
    - Ưu tiên chọn khối thỏa mãn mọi ràng buộc môn (không điểm liệt, đủ điểm sàn môn chuyên ngành).
    - Phạt mạnh điểm học lực nếu thiếu khối, vướng điểm liệt, thiếu môn bắt buộc hoặc dưới min_recommended.
    """
    base_acad, best_block, breakdown = evaluate_academic_readiness_for_major(
        admitted_block_codes, student_block_results, default_score=default_score
    )

    if not student_block_results:
        breakdown["has_matched_block"] = False
        return base_acad, best_block, breakdown

    if not best_block or not isinstance(breakdown, dict) or best_block not in breakdown:
        # Học sinh đã nhập điểm nhưng không có khối nào khớp với tổ hợp xét tuyển của ngành
        breakdown["has_matched_block"] = False
        breakdown["cross_block_blocked"] = True
        breakdown["safety_tier"] = "REACH"
        return 0.15, (admitted_block_codes[0] if admitted_block_codes else None), breakdown

    # Nếu có nhiều khối khớp, ưu tiên khối KHÔNG vi phạm ràng buộc môn/điểm liệt
    norm_raw = normalize_grades_dict(raw_grades)
    candidate_tuples: List[Tuple[bool, float, str, List[str]]] = []
    for b_code, b_info in breakdown.items():
        if not isinstance(b_info, dict) or "raw_sum" not in b_info:
            continue
        merged_scores = dict(norm_raw)
        if isinstance(b_info.get("subject_scores"), dict):
            merged_scores.update(normalize_grades_dict(b_info["subject_scores"]))
        viols = (
            evaluate_subject_constraints_for_block(
                block_code=b_code,
                subject_scores=merged_scores,
                major_code=major_code,
                major_name=major_name,
                category=category,
            )
            if merged_scores
            else []
        )
        b_info["subject_violations"] = viols
        candidate_tuples.append(
            (len(viols) == 0, float(b_info.get("score_academic", 0.5)), b_code, viols)
        )

    if candidate_tuples:
        candidate_tuples.sort(key=lambda t: (1 if t[0] else 0, t[1]), reverse=True)
        _, best_acad, chosen_block, best_violations = candidate_tuples[0]
        best_block = chosen_block
        base_acad = round(best_acad, 4)
    else:
        best_violations = []

    raw_sum = float(breakdown[best_block].get("raw_sum", 18.0))
    gap_to_cutoff = raw_sum - benchmark_cutoff
    gap_to_min = raw_sum - min_recommended

    breakdown["has_matched_block"] = True
    breakdown["subject_violations"] = best_violations
    breakdown["gap_to_cutoff"] = round(gap_to_cutoff, 2)

    if best_violations:
        # Vi phạm điểm liệt hoặc môn tiên quyết -> hạ mạnh điểm học lực và xếp vào REACH
        anchored_score = max(0.08, min(0.28, base_acad * 0.35))
        breakdown["safety_tier"] = "REACH"
        return round(anchored_score, 4), best_block, breakdown

    if gap_to_min >= 0.0:
        if -1.0 <= gap_to_cutoff <= 3.5:
            anchored_score = min(1.0, max(base_acad, 0.82 + 0.04 * max(0.0, gap_to_cutoff + 1.0)))
        elif gap_to_cutoff > 3.5:
            anchored_score = min(1.0, 0.65 * base_acad + 0.35 * 0.86)
        else:
            anchored_score = max(0.65, base_acad)
    else:
        deficit = abs(gap_to_min)
        penalty_factor = max(0.10, 1.0 - (deficit / 10.0) * 0.85)
        anchored_score = max(0.05, base_acad * penalty_factor)

    if raw_sum < min_recommended:
        breakdown["safety_tier"] = "REACH"
    elif raw_sum >= benchmark_cutoff + 1.0:
        breakdown["safety_tier"] = "SAFETY"
    else:
        breakdown["safety_tier"] = "TARGET"

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


def build_radar_and_block_summary(
    student_riasec: Dict[str, float],
    student_zscores: Dict[str, Any],
    raw_grades: Optional[Dict[str, float]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Tổng hợp dữ liệu Radar kép (Sở thích RIASEC vs Học lực thực tế) và khối thi mạnh nhất
    cùng cảnh báo điểm liệt (<= 1.0đ) để trả về nhất quán cho Dashboard.
    """
    norm_grades = normalize_grades_dict(raw_grades)

    def _avg_subjs(s1: str, s2: str, fallback: int) -> int:
        vals = [norm_grades[s] for s in (s1, s2) if s in norm_grades]
        if not vals:
            return fallback
        return max(0, min(100, round((sum(vals) / len(vals)) * 10)))

    radar_meta = [
        ("R", "Thực tế", "Vật lý", "Toán", "Vật lý & Toán", 70),
        ("I", "Nghiên cứu", "Toán", "Hóa học", "Toán & Hóa học", 75),
        ("A", "Nghệ thuật", "Ngữ văn", "Tiếng Anh", "Ngữ văn & Ngoại ngữ", 70),
        ("S", "Xã hội", "Ngữ văn", "Lịch sử", "Ngữ văn & Xã hội", 72),
        ("E", "Quản lý", "Tiếng Anh", "Toán", "Tiếng Anh & Toán", 72),
        ("C", "Nghiệp vụ", "Toán", "Tin học / Công nghệ", "Toán & Tin học", 74),
    ]

    riasec_data: List[Dict[str, Any]] = []
    for key, label, s1, s2, subj_label, fb in radar_meta:
        interest_pct = max(0, min(100, round(float(student_riasec.get(key, 0.5)) * 100)))
        acad_pct = _avg_subjs(s1, s2, interest_pct if norm_grades else fb)
        riasec_data.append({
            "key": key,
            "label": label,
            "value": interest_pct,
            "academicValue": acad_pct,
            "subjectMapping": subj_label,
            "fullMark": 100,
        })

    # Xác định khối thi mạnh nhất từ toàn bộ khối học sinh có đủ điểm
    best_block_info: Dict[str, Any] = {
        "block": "Chưa xác định",
        "raw_sum": None,
        "z_score": "+0.00",
        "percentile": "Chưa có điểm",
        "failing_subjects": [],
    }
    if norm_grades:
        best_block_info["failing_subjects"] = [
            f"{s} ({v:.1f}đ)" for s, v in norm_grades.items() if v <= FAILING_SUBJECT_THRESHOLD
        ]

    if student_zscores:
        best_entry = max(
            (v for v in student_zscores.values() if isinstance(v, dict) and "raw_sum" in v),
            key=lambda v: (float(v.get("raw_sum", 0.0)), float(v.get("z_score", 0.0))),
            default=None,
        )
        if best_entry:
            z = float(best_entry.get("z_score", 0.0))
            pct_str = (
                "Top 10%" if z >= 1.28 else (
                    "Top 20%" if z >= 0.84 else (
                        "Top 35%" if z >= 0.38 else (
                            "Top 50%" if z >= 0.0 else "Cần bứt phá"
                        )
                    )
                )
            )
            best_block_info.update({
                "block": f"Khối {best_entry.get('block_code', 'A00')}",
                "raw_sum": round(float(best_entry.get("raw_sum", 0.0)), 2),
                "z_score": f"{'+' if z >= 0 else ''}{z:.2f}",
                "percentile": pct_str,
            })

    return riasec_data, best_block_info

