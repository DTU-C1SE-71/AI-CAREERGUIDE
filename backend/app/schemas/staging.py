import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict, model_validator
from app.models.staging import StagingStreamType, StagingStatus


class StagingRecordCreate(BaseModel):
    stream_type: StagingStreamType
    major_code: Optional[str] = None
    content_hash: str = Field(description="SHA-256 content hash for deduplication")
    raw_content: Optional[str] = None
    extracted_payload: Dict[str, Any]
    source_title: str
    source_url: str
    source_page: Optional[str] = None


class StagingRecordUpdate(BaseModel):
    """Admin interactive editing schema before final publication."""
    extracted_payload: Optional[Dict[str, Any]] = None
    source_title: Optional[str] = None
    source_url: Optional[str] = None
    source_page: Optional[str] = None


class StagingRecordReview(BaseModel):
    status: StagingStatus = Field(
        description="APPROVED to publish to PostgreSQL/pgvector, or REJECTED"
    )
    review_notes: Optional[str] = None


class StagingRecordResponse(BaseModel):
    id: uuid.UUID
    stream_type: StagingStreamType
    status: StagingStatus
    major_code: Optional[str]
    content_hash: str
    raw_content: Optional[str] = None
    extracted_payload: Dict[str, Any]
    source_title: str
    source_url: str
    source_page: Optional[str]
    retrieved_at: datetime
    reviewed_by: Optional[uuid.UUID]
    reviewed_at: Optional[datetime]
    review_notes: Optional[str]
    created_at: datetime

    # FE StagingRecord compatibility fields
    title: Optional[str] = None
    majorCode: Optional[str] = None
    source: Optional[str] = None
    type: Optional[str] = None
    confidence: Optional[float] = None
    updated: Optional[str] = None
    markdown: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def populate_fe_fields(self):
        if not self.title:
            self.title = self.source_title
        if not self.majorCode:
            self.majorCode = self.major_code or "ALL"
        if not self.source:
            self.source = self.source_url
        if not self.type:
            self.type = "Tavily Discovery" if self.stream_type == StagingStreamType.STREAM_B_ROADMAP else "Qwen3-VL OCR"
        if self.confidence is None:
            self.confidence = 94.5
        if not self.updated:
            self.updated = "Hôm nay"
        if not self.markdown:
            self.markdown = self.raw_content or "## Thông tin đã trích xuất\n\nNội dung đang được kiểm chứng."
        return self


class StreamBDiscoveryRequest(BaseModel):
    major_code: str = Field(description="Level-IV major code to enrich roadmap for, e.g. 7480201")
    major_title: Optional[str] = Field(default=None, description="Standard major title")
    custom_query: Optional[str] = Field(default=None, description="Optional specialized search query")


class StreamAIngestResponse(BaseModel):
    total_parsed: int
    records_staged: int
    content_hash: str
    staged_record_ids: List[uuid.UUID]
    summary: str
