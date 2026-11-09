import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.assessment import StudentAssessment, StudentGrade, StudentDiagnosticTest
from app.models.taxonomy import SubjectBlock
from app.schemas.assessment import (
    RIASECAssessmentSubmit,
    CognitivePreferenceSubmit,
    GradeEntrySubmit,
    DiagnosticCheckInput,
    DiagnosticCheckBatchSubmit,
)
from app.services.recommender.engine import normal_cdf, calculate_z_score_and_cdf
from app.services.gap_roadmap_engine.gap_engine import (
    infer_mastered_skills_from_grades,
    infer_mastered_skills_from_diagnostic_tests,
)


async def save_riasec_assessment(
    db: AsyncSession,
    user_id: uuid.UUID,
    payload: RIASECAssessmentSubmit
) -> StudentAssessment:
    """
    Saves student responses to Holland RIASEC questionnaire and computes normalized vector.
    """
    dimensions = ["R", "I", "A", "S", "E", "C"]

    if payload.riasec_scores:
        riasec_dict = payload.riasec_scores.model_dump()
    else:
        # Calculate from Likert responses (1 to 5)
        sums = {dim: 0.0 for dim in dimensions}
        counts = {dim: 0 for dim in dimensions}
        for q_id, val in payload.raw_responses.items():
            for dim in dimensions:
                if q_id.upper().startswith(dim):
                    sums[dim] += float(val)
                    counts[dim] += 1

        riasec_dict = {}
        for dim in dimensions:
            if counts[dim] > 0:
                # Map 1-5 scale to [0.0, 1.0]
                normalized_val = (sums[dim] / counts[dim] - 1.0) / 4.0
                riasec_dict[dim] = round(max(0.0, min(1.0, normalized_val)), 4)
            else:
                riasec_dict[dim] = 0.5

    # Check existing or create new
    query = select(StudentAssessment).where(StudentAssessment.user_id == user_id)
    result = await db.execute(query)
    assessment = result.scalar_one_or_none()

    if assessment:
        assessment.riasec_scores = riasec_dict
        assessment.raw_responses = payload.raw_responses
        assessment.assessed_at = datetime.now(timezone.utc)
    else:
        assessment = StudentAssessment(
            user_id=user_id,
            riasec_scores=riasec_dict,
            cognitive_preferences={},
            raw_responses=payload.raw_responses,
            assessed_at=datetime.now(timezone.utc)
        )
        db.add(assessment)

    await db.commit()
    await db.refresh(assessment)
    return assessment


async def save_cognitive_preferences(
    db: AsyncSession,
    user_id: uuid.UUID,
    payload: CognitivePreferenceSubmit
) -> StudentAssessment:
    """
    Saves cognitive learning preferences and environment traits.
    """
    query = select(StudentAssessment).where(StudentAssessment.user_id == user_id)
    result = await db.execute(query)
    assessment = result.scalar_one_or_none()

    pref_dict = payload.model_dump()

    if assessment:
        assessment.cognitive_preferences = pref_dict
        assessment.assessed_at = datetime.now(timezone.utc)
    else:
        assessment = StudentAssessment(
            user_id=user_id,
            riasec_scores={"R": 0.5, "I": 0.5, "A": 0.5, "S": 0.5, "E": 0.5, "C": 0.5},
            cognitive_preferences=pref_dict,
            raw_responses={},
            assessed_at=datetime.now(timezone.utc)
        )
        db.add(assessment)

    await db.commit()
    await db.refresh(assessment)
    return assessment


async def process_and_save_grades(
    db: AsyncSession,
    user_id: uuid.UUID,
    payload: GradeEntrySubmit
) -> StudentGrade:
    """
    Standardizes subject grades using national Z-score normalization parameters (mu, sigma)
    and computes cumulative percentile CDF(Z) for each national subject block.
    """
    blocks_res = await db.execute(select(SubjectBlock))
    subject_blocks: List[SubjectBlock] = list(blocks_res.scalars().all())

    computed_blocks: Dict[str, Any] = {}

    for block in subject_blocks:
        required_subjects = block.subjects
        if all(sub in payload.grades for sub in required_subjects):
            raw_sum = sum(float(payload.grades[sub]) for sub in required_subjects)
            z_val, cdf_val = calculate_z_score_and_cdf(
                raw_total=raw_sum,
                national_mean=block.national_mean,
                national_std=block.national_std
            )
            computed_blocks[block.block_code] = {
                "block_code": block.block_code,
                "subjects_used": required_subjects,
                "raw_sum": round(raw_sum, 2),
                "national_mean": block.national_mean,
                "national_std": block.national_std,
                "z_score": z_val,
                "score_academic": cdf_val
            }

    # Save diagnostic checks if submitted concurrently
    if payload.diagnostic_checks:
        for dc in payload.diagnostic_checks:
            norm_score = dc.score / 10.0 if dc.score > 1.0 else dc.score
            is_pass = norm_score >= 0.70
            diag_test = StudentDiagnosticTest(
                user_id=user_id,
                skill_code=dc.skill_code,
                score=round(norm_score, 4),
                is_passed=is_pass,
                details=dc.details or {},
                tested_at=datetime.now(timezone.utc)
            )
            db.add(diag_test)

    # Fetch existing grade record or create new
    grade_query = select(StudentGrade).where(
        StudentGrade.user_id == user_id,
        StudentGrade.academic_year == payload.academic_year
    )
    res = await db.execute(grade_query)
    student_grade = res.scalar_one_or_none()

    multi_sem = payload.multi_semester or {}

    if student_grade:
        student_grade.grades_by_subject = payload.grades
        student_grade.multi_semester_data = multi_sem
        student_grade.computed_block_zscores = computed_blocks
    else:
        student_grade = StudentGrade(
            user_id=user_id,
            grades_by_subject=payload.grades,
            multi_semester_data=multi_sem,
            computed_block_zscores=computed_blocks,
            academic_year=payload.academic_year,
            created_at=datetime.now(timezone.utc)
        )
        db.add(student_grade)

    await db.commit()
    await db.refresh(student_grade)
    return student_grade


async def save_diagnostic_skill_checks(
    db: AsyncSession,
    user_id: uuid.UUID,
    payload: DiagnosticCheckBatchSubmit
) -> List[StudentDiagnosticTest]:
    saved_tests: List[StudentDiagnosticTest] = []
    for check in payload.checks:
        norm_score = check.score / 10.0 if check.score > 1.0 else check.score
        is_pass = norm_score >= 0.70
        test_entry = StudentDiagnosticTest(
            user_id=user_id,
            skill_code=check.skill_code,
            score=round(norm_score, 4),
            is_passed=is_pass,
            details=check.details or {},
            tested_at=datetime.now(timezone.utc)
        )
        db.add(test_entry)
        saved_tests.append(test_entry)

    await db.commit()
    return saved_tests


async def get_student_profile(
    db: AsyncSession,
    user_id: uuid.UUID
) -> Dict[str, Any]:
    assess_res = await db.execute(
        select(StudentAssessment).where(StudentAssessment.user_id == user_id)
    )
    assessment = assess_res.scalar_one_or_none()

    grade_res = await db.execute(
        select(StudentGrade).where(StudentGrade.user_id == user_id).order_by(StudentGrade.created_at.desc())
    )
    grade = grade_res.scalar_one_or_none()

    diag_res = await db.execute(
        select(StudentDiagnosticTest).where(StudentDiagnosticTest.user_id == user_id)
    )
    diagnostic_tests = list(diag_res.scalars().all())

    raw_grades = grade.grades_by_subject if grade else {}
    mastered = infer_mastered_skills_from_grades(raw_grades)
    diag_mastered = infer_mastered_skills_from_diagnostic_tests([
        {"skill_code": d.skill_code, "score": d.score, "is_passed": d.is_passed}
        for d in diagnostic_tests
    ])
    mastered.update(diag_mastered)

    return {
        "user_id": user_id,
        "riasec_vector": assessment.riasec_scores if assessment else None,
        "cognitive_preferences": assessment.cognitive_preferences if assessment else None,
        "computed_block_zscores": grade.computed_block_zscores if grade else None,
        "raw_grades": raw_grades,
        "diagnostic_skills_mastered": sorted(list(mastered)),
        "last_updated": (assessment.assessed_at if assessment else datetime.now(timezone.utc)).isoformat()
    }
