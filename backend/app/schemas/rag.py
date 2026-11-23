import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.schemas.roadmap import RoadmapMilestoneSchema, ReferenceMaterialSchema


class ExtractedRoadmapPayload(BaseModel):
    """
    Pydantic v2 structured output schema used by LlamaIndex + gpt-4o-mini
    to extract verified roadmaps from whitelisted academic syllabi and curricula.
    """
    major_code: str = Field(description="Associated Level-IV MOET major code, e.g. 7480201")
    major_title: str = Field(description="Standard major title")
    prerequisite_knowledge: List[str] = Field(
        description="Fundamental concepts required prior to starting the study roadmap"
    )
    target_skills: List[str] = Field(
        description="Core technical and transferable competencies acquired upon completion"
    )
    milestones: List[RoadmapMilestoneSchema] = Field(
        description="Chronological step-by-step learning modules with action items"
    )
    reference_materials: List[ReferenceMaterialSchema] = Field(
        description="Verified academic textbooks, open courseware, or authoritative portals"
    )
    source_title: str = Field(description="Title of curriculum/syllabus source document")
    source_url: str = Field(description="URL of source document on whitelisted domain")
    source_page: Optional[str] = Field(
        default=None, description="Page number or section within the document"
    )


class SemanticSearchRequest(BaseModel):
    query: str = Field(min_length=2, description="Semantic query text")
    major_code: Optional[str] = Field(default=None, description="Filter embeddings by major_code")
    skill_id: Optional[uuid.UUID] = Field(default=None, description="Filter embeddings by skill_id")
    top_k: int = Field(default=5, ge=1, le=20)


class ChunkSearchResult(BaseModel):
    id: uuid.UUID
    major_code: Optional[str]
    chunk_text: str
    similarity_score: float
    source_title: Optional[str]
    source_url: Optional[str]
    source_page: Optional[str]
    metadata_payload: Dict[str, Any]


class GuidancePersonalizationRequest(BaseModel):
    major_code: str = Field(pattern=r"^[0-9]{7}$")
    user_id: uuid.UUID
    missing_skills: List[str] = Field(
        default_factory=list,
        max_length=50,
        description="Legacy hint; authoritative gaps are resolved on the server"
    )
    weekly_hours_available: int = Field(default=10, ge=2, le=40)


class PersonalizedScheduleTask(BaseModel):
    week_number: int
    focus_skill: str
    tasks: List[str]
    recommended_reading: str
    estimated_hours: int


class GuidancePersonalizationResponse(BaseModel):
    major_code: str
    personalization_summary: str
    schedule: List[PersonalizedScheduleTask]
    is_fallback: bool = False

class GuidanceEvidenceRequest(BaseModel):
    """Raw evidence contract shared with evaluation; null/empty explicitly clears data."""
    user_id: Optional[uuid.UUID] = None
    assessment_id: Optional[uuid.UUID] = None
    riasec_answers: Optional[Dict[str, Any]] = None
    cognitive_answers: Optional[Dict[str, Any]] = None
    riasec_scores: Optional[Dict[str, Any]] = None
    grades_by_subject: Optional[Dict[str, Any]] = None
    diagnostic_skills_mastered: Optional[List[str]] = Field(default=None, max_length=50)
    cognitive_preferences: Optional[Dict[str, Any]] = None
    aspiration: Optional[Dict[str, Any]] = None
    score_context: Optional[Dict[str, Any]] = None
    gender: Optional[str] = None
    grade_level: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def reject_coerced_numeric_evidence(cls, data):
        import math
        import json
        if not isinstance(data, dict):
            return data
        if len(json.dumps(data, default=str, ensure_ascii=False).encode("utf-8")) > 24000:
            raise ValueError("Hồ sơ quá lớn; giới hạn 24 KB cho yêu cầu tư vấn.")
        for field, upper in (("grades_by_subject", 10), ("riasec_scores", 1), ("riasec_answers", 5)):
            values = data.get(field)
            if values is None:
                continue
            if not isinstance(values, dict) or len(values) > 60:
                raise ValueError(f"{field}: dữ liệu phải là bảng điểm có giới hạn.")
            for value in values.values():
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError(f"{field}: chỉ chấp nhận số hữu hạn, không tự đổi chuỗi hoặc boolean thành điểm.")
                if not 0 <= value <= upper or (field == "riasec_answers" and (value < 1 or int(value) != value)):
                    raise ValueError(f"{field}: điểm ngoài thang đánh giá.")
        return data


class AIExplanationRequest(GuidanceEvidenceRequest):
    major_code: str = Field(pattern=r"^[0-9]{7}$")


class AIExplanationResponse(BaseModel):
    major_code: str
    major_name: str
    detailed_explanation: str
    riasec_alignment: str
    academic_alignment: str
    diagnostic_readiness: str
    strengths: List[str]
    recommended_focus_areas: List[str]
    is_ai_generated: bool = True


ResponseLengthPreference = Literal["auto", "short", "medium", "detailed", "low", "high", "extra_high"]
ResponseLengthMode = Literal["short", "medium", "detailed", "extra_high"]


class AIChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class AIChatRequest(GuidanceEvidenceRequest):
    message: str = Field(min_length=1, max_length=4000)
    major_code: Optional[str] = Field(default=None, pattern=r"^[0-9]{7}$")
    session_id: Optional[uuid.UUID] = None
    history: Optional[List[AIChatMessage]] = Field(default=None, max_length=12)
    connection_revision: Optional[str] = Field(default=None, min_length=32, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    weekly_hours_available: int = Field(default=6, ge=2, le=40)
    response_length: ResponseLengthPreference = "auto"


class AIChatResponse(BaseModel):
    reply: str
    suggested_followups: List[str] = Field(default_factory=list)
    context_major_code: Optional[str] = None
    session_id: Optional[uuid.UUID] = None
    session_title: Optional[str] = None
    response_length_mode: Optional[ResponseLengthMode] = None
    is_fallback: bool = False
    is_ai_generated: bool = False
    response_source: Literal["verified_guidance", "ai_advisor", "offline_guidance"] = "verified_guidance"
    connection_available: bool = False
    connection_revision: Optional[str] = None


class ChatMessageRecord(BaseModel):
    id: uuid.UUID
    role: Literal["user", "assistant"]
    content: str
    response_source: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionSummary(BaseModel):
    id: uuid.UUID
    title: str
    major_code: Optional[str] = None
    message_count: int = 0
    last_message_preview: str = ""
    created_at: datetime
    updated_at: datetime


class ChatSessionDetail(BaseModel):
    id: uuid.UUID
    title: str
    major_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageRecord] = Field(default_factory=list)


class ChatHistoryClearResponse(BaseModel):
    deleted: int


class AIChatConnectionResponse(BaseModel):
    available: bool
    code: str
    message: str
    checked_at: str
    latency_ms: float
    # Opaque signed proof bound to the configuration; no timed chat expiry.
    revision_token: str = ""
