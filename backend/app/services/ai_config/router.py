"""Các thao tác quản trị AI đều xác thực ADMIN từ DB (chỉ đọc từ ENV)."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.identity import User
from app.schemas.ai_config import AIConfigStatus
from app.services.ai_config import service


router = APIRouter(prefix="/admin/ai-config", tags=["Admin AI Configuration"])


def no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


@router.get("", response_model=AIConfigStatus)
async def status(response: Response, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    no_store(response)
    return await service.get_status(db)
