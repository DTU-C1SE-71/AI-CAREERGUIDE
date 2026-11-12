import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


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


class StudentSkillAnalysisRequest(BaseModel):
    major_code: Optional[str] = Field(default=None, description="Ngành mục tiêu (tuỳ chọn)")
    riasec_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Vector RIASEC đã chuẩn hoá, ví dụ {'I': 0.85, 'R': 0.6}",
    )
    grades_by_subject: Dict[str, float] = Field(
        default_factory=dict, description="Điểm học bạ theo môn"
    )
    cognitive_preferences: Dict[str, str] = Field(
        default_factory=dict, description="8 thiên hướng nhận thức từ bài test"
    )
    dominant_traits: List[str] = Field(default_factory=list)
    aspiration: Optional[Dict[str, Any]] = None


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
