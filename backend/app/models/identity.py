import uuid
from datetime import datetime, timezone
import enum
from typing import List, Optional
from sqlalchemy import String, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    STUDENT = "STUDENT"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum"), default=UserRole.STUDENT, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
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
    consents: Mapped[List["UserConsent"]] = relationship(
        "UserConsent", back_populates="user", cascade="all, delete-orphan"
    )
    assessments: Mapped[List["StudentAssessment"]] = relationship(
        "StudentAssessment", back_populates="user", cascade="all, delete-orphan"
    )
    grades: Mapped[List["StudentGrade"]] = relationship(
        "StudentGrade", back_populates="user", cascade="all, delete-orphan"
    )


class UserConsent(Base):
    """
    Tracking personal data consent compliance under Vietnamese Law No. 91/2025/QH15
    on Personal Data Protection.
    """
    __tablename__ = "user_consents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    consent_type: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="TERMS_AND_PRIVACY, DATA_PROCESSING, AI_CAREER_ANALYSIS"
    )
    is_granted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    policy_version: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="e.g. v1.0-Law91/2025/QH15"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="consents")
