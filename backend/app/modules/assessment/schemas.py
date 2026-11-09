import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ConfigDict


class LikertScaleItem(BaseModel):
    value: int = Field(ge=1, le=5)
    label: str
    emoji: str
    weight: float = Field(ge=0.0, le=1.0)


class RIASECGroupMeta(BaseModel):
    dimension: str
    step_index: int
    name_vi: str
    name_en: str
    badge: str
    description: str
    related_moet_field_codes: List[str] = []


class CognitiveOptionResponse(BaseModel):
    id: Optional[uuid.UUID] = None
    option_key: str
    trait_code: str
    title: str
    description: str
    related_moet_field_codes: List[str] = []
    order_index: int

    model_config = ConfigDict(from_attributes=True)


class QuestionItemResponse(BaseModel):
    id: Optional[uuid.UUID] = None
    code: str
    category: str
    dimension: str
    dimension_badge: str
    domain_tag: Optional[str] = None
    icon_name: str
    question_text: str
    order_index: int
    xp_reward: int = 25
    options: Optional[List[CognitiveOptionResponse]] = []

    model_config = ConfigDict(from_attributes=True)


class AssessmentQuestionSetConfig(BaseModel):
    xp_per_question: int = 25
    completion_bonus_xp: int = 200
    estimated_minutes: int = 6
    questions_per_riasec_page: int = 5
    total_riasec_questions: int = 30
    total_cognitive_questions: int = 8
    weights: Dict[str, float] = Field(
        default_factory=lambda: {"riasec": 0.45, "academic": 0.35, "cognitive_preference": 0.20}
    )


class AssessmentQuestionSetResponse(BaseModel):
    set_id: uuid.UUID
    set_code: str
    version: str
    title: str
    circular_ref: str = "74/2026/TT-BGDĐT"
    config: AssessmentQuestionSetConfig
    likert_scale: List[LikertScaleItem]
    riasec_groups: List[RIASECGroupMeta]
    riasec_questions: List[QuestionItemResponse]
    cognitive_questions: List[QuestionItemResponse]
    qa_persona_presets: List[Dict[str, Any]] = []


class AssessmentSubmissionRequest(BaseModel):
    set_id: Optional[uuid.UUID] = None
    # Map of question codes (e.g. 'R1', 'I2'...) to Likert score (1 to 5)
    riasec_answers: Dict[str, int] = Field(
        ...,
        description="Dictionary mapping question code (e.g. 'R1') to Likert scale value (1 to 5)"
    )
    # Map of question codes (e.g. 'COG_1' or 'learning_style') to option key ('A', 'B', 'C', 'D')
    cognitive_answers: Dict[str, str] = Field(
        ...,
        description="Dictionary mapping cognitive question code or dimension to chosen option key ('A'|'B'|'C'|'D')"
    )
    completion_time_seconds: Optional[int] = Field(default=360, ge=10)


class AssessmentSubmissionResponse(BaseModel):
    submission_id: uuid.UUID
    riasec_vector: Dict[str, float] = Field(
        description="Normalized 6-dimensional Holland vector [0.0, 1.0]"
    )
    riasec_raw_scores: Dict[str, int] = Field(
        description="Raw point totals for R, I, A, S, E, C (5 to 25 scale)"
    )
    cognitive_traits: Dict[str, str] = Field(
        description="8 identified cognitive preference trait codes"
    )
    dominant_traits: List[str] = Field(
        description="Top 2-3 dominant vocational interest traits"
    )
    xp_earned: int = Field(default=1150)
    summary: str
    completed_at: datetime
