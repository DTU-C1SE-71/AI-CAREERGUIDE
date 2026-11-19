import json
import re
import logging
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
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


async def list_majors(db: AsyncSession, search: Optional[str] = None,
                      category: Optional[str] = None, limit: int = 1000,
                      offset: int = 0) -> List[Dict[str, Any]]:
    """Chỉ đọc danh mục hoạt động trong DB; GET không nạp lại dữ liệu đã xóa."""
    from fastapi import HTTPException
    try:
        query = select(Major).where(Major.is_active.is_(True)).options(
            selectinload(Major.careers),
            selectinload(Major.subject_blocks).selectinload(MajorSubjectBlock.subject_block),
        )
        if search:
            query = query.where(Major.name.ilike(f"%{search}%") | Major.major_code.ilike(f"%{search}%"))
        if category and category.upper() != "ALL":
            query = query.where(Major.category == category)
        result = await db.execute(query.order_by(Major.major_code).limit(limit).offset(offset))
        return [format_major_dict(major, trend_map={}) for major in result.scalars().all()]
    except Exception as exc:
        raise HTTPException(503, "Danh mục tạm thời không truy cập được.") from exc


async def get_major_by_code(db: AsyncSession, major_code: str) -> Optional[Dict[str, Any]]:
    """Ngành đã vô hiệu hóa hoặc xóa không được phục hồi từ seed."""
    from fastapi import HTTPException
    try:
        result = await db.execute(select(Major).where(
            Major.major_code == major_code, Major.is_active.is_(True),
        ).options(selectinload(Major.careers),
                  selectinload(Major.subject_blocks).selectinload(MajorSubjectBlock.subject_block),
                  selectinload(Major.major_skills).selectinload(MajorSkill.skill)))
        major = result.scalar_one_or_none()
        return format_major_dict(major, trend_map={}) if major else None
    except Exception as exc:
        raise HTTPException(503, "Danh mục tạm thời không truy cập được.") from exc


async def list_subject_blocks(db: AsyncSession) -> List[Any]:
    from fastapi import HTTPException
    try:
        result = await db.execute(select(SubjectBlock).order_by(SubjectBlock.block_code))
        return list(result.scalars().all())
    except Exception as exc:
        raise HTTPException(503, "Tổ hợp môn tạm thời không truy cập được.") from exc


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


async def purge_old_major_catalog_data(db: AsyncSession) -> int:
    """
    Xóa sạch toàn bộ dữ liệu ngành & nhóm ngành cũ trong CSDL trước khi nạp file Excel mới:
    - Xóa bảng liên kết tổ hợp môn (major_subject_blocks), nghề nghiệp (careers), kỹ năng ngành (major_skills)
    - Xóa toàn bộ bảng ngành cũ (majors)
    - Xóa cache phân tích ngành (major_insights), lộ trình ngành (major_roadmaps),
      lịch sử đề xuất cũ (recommendation_history), vector tri thức ngành cũ (knowledge_embeddings)
      và bản ghi staging danh mục cũ (staging_records).
    - Giữ nguyên tài khoản người dùng (users), câu hỏi trắc nghiệm và bài làm của học sinh.
    Không commit riêng lẻ để đảm bảo tính nguyên tử (rollback an toàn nếu bước insert sau đó gặp lỗi).
    """
    from app.models.insight import MajorInsight, StudentSkillInsight
    from app.models.roadmap import MajorRoadmap
    from app.models.recommender import RecommendationHistory
    from app.models.vector import KnowledgeEmbedding
    from app.models.staging import StagingRecord, StagingStreamType

    count_res = await db.execute(select(func.count()).select_from(Major))
    raw_count = count_res.scalar_one_or_none()
    deleted_majors_count = raw_count if isinstance(raw_count, int) else 0

    await db.execute(delete(MajorSubjectBlock))
    await db.execute(delete(Career))
    await db.execute(delete(MajorSkill))
    await db.execute(delete(MajorInsight))
    await db.execute(delete(StudentSkillInsight).where(StudentSkillInsight.major_code != ""))
    await db.execute(delete(MajorRoadmap))
    await db.execute(delete(RecommendationHistory))
    await db.execute(delete(KnowledgeEmbedding).where(KnowledgeEmbedding.major_code.is_not(None)))
    await db.execute(delete(StagingRecord).where(StagingRecord.stream_type == StagingStreamType.STREAM_A_MOET))
    await db.execute(delete(Major))
    await db.flush()

    return deleted_majors_count


def validate_catalog_records(items: List[dict], *, allow_six_digit: bool = False) -> None:
    """Chặn dữ liệu thiếu trước mọi purge/ghi; không sửa mã lỗi thành mã ngành giả."""
    if not isinstance(items, list) or not 1 <= len(items) <= 2000:
        raise ValueError("Danh mục phải có từ 1 đến 2000 ngành.")
    pattern = r"(?:[789][0-9]{6}|[0-9]{6})" if allow_six_digit else r"[789][0-9]{6}"
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Ngành phải là một object.")
        code = str(item.get("major_code") or item.get("ma_nganh") or item.get("raw_code") or "").strip()
        name = item.get("name") or item.get("major_name") or item.get("ten_nganh")
        if not re.fullmatch(pattern, code) or not isinstance(name, str) or not 2 <= len(name.strip()) <= 255:
            raise ValueError("Thiếu mã hoặc tên ngành có thể xác minh.")
        if "is_active" in item and not isinstance(item["is_active"], bool):
            raise ValueError("Trạng thái hoạt động phải là boolean.")


async def bulk_sync_majors(
    db: AsyncSession,
    majors_data: List[dict],
    deactivate_missing: bool = False,
) -> dict:
    """
    Syncs or updates MOET Level-IV majors catalog into PostgreSQL.
    Guarantees idempotency, 100% pure guidance scope compliance, and zero async lazy-load crashes.
    Persists category, subject blocks, and careers relationships using batched scalar queries.
    When `deactivate_missing=True`, marks legacy majors absent from `majors_data` as `is_active=False`
    so the active DB count matches the uploaded circular catalog exactly without breaking FKs.
    """
    validate_catalog_records(majors_data)

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

    deactivated_count = 0
    if deactivate_missing and incoming_codes:
        incoming_set = set(incoming_codes)
        active_rows = (
            await db.execute(select(Major.id, Major.major_code).where(Major.is_active == True))
        ).all()
        to_deactivate_ids = [mid for mid, mcode in active_rows if mcode not in incoming_set]
        for start in range(0, len(to_deactivate_ids), 400):
            id_chunk = to_deactivate_ids[start : start + 400]
            await db.execute(
                update(Major).where(Major.id.in_(id_chunk)).values(is_active=False)
            )
        deactivated_count = len(to_deactivate_ids)

    await db.commit()
    return {
        "status": "success",
        "inserted": inserted_count,
        "updated": updated_count,
        "deactivated": deactivated_count,
        "total": len(deduped_items),
    }
