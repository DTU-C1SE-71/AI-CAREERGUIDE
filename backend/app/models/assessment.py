import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy import String, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.assessment.models import (
    AssessmentQuestionSet,
    AssessmentQuestion,
    CognitiveQuestionOption,
    StudentAssessmentSubmission,
    StudentAssessmentResponse,
)


class StudentDiagnosticTest(Base):
    """
    Stores student scores for optional diagnostic skill checks.
    Used by the Competency Gap Analysis Engine to determine mastered vs missing prerequisite/target skills.
    """
    __tablename__ = "student_diagnostic_tests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="e.g. SKILL_TAR_PROG_PYTHON")
    score: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Test score normalized between 0.0 and 1.0 (or 0-10 scale)"
    )
    is_passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    details: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False, comment="Detailed breakdown of diagnostic test answers"
    )
    tested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
