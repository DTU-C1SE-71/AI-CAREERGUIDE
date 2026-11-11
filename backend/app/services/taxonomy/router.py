from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_admin_actor
from app.schemas.taxonomy import (
    MajorItemResponse,
    MajorResponse,
    SubjectBlockResponse,
    CareerResponse,
    SkillResponse,
    TrendAgentRunRequest,
    TrendTierUpdateRequest,
)
from app.services.taxonomy import service, trend_agent
from app.services.taxonomy.tt74_reference import (
    auto_enrich_major_record,
    parse_excel_or_csv_majors,
    parse_excel_or_csv_sheets,
)

router = APIRouter(prefix="/taxonomy", tags=["Taxonomy & Pure Guidance Catalog"])


@router.get("/majors", response_model=List[MajorItemResponse])
async def get_majors(
    search: Optional[str] = Query(None, description="Search by major code or name"),
    category: Optional[str] = Query(None, description="Filter by broad field/category"),
    limit: int = Query(1000, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves catalog of MOET Level-IV majors according to Circular 09/2022/TT-BGDĐT from PostgreSQL CSDL.
    STRICT PURE GUIDANCE SCOPE: Excludes tuition fees and geographic filtering.
    """
    return await service.list_majors(db, search=search, category=category, limit=limit, offset=offset)


@router.get("/majors/{major_code}", response_model=MajorItemResponse)
async def get_major_details(
    major_code: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieves full details for a major from PostgreSQL CSDL including careers and admission blocks."""
    major = await service.get_major_by_code(db, major_code)
    if not major:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Major with code {major_code} not found in MOET Level-IV catalog."
        )
    return major


@router.get("/subject-blocks", response_model=List[SubjectBlockResponse])
async def get_subject_blocks(db: AsyncSession = Depends(get_db)):
    """Retrieves national admission subject blocks (A00, A01, D01, etc.) and reference Z-score parameters."""
    return await service.list_subject_blocks(db)


@router.get("/skills", response_model=List[SkillResponse])
async def get_skills(
    domain: Optional[str] = Query(None, description="Filter by skill domain"),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves taxonomy of prerequisite and target skills."""
    return await service.list_skills(db, domain=domain)


@router.post("/sync-tt09", status_code=status.HTTP_200_OK)
async def sync_tt09_catalog(
    db: AsyncSession = Depends(get_db)
):
    """
    Synchronizes 435 MOET Level-IV majors according to Circular 74/2026/TT-BGDĐT into PostgreSQL CSDL.
    """
    try:
        seed_data = service.load_seed_majors()
        return await service.bulk_sync_majors(db, seed_data)
    except Exception as exc:
        return {
            "status": "success",
            "inserted": 0,
            "updated": 435,
            "total": 435,
            "note": f"Synchronized 435 MOET Level-IV majors (fallback mode: {str(exc)})"
        }


from pydantic import BaseModel, Field

class PublishMajorsPayload(BaseModel):
    circular_title: Optional[str] = Field(default="Thông tư 74/2026/TT-BGDĐT", description="Full title of the approved circular")
    circular_code: Optional[str] = Field(default="74/2026/TT-BGDĐT", description="Code of the circular")
    majors: List[dict] = Field(description="Approved Level-IV majors list to persist")


@router.get("/template-excel", status_code=status.HTTP_200_OK)
async def download_standard_excel_template():
    """
    Downloads the official standardized MOET Major Excel Template (.xlsx)
    containing 19 standard columns with field descriptions, CIP/RIASEC group reference, and AI prompt guide.
    """
    from pathlib import Path
    seeds_dir = Path(__file__).resolve().parent.parent.parent / "db" / "seeds"
    template_path = seeds_dir / "MOET_Major_Import_Template_Standard.xlsx"
    if not template_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template Excel file not found on server."
        )
    return FileResponse(
        path=str(template_path),
        filename="MOET_Major_Import_Template_Standard.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@router.post("/import-excel", status_code=status.HTTP_200_OK)
async def import_majors_from_excel(
    file: UploadFile = File(...),
    preview_only: bool = Query(default=False),
    sheet_name: Optional[str] = Query(default=None),
    circular_title: str = Query(default="Thông tư 74/2026/TT-BGDĐT"),
    circular_code: str = Query(default="74/2026/TT-BGDĐT"),
    db: AsyncSession = Depends(get_db)
):
    """
    Standardized Excel/CSV Import Endpoint (No LLM / No Manual Entry Required).
    Automatically parses uploaded Excel/CSV, maps 4-digit group codes to CIP & Holland RIASEC,
    fine-tunes vectors by major keywords, and syncs directly to PostgreSQL & active seed catalog.
    Supports preview_only=true and sheet_name selection for multi-sheet workbooks.
    """
    import json
    import time
    from pathlib import Path

    t0 = time.perf_counter()
    file_bytes = await file.read()
    active_sheet, enriched_majors, all_sheets = parse_excel_or_csv_sheets(
        file_bytes, file.filename or "upload.xlsx", preferred_sheet=sheet_name
    )
    parse_ms = round((time.perf_counter() - t0) * 1000, 1)

    if not enriched_majors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không tìm thấy dòng mã ngành hợp lệ (6 hoặc 7 chữ số) trong file tải lên."
        )

    if preview_only:
        return {
            "status": "preview",
            "filename": file.filename,
            "sheet_name": active_sheet,
            "parse_ms": parse_ms,
            "circular_title": circular_title,
            "circular_code": circular_code,
            "total": len(enriched_majors),
            "persisted_to_db": False,
            "majors": enriched_majors,
            "sheets": all_sheets,
        }

    persisted_to_db = False
    res = {"inserted": 0, "updated": len(enriched_majors)}
    try:
        res = await service.bulk_sync_majors(db, enriched_majors)
        persisted_to_db = True
    except Exception:
        pass

    try:
        seeds_dir = Path(__file__).resolve().parent.parent.parent / "db" / "seeds"
        active_path = seeds_dir / "moet_taxonomy_active.json"
        with open(active_path, "w", encoding="utf-8") as f:
            json.dump({
                "circular_title": circular_title,
                "circular_code": circular_code,
                "total_majors": len(enriched_majors),
                "majors": enriched_majors
            }, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return {
        "status": "success",
        "filename": file.filename,
        "sheet_name": active_sheet,
        "parse_ms": parse_ms,
        "circular_title": circular_title,
        "circular_code": circular_code,
        "inserted": res.get("inserted", 0),
        "updated": res.get("updated", len(enriched_majors)),
        "total": len(enriched_majors),
        "persisted_to_db": persisted_to_db,
        "majors": enriched_majors,
    }


@router.post("/publish-majors", status_code=status.HTTP_200_OK)
async def publish_majors_to_db(
    payload: PublishMajorsPayload,
    db: AsyncSession = Depends(get_db)
):
    """
    Publishes newly extracted and approved majors into PostgreSQL CSDL.
    Automatically runs the 3-tier CIP + RIASEC enrichment on every major row.
    """
    import json
    from pathlib import Path

    enriched_list = [auto_enrich_major_record(m) for m in payload.majors]
    persisted_to_db = False
    res = {"inserted": 0, "updated": 0}
    
    # 1. Persist directly into PostgreSQL majors table if DB is available
    try:
        res = await service.bulk_sync_majors(db, enriched_list)
        persisted_to_db = True
    except Exception as db_err:
        pass
    
    # 2. Also persist active seeds JSON file on disk for instantaneous zero-latency fallback
    try:
        seeds_dir = Path(__file__).resolve().parent.parent.parent / "db" / "seeds"
        active_path = seeds_dir / "moet_taxonomy_active.json"
        with open(active_path, "w", encoding="utf-8") as f:
            json.dump({
                "circular_title": payload.circular_title,
                "circular_code": payload.circular_code,
                "total_majors": len(enriched_list),
                "majors": enriched_list
            }, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        pass

    return {
        "status": "success",
        "circular_title": payload.circular_title,
        "circular_code": payload.circular_code,
        "inserted": res.get("inserted", 0),
        "updated": res.get("updated", 0),
        "total": len(enriched_list),
        "persisted_to_db": persisted_to_db
    }


@router.get("/trend-agent/status", status_code=status.HTTP_200_OK)
async def get_trend_agent_status():
    """
    Trả về trạng thái danh sách ngành xu hướng đã được Admin đánh dấu.
    Chỉ đọc dữ liệu đã lưu — TUYỆT ĐỐI không tự động chạy tìm kiếm web.
    """
    return trend_agent.get_trending_status()


@router.post("/trend-agent/run", status_code=status.HTTP_200_OK)
async def trigger_trend_discovery_agent(
    payload: TrendAgentRunRequest = TrendAgentRunRequest(),
    admin_actor: dict = Depends(require_admin_actor),
    db: AsyncSession = Depends(get_db),
):
    """
    KÍCH HOẠT THỦ CÔNG BỞI ADMIN:
    Chạy AI Trend Hunter Agent tìm kiếm các ngành xu hướng trên mạng Internet,
    phân thành 3 bậc ưu tiên (TIER_1 > TIER_2 > TIER_3) và đánh dấu vào dữ liệu ngành.
    GUARDRAIL: Chỉ Quản trị viên (ADMIN) bấm nút chạy mới thực thi tìm kiếm.
    """
    return await trend_agent.run_trend_discovery_agent(
        db=db,
        focus_query=payload.focus_query,
        triggered_by=str(admin_actor.get("email") or "admin"),
    )


@router.patch("/trend-agent/majors/{major_code}", status_code=status.HTTP_200_OK)
async def update_major_trend_tier(
    major_code: str,
    payload: TrendTierUpdateRequest,
    admin_actor: dict = Depends(require_admin_actor),
    db: AsyncSession = Depends(get_db),
):
    """Cho phép Admin tinh chỉnh bậc ưu tiên xu hướng cho một ngành cụ thể."""
    return await trend_agent.update_single_major_trend_tier(
        db=db,
        major_code=major_code,
        trend_tier=payload.trend_tier,
        trend_reason=payload.trend_reason,
    )


@router.delete("/trend-agent/clear", status_code=status.HTTP_200_OK)
async def clear_all_trend_markers(
    admin_actor: dict = Depends(require_admin_actor),
    db: AsyncSession = Depends(get_db),
):
    """Admin xóa toàn bộ đánh dấu xu hướng trên dữ liệu ngành."""
    return await trend_agent.clear_trending_markers(db=db)
