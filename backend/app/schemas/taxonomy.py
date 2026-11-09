import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator, ConfigDict
from app.models.taxonomy import SkillType


class RIASECVectorSchema(BaseModel):
    """6-Dimensional Holland Vocational Interest Vector."""
    R: float = Field(ge=0.0, le=1.0, description="Realistic - Kỹ thuật / Thực tế")
    I: float = Field(ge=0.0, le=1.0, description="Investigative - Nghiên cứu / Khám phá")
    A: float = Field(ge=0.0, le=1.0, description="Artistic - Nghệ thuật / Sáng tạo")
    S: float = Field(ge=0.0, le=1.0, description="Social - Xã hội / Giúp đỡ")
    E: float = Field(ge=0.0, le=1.0, description="Enterprising - Quản lý / Khởi nghiệp")
    C: float = Field(ge=0.0, le=1.0, description="Conventional - Nghiệp vụ / Quy củ")


class CognitiveAttributesSchema(BaseModel):
    """Learning environment and cognitive traits matching Gardner / MBTI dimensions."""
    abstract_thinking: str = Field(default="medium", description="low, medium, high")
    analytical_reasoning: str = Field(default="medium", description="low, medium, high")
    spatial_perception: str = Field(default="medium", description="low, medium, high")
    linguistic_ability: str = Field(default="medium", description="low, medium, high")
    learning_environment: str = Field(default="structured", description="structured, exploratory, collaborative")
    teamwork_intensity: str = Field(default="medium", description="independent, balanced, highly_collaborative")


class MajorBase(BaseModel):
    major_code: str = Field(
        min_length=6, max_length=20,
        description="Official Level-IV major code from MOET Circular 09/2022/TT-BGDĐT"
    )
    name: str = Field(min_length=2, max_length=255)
    category: str = Field(default="Kh?c", description="Category according to Circular 09/2022/TT-BGD?T")
    degree_level: str = Field(default="Đại học")
    riasec_vector: RIASECVectorSchema
    cognitive_attributes: CognitiveAttributesSchema
    industry_outlook: str
    description: Optional[str] = None
    is_active: bool = True

    @model_validator(mode="before")
    @classmethod
    def enforce_pure_guidance_scope(cls, data: Any) -> Any:
        """
        PURE GUIDANCE SCOPE GUARDRAIL:
        Strictly forbids economic (tuition fees) or geographic (location) fields to prevent socio-economic bias.
        """
        if isinstance(data, dict):
            prohibited_keys = {"tuition", "tuition_fees", "fee", "cost", "location", "city", "province", "region"}
            found = set(data.keys()).intersection(prohibited_keys)
            if found:
                raise ValueError(
                    f"Pure Guidance Scope Violation: Fields {found} are strictly excluded to avoid socio-economic bias."
                )
        return data


class MajorCreate(MajorBase):
    pass


class SubjectBlockSummary(BaseModel):
    block_code: str
    name: str
    subjects: List[str]
    national_mean: float
    national_std: float

    model_config = ConfigDict(from_attributes=True)


class CareerSummary(BaseModel):
    id: uuid.UUID
    title: str
    career_tree_level: str
    description: str
    responsibilities: List[str]

    model_config = ConfigDict(from_attributes=True)


class SkillSummary(BaseModel):
    id: uuid.UUID
    skill_code: str
    name: str
    skill_type: SkillType
    domain: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MajorItemResponse(BaseModel):
    id: Optional[uuid.UUID] = None
    major_code: str
    raw_code: Optional[str] = None
    name: str
    category: str = "Kh?c"
    degree_level: str = "??i h?c"
    blocks: List[str] = []
    careers: List[str] = []
    riasec: Dict[str, float] = {}
    cognitive: Dict[str, Any] = {}
    outlook: str = ""
    riasec_vector: Optional[Dict[str, float]] = None
    cognitive_attributes: Optional[Dict[str, Any]] = None
    industry_outlook: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True, extra="allow")


class MajorResponse(MajorBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    category: str = "Kh?c"
    blocks: Optional[List[str]] = []
    careers: Optional[List[CareerSummary]] = []
    
    model_config = ConfigDict(from_attributes=True)


class SubjectBlockCreate(BaseModel):
    block_code: str = Field(min_length=3, max_length=10)
    name: str
    subjects: List[str]
    national_mean: float = Field(default=20.0)
    national_std: float = Field(default=3.0)
    description: Optional[str] = None


class SubjectBlockResponse(SubjectBlockCreate):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CareerCreate(BaseModel):
    major_id: uuid.UUID
    title: str
    career_tree_level: str = "Lá - Nghề nghiệp cụ thể"
    description: str
    responsibilities: List[str] = []


class CareerResponse(CareerCreate):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SkillCreate(BaseModel):
    skill_code: str
    name: str
    skill_type: SkillType
    domain: str
    description: Optional[str] = None


class SkillResponse(SkillCreate):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
