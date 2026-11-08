import uuid
import math
import hashlib
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.config import settings
from app.models.staging import StagingRecord, StagingStreamType, StagingStatus
from app.models.roadmap import MajorRoadmap
from app.models.vector import KnowledgeEmbedding
from app.models.identity import User
from app.models.taxonomy import Major
from app.schemas.staging import StagingRecordUpdate, StagingRecordReview

logger = logging.getLogger(__name__)


def generate_deterministic_embedding(text: str, dimension: int = 1536) -> List[float]:
    """
    Generates a deterministic 1536-dimensional normalized unit vector from input text.
    Used during offline mode, test mocking, or when OpenAI API key is unconfigured.
    """
    hasher = hashlib.sha256()
    hasher.update(text.encode("utf-8"))
    digest = hasher.digest()
    
    # Generate pseudo-random numbers using seed from digest
    vector = []
    for i in range(dimension):
        byte_val = digest[i % len(digest)]
        # Generate value between -1.0 and 1.0
        val = math.sin(byte_val * (i + 1) * 0.17)
        vector.append(val)
        
    # Normalize to unit length (L2 norm)
    norm = math.sqrt(sum(x * x for x in vector))
    if norm > 0:
        vector = [x / norm for x in vector]
    return vector


async def get_text_embedding(text: str) -> List[float]:
    """
    Generates a 1536-dimensional vector embedding for text using OpenAI text-embedding-3-small.
    Falls back gracefully to deterministic normalized embedding if OpenAI API is unavailable.
    """
    if settings.OPENAI_API_KEY:
        try:
            from openai import AsyncOpenAI
            client_kwargs = {'api_key': settings.OPENAI_API_KEY, 'timeout': 8.0}
            if settings.OPENAI_BASE_URL:
                client_kwargs['base_url'] = settings.OPENAI_BASE_URL
            client = AsyncOpenAI(**client_kwargs)
            res = await client.embeddings.create(
                input=[text[:8000]],
                model=settings.EMBEDDING_MODEL
            )
            return res.data[0].embedding
        except Exception as exc:
            logger.warning(f"OpenAI embedding generation failed, using fallback embedding: {exc}")

    return generate_deterministic_embedding(text, dimension=settings.EMBEDDING_DIMENSION)


async def list_staging_records(
    db: AsyncSession,
    status_filter: Optional[StagingStatus] = None,
    stream_filter: Optional[StagingStreamType] = None,
    major_code_filter: Optional[str] = None
) -> List[StagingRecord]:
    """
    Administrative query to audit staged documents.
    STRICT GUARDRAIL: Admin role only.
    """
    query = select(StagingRecord)
    conditions = []
    if status_filter:
        conditions.append(StagingRecord.status == status_filter)
    if stream_filter:
        conditions.append(StagingRecord.stream_type == stream_filter)
    if major_code_filter:
        conditions.append(StagingRecord.major_code == major_code_filter)
    if conditions:
        query = query.where(and_(*conditions))
    query = query.order_by(StagingRecord.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_staging_record(db: AsyncSession, record_id: uuid.UUID) -> StagingRecord:
    query = select(StagingRecord).where(StagingRecord.id == record_id)
    result = await db.execute(query)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staging record {record_id} not found."
        )
    return record


async def update_staging_record(
    db: AsyncSession,
    record_id: uuid.UUID,
    update_data: StagingRecordUpdate
) -> StagingRecord:
    """
    Allows Administrator to refine or correct extracted roadmap payload before final approval.
    """
    record = await get_staging_record(db, record_id)
    if record.status != StagingStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot edit record in {record.status.value} status."
        )
    
    if update_data.extracted_payload is not None:
        record.extracted_payload = update_data.extracted_payload
    if update_data.source_title is not None:
        record.source_title = update_data.source_title
    if update_data.source_url is not None:
        record.source_url = update_data.source_url
    if update_data.source_page is not None:
        record.source_page = update_data.source_page
        
    await db.commit()
    await db.refresh(record)
    return record


async def review_and_publish_staging_record(
    db: AsyncSession,
    record_id: uuid.UUID,
    admin_user: User,
    review_data: StagingRecordReview
) -> StagingRecord:
    """
    Step 4: Verification & Publication (Human-in-the-Loop)
    1. Records review audit trail (reviewed_by, reviewed_at, review_notes).
    2. If APPROVED and contains roadmap data:
       - Upserts normalized roadmap JSONB into `major_roadmaps` (is_fallback = False).
       - Chunks content and generates 1536-dim vector embeddings into `knowledge_embeddings` (pgvector).
    """
    record = await get_staging_record(db, record_id)
    record.status = review_data.status
    record.reviewed_by = admin_user.id
    record.reviewed_at = datetime.now(timezone.utc)
    record.review_notes = review_data.review_notes

    # Human-in-the-Loop Publication Trigger
    if review_data.status == StagingStatus.APPROVED and record.major_code:
        payload = record.extracted_payload
        
        # Stream A: MOET Official Circular Ingestion -> Upsert directly into Major catalog
        if record.stream_type == StagingStreamType.STREAM_A_MOET:
            existing_major = await db.execute(
                select(Major).where(Major.major_code == record.major_code)
            )
            major_obj = existing_major.scalar_one_or_none()
            name = payload.get("major_name") or payload.get("name") or f"Ngành chuẩn {record.major_code}"
            riasec = payload.get("riasec") or {"R": 0.3, "I": 0.5, "A": 0.2, "S": 0.3, "E": 0.4, "C": 0.4}
            outlook = payload.get("outlook") or "Ngành đào tạo chính quy theo Thông tư quy định của Bộ GD&ĐT."
            cognitive = payload.get("cognitive") or {"abstract_thinking": "medium", "learning_environment": "structured"}
            
            if major_obj:
                major_obj.name = name
                major_obj.riasec_vector = riasec
                major_obj.industry_outlook = outlook
                major_obj.cognitive_attributes = cognitive
            else:
                new_major = Major(
                    id=uuid.uuid4(),
                    major_code=record.major_code,
                    name=name,
                    degree_level="Đại học",
                    riasec_vector=riasec,
                    cognitive_attributes=cognitive,
                    industry_outlook=outlook,
                    is_active=True
                )
                db.add(new_major)

        # Check if the staged record is a study roadmap (Stream B or contains milestones)
        if "milestones" in payload or record.stream_type == StagingStreamType.STREAM_B_ROADMAP:
            # 1. Upsert into major_roadmaps cache
            existing_cache = await db.execute(
                select(MajorRoadmap).where(MajorRoadmap.major_code == record.major_code)
            )
            cached_entry = existing_cache.scalar_one_or_none()
            title = payload.get("major_title") or f"Lộ trình học tập chuẩn hóa: {record.major_code}"
            
            if cached_entry:
                cached_entry.title = f"Lộ trình chuẩn hóa: {title}"
                cached_entry.roadmap_data = payload
                cached_entry.is_fallback = False
                cached_entry.version = "1.0-approved"
                cached_entry.updated_at = datetime.now(timezone.utc)
            else:
                new_roadmap = MajorRoadmap(
                    major_code=record.major_code,
                    title=f"Lộ trình chuẩn hóa: {title}",
                    version="1.0-approved",
                    roadmap_data=payload,
                    is_fallback=False,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.add(new_roadmap)
                
            # 2. Chunk roadmap and generate 1536-dim embeddings for knowledge_embeddings (pgvector)
            # Chunk A: Overview & Prerequisites & Target Skills
            prereqs = payload.get("prerequisite_knowledge", [])
            skills = payload.get("target_skills", [])
            overview_text = (
                f"Mã ngành: {record.major_code}. Ngành: {title}.\n"
                f"Kiến thức tiên quyết: {'; '.join(prereqs)}.\n"
                f"Kỹ năng mục tiêu đào tạo: {'; '.join(skills)}."
            )
            overview_vec = await get_text_embedding(overview_text)
            overview_embedding = KnowledgeEmbedding(
                major_code=record.major_code,
                chunk_text=overview_text,
                embedding=overview_vec,
                source_title=record.source_title,
                source_url=record.source_url,
                source_page=record.source_page,
                metadata_payload={"chunk_type": "overview", "major_code": record.major_code},
                created_at=datetime.now(timezone.utc)
            )
            db.add(overview_embedding)

            # Chunk B: Milestones
            milestones = payload.get("milestones", [])
            for m in milestones:
                step = m.get("step", 1)
                m_title = m.get("title", "")
                m_desc = m.get("description", "")
                m_objectives = m.get("learning_objectives", [])
                m_actions = m.get("actions", [])
                
                milestone_text = (
                    f"Ngành {record.major_code} - Mốc học tập {step}: {m_title}.\n"
                    f"Mô tả: {m_desc}\n"
                    f"Mục tiêu cần đạt: {'; '.join(m_objectives)}.\n"
                    f"Hành động thực hành: {'; '.join(m_actions)}."
                )
                m_vec = await get_text_embedding(milestone_text)
                milestone_embedding = KnowledgeEmbedding(
                    major_code=record.major_code,
                    chunk_text=milestone_text,
                    embedding=m_vec,
                    source_title=record.source_title,
                    source_url=record.source_url,
                    source_page=record.source_page,
                    metadata_payload={
                        "chunk_type": "milestone",
                        "step": step,
                        "major_code": record.major_code
                    },
                    created_at=datetime.now(timezone.utc)
                )
                db.add(milestone_embedding)

            # Chunk C: Reference Materials
            refs = payload.get("reference_materials", [])
            if refs:
                ref_items = [f"{r.get('title')} ({r.get('author_or_institution', '')})" for r in refs]
                ref_text = f"Tài liệu tham khảo và giáo trình ngành {record.major_code}: {'; '.join(ref_items)}."
                ref_vec = await get_text_embedding(ref_text)
                ref_embedding = KnowledgeEmbedding(
                    major_code=record.major_code,
                    chunk_text=ref_text,
                    embedding=ref_vec,
                    source_title=record.source_title,
                    source_url=record.source_url,
                    source_page=record.source_page,
                    metadata_payload={"chunk_type": "reference_materials", "major_code": record.major_code},
                    created_at=datetime.now(timezone.utc)
                )
                db.add(ref_embedding)

    await db.commit()
    await db.refresh(record)
    return record
