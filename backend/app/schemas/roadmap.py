import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, StrictInt, field_validator


class RoadmapMilestoneSchema(BaseModel):
    step: int = Field(ge=1, description="Step order in the study roadmap")
    title: str = Field(min_length=2, max_length=255)
    description: str
    duration_weeks: int = Field(default=2, ge=1, le=12)
    learning_objectives: List[str] = Field(default_factory=list)
    actions: List[str] = Field(
        default_factory=list,
        description="Concrete study tasks, exercises, or mini-projects"
    )


class RoadmapWeekSchema(BaseModel):
    """Matches FE RoadmapWeek interface directly."""
    id: str
    week: int
    title: str
    eyebrow: str
    description: str
    content: str
    tasks: List[str] = Field(default_factory=list)


class ReferenceMaterialSchema(BaseModel):
    title: str
    author_or_institution: str
    url: str
    material_type: str = Field(
        default="online_course",
        description="textbook, curriculum, online_course, documentation"
    )


class RoadmapDataSchema(BaseModel):
    milestones: List[RoadmapMilestoneSchema]
    prerequisite_knowledge: List[str]
    target_skills: List[str]
    reference_materials: List[ReferenceMaterialSchema]
    source_title: str
    source_url: str
    source_page: Optional[str] = None


class MajorRoadmapResponse(BaseModel):
    id: uuid.UUID
    major_code: str
    title: str
    version: str
    roadmap_data: RoadmapDataSchema
    is_fallback: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentRoadmapProgressUpdate(BaseModel):
    major_code: str = Field(pattern=r"^[789][0-9]{6}$")
    current_step: int = Field(strict=True, ge=1, le=4)
    completed_milestones: List[StrictInt] = Field(max_length=4)
    personalized_schedule: Optional[Dict[str, Any]] = None

    @field_validator("completed_milestones")
    @classmethod
    def valid_steps(cls, value):
        if any(step < 1 or step > 4 for step in value) or len(set(value)) != len(value):
            raise ValueError("Các mốc hoàn tất phải là số tuần 1–4 không trùng nhau.")
        return value

    @field_validator("personalized_schedule")
    @classmethod
    def bounded_schedule(cls, value):
        import json
        if value is not None and len(json.dumps(value,ensure_ascii=False))>32000:
            raise ValueError("Tiến độ vượt giới hạn dữ liệu.")
        return value


class StudentRoadmapProgressResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    major_code: str
    current_step: int
    completed_milestones: List[int]
    personalized_schedule: Optional[Dict[str, Any]] = None
    started_at: datetime
    last_activity_at: datetime

    model_config = ConfigDict(from_attributes=True)
