from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_current_user
from app.models.identity import User
from app.schemas.recommender import (
    RecommendationRequest,
    RecommendationResponse,
    EvaluateProfileRequest,
)
from app.services.recommender import service

router = APIRouter(prefix="/recommender", tags=["Deterministic Explainable Recommender"])


@router.post("/recommend", response_model=RecommendationResponse, status_code=status.HTTP_200_OK)
async def get_major_recommendations(
    payload: RecommendationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Tính điểm tương thích 3 trụ cột XAI kết hợp ràng buộc điểm chuẩn, điểm liệt và khối xét tuyển.
    GUARDRAIL: 100% toán học tất định, LLM không được phép thay đổi thứ hạng hay điểm số.
    """
    return await service.calculate_3pillar_recommendations(db, current_user.id, payload, raise_if_unassessed=True)


@router.post("/evaluate", status_code=status.HTTP_200_OK)
async def evaluate_majors_with_constraints(
    payload: EvaluateProfileRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Đánh giá danh mục đang hoạt động với bằng chứng và điều kiện tham chiếu:
    - Trả về 422 CHUA_HOAN_THANH_BAI_TEST nếu học sinh chưa có dữ liệu bài test/điểm số.
    - Nhận trực tiếp dữ liệu bài làm hiện tại hoặc tự động nạp từ CSDL của user đã đăng nhập.
    - Không dùng giới tính hoặc xu hướng để vượt điều kiện tham chiếu.
    """
    if payload.assessment_id and current_user is None:
        raise HTTPException(401, "Login required to use a saved assessment.")
    target_user_id = current_user.id if current_user else None
    eff_gender = current_user.gender if current_user else payload.gender
    eff_grade_level = current_user.grade_level if current_user else payload.grade_level

    inline_profile = payload.model_dump(exclude_unset=True, exclude={"top_k", "custom_weights"})
    inline_profile.update(gender=eff_gender, grade_level=eff_grade_level)
    return await service.evaluate_dashboard_profile_bundle(
        db=db,
        user_id=target_user_id,
        top_k=payload.top_k,
        custom_weights=payload.custom_weights,
        inline_profile=inline_profile,
        raise_if_unassessed=True,
        persist_history=False,
        user_name=current_user.full_name if current_user else None,
        gender=eff_gender,
        grade_level=eff_grade_level,
    )


@router.post("/analyze-aspiration", status_code=status.HTTP_200_OK)
async def analyze_aspiration_endpoint(
    payload: EvaluateProfileRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint chuyên biệt của AI Agent Phân tích Nguyện vọng & Đối chiếu Kết quả Trắc nghiệm.
    Cho phép cập nhật hoặc phân tích lại nguyện vọng nghề nghiệp ngay trên Dashboard / Trắc nghiệm.
    """
    if payload.assessment_id and current_user is None:
        raise HTTPException(401, "Login required to use a saved assessment.")
    target_user_id = current_user.id if current_user else None
    eff_gender = current_user.gender if current_user else payload.gender
    eff_grade_level = current_user.grade_level if current_user else payload.grade_level

    inline_profile = payload.model_dump(exclude_unset=True, exclude={"top_k", "custom_weights"})
    inline_profile.update(gender=eff_gender, grade_level=eff_grade_level)
    bundle = await service.evaluate_dashboard_profile_bundle(
        db=db,
        user_id=target_user_id,
        top_k=payload.top_k,
        custom_weights=payload.custom_weights,
        inline_profile=inline_profile,
        raise_if_unassessed=True,
        persist_history=False,
        user_name=current_user.full_name if current_user else None,
        gender=eff_gender,
        grade_level=eff_grade_level,
    )
    return bundle.get("aspirationAnalysis")


@router.get("/dashboard/overview")
async def get_dashboard_overview(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Trả về dữ liệu tổng quan cho Dashboard từ hồ sơ thực tế của user trong CSDL.
    Nếu user chưa làm bài test, trả về trạng thái rỗng (tuyệt đối không trả đề xuất mặc định giả lập).
    """
    if not current_user:
        return {
            "has_assessment": False,
            "code": "CHUA_HOAN_THANH_BAI_TEST",
            "user_name": "Học sinh",
            "riasecData": [],
            "bestBlockStats": None,
            "majors": [],
            "funnel": {"tier1_fields": [], "all_majors": []},
        }

    from fastapi import HTTPException
    try:
        return await service.evaluate_dashboard_profile_bundle(
            db=db,
            user_id=current_user.id,
            top_k=15,
            raise_if_unassessed=True,
            persist_history=False,
            user_name=current_user.full_name,
            gender=current_user.gender,
            grade_level=current_user.grade_level,
        )
    except HTTPException as exc:
        if exc.status_code != 422:
            raise
        return {
            "has_assessment": False,
            "code": "CHUA_HOAN_THANH_BAI_TEST",
            "user_name": current_user.full_name,
            "gender": current_user.gender,
            "grade_level": current_user.grade_level,
            "riasecData": [],
            "bestBlockStats": None,
            "majors": [],
            "funnel": {"tier1_fields": [], "all_majors": []},
        }


@router.get("/majors")
async def get_recommended_majors_list(
    top_k: int = Query(15, ge=1, le=500),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Trả về danh sách ngành đề xuất theo hồ sơ user (tương thích DTO Frontend)."""
    target_user_id = current_user.id if current_user else None
    req = RecommendationRequest(
        top_k=top_k,
        gender=current_user.gender if current_user else None,
        grade_level=current_user.grade_level if current_user else None,
    )
    rec_resp = await service.calculate_3pillar_recommendations(
        db,
        target_user_id,
        req,
        persist_history=False,
        raise_if_unassessed=True,
    )
    return rec_resp.recommendations
