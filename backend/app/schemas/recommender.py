import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator


class RecommendationRequest(BaseModel):
    user_id: Optional[uuid.UUID] = None
    custom_weights: Optional[Dict[str, float]] = Field(
        default=None,
        description="Optional custom weights: {'w_riasec': 0.45, 'w_academic': 0.35, 'w_preference': 0.20}"
    )
    top_k: int = Field(default=10, ge=1, le=50)


class MajorRecommendationItem(BaseModel):
    rank: int
    major_id: uuid.UUID
    major_code: str
    major_name: str
    category: Optional[str] = "Khác"
    overall_score: float = Field(ge=0.0, le=1.0)
    score_riasec: float = Field(ge=0.0, le=1.0)
    score_academic: float = Field(ge=0.0, le=1.0)
    score_preference: float = Field(ge=0.0, le=1.0)
    best_matching_block: Optional[str] = None
    score_breakdown: Dict[str, Any]
    top_supporting_factors: List[str] = Field(
        default_factory=list,
        description="Key deterministic XAI drivers supporting this major recommendation"
    )
    competency_gaps: List[str] = Field(
        default_factory=list,
        description="Overall missing prerequisite or target skills identified for self-directed study"
    )
    missing_prerequisites: List[str] = Field(
        default_factory=list,
        description="Prerequisite skills not yet mastered by the student"
    )
    missing_target_skills: List[str] = Field(
        default_factory=list,
        description="Target program competencies student needs to develop"
    )
    explanation: str = Field(
        description="Transparent, deterministic XAI breakdown of why this major was recommended"
    )
    # Solution B: Dynamic Academic Clustering & Admission Feasibility
    feasibility_tier: Optional[str] = Field(
        default="TARGET",
        description="TARGET (Vừa sức), REACH (Thử thách/Mơ ước), or ALTERNATIVE"
    )
    feasibility_label: Optional[str] = Field(default="Vừa sức / Khả thi cao")
    benchmark_cutoff: Optional[float] = Field(default=None)
    score_gap: Optional[float] = Field(default=None)
    admission_advice: Optional[str] = Field(default=None)
    academic_tier: Optional[str] = Field(default="STANDARD_COMPETITION")
    academic_tier_label: Optional[str] = Field(default="Vừa sức / Tiêu chuẩn")

    # Frontend Compatibility Fields (Natively matches FE Major interface)
    id: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    university: Optional[str] = None
    match: Optional[int] = None
    feasibility: Optional[str] = None
    fit: Optional[Dict[str, int]] = None
    gaps: Optional[List[str]] = None

    @model_validator(mode="after")
    def populate_fe_fields(self):
        if not self.id:
            self.id = self.major_code
        if not self.code:
            self.code = self.major_code
        if not self.name:
            self.name = self.major_name
        if self.match is None:
            self.match = int(round(self.overall_score * 100))
        if not self.feasibility:
            self.feasibility = self.feasibility_tier or "TARGET"
        if not self.fit:
            self.fit = {
                "interest": int(round(self.score_riasec * 100)),
                "academic": int(round(self.score_academic * 100)),
                "cognitive": int(round(self.score_preference * 100))
            }
        if not self.gaps:
            self.gaps = self.competency_gaps[:3] if self.competency_gaps else [
                "Tư duy thuật toán", "Tiếng Anh chuyên ngành", "Kỹ năng làm dự án"
            ]
        if not self.university:
            self.university = f"Khối {self.best_matching_block}" if self.best_matching_block else "Chuẩn Bộ GD&ĐT"
        return self


class RecommendationResponse(BaseModel):
    user_id: uuid.UUID
    generated_at: datetime
    weights_applied: Dict[str, float]
    total_majors_evaluated: int
    recommendations: List[MajorRecommendationItem]
