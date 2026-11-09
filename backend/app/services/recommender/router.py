from typing import Optional, List, Dict, Any
from collections import defaultdict
import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_current_user
from app.models.identity import User
from app.schemas.recommender import RecommendationRequest, RecommendationResponse
from app.services.recommender import service

router = APIRouter(prefix="/recommender", tags=["Deterministic Explainable Recommender"])


@router.post("/recommend", response_model=RecommendationResponse, status_code=status.HTTP_200_OK)
async def get_major_recommendations(
    payload: RecommendationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Computes deterministic 3-pillar major compatibility scores:
    1. Cosine similarity on 6-dimensional RIASEC vectors
    2. National Z-score CDF normalization for admission subject blocks
    3. Rule-based cognitive preference mapping
    
    GUARDRAIL: 100% deterministic mathematical ranking. LLMs are strictly forbidden from altering scores.
    """
    return await service.calculate_3pillar_recommendations(db, current_user.id, payload)


@router.get("/dashboard/overview")
async def get_dashboard_overview(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns complete dashboard dataset ready for frontend Dashboard display,
    including 2-tier recommendation funnel and dual RIASEC + Academic radar data.
    """
    target_user_id = current_user.id if current_user else uuid.UUID("00000000-0000-0000-0000-000000000001")
    req = RecommendationRequest(top_k=15)
    rec_resp = await service.calculate_3pillar_recommendations(db, target_user_id, req)
    
    # Dual Radar Data: Holland Vocational Interest + Normalized Academic Readiness
    riasecData = [
        { "key": "R", "label": "Thực tế", "value": 68, "academicValue": 78, "subjectMapping": "Vật lý & Công nghệ", "fullMark": 100 },
        { "key": "I", "label": "Nghiên cứu", "value": 92, "academicValue": 88, "subjectMapping": "Toán & Tin học", "fullMark": 100 },
        { "key": "A", "label": "Nghệ thuật", "value": 64, "academicValue": 72, "subjectMapping": "Ngữ văn & Mỹ thuật", "fullMark": 100 },
        { "key": "S", "label": "Xã hội", "value": 78, "academicValue": 85, "subjectMapping": "Lịch sử & GDCD", "fullMark": 100 },
        { "key": "E", "label": "Quản lý", "value": 72, "academicValue": 80, "subjectMapping": "Tiếng Anh & Kinh tế", "fullMark": 100 },
        { "key": "C", "label": "Nghiệp vụ", "value": 60, "academicValue": 82, "subjectMapping": "Toán & Tin học", "fullMark": 100 },
    ]
    
    scoreBarData = [
        { "name": "Sở thích", "value": 92 },
        { "name": "Học lực", "value": 84 },
        { "name": "Nhận thức", "value": 91 },
    ]

    # Build 2-Tier Recommendation Funnel
    category_groups = defaultdict(list)
    for major in rec_resp.recommendations:
        cat = getattr(major, "category", None) or "Khác"
        category_groups[cat].append(major)

    tier1_fields = []
    field_icons = {
        "Máy tính & Công nghệ thông tin": "💻",
        "Kinh doanh & Quản lý": "📊",
        "Công nghệ kỹ thuật": "⚙️",
        "Kỹ thuật & Công nghiệp": "🔧",
        "Sức khỏe & Y dược": "🩺",
        "Khoa học giáo dục & Đào tạo giáo viên": "📚",
        "Khoa học xã hội & Hành vi": "🌐",
        "Kiến trúc & Xây dựng": "🏛️",
        "Nghệ thuật & Thiết kế": "🎨",
        "Nhân văn & Ngôn ngữ": "📖",
        "Báo chí & Thông tin": "📰",
        "Pháp luật": "⚖️",
    }

    for cat_name, majors_in_cat in category_groups.items():
        avg_score = sum(m.overall_score for m in majors_in_cat) / len(majors_in_cat)
        tier1_fields.append({
            "field_name": cat_name,
            "icon": field_icons.get(cat_name, "🎓"),
            "match": int(round(avg_score * 100)),
            "majors_count": len(majors_in_cat),
            "majors": majors_in_cat[:3]  # Top 2-3 specific majors for Tier 2
        })

    tier1_fields.sort(key=lambda f: f["match"], reverse=True)
    top_tier1 = tier1_fields[:3]

    return {
        "user_name": current_user.full_name if current_user else "Linh Nguyễn",
        "riasecData": riasecData,
        "scoreBarData": scoreBarData,
        "majors": rec_resp.recommendations[:5],
        "funnel": {
            "tier1_fields": top_tier1,
            "all_majors": rec_resp.recommendations
        }
    }


@router.get("/majors")
async def get_recommended_majors_list(
    top_k: int = 10,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns list of top recommended majors with FE compatibility fields."""
    target_user_id = current_user.id if current_user else uuid.UUID("00000000-0000-0000-0000-000000000001")
    req = RecommendationRequest(top_k=top_k)
    rec_resp = await service.calculate_3pillar_recommendations(db, target_user_id, req)
    return rec_resp.recommendations
