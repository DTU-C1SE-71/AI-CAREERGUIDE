import uuid
from datetime import datetime, timezone
import enum
from typing import List, Optional, Dict, Any
from sqlalchemy import String, Boolean, DateTime, Enum, ForeignKey, Text, Float, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SkillType(str, enum.Enum):
    PREREQUISITE = "PREREQUISITE"  # Kiến thức nền tảng / tiên quyết
    TARGET = "TARGET"              # Kỹ năng mục tiêu đầu ra


class Major(Base):
    """
    Catalog of Level-IV higher education majors according to Circular 09/2022/TT-BGDĐT.
    STRICT PURE GUIDANCE SCOPE:
    Tuition fees and geographical locations are deliberately excluded to prevent socio-economic bias.
    """
    __tablename__ = "majors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    major_code: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False,
        comment="Official Level-IV MOET major code, e.g. 7480201 for Information Technology"
    )
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="Kh?c", nullable=False, index=True, comment="MOET broad field or category according to Circular 09/2022/TT-BGD?T")
    degree_level: Mapped[str] = mapped_column(String(50), default="Đại học", nullable=False)
    
    # 6-Dimensional Holland RIASEC Vector: {"R": 0.1, "I": 0.9, "A": 0.2, "S": 0.3, "E": 0.4, "C": 0.6}
    riasec_vector: Mapped[Dict[str, float]] = mapped_column(
        JSONB, nullable=False,
        comment="Holland vocational interest vector with 6 dimensions: R, I, A, S, E, C"
    )
    
    # Cognitive traits & learning environments (Gardner Multiple Intelligences / MBTI dimensions)
    cognitive_attributes: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False,
        comment="Cognitive traits: abstract_thinking, spatial_perception, learning_environment, etc."
    )
    
    industry_outlook: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Labor market demand, digital transformation trends, and future opportunities"
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    subject_blocks: Mapped[List["MajorSubjectBlock"]] = relationship(
        "MajorSubjectBlock", back_populates="major", cascade="all, delete-orphan"
    )
    careers: Mapped[List["Career"]] = relationship(
        "Career", back_populates="major", cascade="all, delete-orphan"
    )
    major_skills: Mapped[List["MajorSkill"]] = relationship(
        "MajorSkill", back_populates="major", cascade="all, delete-orphan"
    )


class SubjectBlock(Base):
    """
    National university admission subject combinations (A00, A01, D01, C00, etc.)
    with national mean (mu) and standard deviation (sigma) for Z-score normalization.
    """
    __tablename__ = "subject_blocks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    block_code: Mapped[str] = mapped_column(
        String(10), unique=True, index=True, nullable=False, comment="e.g. A00, A01, D01, B00"
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="e.g. Toán, Vật lí, Hóa học")
    subjects: Mapped[List[str]] = mapped_column(
        JSONB, nullable=False, comment="List of individual subjects, e.g. ['Toán', 'Vật lí', 'Hóa học']"
    )
    national_mean: Mapped[float] = mapped_column(
        Float, nullable=False, default=20.0, comment="National mean (mu) across exam cohorts"
    )
    national_std: Mapped[float] = mapped_column(
        Float, nullable=False, default=3.0, comment="National standard deviation (sigma)"
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    majors: Mapped[List["MajorSubjectBlock"]] = relationship(
        "MajorSubjectBlock", back_populates="subject_block", cascade="all, delete-orphan"
    )


class MajorSubjectBlock(Base):
    """Association linking majors to their admitted subject blocks."""
    __tablename__ = "major_subject_blocks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    major_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("majors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_block_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subject_blocks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # Relationships
    major: Mapped["Major"] = relationship("Major", back_populates="subject_blocks")
    subject_block: Mapped["SubjectBlock"] = relationship("SubjectBlock", back_populates="majors")


class Career(Base):
    """
    Career roles linked to official Level-IV majors based on the Phoenix Ho Career Tree Model:
    - Gốc (Foundation / Personal attributes)
    - Thân (Core competencies / Transferable academic knowledge)
    - Cành (Functional roles / Specialized industry clusters)
    - Lá (Specific market job titles)
    """
    __tablename__ = "careers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    major_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("majors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="Job title in the labor market")
    career_tree_level: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Lá - Nghề nghiệp cụ thể",
        comment="Gốc - Nền tảng, Thân - Năng lực cốt lõi, Cành - Nhánh chuyên môn, Lá - Nghề nghiệp cụ thể"
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    responsibilities: Mapped[List[str]] = mapped_column(
        JSONB, default=list, nullable=False, comment="Key daily duties and core responsibilities"
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
    major: Mapped["Major"] = relationship("Major", back_populates="careers")


class Skill(Base):
    """Skill taxonomy separating prerequisite knowledge from target competencies."""
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    skill_code: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False, comment="e.g. SKILL_MATH_CALCULUS"
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    skill_type: Mapped[SkillType] = mapped_column(
        Enum(SkillType, name="skill_type_enum"), nullable=False
    )
    domain: Mapped[str] = mapped_column(String(100), nullable=False, comment="e.g. Toán học, Lập trình, Ngoại ngữ")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    prerequisites: Mapped[List["SkillPrerequisite"]] = relationship(
        "SkillPrerequisite",
        foreign_keys="[SkillPrerequisite.skill_id]",
        back_populates="skill",
        cascade="all, delete-orphan"
    )


class SkillPrerequisite(Base):
    """Hierarchical dependency mapping prerequisite skills to target skills."""
    __tablename__ = "skill_prerequisites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True,
        comment="Target skill that requires a prerequisite"
    )
    prerequisite_skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True,
        comment="Prerequisite skill required beforehand"
    )

    # Relationships
    skill: Mapped["Skill"] = relationship(
        "Skill", foreign_keys=[skill_id], back_populates="prerequisites"
    )
    prerequisite_skill: Mapped["Skill"] = relationship(
        "Skill", foreign_keys=[prerequisite_skill_id]
    )


class MajorSkill(Base):
    """Association between a major and required/recommended skills."""
    __tablename__ = "major_skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    major_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("majors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    importance_level: Mapped[str] = mapped_column(
        String(50), default="MANDATORY", comment="MANDATORY (Bắt buộc) or RECOMMENDED (Khuyến nghị)"
    )

    # Relationships
    major: Mapped["Major"] = relationship("Major", back_populates="major_skills")
    skill: Mapped["Skill"] = relationship("Skill")
