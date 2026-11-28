"""Dịch vụ hồ sơ đánh giá và bài chẩn đoán kỹ năng đọc từ bảng chuẩn student_assessment_submissions."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.assessment import StudentAssessmentSubmission, StudentDiagnosticTest
from app.models.identity import User
from app.models.taxonomy import SubjectBlock, Skill
from app.schemas.assessment import DiagnosticCheckBatchSubmit
from app.services.recommender.engine import compute_block_zscores_from_grades, calculate_z_score_and_cdf
from app.services.recommender.readiness import validate_readiness_grades
from app.services.recommender.service import resolve_assessment_evidence
from app.services.gap_roadmap_engine.gap_engine import infer_mastered_skills_from_diagnostic_tests


async def _lock_owner(db, user_id):
    owner = (await db.execute(select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
    if owner is None or not owner.is_active:
        raise HTTPException(401, "Tài khoản không còn hoạt động.")


def _computed_blocks(grades, subject_blocks):
    validated = validate_readiness_grades(grades)["scores"]
    blocks = compute_block_zscores_from_grades({subject: float(score) for subject, score in validated.items()}, db_blocks=subject_blocks)
    for block in blocks.values():
        block["subject_scores"] = {subject: float(validated[subject]) for subject in block["subjects_used"]}
        total = sum((validated[subject] for subject in block["subjects_used"]), Decimal(0))
        z, score = calculate_z_score_and_cdf(float(total), block["national_mean"], block["national_std"])
        block.update(raw_sum=float(total), z_score=z, score_academic=score, score_kind="TRANSCRIPT")
    return blocks


async def _diagnostics(db, user_id, checks):
    if not checks:
        return []
    codes = {check.skill_code for check in checks}
    existing = set((await db.execute(select(Skill.skill_code).where(Skill.skill_code.in_(codes)))).scalars())
    if codes != existing:
        raise HTTPException(422, "Bài chẩn đoán tham chiếu kỹ năng chưa có trong danh mục.")
    saved = []
    for check in checks:
        normalized = check.score / check.score_scale
        item = StudentDiagnosticTest(id=uuid.uuid4(), user_id=user_id, skill_code=check.skill_code,
            score=normalized, is_passed=normalized >= 0.7,
            details={**(check.details or {}), "score_scale": check.score_scale, "raw_score": check.score},
            tested_at=datetime.now(timezone.utc))
        db.add(item)
        saved.append(item)
    return saved


async def save_diagnostic_skill_checks(db: AsyncSession, user_id: uuid.UUID, payload: DiagnosticCheckBatchSubmit) -> list[StudentDiagnosticTest]:
    try:
        await _lock_owner(db, user_id)
        saved = await _diagnostics(db, user_id, payload.checks)
        await db.commit()
        return saved
    except Exception:
        await db.rollback()
        raise


async def get_student_profile(db: AsyncSession, user_id: uuid.UUID) -> dict[str, Any]:
    evidence = await resolve_assessment_evidence(db, user_id)
    blocks = list((await db.execute(select(SubjectBlock))).scalars().all())
    diagnostic_tests = list((await db.execute(select(StudentDiagnosticTest).where(StudentDiagnosticTest.user_id == user_id))).scalars().all())
    mastered = infer_mastered_skills_from_diagnostic_tests([
        {"skill_code": item.skill_code, "score": item.score, "is_passed": item.is_passed} for item in diagnostic_tests])
    submission = None
    if evidence["assessment_id"]:
        try:
            submission = await db.get(StudentAssessmentSubmission, uuid.UUID(str(evidence["assessment_id"])))
        except (ValueError, TypeError):
            submission = None
    raw_answers = submission.raw_answers if submission and isinstance(submission.raw_answers, dict) else {}
    if isinstance(raw_answers.get("cognitive_answers"), dict):
        cognitive_answers = raw_answers["cognitive_answers"]
    elif isinstance(raw_answers.get("cognitive"), dict):
        cognitive_answers = raw_answers["cognitive"]
    elif submission and isinstance(submission.cognitive_answers, dict):
        cognitive_answers = submission.cognitive_answers
    else:
        cognitive_answers = {}
    has_assessment = bool(
        evidence["assessment_id"]
        and (evidence["riasec_answers"] or evidence["riasec_scores"] or evidence["grades_by_subject"])
    )
    return {"user_id": user_id, "assessment_id": evidence["assessment_id"],
            "has_assessment": has_assessment,
            "riasec_vector": evidence["riasec_scores"], "riasec_answers": evidence["riasec_answers"],
            "cognitive_preferences": evidence["cognitive_preferences"], "cognitive_answers": cognitive_answers,
            "aspiration": evidence["aspiration"],
            "computed_block_zscores": _computed_blocks(evidence["grades_by_subject"], blocks),
            "raw_grades": evidence["grades_by_subject"], "score_context": evidence["score_context"],
            "diagnostic_skills_mastered": sorted(mastered),
            "last_updated": (submission.completed_at if submission else datetime.now(timezone.utc)).isoformat()}
