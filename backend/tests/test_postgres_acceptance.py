"""@blast-radius: db, api, integration — PostgreSQL16 thật, schema dùng một lần."""
import asyncio
import json
import os
import uuid
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text, select, inspect
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_password_hash
from app.db.migrations import migrate, VERSIONS
from app.main import app
from app.models.identity import User, UserRole
from app.services.ai_config.service import resolve_snapshot

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not os.environ.get("AUDIT_TEST_DATABASE_URL"),
        reason="Cần PostgreSQL16 audit loopback qua AUDIT_TEST_DATABASE_URL; không dùng DB người dùng",
    ),
]


@pytest_asyncio.fixture
async def pg_scope(monkeypatch):
    from sqlalchemy.engine import make_url
    url = make_url(os.environ["AUDIT_TEST_DATABASE_URL"])
    assert url.host in {"127.0.0.1", "localhost", "::1"} and url.database == "careerguide_v9_test"
    base = create_async_engine(url)
    schema = "audit_v9_" + uuid.uuid4().hex
    async with base.begin() as conn:
        database, version = (await conn.execute(text("SELECT current_database(),current_setting('server_version_num')"))).one()
        assert database == "careerguide_v9_test" and version.startswith("16")
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(
        url,
        connect_args={"server_settings": {"search_path": f'"{schema}",public'}},
        execution_options={"schema_translate_map": {None: schema}},
    )
    async with engine.connect() as conn:
        assert (await conn.execute(text("SELECT current_schema()"))).scalar() == schema
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def override():
        async with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override
    monkeypatch.setattr(settings, "AI_LOCAL_ALLOWED_BASE_URLS", [])
    try:
        yield engine, sessions, schema
    finally:
        app.dependency_overrides.pop(get_db, None)
        await engine.dispose()
        async with base.begin() as conn:
            assert (await conn.execute(text("SELECT current_database()"))).scalar() == "careerguide_v9_test"
            await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await base.dispose()


async def admin_login(client, sessions):
    async with sessions() as db:
        db.add(User(email="admin-pg@example.com", full_name="Quản trị Tổng Hợp", hashed_password=get_password_hash("synthetic-pg-test-only"), role=UserRole.ADMIN, is_active=True))
        await db.commit()
    response = await client.post("/api/v1/identity/login", json={"email": "admin-pg@example.com", "password": "synthetic-pg-test-only"})
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["access_token"]}


@contextmanager
def provider():
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append({"model": body["model"], "authorization": self.headers.get("Authorization")})
            content = json.dumps([{"major_code": "7480101", "trend_tier": "TIER_1", "trend_reason": "Dữ liệu tổng hợp đã kiểm chứng"}])
            raw = json.dumps({"choices": [{"message": {"content": content}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", seen
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


async def test_migrations_fresh_upgrade_idempotent_preserve_rows(pg_scope):
    engine, sessions, schema = pg_scope
    assert await migrate(engine) == list(VERSIONS)
    async with sessions() as db:
        db.add(User(email="preserved@example.com", full_name="Nguyễn Ánh Việt", hashed_password="synthetic-hash", role=UserRole.STUDENT, is_active=True))
        await db.commit()
    # Mô phỏng schema cũ trong namespace mới, không thay đổi DB gốc.
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE users DROP COLUMN school_name"))
        await conn.execute(text("ALTER TABLE users DROP COLUMN school_class"))
        await conn.execute(text("ALTER TABLE recommendation_snapshots DROP COLUMN submission_id"))
        await conn.execute(text("DELETE FROM schema_migrations WHERE version != :v"), {"v": VERSIONS[0]})
    assert await migrate(engine) == list(VERSIONS)
    assert await migrate(engine) == list(VERSIONS)
    async with sessions() as db:
        user = (await db.execute(select(User))).scalar_one()
        assert user.full_name == "Nguyễn Ánh Việt" and user.school_name is None
        columns = await db.run_sync(lambda s: {c["name"] for c in inspect(s.connection()).get_columns("users", schema=schema)})
        assert {"school_name", "school_class"}.issubset(columns)
        snap_cols = await db.run_sync(lambda s: {c["name"] for c in inspect(s.connection()).get_columns("recommendation_snapshots", schema=schema)})
        assert "submission_id" in snap_cols


async def test_real_auth_env_readonly_and_revoked_role(pg_scope, monkeypatch):
    engine, sessions, _ = pg_scope
    await migrate(engine)
    with provider() as (url, _):
        monkeypatch.setattr(settings, "ENVIRONMENT", "test")
        monkeypatch.setattr(settings, "AI_LOCAL_ALLOWED_BASE_URLS", [url])
        monkeypatch.setattr(settings, "LLM_BASE_URL", url)
        monkeypatch.setattr(settings, "LLM_MODEL", "model-a")
        monkeypatch.setattr(settings, "LLM_API_KEY", "sk-synth-test-only-00001234")
        monkeypatch.setattr(settings, "LLM_AUTH_MODE", "BEARER")
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            headers = await admin_login(client, sessions)
            res = await client.get("/api/v1/admin/ai-config", headers=headers)
            assert res.status_code == 200 and res.headers["cache-control"] == "no-store"
            body = res.json()
            assert body["active"]["source_mode"] == "ENV" and body["active"]["model"] == "model-a"
            assert body["persisted"] is None
            assert "sk-synth-test-only-00001234" not in res.text

            alias = await client.get("/api/v1/rag-governance/llm-status", headers=headers)
            assert alias.status_code == 200 and alias.json()["revision_token"] == body["revision_token"]

            assert (await client.put("/api/v1/admin/ai-config", headers=headers, json={})).status_code in {404, 405}
            assert (await client.post("/api/rag-governance/update-llm-config", headers=headers, json={})).status_code in {404, 405}
            assert (await client.post("/api/rag-governance/test-llm-connection", headers=headers, json={})).status_code in {404, 405}

            async with sessions() as db:
                user = (await db.execute(select(User))).scalar_one()
                user.role = UserRole.STUDENT
                await db.commit()
            denied = await client.get("/api/admin/ai-config", headers=headers)
            assert denied.status_code == 403


async def test_real_trend_consumer_switches_a_to_b_with_task_snapshot(pg_scope, monkeypatch):
    from app.services.taxonomy.trend_agent import _refine_tiers_with_llm
    engine, sessions, _ = pg_scope
    await migrate(engine)
    candidate = {"major_code": "7480101", "major_name": "Khoa học máy tính", "category": "MÁY TÍNH VÀ CÔNG NGHỆ THÔNG TIN", "macro_suggested_tier": "TIER_1", "matched_topics": ["Kỹ thuật"]}
    with provider() as (url_a, seen_a), provider() as (url_b, seen_b):
        monkeypatch.setattr(settings, "ENVIRONMENT", "test")
        monkeypatch.setattr(settings, "AI_LOCAL_ALLOWED_BASE_URLS", [url_a, url_b])
        monkeypatch.setattr(settings, "LLM_AUTH_MODE", "BEARER")
        async with sessions() as db:
            monkeypatch.setattr(settings, "LLM_BASE_URL", url_a)
            monkeypatch.setattr(settings, "LLM_MODEL", "model-a")
            monkeypatch.setattr(settings, "LLM_API_KEY", "sk-synth-test-only-A0001234")
            snapshot_a = await resolve_snapshot(db)
            result = await _refine_tiers_with_llm("dữ liệu tổng hợp", [], [candidate], [candidate["category"]], snapshot=snapshot_a)
            assert "7480101" in result

            monkeypatch.setattr(settings, "LLM_BASE_URL", url_b)
            monkeypatch.setattr(settings, "LLM_MODEL", "model-b")
            monkeypatch.setattr(settings, "LLM_API_KEY", "sk-synth-test-only-B0001234")
            snapshot_b = await resolve_snapshot(db)
            await _refine_tiers_with_llm("dữ liệu tổng hợp", [], [candidate], [candidate["category"]], snapshot=snapshot_b)
            await _refine_tiers_with_llm("retry tác vụ cũ", [], [candidate], [candidate["category"]], snapshot=snapshot_a)
        assert [r["model"] for r in seen_a] == ["model-a", "model-a"]
        assert [r["model"] for r in seen_b] == ["model-b"]
        assert all(r["authorization"] == "Bearer sk-synth-test-only-A0001234" for r in seen_a)
        assert seen_b[0]["authorization"] == "Bearer sk-synth-test-only-B0001234"


async def test_postgres_student_snapshot_ownership_clear_and_vietnamese(pg_scope):
    from app.models.taxonomy import Major
    from app.models.assessment import StudentAssessmentSubmission
    from app.models.recommender import RecommendationSnapshot
    engine, sessions, _ = pg_scope
    await migrate(engine)
    async with sessions() as db:
        db.add(Major(major_code="7480101", name="Khoa học máy tính — Việt Nam", category="CNTT", riasec_vector={g: 0.8 if g == "I" else 0.2 for g in "RIASEC"}, cognitive_attributes={}, industry_outlook="Dữ liệu tổng hợp", is_active=True))
        await db.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        headers = await admin_login(client, sessions)
        other = await client.post("/api/identity/register", json={"email": "student-snapshot@example.com", "password": "synthetic-student-test-only", "full_name": "Trần Minh Ánh", "gender": "Khác", "grade_level": "Lớp 12"})
        assert other.status_code == 201
        login = await client.post("/api/identity/login", json={"email": "student-snapshot@example.com", "password": "synthetic-student-test-only"})
        student = {"Authorization": "Bearer " + login.json()["access_token"]}
        answers = {f"{g}{i}": 5 if g == "I" else 2 for g in "RIASEC" for i in range(1, 6)}
        saved = await client.post("/api/assessments/submit", headers=student, json={"riasec_answers": answers, "cognitive_answers": {}, "grades_by_subject": {"Toán": 8.125, "Vật lí": 8.125, "Hóa học": 8.125}, "aspiration": {"dream_job": "Kỹ sư trí tuệ nhân tạo"}})
        assert saved.status_code == 200, saved.text
        snapshot = saved.json()["submission_id"]

        listed = await client.get("/api/assessment/submissions", headers=student)
        assert listed.status_code == 200 and listed.json()[0]["submission_id"] == snapshot
        detail = await client.get(f"/api/assessment/submissions/{snapshot}", headers=student)
        assert detail.status_code == 200 and detail.json()["submission_id"] == snapshot
        assert (await client.get(f"/api/assessment/submissions/{snapshot}", headers=headers)).status_code == 404

        recommendation = await client.post("/api/recommender/recommend", headers=student, json={"top_k": 3})
        assert recommendation.status_code == 200, recommendation.text

        async with sessions() as db:
            snap = (await db.execute(select(RecommendationSnapshot))).scalar_one()
            assert snap.submission_id == uuid.UUID(snapshot)

        mine = await client.post("/api/recommender/evaluate", headers=student, json={"assessment_id": snapshot})
        assert mine.status_code == 200
        assert mine.json()["majors"][0]["major_name"] == "Khoa học máy tính — Việt Nam"
        for prefix in ("/api", "/api/v1"):
            forbidden = await client.post(prefix + "/recommender/evaluate", headers=headers, json={"assessment_id": snapshot})
            assert forbidden.status_code == 404
        empty = await client.post("/api/recommender/evaluate", headers=student, json={"riasec_answers": {}, "cognitive_answers": {}, "grades_by_subject": {}, "aspiration": {}})
        assert empty.status_code == 422
        async with sessions() as db:
            row = (await db.execute(select(StudentAssessmentSubmission).where(StudentAssessmentSubmission.id == uuid.UUID(snapshot)))).scalar_one()
            assert row.raw_answers["grades_by_subject"]["Toán"] == 8.125
            assert row.raw_answers["aspiration"]["dream_job"] == "Kỹ sư trí tuệ nhân tạo"


async def test_postgres_human_review_race_one_final_decision(pg_scope):
    from app.models.staging import StagingRecord, StagingStatus, StagingStreamType
    engine, sessions, _ = pg_scope
    await migrate(engine)
    record_id = uuid.uuid4()
    async with sessions() as db:
        db.add(StagingRecord(id=record_id, stream_type=StagingStreamType.STREAM_A_MOET, status=StagingStatus.PENDING, content_hash="synthetic-hash-" + record_id.hex, raw_content="Dữ liệu tổng hợp cần rà soát", extracted_payload={}, source_title="Nguồn tổng hợp", source_url="https://example.com"))
        await db.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        headers = await admin_login(client, sessions)
        responses = await asyncio.gather(*(client.post(f"/api/rag-governance/staging/{record_id}/review", headers=headers, json={"status": "REJECTED", "review_notes": f"Quyết định {index}"}) for index in range(2)))
        assert sorted(r.status_code for r in responses) == [200, 409]
    async with sessions() as db:
        row = (await db.execute(select(StagingRecord).where(StagingRecord.id == record_id))).scalar_one()
        assert row.status == StagingStatus.REJECTED and row.reviewed_by


async def test_postgres_roadmap_double_submit_is_one_record_and_clear_is_empty(pg_scope):
    from app.models.taxonomy import Major
    from app.models.roadmap import StudentRoadmapProgress
    engine, sessions, _ = pg_scope
    await migrate(engine)
    async with sessions() as db:
        db.add(Major(major_code="7480101", name="Khoa học máy tính", category="CNTT", riasec_vector={g: 0.5 for g in "RIASEC"}, cognitive_attributes={}, industry_outlook="Tổng hợp", is_active=True))
        await db.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        headers = await admin_login(client, sessions)
        body = {"major_code": "7480101", "current_step": 1, "completed_milestones": [1], "personalized_schedule": {"completed_tasks": ["week-1-task-0"]}}
        responses = await asyncio.gather(*(client.post("/api/roadmap/progress", headers=headers, json=body) for _ in range(2)))
        assert all(r.status_code == 200 for r in responses)
        async with sessions() as db:
            rows = list((await db.execute(select(StudentRoadmapProgress))).scalars())
            assert len(rows) == 1
        clear = await client.post("/api/roadmap/progress", headers=headers, json={**body, "completed_milestones": [], "personalized_schedule": {}})
        assert clear.status_code == 200 and clear.json()["personalized_schedule"] == {}
