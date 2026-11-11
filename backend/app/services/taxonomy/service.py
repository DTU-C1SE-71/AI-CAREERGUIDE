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


def format_major_dict(
    major: Major,
    trend_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Formats a Major ORM entity into a standardized frontend & API response dictionary."""
    from app.services.taxonomy.trend_agent import get_major_trend_info

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
    t_info = get_major_trend_info(major.major_code, trend_map=trend_map, cognitive_attributes=cog)

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
        **t_info,
    }


def _attach_seed_trend_info(
    m_dict: Dict[str, Any],
    trend_map: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    from app.services.taxonomy.trend_agent import get_major_trend_info

    enriched = dict(m_dict)
    t_info = get_major_trend_info(
        str(enriched.get("major_code") or ""),
        trend_map=trend_map,
        cognitive_attributes=enriched.get("cognitive") or enriched.get("cognitive_attributes"),
    )
    enriched.update(t_info)
    return enriched


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

        from app.services.taxonomy.trend_agent import load_trending_registry_map
        trend_map = load_trending_registry_map()

        if majors:
            return [format_major_dict(m, trend_map=trend_map) for m in majors]
    except Exception as exc:
        logger.warning("Database unavailable in list_majors (%s), falling back to seed JSON", exc)

    # Safe fallback to seed JSON (435 majors)
    from app.services.taxonomy.trend_agent import load_trending_registry_map
    trend_map = load_trending_registry_map()
    seed_data = load_seed_majors()
    if search:
        s_lower = search.lower()
        seed_data = [
            m for m in seed_data
            if s_lower in m.get("name", "").lower() or s_lower in m.get("major_code", "").lower()
        ]
    if category and category.upper() != "ALL":
        seed_data = [m for m in seed_data if m.get("category") == category]

    return [_attach_seed_trend_info(m, trend_map) for m in seed_data[offset : offset + limit]]


async def get_major_by_code(db: AsyncSession, major_code: str) -> Optional[Dict[str, Any]]:
    from app.services.taxonomy.trend_agent import load_trending_registry_map
    trend_map = load_trending_registry_map()
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
            return format_major_dict(major, trend_map=trend_map)
    except Exception as exc:
        logger.warning("Database unavailable in get_major_by_code (%s), falling back to seed JSON", exc)

    seed_data = load_seed_majors()
    for m in seed_data:
        if m.get("major_code") == major_code:
            return _attach_seed_trend_info(m, trend_map)
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
    Guarantees idempotency, 100% pure guidance scope compliance, and zero async lazy-load crashes.
    Persists category, subject blocks, and careers relationships using batched scalar queries.
    """
    if not majors_data:
        return {"status": "success", "inserted": 0, "updated": 0, "total": 0}

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

    # Deduplicate incoming payload by normalized major_code (last row wins)
    deduped_items: List[dict] = []
    seen_order: Dict[str, int] = {}
    for raw_item in majors_data:
        code = str(raw_item.get("major_code") or "").strip()[:20]
        if not code:
            continue
        item_copy = dict(raw_item)
        item_copy["major_code"] = code
        if code in seen_order:
            deduped_items[seen_order[code]] = item_copy
        else:
            seen_order[code] = len(deduped_items)
            deduped_items.append(item_copy)

    if not deduped_items:
        return {"status": "success", "inserted": 0, "updated": 0, "total": 0}

    incoming_codes = [it["major_code"] for it in deduped_items]

    # Batch-fetch existing majors (chunked for SQLite/PostgreSQL bind parameter safety)
    existing_majors: Dict[str, Major] = {}
    for start in range(0, len(incoming_codes), 400):
        chunk = incoming_codes[start : start + 400]
        res = await db.execute(select(Major).where(Major.major_code.in_(chunk)))
        for m in res.scalars().all():
            existing_majors[m.major_code] = m

    # Batch-fetch existing subject-block links & career titles via scalar queries (never trigger async lazy-load)
    existing_blocks_by_major: Dict[uuid.UUID, set] = {}
    existing_careers_by_major: Dict[uuid.UUID, set] = {}
    existing_ids = [m.id for m in existing_majors.values()]
    for start in range(0, len(existing_ids), 400):
        id_chunk = existing_ids[start : start + 400]
        msb_res = await db.execute(
            select(MajorSubjectBlock.major_id, MajorSubjectBlock.subject_block_id).where(
                MajorSubjectBlock.major_id.in_(id_chunk)
            )
        )
        for mid, sbid in msb_res.all():
            existing_blocks_by_major.setdefault(mid, set()).add(sbid)

        car_res = await db.execute(
            select(Career.major_id, Career.title).where(Career.major_id.in_(id_chunk))
        )
        for mid, ctitle in car_res.all():
            existing_careers_by_major.setdefault(mid, set()).add(ctitle)

    pending_links: List[tuple] = []

    for item in deduped_items:
        code = item["major_code"]
        name = (str(item.get("name") or f"Ngành {code}").strip() or f"Ngành {code}")[:255]
        category = (str(item.get("category") or "Khác").strip() or "Khác")[:100]
        degree_level = (str(item.get("degree_level") or "Đại học").strip() or "Đại học")[:50]
        riasec = item.get("riasec") or item.get("riasec_vector") or {"R": 0.5, "I": 0.5, "A": 0.5, "S": 0.5, "E": 0.5, "C": 0.5}
        raw_cog = item.get("cognitive") or item.get("cognitive_attributes") or {}
        cognitive = dict(raw_cog) if isinstance(raw_cog, dict) else {}
        outlook = str(item.get("outlook") or item.get("industry_outlook") or f"Ngành đào tạo {name}").strip()
        description = item.get("description")

        major_obj = existing_majors.get(code)
        if major_obj is not None:
            # Preserve persisted _trend marker if incoming Excel/payload doesn't include it
            old_cog = major_obj.cognitive_attributes if isinstance(major_obj.cognitive_attributes, dict) else {}
            if "_trend" in old_cog and "_trend" not in cognitive:
                cognitive["_trend"] = old_cog["_trend"]

            major_obj.name = name
            major_obj.category = category
            major_obj.degree_level = degree_level
            major_obj.riasec_vector = riasec
            major_obj.cognitive_attributes = cognitive
            major_obj.industry_outlook = outlook
            if description is not None:
                major_obj.description = str(description)
            major_obj.is_active = bool(item.get("is_active", True))
            updated_count += 1
        else:
            major_obj = Major(
                id=uuid.uuid4(),
                major_code=code,
                name=name,
                category=category,
                degree_level=degree_level,
                riasec_vector=riasec,
                cognitive_attributes=cognitive,
                industry_outlook=outlook,
                description=str(description) if description is not None else None,
                is_active=bool(item.get("is_active", True)),
            )
            db.add(major_obj)
            existing_majors[code] = major_obj
            inserted_count += 1

        pending_links.append(
            (
                major_obj.id,
                name,
                item.get("blocks") or [],
                item.get("careers") or [],
            )
        )

    # Flush all parent Major rows first so child ForeignKeys resolve reliably
    await db.flush()

    for major_id, major_name, blocks_list, careers_list in pending_links:
        existing_block_ids = existing_blocks_by_major.setdefault(major_id, set())
        for raw_b in blocks_list:
            b_code = str(raw_b).strip().upper()
            if b_code in block_map and block_map[b_code].id not in existing_block_ids:
                existing_block_ids.add(block_map[b_code].id)
                db.add(
                    MajorSubjectBlock(
                        id=uuid.uuid4(),
                        major_id=major_id,
                        subject_block_id=block_map[b_code].id,
                        weight=1.0,
                    )
                )

        existing_career_titles = existing_careers_by_major.setdefault(major_id, set())
        for raw_c in careers_list:
            c_title = str(raw_c).strip()[:255]
            if c_title and c_title not in existing_career_titles:
                existing_career_titles.add(c_title)
                db.add(
                    Career(
                        id=uuid.uuid4(),
                        major_id=major_id,
                        title=c_title,
                        career_tree_level="Lá - Nghề nghiệp cụ thể",
                        description=f"Vị trí công việc thực tế trong thị trường lao động thuộc ngành {major_name}",
                        responsibilities=["Thực hiện các nghiệp vụ chuyên môn"],
                    )
                )

    await db.commit()
    return {
        "status": "success",
        "inserted": inserted_count,
        "updated": updated_count,
        "total": len(deduped_items),
    }
