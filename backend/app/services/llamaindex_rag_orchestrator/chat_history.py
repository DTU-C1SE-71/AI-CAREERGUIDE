"""Quản lý lưu trữ và truy xuất lịch sử trò chuyện Cố vấn AI theo tài khoản."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatSession
from app.schemas.rag import ChatMessageRecord, ChatSessionDetail, ChatSessionSummary

logger = logging.getLogger(__name__)


def derive_session_title(message: str) -> str:
    cleaned = " ".join((message or "").strip().split())
    if not cleaned:
        return "Cuộc trò chuyện hướng nghiệp"
    if len(cleaned) <= 80:
        return cleaned
    return cleaned[:77].rstrip() + "..."


async def verify_session_owner(
    db: Optional[AsyncSession],
    user_id: Optional[uuid.UUID],
    session_id: Optional[uuid.UUID],
) -> Optional[ChatSession]:
    """Đảm bảo phiên chat tồn tại và thuộc chính tài khoản đang đăng nhập."""
    if db is None or user_id is None or session_id is None:
        return None
    session = (
        await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if session is None:
        raise HTTPException(404, "Không tìm thấy cuộc trò chuyện này.")
    return session


async def persist_chat_turn(
    db: Optional[AsyncSession],
    user_id: Optional[uuid.UUID],
    session_id: Optional[uuid.UUID],
    user_message: str,
    assistant_reply: str,
    response_source: Optional[str] = None,
    major_code: Optional[str] = None,
) -> Tuple[Optional[uuid.UUID], Optional[str]]:
    """Lưu cặp tin nhắn người dùng + AI vào CSDL cho người dùng đã đăng nhập."""
    if db is None or user_id is None:
        return None, None
    try:
        session = await verify_session_owner(db, user_id, session_id)
        now = datetime.now(timezone.utc)
        if session is None:
            session = ChatSession(
                id=uuid.uuid4(),
                user_id=user_id,
                title=derive_session_title(user_message),
                major_code=major_code,
                created_at=now,
                updated_at=now,
            )
            db.add(session)
            await db.flush()
        else:
            if major_code:
                session.major_code = major_code
            session.updated_at = now

        db.add(
            ChatMessage(
                id=uuid.uuid4(),
                session_id=session.id,
                role="user",
                content=(user_message or "")[:4000],
                response_source=None,
                created_at=now,
            )
        )
        db.add(
            ChatMessage(
                id=uuid.uuid4(),
                session_id=session.id,
                role="assistant",
                content=(assistant_reply or "")[:12000],
                response_source=response_source,
                created_at=now + timedelta(milliseconds=1),
            )
        )
        await db.commit()
        return session.id, session.title
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("[ChatHistory] Persist failed: %s", exc)
        try:
            await db.rollback()
        except Exception:
            pass
        return None, None


async def list_chat_sessions(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 40,
) -> List[ChatSessionSummary]:
    sessions = (
        await db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .limit(max(1, min(limit, 100)))
        )
    ).scalars().all()
    if not sessions:
        return []

    session_ids = [s.id for s in sessions]
    counts_rows = (
        await db.execute(
            select(ChatMessage.session_id, func.count(ChatMessage.id))
            .where(ChatMessage.session_id.in_(session_ids))
            .group_by(ChatMessage.session_id)
        )
    ).all()
    count_map = {row[0]: int(row[1]) for row in counts_rows}

    all_msgs = (
        await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id.in_(session_ids))
            .order_by(ChatMessage.created_at.desc())
        )
    ).scalars().all()
    preview_map: dict[uuid.UUID, str] = {}
    for msg in all_msgs:
        if msg.session_id not in preview_map:
            text = " ".join((msg.content or "").replace("#", "").replace("*", "").split())
            preview_map[msg.session_id] = text[:120] + ("..." if len(text) > 120 else "")

    return [
        ChatSessionSummary(
            id=s.id,
            title=s.title,
            major_code=s.major_code,
            message_count=count_map.get(s.id, 0),
            last_message_preview=preview_map.get(s.id, ""),
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sessions
    ]


async def get_chat_session_detail(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> ChatSessionDetail:
    session = await verify_session_owner(db, user_id, session_id)
    assert session is not None
    msgs = (
        await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at.asc())
        )
    ).scalars().all()
    return ChatSessionDetail(
        id=session.id,
        title=session.title,
        major_code=session.major_code,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[ChatMessageRecord.model_validate(m) for m in msgs],
    )


async def delete_chat_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> None:
    session = await verify_session_owner(db, user_id, session_id)
    assert session is not None
    await db.delete(session)
    await db.commit()


async def clear_chat_sessions(db: AsyncSession, user_id: uuid.UUID) -> int:
    result = await db.execute(
        delete(ChatSession).where(ChatSession.user_id == user_id)
    )
    await db.commit()
    return int(result.rowcount or 0)
