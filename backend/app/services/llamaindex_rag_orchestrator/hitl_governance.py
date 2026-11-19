"""Kiểm duyệt nguyên tử, không xuất bản payload hoặc embedding chưa được xác thực."""
import asyncio
import hashlib
import math
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.ai_runtime import ConfigSnapshot
from app.models.staging import StagingRecord, StagingStreamType, StagingStatus
from app.models.roadmap import MajorRoadmap
from app.models.vector import KnowledgeEmbedding
from app.models.identity import User, UserRole
from app.models.taxonomy import Major, SubjectBlock, MajorSubjectBlock
from app.schemas.staging import StagingRecordUpdate, StagingRecordReview
from app.services.ai_config import adapter
from app.services.ai_config.service import resolve_snapshot
from app.services.llamaindex_rag_orchestrator.stream_b_discovery import is_url_whitelisted, validate_roadmap_evidence


def generate_deterministic_embedding(text: str, dimension: int = 1536) -> list[float]:
    """
    Generates a deterministic 1536-dimensional normalized unit vector from input text.
    Chỉ phục vụ test toán học; không dùng làm embedding runtime hoặc bằng chứng đã đo.
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



async def get_text_embedding(text: str, *, snapshot: ConfigSnapshot | None = None, db: AsyncSession | None = None) -> list[float]:
    """Provider lỗi hoặc key trống phải dừng; không tạo vector ngẫu nhiên thay thế."""
    snapshot = snapshot or await resolve_snapshot(db)
    from app.services.llamaindex_rag_orchestrator.guidance_rag import sanitize_pii
    return await adapter.embeddings(snapshot, sanitize_pii(text), dimensions=1536)


async def list_staging_records(db: AsyncSession, status_filter: Optional[StagingStatus] = None,
                               stream_filter: Optional[StagingStreamType] = None,
                               major_code_filter: Optional[str] = None, limit: Optional[int] = None, offset: int = 0) -> list[StagingRecord]:
    query = select(StagingRecord)
    if status_filter:
        query = query.where(StagingRecord.status == status_filter)
    if stream_filter:
        query = query.where(StagingRecord.stream_type == stream_filter)
    if major_code_filter:
        query = query.where(StagingRecord.major_code == major_code_filter)
    query = query.order_by(StagingRecord.created_at.desc(), StagingRecord.id)
    # Alias hiện hữu trả danh sách hoàn chỉnh để UI phân trang/lọc không mất bản ghi.
    if limit is not None:
        query = query.limit(min(max(limit, 1), 200)).offset(max(offset, 0))
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_staging_record(db: AsyncSession, record_id: uuid.UUID, *, for_update: bool = False) -> StagingRecord:
    query = select(StagingRecord).where(StagingRecord.id == record_id).execution_options(populate_existing=True)
    if for_update:
        query = query.with_for_update()
    record = (await db.execute(query)).scalar_one_or_none()
    if record is None:
        raise HTTPException(404, "Không tìm thấy bản ghi kiểm duyệt.")
    return record


def _pending(record: StagingRecord) -> None:
    if record.status != StagingStatus.PENDING:
        raise HTTPException(409, "Bản ghi đã được duyệt hoặc từ chối; hãy tải lại danh sách.")


def _record_conditions(record: StagingRecord) -> list:
    """CAS bổ sung cho engine không có row lock, cũng phát hiện edit giữa tác vụ."""
    return [StagingRecord.id == record.id, StagingRecord.status == StagingStatus.PENDING,
            StagingRecord.extracted_payload == deepcopy(record.extracted_payload),
            StagingRecord.source_url == record.source_url, StagingRecord.source_title == record.source_title,
            StagingRecord.source_page == record.source_page, StagingRecord.raw_content == record.raw_content,
            StagingRecord.content_hash == record.content_hash]


async def _major(db: AsyncSession, code: str, *, active: bool = False) -> Major | None:
    query = select(Major).where(Major.major_code == code)
    if active:
        query = query.where(Major.is_active.is_(True))
    return (await db.execute(query.with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()


async def _validate_payload(db: AsyncSession, record: StagingRecord, payload: dict, source_title: str, source_url: str):
    if not record.major_code or not re.fullmatch(r"[0-9]{7}", record.major_code):
        raise HTTPException(422, "Bản ghi tổng hợp không thể xuất bản; hãy duyệt từng ngành.")
    if record.stream_type == StagingStreamType.STREAM_B_ROADMAP:
        major = await _major(db, record.major_code, active=True)
        if major is None:
            raise HTTPException(422, "Lộ trình chỉ được xuất bản cho ngành đang hoạt động.")
        result = validate_roadmap_evidence(payload, record.major_code, source_title, source_url, record.raw_content or "")
        result.major_title = major.name
        return result.model_dump(), major, []
    if record.stream_type != StagingStreamType.STREAM_A_MOET:
        raise HTTPException(422, "Loại bản ghi kiểm duyệt không được hỗ trợ.")
    if not is_url_whitelisted(source_url, settings.WHITELISTED_SEARCH_DOMAINS + ["moet.gov.vn"]):
        raise HTTPException(422, "Nguồn danh mục ngành không hợp lệ.")
    if not isinstance(payload, dict) or payload.get("major_code") != record.major_code:
        raise HTTPException(422, "Mã ngành trong payload không khớp bản ghi.")
    name = payload.get("major_name") or payload.get("name")
    if not isinstance(name, str) or not 2 <= len(name.strip()) <= 255:
        raise HTTPException(422, "Cần tên ngành có trong tài liệu nguồn.")
    major = await _major(db, record.major_code)
    if major is None:
        riasec = payload.get("riasec") or payload.get("riasec_vector")
        cognitive = payload.get("cognitive") or payload.get("cognitive_attributes")
        outlook = payload.get("outlook") or payload.get("industry_outlook")
        if not isinstance(riasec, dict) or set(riasec) != set("RIASEC") or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1 for v in riasec.values()):
            raise HTTPException(422, "Ngành mới cần vector RIASEC đủ sáu chiều hợp lệ; không tự điền điểm.")
        if not isinstance(cognitive, dict) or not cognitive or any(not isinstance(v, str) or not v.strip() for v in cognitive.values()) or not isinstance(outlook, str) or not outlook.strip():
            raise HTTPException(422, "Ngành mới cần hồ sơ nhận thức và mô tả triển vọng được kiểm chứng.")
    blocks = payload.get("admission_blocks", [])
    if not isinstance(blocks, list) or len(blocks) > 30 or any(not isinstance(b, str) or not re.fullmatch(r"[A-Z][0-9]{2}", b) for b in blocks) or len(set(blocks)) != len(blocks):
        raise HTTPException(422, "Tổ hợp tuyển sinh không hợp lệ.")
    rows = []
    if blocks:
        rows = list((await db.execute(select(SubjectBlock).where(SubjectBlock.block_code.in_(blocks)))).scalars().all())
        if {row.block_code for row in rows} != set(blocks):
            raise HTTPException(422, "Tổ hợp tuyển sinh chưa có trong danh mục đã xác minh.")
    return dict(payload), major, rows


async def update_staging_record(db: AsyncSession, record_id: uuid.UUID, update_data: StagingRecordUpdate) -> StagingRecord:
    """Chỉnh bản PENDING có khóa; không để phản hồi sửa muộn ghi đè bản đã duyệt."""
    try:
        record = await get_staging_record(db, record_id, for_update=True)
        _pending(record)
        conditions = _record_conditions(record)
        payload = update_data.extracted_payload if update_data.extracted_payload is not None else record.extracted_payload
        title = update_data.source_title if update_data.source_title is not None else record.source_title
        url = update_data.source_url if update_data.source_url is not None else record.source_url
        validated, _, _ = await _validate_payload(db, record, payload, title, url)
        values = {"extracted_payload": validated, "source_title": title, "source_url": url}
        if update_data.source_page is not None:
            if record.stream_type == StagingStreamType.STREAM_B_ROADMAP and update_data.source_page != validated.get("source_page"):
                raise HTTPException(422, "Trang nguồn phải khớp trích dẫn đã được kiểm chứng trong payload.")
            values["source_page"] = update_data.source_page
        result = await db.execute(update(StagingRecord).where(*conditions).values(**values).execution_options(synchronize_session=False))
        if result.rowcount != 1:
            raise HTTPException(409, "Bản ghi vừa thay đổi; hãy tải lại trước khi lưu.")
        await db.commit()
        await db.refresh(record)
        return record
    except Exception:
        await db.rollback()
        raise


def _roadmap_chunks(code: str, payload: dict) -> list[tuple[str, dict]]:
    chunks = [(f"Mã ngành: {code}. Ngành: {payload['major_title']}.\nKiến thức tiên quyết: {'; '.join(payload['prerequisite_knowledge'])}.\nKỹ năng: {'; '.join(payload['target_skills'])}.", {"chunk_type": "overview"})]
    for milestone in payload["milestones"]:
        chunks.append((f"Ngành {code} - Mốc {milestone['step']}: {milestone['title']}.\n{milestone['description']}\nMục tiêu: {'; '.join(milestone['learning_objectives'])}.\nHành động: {'; '.join(milestone['actions'])}.", {"chunk_type": "milestone", "step": milestone["step"]}))
    if payload["reference_materials"]:
        chunks.append(("Tài liệu: " + "; ".join(f"{r['title']} ({r['author_or_institution']})" for r in payload["reference_materials"]), {"chunk_type": "reference_materials"}))
    if any(len(text) > 16000 for text, _ in chunks):
        raise HTTPException(422, "Nội dung một đoạn học liệu vượt ngân sách embedding.")
    return chunks


async def review_and_publish_staging_record(db: AsyncSession, record_id: uuid.UUID, admin_user: User, review_data: StagingRecordReview) -> StagingRecord:
    """Khóa bản ghi + CAS; quyết định, roadmap và vector commit nguyên tử."""
    if review_data.status not in (StagingStatus.APPROVED, StagingStatus.REJECTED):
        raise HTTPException(422, "Chỉ cho phép duyệt hoặc từ chối bản ghi.")
    try:
        async with asyncio.timeout(60):
            # Quyền vẫn do DB xác nhận khi service được gọi trực tiếp.
            actor = (await db.execute(select(User).where(User.id == admin_user.id).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
            if actor is None or actor.role != UserRole.ADMIN or not actor.is_active:
                raise HTTPException(403, "Quyền quản trị không còn hiệu lực.")
            record = await get_staging_record(db, record_id, for_update=True)
            _pending(record)
            conditions = _record_conditions(record)
            payload, major, blocks = record.extracted_payload, None, []
            embedded = []
            if review_data.status == StagingStatus.APPROVED:
                payload, major, blocks = await _validate_payload(db, record, payload, record.source_title, record.source_url)
                if record.stream_type == StagingStreamType.STREAM_B_ROADMAP:
                    if record.source_page != payload.get("source_page"):
                        raise HTTPException(422, "Trang nguồn trong bản ghi không khớp payload đã xác minh.")
                    snapshot = await resolve_snapshot(db)
                    for text_value, metadata in _roadmap_chunks(record.major_code, payload):
                        vector = await get_text_embedding(text_value, snapshot=snapshot, db=db)
                        embedded.append((text_value, metadata, vector, snapshot.revision_token))
            now = datetime.now(timezone.utc)
            claimed = await db.execute(update(StagingRecord).where(*conditions).values(
                status=review_data.status, reviewed_by=actor.id, reviewed_at=now,
                review_notes=review_data.review_notes, extracted_payload=payload,
            ).execution_options(synchronize_session=False))
            if claimed.rowcount != 1:
                raise HTTPException(409, "Bản ghi vừa được xử lý hoặc chỉnh sửa; hãy tải lại.")
            if review_data.status == StagingStatus.APPROVED:
                if record.stream_type == StagingStreamType.STREAM_A_MOET:
                    if major is None:
                        major = Major(id=uuid.uuid4(), major_code=record.major_code,
                                      name=payload.get("major_name") or payload["name"],
                                      riasec_vector=payload.get("riasec") or payload["riasec_vector"],
                                      cognitive_attributes=payload.get("cognitive") or payload["cognitive_attributes"],
                                      industry_outlook=payload.get("outlook") or payload["industry_outlook"], is_active=True)
                        db.add(major)
                        await db.flush()
                    else:
                        major.name = payload.get("major_name") or payload["name"]
                    if "admission_blocks" in payload:
                        await db.execute(delete(MajorSubjectBlock).where(MajorSubjectBlock.major_id == major.id))
                        db.add_all([MajorSubjectBlock(major_id=major.id, subject_block_id=block.id) for block in blocks])
                else:
                    cached = (await db.execute(select(MajorRoadmap).where(MajorRoadmap.major_code == record.major_code).with_for_update())).scalar_one_or_none()
                    if cached is None:
                        cached = MajorRoadmap(major_code=record.major_code, title=payload["major_title"], version="1.0-approved", roadmap_data=payload, is_fallback=False)
                        db.add(cached)
                    else:
                        cached.title, cached.roadmap_data, cached.is_fallback = payload["major_title"], payload, False
                        cached.version, cached.updated_at = "1.0-approved", now
                    await db.execute(delete(KnowledgeEmbedding).where(KnowledgeEmbedding.major_code == record.major_code,
                        KnowledgeEmbedding.metadata_payload["chunk_type"].as_string().in_(["overview", "milestone", "reference_materials"])))
                    for text_value, metadata, vector, revision in embedded:
                        db.add(KnowledgeEmbedding(major_code=record.major_code, chunk_text=text_value, embedding=vector,
                               source_title=record.source_title, source_url=record.source_url, source_page=record.source_page,
                               metadata_payload={**metadata, "major_code": record.major_code, "staging_id": str(record.id), "ai_revision": revision}))
            await db.commit()
            await db.refresh(record)
            return record
    except TimeoutError:
        await db.rollback()
        raise HTTPException(504, "Kiểm duyệt quá thời gian; chưa xuất bản dữ liệu.") from None
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Dữ liệu vừa thay đổi trong phiên khác; chưa xuất bản bản ghi này.") from None
    except Exception:
        await db.rollback()
        raise
