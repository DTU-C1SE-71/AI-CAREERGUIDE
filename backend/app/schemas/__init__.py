"""
Consolidated Pydantic v2 Schemas for AI CareerGuide.
Supports API validation, response serialization, and LlamaIndex structured extraction.
"""

from app.schemas.identity import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    UserConsentCreate,
    UserConsentResponse,
)
from app.schemas.taxonomy import (
    RIASECVectorSchema,
    CognitiveAttributesSchema,
    MajorBase,
    MajorCreate,
    MajorResponse,
    SubjectBlockCreate,
    SubjectBlockResponse,
    CareerCreate,
    CareerResponse,
    SkillCreate,
    SkillResponse,
)
from app.schemas.assessment import (
    RIASECAssessmentSubmit,
    CognitivePreferenceSubmit,
    GradeEntrySubmit,
    DiagnosticCheckInput,
    DiagnosticCheckBatchSubmit,
    BlockZScoreResult,
    StudentProfileSummary,
)
from app.schemas.recommender import (
    RecommendationRequest,
    MajorRecommendationItem,
    RecommendationResponse,
)
from app.schemas.roadmap import (
    RoadmapMilestoneSchema,
    ReferenceMaterialSchema,
    RoadmapDataSchema,
    MajorRoadmapResponse,
    StudentRoadmapProgressUpdate,
    StudentRoadmapProgressResponse,
)
from app.schemas.staging import (
    StagingRecordCreate,
    StagingRecordReview,
    StagingRecordResponse,
)
from app.schemas.rag import (
    ExtractedRoadmapPayload,
    SemanticSearchRequest,
    ChunkSearchResult,
    GuidancePersonalizationRequest,
    GuidancePersonalizationResponse,
    PersonalizedScheduleTask,
)

__all__ = [
    "UserRegisterRequest",
    "UserLoginRequest",
    "TokenResponse",
    "UserResponse",
    "UserConsentCreate",
    "UserConsentResponse",
    "RIASECVectorSchema",
    "CognitiveAttributesSchema",
    "MajorBase",
    "MajorCreate",
    "MajorResponse",
    "SubjectBlockCreate",
    "SubjectBlockResponse",
    "CareerCreate",
    "CareerResponse",
    "SkillCreate",
    "SkillResponse",
    "RIASECAssessmentSubmit",
    "CognitivePreferenceSubmit",
    "GradeEntrySubmit",
    "DiagnosticCheckInput",
    "DiagnosticCheckBatchSubmit",
    "BlockZScoreResult",
    "StudentProfileSummary",
    "RecommendationRequest",
    "MajorRecommendationItem",
    "RecommendationResponse",
    "RoadmapMilestoneSchema",
    "ReferenceMaterialSchema",
    "RoadmapDataSchema",
    "MajorRoadmapResponse",
    "StudentRoadmapProgressUpdate",
    "StudentRoadmapProgressResponse",
    "StagingRecordCreate",
    "StagingRecordReview",
    "StagingRecordResponse",
    "ExtractedRoadmapPayload",
    "SemanticSearchRequest",
    "ChunkSearchResult",
    "GuidancePersonalizationRequest",
    "GuidancePersonalizationResponse",
    "PersonalizedScheduleTask",
]
