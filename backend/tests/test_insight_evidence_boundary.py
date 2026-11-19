import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.schemas.insight import StudentSkillAnalysisRequest
from app.services.major_insight import service
from app.services.gap_roadmap_engine.gap_engine import infer_mastered_skills_from_diagnostic_tests
from app.services.gap_roadmap_engine.service import generate_static_fallback_roadmap, get_student_major_skill_gaps


@pytest.mark.anyio
@pytest.mark.parametrize("owner,requested,assessment,expected", [
    (None, uuid.uuid4(), None, 401),
    (uuid.uuid4(), uuid.uuid4(), None, 403),
    (None, None, uuid.uuid4(), 401),
])
async def test_skill_owner_rejected_before_database(owner, requested, assessment, expected):
    db = AsyncMock()
    with pytest.raises(HTTPException) as error:
        await service.analyze_student_skills(db, StudentSkillAnalysisRequest(user_id=requested, assessment_id=assessment), owner)
    assert error.value.status_code == expected
    db.execute.assert_not_awaited()


@pytest.mark.anyio
async def test_explicit_nulls_are_empty_evidence():
    result = await service.analyze_student_skills(None, StudentSkillAnalysisRequest(
        riasec_answers=None, riasec_scores=None, grades_by_subject=None,
        cognitive_answers=None, cognitive_preferences=None, aspiration=None, score_context=None))
    assert result.strengths == []
    assert result.weaknesses == []
    assert result.skill_gaps == []
    assert not result.is_ai_generated


@pytest.mark.anyio
async def test_skill_cache_hash_tracks_owner_catalog_context_and_raw_answers(monkeypatch):
    context = {"name": "Ngành A", "description": "V1"}
    monkeypatch.setattr(service, "_load_major_context", AsyncMock(side_effect=lambda *_: dict(context)))
    payload = StudentSkillAnalysisRequest(major_code="7480101", riasec_answers={"I1": 3}, grades_by_subject={}, aspiration={})
    first = await service.analyze_student_skills(None, payload)
    same = await service.analyze_student_skills(None, payload)
    assert first.profile_hash == same.profile_hash
    context["description"] = "V2"
    changed = await service.analyze_student_skills(None, payload)
    other_owner = await service.analyze_student_skills(None, payload, uuid.uuid4())
    other_answers = await service.analyze_student_skills(None, payload.model_copy(update={"riasec_answers": {"I1": 4}}))
    assert len({first.profile_hash, changed.profile_hash, other_owner.profile_hash, other_answers.profile_hash}) == 4


def test_diagnostics_require_scale_and_honor_explicit_verdict():
    cases = [
        {"skill_code": "ambiguous", "score": .8},
        {"skill_code": "failed", "score": 10, "score_scale": 10, "is_passed": False},
        {"skill_code": "passed", "score": 0, "is_passed": True},
        {"skill_code": "scaled", "score": .8, "score_scale": 1},
        {"skill_code": "boolean", "score": True, "score_scale": 1},
        {"skill_code": "nan", "score": float("nan"), "score_scale": 10},
        {"skill_code": "oversized", "score": 99, "score_scale": 10},
        {"skill_code": "string", "is_passed": "true"},
    ]
    assert infer_mastered_skills_from_diagnostic_tests(cases) == {"passed", "scaled"}


def test_roadmap_template_has_no_fabricated_sources():
    result = generate_static_fallback_roadmap("7480101", "Khoa học máy tính")
    assert result["reference_materials"] == []
    assert result["source_url"] == ""
    assert "chưa" in result["source_title"]


@pytest.mark.anyio
async def test_grades_do_not_confirm_mastery_and_undeclared_skills_are_unknown():
    major = SimpleNamespace(name="Ngành thử", major_skills=[])
    grade = SimpleNamespace(grades_by_subject={"Toán": 9})
    results = [SimpleNamespace(scalar_one_or_none=lambda: major),
               # Snapshot query precedes legacy grades when no current snapshot exists.
               SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: None)),
               SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: grade)),
               SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [])),
               SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))]
    db = AsyncMock()
    db.execute.side_effect = results
    result = await get_student_major_skill_gaps(db, uuid.uuid4(), "7480101")
    assert result["mastered_skills"] == []
    assert "SKILL_PRE_CALCULUS" in result["suggested_foundation"]
    assert result["requirements_status"] == "UNKNOWN"
    assert result["skill_evidence_status"] == "UNASSESSED"
    assert "chưa thể kết luận" in result["readiness_summary"]
