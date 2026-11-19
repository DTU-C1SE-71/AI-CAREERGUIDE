"""One active catalog for ranking, guidance, insights and roadmaps."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.taxonomy import Major, MajorSubjectBlock, MajorSkill


async def load_active_catalog(db):
    if db is not None:
        try:
            result = await db.execute(select(Major).options(
                selectinload(Major.subject_blocks).selectinload(MajorSubjectBlock.subject_block),
                selectinload(Major.major_skills).selectinload(MajorSkill.skill),
                selectinload(Major.careers),
            ))
            rows = list(result.scalars().all())
        except Exception as exc:
            raise HTTPException(503, "Danh mục ngành tạm thời không truy cập được. Vui lòng thử lại.") from exc
        # An imported catalog replaces seeds. Inactive-only catalogs remain empty.
        return [row for row in rows if row.is_active]
    from app.services.taxonomy.service import load_seed_majors
    return [entry for entry in load_seed_majors() if entry.get("is_active", True)]


async def get_active_major_context(db, major_code):
    for major in await load_active_catalog(db):
        code = str(major.get("major_code", "")) if isinstance(major, dict) else major.major_code
        if code != major_code:
            continue
        if isinstance(major, dict):
            return {"major_code": code, "name": major.get("name", code),
                    "category": major.get("category", ""), "description": major.get("description", ""),
                    "careers": major.get("careers") or [], "blocks": major.get("blocks") or []}
        return {"major_code": code, "name": major.name, "category": major.category or "",
                "description": major.description or "",
                "careers": [c.title for c in major.careers if c.title],
                "blocks": [b.subject_block.block_code for b in major.subject_blocks if b.subject_block]}
    raise HTTPException(404, "Ngành không có trong danh mục đang hoạt động.")
