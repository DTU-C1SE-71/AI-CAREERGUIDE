import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator
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
    """Chỉ chấp nhận bằng chứng đã trả lời, không tạo điểm cho nhóm còn thiếu."""
    model_config = ConfigDict(extra="forbid", strict=True)
    raw_responses: Dict[str, int] = Field(default_factory=dict, max_length=60)
    riasec_scores: Optional[RIASECVectorSchema] = None

    @model_validator(mode="before")
    @classmethod
    def validate_evidence(cls, data):
        import math
        import re
        if not isinstance(data, dict):
            return data
        data = dict(data)
        answers = data.get("raw_responses", {})
        if not isinstance(answers, dict) or len(answers) > 60:
            raise ValueError("Câu trả lời phải là bảng tối đa 60 mục.")
        canonical = {}
        for key, value in answers.items():
            if not isinstance(key, str) or isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
                raise ValueError("Câu Likert yêu cầu số nguyên 1–5.")
            code = key.upper()
            if re.fullmatch(r"1-(?:[0-9]|[12][0-9])", code):
                index = int(code[2:])
                code = "RIASEC"[index // 5] + str(index % 5 + 1)
            if not re.fullmatch(r"[RIASEC][1-5]", code):
                raise ValueError("Mã câu trả lời không được hỗ trợ.")
            if code in canonical and canonical[code] != value:
                raise ValueError("Hai alias của cùng câu hỏi có giá trị khác nhau.")
            canonical[code] = value
        direct = data.get("riasec_scores")
        if direct is not None:
            values = direct.model_dump() if isinstance(direct, RIASECVectorSchema) else direct
            if not isinstance(values, dict) or set(values) != set("RIASEC") or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1 for v in values.values()):
                raise ValueError("Vector trực tiếp phải đủ sáu chiều với số hữu hạn 0–1.")
            if canonical:
                raise ValueError("Chọn câu trả lời gốc hoặc vector trực tiếp; không trộn hai nguồn.")
        data["raw_responses"] = canonical
        return data


class CognitivePreferenceSubmit(BaseModel):
    """Thuộc tính tự khai chưa có phải được để trống, không tự gán trung bình."""
    model_config = ConfigDict(extra="forbid", strict=True)
    abstract_thinking: Optional[Literal["low", "medium", "high"]] = None
    analytical_reasoning: Optional[Literal["low", "medium", "high"]] = None
    spatial_perception: Optional[Literal["low", "medium", "high"]] = None
    linguistic_ability: Optional[Literal["low", "medium", "high"]] = None
    learning_environment: Optional[Literal["structured", "exploratory", "collaborative", "independent"]] = None
    teamwork_intensity: Optional[Literal["independent", "balanced", "highly_collaborative"]] = None


class DiagnosticCheckInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    skill_code: str = Field(min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    score: float = Field(ge=0.0, le=10.0, allow_inf_nan=False)
    score_scale: Literal[1, 10] = 10
    details: Optional[Dict[str, Any]] = None

    @model_validator(mode="before")
    @classmethod
    def validate_scale(cls, data):
        import math
        import json
        if not isinstance(data, dict):
            return data
        value, scale = data.get("score"), data.get("score_scale", 10)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or isinstance(scale, bool) or scale not in (1, 10) or not 0 <= value <= scale:
            raise ValueError("Điểm phải khớp thang điểm tường minh 1 hoặc 10.")
        if len(json.dumps(data.get("details") or {}, ensure_ascii=False)) > 8000:
            raise ValueError("Chi tiết bài chẩn đoán quá lớn.")
        return data


class DiagnosticCheckBatchSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    checks: List[DiagnosticCheckInput] = Field(max_length=50)


class GradeEntrySubmit(BaseModel):
    """Điểm học bạ và nguồn điểm được lưu cùng snapshot, giữ độ chính xác nhập."""
    model_config = ConfigDict(extra="forbid", strict=True)
    academic_year: str = Field(default="2025-2026", max_length=20)
    grades: Dict[str, float] = Field(max_length=40)
    multi_semester: Optional[Dict[str, Dict[str, float]]] = Field(default=None, max_length=12)
    diagnostic_checks: Optional[List[DiagnosticCheckInput]] = Field(default=None, max_length=50)

    @field_validator("grades", mode="before")
    @classmethod
    def validate_grades(cls, value):
        from app.services.recommender.readiness import validate_readiness_grades
        if not isinstance(value, dict) or len(value) > 40 or any(not isinstance(k, str) or len(k) > 80 for k in value):
            raise ValueError("Danh sách điểm không hợp lệ.")
        result = validate_readiness_grades(value)
        if result["errors"]:
            raise ValueError("Điểm không hợp lệ hoặc alias môn học mâu thuẫn.")
        return {key: float(number) for key, number in result["scores"].items()}

    @field_validator("multi_semester", mode="before")
    @classmethod
    def validate_semesters(cls, value):
        if value is None:
            return None
        if not isinstance(value, dict) or len(value) > 12 or any(not isinstance(k, str) or len(k) > 40 for k in value):
            raise ValueError("Thông tin học kỳ không hợp lệ.")
        return {semester: cls.validate_grades(grades) for semester, grades in value.items()}


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
