import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_admin, get_current_user, get_optional_current_user
from app.models.identity import User
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
    LLMConnectionTestRequest,
    LLMConnectionTestResponse,
    LLMStatusResponse,
    LLMConfigUpdateRequest,
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
    content = await file.read()
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
    """
    Guidance RAG endpoint for students (FR06, DF06):
    Retrieves verified cached roadmap context from PostgreSQL (status = APPROVED, <= 1s)
    and tailors weekly study milestones according to identified skill gaps using gpt-4o-mini.
    Includes strict 8s timeout with automatic graceful Static Fallback Template.
    """
    return await service.personalize_guidance(db, payload)

@router.post("/explain-recommendation", response_model=AIExplanationResponse)
async def explain_major_recommendation(
    payload: AIExplanationRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Explains in-depth why a specific major was recommended using AI (FR06).
    PII SANITIZATION: Strictly uses anonymized student test metrics (RIASEC, grades, diagnostic skills).
    Excludes all student personal information (name, address, school, phone, email) to comply with Law 91/2025/QH15.
    """
    user_id = current_user.id if current_user else payload.user_id
    return await service.explain_recommendation_with_ai(db, payload, user_id)


@router.post("/chat", response_model=AIChatResponse)
async def chat_with_counselor(
    payload: AIChatRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    AI Career Guidance Counselor chat endpoint.
    Answers student questions on majors, academic preparation, diagnostic checks, and roadmaps.
    PII SANITIZATION: All messages pass through sanitize_pii before LLM invocation.
    Guarantees pure guidance scope: no tuition or geographic bias.
    """
    user_id = current_user.id if current_user else payload.user_id
    return await service.chat_with_career_counselor(db, payload, user_id)


@router.get("/llm-status", response_model=LLMStatusResponse)
async def get_system_llm_status():
    """Returns the current LLM model, base URL, and masked API key status."""
    return service.get_llm_status()


@router.post("/test-llm-connection", response_model=LLMConnectionTestResponse)
async def test_llm_api_connection(
    payload: Optional[LLMConnectionTestRequest] = None,
):
    """
    Tests live connection to the configured LLM API (DeepSeek / OpenAI).
    Returns success status, round-trip latency (ms), HTTP code, and Vietnamese diagnostic messages.
    """
    request_data = payload or LLMConnectionTestRequest()
    return await service.test_llm_connection(request_data)

@router.post("/update-llm-config", response_model=LLMStatusResponse)
async def update_system_llm_config(
    payload: LLMConfigUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    """Allows Admin to dynamically update the active LLM Model, Base URL, and API Key."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Quản trị viên (ADMIN) mới có quyền cập nhật cấu hình mô hình AI.",
        )
    return service.update_llm_config(
        model=payload.model,
        base_url=payload.base_url,
        api_key=payload.api_key,
    )
