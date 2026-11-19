"""Counterfactual tests for evidence, ranking, and aspiration scoring."""
from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.schemas.recommender import RecommendationRequest
from app.services.recommender.evidence import cognitive_evidence, _cognitive_questions, score_observed_pillars, aspiration_preference_evidence
from app.services.recommender.service import calculate_3pillar_recommendations


def test_cognitive_missing_partial_and_invalid_answers_do_not_create_traits():
    assert cognitive_evidence({})["traits"] == {}
    answers = {q["code"]: q["options"][0]["option_key"] for q in _cognitive_questions()}
    assert cognitive_evidence(answers)["status"] == "COMPLETE"
    answers.pop(next(iter(answers)))
    assert cognitive_evidence(answers)["status"] == "PARTIAL"
    assert cognitive_evidence(answers)["traits"] == {}
    q = _cognitive_questions()[0]
    assert cognitive_evidence({q["code"]: "invalid", q["dimension_key"]: q["options"][0]["option_key"]})["answered"] == 0


def test_strategy_changes_observed_weights_without_reviving_absent_evidence():
    base = {"w_riasec": .45, "w_academic": .35, "w_preference": .2}
    observed = {"w_riasec": True, "w_academic": True, "w_preference": False}
    scores = {"w_riasec": 1, "w_academic": .3, "w_preference": 1}
    safe, sw = score_observed_pillars(scores, observed, base, "REALISTIC_SAFE")
    stretch, tw = score_observed_pillars(scores, observed, base, "CHALLENGE_TOP")
    assert safe < stretch
    assert sw["w_academic"] > tw["w_academic"]
    assert sw["w_preference"] == tw["w_preference"] == 0
    assert sum(sw.values()) == pytest.approx(1)
    zero, zw = score_observed_pillars(scores, dict.fromkeys(base, False), base, "CHALLENGE_TOP")
    assert zero == 0 and sum(zw.values()) == 0


@pytest.mark.parametrize("weights", [{"w_riasec": True}, {"w_academic": float("nan")}, {"w_academic": -1}, {"foo": 1}, {"w_riasec": "1"}, {"w_riasec": 0}])
def test_invalid_custom_weights_rejected(weights):
    with pytest.raises(ValidationError):
        RecommendationRequest(custom_weights=weights)


def test_values_require_declared_catalog_evidence():
    aspiration = {"work_values": ["HIGH_INCOME_GROWTH"], "preferred_environment": "structured"}
    unsupported = aspiration_preference_evidence(aspiration, {})
    assert unsupported["score"] is None
    assert unsupported["work_values"]["status"] == "UNSUPPORTED_CATALOG"
    matching = aspiration_preference_evidence(aspiration, {"work_values": ["HIGH_INCOME_GROWTH"], "learning_environment": "structured"})
    different = aspiration_preference_evidence(aspiration, {"work_values": ["SOCIAL_IMPACT"], "learning_environment": "collaborative"})
    assert matching["score"] == 1 and different["score"] == 0


def major(code, cutoff=None):
    row = {"major_code": code, "name": "Ngành " + code, "category": "Khác", "blocks": ["D01"], "riasec": {"E": 1}, "cognitive": {}}
    if cutoff is not None:
        row["readiness_reference"] = {"id": "fixture", "kind": "ACADEMIC_POLICY", "verified": True,
            "source": "test-only", "expectedScoreKind": "TRANSCRIPT", "calculationMethod": "SUM_THREE_SUBJECTS",
            "admittedBlocks": ["D01"], "cutoff": cutoff, "minimum": cutoff}
    return row


@pytest.mark.asyncio
async def test_readiness_before_top_k_and_no_gender_strategy_bypass(monkeypatch):
    from app.services.taxonomy import service as taxonomy
    monkeypatch.setattr(taxonomy, "load_seed_majors", lambda: [major("7340101", 28), major("7340102", 20)])
    for strategy in ("CHALLENGE_TOP", "REALISTIC_SAFE", "FLEXIBLE_PATHWAY"):
        for gender in ("male", "female"):
            response = await calculate_3pillar_recommendations(None, uuid4(), RecommendationRequest(top_k=1, gender=gender),
                inline_profile={"grades_by_subject": {"Toán": 8, "Ngữ văn": 8, "Tiếng Anh": 8},
                    "aspiration": {"score_strategy": strategy}}, persist_history=False)
            assert [x.major_code for x in response.recommendations] == ["7340102"]
            item = response.recommendations[0]
            assert item.readiness["status"] == "READY_REFERENCE"
            assert item.fit["interest"] is None and item.fit["cognitive"] is None
            assert item.score_breakdown["weights"]["w_academic"] == 1
            assert item.gaps == []


@pytest.mark.asyncio
async def test_empty_profile_never_manufactures_fit_or_eligibility(monkeypatch):
    from app.services.taxonomy import service as taxonomy
    monkeypatch.setattr(taxonomy, "load_seed_majors", lambda: [major("7340101")])
    response = await calculate_3pillar_recommendations(None, uuid4(), RecommendationRequest(), inline_profile={}, persist_history=False)
    item = response.recommendations[0]
    assert item.match is None
    assert all(value is None for value in item.fit.values())
    assert item.feasibility_tier == "UNKNOWN" and not item.constraint_passed
    assert item.overall_score == 0 and item.score_preference == 0
    assert item.gaps == []


@pytest.mark.asyncio
async def test_saved_explicit_empty_cognition_cannot_revive_legacy_default_traits():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from app.services.recommender.service import resolve_assessment_evidence
    legacy = {"abstract_thinking": "high", "analytical_reasoning": "high", "spatial_perception": "high", "linguistic_ability": "high", "learning_environment": "structured", "teamwork_intensity": "balanced"}
    row = SimpleNamespace(id=uuid4(), raw_responses={"cognitive": {}}, cognitive_preferences=legacy, riasec_scores={})
    db = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: row))))
    profile = await resolve_assessment_evidence(db, uuid4(), {"assessment_id": row.id})
    assert profile["cognitive_preferences"] == {}
    assert cognitive_evidence(profile["cognitive_preferences"])["status"] == "MISSING"


@pytest.mark.asyncio
async def test_missing_profile_field_score_remains_unknown(monkeypatch):
    from app.services.taxonomy import service as taxonomy
    from app.services.recommender.service import evaluate_dashboard_profile_bundle
    monkeypatch.setattr(taxonomy, "load_seed_majors", lambda: [major("7340101")])
    bundle = await evaluate_dashboard_profile_bundle(None, uuid4(), inline_profile={})
    assert bundle["funnel"]["tier1_fields"][0]["match"] is None


@pytest.mark.asyncio
async def test_neutral_or_partial_interests_never_publish_high_suitability_with_high_grades():
    from app.services.recommender.service import calculate_3pillar_recommendations
    from app.schemas.recommender import RecommendationRequest
    profile={"riasec_answers":{f"{g}{i}":3 for g in "RIASEC" for i in range(1,6)},
             "grades_by_subject":{"Toán":9.9,"Vật lí":9.9,"Hóa học":9.9,"Tiếng Anh":9.9},
             "cognitive_preferences":{"abstract_thinking":"high","analytical_reasoning":"high","spatial_perception":"high","linguistic_ability":"high","learning_environment":"structured","teamwork_intensity":"balanced"},"aspiration":{}}
    result=await calculate_3pillar_recommendations(None,None,RecommendationRequest(top_k=3),profile,persist_history=False)
    assert result.recommendations
    assert all(m.match is None for m in result.recommendations)
    assert all(m.fit["academic"] is not None for m in result.recommendations)
    profile["riasec_answers"].update({f"I{i}":5 for i in range(1,6)})
    changed=await calculate_3pillar_recommendations(None,None,RecommendationRequest(top_k=3),profile,persist_history=False)
    assert all(m.match is not None for m in changed.recommendations)
