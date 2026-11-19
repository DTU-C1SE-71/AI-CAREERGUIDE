"""Hồ sơ AI duy nhất và nhật ký thao tác không chứa bí mật."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import CheckConstraint, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class AIRuntimeConfig(Base):
    __tablename__ = "ai_runtime_config"
    __table_args__ = (CheckConstraint("id = 1", name="ck_ai_runtime_singleton"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    profile: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    credential_state: Mapped[str] = mapped_column(String(16), nullable=False)
    secret_ciphertext: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    secret_fingerprint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    encryption_key_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class AIConfigAudit(Base):
    __tablename__ = "ai_config_audit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    revision_token: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
