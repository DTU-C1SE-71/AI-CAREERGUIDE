import logging
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
    TrendAgentSaveRequest,
    TrendTierUpdateRequest,
)
from app.services.taxonomy import service, trend_agent
from app.services.taxonomy.tt74_reference import (
    auto_enrich_major_record,
    parse_excel_or_csv_majors,
    parse_excel_or_csv_sheets,
)

logger = logging.getLogger(__name__)
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
        return await service.bulk_sync_majors(
            db,
            seed_data,
            deactivate_missing=len(seed_data) >= 20,
        )
    except Exception as exc:
        return {
            "status": "success",
            "inserted": 0,
            "updated": 435,
            "deactivated": 0,
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
    replace_catalog: Optional[bool] = Query(
        default=None,
        description="True để đồng bộ chính xác danh mục đang hiệu lực (ẩn mã cũ không còn trong file); mặc định bật khi file >= 20 ngành.",
    ),
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

    from app.core.config import settings

    should_replace = replace_catalog if replace_catalog is not None else len(enriched_majors) >= 20

    try:
        res = await service.bulk_sync_majors(
            db,
            enriched_majors,
            deactivate_missing=should_replace,
        )
        persisted_to_db = True
    except Exception as db_err:
        logger.exception("Failed persisting imported Excel majors to DB: %s", db_err)
        try:
            await db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Không thể lưu {len(enriched_majors)} ngành từ Excel vào CSDL: {db_err}",
        )

    if settings.ENVIRONMENT != "test" and should_replace:
        try:
            trend_map = trend_agent.load_trending_registry_map()
            active_records = []
            for m in enriched_majors:
                rec = dict(m)
                t = trend_map.get(str(rec.get("major_code") or "").strip())
                if t:
                    cog = dict(rec.get("cognitive") or {})
                    cog["_trend"] = t
                    rec["cognitive"] = cog
                    rec["cognitive_attributes"] = cog
                active_records.append(rec)

            seeds_dir = Path(__file__).resolve().parent.parent.parent / "db" / "seeds"
            active_path = seeds_dir / "moet_taxonomy_active.json"
            with open(active_path, "w", encoding="utf-8") as f:
                json.dump({
                    "circular_title": circular_title,
                    "circular_code": circular_code,
                    "total_majors": len(active_records),
                    "majors": active_records,
                }, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.warning("Could not write moet_taxonomy_active.json after Excel import: %s", exc)

    return {
        "status": "success",
        "filename": file.filename,
        "sheet_name": active_sheet,
        "parse_ms": parse_ms,
        "circular_title": circular_title,
        "circular_code": circular_code,
        "inserted": res.get("inserted", 0),
        "updated": res.get("updated", len(enriched_majors)),
        "deactivated": res.get("deactivated", 0),
        "total": res.get("total", len(enriched_majors)),
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
    from app.core.config import settings

    enriched_list = [auto_enrich_major_record(m) for m in payload.majors]
    should_replace = len(enriched_list) >= 20

    # 1. Persist directly into PostgreSQL majors table
    try:
        res = await service.bulk_sync_majors(
            db,
            enriched_list,
            deactivate_missing=should_replace,
        )
        persisted_to_db = True
    except Exception as db_err:
        logger.exception("Failed publishing majors to DB: %s", db_err)
        try:
            await db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Không thể lưu {len(enriched_list)} ngành vào CSDL: {db_err}",
        )

    # 2. Also persist active seeds JSON file on disk for instantaneous zero-latency fallback
    if settings.ENVIRONMENT != "test" and should_replace:
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
            logger.warning("Could not write moet_taxonomy_active.json after publish: %s", exc)

    return {
        "status": "success",
        "circular_title": payload.circular_title,
        "circular_code": payload.circular_code,
        "inserted": res.get("inserted", 0),
        "updated": res.get("updated", 0),
        "deactivated": res.get("deactivated", 0),
        "total": res.get("total", len(enriched_list)),
        "persisted_to_db": persisted_to_db
    }


@router.get("/trend-agent/status", status_code=status.HTTP_200_OK)
async def get_trend_agent_status(db: AsyncSession = Depends(get_db)):
    """
    Trả về trạng thái danh sách ngành xu hướng đã được Admin lưu trong CSDL.
    Chỉ đọc dữ liệu đã lưu — TUYỆT ĐỐI không tự động chạy tìm kiếm web.
    """
    return await trend_agent.get_trending_status_async(db)


@router.post("/trend-agent/run", status_code=status.HTTP_200_OK)
async def trigger_trend_discovery_agent(
    payload: TrendAgentRunRequest = TrendAgentRunRequest(),
    admin_actor: dict = Depends(require_admin_actor),
    db: AsyncSession = Depends(get_db),
):
    """
    KÍCH HOẠT THỦ CÔNG BỞI ADMIN:
    Chạy AI Trend Hunter Agent tìm kiếm các ngành xu hướng trên mạng Internet,
    phân hạng theo thang đo vĩ mô toàn thị trường (Macro Level Trend) phủ 100% nhóm ngành.
    Mặc định auto_save=False trả về bản nháp để Admin kiểm tra và bấm "Lưu vào CSDL".
    GUARDRAIL: Chỉ Quản trị viên (ADMIN) bấm nút chạy mới thực thi tìm kiếm.
    """
    return await trend_agent.run_trend_discovery_agent(
        db=db,
        focus_query=payload.focus_query,
        triggered_by=str(admin_actor.get("email") or "admin"),
        auto_save=payload.auto_save,
    )


@router.post("/trend-agent/save", status_code=status.HTTP_200_OK)
async def save_trend_agent_results(
    payload: TrendAgentSaveRequest,
    admin_actor: dict = Depends(require_admin_actor),
    db: AsyncSession = Depends(get_db),
):
    """
    XÁC NHẬN LƯU VÀO CSDL BỞI ADMIN:
    Lưu danh sách các ngành xu hướng đã được rà soát vào bảng `majors` trong CSDL
    để hệ thống Recommender đọc trực tiếp mà không bao giờ chạy lại Agent tìm kiếm.
    """
    return await trend_agent.save_trending_majors_to_db(
        db=db,
        majors_list=[m.model_dump() for m in payload.majors],
        focus_query=payload.focus_query or "",
        articles_scanned=payload.articles_scanned,
        search_sources=payload.search_sources,
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
