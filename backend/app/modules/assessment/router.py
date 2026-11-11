import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_optional_current_user
from app.models.identity import User
from app.modules.assessment import service
from app.modules.assessment.schemas import (
    AssessmentQuestionSetResponse,
    AssessmentSubmissionRequest,
    AssessmentSubmissionResponse,
)

router = APIRouter(prefix="/assessments", tags=["Assessment & Questionnaire Engine (FR02, FR04)"])


@router.get(
    "/active-questions",
    response_model=AssessmentQuestionSetResponse,
    status_code=status.HTTP_200_OK,
    summary="Tải bộ câu hỏi khảo sát hoạt động (30 RIASEC + 8 Cognitive Preferences)"
)
async def get_active_questions(
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves the currently active questionnaire set according to Circular 74/2026/TT-BGDĐT.
    Single Source of Truth: Centralized in PostgreSQL with questionnaire versioning.
    Sets Cache-Control header max-age=3600 to optimize frontend network requests.
    """
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=600"
    return await service.get_active_questionnaire_set(db)


@router.post(
    "/submit",
    response_model=AssessmentSubmissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Nộp bài làm khảo sát và tính toán chân dung sở thích nghề nghiệp 3 trụ cột (100% tất định)"
)
async def submit_assessment(
    payload: AssessmentSubmissionRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Nhận đáp án Likert và nhận thức từ học sinh, chấm điểm toán học tất định và lưu cho user đang đăng nhập.
    """
    target_user_id = current_user.id if current_user else uuid.uuid4()
    return await service.process_assessment_submission(
        db,
        target_user_id,
        payload,
        persist_to_db=(current_user is not None),
    )


@router.post(
    "/seed",
    status_code=status.HTTP_200_OK,
    summary="Nạp bộ câu hỏi khảo sát Circular 74/2026/TT-BGDĐT v1.8 vào CSDL PostgreSQL"
)
async def seed_questions_endpoint(
    db: AsyncSession = Depends(get_db)
):
    """Admin / Setup endpoint to seed the assessment questionnaire into PostgreSQL."""
    from app.db.seeds.seed_assessment_questions import seed_assessment_questions
    q_set = await seed_assessment_questions(db)
    return {
        "status": "success",
        "set_id": str(q_set.id),
        "set_code": q_set.set_code,
        "version": q_set.version,
        "message": "Bộ câu hỏi khảo sát đã được nạp và lưu vào CSDL PostgreSQL thành công!"
    }
