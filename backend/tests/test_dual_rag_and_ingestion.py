import asyncio
import hashlib
import json
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from fastapi import HTTPException, status

from app.core.config import settings

@pytest.fixture(autouse=True)
def mock_openai_key_in_tests(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
from app.models.staging import StagingRecord, StagingStreamType, StagingStatus
from app.models.roadmap import MajorRoadmap
from app.models.vector import KnowledgeEmbedding
from app.models.identity import User, UserRole
from app.schemas.staging import StagingRecordUpdate, StagingRecordReview
from app.schemas.rag import (
    ExtractedRoadmapPayload,
    GuidancePersonalizationRequest,
    GuidancePersonalizationResponse,
    SemanticSearchRequest
)

from app.services.llamaindex_rag_orchestrator.stream_a_ingest import (
    compute_bytes_sha256,
    extract_majors_from_text,
    ingest_moet_circular
)
from app.services.llamaindex_rag_orchestrator.stream_b_discovery import (
    is_url_whitelisted,
    discover_academic_resources_via_tavily,
    fetch_with_jina_reader,
    extract_roadmap_with_llm,
    discover_and_stage_roadmap
)
from app.services.llamaindex_rag_orchestrator.hitl_governance import (
    generate_deterministic_embedding,
    get_text_embedding,
    list_staging_records,
    get_staging_record,
    update_staging_record,
    review_and_publish_staging_record
)
from app.services.llamaindex_rag_orchestrator.guidance_rag import (
    sanitize_pii,
    build_fallback_personalized_schedule,
    personalize_guidance,
    semantic_search_chunks
)
from app.services.gap_roadmap_engine.service import generate_static_fallback_roadmap



# @blast-radius: core, api, db, integration
# Fixture chỉ dùng dữ liệu tổng hợp và HTTP stub; không đọc DB/provider người dùng.
from sqlalchemy import select
from cryptography.fernet import Fernet
from app.models.taxonomy import Major
from test_ai_config_runtime import stubs

SOURCE_TITLE = "Nguồn học liệu tổng hợp"
SOURCE_URL = "https://vnu.edu.vn/curriculum/7480201"
SOURCE_TEXT = "Tài liệu tổng hợp: Toán học, Logic, Python và Cơ sở dữ liệu. Thực hành ba mốc kỹ năng. Nguồn tham khảo: " + SOURCE_URL


def roadmap_payload():
    return {"major_code": "7480201", "major_title": "Công nghệ thông tin",
            "prerequisite_knowledge": ["Toán học", "Logic"], "target_skills": ["Python", "Cơ sở dữ liệu"],
            "milestones": [{"step": i, "title": f"Mốc học tập {i}", "description": "Thực hành kiến thức nền", "duration_weeks": 2, "learning_objectives": ["Đọc tài liệu"], "actions": ["Làm bài tập"]} for i in range(1, 4)],
            "reference_materials": [{"title": SOURCE_TITLE, "author_or_institution": "Nguồn tổng hợp", "url": SOURCE_URL}],
            "source_title": SOURCE_TITLE, "source_url": SOURCE_URL, "source_page": None}


async def seed_major(db):
    major = Major(major_code="7480201", name="Công nghệ thông tin", category="Máy tính và công nghệ thông tin", riasec_vector={"R": .6, "I": .9, "A": .3, "S": .3, "E": .4, "C": .7}, cognitive_attributes={"thinking": "logical"}, industry_outlook="Thông tin tổng hợp đã kiểm thử", is_active=True)
    db.add(major)
    await db.commit()
    return major


async def seed_admin(db):
    admin = User(email="synthetic-admin@example.test", full_name="Admin tổng hợp", hashed_password="synthetic-non-login-hash", role=UserRole.ADMIN, is_active=True)
    db.add(admin)
    await db.commit()
    return admin


async def seed_staging(db):
    record = StagingRecord(stream_type=StagingStreamType.STREAM_B_ROADMAP, status=StagingStatus.PENDING, major_code="7480201", content_hash=hashlib.sha256(uuid.uuid4().bytes).hexdigest(), extracted_payload=roadmap_payload(), raw_content=SOURCE_TEXT, source_title=SOURCE_TITLE, source_url=SOURCE_URL)
    db.add(record)
    await db.commit()
    return record


async def configured_snapshot(db, url, monkeypatch):
    from test_ai_config_runtime import draft_for
    from app.services.ai_config.service import apply_config, resolve_snapshot
    monkeypatch.setattr(settings, "AI_CONFIG_ENCRYPTION_KEY", Fernet.generate_key().decode())
    await apply_config(db, await draft_for(db, url), "synthetic-config-admin")
    return await resolve_snapshot(db)


# =========================================================================
# 1. PII SANITIZATION TESTS (Law 91/2025/QH15 & OWASP ASVS Level 2)
# =========================================================================

class TestPIISanitization:
    def test_sanitize_emails(self):
        text = "Học sinh Nguyễn Văn A có email là nguyen.vana@hust.edu.vn và liên hệ phuhuynh@gmail.com."
        sanitized = sanitize_pii(text)
        assert "[REDACTED_EMAIL]" in sanitized
        assert "nguyen.vana@hust.edu.vn" not in sanitized
        assert "phuhuynh@gmail.com" not in sanitized

    def test_sanitize_vietnamese_phone_numbers(self):
        text = "Số điện thoại học sinh: 0912345678, số phụ huynh: +84987654321 hoặc 0388123456."
        sanitized = sanitize_pii(text)
        assert "[REDACTED_PHONE]" in sanitized
        assert "0912345678" not in sanitized
        assert "+84987654321" not in sanitized
        assert "0388123456" not in sanitized

    def test_sanitize_citizen_and_student_ids(self):
        text = "Căn cước công dân: 001202009876 (12 chữ số) và MSSV: 29211142148."
        sanitized = sanitize_pii(text)
        assert "[REDACTED_ID]" in sanitized
        assert "[REDACTED_STUDENT_ID]" in sanitized
        assert "001202009876" not in sanitized
        assert "29211142148" not in sanitized

    def test_clean_text_remains_intact(self):
        text = "Chương trình đào tạo ngành Công nghệ thông tin chuẩn Thông tư 09/2022/TT-BGDĐT."
        sanitized = sanitize_pii(text)
        assert sanitized == text


# =========================================================================
# 2. STREAM A: MOET CIRCULAR INGESTION (PDF / EXCEL / DEDUPLICATION)
# =========================================================================

class TestStreamAIngestion:
    def test_extract_majors_from_raw_moet_text(self):
        moet_sample = """
        DANH MỤC GIÁO DỤC ĐÀO TẠO CẤP IV
        7480201  Công nghệ thông tin  A00, A01, D01
        7480101  Khoa học máy tính    A00, A01
        7340101  Quản trị kinh doanh  A00, A01, D01, D07
        """
        majors = extract_majors_from_text(moet_sample)
        assert len(majors) == 3
        codes = [m["major_code"] for m in majors]
        assert "7480201" in codes
        assert "7480101" in codes
        assert "7340101" in codes
        
        cntt = next(m for m in majors if m["major_code"] == "7480201")
        assert "Công nghệ thông tin" in cntt["major_name"]
        assert "A00" in cntt["admission_blocks"]

    def test_sha256_file_hash_computation(self):
        data = b"MOET Circular 09/2022/TT-BGDDT Official Table"
        expected_hash = hashlib.sha256(data).hexdigest()
        assert compute_bytes_sha256(data) == expected_hash

    @pytest.mark.anyio
    async def test_stream_a_duplicate_document_triggers_409(self):
        db = AsyncMock()
        file_bytes = b"Sample Duplicate PDF Content 7480201"
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        # Mock database returning existing staging record
        existing_record = StagingRecord(
            content_hash=file_hash,
            stream_type=StagingStreamType.STREAM_A_MOET,
            status=StagingStatus.PENDING,
            source_title="Thông tư 09"
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_record
        db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await ingest_moet_circular(db, file_bytes, "moet_09.pdf")
        
        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        assert "Duplicate document detected" in exc_info.value.detail

    @pytest.mark.anyio
    async def test_stream_a_successful_ingestion(self):
        db = AsyncMock()
        db.add = MagicMock()
        file_bytes = b"7480201 Cong nghe thong tin A00 A01\n7480101 Khoa hoc may tinh A00"
        
        # Mock database returning no duplicates
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        response = await ingest_moet_circular(db, file_bytes, "circular_sample.txt")
        assert response.total_parsed == 2
        assert response.records_staged >= 2
        assert db.add.called
        assert db.commit.called


# =========================================================================
# 3. STREAM B: AUTOMATED ROADMAP DISCOVERY (TAVILY, JINA, LLM EXTRACTION)
# =========================================================================

class TestStreamBDiscovery:
    def test_domain_whitelisting_guardrail(self):
        # Whitelisted academic domains
        assert is_url_whitelisted("https://hust.edu.vn/ctdt/cntt", settings.WHITELISTED_SEARCH_DOMAINS) is True
        assert is_url_whitelisted("https://vnu.edu.vn/curriculum/7480201", settings.WHITELISTED_SEARCH_DOMAINS) is True
        assert is_url_whitelisted("https://mit.edu/courses/eecs", settings.WHITELISTED_SEARCH_DOMAINS) is True
        assert is_url_whitelisted("https://coursera.org/specializations/cs", settings.WHITELISTED_SEARCH_DOMAINS) is True
        assert is_url_whitelisted("https://roadmap.sh/computer-science", settings.WHITELISTED_SEARCH_DOMAINS) is True
        
        # Strictly rejected non-whitelisted or untrusted domains
        assert is_url_whitelisted("https://unverified-blog.com/it-guide", settings.WHITELISTED_SEARCH_DOMAINS) is False
        assert is_url_whitelisted("https://buy-cheap-diploma.xyz/degree", settings.WHITELISTED_SEARCH_DOMAINS) is False
        assert is_url_whitelisted("https://social-network.org/post/123", settings.WHITELISTED_SEARCH_DOMAINS) is False

    @pytest.mark.asyncio
    async def test_missing_tavily_key_never_invents_fallback_source(self, monkeypatch):
        monkeypatch.setattr(settings, "TAVILY_API_KEY", "")
        with pytest.raises(HTTPException) as exc:
            await discover_academic_resources_via_tavily("7480201", "Công nghệ thông tin")
        assert exc.value.status_code == 503
        assert "Chưa cấu hình Tavily" in exc.value.detail

    @pytest.mark.asyncio
    async def test_extract_roadmap_structure_matches_pydantic_schema(self, ai_runtime_db, stubs, monkeypatch):
        db = ai_runtime_db
        a, _ = stubs
        snapshot = await configured_snapshot(db, a.url, monkeypatch)
        evidence = roadmap_payload()
        a.payload = {"choices": [{"message": {"content": json.dumps(evidence)}, "finish_reason": "stop"}]}
        payload = await extract_roadmap_with_llm("7480201", "Công nghệ thông tin", SOURCE_TITLE, SOURCE_URL, SOURCE_TEXT, snapshot=snapshot, db=db)
        assert isinstance(payload, ExtractedRoadmapPayload)
        assert payload.major_code == "7480201"
        assert len(payload.prerequisite_knowledge) >= 2
        assert len(payload.target_skills) >= 2
        assert len(payload.milestones) >= 3
        for idx, milestone in enumerate(payload.milestones, start=1):
            assert milestone.step == idx
            assert milestone.actions and milestone.learning_objectives
        assert a.received[0]["body"]["model"] == snapshot.model

    @pytest.mark.asyncio
    async def test_stream_b_duplicate_staged_roadmap_triggers_409(self, ai_runtime_db, stubs, monkeypatch):
        db = ai_runtime_db
        a, _ = stubs
        await seed_major(db)
        await configured_snapshot(db, a.url, monkeypatch)
        a.payload = {"choices": [{"message": {"content": json.dumps(roadmap_payload())}, "finish_reason": "stop"}]}
        with patch("app.services.llamaindex_rag_orchestrator.stream_b_discovery.discover_academic_resources_via_tavily", new=AsyncMock(return_value=[{"title": SOURCE_TITLE, "url": SOURCE_URL, "raw_content": SOURCE_TEXT}])):
            with patch("app.services.llamaindex_rag_orchestrator.stream_b_discovery.fetch_with_jina_reader", new=AsyncMock(return_value=SOURCE_TEXT)):
                first = await discover_and_stage_roadmap(db, "7480201", "Công nghệ thông tin")
                assert first.status == StagingStatus.PENDING
                with pytest.raises(HTTPException) as exc:
                    await discover_and_stage_roadmap(db, "7480201", "Công nghệ thông tin")
                assert exc.value.status_code == 409
        assert len((await db.execute(select(StagingRecord))).scalars().all()) == 1


# =========================================================================
# 4. VECTOR EMBEDDING GENERATION (1536 DIMENSIONS & NORMALIZATION)
# =========================================================================

class TestVectorEmbedding:
    def test_deterministic_embedding_dimension_and_unit_norm(self):
        vec = generate_deterministic_embedding("Chương trình đào tạo Công nghệ thông tin")
        assert len(vec) == 1536
        l2_norm = sum(x * x for x in vec) ** 0.5
        assert pytest.approx(l2_norm, rel=1e-5) == 1.0

    def test_deterministic_embedding_repeatability(self):
        text = "Kỹ năng lập trình cấu trúc dữ liệu và giải thuật"
        vec1 = generate_deterministic_embedding(text)
        vec2 = generate_deterministic_embedding(text)
        assert vec1 == vec2

    @pytest.mark.asyncio
    async def test_get_text_embedding_returns_1536_vector(self, ai_runtime_db, stubs, monkeypatch):
        a, _ = stubs
        snapshot = await configured_snapshot(ai_runtime_db, a.url, monkeypatch)
        vector = [1.0] + [0.0] * 1535
        a.payload = {"data": [{"embedding": vector}]}
        vec = await get_text_embedding("Kiến thức tiên quyết Toán rời rạc", snapshot=snapshot, db=ai_runtime_db)
        assert len(vec) == 1536 and all(isinstance(x, float) for x in vec)
        assert vec == vector
        assert a.received[0]["path"].endswith("/embeddings")


# =========================================================================
# 5. HUMAN-IN-THE-LOOP (HITL) GOVERNANCE & PUBLICATION
# =========================================================================

class TestHITLGovernance:
    @pytest.mark.asyncio
    async def test_admin_update_pending_staging_payload(self, ai_runtime_db):
        db = ai_runtime_db
        await seed_major(db)
        record = await seed_staging(db)
        changed = roadmap_payload()
        changed["milestones"][0]["title"] = "Nền tảng đã kiểm chứng"
        updated = await update_staging_record(db, record.id, StagingRecordUpdate(extracted_payload=changed, source_title=SOURCE_TITLE))
        await db.refresh(updated)
        assert updated.extracted_payload["milestones"][0]["title"] == "Nền tảng đã kiểm chứng"
        assert updated.source_title == SOURCE_TITLE and updated.status == StagingStatus.PENDING

    @pytest.mark.asyncio
    async def test_review_approval_publishes_to_major_roadmaps_and_vector(self, ai_runtime_db, stubs, monkeypatch):
        db = ai_runtime_db
        a, _ = stubs
        await seed_major(db)
        admin = await seed_admin(db)
        record = await seed_staging(db)
        await configured_snapshot(db, a.url, monkeypatch)
        a.payload = {"data": [{"embedding": [1.0] + [0.0] * 1535}]}
        reviewed = await review_and_publish_staging_record(db, record.id, admin, StagingRecordReview(status=StagingStatus.APPROVED, review_notes="Đã đối chiếu nguồn tổng hợp."))
        assert reviewed.status == StagingStatus.APPROVED
        assert reviewed.reviewed_by == admin.id
        assert reviewed.review_notes == "Đã đối chiếu nguồn tổng hợp."
        roadmap = (await db.execute(select(MajorRoadmap))).scalar_one()
        embeddings = (await db.execute(select(KnowledgeEmbedding))).scalars().all()
        assert roadmap.is_fallback is False
        assert len(embeddings) >= 3
        for embedding in embeddings:
            assert len(embedding.embedding) == 1536
            assert embedding.major_code == "7480201"
        assert len(a.received) == len(embeddings)

    @pytest.mark.asyncio
    async def test_review_rejection_does_not_publish_roadmap(self, ai_runtime_db):
        db = ai_runtime_db
        await seed_major(db)
        admin = await seed_admin(db)
        record = await seed_staging(db)
        reviewed = await review_and_publish_staging_record(db, record.id, admin, StagingRecordReview(status=StagingStatus.REJECTED, review_notes="Nội dung chưa đủ bằng chứng."))
        assert reviewed.status == StagingStatus.REJECTED
        assert not (await db.execute(select(MajorRoadmap))).scalars().all()
        assert not (await db.execute(select(KnowledgeEmbedding))).scalars().all()


# =========================================================================
# 6. GUIDANCE RAG, TIMEOUT & GRACEFUL STATIC FALLBACK (NFR01, NFR05)
# =========================================================================

class TestGuidanceRAGAndFallback:
    def test_static_fallback_template_generation(self):
        template = generate_static_fallback_roadmap("7480201", "Công nghệ thông tin")
        assert "milestones" in template
        assert len(template["milestones"]) >= 3
        assert "prerequisite_knowledge" in template
        assert "target_skills" in template
        assert "reference_materials" in template

    @pytest.mark.anyio
    async def test_unknown_major_is_rejected_before_personalization(self):
        db = AsyncMock()
        # Mock database returning no cached roadmap
        mock_res1 = MagicMock()
        mock_res1.scalar_one_or_none.return_value = None  # No MajorRoadmap
        mock_res2 = MagicMock()
        mock_res2.scalar_one_or_none.return_value = None  # No Major entry
        db.execute.side_effect = [mock_res1, mock_res2]

        req = GuidancePersonalizationRequest(
            major_code="7480999",
            user_id=uuid.uuid4(),
            missing_skills=["Tư duy thuật toán", "Lập trình căn bản"],
            weekly_hours_available=12
        )
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as error:
            await personalize_guidance(db, req)
        assert error.value.status_code == 404

    @pytest.mark.asyncio
    @patch("app.services.gap_roadmap_engine.service.get_student_major_skill_gaps", new_callable=AsyncMock, return_value={})
    async def test_personalization_does_not_call_slow_llm(self, gaps, ai_runtime_db):
        db = ai_runtime_db
        await seed_major(db)
        req = GuidancePersonalizationRequest(major_code="7480201", user_id=uuid.uuid4(), missing_skills=["Cơ sở dữ liệu"], weekly_hours_available=10)
        with patch("app.services.ai_config.adapter.chat", side_effect=asyncio.TimeoutError) as provider:
            response = await personalize_guidance(db, req)
            provider.assert_not_called()
        assert response.is_fallback is True
        assert "mẫu khám phá" in response.personalization_summary
        assert response.schedule and response.schedule[0].focus_skill != "Cơ sở dữ liệu"

    @pytest.mark.asyncio
    @patch("app.services.gap_roadmap_engine.service.get_student_major_skill_gaps", new_callable=AsyncMock, return_value={})
    async def test_personalization_is_independent_of_provider_errors(self, gaps, ai_runtime_db):
        db = ai_runtime_db
        await seed_major(db)
        req = GuidancePersonalizationRequest(major_code="7480201", user_id=uuid.uuid4(), missing_skills=["Cấu trúc dữ liệu"], weekly_hours_available=8)
        with patch("app.services.ai_config.adapter.chat", side_effect=RuntimeError("Synthetic provider failure")) as provider:
            response = await personalize_guidance(db, req)
            provider.assert_not_called()
        assert response.is_fallback is True
        assert "mẫu khám phá" in response.personalization_summary


# =========================================================================
# 7. SECURITY & ARCHITECTURAL BOUNDARY ISOLATION (Table 6 Guardrails)
# =========================================================================

class TestSecurityAndGuardrails:
    def test_student_role_cannot_be_confused_with_admin(self):
        student = User(id=uuid.uuid4(), email="student@highschool.edu.vn", role=UserRole.STUDENT)
        admin = User(id=uuid.uuid4(), email="admin@careerguide.vn", role=UserRole.ADMIN)
        assert student.role == UserRole.STUDENT
        assert admin.role == UserRole.ADMIN
        assert student.role != UserRole.ADMIN

    @pytest.mark.asyncio
    async def test_cache_lookup_latency_is_under_one_second(self, ai_runtime_db):
        import time
        from app.services.gap_roadmap_engine.service import get_cached_major_roadmap
        db = ai_runtime_db
        await seed_major(db)
        db.add(MajorRoadmap(major_code="7480201", title="Lộ trình CNTT", version="1.0-approved", is_fallback=False, roadmap_data=roadmap_payload()))
        await db.commit()
        start = time.perf_counter()
        result = await get_cached_major_roadmap(db, "7480201")
        assert time.perf_counter() - start < 1.0
        assert result.major_code == "7480201" and result.is_fallback is False

# =========================================================================
# 7. AI EXPLANATION & AI COUNSELOR CHAT TESTS (FR06 & LAW 91/2025 COMPLIANCE)
# =========================================================================

class TestAIExplanationAndChatCounselor:
    @pytest.mark.anyio
    async def test_ai_explanation_strictly_anonymized_and_includes_diagnostics(self, ai_runtime_db):
        from app.schemas.rag import AIExplanationRequest
        from app.services.llamaindex_rag_orchestrator.guidance_rag import explain_recommendation_with_ai

        db = ai_runtime_db
        await seed_major(db)

        req = AIExplanationRequest(
            major_code="7480201",
            riasec_scores={"R": 0.85, "I": 0.90, "A": 0.40, "S": 0.30, "E": 0.50, "C": 0.70},
            grades_by_subject={"math": 9.2, "physics": 9.0, "chemistry": 8.0, "english": 8.5},
            diagnostic_skills_mastered=["SKILL_PRE_LOGIC_DISCRETE", "SKILL_TAR_PROG_PYTHON"]
        )

        resp = await explain_recommendation_with_ai(db, req)
        assert resp.major_code == "7480201"
        assert resp.major_name == "Công nghệ thông tin"
        assert "SKILL_PRE_LOGIC_DISCRETE" in resp.diagnostic_readiness or "2 kỹ năng" in resp.diagnostic_readiness
        assert len(resp.strengths) >= 2
        assert len(resp.recommended_focus_areas) >= 2

        # PII Verification: No personal identifiers in output
        assert "@" not in resp.detailed_explanation
        assert "09" not in resp.detailed_explanation

    @pytest.mark.anyio
    async def test_ai_explanation_database_caching(self, ai_runtime_db):
        from app.schemas.rag import AIExplanationRequest
        from app.services.llamaindex_rag_orchestrator.guidance_rag import explain_recommendation_with_ai
        from app.models.insight import MajorExplanationInsight
        from sqlalchemy import select

        db = ai_runtime_db
        await seed_major(db)

        req = AIExplanationRequest(
            major_code="7480201",
            riasec_scores={"R": 0.85, "I": 0.90},
            grades_by_subject={"math": 9.0},
        )

        resp1 = await explain_recommendation_with_ai(db, req)
        assert resp1.major_code == "7480201"

        # Check DB has cached record
        stmt = select(MajorExplanationInsight).where(MajorExplanationInsight.major_code == "7480201")
        cached = (await db.execute(stmt)).scalar_one_or_none()
        assert cached is not None
        assert cached.major_code == "7480201"
        assert cached.detailed_explanation == resp1.detailed_explanation

        # Second call returns cached content with 0 extra token overhead
        resp2 = await explain_recommendation_with_ai(db, req)
        assert resp2.detailed_explanation == resp1.detailed_explanation

    @pytest.mark.anyio
    async def test_ai_counselor_chat_sanitizes_pii_and_responds(self, ai_runtime_db):
        from app.schemas.rag import AIChatRequest
        from app.services.llamaindex_rag_orchestrator.guidance_rag import chat_with_career_counselor

        db = ai_runtime_db
        await seed_major(db)

        # Student sends message containing accidental PII
        req = AIChatRequest(
            message="Em tên là Nguyễn Tuấn, sđt 0987654321, tại sao em lại phù hợp với ngành Công nghệ thông tin?",
            major_code="7480201",
            riasec_scores={"R": 0.8, "I": 0.9, "A": 0.3, "S": 0.4, "E": 0.5, "C": 0.6},
            grades_by_subject={"math": 9.0, "physics": 8.5},
            diagnostic_skills_mastered=["SKILL_PRE_LOGIC_DISCRETE"]
        )

        resp = await chat_with_career_counselor(db, req)
        assert resp.reply is not None
        assert len(resp.reply) > 20
        assert len(resp.suggested_followups) >= 2
        # Ensure student's personal phone number was not echoed or exposed
        assert "0987654321" not in resp.reply

    @pytest.mark.asyncio
    async def test_llm_status_reports_model_and_masked_key(self, ai_runtime_db, monkeypatch):
        from app.services.llamaindex_rag_orchestrator.guidance_rag import get_llm_status
        monkeypatch.setattr(settings, "LLM_API_KEY", "sk-synth-status-test-only")
        status_info = await get_llm_status(ai_runtime_db)
        assert status_info["active"]["model"] == settings.LLM_MODEL
        assert status_info["credential"]["state"] == "SET"
        assert status_info["credential"]["masked"]
        assert "sk-synth-status-test-only" not in json.dumps(status_info)

    @pytest.mark.asyncio
    async def test_llm_connection_test_without_key_reports_clean_failure(self, ai_runtime_db):
        from app.schemas.ai_config import AIConfigProbe
        from app.services.llamaindex_rag_orchestrator.guidance_rag import get_llm_status, test_llm_connection
        state = await get_llm_status(ai_runtime_db)
        active = state["active"]
        req = AIConfigProbe(source_mode="ENV", protocol=active["protocol"], base_url=active["base_url"], model=active["model"], auth_mode="BEARER", credential_action="KEEP", base_revision_token=state["revision_token"], probe_request_id="without-key", draft_digest="draft")
        result = await test_llm_connection(req, ai_runtime_db, "test-without-key")
        assert result["success"] is False
        assert result["status_code"] == 409
        assert result["code"] == "UNCONFIGURED_CREDENTIAL"

    @pytest.mark.asyncio
    async def test_llm_connection_test_with_actual_http_stub(self, ai_runtime_db, stubs, monkeypatch):
        from app.services.llamaindex_rag_orchestrator.guidance_rag import test_llm_connection
        from test_ai_config_runtime import draft_for, probe_for
        a, _ = stubs
        request = probe_for(await draft_for(ai_runtime_db, a.url, model="synthetic-probe-model"))
        result = await test_llm_connection(request, ai_runtime_db, "probe-integration")
        assert result["success"] is True
        assert result["status_code"] == 200
        assert result["model_used"] == "synthetic-probe-model"
        assert result["latency_ms"] >= 0
        assert len(a.received) == 1 and a.received[0]["body"]["max_tokens"] == 64

    @pytest.mark.asyncio
    async def test_dynamic_token_resolution_respects_safe_budget_and_exact_model(self, ai_runtime_db):
        from app.core.llm_client import _match_model_record, _parse_capabilities, resolve_model_token_limits, clear_model_caps_cache
        from app.services.ai_config.service import resolve_snapshot
        clear_model_caps_cache()
        models = [{"id": "cx/gpt-6-luna", "capabilities": {"contextWindow": 272000, "maxOutput": 128000}}]
        assert _match_model_record(models, "gpt-6-luna") is None
        matched = _match_model_record(models, "cx/gpt-6-luna")
        assert matched is not None
        caps = _parse_capabilities(matched)
        assert caps["max_output_tokens"] == 128000
        assert caps["context_window"] == 272000 and caps["max_context_chars"] == 1000000
        snapshot = await resolve_snapshot(ai_runtime_db, allow_unconfigured=True)
        with patch("app.services.ai_config.adapter.list_models", side_effect=AssertionError("No key must not call provider")) as listing:
            limits = await resolve_model_token_limits(snapshot)
            listing.assert_not_called()
        assert limits["max_output_tokens"] <= 4096
