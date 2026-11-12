import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MajorInsight(Base):
    """
    Cache nội dung đào tạo & vị trí nghề nghiệp của một ngành.

    Write-once / read-many: lần đầu học sinh bấm "Phân tích ngành", AI sinh nội dung
    và lưu tại đây (tra cứu trực tiếp theo major_code). Các lần xem sau chỉ đọc từ DB,
    không gọi lại AI => tiết kiệm chi phí token.
    """
    __tablename__ = "major_insights"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    major_code: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False,
        comment="Mã ngành MOET cấp IV, ví dụ 7480101"
    )
    major_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # {"overview": str, "core_knowledge": [str], "practical_skills": [str],
    #  "curriculum_highlights": [str], "study_duration": str}
    training_content: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, comment="Nội dung đào tạo của ngành"
    )
    # [{"title": str, "description": str, "career_level": str}]
    career_positions: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False, comment="Vị trí nghề nghiệp sau tốt nghiệp"
    )
    subject_blocks: Mapped[List[str]] = mapped_column(
        JSONB, default=list, nullable=False, comment="Tổ hợp xét tuyển"
    )

    is_ai_generated: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="False nếu nội dung được dựng từ dữ liệu chuẩn (AI không khả dụng)"
    )
    model_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )


class StudentSkillInsight(Base):
    """
    Cache kết quả agent phân tích kỹ năng của học sinh.

    Khoá cache là (profile_hash, major_code): cùng một hồ sơ năng lực + cùng ngành
    chỉ gọi AI đúng một lần. Không lưu thông tin định danh cá nhân trong bản ghi,
    profile_hash chỉ là băm SHA-256 của vector RIASEC / điểm môn / thiên hướng nhận thức.
    """
    __tablename__ = "student_skill_insights"
    __table_args__ = (
        UniqueConstraint("profile_hash", "major_code", name="uq_student_skill_insight_profile_major"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    profile_hash: Mapped[str] = mapped_column(
        String(64), index=True, nullable=False,
        comment="SHA-256 của hồ sơ năng lực đã ẩn danh"
    )
    major_code: Mapped[str] = mapped_column(
        String(20), default="", nullable=False, index=True,
        comment="Ngành mục tiêu, rỗng nếu phân tích tổng quát"
    )

    summary: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Nhận định tổng quan ngắn gọn, dễ hiểu"
    )
    # [{"title": str, "detail": str}]
    strengths: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False, comment="Ưu điểm trong cách học"
    )
    weaknesses: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False, comment="Điểm cần cải thiện, giải thích ngắn"
    )
    # [{"skill": str, "why": str, "how_to_improve": [str], "priority": "HIGH"|"MEDIUM"|"LOW"}]
    skill_gaps: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False, comment="Kỹ năng cần bổ sung và cách cải thiện"
    )

    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    model_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
