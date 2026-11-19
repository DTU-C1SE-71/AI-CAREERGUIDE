"""Bằng chứng nguồn, snapshot và giao dịch của ingestion/HITL."""
import json
import uuid
from copy import deepcopy
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base
from app.core.ai_runtime import ConfigSnapshot, AIConfigError
from app.models.identity import User, UserRole
from app.models.taxonomy import Major
from app.models.staging import StagingRecord, StagingStatus, StagingStreamType
from app.models.roadmap import MajorRoadmap
from app.models.vector import KnowledgeEmbedding
from app.schemas.staging import StagingRecordReview, StagingRecordUpdate
from app.services.llamaindex_rag_orchestrator import stream_b_discovery as discovery
from app.services.llamaindex_rag_orchestrator import hitl_governance as governance

SOURCE = "https://hust.edu.vn/curriculum/test"
CONTENT = "Nguồn tổng hợp mô tả môn nhập môn lập trình, kiến thức logic, kỹ năng Python và bài tập viết hàm."


def roadmap():
    return {"major_code": "7480201", "major_title": "Công nghệ thông tin", "prerequisite_knowledge": ["Logic"], "target_skills": ["Python"],
            "milestones": [{"step": 1, "title": "Nhập môn lập trình", "description": "Học Python", "duration_weeks": 2, "learning_objectives": ["Viết hàm"], "actions": ["Làm bài tập"]}],
            "reference_materials": [{"title": "Đề cương tổng hợp", "author_or_institution": "Nguồn tổng hợp", "url": SOURCE, "material_type": "curriculum"}],
            "source_title": "Đề cương tổng hợp", "source_url": SOURCE, "source_page": None}


def snapshot(revision="initial"):
    return ConfigSnapshot("DATABASE", "openai_compatible", "https://provider.example/v1", "synthetic-model", "BEARER", ("openai_compatible", "https", "provider.example", 443, "/v1"), revision, "sk-synthetic-test-only-12345678")


@pytest_asyncio.fixture
async def ingestion_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "")
    path = tmp_path / "ingestion-isolated.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{path.as_posix()}")
    async with engine.begin() as conn:
        actual = (await conn.execute(text("PRAGMA database_list"))).fetchall()
        assert __import__("pathlib").Path(actual[0][2]).resolve() == path.resolve()
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as db:
        admin = User(email="admin@example.com", full_name="Quản trị tổng hợp", hashed_password="unused-test-hash", role=UserRole.ADMIN, is_active=True)
        major = Major(major_code="7480201", name="Công nghệ thông tin", riasec_vector={code: 0.5 for code in "RIASEC"}, cognitive_attributes={}, industry_outlook="Dữ liệu tổng hợp", is_active=True)
        record = StagingRecord(stream_type=StagingStreamType.STREAM_B_ROADMAP, status=StagingStatus.PENDING, major_code="7480201", content_hash=uuid.uuid4().hex * 2,
                               raw_content=CONTENT, extracted_payload=roadmap(), source_title="Đề cương tổng hợp", source_url=SOURCE)
        db.add_all([admin, major, record])
        await db.commit()
        yield db, admin, record, sessions
    await engine.dispose()


@pytest.mark.asyncio
async def test_no_tavily_key_never_invents_resources(monkeypatch):
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "")
    with pytest.raises(HTTPException) as error:
        await discovery.discover_academic_resources_via_tavily("7480201", "Công nghệ thông tin")
    assert error.value.status_code == 503


@pytest.mark.asyncio
async def test_no_embedding_key_never_returns_fake_vector(ingestion_db):
    db, _, _, _ = ingestion_db
    with pytest.raises(HTTPException):
        await governance.get_text_embedding("Kiến thức tiên quyết tổng hợp", db=db)


@pytest.mark.asyncio
async def test_repeated_review_cannot_change_final_decision(ingestion_db):
    db, admin, record, _ = ingestion_db
    await governance.review_and_publish_staging_record(db, record.id, admin, StagingRecordReview(status=StagingStatus.REJECTED))
    with pytest.raises(HTTPException) as error:
        await governance.review_and_publish_staging_record(db, record.id, admin, StagingRecordReview(status=StagingStatus.REJECTED))
    assert error.value.status_code == 409


@pytest.mark.parametrize("url", ["http://hust.edu.vn/path", "ftp://hust.edu.vn/path", "https://user:password@hust.edu.vn/path", "https://hust.edu.vn.evil.example/path"])
def test_source_url_rejects_unsafe_schemes_and_authority(url):
    assert discovery.is_url_whitelisted(url, settings.WHITELISTED_SEARCH_DOMAINS) is False


@pytest.mark.asyncio
@pytest.mark.parametrize("change", [
    {"major_code": "9999999"},
    {"source_url": "https://mit.edu/invented"},
    {"reference_materials": [{"title": "Invented", "author_or_institution": "Unknown", "url": "https://mit.edu/invented", "material_type": "textbook"}]},
    {"source_page": "Trang không có trong nguồn"},
    {"milestones": []},
])
async def test_extraction_rejects_untrusted_ids_and_sources(monkeypatch, change):
    payload = {**roadmap(), **change}
    monkeypatch.setattr(discovery.adapter, "chat", AsyncMock(return_value=json.dumps(payload)))
    with pytest.raises(HTTPException) as error:
        await discovery.extract_roadmap_with_llm("7480201", "Công nghệ thông tin", "Đề cương tổng hợp", SOURCE, CONTENT, snapshot=snapshot())
    assert error.value.status_code == 422


@pytest.mark.asyncio
async def test_extraction_provider_failure_never_creates_fallback(monkeypatch):
    monkeypatch.setattr(discovery.adapter, "chat", AsyncMock(side_effect=AIConfigError("TIMEOUT", "synthetic timeout", 504)))
    with pytest.raises(HTTPException) as error:
        await discovery.extract_roadmap_with_llm("7480201", "Công nghệ thông tin", "Đề cương tổng hợp", SOURCE, CONTENT, snapshot=snapshot())
    assert error.value.status_code == 504


@pytest.mark.asyncio
async def test_discovery_uses_one_snapshot_and_catalog_identity(ingestion_db, monkeypatch):
    db, _, _, _ = ingestion_db
    frozen = snapshot("task-start")
    resolver = AsyncMock(return_value=frozen)
    chat = AsyncMock(return_value=json.dumps(roadmap()))
    monkeypatch.setattr(discovery, "resolve_snapshot", resolver)
    monkeypatch.setattr(discovery.adapter, "chat", chat)
    discover = AsyncMock(return_value=[{"title": "Đề cương tổng hợp", "url": SOURCE, "raw_content": CONTENT}])
    monkeypatch.setattr(discovery, "discover_academic_resources_via_tavily", discover)
    monkeypatch.setattr(discovery, "fetch_with_jina_reader", AsyncMock(return_value=CONTENT))
    result = await discovery.discover_and_stage_roadmap(db, "7480201", "Tên bịa từ client")
    assert result.status == StagingStatus.PENDING
    assert result.extracted_payload["major_title"] == "Công nghệ thông tin"
    resolver.assert_awaited_once_with(db)
    assert chat.call_args.args[0] is frozen
    assert discover.call_args.args[1] == "Công nghệ thông tin"
    assert result.source_url == SOURCE and result.raw_content == CONTENT
    with pytest.raises(HTTPException) as duplicate:
        await discovery.discover_and_stage_roadmap(db, "7480201")
    assert duplicate.value.status_code == 409


@pytest.mark.asyncio
async def test_inactive_major_is_rejected_before_outbound(ingestion_db, monkeypatch):
    db, _, _, _ = ingestion_db
    major = (await db.execute(select(Major))).scalar_one()
    major.is_active = False
    await db.commit()
    resolver = AsyncMock(return_value=snapshot())
    monkeypatch.setattr(discovery, "resolve_snapshot", resolver)
    with pytest.raises(HTTPException) as error:
        await discovery.discover_and_stage_roadmap(db, "7480201")
    assert error.value.status_code == 404
    resolver.assert_not_called()


@pytest.mark.asyncio
async def test_hitl_approval_has_one_snapshot_for_all_chunks(ingestion_db, monkeypatch):
    db, admin, record, _ = ingestion_db
    frozen = snapshot("before-apply")
    resolver = AsyncMock(return_value=frozen)
    observed = []
    async def embed(config, value, **kwargs):
        observed.append(config)
        resolver.return_value = snapshot("after-apply")
        return [0.1] * 1536
    monkeypatch.setattr(governance, "resolve_snapshot", resolver)
    monkeypatch.setattr(governance.adapter, "embeddings", embed)
    approved = await governance.review_and_publish_staging_record(db, record.id, admin, StagingRecordReview(status=StagingStatus.APPROVED, review_notes="Đã đối chiếu nguồn"))
    assert approved.status == StagingStatus.APPROVED and approved.reviewed_by == admin.id
    assert len(observed) == 3 and all(config is frozen for config in observed)
    resolver.assert_awaited_once_with(db)
    cached = (await db.execute(select(MajorRoadmap))).scalar_one()
    vectors = (await db.execute(select(KnowledgeEmbedding))).scalars().all()
    assert cached.is_fallback is False
    assert len(vectors) == 3 and all(v.metadata_payload["ai_revision"] == "before-apply" for v in vectors)
    with pytest.raises(HTTPException) as repeat:
        await governance.update_staging_record(db, record.id, StagingRecordUpdate(extracted_payload=roadmap()))
    assert repeat.value.status_code == 409


@pytest.mark.asyncio
async def test_embedding_failure_rolls_back_review_and_publication(ingestion_db, monkeypatch):
    db, admin, record, _ = ingestion_db
    record_id = record.id
    monkeypatch.setattr(governance, "resolve_snapshot", AsyncMock(return_value=snapshot()))
    monkeypatch.setattr(governance.adapter, "embeddings", AsyncMock(side_effect=AIConfigError("PROVIDER_ERROR", "synthetic error", 502)))
    with pytest.raises(HTTPException) as error:
        await governance.review_and_publish_staging_record(db, record_id, admin, StagingRecordReview(status=StagingStatus.APPROVED))
    assert error.value.status_code == 502
    saved = (await db.execute(select(StagingRecord).where(StagingRecord.id == record_id))).scalar_one()
    assert saved.status == StagingStatus.PENDING and saved.reviewed_by is None
    assert not (await db.execute(select(MajorRoadmap))).scalars().all()
    assert not (await db.execute(select(KnowledgeEmbedding))).scalars().all()


@pytest.mark.asyncio
async def test_hitl_rejects_pending_status_and_unknown_payload_id(ingestion_db):
    db, admin, record, _ = ingestion_db
    with pytest.raises(HTTPException) as pending:
        await governance.review_and_publish_staging_record(db, record.id, admin, StagingRecordReview(status=StagingStatus.PENDING))
    assert pending.value.status_code == 422
    with pytest.raises(HTTPException) as changed:
        await governance.update_staging_record(db, record.id, StagingRecordUpdate(extracted_payload={**roadmap(), "major_code": "9999999"}))
    assert changed.value.status_code == 422


@pytest.mark.asyncio
async def test_stream_a_new_major_requires_explicit_profile(ingestion_db):
    db, admin, record, _ = ingestion_db
    record.stream_type = StagingStreamType.STREAM_A_MOET
    record.major_code = "7480998"
    record.extracted_payload = {"major_code": "7480998", "major_name": "Ngành tổng hợp", "admission_blocks": []}
    await db.commit()
    record_id = record.id
    with pytest.raises(HTTPException) as error:
        await governance.review_and_publish_staging_record(db, record_id, admin, StagingRecordReview(status=StagingStatus.APPROVED))
    assert error.value.status_code == 422
    assert (await db.execute(select(Major).where(Major.major_code == "7480998"))).scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_two_review_requests_have_single_final_decision(ingestion_db):
    import asyncio
    db, admin, record, sessions = ingestion_db
    admin_id, record_id = admin.id, record.id
    await db.rollback()
    async def review():
        async with sessions() as separate:
            actor = await separate.get(User, admin_id)
            try:
                await governance.review_and_publish_staging_record(separate, record_id, actor, StagingRecordReview(status=StagingStatus.REJECTED))
                return 200
            except HTTPException as error:
                return error.status_code
    assert sorted(await asyncio.gather(review(), review())) == [200, 409]
