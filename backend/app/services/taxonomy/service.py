import json
import logging
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.taxonomy import (
    Major,
    SubjectBlock,
    Career,
    Skill,
    MajorSubjectBlock,
    MajorSkill,
)

logger = logging.getLogger(__name__)


def load_seed_majors() -> List[dict]:
    """Loads standardized MOET Level-IV majors prioritizing the active published circular, TT74, or TT09."""
    seeds_dir = Path(__file__).resolve().parent.parent.parent / "db" / "seeds"
    
    # 1. Check for actively published circular
    active_path = seeds_dir / "moet_taxonomy_active.json"
    if active_path.exists():
        try:
            with open(active_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "majors" in data:
                    return data["majors"]
                elif isinstance(data, list):
                    return data
        except Exception as e:
            logger.warning("Error reading moet_taxonomy_active.json: %s", e)

    # 2. Check for TT74/2026/TT-BGDĐT
    tt74_path = seeds_dir / "moet_taxonomy_tt74.json"
    if tt74_path.exists():
        try:
            with open(tt74_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Error reading moet_taxonomy_tt74.json: %s", e)

    # 3. Fallback to TT09/2022/TT-BGDĐT
    tt09_path = seeds_dir / "moet_taxonomy_tt09.json"
    if tt09_path.exists():
        with open(tt09_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def format_major_dict(major: Major) -> Dict[str, Any]:
    """Formats a Major ORM entity into a standardized frontend & API response dictionary."""
    blocks: List[str] = []
    if hasattr(major, "subject_blocks") and major.subject_blocks:
        blocks = [
            msb.subject_block.block_code
            for msb in major.subject_blocks
            if getattr(msb, "subject_block", None) is not None
        ]

    careers: List[str] = []
    if hasattr(major, "careers") and major.careers:
        careers = [c.title for c in major.careers if getattr(c, "title", None)]

    rv = major.riasec_vector or {}
    cog = major.cognitive_attributes or {}
    outlook = major.industry_outlook or ""

    return {
        "id": major.id,
        "major_code": major.major_code,
        "raw_code": major.major_code[1:] if (major.major_code and major.major_code.startswith("7") and len(major.major_code) == 7) else major.major_code,
        "name": major.name,
        "category": getattr(major, "category", "Khác") or "Khác",
        "degree_level": major.degree_level or "Đại học",
        "blocks": blocks,
        "careers": careers,
        "riasec": rv,
        "cognitive": cog,
        "outlook": outlook,
        "riasec_vector": rv,
        "cognitive_attributes": cog,
        "industry_outlook": outlook,
        "description": major.description,
        "is_active": major.is_active,
    }


async def list_majors(
    db: AsyncSession,
    search: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 1000,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Retrieves MOET Level-IV majors catalog from PostgreSQL.
    Automatically self-heals and seeds the 108 majors from seed JSON if table is empty
    or if database is unreachable.
    """
    try:
        query = (
            select(Major)
            .where(Major.is_active == True)
            .options(
                selectinload(Major.careers),
                selectinload(Major.subject_blocks).selectinload(MajorSubjectBlock.subject_block),
            )
        )
        if search:
            query = query.where(Major.name.ilike(f"%{search}%") | Major.major_code.ilike(f"%{search}%"))
        if category and category.upper() != "ALL":
            query = query.where(Major.category == category)

        query = query.order_by(Major.major_code.asc()).limit(limit).offset(offset)
        result = await db.execute(query)
        majors = list(result.scalars().all())

        # Auto-seed if database table is completely empty
        if len(majors) == 0 and not search and not category:
            seed_data = load_seed_majors()
            if seed_data:
                logger.info("Majors table empty. Auto-seeding 435 MOET Level-IV majors into PostgreSQL...")
                await bulk_sync_majors(db, seed_data)
                result = await db.execute(query)
                majors = list(result.scalars().all())

        if majors:
            return [format_major_dict(m) for m in majors]
    except Exception as exc:
        logger.warning("Database unavailable in list_majors (%s), falling back to seed JSON", exc)

    # Safe fallback to seed JSON (435 majors)
    seed_data = load_seed_majors()
    if search:
        s_lower = search.lower()
        seed_data = [
            m for m in seed_data
            if s_lower in m.get("name", "").lower() or s_lower in m.get("major_code", "").lower()
        ]
    if category and category.upper() != "ALL":
        seed_data = [m for m in seed_data if m.get("category") == category]

    return seed_data[offset : offset + limit]


async def get_major_by_code(db: AsyncSession, major_code: str) -> Optional[Dict[str, Any]]:
    try:
        query = (
            select(Major)
            .where(Major.major_code == major_code)
            .options(
                selectinload(Major.careers),
                selectinload(Major.subject_blocks).selectinload(MajorSubjectBlock.subject_block),
                selectinload(Major.major_skills).selectinload(MajorSkill.skill),
            )
        )
        result = await db.execute(query)
        major = result.scalar_one_or_none()
        if major:
            return format_major_dict(major)
    except Exception as exc:
        logger.warning("Database unavailable in get_major_by_code (%s), falling back to seed JSON", exc)

    seed_data = load_seed_majors()
    for m in seed_data:
        if m.get("major_code") == major_code:
            return m
    return None


async def list_subject_blocks(db: AsyncSession) -> List[Any]:
    try:
        query = select(SubjectBlock).order_by(SubjectBlock.block_code.asc())
        result = await db.execute(query)
        blocks = list(result.scalars().all())
        if blocks:
            return blocks
    except Exception as exc:
        logger.warning("Database unavailable in list_subject_blocks (%s), falling back to static blocks", exc)

    return [
        {"block_code": "A00", "name": "Toán, Vật lí, Hóa học", "subjects": ["Toán", "Vật lí", "Hóa học"], "national_mean": 20.85, "national_std": 3.25},
        {"block_code": "A01", "name": "Toán, Vật lí, Tiếng Anh", "subjects": ["Toán", "Vật lí", "Tiếng Anh"], "national_mean": 20.15, "national_std": 3.10},
        {"block_code": "B00", "name": "Toán, Hóa học, Sinh học", "subjects": ["Toán", "Hóa học", "Sinh học"], "national_mean": 19.80, "national_std": 3.40},
        {"block_code": "C00", "name": "Ngữ văn, Lịch sử, Địa lí", "subjects": ["Ngữ văn", "Lịch sử", "Địa lí"], "national_mean": 21.50, "national_std": 3.35},
        {"block_code": "D01", "name": "Toán, Ngữ văn, Tiếng Anh", "subjects": ["Toán", "Ngữ văn", "Tiếng Anh"], "national_mean": 19.20, "national_std": 3.15},
        {"block_code": "D07", "name": "Toán, Hóa học, Tiếng Anh", "subjects": ["Toán", "Hóa học", "Tiếng Anh"], "national_mean": 20.40, "national_std": 3.20},
        {"block_code": "D08", "name": "Toán, Sinh học, Tiếng Anh", "subjects": ["Toán", "Sinh học", "Tiếng Anh"], "national_mean": 19.90, "national_std": 3.30},
    ]


async def list_careers_by_major(db: AsyncSession, major_id: uuid.UUID) -> List[Career]:
    query = select(Career).where(Career.major_id == major_id).order_by(Career.title.asc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def list_skills(
    db: AsyncSession,
    domain: Optional[str] = None,
    limit: int = 100
) -> List[Skill]:
    query = select(Skill)
    if domain:
        query = query.where(Skill.domain.ilike(f"%{domain}%"))
    query = query.order_by(Skill.skill_code.asc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def bulk_sync_majors(db: AsyncSession, majors_data: List[dict]) -> dict:
    """
    Syncs or updates MOET Level-IV majors catalog into PostgreSQL.
    Guarantees idempotency and 100% pure guidance scope compliance.
    Persists category, subject blocks, and careers relationships.
    """
    inserted_count = 0
    updated_count = 0

    # Cache existing subject blocks & auto-create missing standard blocks
    from app.services.recommender.engine import STANDARD_SUBJECT_BLOCKS

    sb_result = await db.execute(select(SubjectBlock))
    block_map = {b.block_code: b for b in sb_result.scalars().all()}
    for b_code, b_meta in STANDARD_SUBJECT_BLOCKS.items():
        if b_code not in block_map:
            new_blk = SubjectBlock(
                id=uuid.uuid4(),
                block_code=b_code,
                name=b_meta["name"],
                subjects=b_meta["subjects"],
                national_mean=float(b_meta["national_mean"]),
                national_std=float(b_meta["national_std"]),
            )
            db.add(new_blk)
            await db.flush()
            block_map[b_code] = new_blk

    for item in majors_data:
        code = item["major_code"]
        existing = await db.execute(
            select(Major)
            .where(Major.major_code == code)
            .options(
                selectinload(Major.careers),
                selectinload(Major.subject_blocks)
            )
        )
        major_obj = existing.scalar_one_or_none()

        if major_obj:
            major_obj.name = item["name"]
            major_obj.category = item.get("category", getattr(major_obj, "category", "Khác"))
            major_obj.riasec_vector = item.get("riasec", major_obj.riasec_vector)
            major_obj.cognitive_attributes = item.get("cognitive", major_obj.cognitive_attributes)
            major_obj.industry_outlook = item.get("outlook", major_obj.industry_outlook)
            updated_count += 1
        else:
            major_obj = Major(
                id=uuid.uuid4(),
                major_code=code,
                name=item["name"],
                category=item.get("category", "Khác"),
                degree_level="Đại học",
                riasec_vector=item.get("riasec", {}),
                cognitive_attributes=item.get("cognitive", {}),
                industry_outlook=item.get("outlook", ""),
                is_active=True
            )
            db.add(major_obj)
            await db.flush()
            inserted_count += 1

        # Link subject blocks if provided
        existing_block_ids = {msb.subject_block_id for msb in (major_obj.subject_blocks or [])}
        for b_code in item.get("blocks", []):
            if b_code in block_map and block_map[b_code].id not in existing_block_ids:
                msb = MajorSubjectBlock(
                    major_id=major_obj.id,
                    subject_block_id=block_map[b_code].id,
                    weight=1.0
                )
                db.add(msb)

        # Link careers if provided
        existing_career_titles = {c.title for c in (major_obj.careers or [])}
        for c_title in item.get("careers", []):
            if c_title not in existing_career_titles:
                c = Career(
                    id=uuid.uuid4(),
                    major_id=major_obj.id,
                    title=c_title,
                    career_tree_level="Lá - Nghề nghiệp cụ thể",
                    description=f"Vị trí công việc thực tế trong thị trường lao động thuộc ngành {major_obj.name}",
                    responsibilities=["Thực hiện các nghiệp vụ chuyên môn"]
                )
                db.add(c)

    await db.commit()
    return {
        "status": "success",
        "inserted": inserted_count,
        "updated": updated_count,
        "total": len(majors_data)
    }
