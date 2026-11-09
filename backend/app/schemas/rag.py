import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
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
    major_code: str
    user_id: uuid.UUID
    missing_skills: List[str] = Field(
        default_factory=list,
        description="Identified competency gaps to focus on"
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

class AIExplanationRequest(BaseModel):
    major_code: str
    user_id: Optional[uuid.UUID] = None
    riasec_scores: Optional[Dict[str, float]] = None
    grades_by_subject: Optional[Dict[str, float]] = None
    diagnostic_skills_mastered: Optional[List[str]] = None
    cognitive_preferences: Optional[Dict[str, Any]] = None


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


class AIChatMessage(BaseModel):
    role: str = Field(description="'user' or 'assistant'")
    content: str


class AIChatRequest(BaseModel):
    message: str
    major_code: Optional[str] = None
    user_id: Optional[uuid.UUID] = None
    history: Optional[List[AIChatMessage]] = None
    riasec_scores: Optional[Dict[str, float]] = None
    grades_by_subject: Optional[Dict[str, float]] = None
    diagnostic_skills_mastered: Optional[List[str]] = None
    cognitive_preferences: Optional[Dict[str, Any]] = None


class AIChatResponse(BaseModel):
    reply: str
    suggested_followups: List[str] = Field(default_factory=list)
    context_major_code: Optional[str] = None
    is_fallback: bool = False


class LLMConnectionTestRequest(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


class LLMConnectionTestResponse(BaseModel):
    success: bool
    status_code: int
    latency_ms: float
    model_used: str
    base_url: str
    is_configured: bool
    message: str
    preview_reply: Optional[str] = None
    tested_at: str


class LLMStatusResponse(BaseModel):
    model: str
    base_url: Optional[str] = None
    is_key_configured: bool
    masked_key: Optional[str] = None
    embedding_model: str

class LLMConfigUpdateRequest(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
