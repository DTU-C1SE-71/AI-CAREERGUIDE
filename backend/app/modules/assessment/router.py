import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_current_user, require_admin
from app.models.identity import User
from app.modules.assessment import service
from app.modules.assessment.schemas import (
    AssessmentQuestionSetResponse,
    AssessmentSubmissionDetail,
    AssessmentSubmissionRequest,
    AssessmentSubmissionResponse,
    AssessmentSubmissionSummary,
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


@router.get(
    "/submissions",
    response_model=List[AssessmentSubmissionSummary],
    status_code=status.HTTP_200_OK,
    summary="Lịch sử nộp bài khảo sát của người dùng hiện tại",
)
async def list_my_submissions(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_student_submissions(db, current_user.id, limit=limit)


@router.get(
    "/submissions/{submission_id}",
    response_model=AssessmentSubmissionDetail,
    status_code=status.HTTP_200_OK,
    summary="Chi tiết một lần làm bài khảo sát kèm từng câu trả lời",
)
async def get_my_submission_detail(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_student_submission_detail(db, current_user.id, submission_id)


@router.put(
    "/submissions/{submission_id}",
    response_model=AssessmentSubmissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật hồ sơ đánh giá đã lưu, xóa cache AI cũ và chạy lại thuật toán đề xuất",
)
async def update_my_submission(
    submission_id: uuid.UUID,
    payload: AssessmentSubmissionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.update_student_submission(db, current_user.id, submission_id, payload)


@router.delete(
    "/submissions/{submission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa một lần làm bài khảo sát đã lưu khỏi CSDL",
)
async def delete_my_submission(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await service.delete_student_submission(db, current_user.id, submission_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/seed",
    status_code=status.HTTP_200_OK,
    summary="Nạp bộ câu hỏi khảo sát Circular 74/2026/TT-BGDĐT v1.8 vào CSDL PostgreSQL"
)
async def seed_questions_endpoint(
    current_user: User = Depends(require_admin),
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
