"""Các alias đánh giá cũ cùng dùng snapshot và bằng chứng với luồng modular."""
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.assessment import StudentAssessment, StudentGrade, StudentDiagnosticTest
from app.models.identity import User
from app.models.taxonomy import SubjectBlock, Skill
from app.schemas.assessment import RIASECAssessmentSubmit, CognitivePreferenceSubmit, GradeEntrySubmit, DiagnosticCheckBatchSubmit
from app.services.recommender.engine import compute_block_zscores_from_grades, calculate_z_score_and_cdf
from app.services.recommender.readiness import build_interest_evidence, validate_readiness_grades
from app.services.recommender.service import resolve_assessment_evidence
from app.services.gap_roadmap_engine.gap_engine import infer_mastered_skills_from_diagnostic_tests


async def _lock_owner(db, user_id):
    owner = (await db.execute(select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
    if owner is None or not owner.is_active:
        raise HTTPException(401, "Tài khoản không còn hoạt động.")


async def _new_snapshot(db, user_id):
    await _lock_owner(db, user_id)
    evidence = await resolve_assessment_evidence(db, user_id)
    snapshot = StudentAssessment(id=uuid.uuid4(), user_id=user_id,
        riasec_scores=deepcopy(evidence["riasec_scores"] or {}),
        cognitive_preferences=deepcopy(evidence["cognitive_preferences"] or {}),
        raw_responses={"riasec": deepcopy(evidence["riasec_answers"] or {}),
                       "cognitive": deepcopy(evidence["cognitive_preferences"] or {}),
                       "aspiration": deepcopy(evidence["aspiration"] or {}),
                       "grades_by_subject": deepcopy(evidence["grades_by_subject"] or {}),
                       "score_context": deepcopy(evidence["score_context"] or {})},
        assessed_at=datetime.now(timezone.utc))
    return snapshot


async def save_riasec_assessment(db: AsyncSession, user_id: uuid.UUID, payload: RIASECAssessmentSubmit) -> StudentAssessment:
    try:
        snapshot = await _new_snapshot(db, user_id)
        answers = dict(payload.raw_responses)
        if payload.riasec_scores is not None:
            scores = payload.riasec_scores.model_dump()
        else:
            interest = build_interest_evidence(answers)
            scores = {group["code"]: group["percent"] / 100 for group in interest["groups"] if group["percent"] is not None}
        snapshot.riasec_scores = scores
        snapshot.raw_responses = {**snapshot.raw_responses, "riasec": answers}
        db.add(snapshot)
        await db.commit()
        return snapshot
    except Exception:
        await db.rollback()
        raise


async def save_cognitive_preferences(db: AsyncSession, user_id: uuid.UUID, payload: CognitivePreferenceSubmit) -> StudentAssessment:
    try:
        snapshot = await _new_snapshot(db, user_id)
        preferences = payload.model_dump(exclude_none=True)
        snapshot.cognitive_preferences = preferences
        snapshot.raw_responses = {**snapshot.raw_responses, "cognitive": preferences}
        db.add(snapshot)
        await db.commit()
        return snapshot
    except Exception:
        await db.rollback()
        raise


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


async def process_and_save_grades(db: AsyncSession, user_id: uuid.UUID, payload: GradeEntrySubmit) -> StudentGrade:
    try:
        snapshot = await _new_snapshot(db, user_id)
        grades = dict(payload.grades)
        blocks = list((await db.execute(select(SubjectBlock))).scalars().all())
        computed = _computed_blocks(grades, blocks)
        grade = StudentGrade(id=uuid.uuid4(), user_id=user_id, grades_by_subject=grades,
            multi_semester_data=payload.multi_semester or {}, computed_block_zscores=computed,
            academic_year=payload.academic_year, created_at=datetime.now(timezone.utc))
        snapshot.raw_responses = {**snapshot.raw_responses, "grades_by_subject": grades,
            "score_context": {"kind": "TRANSCRIPT", "scale": 10, "academic_year": payload.academic_year}}
        await _diagnostics(db, user_id, payload.diagnostic_checks)
        db.add_all([grade, snapshot])
        await db.commit()
        # ID snapshot vừa tạo chỉ dùng cho phản hồi của thao tác này.
        grade.assessment_id = snapshot.id
        return grade
    except Exception:
        await db.rollback()
        raise


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
    snapshot = None
    if evidence["assessment_id"]:
        snapshot = await db.get(StudentAssessment, uuid.UUID(evidence["assessment_id"]))
    raw_responses = snapshot.raw_responses if snapshot and isinstance(snapshot.raw_responses, dict) else {}
    cognitive_answers = raw_responses.get("cognitive") if isinstance(raw_responses.get("cognitive"), dict) else {}
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
            "last_updated": (snapshot.assessed_at if snapshot else datetime.now(timezone.utc)).isoformat()}
