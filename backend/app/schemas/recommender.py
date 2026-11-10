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
    top_k: int = Field(default=10, ge=1, le=500)


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
    # Phân tầng khả thi & Ràng buộc điểm (Solution B + Multi-Layer Gatekeeper)
    feasibility_tier: Optional[str] = Field(
        default="TARGET",
        description="TARGET (Vừa sức/An toàn) hoặc REACH (Thử thách/Chưa đạt ngưỡng)"
    )
    feasibility_label: Optional[str] = Field(default="Vừa sức / Khả thi cao")
    benchmark_cutoff: Optional[float] = Field(default=None)
    min_recommended: Optional[float] = Field(default=None)
    best_block_score: Optional[float] = Field(default=None)
    score_gap: Optional[float] = Field(default=None)
    constraint_passed: bool = Field(default=True)
    constraint_violations: List[str] = Field(default_factory=list)
    admission_advice: Optional[str] = Field(default=None)
    academic_tier: Optional[str] = Field(default="STANDARD_COMPETITION")
    academic_tier_label: Optional[str] = Field(default="Vừa sức / Tiêu chuẩn")

    # Tương thích ngược với DTO Frontend
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
            if self.best_matching_block and self.benchmark_cutoff:
                self.university = f"Khối {self.best_matching_block} · Chuẩn ~{self.benchmark_cutoff}đ"
            elif self.best_matching_block:
                self.university = f"Khối {self.best_matching_block}"
            else:
                self.university = "Chuẩn Bộ GD&ĐT"
        return self


class EvaluateProfileRequest(BaseModel):
    """Yêu cầu đánh giá trực tiếp 435 ngành từ hồ sơ bài test (hoặc tự nạp từ CSDL của user)."""
    riasec_scores: Optional[Dict[str, float]] = None
    riasec_answers: Optional[Dict[str, int]] = None
    cognitive_preferences: Optional[Dict[str, Any]] = None
    cognitive_answers: Optional[Dict[str, Any]] = None
    grades_by_subject: Optional[Dict[str, float]] = None
    custom_weights: Optional[Dict[str, float]] = None
    top_k: int = Field(default=15, ge=1, le=500)


class RecommendationResponse(BaseModel):
    user_id: uuid.UUID
    generated_at: datetime
    weights_applied: Dict[str, float]
    total_majors_evaluated: int
    recommendations: List[MajorRecommendationItem]
