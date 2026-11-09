import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.staging import StagingRecord, StagingStreamType, StagingStatus
from app.models.identity import User
from app.schemas.staging import (
    StagingRecordCreate,
    StagingRecordUpdate,
    StagingRecordReview,
    StreamAIngestResponse,
    StreamBDiscoveryRequest,
)
from app.schemas.rag import (
    GuidancePersonalizationRequest,
    GuidancePersonalizationResponse,
    SemanticSearchRequest,
    ChunkSearchResult,
)

# Modular Service Imports
from app.services.llamaindex_rag_orchestrator.stream_a_ingest import (
    ingest_moet_circular,
    compute_bytes_sha256,
)
from app.services.llamaindex_rag_orchestrator.stream_b_discovery import (
    discover_and_stage_roadmap,
    is_url_whitelisted,
)
from app.services.llamaindex_rag_orchestrator.hitl_governance import (
    list_staging_records,
    get_staging_record,
    update_staging_record,
    review_and_publish_staging_record,
    get_text_embedding,
)
from app.services.llamaindex_rag_orchestrator.guidance_rag import (
    sanitize_pii,
    personalize_guidance,
    semantic_search_chunks,
    explain_recommendation_with_ai,
    chat_with_career_counselor,
    get_llm_status,
    test_llm_connection,
    update_llm_config,
)


def compute_content_sha256(content: str | bytes) -> str:
    """Computes SHA-256 checksum for string or binary content to guarantee deduplication."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return compute_bytes_sha256(content)


async def create_staging_entry(
    db: AsyncSession,
    payload: StagingRecordCreate
) -> StagingRecord:
    """Manual or testing staging intake helper."""
    import hashlib
    from datetime import datetime, timezone
    from fastapi import HTTPException, status
    from sqlalchemy import select

    existing = await db.execute(
        select(StagingRecord).where(StagingRecord.content_hash == payload.content_hash)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate document detected. Content with identical SHA-256 hash already staged."
        )

    record = StagingRecord(
        stream_type=payload.stream_type,
        status=StagingStatus.PENDING,
        major_code=payload.major_code,
        content_hash=payload.content_hash,
        raw_content=payload.raw_content,
        extracted_payload=payload.extracted_payload,
        source_title=payload.source_title,
        source_url=payload.source_url,
        source_page=payload.source_page,
        retrieved_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc)
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def review_staging_record(
    db: AsyncSession,
    record_id: uuid.UUID,
    admin_user: User,
    review_data: StagingRecordReview
) -> StagingRecord:
    return await review_and_publish_staging_record(db, record_id, admin_user, review_data)
