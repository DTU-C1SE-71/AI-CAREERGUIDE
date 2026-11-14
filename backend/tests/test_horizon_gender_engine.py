import pytest
from app.services.recommender.horizon_gender_engine import (
    get_grade_horizon_config,
    compute_gender_ergonomic_adjustment,
    apply_horizon_gender_reranking,
    build_horizon_gender_xai_explanation,
    audit_cohort_gender_fairness,
)
from app.schemas.recommender import MajorRecommendationItem
import uuid


def test_grade_horizon_configuration_tau_and_deltas():
    c10 = get_grade_horizon_config("Lớp 10")
    assert c10["tau"] == 1.00
    assert c10["delta_reach_max"] == 3.5
    assert c10["w_riasec"] > c10["w_academic"]

    c11 = get_grade_horizon_config("Lớp 11")
    assert c11["tau"] == 0.65
    assert c11["delta_reach_max"] == 2.6

    c12 = get_grade_horizon_config("Lớp 12")
    assert c12["tau"] == 0.25
    assert c12["delta_reach_max"] == 1.2
    assert c12["w_academic"] >= 0.40

    c_grad = get_grade_horizon_config("Đã tốt nghiệp cấp 3")
    assert c_grad["tau"] == 0.15
    assert c_grad["delta_reach_max"] == 1.0


def test_gender_ergonomic_zero_penalty_and_affirmative_nudges():
    # Female in Computer Science (STEM)
    boost, adv, badge, ergo = compute_gender_ergonomic_adjustment(
        gender="Nữ",
        major_code="7480101",
        major_name="Khoa học máy tính",
        major_category="Máy tính và công nghệ thông tin",
        score_riasec=0.85,
        score_academic=0.80,
        riasec_dict={"I": 0.85, "R": 0.60, "A": 0.40, "S": 0.30, "E": 0.40, "C": 0.50},
        grade_level="Lớp 12",
    )
    assert boost >= 0.0, "Zero-Penalty Invariant violated"
    assert badge == "Khuyến khích Nữ sinh STEM & Công nghệ"

    # Male in Nursing (Care)
    boost_m, adv_m, badge_m, _ = compute_gender_ergonomic_adjustment(
        gender="Nam",
        major_code="7720301",
        major_name="Điều dưỡng",
        major_category="Sức khỏe",
        score_riasec=0.75,
        score_academic=0.70,
        riasec_dict={"I": 0.40, "R": 0.30, "A": 0.30, "S": 0.80, "E": 0.40, "C": 0.50},
        grade_level="Lớp 12",
    )
    assert boost_m >= 0.0
    assert badge_m == "Khuyến khích Nam sinh Giáo dục & Y tế"

    # Statutory Hazard: Mining Engineering (7520601)
    boost_h, adv_h, badge_h, _ = compute_gender_ergonomic_adjustment(
        gender="Nữ",
        major_code="7520601",
        major_name="Kỹ thuật Mỏ",
        major_category="Kỹ thuật",
        score_riasec=0.70,
        score_academic=0.70,
        riasec_dict={"R": 0.70},
        grade_level="Lớp 12",
    )
    assert adv_h is not None
    assert "Thông tư 10/2020" in adv_h
    assert "Thiết kế mỏ" in adv_h or "Trắc địa mỏ" in adv_h


def test_horizon_reranking_decoupled_gatekeeper_and_grade_adaptation():
    def _create_item(code, name, cat, overall, riasec, gap, tier="TARGET"):
        return MajorRecommendationItem(
            rank=0,
            major_id=uuid.uuid4(),
            major_code=code,
            major_name=name,
            category=cat,
            overall_score=overall,
            score_riasec=riasec,
            score_academic=0.8,
            score_preference=0.7,
            score_gap=gap,
            feasibility_tier=tier,
            score_breakdown={},
            explanation="Test explanation",
        )

    # 1 item TARGET, 1 item REACH gap -1.0 (feasible for all), 1 item REACH gap -2.5 (feasible for Grade 10, unrealistic for Grade 12), 1 item deficit -4.5 (unrealistic for all)
    items = [
        _create_item("7480101", "Khoa học máy tính", "CNTT", 0.90, 0.90, 1.0, "TARGET"),
        _create_item("7480107", "Trí tuệ nhân tạo", "CNTT", 0.92, 0.95, -1.0, "REACH"),
        _create_item("7480201", "An toàn thông tin", "CNTT", 0.93, 0.95, -2.5, "REACH"),
        _create_item("7480104", "Hệ thống thông tin", "CNTT", 0.95, 0.95, -4.5, "REACH"),
        _create_item("7520201", "Kỹ thuật điện", "Kỹ thuật", 0.88, 0.80, 2.5, "TARGET"),
        _create_item("7520216", "Kỹ thuật điều khiển", "Kỹ thuật", 0.87, 0.80, 1.5, "TARGET"),
        _create_item("7340101", "Quản trị kinh doanh", "Kinh doanh", 0.85, 0.70, 3.0, "TARGET"),
    ]

    # Grade 12 evaluation: delta_reach_max = 1.2
    # Item 7480201 (-2.5) and 7480104 (-4.5) MUST be isolated as UNREALISTIC and excluded from top_k
    recs_12 = apply_horizon_gender_reranking(
        scored_items=list(items),
        grade_level="Lớp 12",
        gender="Nam",
        top_k=5,
        has_academic_scores=True,
    )
    rec_codes_12 = [m.major_code for m in recs_12]
    assert "7480104" not in rec_codes_12, "Unrealistic major (-4.5) must be isolated"
    assert "7480201" not in rec_codes_12, "Major with deficit -2.5 must exceed Grade 12 delta_max 1.2"
    # Grade 12 top 5 should all be realistic TARGETs
    assert recs_12[0].feasibility_tier == "TARGET"

    # Grade 10 evaluation: delta_reach_max = 3.5
    # Item 7480201 (-2.5) IS ELIGIBLE as a long-term stretch target (REACH)!
    recs_10 = apply_horizon_gender_reranking(
        scored_items=list(items),
        grade_level="Lớp 10",
        gender="Nam",
        top_k=5,
        has_academic_scores=True,
    )
    rec_codes_10 = [m.major_code for m in recs_10]
    assert "7480201" in rec_codes_10, "Grade 10 with 3 years left should allow stretch target (-2.5 deficit)"
    assert "7480104" not in rec_codes_10, "Deficit -4.5 > 3.5 must still be excluded"


def test_cohort_fairness_audit():
    mock_logs = [
        {"gender": "Nữ", "top_recommendations": [{"major_code": "7480101", "category": "MÁY TÍNH VÀ CÔNG NGHỆ THÔNG TIN"}]},
        {"gender": "Nữ", "top_recommendations": [{"major_code": "7340101", "category": "KINH DOANH"}]},
        {"gender": "Nam", "top_recommendations": [{"major_code": "7480101", "category": "MÁY TÍNH VÀ CÔNG NGHỆ THÔNG TIN"}]},
        {"gender": "Nam", "top_recommendations": [{"major_code": "7340101", "category": "KINH DOANH"}]},
    ]
    audit = audit_cohort_gender_fairness(mock_logs)
    assert audit["is_fair"] is True
    assert 0.80 <= audit["disparate_impact_ratio"] <= 1.25
    assert audit["status"] == "PASS"
