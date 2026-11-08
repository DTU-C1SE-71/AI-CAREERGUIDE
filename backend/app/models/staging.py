import uuid
from datetime import datetime, timezone
import enum
from typing import Optional, Dict, Any
from sqlalchemy import String, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class StagingStreamType(str, enum.Enum):
    STREAM_A_MOET = "STREAM_A_MOET"        # Luồng nạp văn bản quy phạm / Thông tư Bộ GD&ĐT
    STREAM_B_ROADMAP = "STREAM_B_ROADMAP"  # Luồng thu thập tự động từ domain học thuật whitelist qua Tavily/Jina


class StagingStatus(str, enum.Enum):
    PENDING = "PENDING"      # Đang chờ quản trị viên duyệt
    APPROVED = "APPROVED"    # Đã duyệt và xuất bản vào knowledge base chính
    REJECTED = "REJECTED"    # Bị từ chối do trùng lặp, sai lệch hoặc nguồn không hợp lệ


class StagingRecord(Base):
    """
    Human-in-the-Loop staging buffer for both MOET circulars and AI-discovered roadmaps.
    
    STRICT GUARDRAILS:
    1. Unapproved records (status == PENDING) must NEVER be exposed to student-facing endpoints.
    2. Duplication prevention enforced via unique SHA-256 content_hash.
    3. Mandatory provenance metadata tracking: source_title, source_url, source_page, retrieved_at.
    """
    __tablename__ = "staging_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    stream_type: Mapped[StagingStreamType] = mapped_column(
        Enum(StagingStreamType, name="staging_stream_type_enum"), nullable=False,
        comment="STREAM_A_MOET or STREAM_B_ROADMAP"
    )
    status: Mapped[StagingStatus] = mapped_column(
        Enum(StagingStatus, name="staging_status_enum"), default=StagingStatus.PENDING, nullable=False, index=True,
        comment="PENDING, APPROVED, REJECTED"
    )
    major_code: Mapped[Optional[str]] = mapped_column(
        String(20), index=True, nullable=True,
        comment="Associated Level-IV major code"
    )
    
    # SHA-256 hash for deduplication
    content_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False,
        comment="SHA-256 content hash preventing duplicate ingestion"
    )
    
    raw_content: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Original extracted text before normalization"
    )
    
    # Pydantic structured output payload
    extracted_payload: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False,
        comment="Normalized payload matching Pydantic structured schema"
    )
    
    # Provenance Metadata
    source_title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_page: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    
    # Audit trail
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    reviewer: Mapped[Optional["User"]] = relationship("User")
