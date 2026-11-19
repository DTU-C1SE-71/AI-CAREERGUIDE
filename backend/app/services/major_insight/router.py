from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_optional_current_user, require_admin_actor, oauth2_scheme_optional
from app.models.identity import User
from app.schemas.insight import (
    MajorInsightResponse,
    StudentSkillAnalysisRequest,
    StudentSkillAnalysisResponse,
)
from app.services.major_insight import service

router = APIRouter(prefix="/major-insights", tags=["Major Insight & Student Skill Agent"])


@router.get(
    "/{major_code}",
    response_model=MajorInsightResponse,
    summary="Nội dung đào tạo & vị trí nghề nghiệp của ngành (theo danh mục, có bộ nhớ đệm)",
)
async def get_major_insight(
    major_code: str,
    refresh: bool = Query(default=False, description="Bỏ cache và sinh lại nội dung"),
    token: str = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Đọc danh mục ngành đang hoạt động và trả thông tin tham khảo tất định; cache đổi khi nội dung danh mục đổi.
    """
    if refresh:
        await require_admin_actor(token, db)
    return await service.get_or_create_major_insight(db, major_code, refresh=refresh)


@router.post(
    "/{major_code}/regenerate",
    response_model=MajorInsightResponse,
    summary="Admin: bỏ cache và cập nhật nội dung đào tạo từ danh mục",
)
async def regenerate_major_insight(
    major_code: str,
    admin_actor: dict = Depends(require_admin_actor),
    db: AsyncSession = Depends(get_db),
):
    """Tạo lại thông tin từ danh mục ngành hiện hành."""
    return await service.get_or_create_major_insight(db, major_code, refresh=True)


@router.delete(
    "/{major_code}",
    summary="Admin: xoá cache nội dung đào tạo của một ngành",
)
async def delete_major_insight(
    major_code: str,
    admin_actor: dict = Depends(require_admin_actor),
    db: AsyncSession = Depends(get_db),
):
    """
    Xoá bản ghi trong `major_insights`. Lần xem tiếp theo của học sinh sẽ sinh lại
    nội dung từ danh mục và cache lại như bình thường.
    """
    deleted = await service.delete_major_insight(db, major_code)
    return {
        "major_code": major_code,
        "deleted": deleted,
        "message": (
            "Đã xoá cache nội dung đào tạo."
            if deleted
            else "Ngành này chưa có cache nội dung đào tạo."
        ),
    }


@router.post(
    "/student-skills",
    response_model=StudentSkillAnalysisResponse,
    summary="Agent phân tích ưu/nhược điểm học tập và kỹ năng cần bổ sung từ bài test",
)
async def analyze_student_skills(
    payload: StudentSkillAnalysisRequest,
    current_user: User = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Phân tích dựa trên dữ liệu bài test (RIASEC, điểm học bạ, thiên hướng nhận thức):
    - Ưu điểm và điểm cần cải thiện trong cách học (giải thích ngắn, dễ hiểu).
    - Kỹ năng cần bổ sung + việc cần làm cụ thể để cải thiện.
    Kết quả được cache theo hồ sơ năng lực để không gọi AI lặp lại.
    """
    eff_gender = current_user.gender if current_user else payload.gender
    eff_grade_level = current_user.grade_level if current_user else payload.grade_level
    resolved_payload = payload.model_copy(
        update={
            "gender": eff_gender,
            "grade_level": eff_grade_level,
        }
    )
    return await service.analyze_student_skills(
        db,
        resolved_payload,
        user_id=current_user.id if current_user else None,
    )
