from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.identity import User
from app.schemas.roadmap import (
    MajorRoadmapResponse,
    StudentRoadmapProgressUpdate,
    StudentRoadmapProgressResponse,
    RoadmapWeekSchema,
)
from app.schemas.rag import (
    GuidancePersonalizationRequest,
    GuidancePersonalizationResponse,
)
from app.services.gap_roadmap_engine import service

router = APIRouter(prefix="/roadmap", tags=["Gap Analysis & Roadmap Engine"])


@router.get("/roadmaps/{major_code}", response_model=MajorRoadmapResponse)
async def get_major_roadmap(
    major_code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves verified study roadmap directly indexed by major_code from cache (<= 1s response time).
    Falls back gracefully to static verified template if detailed curriculum is still in curation.
    """
    return await service.get_cached_major_roadmap(db, major_code)


@router.get("/gap-analysis/{major_code}")
async def get_major_gap_analysis(
    major_code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Performs deterministic Competency Gap Analysis comparing student's academic grades
    and diagnostic checks against major's prerequisite knowledge and target competencies.
    """
    return await service.get_student_major_skill_gaps(db, current_user.id, major_code)


@router.post("/roadmaps/{major_code}/personalized", response_model=GuidancePersonalizationResponse)
async def personalize_roadmap_for_student(
    major_code: str,
    weekly_hours_available: int = Query(default=10, ge=2, le=40),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Guidance RAG orchestration (FR06, DF06):
    Synthesizes student's analyzed skill gaps with the verified major roadmap
    to formulate personalized weekly tasks. Includes strict 8s timeout with static fallback.
    """
    from app.services.llamaindex_rag_orchestrator.guidance_rag import personalize_guidance
    
    gap_result = await service.get_student_major_skill_gaps(db, current_user.id, major_code)
    missing_skills = [s["skill_name"] for s in gap_result.get("missing_skills", [])]
    
    req = GuidancePersonalizationRequest(
        major_code=major_code,
        user_id=current_user.id,
        missing_skills=missing_skills,
        weekly_hours_available=weekly_hours_available
    )
    return await personalize_guidance(db, req)


@router.post("/progress", response_model=StudentRoadmapProgressResponse)
async def update_progress(
    payload: StudentRoadmapProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Updates student self-study checklist and milestone completion status for a major roadmap."""
    return await service.update_student_roadmap_progress(db, current_user.id, payload)


@router.get("/progress/{major_code}", response_model=StudentRoadmapProgressResponse)
async def get_progress(
    major_code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves current student study execution progress for a given major."""
    prog = await service.get_student_roadmap_progress(db, current_user.id, major_code)
    if not prog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active roadmap progress found for major {major_code}."
        )
    return prog


@router.get("/weeks/{major_code}", response_model=List[RoadmapWeekSchema])
@router.get("/weeks", response_model=List[RoadmapWeekSchema])
async def get_roadmap_weeks_for_fe(
    major_code: str = "7480101",
    db: AsyncSession = Depends(get_db)
):
    """Returns 4-week roadmap formatted directly for frontend RoadmapView."""
    roadmap_res = await service.get_cached_major_roadmap(db, major_code)
    milestones = roadmap_res.roadmap_data.milestones if roadmap_res and roadmap_res.roadmap_data else []
    
    eyebrows = ["Nền tảng", "Thực hành", "Dự án", "Bứt phá"]
    weeks: List[RoadmapWeekSchema] = []
    
    for idx, m in enumerate(milestones[:4]):
        w_num = idx + 1
        eyebrow = eyebrows[idx] if idx < len(eyebrows) else f"Tuần {w_num}"
        content_lines = [
            f"## Mục tiêu tuần {w_num}: {m.title}",
            m.description,
            "\n### Nhiệm vụ trọng tâm:"
        ]
        for a in m.actions:
            content_lines.append(f"- {a}")
        if m.learning_objectives:
            content_lines.append("\n### Năng lực cần đạt:")
            for o in m.learning_objectives:
                content_lines.append(f"- {o}")
                
        weeks.append(RoadmapWeekSchema(
            id=f"week-{w_num}",
            week=w_num,
            eyebrow=eyebrow,
            title=m.title,
            description=m.description,
            content="\n".join(content_lines),
            tasks=m.actions if m.actions else ["Đọc tài liệu tổng quan", "Thực hành bài tập nhỏ", "Đánh giá tiến độ"]
        ))
    
    while len(weeks) < 4:
        w_num = len(weeks) + 1
        weeks.append(RoadmapWeekSchema(
            id=f"week-{w_num}",
            week=w_num,
            eyebrow=eyebrows[w_num - 1] if w_num - 1 < len(eyebrows) else f"Tuần {w_num}",
            title=f"Giai đoạn {w_num}: Đánh giá & Phát triển",
            description="Tự đánh giá năng lực và chuẩn bị cho kỳ thi tốt nghiệp THPT.",
            content=f"## Mục tiêu tuần {w_num}\nHoàn thành bài tập mẫu và đánh giá kỹ năng.",
            tasks=["Hoàn thành bài đánh giá", "Cập nhật hồ sơ năng lực", "Lập kế hoạch 90 ngày"]
        ))
        
    return weeks
