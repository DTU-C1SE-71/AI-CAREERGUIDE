import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import String, DateTime, ForeignKey, Float, Boolean, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AssessmentQuestionSet(Base):
    """
    Central repository for versioned questionnaires (FR02, FR04).
    Single Source of Truth according to Circular 74/2026/TT-BGDĐT.
    """
    __tablename__ = "assessment_question_sets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    set_code: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False,
        comment="e.g. RIASEC_COG_V1_8"
    )
    version: Mapped[str] = mapped_column(
        String(20), default="1.8", nullable=False,
        comment="Semantic questionnaire version, e.g. 1.8"
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False,
        default="Bộ câu hỏi Đánh giá Sở thích & Thiên hướng Nhận thức chuẩn v1.8"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Detailed description of questionnaire scope and theoretical background"
    )
    circular_ref: Mapped[str] = mapped_column(
        String(100), default="74/2026/TT-BGDĐT", nullable=False
    )
    config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False,
        comment="Configuration parameters: xp_reward, page limits, weights"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, index=True, nullable=False,
        comment="Only one questionnaire set is actively served to students at a given time"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    questions: Mapped[List["AssessmentQuestion"]] = relationship(
        "AssessmentQuestion",
        back_populates="question_set",
        cascade="all, delete-orphan",
        order_by="AssessmentQuestion.order_index"
    )
    submissions: Mapped[List["StudentAssessmentSubmission"]] = relationship(
        "StudentAssessmentSubmission",
        back_populates="question_set"
    )


class AssessmentQuestion(Base):
    """
    Individual assessment item. Category is either 'RIASEC' (30 items) or 'COGNITIVE' (8 items).
    """
    __tablename__ = "assessment_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_question_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    code: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True,
        comment="Unique identifier within questionnaire set, e.g. R1, I2, COG_1"
    )
    category: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True,
        comment="'RIASEC' or 'COGNITIVE'"
    )
    dimension: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        comment="RIASEC: R, I, A, S, E, C | COGNITIVE: learning_style, work_environment, etc."
    )
    dimension_badge: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="e.g. Thực tế (Realistic), Nghiên cứu (Investigative)"
    )
    domain_tag: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True,
        comment="e.g. Cơ khí, Điện tử & Tự động hóa (Mã 51, 52)"
    )
    icon_name: Mapped[str] = mapped_column(
        String(50), default="BrainCircuit", nullable=False,
        comment="Lucide icon name, e.g. Wrench, BrainCircuit, Palette, Compass"
    )
    question_text: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Question prompt or title"
    )
    order_index: Mapped[int] = mapped_column(
        Integer, default=1, index=True, nullable=False,
        comment="Display sequence: 1 to 30 for RIASEC, 1 to 8 for Cognitive"
    )
    xp_reward: Mapped[int] = mapped_column(
        Integer, default=25, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # Relationships
    question_set: Mapped["AssessmentQuestionSet"] = relationship(
        "AssessmentQuestionSet", back_populates="questions"
    )
    cognitive_options: Mapped[List["CognitiveQuestionOption"]] = relationship(
        "CognitiveQuestionOption",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="CognitiveQuestionOption.order_index"
    )


class CognitiveQuestionOption(Base):
    """
    Multiple choice options (A, B, C, D) for cognitive preference questions.
    Links choices directly to 2-digit MOET educational field codes (Circular 74/2026/TT-BGDĐT).
    """
    __tablename__ = "cognitive_question_options"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    option_key: Mapped[str] = mapped_column(
        String(5), nullable=False,
        comment="'A', 'B', 'C', 'D'"
    )
    trait_code: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
        comment="e.g. LEARN_VISUAL_SPATIAL, ENV_DYNAMIC_CORPORATE"
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="e.g. Trực quan & Mô hình hóa"
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Detailed option explanation"
    )
    related_moet_field_codes: Mapped[List[str]] = mapped_column(
        JSONB, default=list, nullable=False,
        comment="e.g. ['21', '58'] under Circular 74/2026/TT-BGDĐT"
    )
    order_index: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )

    # Relationships
    question: Mapped["AssessmentQuestion"] = relationship(
        "AssessmentQuestion", back_populates="cognitive_options"
    )


class StudentAssessmentSubmission(Base):
    """
    Full student assessment lifecycle record. Stores raw answers, normalized 6-dimensional
    RIASEC interest vector, cognitive trait selections, and XP rewards.
    """
    __tablename__ = "student_assessment_submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    set_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_question_sets.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    # 6-Dimensional Holland vector: {"R": 0.45, "I": 0.85, "A": 0.30, "S": 0.25, "E": 0.40, "C": 0.70}
    riasec_vector: Mapped[Dict[str, float]] = mapped_column(
        JSONB, nullable=False,
        comment="Normalized Holland vocational vector [0.0, 1.0]"
    )
    riasec_raw_scores: Mapped[Dict[str, int]] = mapped_column(
        JSONB, nullable=False,
        comment="Sum of 5 Likert items per dimension, range [5, 25]"
    )
    # Cognitive traits: {"learning_style": "LEARN_VISUAL_SPATIAL", "work_environment": "ENV_DYNAMIC_CORPORATE", ...}
    cognitive_traits: Mapped[Dict[str, str]] = mapped_column(
        JSONB, nullable=False,
        comment="8 cognitive preference traits"
    )
    cognitive_answers: Mapped[Dict[str, str]] = mapped_column(
        JSONB, nullable=False,
        comment="Raw option keys selected: {'learning_style': 'A', ...}"
    )
    raw_answers: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False,
        comment="Full raw response payload for reproducibility & audit"
    )
    dominant_traits: Mapped[List[str]] = mapped_column(
        JSONB, default=list, nullable=False,
        comment="Top 2-3 dominant vocational interest traits"
    )
    xp_earned: Mapped[int] = mapped_column(
        Integer, default=1150, nullable=False,
        comment="Total gamification XP awarded (30*25 + 8*25 + 200 completion bonus)"
    )
    completion_time_seconds: Mapped[int] = mapped_column(
        Integer, default=360, nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    question_set: Mapped[Optional["AssessmentQuestionSet"]] = relationship(
        "AssessmentQuestionSet", back_populates="submissions"
    )
    responses: Mapped[List["StudentAssessmentResponse"]] = relationship(
        "StudentAssessmentResponse",
        back_populates="submission",
        cascade="all, delete-orphan"
    )


class StudentAssessmentResponse(Base):
    """
    Granular audit log of each individual question answered by a student.
    """
    __tablename__ = "student_assessment_responses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_assessment_submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    question_code: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )
    likert_value: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        comment="1 to 5 for RIASEC questions"
    )
    option_key: Mapped[Optional[str]] = mapped_column(
        String(5), nullable=True,
        comment="'A', 'B', 'C', 'D' for Cognitive questions"
    )
    selected_trait_code: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True,
        comment="Trait code corresponding to selected option"
    )
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    submission: Mapped["StudentAssessmentSubmission"] = relationship(
        "StudentAssessmentSubmission", back_populates="responses"
    )
    question: Mapped["AssessmentQuestion"] = relationship(
        "AssessmentQuestion"
    )
