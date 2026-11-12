"""Tests cho 2 agent: Phân tích ngành (cache-first AI) và Phân tích kỹ năng học sinh."""

import uuid
from typing import Any, Dict

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base
from app.schemas.insight import StudentSkillAnalysisRequest
from app.services.major_insight import service

VALID_PRIORITIES = {"HIGH", "MEDIUM", "LOW"}

SAMPLE_CTX: Dict[str, Any] = {
    "major_code": "7480101",
    "name": "Khoa học máy tính",
    "category": "Máy tính & Công nghệ thông tin",
    "description": "",
    "careers": ["Kỹ sư phần mềm", "Kỹ sư dữ liệu"],
    "blocks": ["A00", "A01", "D01"],
}

SAMPLE_SKILL_REQUEST = StudentSkillAnalysisRequest(
    major_code="7480101",
    riasec_scores={"R": 0.8, "I": 0.95, "A": 0.2, "S": 0.3, "E": 0.4, "C": 0.6},
    grades_by_subject={"Toán": 8.5, "Vật lý": 5.0, "Tiếng Anh": 6.0},
    cognitive_preferences={"learning_style": "LEARN_VISUAL_SPATIAL"},
)


@pytest.fixture()
def offline_ai(monkeypatch):
    """Ép service đi nhánh dựng tất định, không gọi mạng."""
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")


@pytest.fixture()
def offline_client(offline_ai):
    from fastapi.testclient import TestClient

    from app.core.database import get_db
    from app.main import app

    async def _override_get_db_none():
        yield None

    app.dependency_overrides[get_db] = _override_get_db_none
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


async def _sqlite_session(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'insight.db').as_posix()}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    return engine, session_factory


# =========================================================================
# 1. AGENT PHÂN TÍCH NGÀNH
# =========================================================================

class TestMajorInsightAgent:
    def test_deterministic_content_has_required_sections(self):
        training, careers, is_ai = service.build_deterministic_major_insight(
            SAMPLE_CTX
        )

        assert len(training.overview) > 40
        assert training.core_knowledge, "Phải có khối kiến thức cốt lõi"
        assert training.practical_skills, "Phải có kỹ năng thực hành"
        assert training.study_duration
        assert len(careers) >= 1
        assert all(c.title for c in careers)
        assert any(c.description for c in careers)
        assert is_ai is False

    def test_deterministic_content_mentions_major_name(self):
        training, _, _ = service.build_deterministic_major_insight(SAMPLE_CTX)
        assert "Khoa học máy tính" in training.overview

    def test_deterministic_content_avoids_duplicate_bullets(self):
        training, _, _ = service.build_deterministic_major_insight(SAMPLE_CTX)
        for section in (
            training.core_knowledge,
            training.practical_skills,
            training.curriculum_highlights,
        ):
            assert len(section) == len(set(section))

    def test_endpoint_returns_offline_insight(self, offline_client):
        res = offline_client.get("/api/v1/major-insights/7480101")
        assert res.status_code == 200
        body = res.json()

        assert body["major_code"] == "7480101"
        assert body["major_name"]
        assert body["is_ai_generated"] is False
        assert body["cached"] is False
        assert body["training_content"]["overview"]
        assert body["career_positions"]
        assert body["subject_blocks"]
        # Nội dung phải là tiếng Việt có dấu, không phải chuỗi rỗng/placeholder
        assert any(ord(ch) > 127 for ch in body["training_content"]["overview"])

    def test_endpoint_unknown_major_does_not_crash(self, offline_client):
        res = offline_client.get("/api/v1/major-insights/9999999")
        assert res.status_code == 200
        body = res.json()
        assert body["major_code"] == "9999999"
        assert body["training_content"]["overview"]

    @pytest.mark.anyio
    async def test_cache_written_once_and_read_many(self, tmp_path, offline_ai):
        engine, session_factory = await _sqlite_session(tmp_path)
        try:
            async with session_factory() as db:
                first = await service.get_or_create_major_insight(db, "7480101")
                second = await service.get_or_create_major_insight(db, "7480101")

                assert first.cached is False
                assert second.cached is True
                assert second.training_content.overview == first.training_content.overview
                assert [c.title for c in second.career_positions] == [
                    c.title for c in first.career_positions
                ]

                refreshed = await service.get_or_create_major_insight(
                    db, "7480101", refresh=True
                )
                assert refreshed.cached is False

                assert await service.delete_major_insight(db, "7480101") is True
                assert await service.delete_major_insight(db, "7480101") is False
        finally:
            await engine.dispose()


# =========================================================================
# 2. AGENT PHÂN TÍCH KỸ NĂNG
# =========================================================================

class TestStudentSkillAgent:
    def test_analysis_returns_strengths_weaknesses_and_gaps(self):
        summary, strengths, weaknesses, gaps = (
            service.build_deterministic_skill_analysis(SAMPLE_SKILL_REQUEST, "Khoa học máy tính")
        )

        assert summary
        assert "Khoa học máy tính" in summary
        assert strengths
        assert weaknesses
        assert gaps
        assert len(strengths) <= 5 and len(weaknesses) <= 5
        for item in strengths + weaknesses:
            assert item.title and item.detail
            assert len(item.detail) <= 220, "Giải thích phải gọn"

    def test_gap_items_are_actionable(self):
        _, _, _, gaps = service.build_deterministic_skill_analysis(
            SAMPLE_SKILL_REQUEST, "Khoa học máy tính"
        )

        for gap in gaps:
            assert gap.skill
            assert gap.why
            assert gap.how_to_improve, "Mỗi kỹ năng phải có cách cải thiện"
            assert gap.priority in VALID_PRIORITIES
        # Kỹ năng ưu tiên cao phải đứng trước
        weights = [{"HIGH": 0, "MEDIUM": 1, "LOW": 2}[g.priority] for g in gaps]
        assert weights == sorted(weights)

    def test_low_grade_becomes_priority_gap(self):
        _, _, _, gaps = service.build_deterministic_skill_analysis(
            SAMPLE_SKILL_REQUEST, "Khoa học máy tính"
        )
        assert any("Vật lý" in gap.skill for gap in gaps)
        assert any("Vật lý" in gap.skill and gap.priority == "HIGH" for gap in gaps)

    def test_profile_hash_is_stable_and_anonymous(self):
        base = StudentSkillAnalysisRequest(
            major_code="7480101",
            riasec_scores={"I": 0.9, "R": 0.7},
            grades_by_subject={"Toán": 8.5, "Ngữ văn": 7.0},
            cognitive_preferences={"learning_style": "LEARN_VISUAL_SPATIAL"},
        )
        reordered = StudentSkillAnalysisRequest(
            major_code="7480101",
            riasec_scores={"R": 0.7, "I": 0.9},
            grades_by_subject={"Ngữ văn": 7.0, "Toán": 8.5},
            cognitive_preferences={"learning_style": "LEARN_VISUAL_SPATIAL"},
        )
        different_grade = base.model_copy(
            update={"grades_by_subject": {"Toán": 6.0, "Ngữ văn": 7.0}}
        )

        hashed = service._profile_hash(base)
        assert hashed == service._profile_hash(reordered)
        assert hashed != service._profile_hash(different_grade)
        assert len(hashed) == 64
        assert "Toán" not in hashed and "7480101" not in hashed

    def test_endpoint_accepts_partial_payload(self, offline_client):
        res = offline_client.post(
            "/api/v1/major-insights/student-skills",
            json={"grades_by_subject": {"Toán": 8.0}},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["summary"]
        assert body["strengths"]
        assert body["skill_gaps"]
        assert len(body["profile_hash"]) == 64
        assert body["cached"] is False

    def test_endpoint_accepts_empty_payload(self, offline_client):
        res = offline_client.post("/api/v1/major-insights/student-skills", json={})
        assert res.status_code == 200
        assert res.json()["summary"]

    @pytest.mark.anyio
    async def test_same_profile_reuses_cached_analysis(self, tmp_path, offline_ai):
        engine, session_factory = await _sqlite_session(tmp_path)
        try:
            async with session_factory() as db:
                first = await service.analyze_student_skills(db, SAMPLE_SKILL_REQUEST, None)
                second = await service.analyze_student_skills(db, SAMPLE_SKILL_REQUEST, None)
                assert first.cached is False
                assert second.cached is True
                assert second.profile_hash == first.profile_hash

                other = SAMPLE_SKILL_REQUEST.model_copy(
                    update={"grades_by_subject": {"Toán": 6.5}}
                )
                third = await service.analyze_student_skills(db, other, None)
                assert third.cached is False
                assert third.profile_hash != first.profile_hash
        finally:
            await engine.dispose()


# =========================================================================
# 3. QUYỀN ADMIN CHO CACHE NỘI DUNG ĐÀO TẠO
# =========================================================================

class TestMajorInsightAdminEndpoints:
    def test_regenerate_requires_admin_token(self, offline_client):
        assert (
            offline_client.post("/api/v1/major-insights/7480101/regenerate").status_code
            == 401
        )
        assert offline_client.delete("/api/v1/major-insights/7480101").status_code == 401

    def test_student_token_is_forbidden(self, offline_client):
        from app.core.security import create_access_token

        token = create_access_token(subject=str(uuid.uuid4()), role="STUDENT")
        res = offline_client.post(
            "/api/v1/major-insights/7480101/regenerate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 403

    def test_admin_can_regenerate_and_delete_cache(self, offline_client):
        from app.core.security import create_access_token

        token = create_access_token(subject=str(uuid.uuid4()), role="ADMIN")
        headers = {"Authorization": f"Bearer {token}"}

        regen = offline_client.post(
            "/api/v1/major-insights/7480101/regenerate", headers=headers
        )
        assert regen.status_code == 200
        assert regen.json()["cached"] is False

        deleted = offline_client.delete(
            "/api/v1/major-insights/7480101", headers=headers
        )
        assert deleted.status_code == 200
        # DB đã bị override thành None nên chưa có bản ghi nào để xoá
        assert deleted.json()["deleted"] is False
        assert deleted.json()["major_code"] == "7480101"
