from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_optional_current_user, require_admin_actor
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
    summary="Nội dung đào tạo & vị trí nghề nghiệp của ngành (cache-first, chỉ gọi AI lần đầu)",
)
async def get_major_insight(
    major_code: str,
    refresh: bool = Query(default=False, description="Bỏ cache và sinh lại nội dung"),
    db: AsyncSession = Depends(get_db),
):
    """
    Đọc `major_insights` theo major_code. Nếu chưa có, agent gọi AI một lần rồi lưu DB;
    các lần xem sau trả về ngay từ DB, không phát sinh chi phí token.
    """
    return await service.get_or_create_major_insight(db, major_code, refresh=refresh)


@router.post(
    "/{major_code}/regenerate",
    response_model=MajorInsightResponse,
    summary="Admin: bỏ cache và sinh lại nội dung đào tạo của một ngành bằng AI",
)
async def regenerate_major_insight(
    major_code: str,
    admin_actor: dict = Depends(require_admin_actor),
    db: AsyncSession = Depends(get_db),
):
    """Xoá bản ghi cũ và gọi AI sinh lại nội dung; kết quả mới được ghi đè vào DB."""
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
    nội dung (tốn một lần gọi AI) và cache lại như bình thường.
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
    return await service.analyze_student_skills(
        db,
        payload,
        user_id=current_user.id if current_user else None,
    )
