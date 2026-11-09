import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
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


class StudentAssessment(Base):
    """Stores student responses and normalized scores for RIASEC and cognitive traits."""
    __tablename__ = "student_assessments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Calculated 6-dim Holland vector: {"R": 0.8, "I": 0.9, "A": 0.4, "S": 0.5, "E": 0.6, "C": 0.7}
    riasec_scores: Mapped[Dict[str, float]] = mapped_column(
        JSONB, nullable=False, comment="Normalized Holland interest vector"
    )
    # Cognitive traits: {"abstract_thinking": "high", "spatial_reasoning": "medium", ...}
    cognitive_preferences: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, comment="Cognitive traits and learning preferences"
    )
    raw_responses: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False, comment="Raw questionnaire choices for auditability"
    )
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="assessments")


class StudentGrade(Base):
    """Stores student raw subject grades across semesters and standardized Z-scores per subject block."""
    __tablename__ = "student_grades"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Raw grades: {"Toán": 8.5, "Vật lí": 8.0, "Hóa học": 7.5, "Tiếng Anh": 8.0}
    # Can also store multi-semester structure: {"semesters": {"HK1_10": {...}, "HK2_10": {...}}, "aggregated": {...}}
    grades_by_subject: Mapped[Dict[str, float]] = mapped_column(
        JSONB, nullable=False, comment="Aggregated or weighted raw subject scores (0.0 to 10.0 scale)"
    )
    multi_semester_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False, comment="Semester-by-semester historical grades for longitudinal tracking"
    )
    # Standardized Z-scores and CDF percentiles per admission block
    computed_block_zscores: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False,
        comment="Normalized scores: {'A00': {'raw_total': 24.0, 'z_score': 1.05, 'score_academic': 0.853}}"
    )
    academic_year: Mapped[str] = mapped_column(String(20), default="2025-2026", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="grades")


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
