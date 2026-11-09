import uuid
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.roadmap import MajorRoadmap, StudentRoadmapProgress
from app.models.taxonomy import Major, MajorSkill, Skill, SkillPrerequisite
from app.models.assessment import StudentGrade, StudentDiagnosticTest
from app.schemas.roadmap import (
    MajorRoadmapResponse,
    RoadmapDataSchema,
    RoadmapMilestoneSchema,
    ReferenceMaterialSchema,
    StudentRoadmapProgressUpdate,
    StudentRoadmapProgressResponse,
)
from app.services.gap_roadmap_engine.gap_engine import (
    infer_mastered_skills_from_grades,
    infer_mastered_skills_from_diagnostic_tests,
    analyze_competency_gaps,
)


def generate_static_fallback_roadmap(major_code: str, major_name: str) -> Dict[str, Any]:
    """
    Generates a standardized static fallback study roadmap compliant with proposal NFR01 & NFR05.
    Guarantees instant response (<1s) even during AI API outages or for majors awaiting curation.
    """
    return {
        "milestones": [
            {
                "step": 1,
                "title": f"Nền tảng kiến thức nhập môn ngành {major_name}",
                "description": f"Xây dựng cơ sở lý thuyết, tư duy logic và các nguyên lý cơ bản của ngành {major_name}.",
                "duration_weeks": 4,
                "learning_objectives": [
                    "Nắm vững các thuật ngữ chuyên ngành cơ bản",
                    "Hiểu cấu trúc chương trình đào tạo theo chuẩn Bộ GD&ĐT",
                    "Thực hành bài tập tư duy nền tảng"
                ],
                "actions": [
                    "Đọc tài liệu giáo trình nhập môn từ thư viện trường đại học",
                    "Hoàn thành các bài tập kiểm tra trắc nghiệm đánh giá năng lực",
                    "Tham gia diễn đàn sinh viên ngành"
                ]
            },
            {
                "step": 2,
                "title": f"Phát triển kỹ năng cốt lõi và công cụ chuyên ngành",
                "description": "Làm quen với các công cụ thực hành, phương pháp luận nghiên cứu và phân tích số liệu.",
                "duration_weeks": 6,
                "learning_objectives": [
                    "Sử dụng thành thạo phần mềm/công cụ cơ bản của ngành",
                    "Phân tích các case study điển hình",
                    "Làm việc nhóm giải quyết bài toán giả định"
                ],
                "actions": [
                    "Thực hành đồ án nhỏ (mini project) theo nhóm",
                    "Tham gia các khóa học mở trực tuyến (MOOC) uy tín",
                    "Đọc bài báo tổng quan thị trường lao động"
                ]
            },
            {
                "step": 3,
                "title": "Định hướng chuyên sâu và chuẩn bị chuyển tiếp đại học",
                "description": "Kết nối kiến thức THPT với môi trường học tập tự chủ bậc đại học.",
                "duration_weeks": 4,
                "learning_objectives": [
                    "Xác định nhánh chuyên ngành hẹp phù hợp",
                    "Lập kế hoạch phát triển kỹ năng ngoại ngữ và mềm",
                    "Tìm hiểu các cơ hội thực tập, học bổng"
                ],
                "actions": [
                    "Xây dựng hồ sơ năng lực cá nhân (Portfolio)",
                    "Trao đổi cùng cố vấn học tập hoặc cựu sinh viên",
                    "Đăng ký tham quan open-day của các cơ sở đào tạo"
                ]
            }
        ],
        "prerequisite_knowledge": [
            "Kiến thức tổ hợp môn xét tuyển tương ứng (Toán, KHTN hoặc KHXH)",
            "Kỹ năng tự học và tra cứu tài liệu trực tuyến",
            "Ngoại ngữ cơ bản (Tiếng Anh chuyên ngành)"
        ],
        "target_skills": [
            "Tư duy phản biện và giải quyết vấn đề",
            "Kỹ năng ứng dụng công nghệ và công cụ ngành",
            "Kỹ năng giao tiếp và làm việc nhóm hiệu quả"
        ],
        "reference_materials": [
            {
                "title": f"Chương trình khung đào tạo ngành {major_name}",
                "author_or_institution": "Bộ Giáo dục và Đào tạo / Các trường Đại học trọng điểm",
                "url": "https://moet.gov.vn",
                "material_type": "curriculum"
            },
            {
                "title": "Khóa học mở nhập môn chuyên ngành",
                "author_or_institution": "Nền tảng Học trực tuyến Mở Quốc gia & Quốc tế",
                "url": "https://coursera.org",
                "material_type": "online_course"
            }
        ],
        "source_title": "Bộ chuẩn chương trình đào tạo đại học Việt Nam (Thông tư 09/2022/TT-BGDĐT)",
        "source_url": "https://moet.gov.vn",
        "source_page": "Khung chuẩn"
    }


async def get_cached_major_roadmap(db: AsyncSession, major_code: str) -> MajorRoadmapResponse:
    """
    Direct indexed cache lookup (<= 1s response latency).
    If verified roadmap is cached in major_roadmaps, serves it immediately.
    If absent or DB connection fails, generates and returns a verified static fallback roadmap.
    """
    roadmap = None
    major_name = None

    try:
        query = select(MajorRoadmap).where(MajorRoadmap.major_code == major_code)
        result = await db.execute(query)
        roadmap = result.scalar_one_or_none()

        if roadmap:
            return MajorRoadmapResponse(
                id=roadmap.id,
                major_code=roadmap.major_code,
                title=roadmap.title,
                version=roadmap.version,
                roadmap_data=RoadmapDataSchema(**roadmap.roadmap_data),
                is_fallback=roadmap.is_fallback,
                created_at=roadmap.created_at,
                updated_at=roadmap.updated_at
            )

        # If not in cache, find major name to create static fallback
        major_res = await db.execute(select(Major).where(Major.major_code == major_code))
        major = major_res.scalar_one_or_none()
        major_name = major.name if major else None
    except Exception as db_err:
        logger.warning(f"[RoadmapService] Database query bypassed/unavailable for {major_code}: {db_err}")

    # Fallback to catalog seed data for exact major name
    if not major_name:
        try:
            from scripts.seed_tt09 import MAJORS_DATA
            for m in MAJORS_DATA:
                if m["major_code"] == major_code:
                    major_name = m["name"]
                    break
        except Exception:
            pass

    if not major_name:
        major_name = f"Ngành đào tạo (Mã {major_code})"

    fallback_data = generate_static_fallback_roadmap(major_code, major_name)

    try:
        fallback_entry = MajorRoadmap(
            major_code=major_code,
            title=f"Lộ trình học tập chuẩn hóa: {major_name}",
            version="1.0-fallback",
            roadmap_data=fallback_data,
            is_fallback=True,
            fallback_template=fallback_data,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(fallback_entry)
        await db.commit()
        await db.refresh(fallback_entry)

        return MajorRoadmapResponse(
            id=fallback_entry.id,
            major_code=fallback_entry.major_code,
            title=fallback_entry.title,
            version=fallback_entry.version,
            roadmap_data=RoadmapDataSchema(**fallback_entry.roadmap_data),
            is_fallback=True,
            created_at=fallback_entry.created_at,
            updated_at=fallback_entry.updated_at
        )
    except Exception:
        # If DB write fails, return in-memory static verified roadmap immediately
        return MajorRoadmapResponse(
            id=str(uuid.uuid4()),
            major_code=major_code,
            title=f"Lộ trình học tập chuẩn hóa: {major_name}",
            version="1.0-fallback",
            roadmap_data=RoadmapDataSchema(**fallback_data),
            is_fallback=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )


async def get_student_major_skill_gaps(
    db: AsyncSession,
    user_id: uuid.UUID,
    major_code: str
) -> Dict[str, Any]:
    """
    Performs deterministic Competency Gap Analysis for a student targeting a specific major_code (FR04, FR06).
    """
    # 1. Fetch Major and its required skills
    major_query = select(Major).where(Major.major_code == major_code).options(
        selectinload(Major.major_skills).selectinload(MajorSkill.skill)
    )
    major_res = await db.execute(major_query)
    major = major_res.scalar_one_or_none()
    if not major:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Major with code {major_code} not found."
        )

    # 2. Fetch Student Grades & Diagnostic Tests
    grade_res = await db.execute(
        select(StudentGrade).where(StudentGrade.user_id == user_id).order_by(StudentGrade.created_at.desc())
    )
    grade = grade_res.scalar_one_or_none()
    raw_grades = grade.grades_by_subject if grade else {}

    diag_res = await db.execute(
        select(StudentDiagnosticTest).where(StudentDiagnosticTest.user_id == user_id)
    )
    diag_tests = list(diag_res.scalars().all())

    mastered = infer_mastered_skills_from_grades(raw_grades)
    diag_mastered = infer_mastered_skills_from_diagnostic_tests([
        {"skill_code": d.skill_code, "score": d.score, "is_passed": d.is_passed}
        for d in diag_tests
    ])
    mastered.update(diag_mastered)

    # 3. Fetch Skill Prerequisites Map
    prereq_res = await db.execute(
        select(SkillPrerequisite).options(
            selectinload(SkillPrerequisite.skill),
            selectinload(SkillPrerequisite.prerequisite_skill)
        )
    )
    prereqs = list(prereq_res.scalars().all())
    prereq_map: Dict[str, List[str]] = {}
    for p in prereqs:
        t_code = p.skill.skill_code if p.skill else ""
        s_code = p.prerequisite_skill.skill_code if p.prerequisite_skill else ""
        if t_code and s_code:
            prereq_map.setdefault(t_code, []).append(s_code)

    # 4. Analyze Gaps
    major_skills_list = [
        {
            "skill_code": ms.skill.skill_code,
            "name": ms.skill.name,
            "skill_type": ms.skill.skill_type.value if hasattr(ms.skill.skill_type, "value") else str(ms.skill.skill_type),
            "importance": ms.importance_level
        }
        for ms in major.major_skills if ms.skill
    ]

    overall_gaps, missing_pre, missing_tar = analyze_competency_gaps(
        required_major_skills=major_skills_list,
        skill_prerequisites_map=prereq_map,
        mastered_skill_codes=mastered
    )

    return {
        "user_id": user_id,
        "major_code": major_code,
        "major_name": major.name,
        "mastered_skills": sorted(list(mastered)),
        "competency_gaps": overall_gaps,
        "missing_prerequisites": missing_pre,
        "missing_target_skills": missing_tar,
        "has_gap": len(overall_gaps) > 0,
        "readiness_summary": (
            f"Bạn đã thành thạo {len(mastered)} kỹ năng nền tảng. "
            f"Cần chuẩn bị bổ sung {len(missing_pre)} kiến thức tiên quyết và {len(missing_tar)} kỹ năng chuyên ngành."
            if overall_gaps else "Bạn đã đáp ứng trọn vẹn toàn bộ các kỹ năng tiên quyết yêu cầu của ngành này!"
        )
    }


async def update_student_roadmap_progress(
    db: AsyncSession,
    user_id: uuid.UUID,
    payload: StudentRoadmapProgressUpdate
) -> StudentRoadmapProgress:
    query = select(StudentRoadmapProgress).where(
        StudentRoadmapProgress.user_id == user_id,
        StudentRoadmapProgress.major_code == payload.major_code
    )
    res = await db.execute(query)
    progress = res.scalar_one_or_none()

    if progress:
        progress.current_step = payload.current_step
        progress.completed_milestones = payload.completed_milestones
        if payload.personalized_schedule:
            progress.personalized_schedule = payload.personalized_schedule
        progress.last_activity_at = datetime.now(timezone.utc)
    else:
        progress = StudentRoadmapProgress(
            user_id=user_id,
            major_code=payload.major_code,
            current_step=payload.current_step,
            completed_milestones=payload.completed_milestones,
            personalized_schedule=payload.personalized_schedule,
            started_at=datetime.now(timezone.utc),
            last_activity_at=datetime.now(timezone.utc)
        )
        db.add(progress)

    await db.commit()
    await db.refresh(progress)
    return progress


async def get_student_roadmap_progress(
    db: AsyncSession,
    user_id: uuid.UUID,
    major_code: str
) -> Optional[StudentRoadmapProgress]:
    query = select(StudentRoadmapProgress).where(
        StudentRoadmapProgress.user_id == user_id,
        StudentRoadmapProgress.major_code == major_code
    )
    res = await db.execute(query)
    return res.scalar_one_or_none()
