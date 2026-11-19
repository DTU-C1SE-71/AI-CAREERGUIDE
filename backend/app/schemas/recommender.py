import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator, field_validator
import math


class ValidatedWeightsRequest(BaseModel):
    @field_validator("custom_weights", mode="before", check_fields=False)
    @classmethod
    def validate_weights(cls, value):
        if value is None:
            return value
        allowed = {"w_riasec", "w_academic", "w_preference"}
        if not isinstance(value, dict) or not value or set(value) - allowed:
            raise ValueError("Trọng số chỉ được gồm ba trụ cột được hỗ trợ.")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in value.values()) or sum(value.values()) <= 0:
            raise ValueError("Trọng số phải hữu hạn, không âm và có tổng dương.")
        return value


class RecommendationRequest(ValidatedWeightsRequest):
    user_id: Optional[uuid.UUID] = None
    custom_weights: Optional[Dict[str, float]] = Field(
        default=None,
        description="Optional custom weights: {'w_riasec': 0.45, 'w_academic': 0.35, 'w_preference': 0.20}"
    )
    gender: Optional[str] = None
    grade_level: Optional[str] = None
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
    readiness: Dict[str, Any] = Field(default_factory=lambda: {
        "status": "UNKNOWN", "reason": "EVIDENCE_MISSING",
        "message": "Chưa đủ bằng chứng để đối chiếu học lực hiện tại.",
        "block": None, "block_score": None, "benchmark_cutoff": None,
        "min_recommended": None, "missing_subjects": [], "violations": [], "gaps": [],
        "reference_kind": None, "reference_id": None, "reference_method": None,
        "score_kind": None, "block_source": "MISSING", "policy_version": "aspiration-v1",
    })

    # Phân tầng khả thi & Ràng buộc điểm (Solution B + Multi-Layer Gatekeeper)
    feasibility_tier: Optional[str] = Field(
        default="UNKNOWN",
        description="TARGET (Vừa sức/An toàn) hoặc REACH (Thử thách/Chưa đạt ngưỡng)"
    )
    feasibility_label: Optional[str] = Field(default="Chưa đủ bằng chứng")
    benchmark_cutoff: Optional[float] = Field(default=None)
    min_recommended: Optional[float] = Field(default=None)
    best_block_score: Optional[float] = Field(default=None)
    score_gap: Optional[float] = Field(default=None)
    constraint_passed: bool = Field(default=False)
    constraint_violations: List[str] = Field(default_factory=list)
    admission_advice: Optional[str] = Field(default=None)
    academic_tier: Optional[str] = Field(default="STANDARD_COMPETITION")
    academic_tier_label: Optional[str] = Field(default="Vừa sức / Tiêu chuẩn")

    # Đánh dấu Ngành Xu Hướng theo 3 Bậc Ưu tiên (tìm kiếm bởi Admin Trend Agent)
    is_trending: bool = Field(default=False)
    trend_tier: Optional[str] = Field(default=None, description="TIER_1 | TIER_2 | TIER_3")
    trend_priority: int = Field(default=0, description="3=Bậc 1, 2=Bậc 2, 1=Bậc 3, 0=Thường")
    trend_label: Optional[str] = Field(default=None)
    trend_reason: Optional[str] = Field(default=None)
    trend_sources: List[Dict[str, str]] = Field(default_factory=list)

    # HA-GAE v3.1 Horizon & Gender-Aware Adaptive Fields
    nudge_badge: Optional[str] = None
    advisory_note: Optional[str] = None
    admission_tactic: Optional[str] = None

    # Tương thích ngược với DTO Frontend
    id: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    university: Optional[str] = None
    match: Optional[int] = None
    feasibility: Optional[str] = None
    fit: Optional[Dict[str, Optional[int]]] = None
    gaps: Optional[List[str]] = None

    @model_validator(mode="after")
    def populate_fe_fields(self):
        if not self.id:
            self.id = self.major_code
        if not self.code:
            self.code = self.major_code
        if not self.name:
            self.name = self.major_name
        availability = self.score_breakdown.get("pillar_availability")
        interest_known = self.score_breakdown.get("interest_evidence_status", "UNKNOWN") == "COMPLETE"
        if self.match is None and interest_known and (availability is None or any(availability.values())):
            self.match = int(round(self.overall_score * 100))
        if not self.feasibility:
            self.feasibility = self.feasibility_tier or "UNKNOWN"
        if not self.fit:
            self.fit = {
                "interest": int(round(self.score_riasec * 100)),
                "academic": int(round(self.score_academic * 100)),
                "cognitive": int(round(self.score_preference * 100))
            }
        if not self.gaps:
            self.gaps = self.competency_gaps[:3]
        if not self.university:
            if self.best_matching_block and self.benchmark_cutoff:
                self.university = f"Khối {self.best_matching_block} · Chuẩn ~{self.benchmark_cutoff}đ"
            elif self.best_matching_block:
                self.university = f"Khối {self.best_matching_block}"
            else:
                self.university = "Cần đối chiếu trường và phương thức tuyển sinh"
        return self


class EvaluateProfileRequest(ValidatedWeightsRequest):
    """Yêu cầu đánh giá trực tiếp 435 ngành từ hồ sơ bài test (hoặc tự nạp từ CSDL của user)."""
    riasec_scores: Optional[Dict[str, float]] = None
    riasec_answers: Optional[Dict[str, Any]] = None
    cognitive_preferences: Optional[Dict[str, Any]] = None
    cognitive_answers: Optional[Dict[str, Any]] = None
    grades_by_subject: Optional[Dict[str, Any]] = None
    score_context: Optional[Dict[str, Any]] = None
    assessment_id: Optional[uuid.UUID] = None
    aspiration: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Nguyện vọng nghề nghiệp tương lai của học sinh (dream_job, desired_field, work_values, preferred_environment, score_strategy)"
    )
    gender: Optional[str] = None
    grade_level: Optional[str] = None
    custom_weights: Optional[Dict[str, float]] = None
    top_k: int = Field(default=15, ge=1, le=500)


class RecommendationResponse(BaseModel):
    user_id: Optional[uuid.UUID]
    generated_at: datetime
    weights_applied: Dict[str, float]
    total_majors_evaluated: int
    recommendations: List[MajorRecommendationItem]
