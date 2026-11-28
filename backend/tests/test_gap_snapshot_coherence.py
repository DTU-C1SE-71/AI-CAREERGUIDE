"""Gap Engine phải đọc cùng snapshot hiện tại với recommender từ student_assessment_submissions."""
from datetime import datetime, timedelta, timezone
import uuid

import pytest
from app.models.identity import User, UserRole
from app.models.taxonomy import Major
from app.models.assessment import StudentAssessmentSubmission, StudentDiagnosticTest
from app.services.gap_roadmap_engine.service import get_student_major_skill_gaps


@pytest.mark.asyncio
@pytest.mark.parametrize("snapshot_grades,old_grades,expect_foundation", [
    ({}, {"Toán": 9.9}, False),
    ({"Toán": 3}, {"Toán": 9.9}, False),
    ({"math": 9.9}, {"Toán": 3}, True),
])
async def test_current_snapshot_controls_foundation_without_reviving_old_grades(ai_runtime_db, snapshot_grades, old_grades, expect_foundation):
    db = ai_runtime_db
    owner_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    db.add(User(id=owner_id, email="gap-snapshot@example.com", full_name="Học sinh tổng hợp", hashed_password="synthetic-unused", role=UserRole.STUDENT))
    db.add(Major(major_code="7480101", name="Khoa học máy tính", riasec_vector={code: 0.5 for code in "RIASEC"}, cognitive_attributes={}, industry_outlook="Tổng hợp"))
    db.add(StudentAssessmentSubmission(
        user_id=owner_id,
        riasec_vector={},
        riasec_raw_scores={},
        cognitive_traits={},
        cognitive_answers={},
        raw_answers={"riasec_answers": {}, "grades_by_subject": old_grades, "score_context": {"kind": "TRANSCRIPT", "scale": 10}},
        dominant_traits=[],
        completed_at=now - timedelta(hours=1),
    ))
    db.add(StudentAssessmentSubmission(
        user_id=owner_id,
        riasec_vector={},
        riasec_raw_scores={},
        cognitive_traits={},
        cognitive_answers={},
        raw_answers={"riasec_answers": {}, "grades_by_subject": snapshot_grades, "score_context": {"kind": "TRANSCRIPT", "scale": 10}},
        dominant_traits=[],
        completed_at=now,
    ))
    db.add(StudentDiagnosticTest(user_id=owner_id, skill_code="SYNTHETIC_DIAGNOSTIC", score=0.8, is_passed=True, details={"score_scale": 1}))
    await db.commit()
    result = await get_student_major_skill_gaps(db, owner_id, "7480101")
    assert bool(result["suggested_foundation"]) is expect_foundation
    assert result["mastered_skills"] == ["SYNTHETIC_DIAGNOSTIC"]
    assert result["requirements_status"] == "UNKNOWN"
