import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import String, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RecommendationSnapshot(Base):
    """Stores cached deterministic Dashboard recommendation bundles keyed by (user_id, input_hash)."""
    __tablename__ = "recommendation_snapshots"
    __table_args__ = (
        UniqueConstraint("user_id", "input_hash", name="uq_recommendation_snapshot_user_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    submission_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_assessment_submissions.id", ondelete="SET NULL", name="fk_recommendation_snapshots_submission_id"),
        nullable=True,
        index=True,
        comment="Optional link to canonical student_assessment_submissions record",
    )
    input_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
        comment="SHA-256 of scoring-relevant assessment, profile grade_level, diagnostics, and catalog"
    )
    algorithm_version: Mapped[str] = mapped_column(
        String(40), default="rec-bundle-v1", nullable=False
    )
    top_k: Mapped[int] = mapped_column(
        Integer, default=435, nullable=False
    )
    payload: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False,
        comment="Serialized Dashboard evaluate response bundle"
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

    # Relationships
    user: Mapped["User"] = relationship("User")
    submission: Mapped[Optional["StudentAssessmentSubmission"]] = relationship("StudentAssessmentSubmission")
