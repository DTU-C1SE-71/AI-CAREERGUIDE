import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from app.schemas.taxonomy import RIASECVectorSchema, CognitiveAttributesSchema
from app.modules.assessment.schemas import (
    LikertScaleItem,
    RIASECGroupMeta,
    CognitiveOptionResponse,
    QuestionItemResponse,
    AssessmentQuestionSetConfig,
    AssessmentQuestionSetResponse,
    AssessmentSubmissionRequest,
    AssessmentSubmissionResponse,
)


class RIASECAssessmentSubmit(BaseModel):
    """Student submits answers to RIASEC questionnaire or direct scores."""
    raw_responses: Dict[str, int] = Field(
        default_factory=dict,
        description="Map of question_id to Likert scale value (1 to 5)"
    )
    # Direct scores (0.0 to 1.0) if client calculated
    riasec_scores: Optional[RIASECVectorSchema] = None


class CognitivePreferenceSubmit(BaseModel):
    """Student submits cognitive traits and learning style preferences."""
    abstract_thinking: str = Field(default="medium", description="low, medium, high")
    analytical_reasoning: str = Field(default="medium", description="low, medium, high")
    spatial_perception: str = Field(default="medium", description="low, medium, high")
    linguistic_ability: str = Field(default="medium", description="low, medium, high")
    learning_environment: str = Field(default="structured", description="structured, exploratory, collaborative")
    teamwork_intensity: str = Field(default="balanced", description="independent, balanced, highly_collaborative")


class DiagnosticCheckInput(BaseModel):
    skill_code: str = Field(description="e.g. SKILL_PRE_CALCULUS, SKILL_TAR_PROG_PYTHON")
    score: float = Field(ge=0.0, le=10.0, description="Test score on 0.0 to 10.0 scale (or normalized 0-1)")
    details: Optional[Dict[str, Any]] = None


class DiagnosticCheckBatchSubmit(BaseModel):
    checks: List[DiagnosticCheckInput]


class GradeEntrySubmit(BaseModel):
    """
    Student submits high school grades across standard subjects for Z-score normalization.
    Supports single semester aggregated grades or multi-semester historical grade breakdown.
    """
    academic_year: str = Field(default="2025-2026")
    grades: Dict[str, float] = Field(
        ...,
        description="e.g. {'Toán': 8.5, 'Vật lí': 8.0, 'Hóa học': 7.5, 'Tiếng Anh': 8.0, 'Ngữ văn': 7.0}"
    )
    multi_semester: Optional[Dict[str, Dict[str, float]]] = Field(
        default=None,
        description="Optional semester-by-semester breakdown, e.g. {'Grade10_S1': {...}, 'Grade11_S2': {...}}"
    )
    diagnostic_checks: Optional[List[DiagnosticCheckInput]] = Field(
        default=None,
        description="Optional diagnostic skill checks submitted together with grades"
    )


class BlockZScoreResult(BaseModel):
    block_code: str
    subjects_used: List[str]
    raw_sum: float
    national_mean: float
    national_std: float
    z_score: float
    score_academic: float  # CDF(Z)


class StudentProfileSummary(BaseModel):
    user_id: uuid.UUID
    riasec_vector: Optional[Dict[str, float]] = None
    cognitive_preferences: Optional[Dict[str, Any]] = None
    computed_block_zscores: Optional[Dict[str, Any]] = None
    raw_grades: Optional[Dict[str, float]] = None
    diagnostic_skills_mastered: Optional[List[str]] = None
    last_updated: datetime
