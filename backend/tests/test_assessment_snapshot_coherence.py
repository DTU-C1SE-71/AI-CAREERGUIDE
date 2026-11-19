from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
import pytest
from fastapi import HTTPException
from app.modules.assessment.schemas import AssessmentSubmissionRequest
from app.modules.assessment.service import process_assessment_submission
from app.services.recommender.service import resolve_assessment_evidence, calculate_3pillar_recommendations, _riasec_vector_from_answers
from app.services.recommender.readiness import build_interest_evidence
from app.schemas.recommender import RecommendationRequest


@pytest.mark.asyncio
async def test_snapshot_roundtrip_preserves_grade_precision_context_and_missing_cognition():
    question = SimpleNamespace(code="I1", id=uuid4(), set_id=uuid4())
    db = SimpleNamespace(add=Mock(), commit=AsyncMock(), rollback=AsyncMock(), execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda:SimpleNamespace(id=question.set_id, questions=[question], is_active=True))))
    payload = AssessmentSubmissionRequest(riasec_answers={"I1":5}, cognitive_answers={},
        grades_by_subject={"Toán":7.999, "Ngữ văn":7.999, "Tiếng Anh":7.999},
        score_context={"kind":"EXAM", "scale":10, "examId":"test"}, aspiration={"dream_job":"Y khoa"})
    response = await process_assessment_submission(db, uuid4(), payload)
    saved = next(call.args[0] for call in db.add.call_args_list if hasattr(call.args[0], "raw_responses"))
    assert saved.id == response.submission_id
    db.execute = AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda:saved)))
    profile = await resolve_assessment_evidence(db, uuid4(), {"assessment_id":response.submission_id})
    assert profile["grades_by_subject"] == payload.grades_by_subject
    assert profile["score_context"] == payload.score_context
    assert profile["cognitive_preferences"] == response.cognitive_traits == {}
    assert response.riasec_vector == {"I":1}
    assert response.dominant_traits == []
    assert response.xp_earned == 25
    assert db.add.call_args_list[1].args[0].question_id == question.id
    assert len(db.add.call_args_list) == 3  # submission + one actual answer + legacy snapshot


@pytest.mark.asyncio
async def test_failed_authenticated_snapshot_save_is_not_reported_as_success():
    db = SimpleNamespace(add=Mock(), commit=AsyncMock(side_effect=RuntimeError("private DB information")), rollback=AsyncMock(), execute=AsyncMock(side_effect=[SimpleNamespace(scalar_one_or_none=lambda:SimpleNamespace(is_active=True)),SimpleNamespace(scalar_one_or_none=lambda:None)]))
    with pytest.raises(HTTPException) as error:
        await process_assessment_submission(db,uuid4(),AssessmentSubmissionRequest(riasec_answers={},cognitive_answers={}))
    assert error.value.status_code == 503
    assert "private" not in error.value.detail
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("answer", [1, 3, 5])
async def test_uniform_complete_interest_is_exploratory_not_high_fit(answer):
    answers={f"{g}{n}":answer for g in "RIASEC" for n in range(1,6)}
    evidence=build_interest_evidence(answers)
    assert evidence["status"] == "NON_DISCRIMINATING"
    assert all(g["percent"] == (answer-1)*25 for g in evidence["groups"])
    assert all(value == (answer-1)/4 for value in _riasec_vector_from_answers(answers).values())
    result=await calculate_3pillar_recommendations(None,uuid4(),RecommendationRequest(top_k=1),inline_profile={"riasec_answers":answers},persist_history=False)
    item=result.recommendations[0]
    assert item.fit["interest"] is None and item.match is None
    assert item.score_breakdown["weights"]["w_riasec"] == 0


@pytest.mark.asyncio
async def test_explicit_missing_question_set_rejected_without_saving_snapshot():
    db=SimpleNamespace(add=Mock(),execute=AsyncMock(side_effect=[SimpleNamespace(scalar_one_or_none=lambda:SimpleNamespace(is_active=True)),SimpleNamespace(scalar_one_or_none=lambda:None)]),commit=AsyncMock(),rollback=AsyncMock())
    with pytest.raises(HTTPException) as error:
        await process_assessment_submission(db,uuid4(),AssessmentSubmissionRequest(set_id=uuid4(),riasec_answers={},cognitive_answers={}))
    assert error.value.status_code == 422
    db.add.assert_not_called()
    db.commit.assert_not_awaited()
    db.rollback.assert_awaited_once()


def test_display_and_save_query_select_single_deterministic_set():
    from app.modules.assessment.service import _question_set_query
    from sqlalchemy.dialects import postgresql
    selected=uuid4()
    active=_question_set_query().compile(dialect=postgresql.dialect(),compile_kwargs={"literal_binds":True})
    explicit=_question_set_query(selected).compile(dialect=postgresql.dialect(),compile_kwargs={"literal_binds":True})
    assert "is_active IS true" in str(active)
    assert "created_at DESC, assessment_question_sets.id ASC" in str(active)
    assert "LIMIT 1" in str(active)
    assert str(selected) in str(explicit)
    assert "is_active" not in str(explicit).split("WHERE")[1]


@pytest.mark.asyncio
@pytest.mark.parametrize("grades", [{}, {"Toán":7.999}])
async def test_current_snapshot_grade_keys_prevent_borrowing_stale_grade_table(grades):
    context={"kind":"EXAM", "scale":10, "examId":"snapshot-exam"}
    row=SimpleNamespace(id=uuid4(),raw_responses={"grades_by_subject":grades,"score_context":context,"cognitive":{}},riasec_scores={},cognitive_preferences={})
    stale=SimpleNamespace(grades_by_subject={"Toán":10,"Ngữ văn":10,"Tiếng Anh":10})
    result=lambda value:SimpleNamespace(scalars=lambda:SimpleNamespace(first=lambda:value))
    db=SimpleNamespace(execute=AsyncMock(side_effect=[result(row),result(stale)]))
    profile=await resolve_assessment_evidence(db,uuid4())
    assert profile["grades_by_subject"] == grades
    assert profile["score_context"] == context
    assert profile["assessment_id"] == str(row.id)
    assert db.execute.await_count == 1


@pytest.mark.asyncio
async def test_current_legacy_snapshot_without_grade_key_still_uses_grade_table():
    row=SimpleNamespace(id=uuid4(),raw_responses={"cognitive":{}},riasec_scores={},cognitive_preferences={})
    legacy=SimpleNamespace(grades_by_subject={"Toán":8})
    result=lambda value:SimpleNamespace(scalars=lambda:SimpleNamespace(first=lambda:value))
    db=SimpleNamespace(execute=AsyncMock(side_effect=[result(row),result(legacy)]))
    profile=await resolve_assessment_evidence(db,uuid4())
    assert profile["grades_by_subject"] == {"Toán":8}
    assert profile["score_context"] == {"kind":"TRANSCRIPT","scale":10}
    assert db.execute.await_count == 2
