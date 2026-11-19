import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_admin, get_current_user, get_optional_current_user
from app.models.identity import User, UserRole
from app.models.staging import StagingStatus, StagingStreamType
from app.schemas.staging import (
    StagingRecordCreate,
    StagingRecordUpdate,
    StagingRecordReview,
    StagingRecordResponse,
    StreamAIngestResponse,
    StreamBDiscoveryRequest,
)
from app.schemas.rag import (
    GuidancePersonalizationRequest,
    GuidancePersonalizationResponse,
    SemanticSearchRequest,
    ChunkSearchResult,
    AIExplanationRequest,
    AIExplanationResponse,
    AIChatRequest,
    AIChatResponse,
    AIChatConnectionResponse,
)
from app.services.llamaindex_rag_orchestrator import service

router = APIRouter(prefix="/rag-governance", tags=["LlamaIndex Dual RAG & Governance"])


@router.post("/staging", response_model=StagingRecordResponse, status_code=status.HTTP_201_CREATED)
async def submit_staging_document(
    payload: StagingRecordCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingestion RAG endpoint for submitting extracted documents into Human-in-the-Loop staging.
    Enforces deduplication via SHA-256 content_hash and captures complete provenance metadata.
    GUARDRAIL: Strictly restricted to ADMIN role.
    """
    return await service.create_staging_entry(db, payload)


@router.get("/staging", response_model=List[StagingRecordResponse])
async def get_staged_documents(
    status_filter: Optional[StagingStatus] = Query(None, description="PENDING, APPROVED, REJECTED"),
    stream_filter: Optional[StagingStreamType] = Query(None, description="STREAM_A_MOET or STREAM_B_ROADMAP"),
    major_code_filter: Optional[str] = Query(None, description="Filter by Level-IV major code"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves staged documents for administrative review.
    GUARDRAIL: Restricted strictly to ADMIN role. Unapproved PENDING records are never exposed to students.
    """
    return await service.list_staging_records(
        db,
        status_filter=status_filter,
        stream_filter=stream_filter,
        major_code_filter=major_code_filter
    )


@router.get("/staging/{record_id}", response_model=StagingRecordResponse)
async def get_staged_document_detail(
    record_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Admin retrieves detailed payload and metadata of a staged record."""
    return await service.get_staging_record(db, record_id)


@router.put("/staging/{record_id}", response_model=StagingRecordResponse)
async def update_staged_document(
    record_id: uuid.UUID,
    payload: StagingRecordUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Allows administrator to edit and refine staged payload before giving final approval.
    """
    return await service.update_staging_record(db, record_id, payload)


@router.post("/staging/{record_id}/review", response_model=StagingRecordResponse)
async def review_staged_document(
    record_id: uuid.UUID,
    review_data: StagingRecordReview,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Human-in-the-Loop review decision.
    Upon APPROVAL:
    1. Automatically publishes roadmap JSONB to the reusable major_roadmaps cache (is_fallback = False).
    2. Chunks and inserts 1536-dim vector embeddings into knowledge_embeddings (pgvector).
    """
    return await service.review_staging_record(db, record_id, current_user, review_data)


@router.post("/ingest/stream-a/upload", response_model=StreamAIngestResponse)
async def upload_moet_circular_document(
    file: UploadFile = File(..., description="PDF or Excel document of official MOET circular"),
    source_title: str = Form(default="Thông tư 09/2022/TT-BGDĐT"),
    source_url: str = Form(default="https://moet.gov.vn"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Stream A: Official MOET Circular PDF/Excel Ingestion (FR07, DF03, DF04).
    Extracts Level-IV majors, admission subject blocks, checks SHA-256 deduplication,
    and stages into staging_records (status = PENDING).
    GUARDRAIL: Admin role only.
    """
    content = await file.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "Tệp vượt quá giới hạn 10 MB.")
    return await service.ingest_moet_circular(
        db=db,
        file_bytes=content,
        file_name=file.filename or "circular_document.pdf",
        source_title=source_title,
        source_url=source_url
    )


@router.post("/discover/stream-b", response_model=StagingRecordResponse)
async def discover_roadmap_for_major(
    request: StreamBDiscoveryRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Stream B: 5-Step Automated Roadmap Discovery & Reusable Caching (FR07, DF03, DF04).
    Invokes Tavily Search API (restricted strictly to whitelisted educational domains)
    and Jina Reader, extracts structured roadmap via LlamaIndex + gpt-4o-mini,
    and stages into staging_records (status = PENDING).
    GUARDRAIL: Admin role only. Students cannot trigger live web searches.
    """
    return await service.discover_and_stage_roadmap(
        db=db,
        major_code=request.major_code,
        major_title=request.major_title,
        custom_query=request.custom_query
    )


@router.post("/semantic-search", response_model=List[ChunkSearchResult])
async def search_knowledge_chunks(
    request: SemanticSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Performs cosine similarity vector retrieval on pgvector knowledge_embeddings.
    Filtered by major_code and/or skill_id.
    """
    return await service.semantic_search_chunks(db, request)


@router.post("/guidance-personalize", response_model=GuidancePersonalizationResponse)
async def personalize_study_guidance(
    payload: GuidancePersonalizationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Build an owned, deterministic study plan with explicit source provenance."""
    if payload.user_id != current_user.id:
        raise HTTPException(403, "Chỉ được lập kế hoạch cho tài khoản đang đăng nhập.")
    return await service.personalize_guidance(db, payload)

@router.post("/explain-recommendation", response_model=AIExplanationResponse)
async def explain_major_recommendation(
    payload: AIExplanationRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Explain catalog and scorer facts from the authorized assessment snapshot."""
    user_id = current_user.id if current_user else None
    return await service.explain_recommendation_with_ai(db, payload, user_id)


@router.post("/chat/connection", response_model=AIChatConnectionResponse)
async def check_counselor_connection(
    response: Response,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """One fixed provider probe when the chat opens; never send student data."""
    from app.services.llamaindex_rag_orchestrator.counselor_connection import check_connection
    response.headers["Cache-Control"] = "no-store"
    return await check_connection(db)


@router.post("/chat", response_model=AIChatResponse)
async def chat_with_counselor(
    payload: AIChatRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Locally gate scope before any conversational provider generation."""
    user_id = current_user.id if current_user else None
    return await service.chat_with_career_counselor(db, payload, user_id)


# Alias quản trị dùng cùng DB profile/service với /admin/ai-config.
from app.schemas.ai_config import AIConfigDraft, AIConfigProbe, AIConfigStatus, AIProbeResult
from app.services.ai_config import service as config_service
from app.services.ai_config.router import no_store

@router.get("/llm-status", response_model=AIConfigStatus)
async def get_system_llm_status(response: Response, current_user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    no_store(response)
    return await config_service.get_status(db)

@router.post("/test-llm-connection", response_model=AIProbeResult)
async def test_llm_api_connection(payload: AIConfigProbe, response: Response, current_user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    no_store(response)
    return await config_service.probe_draft(db,payload,current_user.id)

@router.post("/update-llm-config", response_model=AIConfigStatus)
async def update_system_llm_config(payload: AIConfigDraft, response: Response, current_user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    no_store(response)
    return await config_service.apply_config(db,payload,current_user.id)
