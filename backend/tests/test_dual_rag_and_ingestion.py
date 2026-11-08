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

    @pytest.mark.anyio
    async def test_discover_academic_resources_via_tavily_fallback(self):
        # When no external API key, provides verified fallback domain
        results = await discover_academic_resources_via_tavily("7480201", "Công nghệ thông tin")
        assert len(results) > 0
        assert is_url_whitelisted(results[0]["url"], settings.WHITELISTED_SEARCH_DOMAINS) is True
        assert "7480201" in results[0]["url"]

    @pytest.mark.anyio
    async def test_extract_roadmap_structure_matches_pydantic_schema(self):
        payload = await extract_roadmap_with_llm(
            major_code="7480201",
            major_title="Công nghệ thông tin",
            source_title="Chương trình đào tạo chuẩn ĐHQG",
            source_url="https://vnu.edu.vn/curriculum/7480201",
            scraped_content="Đề cương môn học..."
        )
        assert isinstance(payload, ExtractedRoadmapPayload)
        assert payload.major_code == "7480201"
        assert len(payload.prerequisite_knowledge) >= 2
        assert len(payload.target_skills) >= 2
        assert len(payload.milestones) >= 3
        for idx, m in enumerate(payload.milestones, start=1):
            assert m.step == idx
            assert len(m.actions) > 0
            assert len(m.learning_objectives) > 0

    @pytest.mark.anyio
    async def test_stream_b_duplicate_staged_roadmap_triggers_409(self):
        db = AsyncMock()
        # Mock database returning existing duplicate record
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = StagingRecord(
            content_hash="mock_hash",
            stream_type=StagingStreamType.STREAM_B_ROADMAP,
            status=StagingStatus.PENDING,
            source_title="Title"
        )
        db.execute.return_value = mock_res

        with patch("app.services.llamaindex_rag_orchestrator.stream_b_discovery.discover_academic_resources_via_tavily") as mock_disc:
            mock_disc.return_value = [{"title": "Chương trình", "url": "https://vnu.edu.vn/curriculum/7480201", "snippet": "Snippet", "raw_content": "Content"}]
            with pytest.raises(HTTPException) as exc:
                await discover_and_stage_roadmap(db, "7480201", "Công nghệ thông tin")
            assert exc.value.status_code == status.HTTP_409_CONFLICT


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

    @pytest.mark.anyio
    async def test_get_text_embedding_returns_1536_vector(self):
        vec = await get_text_embedding("Kiến thức tiên quyết Toán rời rạc")
        assert len(vec) == 1536
        assert all(isinstance(x, float) for x in vec)


# =========================================================================
# 5. HUMAN-IN-THE-LOOP (HITL) GOVERNANCE & PUBLICATION
# =========================================================================

class TestHITLGovernance:
    @pytest.mark.anyio
    async def test_admin_update_pending_staging_payload(self):
        db = AsyncMock()
        record_id = uuid.uuid4()
        record = StagingRecord(
            id=record_id,
            stream_type=StagingStreamType.STREAM_B_ROADMAP,
            status=StagingStatus.PENDING,
            major_code="7480201",
            content_hash="hash1",
            extracted_payload={"title": "Original Title"},
            source_title="Source",
            source_url="https://vnu.edu.vn"
        )
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = record
        db.execute.return_value = mock_res

        update_data = StagingRecordUpdate(
            extracted_payload={"title": "Updated Refined Title"},
            source_title="Verified Source Title"
        )
        updated = await update_staging_record(db, record_id, update_data)
        assert updated.extracted_payload["title"] == "Updated Refined Title"
        assert updated.source_title == "Verified Source Title"
        assert db.commit.called

    @pytest.mark.anyio
    async def test_review_approval_publishes_to_major_roadmaps_and_vector(self):
        db = AsyncMock()
        db.add = MagicMock()
        admin_user = User(id=uuid.uuid4(), email="admin@careerguide.vn", role=UserRole.ADMIN)
        record_id = uuid.uuid4()
        
        roadmap_payload = {
            "major_title": "Công nghệ thông tin",
            "prerequisite_knowledge": ["Toán học", "Logic"],
            "target_skills": ["Lập trình Python", "Cơ sở dữ liệu"],
            "milestones": [
                {
                    "step": 1,
                    "title": "Nhập môn Lập trình",
                    "description": "Làm quen với Python",
                    "duration_weeks": 4,
                    "learning_objectives": ["Viết hàm", "Xử lý mảng"],
                    "actions": ["Làm bài tập LeetCode", "Đọc giáo trình"]
                }
            ],
            "reference_materials": [
                {"title": "Giáo trình CSDL", "author_or_institution": "HUST", "url": "https://hust.edu.vn"}
            ]
        }
        
        record = StagingRecord(
            id=record_id,
            stream_type=StagingStreamType.STREAM_B_ROADMAP,
            status=StagingStatus.PENDING,
            major_code="7480201",
            content_hash="hash_approval_test",
            extracted_payload=roadmap_payload,
            source_title="ĐHQG Hà Nội",
            source_url="https://vnu.edu.vn"
        )
        
        # db.execute returns: 1st for get_staging_record, 2nd for select(MajorRoadmap)
        mock_res1 = MagicMock()
        mock_res1.scalar_one_or_none.return_value = record
        mock_res2 = MagicMock()
        mock_res2.scalar_one_or_none.return_value = None  # No prior cached roadmap
        db.execute.side_effect = [mock_res1, mock_res2]

        review_req = StagingRecordReview(
            status=StagingStatus.APPROVED,
            review_notes="Đã kiểm tra kỹ khung chương trình đối chiếu Thông tư 09."
        )

        reviewed = await review_and_publish_staging_record(db, record_id, admin_user, review_req)
        
        assert reviewed.status == StagingStatus.APPROVED
        assert reviewed.reviewed_by == admin_user.id
        assert reviewed.review_notes == "Đã kiểm tra kỹ khung chương trình đối chiếu Thông tư 09."
        
        # Verify publications added to db session
        added_objects = [call.args[0] for call in db.add.call_args_list]
        roadmap_added = any(isinstance(obj, MajorRoadmap) and obj.is_fallback is False for obj in added_objects)
        embeddings_added = [obj for obj in added_objects if isinstance(obj, KnowledgeEmbedding)]
        
        assert roadmap_added is True
        assert len(embeddings_added) >= 3  # overview, milestone, reference materials
        for emb in embeddings_added:
            assert len(emb.embedding) == 1536
            assert emb.major_code == "7480201"

    @pytest.mark.anyio
    async def test_review_rejection_does_not_publish_roadmap(self):
        db = AsyncMock()
        admin_user = User(id=uuid.uuid4(), email="admin@careerguide.vn", role=UserRole.ADMIN)
        record_id = uuid.uuid4()
        record = StagingRecord(
            id=record_id,
            stream_type=StagingStreamType.STREAM_B_ROADMAP,
            status=StagingStatus.PENDING,
            major_code="7480201",
            content_hash="hash_reject",
            extracted_payload={"title": "Invalid Curriculum"},
            source_title="Source",
            source_url="https://vnu.edu.vn"
        )
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = record
        db.execute.return_value = mock_res

        review_req = StagingRecordReview(
            status=StagingStatus.REJECTED,
            review_notes="Nội dung không chuẩn hóa."
        )
        reviewed = await review_and_publish_staging_record(db, record_id, admin_user, review_req)
        
        assert reviewed.status == StagingStatus.REJECTED
        assert not any(isinstance(call.args[0], MajorRoadmap) for call in db.add.call_args_list)


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
    async def test_uncurated_major_immediately_serves_static_fallback(self):
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
        res = await personalize_guidance(db, req)
        assert res.is_fallback is True
        assert res.major_code == "7480999"
        assert len(res.schedule) == 3 or len(res.schedule) == 4
        assert res.schedule[0].focus_skill == "Tư duy thuật toán"

    @pytest.mark.anyio
    async def test_ai_api_timeout_triggers_graceful_static_fallback(self):
        db = AsyncMock()
        cached_roadmap = MajorRoadmap(
            major_code="7480201",
            title="Lộ trình CNTT",
            version="1.0-approved",
            is_fallback=False,
            roadmap_data={
                "major_title": "Công nghệ thông tin",
                "milestones": [
                    {"step": 1, "title": "Bước 1", "learning_objectives": ["A"], "actions": ["B"]}
                ]
            }
        )
        mock_res1 = MagicMock()
        mock_res1.scalar_one_or_none.return_value = cached_roadmap
        mock_res2 = MagicMock()
        mock_res2.scalar_one_or_none.return_value = None
        db.execute.side_effect = [mock_res1, mock_res2]

        req = GuidancePersonalizationRequest(
            major_code="7480201",
            user_id=uuid.uuid4(),
            missing_skills=["Cơ sở dữ liệu"],
            weekly_hours_available=10
        )

        # Simulate OpenAI timing out (> 8.0s)
        async def slow_llm_call(*args, **kwargs):
            await asyncio.sleep(15.0)  # Exceeds 8.0s timeout

        with patch("app.services.llamaindex_rag_orchestrator.guidance_rag.settings.OPENAI_API_KEY", "mock_key"):
            with patch("app.services.llamaindex_rag_orchestrator.guidance_rag.call_llm_for_personalization", side_effect=asyncio.TimeoutError):
                response = await personalize_guidance(db, req)
                
                assert response.is_fallback is True
                assert "AI phản hồi quá 8 giây" in response.personalization_summary
                assert len(response.schedule) > 0
                assert response.schedule[0].focus_skill == "Cơ sở dữ liệu"

    @pytest.mark.anyio
    async def test_ai_network_error_triggers_graceful_fallback(self):
        db = AsyncMock()
        cached_roadmap = MajorRoadmap(
            major_code="7480201",
            title="Lộ trình CNTT",
            version="1.0-approved",
            is_fallback=False,
            roadmap_data={"milestones": [{"step": 1, "title": "Step 1"}]}
        )
        mock_res1 = MagicMock()
        mock_res1.scalar_one_or_none.return_value = cached_roadmap
        mock_res2 = MagicMock()
        mock_res2.scalar_one_or_none.return_value = None
        db.execute.side_effect = [mock_res1, mock_res2]

        req = GuidancePersonalizationRequest(
            major_code="7480201",
            user_id=uuid.uuid4(),
            missing_skills=["Cấu trúc dữ liệu"],
            weekly_hours_available=8
        )

        with patch("app.services.llamaindex_rag_orchestrator.guidance_rag.settings.OPENAI_API_KEY", "mock_key"):
            with patch("app.services.llamaindex_rag_orchestrator.guidance_rag.call_llm_for_personalization", side_effect=RuntimeError("Connection Reset by Peer")):
                response = await personalize_guidance(db, req)
                assert response.is_fallback is True
                assert "Sự cố kết nối AI API" in response.personalization_summary


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

    @pytest.mark.anyio
    async def test_cache_lookup_latency_is_under_one_second(self):
        db = AsyncMock()
        now = datetime.now(timezone.utc)
        cached_roadmap = MajorRoadmap(
            id=uuid.uuid4(),
            major_code="7480201",
            title="Lộ trình CNTT",
            version="1.0-approved",
            is_fallback=False,
            roadmap_data={
                "milestones": [],
                "prerequisite_knowledge": ["Toán"],
                "target_skills": ["Lập trình"],
                "reference_materials": [],
                "source_title": "ĐHQG",
                "source_url": "https://vnu.edu.vn"
            },
            created_at=now,
            updated_at=now
        )
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = cached_roadmap
        db.execute.return_value = mock_res

        import time
        t0 = time.perf_counter()
        # Direct DB query simulation
        from app.services.gap_roadmap_engine.service import get_cached_major_roadmap
        result = await get_cached_major_roadmap(db, "7480201")
        elapsed = time.perf_counter() - t0
        
        # Must execute within 1.0s SLA (NFR01)
        assert elapsed < 1.0
        assert result.major_code == "7480201"

# =========================================================================
# 7. AI EXPLANATION & AI COUNSELOR CHAT TESTS (FR06 & LAW 91/2025 COMPLIANCE)
# =========================================================================

class TestAIExplanationAndChatCounselor:
    @pytest.mark.anyio
    async def test_ai_explanation_strictly_anonymized_and_includes_diagnostics(self):
        from app.schemas.rag import AIExplanationRequest
        from app.services.llamaindex_rag_orchestrator.guidance_rag import explain_recommendation_with_ai

        db = AsyncMock()
        mock_major = MagicMock()
        mock_major.name = "Công nghệ thông tin"
        mock_major.category = "Máy tính và công nghệ thông tin"
        mock_major.id = uuid.uuid4()
        
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = mock_major
        mock_res.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_res

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
    async def test_ai_counselor_chat_sanitizes_pii_and_responds(self):
        from app.schemas.rag import AIChatRequest
        from app.services.llamaindex_rag_orchestrator.guidance_rag import chat_with_career_counselor

        db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        mock_res.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_res

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

    def test_llm_status_reports_model_and_masked_key(self):
        from app.services.llamaindex_rag_orchestrator.guidance_rag import get_llm_status
        status_info = get_llm_status()
        from app.core.config import settings
        assert status_info.model == settings.LLM_MODEL
        assert status_info.embedding_model == "text-embedding-3-small"
        assert isinstance(status_info.is_key_configured, bool)

    @pytest.mark.anyio
    async def test_llm_connection_test_without_key_reports_clean_failure(self):
        from app.schemas.rag import LLMConnectionTestRequest
        from app.services.llamaindex_rag_orchestrator.guidance_rag import test_llm_connection
        req = LLMConnectionTestRequest(api_key="")
        result = await test_llm_connection(req)
        assert result.success is False
        assert result.status_code == 400
        assert "Chưa cấu hình API Key" in result.message

    @pytest.mark.anyio
    async def test_llm_connection_test_with_mocked_success(self):
        from app.schemas.rag import LLMConnectionTestRequest
        from app.services.llamaindex_rag_orchestrator.guidance_rag import test_llm_connection
        with patch("openai.AsyncOpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_chat = AsyncMock()
            mock_choice = MagicMock()
            mock_choice.message.content = "PONG"
            mock_response = MagicMock(choices=[mock_choice])
            mock_chat.completions.create.return_value = mock_response
            mock_client.chat = mock_chat
            mock_openai_cls.return_value = mock_client

            req = LLMConnectionTestRequest(api_key="sk-test-valid-key", model="deepseek-4.1-flash-ckey")
            result = await test_llm_connection(req)
            assert result.success is True
            assert result.status_code == 200
            assert result.model_used == "deepseek-4.1-flash-ckey"
            assert result.preview_reply == "PONG"
            assert result.latency_ms >= 0.0

