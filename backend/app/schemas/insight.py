import uuid
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from app.schemas.rag import GuidanceEvidenceRequest


class TrainingContent(BaseModel):
    overview: str = Field(description="Mô tả ngắn gọn chương trình đào tạo")
    core_knowledge: List[str] = Field(
        default_factory=list, description="Khối kiến thức nền tảng cốt lõi"
    )
    practical_skills: List[str] = Field(
        default_factory=list, description="Kỹ năng thực hành được rèn luyện"
    )
    curriculum_highlights: List[str] = Field(
        default_factory=list, description="Điểm nổi bật: dự án, thực tập, chứng chỉ"
    )
    study_duration: Optional[str] = Field(default=None, description="Thời gian đào tạo")


class CareerPosition(BaseModel):
    title: str
    description: Optional[str] = None
    career_level: Optional[str] = Field(default=None, description="Cấp bậc / nhóm vị trí")


class MajorInsightResponse(BaseModel):
    major_code: str
    major_name: str
    training_content: TrainingContent
    career_positions: List[CareerPosition] = []
    subject_blocks: List[str] = []
    is_ai_generated: bool = False
    cached: bool = Field(default=True, description="True nếu đọc từ DB, False nếu vừa sinh mới")
    generated_at: Optional[str] = None


class StudentSkillAnalysisRequest(GuidanceEvidenceRequest):
    """Shared evidence contract used by student skill analysis and guidance."""
    major_code: Optional[str] = Field(
        default=None, pattern=r"^[0-9]{7}$", description="Ngành mục tiêu (tuỳ chọn)"
    )
    dominant_traits: List[str] = Field(default_factory=list, max_length=20)


class InsightPoint(BaseModel):
    title: str
    detail: str


class SkillGapItem(BaseModel):
    skill: str
    why: str = Field(description="Vì sao học sinh cần kỹ năng này - 1 câu ngắn")
    how_to_improve: List[str] = Field(default_factory=list)
    priority: str = Field(default="MEDIUM", description="HIGH | MEDIUM | LOW")


class StudentSkillAnalysisResponse(BaseModel):
    profile_hash: str
    major_code: str = ""
    summary: str
    strengths: List[InsightPoint] = []
    weaknesses: List[InsightPoint] = []
    skill_gaps: List[SkillGapItem] = []
    is_ai_generated: bool = False
    cached: bool = False
    insight_id: Optional[uuid.UUID] = None

    model_config = ConfigDict(from_attributes=True)


class AspirationMajorSuggestion(BaseModel):
    major_code: str
    major_name: str
    reason: str
    match_score: Optional[int] = None


class AspirationAIAnalysisRequest(GuidanceEvidenceRequest):
    dream_job: Optional[str] = Field(default=None, max_length=200)


class AspirationAIAnalysisResponse(BaseModel):
    profile_hash: str
    dream_job: str = ""
    fit_level: Literal["HIGH", "MEDIUM", "LOW", "UNKNOWN"] = "UNKNOWN"
    fit_label: str = "Chưa đủ dữ liệu"
    summary: str
    reasons_fit: List[InsightPoint] = []
    reasons_gap: List[InsightPoint] = []
    better_majors: List[AspirationMajorSuggestion] = []
    is_ai_generated: bool = False
    cached: bool = False
    insight_id: Optional[uuid.UUID] = None

    model_config = ConfigDict(from_attributes=True)
