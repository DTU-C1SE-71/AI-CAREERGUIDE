"""Service boundaries for aspiration evidence (no external DB or LLM)."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.schemas.recommender import EvaluateProfileRequest
from app.services.recommender.service import resolve_assessment_evidence, evaluate_dashboard_profile_bundle


def result(row):
    return SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: row))


@pytest.mark.asyncio
async def test_explicit_empty_input_does_not_restore_saved_grades_or_aspiration():
    saved = SimpleNamespace(id=uuid4(), riasec_scores={"I": 1}, cognitive_preferences={},
                            raw_responses={"riasec": {"I1": 5}, "aspiration": {"dream_job": "Bác sĩ"}})
    db = SimpleNamespace(execute=AsyncMock(return_value=result(saved)))
    profile = await resolve_assessment_evidence(db, uuid4(), {
        "grades_by_subject": {}, "aspiration": {}, "riasec_answers": {}, "cognitive_answers": {},
    })
    assert profile["grades_by_subject"] == {}
    assert profile["aspiration"] == {}
    assert profile["riasec_answers"] == {}
    assert profile["riasec_scores"] == {}
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_selected_assessment_without_grades_cannot_borrow_latest_grades():
    saved = SimpleNamespace(id=uuid4(), riasec_scores={"I": 1}, cognitive_preferences={}, raw_responses={})
    db = SimpleNamespace(execute=AsyncMock(return_value=result(saved)))
    profile = await resolve_assessment_evidence(db, uuid4(), {"assessment_id": saved.id})
    assert profile["grades_by_subject"] == {}
    assert profile["assessment_id"] == str(saved.id)
    assert profile["evidence_source"] == "SELECTED_ASSESSMENT"
    assert db.execute.await_count == 1


def test_endpoint_model_preserves_boolean_and_explicit_empty_evidence():
    payload = EvaluateProfileRequest(grades_by_subject={"Toán": True}, aspiration={})
    inline = payload.model_dump(exclude_unset=True)
    assert inline["grades_by_subject"]["Toán"] is True
    assert inline["aspiration"] == {}
    assert "riasec_scores" not in inline


@pytest.mark.asyncio
async def test_bundle_without_answers_does_not_fabricate_radar_or_eligible_options():
    bundle = await evaluate_dashboard_profile_bundle(
        None, uuid4(), top_k=1,
        inline_profile={"grades_by_subject": {"Toán": 9, "Vật lý": 9, "Hóa học": 9},
                        "aspiration": {"dream_job": "Bác sĩ"}, "riasec_answers": {}},
    )
    assert all(point["value"] is None for point in bundle["riasecData"])
    analysis = bundle["aspirationAnalysis"]
    assert analysis["current_options"] == []
    assert analysis["alignment_score"] is None
    assert analysis["holland_code"] == ""
    assert all(item["readiness"]["status"] == "UNKNOWN" for item in analysis["dream_majors"])
    assert len(bundle["majors"]) == 1


@pytest.mark.asyncio
async def test_bundle_uses_full_catalog_for_aspiration_even_when_top_k_is_one(monkeypatch):
    from app.services.taxonomy import service as taxonomy_service
    catalog = [
        {"major_code": "7480101", "name": "Khoa học máy tính", "category": "Máy tính", "blocks": ["A00"],
         "riasec": {"I": 1}, "cognitive": {}},
        {"major_code": "7720101", "name": "Y khoa", "category": "Sức khỏe", "blocks": ["B00"],
         "riasec": {"S": 1}, "cognitive": {}},
    ]
    monkeypatch.setattr(taxonomy_service, "load_seed_majors", lambda: catalog)
    bundle = await evaluate_dashboard_profile_bundle(
        None, uuid4(), top_k=1, inline_profile={"riasec_answers": {"I1": 5},
            "grades_by_subject": {"Toán": 9, "Vật lý": 9, "Hóa học": 9},
            "aspiration": {"dream_job": "Bác sĩ"}},
    )
    assert len(bundle["majors"]) == 1
    assert bundle["total_majors_evaluated"] == 2
    assert any(item["major_code"] == "7720101" for item in bundle["aspirationAnalysis"]["dream_majors"])
    assert bundle["aspirationAnalysis"]["current_options"] == []


@pytest.mark.asyncio
async def test_invalid_and_rounded_up_grades_never_pass_verified_reference(monkeypatch):
    from app.services.taxonomy import service as taxonomy_service
    catalog = [{"major_code": "7340101", "name": "Quản trị kinh doanh", "category": "Kinh doanh", "blocks": ["D01"],
                "riasec": {"E": 1}, "cognitive": {}, "readiness_reference": {
                    "id": "test-policy-only", "kind": "ACADEMIC_POLICY", "verified": True,
                    "source": "synthetic-test-fixture", "expectedScoreKind": "TRANSCRIPT",
                    "calculationMethod": "SUM_THREE_SUBJECTS", "admittedBlocks": ["D01"], "cutoff": 24, "minimum": 20,
                }}]
    monkeypatch.setattr(taxonomy_service, "load_seed_majors", lambda: catalog)
    for score in (7.999, 99, True):
        bundle = await evaluate_dashboard_profile_bundle(None, uuid4(), top_k=1, inline_profile={
            "riasec_answers": {"E1": 5}, "grades_by_subject": {"Toán": score, "Ngữ văn": score, "Tiếng Anh": score},
            "aspiration": {"dream_job": "Quản trị kinh doanh"},
        })
        assert all(item.readiness["status"] != "READY_REFERENCE" for item in bundle["majors"] + bundle["blocked_goals"])
        assert all(item.readiness["status"] == "NEEDS_IMPROVEMENT" for item in bundle["blocked_goals"])
        assert bundle["aspirationAnalysis"]["current_options"] == []

@pytest.mark.asyncio
async def test_public_major_does_not_publish_heuristic_target_as_evidence():
    bundle = await evaluate_dashboard_profile_bundle(None, uuid4(), top_k=3, inline_profile={
        "riasec_answers": {"I1": 5}, "grades_by_subject": {"Toán": 10, "Vật lý": 10, "Hóa học": 10},
        "aspiration": {"dream_job": "Kỹ sư AI"},
    })
    for major in bundle["majors"]:
        assert major.readiness["reason"] == "REFERENCE_BASIS_MISSING"
        assert major.feasibility_tier == major.feasibility == "UNKNOWN"
        assert major.constraint_passed is False
        assert major.best_block_score is None
        assert "Đạt ngưỡng tuyển sinh" not in " ".join(major.top_supporting_factors)
        assert "nắm chắc suất đỗ" not in major.explanation


def test_fit_input_preserves_decimal_total_before_reference_comparison():
    from app.services.recommender.service import _exact_block_results
    from app.services.recommender.readiness import validate_readiness_grades
    raw = {"Toán": 7.999, "Ngữ văn": 7.999, "Tiếng Anh": 7.999}
    blocks = _exact_block_results(validate_readiness_grades(raw)["scores"])
    assert blocks["D01"]["raw_sum"] == 23.997
    assert blocks["D01"]["subject_scores"]["Toán"] == 7.999


@pytest.mark.asyncio
async def test_verified_current_option_and_all_explanations_use_same_ready_block(monkeypatch):
    from app.services.taxonomy import service as taxonomy_service
    catalog = [{"major_code": "7340101", "name": "Quản trị kinh doanh", "category": "Kinh doanh", "blocks": ["A00", "D01"],
                "riasec": {"E": 1}, "cognitive": {}, "readiness_reference": {
                    "id": "test-policy-only", "kind": "ACADEMIC_POLICY", "verified": True,
                    "source": "synthetic-test-fixture", "expectedScoreKind": "TRANSCRIPT",
                    "calculationMethod": "SUM_THREE_SUBJECTS", "admittedBlocks": ["A00", "D01"], "cutoff": 24, "minimum": 20,
                }}]
    monkeypatch.setattr(taxonomy_service, "load_seed_majors", lambda: catalog)
    bundle = await evaluate_dashboard_profile_bundle(None, uuid4(), top_k=1, inline_profile={
        "riasec_answers": {"E1": 5}, "grades_by_subject": {"Toán": 8, "Vật lý": 7.5, "Hóa học": 7.5, "Ngữ văn": 8.5, "Tiếng Anh": 8.5},
        "aspiration": {"dream_job": "Quản trị kinh doanh"},
    })
    major = bundle["majors"][0]
    option = bundle["aspirationAnalysis"]["current_options"][0]
    assert major.readiness["status"] == "READY_REFERENCE"
    assert major.best_matching_block == option["best_matching_block"] == "D01"
    assert major.best_block_score == option["best_block_score"] == 25
    assert major.score_breakdown["admitted_blocks_evaluated"]["D01"]["raw_sum"] == 25
    assert "A00" not in bundle["aspirationAnalysis"]["agent_verdict"]


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["inline", "live", "snapshot"])
async def test_score_context_is_paired_with_grade_source(source):
    from app.services.recommender.readiness import evaluate_current_readiness

    grades = {"Toán": 9, "Vật lý": 9, "Hóa học": 9}
    exam_context = {"kind": "EXAM", "scale": 10, "examId": "old-exam"}
    saved = SimpleNamespace(id=uuid4(), riasec_scores={}, cognitive_preferences={},
                            raw_responses={"score_context": exam_context, "grades_by_subject": grades})
    current_grade = SimpleNamespace(grades_by_subject=grades)
    db = SimpleNamespace(execute=AsyncMock(side_effect=[result(saved), result(current_grade)]))
    inline = {"grades_by_subject": grades} if source == "inline" else (
        {"assessment_id": saved.id} if source == "snapshot" else {})
    profile = await resolve_assessment_evidence(db, uuid4(), inline)
    assert profile["grades_by_subject"] == grades
    assert profile["score_context"] == (exam_context if source in {"snapshot", "live"} else {"kind": "TRANSCRIPT", "scale": 10})
    reference = {"id": "test-only", "kind": "ADMISSION_REFERENCE", "verified": True,
                 "source": "synthetic-fixture", "expectedScoreKind": "EXAM",
                 "calculationMethod": "SUM_THREE_SUBJECTS", "admittedBlocks": ["A00"],
                 "cutoff": 26, "minimum": 20, "institution": "test", "program": "test",
                 "year": 2026, "examId": "old-exam"}
    readiness = evaluate_current_readiness(raw_grades=profile["grades_by_subject"],
        score_context=profile["score_context"], admitted_blocks=["A00"], block_source="DATABASE",
        major_code="test", major_name="Test", reference=reference)
    assert readiness["status"] == ("READY_REFERENCE" if source in {"snapshot", "live"} else "UNKNOWN")
    if source == "inline":
        assert readiness["reason"] == "REFERENCE_NOT_COMPARABLE"


@pytest.mark.asyncio
@pytest.mark.parametrize("context", [{}, None])
async def test_explicit_empty_score_context_does_not_restore_saved_context(context):
    from app.services.recommender.readiness import evaluate_current_readiness

    saved = SimpleNamespace(id=uuid4(), riasec_scores={}, cognitive_preferences={}, raw_responses={
        "score_context": {"kind": "TRANSCRIPT", "scale": 10}})
    db = SimpleNamespace(execute=AsyncMock(return_value=result(saved)))
    profile = await resolve_assessment_evidence(db, uuid4(), {
        "grades_by_subject": {"Toán": 9, "Vật lý": 9, "Hóa học": 9}, "score_context": context})
    assert profile["score_context"] == {}
    readiness = evaluate_current_readiness(raw_grades=profile["grades_by_subject"],
        score_context=profile["score_context"], admitted_blocks=["A00"], block_source="DATABASE",
        major_code="test", major_name="Test", reference={
            "id": "test-only", "kind": "ACADEMIC_POLICY", "verified": True,
            "source": "synthetic-fixture", "expectedScoreKind": "TRANSCRIPT",
            "calculationMethod": "SUM_THREE_SUBJECTS", "admittedBlocks": ["A00"],
            "cutoff": 24, "minimum": 20})
    assert readiness["status"] == "UNKNOWN"
    assert readiness["reason"] == "REFERENCE_NOT_COMPARABLE"
