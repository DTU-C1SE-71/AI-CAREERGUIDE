"""Các thao tác quản trị AI đều xác thực ADMIN từ DB."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.identity import User
from app.schemas.ai_config import AIConfigDraft, AIConfigProbe, AIActiveProbe, AIConfigStatus, AIProbeResult
from app.services.ai_config import service


router = APIRouter(prefix="/admin/ai-config", tags=["Admin AI Configuration"])


def no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


@router.get("", response_model=AIConfigStatus)
async def status(response: Response, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    no_store(response)
    return await service.get_status(db)


@router.put("", response_model=AIConfigStatus)
async def apply(payload: AIConfigDraft, response: Response, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    no_store(response)
    return await service.apply_config(db, payload, user.id)


@router.post("/probe", response_model=AIProbeResult)
async def probe(payload: AIConfigProbe, response: Response, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    no_store(response)
    return await service.probe_draft(db, payload, user.id)


@router.post("/probe-active", response_model=AIProbeResult)
async def probe_current(payload: AIActiveProbe, response: Response, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    no_store(response)
    return await service.probe_active(db, payload, user.id)
