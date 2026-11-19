"""Tests for PA 3: Item-level Sub-facet Affinity & Asymmetric Veto Gate."""
import pytest

from app.schemas.recommender import RecommendationRequest
from app.services.recommender.subfacet_gate import evaluate_subfacet_gate, extract_item_ratings
from app.services.recommender.service import (
    build_two_tier_funnel_from_items,
    calculate_3pillar_recommendations,
)


def _full_artistic_hate_music_answers() -> dict:
    """Student strongly loves Design/Architecture/Media (A1/A2/A3/A5=5) but hates Music (A4=1)."""
    answers = {f"{g}{i}": 2 for g in ("R", "I", "S", "E", "C") for i in range(1, 6)}
    answers.update({"A1": 5, "A2": 5, "A3": 5, "A4": 1, "A5": 5})
    return answers


def test_subfacet_gate_music_veto_vs_design_boost():
    answers = _full_artistic_hate_music_answers()

    music_gate = evaluate_subfacet_gate("7210205", "Thanh nhạc", answers)
    assert music_gate["status"] == "STRONG_VETO"
    assert music_gate["overall_multiplier"] == 0.45
    assert music_gate["riasec_multiplier"] == 0.30
    assert "A4" in (music_gate["note"] or "")

    design_gate = evaluate_subfacet_gate("7210403", "Thiết kế đồ họa", answers)
    assert design_gate["status"] == "AFFINITY_BOOST"
    assert design_gate["overall_boost"] > 0
    assert "A1" in (design_gate["note"] or "")


def test_interdisciplinary_strictest_veto_wins_for_music_pedagogy():
    answers = {f"{g}{i}": 3 for g in ("R", "I", "A", "S", "E", "C") for i in range(1, 6)}
    answers["S1"] = 5  # Loves teaching
    answers["A4"] = 1  # Strongly dislikes music

    music_edu = evaluate_subfacet_gate("7140221", "Sư phạm Âm nhạc", answers)
    assert music_edu["status"] == "STRONG_VETO"
    assert "A4" in (music_edu["note"] or "")

    math_edu = evaluate_subfacet_gate("7140209", "Sư phạm Toán học", answers)
    assert math_edu["status"] in ("AFFINITY_BOOST", "NEUTRAL")


def test_soft_penalty_and_other_domain_pairs_and_numeric_keys():
    # Numeric index 13 == A4 (R:0..4, I:5..9, A:10..14 -> A4 is index 13)
    numeric_ratings = extract_item_ratings({"13": 2})
    assert numeric_ratings["A4"] == 2
    soft = evaluate_subfacet_gate("7210201", "Âm nhạc học", {"13": 2})
    assert soft["status"] == "SOFT_PENALTY"
    assert soft["overall_multiplier"] == 0.78

    # Loves IT (I2=5), strongly dislikes Medicine/Bio (I3=1)
    tech_answers = {"I2": 5, "I3": 1, "R1": 5, "R3": 1}
    assert evaluate_subfacet_gate("7480101", "Khoa học máy tính", tech_answers)["status"] == "AFFINITY_BOOST"
    assert evaluate_subfacet_gate("7720101", "Y khoa", tech_answers)["status"] == "STRONG_VETO"
    assert evaluate_subfacet_gate("7640101", "Thú y", tech_answers)["status"] == "STRONG_VETO"

    # Legacy profiles without raw answers remain strictly NEUTRAL
    assert evaluate_subfacet_gate("7210205", "Thanh nhạc", None)["status"] == "NEUTRAL"
    assert evaluate_subfacet_gate("7210205", "Thanh nhạc", {})["status"] == "NEUTRAL"


@pytest.mark.asyncio
async def test_e2e_recommender_never_recommends_music_when_a4_is_1():
    answers = _full_artistic_hate_music_answers()
    inline_profile = {
        "riasec_answers": answers,
        "grades_by_subject": {"Toán": 8.5, "Ngữ văn": 8.5, "Tiếng Anh": 8.5},
        "cognitive_preferences": {
            "COG_1": "A", "COG_2": "A", "COG_3": "A", "COG_4": "A",
            "COG_5": "A", "COG_6": "A", "COG_7": "A", "COG_8": "A",
        },
        "grade_level": "Lớp 12",
        "gender": "Nữ",
    }
    result = await calculate_3pillar_recommendations(
        db=None,
        user_id=None,
        payload=RecommendationRequest(top_k=500),
        inline_profile=inline_profile,
        include_all_candidates=True,
        raise_if_unassessed=False,
        persist_history=False,
    )

    top15 = result.recommendations[:15]
    assert top15, "Expected recommendations from seed catalog"
    for item in top15:
        assert not item.major_code.startswith("72102"), (
            f"Vetoed Music major {item.major_code} ({item.major_name}) leaked into Top 15!"
        )

    funnel = build_two_tier_funnel_from_items(
        result.recommendations,
        grade_level="Lớp 12",
        top_fields=5,
        majors_per_field=5,
    )
    for field in funnel["tier1_fields"]:
        for m in field["majors"]:
            assert not m.major_code.startswith("72102"), (
                f"Vetoed Music major {m.major_code} ({m.major_name}) leaked into funnel field {field['field_name']}!"
            )
    for m in funnel["all_majors"]:
        assert not m.major_code.startswith("72102")
