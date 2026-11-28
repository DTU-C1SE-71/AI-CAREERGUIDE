import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_current_user
from app.models.identity import User
from app.schemas.assessment import (
    DiagnosticCheckBatchSubmit,
    AssessmentQuestionSetResponse,
    AssessmentSubmissionDetail,
    AssessmentSubmissionRequest,
    AssessmentSubmissionResponse,
    AssessmentSubmissionSummary,
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
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lưu bài đánh giá RIASEC & Nhận thức theo đúng user_id đang đăng nhập (hoặc tính toán không lưu DB cho khách)."""
    target_user_id = current_user.id if current_user else uuid.uuid4()
    return await modular_assessment_service.process_assessment_submission(
        db,
        target_user_id,
        payload,
        persist_to_db=(current_user is not None),
    )


@router.get("/submissions", response_model=List[AssessmentSubmissionSummary], status_code=status.HTTP_200_OK)
async def list_submissions_alt(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lịch sử nộp bài khảo sát của người dùng hiện tại (alias under /assessment prefix)."""
    return await modular_assessment_service.list_student_submissions(db, current_user.id, limit=limit)


@router.get("/submissions/{submission_id}", response_model=AssessmentSubmissionDetail, status_code=status.HTTP_200_OK)
async def get_submission_detail_alt(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Chi tiết một lượt nộp bài khảo sát của người dùng hiện tại (alias under /assessment prefix)."""
    return await modular_assessment_service.get_student_submission_detail(db, current_user.id, submission_id)


@router.put("/submissions/{submission_id}", response_model=AssessmentSubmissionResponse, status_code=status.HTTP_200_OK)
async def update_submission_alt(
    submission_id: uuid.UUID,
    payload: AssessmentSubmissionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cập nhật hồ sơ đã lưu, làm mới cache AI và tính lại đề xuất (alias under /assessment prefix)."""
    return await modular_assessment_service.update_student_submission(db, current_user.id, submission_id, payload)


@router.delete("/submissions/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_submission_alt(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Xóa vĩnh viễn một lượt nộp bài khảo sát của người dùng hiện tại (alias under /assessment prefix)."""
    await modular_assessment_service.delete_student_submission(db, current_user.id, submission_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
