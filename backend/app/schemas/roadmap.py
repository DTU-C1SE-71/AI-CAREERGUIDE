import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


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
    major_code: str
    current_step: int
    completed_milestones: List[int]
    personalized_schedule: Optional[Dict[str, Any]] = None


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
