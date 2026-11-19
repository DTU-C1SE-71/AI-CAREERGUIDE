"""@blast-radius: core, api, db, integration
Legacy aliases phải bảo toàn bằng chứng và lịch sử giống luồng modular.
"""
import uuid
import pytest
from pydantic import ValidationError
from sqlalchemy import select
from app.models.identity import User, UserRole
from app.models.assessment import StudentAssessment, StudentDiagnosticTest
from app.schemas.assessment import RIASECAssessmentSubmit, CognitivePreferenceSubmit, GradeEntrySubmit, DiagnosticCheckInput
from app.services.assessment import service
from app.services.recommender.service import resolve_assessment_evidence


async def seed_user(db):
    user = User(email=f"{uuid.uuid4()}@example.test", hashed_password="synthetic-no-login", full_name="Học sinh tổng hợp", role=UserRole.STUDENT)
    db.add(user)
    await db.commit()
    return user


@pytest.mark.asyncio
async def test_partial_riasec_keeps_unknown_dimensions_missing(ai_runtime_db):
    db = ai_runtime_db
    user = await seed_user(db)
    result = await service.save_riasec_assessment(db, user.id, RIASECAssessmentSubmit(raw_responses={"R1": 5}))
    assert result.riasec_scores == {"R": 1.0}
    assert result.raw_responses["riasec"] == {"R1": 5}


@pytest.mark.asyncio
async def test_cognitive_only_does_not_create_invented_riasec_or_preferences(ai_runtime_db):
    user = await seed_user(ai_runtime_db)
    result = await service.save_cognitive_preferences(ai_runtime_db, user.id, CognitivePreferenceSubmit(abstract_thinking="high"))
    assert result.riasec_scores == {}
    assert result.cognitive_preferences == {"abstract_thinking": "high"}


@pytest.mark.asyncio
async def test_legacy_updates_create_new_coherent_snapshot_without_mutating_history(ai_runtime_db):
    db = ai_runtime_db
    user = await seed_user(db)
    first = await service.save_riasec_assessment(db, user.id, RIASECAssessmentSubmit(raw_responses={"R1": 5}))
    second = await service.save_cognitive_preferences(db, user.id, CognitivePreferenceSubmit(abstract_thinking="high"))
    assert second.id != first.id
    await db.refresh(first)
    assert first.cognitive_preferences == {}
    assert second.riasec_scores == {"R": 1.0}
    await service.process_and_save_grades(db, user.id, GradeEntrySubmit(grades={"Toán": 9.123456, "Vật lý": 8.0, "Hóa học": 7.0}))
    current = await resolve_assessment_evidence(db, user.id)
    assert current["grades_by_subject"]["Toán"] == 9.123456
    assert current["cognitive_preferences"] == {"abstract_thinking": "high"}
    historical = await resolve_assessment_evidence(db, user.id, {"assessment_id": first.id})
    assert historical["grades_by_subject"] == {}
    await service.process_and_save_grades(db, user.id, GradeEntrySubmit(grades={}))
    cleared = await resolve_assessment_evidence(db, user.id)
    assert cleared["grades_by_subject"] == {}
    profile = await service.get_student_profile(db, user.id)
    assert profile["raw_grades"] == {} and profile["riasec_vector"] == {"R": 1.0}
    assert len((await db.execute(select(StudentAssessment).where(StudentAssessment.user_id == user.id))).scalars().all()) == 4


@pytest.mark.parametrize("data", [{"raw_responses": {"R1": True}}, {"raw_responses": {"R1": "5"}}, {"raw_responses": {"R1": 6}}, {"raw_responses": {"R1": 2, "1-0": 5}}, {"raw_responses": {"garbage": 3}}])
def test_invalid_likert_or_conflicting_aliases_rejected(data):
    with pytest.raises(ValidationError):
        RIASECAssessmentSubmit(**data)


@pytest.mark.parametrize("grades", [{"Toán": True}, {"Toán": "9"}, {"Toán": 11}, {"Toán": float("nan")}, {"Toán": 8, "math": 9}])
def test_grades_reject_non_numeric_and_conflicting_aliases(grades):
    with pytest.raises(ValidationError):
        GradeEntrySubmit(grades=grades)


@pytest.mark.asyncio
async def test_transcript_never_becomes_mastered_skill(ai_runtime_db):
    user = await seed_user(ai_runtime_db)
    await service.process_and_save_grades(ai_runtime_db, user.id, GradeEntrySubmit(grades={"Toán": 10, "Tin học": 10, "Tiếng Anh": 10}))
    profile = await service.get_student_profile(ai_runtime_db, user.id)
    assert profile["diagnostic_skills_mastered"] == []
    check = DiagnosticCheckInput(skill_code="SKILL_SYNTHETIC", score=0.8)
    assert check.score_scale == 10


@pytest.mark.asyncio
async def test_clearing_interest_and_cognitive_never_revives_older_snapshot(ai_runtime_db):
    user = await seed_user(ai_runtime_db)
    await service.save_riasec_assessment(ai_runtime_db, user.id, RIASECAssessmentSubmit(raw_responses={"R1": 5}))
    await service.save_cognitive_preferences(ai_runtime_db, user.id, CognitivePreferenceSubmit(abstract_thinking="high"))
    await service.save_riasec_assessment(ai_runtime_db, user.id, RIASECAssessmentSubmit(raw_responses={}))
    await service.save_cognitive_preferences(ai_runtime_db, user.id, CognitivePreferenceSubmit())
    current = await resolve_assessment_evidence(ai_runtime_db, user.id)
    assert current["riasec_answers"] == {} and current["riasec_scores"] == {}
    assert current["cognitive_preferences"] == {}


@pytest.mark.asyncio
async def test_explicit_diagnostic_scale_and_catalog_identity(ai_runtime_db):
    from app.models.taxonomy import Skill, SkillType
    from app.schemas.assessment import DiagnosticCheckBatchSubmit
    from fastapi import HTTPException
    db = ai_runtime_db
    user = await seed_user(db)
    db.add(Skill(skill_code="SKILL_SYNTHETIC", name="Kỹ năng tổng hợp", skill_type=SkillType.PREREQUISITE, domain="Test"))
    await db.commit()
    low = await service.save_diagnostic_skill_checks(db, user.id, DiagnosticCheckBatchSubmit(checks=[DiagnosticCheckInput(skill_code="SKILL_SYNTHETIC", score=.8)]))
    assert low[0].score == .08 and low[0].is_passed is False
    high = await service.save_diagnostic_skill_checks(db, user.id, DiagnosticCheckBatchSubmit(checks=[DiagnosticCheckInput(skill_code="SKILL_SYNTHETIC", score=.8, score_scale=1)]))
    assert high[0].score == .8 and high[0].is_passed is True
    with pytest.raises(HTTPException) as exc:
        await service.save_diagnostic_skill_checks(db, user.id, DiagnosticCheckBatchSubmit(checks=[DiagnosticCheckInput(skill_code="INVENTED", score=10)]))
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_active_questionnaire_does_not_restore_file_when_db_empty_or_failed(ai_runtime_db):
    from app.modules.assessment.service import get_active_questionnaire_set
    from fastapi import HTTPException
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from sqlalchemy.exc import OperationalError
    with pytest.raises(HTTPException) as empty:
        await get_active_questionnaire_set(ai_runtime_db)
    assert empty.value.status_code == 404
    failed = SimpleNamespace(execute=AsyncMock(side_effect=OperationalError("SELECT", {}, Exception("synthetic-db-private"))))
    with pytest.raises(HTTPException) as unavailable:
        await get_active_questionnaire_set(failed)
    assert unavailable.value.status_code == 503
    assert "synthetic-db-private" not in unavailable.value.detail
    assert (await get_active_questionnaire_set(None)).riasec_questions


@pytest.mark.parametrize("grades", [{"math": 8.125, "physics": 8.125, "chemistry": 8.125}, {"Toán": 8.125, "Vật lí": 8.125, "Hóa học": 8.125}])
def test_profile_blocks_share_normalized_exact_snapshot_subject_values(grades):
    result = service._computed_blocks(grades, [])
    assert result["A00"]["raw_sum"] == 24.375
    assert result["A00"]["subject_scores"] == {"Toán": 8.125, "Vật lý": 8.125, "Hóa học": 8.125}
