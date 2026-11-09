import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MajorRoadmap(Base):
    """
    Cached standardized study roadmaps indexed directly by major_code (write-once/read-many).
    Guarantees lookup latency <= 1s for multi-student reuse without recurring AI token costs.
    Includes static fallback templates when AI API fails or curriculum is in curation.
    """
    __tablename__ = "major_roadmaps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    major_code: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False,
        comment="Direct indexed lookup key matching Level-IV MOET major code"
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0", nullable=False)
    
    # Structured roadmap JSONB: milestones, prerequisite_knowledge, target_skills, reference_materials, provenance
    roadmap_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False,
        comment="Standardized study roadmap with step-by-step milestones, prerequisites, target skills, and provenance"
    )
    
    # Static fallback guardrail: ensures immediate 1s response even if AI API is down
    is_fallback: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="Flag indicating whether this entry serves as a verified static fallback"
    )
    fallback_template: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True,
        comment="Static fallback template for quick offline serving"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )


class StudentRoadmapProgress(Base):
    """Tracks a student's self-directed execution of a cached major roadmap."""
    __tablename__ = "student_roadmap_progress"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    major_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    current_step: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    completed_milestones: Mapped[List[int]] = mapped_column(
        JSONB, default=list, nullable=False, comment="List of completed step numbers"
    )
    personalized_schedule: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="AI-personalized timeline adapted to student's skill gaps"
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
