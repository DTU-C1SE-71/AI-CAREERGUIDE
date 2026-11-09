"""
Consolidated SQLAlchemy 2.0 Async Models for AI CareerGuide.
Includes all entities across the 6 modular services:
- identity: User, UserConsent, UserRole
- taxonomy: Major, SubjectBlock, MajorSubjectBlock, Career, Skill, SkillPrerequisite, MajorSkill, SkillType
- assessment: StudentAssessment, StudentGrade, StudentDiagnosticTest
- recommender: RecommendationHistory
- roadmap: MajorRoadmap, StudentRoadmapProgress
- staging: StagingRecord, StagingStreamType, StagingStatus
- vector: KnowledgeEmbedding
"""

from app.core.database import Base
from app.models.identity import User, UserRole, UserConsent
from app.models.taxonomy import (
    Major,
    SubjectBlock,
    MajorSubjectBlock,
    Career,
    Skill,
    SkillType,
    SkillPrerequisite,
    MajorSkill,
)
from app.models.assessment import (
    StudentAssessment,
    StudentGrade,
    StudentDiagnosticTest,
    AssessmentQuestionSet,
    AssessmentQuestion,
    CognitiveQuestionOption,
    StudentAssessmentSubmission,
    StudentAssessmentResponse,
)
from app.models.recommender import RecommendationHistory
from app.models.roadmap import MajorRoadmap, StudentRoadmapProgress
from app.models.staging import StagingRecord, StagingStreamType, StagingStatus
from app.models.vector import KnowledgeEmbedding

__all__ = [
    "Base",
    "User",
    "UserRole",
    "UserConsent",
    "Major",
    "SubjectBlock",
    "MajorSubjectBlock",
    "Career",
    "Skill",
    "SkillType",
    "SkillPrerequisite",
    "MajorSkill",
    "StudentAssessment",
    "StudentGrade",
    "StudentDiagnosticTest",
    "AssessmentQuestionSet",
    "AssessmentQuestion",
    "CognitiveQuestionOption",
    "StudentAssessmentSubmission",
    "StudentAssessmentResponse",
    "RecommendationHistory",
    "MajorRoadmap",
    "StudentRoadmapProgress",
    "StagingRecord",
    "StagingStreamType",
    "StagingStatus",
    "KnowledgeEmbedding",
]
