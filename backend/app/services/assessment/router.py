from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.identity import User
from app.schemas.assessment import (
    RIASECAssessmentSubmit,
    CognitivePreferenceSubmit,
    GradeEntrySubmit,
    DiagnosticCheckBatchSubmit,
    AssessmentQuestionSetResponse,
    AssessmentSubmissionRequest,
    AssessmentSubmissionResponse,
)
from app.services.assessment import service
from app.modules.assessment import service as modular_assessment_service

router = APIRouter(prefix="/assessment", tags=["Vocational Assessment & Grade Standardization"])


@router.get("/active-questions", response_model=AssessmentQuestionSetResponse, status_code=status.HTTP_200_OK)
async def get_active_questions_alt(
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Retrieves the active questionnaire set (alias under /assessment prefix)."""
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=600"
    return await modular_assessment_service.get_active_questionnaire_set(db)


@router.post("/submit", response_model=AssessmentSubmissionResponse, status_code=status.HTTP_200_OK)
async def submit_assessment_alt(
    payload: AssessmentSubmissionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Submits student assessment responses (alias under /assessment prefix)."""
    import uuid
    mock_user_id = uuid.uuid4()
    return await modular_assessment_service.process_assessment_submission(db, mock_user_id, payload)



@router.post("/riasec", status_code=status.HTTP_200_OK)
async def submit_riasec_assessment(
    payload: RIASECAssessmentSubmit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submits Holland RIASEC answers and calculates normalized 6-dimensional interest vector."""
    assessment = await service.save_riasec_assessment(db, current_user.id, payload)
    return {
        "message": "RIASEC assessment recorded successfully",
        "riasec_scores": assessment.riasec_scores,
        "assessed_at": assessment.assessed_at
    }


@router.post("/cognitive-preferences", status_code=status.HTTP_200_OK)
async def submit_cognitive_preferences(
    payload: CognitivePreferenceSubmit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submits cognitive style and learning environment preferences."""
    assessment = await service.save_cognitive_preferences(db, current_user.id, payload)
    return {
        "message": "Cognitive preferences recorded successfully",
        "cognitive_preferences": assessment.cognitive_preferences
    }


@router.post("/grades", status_code=status.HTTP_200_OK)
async def submit_grades(
    payload: GradeEntrySubmit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submits subject grades (single or multi-semester), computes national Z-scores for admission blocks
    using national mean and std dev parameters, and returns standardized percentiles.
    """
    grade_record = await service.process_and_save_grades(db, current_user.id, payload)
    return {
        "message": "Academic grades standardized successfully",
        "academic_year": grade_record.academic_year,
        "computed_block_zscores": grade_record.computed_block_zscores
    }


@router.post("/diagnostic-checks", status_code=status.HTTP_200_OK)
async def submit_diagnostic_checks(
    payload: DiagnosticCheckBatchSubmit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submits optional diagnostic skill test results for competency gap analysis."""
    saved = await service.save_diagnostic_skill_checks(db, current_user.id, payload)
    return {
        "message": f"Successfully recorded {len(saved)} diagnostic skill tests.",
        "skills_tested": [s.skill_code for s in saved]
    }


@router.get("/profile", status_code=status.HTTP_200_OK)
async def get_student_evaluation_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves full student assessment profile including RIASEC, cognitive preferences, Z-scores, and mastered skills."""
    return await service.get_student_profile(db, current_user.id)
