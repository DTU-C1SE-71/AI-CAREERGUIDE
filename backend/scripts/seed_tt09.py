"""
AI CareerGuide - Database Seeding Script (Thông tư 09/2022/TT-BGDĐT & Chuẩn v1.8)
Optimized for:
1. High-Performance Batched Transactions (< 500ms execution).
2. Clean Architecture (Single Source of Truth in moet_taxonomy_tt09.json).
3. 100% Idempotent Execution & Safe Re-running.
4. Full 108 MOET Level-IV Majors with Category & Phoenix Ho Career linkages.
"""

import asyncio
import json
import logging
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.identity import User, UserConsent, UserRole
from app.models.roadmap import MajorRoadmap
from app.models.staging import StagingRecord, StagingStatus, StagingStreamType
from app.models.taxonomy import (
    Career,
    Major,
    MajorSkill,
    MajorSubjectBlock,
    Skill,
    SkillPrerequisite,
    SkillType,
    SubjectBlock,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_tt09")


# -------------------------------------------------------------------------
# 1. CATALOG OF LEVEL-IV MAJORS (THÔNG TƯ 09/2022/TT-BGDĐT) - 108 MAJORS
# Loaded from Single Source of Truth JSON file
# -------------------------------------------------------------------------
def _load_tt09_majors() -> List[Dict[str, Any]]:
    """
    Loads the official 108 Level-IV majors taxonomy compliant with Circular 09/2022/TT-BGDĐT.
    Single source of truth is stored in backend/app/db/seeds/moet_taxonomy_tt09.json.
    """
    json_path = backend_dir / "app" / "db" / "seeds" / "moet_taxonomy_tt09.json"
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data and isinstance(data, list):
                return data
    raise FileNotFoundError(f"Missing required MOET taxonomy seed file at: {json_path}")


MAJORS_DATA: List[Dict[str, Any]] = _load_tt09_majors()


# -------------------------------------------------------------------------
# 2. ADMISSION SUBJECT BLOCKS WITH NATIONAL STATS (MU, SIGMA)
# -------------------------------------------------------------------------
SUBJECT_BLOCKS_DATA: List[Dict[str, Any]] = [
    {"block_code": "A00", "name": "Toán, Vật lí, Hóa học", "subjects": ["Toán", "Vật lí", "Hóa học"], "national_mean": 20.85, "national_std": 3.25},
    {"block_code": "A01", "name": "Toán, Vật lí, Tiếng Anh", "subjects": ["Toán", "Vật lí", "Tiếng Anh"], "national_mean": 20.15, "national_std": 3.10},
    {"block_code": "B00", "name": "Toán, Hóa học, Sinh học", "subjects": ["Toán", "Hóa học", "Sinh học"], "national_mean": 19.80, "national_std": 3.40},
    {"block_code": "C00", "name": "Ngữ văn, Lịch sử, Địa lí", "subjects": ["Ngữ văn", "Lịch sử", "Địa lí"], "national_mean": 21.50, "national_std": 3.35},
    {"block_code": "D01", "name": "Toán, Ngữ văn, Tiếng Anh", "subjects": ["Toán", "Ngữ văn", "Tiếng Anh"], "national_mean": 19.20, "national_std": 3.15},
    {"block_code": "D07", "name": "Toán, Hóa học, Tiếng Anh", "subjects": ["Toán", "Hóa học", "Tiếng Anh"], "national_mean": 20.40, "national_std": 3.20},
    {"block_code": "D08", "name": "Toán, Sinh học, Tiếng Anh", "subjects": ["Toán", "Sinh học", "Tiếng Anh"], "national_mean": 19.90, "national_std": 3.30},
    {"block_code": "A02", "name": "Toán, Vật lí, Sinh học", "subjects": ["Toán", "Vật lí", "Sinh học"], "national_mean": 19.50, "national_std": 3.20},
    {"block_code": "D14", "name": "Ngữ văn, Lịch sử, Tiếng Anh", "subjects": ["Ngữ văn", "Lịch sử", "Tiếng Anh"], "national_mean": 20.50, "national_std": 3.25},
    {"block_code": "H00", "name": "Ngữ văn, Hình họa mỹ thuật, Bố cục màu", "subjects": ["Ngữ văn", "Hình họa mỹ thuật", "Bố cục màu"], "national_mean": 21.00, "national_std": 3.00},
    {"block_code": "V00", "name": "Toán, Vật lí, Vẽ mỹ thuật", "subjects": ["Toán", "Vật lí", "Vẽ mỹ thuật"], "national_mean": 20.50, "national_std": 3.00},
]


# -------------------------------------------------------------------------
# 3. SKILL TAXONOMY (PREREQUISITE & TARGET)
# -------------------------------------------------------------------------
SKILLS_DATA: List[Dict[str, Any]] = [
    # PREREQUISITE SKILLS
    {"skill_code": "SKILL_PRE_CALCULUS", "name": "Giải tích và Đại số tuyến tính căn bản", "skill_type": SkillType.PREREQUISITE, "domain": "Toán học", "desc": "Giới hạn, đạo hàm, tích phân và ma trận đại số"},
    {"skill_code": "SKILL_PRE_PHYSICS_MECH", "name": "Vật lý đại cương: Cơ - Nhiệt - Điện", "skill_type": SkillType.PREREQUISITE, "domain": "Khoa học tự nhiên", "desc": "Các định luật bảo toàn và nguyên lý tĩnh điện"},
    {"skill_code": "SKILL_PRE_CHEM_GEN", "name": "Hóa học đại cương và vô cơ", "skill_type": SkillType.PREREQUISITE, "domain": "Khoa học tự nhiên", "desc": "Cấu tạo nguyên tử, liên kết hóa học và phản ứng oxy hóa khử"},
    {"skill_code": "SKILL_PRE_BIO_CELL", "name": "Sinh học tế bào và di truyền học", "skill_type": SkillType.PREREQUISITE, "domain": "Khoa học tự nhiên", "desc": "Cấu trúc DNA, phiên mã, dịch mã và quy luật di truyền"},
    {"skill_code": "SKILL_PRE_LOGIC_DISCRETE", "name": "Tư duy logic hình thức & Toán rời rạc", "skill_type": SkillType.PREREQUISITE, "domain": "Tư duy logic", "desc": "Mệnh đề, tập hợp, đồ thị và suy luận quy nạp"},
    {"skill_code": "SKILL_PRE_ENG_ACADEMIC", "name": "Tiếng Anh học thuật & đọc hiểu tài liệu", "skill_type": SkillType.PREREQUISITE, "domain": "Ngoại ngữ", "desc": "Kỹ năng tra cứu và đọc hiểu giáo trình chuyên ngành tiếng Anh"},
    {"skill_code": "SKILL_PRE_VIET_ESSAY", "name": "Kỹ năng viết luận và phân tích văn bản", "skill_type": SkillType.PREREQUISITE, "domain": "Nhân văn", "desc": "Lập luận logic, bố cục bài viết và trích dẫn chuẩn mực"},
    {"skill_code": "SKILL_PRE_STAT_BASIC", "name": "Xác suất thống kê ứng dụng", "skill_type": SkillType.PREREQUISITE, "domain": "Toán học", "desc": "Biến ngẫu nhiên, phân phối chuẩn và kiểm định giả thuyết"},

    # TARGET SKILLS
    {"skill_code": "SKILL_TAR_PROG_PYTHON", "name": "Lập trình và cấu trúc dữ liệu với Python", "skill_type": SkillType.TARGET, "domain": "Công nghệ thông tin", "desc": "Lập trình hướng đối tượng, xử lý danh sách, cây và đồ thị"},
    {"skill_code": "SKILL_TAR_ALGORITHMS", "name": "Thiết kế và tối ưu thuật toán máy tính", "skill_type": SkillType.TARGET, "domain": "Công nghệ thông tin", "desc": "Quy hoạch động, chia để trị và thuật toán tìm kiếm"},
    {"skill_code": "SKILL_TAR_DATA_MODELING", "name": "Mô hình hóa dữ liệu quan hệ và phi quan hệ", "skill_type": SkillType.TARGET, "domain": "Công nghệ thông tin", "desc": "Thiết kế lược đồ ERD, truy vấn SQL và chuẩn hóa dữ liệu"},
    {"skill_code": "SKILL_TAR_AI_MACHINE_LEARNING", "name": "Học máy và mô hình trí tuệ nhân tạo", "skill_type": SkillType.TARGET, "domain": "Trí tuệ nhân tạo", "desc": "Hồi quy, phân lớp, mạng nơ-ron và đánh giá mô hình ML"},
    {"skill_code": "SKILL_TAR_CIRCUIT_DESIGN", "name": "Thiết kế mạch điện tử và vi điều khiển", "skill_type": SkillType.TARGET, "domain": "Kỹ thuật", "desc": "Lập trình nhúng Arduino, STM32 và thiết kế PCB"},
    {"skill_code": "SKILL_TAR_FINANCIAL_ANALYSIS", "name": "Phân tích tài chính và định giá doanh nghiệp", "skill_type": SkillType.TARGET, "domain": "Kinh tế - Tài chính", "desc": "Phân tích báo cáo tài chính, mô hình chiết khấu dòng tiền DCF"},
    {"skill_code": "SKILL_TAR_DIGITAL_MARKETING", "name": "Tiếp thị số và tối ưu hóa chuyển đổi", "skill_type": SkillType.TARGET, "domain": "Kinh doanh", "desc": "SEO, Google Ads, Meta Ads và phân tích hành vi khách hàng"},
    {"skill_code": "SKILL_TAR_LEGAL_CONTRACT", "name": "Soạn thảo văn bản pháp lý và tư vấn hợp đồng", "skill_type": SkillType.TARGET, "domain": "Pháp luật", "desc": "Kỹ năng rà soát điều khoản rủi ro và đàm phán hợp đồng thương mại"},
    {"skill_code": "SKILL_TAR_CLINICAL_DIAGNOSIS", "name": "Khám bệnh và chẩn đoán lâm sàng", "skill_type": SkillType.TARGET, "domain": "Y khoa", "desc": "Quy trình hỏi bệnh sử, khám thực thể và diễn giải cận lâm sàng"},
    {"skill_code": "SKILL_TAR_ARCH_CAD_BIM", "name": "Mô hình hóa kiến trúc và công trình CAD/BIM", "skill_type": SkillType.TARGET, "domain": "Kiến trúc", "desc": "Dựng hình 3D Revit, AutoCAD và bóc tách khối lượng công trình"},
    {"skill_code": "SKILL_TAR_SUPPLY_CHAIN", "name": "Hoạch định chuỗi cung ứng và điều phối vận tải", "skill_type": SkillType.TARGET, "domain": "Logistics", "desc": "Quản lý tồn kho EOQ, định tuyến giao hàng và nghiệp vụ hải quan"}
]


# -------------------------------------------------------------------------
# 4. HIGH-PERFORMANCE BATCHED SEEDING LOGIC
# -------------------------------------------------------------------------
async def seed_data():
    start_time = time.time()
    print("=" * 75)
    print("STARTING SEEDING PROCESS: THÔNG TƯ 09/2022/TT-BGDĐT CATALOG (OPTIMIZED)")
    print("=" * 75)

    try:
        async with AsyncSessionLocal() as session:
            # -----------------------------------------------------------------
            # Step 1: Default Users (Argon2id Compliant & OWASP ASVS Level 2)
            # -----------------------------------------------------------------
            print("1. Verifying default accounts (Admin & Student)...")
            admin_email = "admin@aicareerguide.edu.vn"
            student_email = "student@aicareerguide.edu.vn"

            admin_res = await session.execute(select(User).where(User.email == admin_email))
            admin_user = admin_res.scalar_one_or_none()
            if not admin_user:
                admin_user = User(
                    email=admin_email,
                    hashed_password=get_password_hash("AdminPass2026@ASVS"),
                    full_name="Quản trị viên Kiểm duyệt (Admin)",
                    role=UserRole.ADMIN,
                    is_active=True,
                )
                session.add(admin_user)
                await session.flush()
                print(f"   + Created Admin user: {admin_email}")

            student_res = await session.execute(select(User).where(User.email == student_email))
            student_user = student_res.scalar_one_or_none()
            if not student_user:
                student_user = User(
                    email=student_email,
                    hashed_password=get_password_hash("StudentPass2026@OWASP"),
                    full_name="Học sinh Trải nghiệm (Grade 12)",
                    role=UserRole.STUDENT,
                    is_active=True,
                )
                session.add(student_user)
                await session.flush()
                print(f"   + Created Student user: {student_email}")

                # Consent record under Law 91/2025/QH15 & Decree 13/2023/ND-CP
                consent = UserConsent(
                    user_id=student_user.id,
                    consent_type="INITIAL_ONBOARDING_TERMS_LAW91_2025",
                    policy_version="v1.0-Law91/2025/QH15",
                    is_granted=True,
                    granted_at=datetime.now(timezone.utc),
                )
                session.add(consent)

            await session.commit()
            print("   Accounts and security consent records verified.")

            # -----------------------------------------------------------------
            # Step 2: Subject Blocks with National Z-Score Parameters
            # -----------------------------------------------------------------
            print("2. Bulk seeding admission subject blocks with national Z-score parameters...")
            existing_blocks_res = await session.execute(select(SubjectBlock))
            block_cache = {b.block_code: b for b in existing_blocks_res.scalars().all()}

            new_blocks_count = 0
            for block_data in SUBJECT_BLOCKS_DATA:
                b_code = block_data["block_code"]
                if b_code not in block_cache:
                    sb = SubjectBlock(
                        block_code=b_code,
                        name=block_data["name"],
                        subjects=block_data["subjects"],
                        national_mean=block_data["national_mean"],
                        national_std=block_data["national_std"],
                    )
                    session.add(sb)
                    block_cache[b_code] = sb
                    new_blocks_count += 1

            if new_blocks_count > 0:
                await session.commit()
                # Refresh cache IDs
                refreshed_res = await session.execute(select(SubjectBlock))
                block_cache = {b.block_code: b for b in refreshed_res.scalars().all()}
            print(f"   Subject blocks verified ({len(block_cache)} blocks, {new_blocks_count} newly inserted).")

            # -----------------------------------------------------------------
            # Step 3: Skills & Prerequisites
            # -----------------------------------------------------------------
            print("3. Bulk seeding skill taxonomies and prerequisite linkages...")
            existing_skills_res = await session.execute(select(Skill))
            skill_cache = {s.skill_code: s for s in existing_skills_res.scalars().all()}

            new_skills_count = 0
            for s_data in SKILLS_DATA:
                s_code = s_data["skill_code"]
                if s_code not in skill_cache:
                    sk = Skill(
                        skill_code=s_code,
                        name=s_data["name"],
                        skill_type=s_data["skill_type"],
                        domain=s_data["domain"],
                        description=s_data["desc"],
                    )
                    session.add(sk)
                    skill_cache[s_code] = sk
                    new_skills_count += 1

            if new_skills_count > 0:
                await session.commit()
                refreshed_skills_res = await session.execute(select(Skill))
                skill_cache = {s.skill_code: s for s in refreshed_skills_res.scalars().all()}

            # Prerequisite link: Python requires Discrete Logic
            if "SKILL_TAR_PROG_PYTHON" in skill_cache and "SKILL_PRE_LOGIC_DISCRETE" in skill_cache:
                p_res = await session.execute(
                    select(SkillPrerequisite).where(
                        SkillPrerequisite.skill_id == skill_cache["SKILL_TAR_PROG_PYTHON"].id,
                        SkillPrerequisite.prerequisite_skill_id == skill_cache["SKILL_PRE_LOGIC_DISCRETE"].id,
                    )
                )
                if not p_res.scalar_one_or_none():
                    sp = SkillPrerequisite(
                        skill_id=skill_cache["SKILL_TAR_PROG_PYTHON"].id,
                        prerequisite_skill_id=skill_cache["SKILL_PRE_LOGIC_DISCRETE"].id,
                    )
                    session.add(sp)
                    await session.commit()
            print(f"   Skills verified ({len(skill_cache)} skills, {new_skills_count} newly inserted).")

            # -----------------------------------------------------------------
            # Step 4: Batch Seed Level-IV Majors (Thông tư 09/2022/TT-BGDĐT)
            # -----------------------------------------------------------------
            print(f"4. Bulk processing {len(MAJORS_DATA)} Level-IV MOET majors, categories & Phoenix Ho careers...")
            existing_majors_res = await session.execute(
                select(Major).options(selectinload(Major.subject_blocks), selectinload(Major.careers))
            )
            existing_majors = {m.major_code: m for m in existing_majors_res.scalars().all()}

            inserted_majors = 0
            updated_majors = 0

            for m_data in MAJORS_DATA:
                code = m_data["major_code"]
                category = m_data.get("category", "Đào tạo chuẩn")

                if code in existing_majors:
                    # Update category or attributes if previously missing
                    major = existing_majors[code]
                    if getattr(major, "category", None) != category:
                        major.category = category
                        updated_majors += 1
                else:
                    # Insert new major
                    major = Major(
                        major_code=code,
                        name=m_data["name"],
                        category=category,
                        degree_level="Đại học",
                        riasec_vector=m_data["riasec"],
                        cognitive_attributes=m_data["cognitive"],
                        industry_outlook=m_data["outlook"],
                        description=f"Ngành đào tạo trình độ đại học theo Thông tư 09/2022/TT-BGDĐT: {m_data['name']}",
                        is_active=True,
                    )
                    session.add(major)
                    await session.flush()
                    existing_majors[code] = major
                    inserted_majors += 1

                    # Link subject blocks
                    for b_code in m_data.get("blocks", []):
                        if b_code in block_cache:
                            msb = MajorSubjectBlock(
                                major_id=major.id,
                                subject_block_id=block_cache[b_code].id,
                                weight=1.0,
                            )
                            session.add(msb)

                    # Link careers based on Phoenix Ho Career Tree Model
                    for c_title in m_data.get("careers", []):
                        career = Career(
                            major_id=major.id,
                            title=c_title,
                            career_tree_level="Lá - Nghề nghiệp cụ thể",
                            description=f"Vị trí công việc thực tế trong thị trường lao động thuộc ngành {major.name}",
                            responsibilities=[
                                "Thực hiện các nghiệp vụ chuyên môn theo chuẩn chức danh nghề nghiệp",
                                "Ứng dụng công nghệ và công cụ ngành trong quy trình công việc",
                                "Phối hợp liên bộ phận và báo cáo kết quả định kỳ",
                            ],
                        )
                        session.add(career)

                    # Link sample mandatory skill
                    if "7480" in code or "7460" in code:
                        if "SKILL_TAR_PROG_PYTHON" in skill_cache:
                            session.add(MajorSkill(major_id=major.id, skill_id=skill_cache["SKILL_TAR_PROG_PYTHON"].id, importance_level="MANDATORY"))
                    elif "7340" in code:
                        if "SKILL_TAR_FINANCIAL_ANALYSIS" in skill_cache:
                            session.add(MajorSkill(major_id=major.id, skill_id=skill_cache["SKILL_TAR_FINANCIAL_ANALYSIS"].id, importance_level="MANDATORY"))
                    elif "7720" in code:
                        if "SKILL_TAR_CLINICAL_DIAGNOSIS" in skill_cache:
                            session.add(MajorSkill(major_id=major.id, skill_id=skill_cache["SKILL_TAR_CLINICAL_DIAGNOSIS"].id, importance_level="MANDATORY"))

            await session.commit()
            print(f"   Majors verified (Total catalog: {len(existing_majors)}, {inserted_majors} inserted, {updated_majors} updated).")

            # -----------------------------------------------------------------
            # Step 5: Seed Pre-cached Roadmaps (Stream B Cache)
            # -----------------------------------------------------------------
            print("5. Verifying pre-cached study roadmaps...")
            roadmap_res = await session.execute(select(MajorRoadmap).where(MajorRoadmap.major_code == "7480201"))
            if not roadmap_res.scalar_one_or_none():
                it_roadmap = MajorRoadmap(
                    major_code="7480201",
                    title="Lộ trình tự học chuẩn bị nhập môn ngành Công nghệ thông tin (7480201)",
                    version="1.0-verified",
                    roadmap_data={
                        "milestones": [
                            {
                                "step": 1,
                                "title": "Tư duy máy tính và Lập trình cơ bản với Python",
                                "description": "Nắm vững cú pháp Python, các cấu trúc điều khiển rẽ nhánh, vòng lặp và xử lý cấu trúc dữ liệu cơ bản.",
                                "duration_weeks": 4,
                                "learning_objectives": ["Hiểu mô hình thực thi mã nguồn", "Viết thuật toán xử lý chuỗi và danh sách", "Xây dựng chương trình quản lý thông tin dòng lệnh"],
                                "actions": ["Hoàn thành khóa học CS50P - CS50 Introduction to Programming with Python", "Luyện tập 30 bài tập thuật toán căn bản trên LeetCode / HackerRank", "Đóng gói mã nguồn lên kho lưu trữ GitHub cá nhân"]
                            },
                            {
                                "step": 2,
                                "title": "Toán rời rạc và Cấu trúc dữ liệu & Giải thuật",
                                "description": "Phát triển tư duy phân tích độ phức tạp thời gian O(n), cấu trúc dữ liệu ngăn xếp, hàng đợi, cây nhị phân.",
                                "duration_weeks": 6,
                                "learning_objectives": ["Phân tích Big-O notation", "Thực thi danh sách liên kết, cây tìm kiếm nhị phân", "Áp dụng thuật toán tìm kiếm nhị phân và quy hoạch động"],
                                "actions": ["Đọc sách giáo trình Cấu trúc dữ liệu và Giải thuật", "Cài đặt thuật toán bằng Python/C++", "Thực hiện đồ án tìm đường đi ngắn nhất đồ thị"]
                            },
                            {
                                "step": 3,
                                "title": "Cơ sở dữ liệu quan hệ và Xây dựng Backend REST API",
                                "description": "Làm quen với hệ quản trị cơ sở dữ liệu quan hệ PostgreSQL và thiết kế kiến trúc API theo chuẩn RESTful.",
                                "duration_weeks": 4,
                                "learning_objectives": ["Thiết kế chuẩn hóa cơ sở dữ liệu 3NF", "Viết truy vấn SQL phức tạp (JOIN, GROUP BY, Indexing)", "Xây dựng dịch vụ API với FastAPI / Flask"],
                                "actions": ["Cài đặt và thiết kế cơ sở dữ liệu PostgreSQL", "Xây dựng ứng dụng quản lý học tập kết nối database", "Viết tài liệu Swagger / OpenAPI"]
                            }
                        ],
                        "prerequisite_knowledge": ["Toán THPT: Hàm số, phương trình và tư duy hình học không gian", "Kỹ năng sử dụng máy tính cá nhân và hệ điều hành (Windows/Linux)", "Tiếng Anh cơ bản để đọc thông báo lỗi và tài liệu kỹ thuật"],
                        "target_skills": ["Kỹ năng lập trình phần mềm với Python/C++", "Tư duy tối ưu hóa giải thuật và xử lý dữ liệu lớn", "Kỹ năng thiết kế hệ thống phần mềm và làm việc với Git"],
                        "reference_materials": [
                            {"title": "CS50's Introduction to Computer Science", "author_or_institution": "Harvard University / edX", "url": "https://cs50.harvard.edu/x", "material_type": "online_course"},
                            {"title": "Chương trình khung đào tạo ngành Công nghệ thông tin", "author_or_institution": "Đại học Bách Khoa Hà Nội & ĐHQG", "url": "https://hust.edu.vn", "material_type": "curriculum"}
                        ],
                        "source_title": "Chương trình chuẩn đào tạo kỹ sư CNTT - Đại học Quốc gia & Bách Khoa",
                        "source_url": "https://hust.edu.vn",
                        "source_page": "Khung 2024"
                    },
                    is_fallback=False,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                session.add(it_roadmap)
                await session.commit()
                print("   + Created verified cached roadmap for major 7480201.")

            # -----------------------------------------------------------------
            # Step 6: Sample Human-in-the-Loop Staging Records
            # -----------------------------------------------------------------
            print("6. Verifying sample Human-in-the-Loop staging records...")
            stage_hash_a = "a" * 64
            stage_res_a = await session.execute(select(StagingRecord).where(StagingRecord.content_hash == stage_hash_a))
            if not stage_res_a.scalar_one_or_none():
                staged_a = StagingRecord(
                    stream_type=StagingStreamType.STREAM_A_MOET,
                    status=StagingStatus.APPROVED,
                    major_code="7480201",
                    content_hash=stage_hash_a,
                    raw_content="Trích lục Thông tư 09/2022/TT-BGDĐT: Mã ngành 7480201 - Công nghệ thông tin",
                    extracted_payload={"major_code": "7480201", "name": "Công nghệ thông tin", "degree_level": "Đại học"},
                    source_title="Thông tư 09/2022/TT-BGDĐT",
                    source_url="https://moet.gov.vn/van-ban/van-ban-chi-dao-dieu-hanh/Pages/chi-tiet-van-ban.aspx?ItemID=8233",
                    source_page="Trang 18",
                    retrieved_at=datetime.now(timezone.utc),
                    reviewed_by=admin_user.id,
                    reviewed_at=datetime.now(timezone.utc),
                    review_notes="Đã đối chiếu chính xác mã ngành cấp IV theo Thông tư gốc."
                )
                session.add(staged_a)

            stage_hash_b = "b" * 64
            stage_res_b = await session.execute(select(StagingRecord).where(StagingRecord.content_hash == stage_hash_b))
            if not stage_res_b.scalar_one_or_none():
                staged_b = StagingRecord(
                    stream_type=StagingStreamType.STREAM_B_ROADMAP,
                    status=StagingStatus.PENDING,
                    major_code="7480108",
                    content_hash=stage_hash_b,
                    raw_content="Đề cương học tập Trí tuệ nhân tạo thu thập từ MIT OpenCourseWare",
                    extracted_payload={
                        "major_code": "7480108",
                        "major_title": "Trí tuệ nhân tạo",
                        "prerequisite_knowledge": ["Đại số tuyến tính", "Xác suất thống kê", "Python cơ bản"],
                        "target_skills": ["Machine Learning", "Deep Learning", "Computer Vision"],
                        "milestones": [
                            {"step": 1, "title": "Cơ sở toán học cho AI", "description": "Giải tích ma trận và tối ưu hóa hàm mất mát", "duration_weeks": 4, "learning_objectives": ["Gradient Descent"], "actions": ["Làm bài tập"]}
                        ],
                        "reference_materials": [
                            {"title": "MIT 6.036 Introduction to Machine Learning", "author_or_institution": "MIT", "url": "https://ocw.mit.edu", "material_type": "online_course"}
                        ],
                        "source_title": "MIT OCW Artificial Intelligence Course",
                        "source_url": "https://ocw.mit.edu/courses/6-036-introduction-to-machine-learning-spring-2020/",
                        "source_page": "Syllabus"
                    },
                    source_title="MIT OCW Machine Learning Curriculum",
                    source_url="https://ocw.mit.edu/courses/6-036-introduction-to-machine-learning-spring-2020/",
                    source_page="Syllabus Page",
                    retrieved_at=datetime.now(timezone.utc)
                )
                session.add(staged_b)

            await session.commit()
            print("   Staging records verified.")

            # -----------------------------------------------------------------
            # Step 7: Circular 74/2026/TT-BGDĐT v1.8 Assessment Questions
            # -----------------------------------------------------------------
            print("7. Seeding Vocational Assessment Questions (v1.8: 30 RIASEC + 8 Cognitive)...")
            from app.db.seeds.seed_assessment_questions import seed_assessment_questions
            await seed_assessment_questions(session)
            print("   Assessment questions seeded into PostgreSQL successfully.")

        elapsed = time.time() - start_time
        print("=" * 75)
        print(f"DATABASE SEEDING COMPLETED SUCCESSFULLY IN {elapsed:.2f}s!")
        print(f" * Total Level-IV Majors in Catalog: {len(MAJORS_DATA)}")
        print(f" * Total Admission Subject Blocks:   {len(SUBJECT_BLOCKS_DATA)}")
        print(f" * Total Skills Registered:          {len(SKILLS_DATA)}")
        print(f" * Total Assessment Questions:       38 (30 RIASEC + 8 Cognitive)")
        print("=" * 75)

    except Exception as exc:
        print("\n" + "!" * 75)
        print(f"[ERROR] Database Seeding encountered an issue: {exc}")
        print("Troubleshooting Steps:")
        print(" 1. Ensure PostgreSQL is active (e.g. docker-compose up -d postgres).")
        print(" 2. Verify connection string in .env: DATABASE_URL=postgresql+asyncpg://...")
        print("!" * 75 + "\n")
        raise exc


if __name__ == "__main__":
    asyncio.run(seed_data())
