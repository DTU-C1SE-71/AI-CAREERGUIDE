"""Unit & integration tests for Phase 4 DB Architecture Cleanup (Group A1-A6)."""
import json
import uuid
from datetime import datetime, timezone

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import delete, event, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.db.migrations import VERSIONS, migrate
from app.main import app
from app.models.assessment import (
    AssessmentQuestion,
    AssessmentQuestionSet,
    StudentAssessmentResponse,
    StudentAssessmentSubmission,
)
from app.models.identity import User, UserRole
from app.models.insight import MajorExplanationInsight, MajorInsight, StudentSkillInsight
from app.models.recommender import RecommendationSnapshot
from app.models.roadmap import MajorRoadmap, StudentRoadmapProgress
from app.models.taxonomy import Career, Major, MajorSubjectBlock, SubjectBlock
from app.schemas.insight import AspirationAIAnalysisRequest, StudentSkillAnalysisRequest
from app.services.major_insight import service as insight_service
from app.services.taxonomy.service import purge_old_major_catalog_data


def _full_riasec(val: int = 4) -> dict[str, int]:
    return {f"{d}{i}": (5 if d == "I" else val) for d in "RIASEC" for i in range(1, 6)}


def _create_fk_enabled_engine(db_url: str):
    engine = create_async_engine(db_url)

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fks(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@pytest_asyncio.fixture
async def cleanup_env(tmp_path):
    db_path = tmp_path / "cleanup-suite.db"
    engine = _create_fk_enabled_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    student_id = uuid.uuid4()
    other_id = uuid.uuid4()
    set_id = uuid.uuid4()
    q1_id = uuid.uuid4()
    async with sessions() as db:
        db.add_all([
            User(
                id=student_id,
                email="student-cleanup@example.test",
                full_name="Học sinh Kiểm thử",
                hashed_password=get_password_hash("SyntheticPass123!"),
                role=UserRole.STUDENT,
                is_active=True,
                grade_level="Lớp 12",
            ),
            User(
                id=other_id,
                email="other-cleanup@example.test",
                full_name="Học sinh Khác",
                hashed_password=get_password_hash("SyntheticPass123!"),
                role=UserRole.STUDENT,
                is_active=True,
            ),
            Major(
                major_code="7480101",
                name="Khoa học máy tính",
                category="Máy tính & Công nghệ thông tin",
                riasec_vector={"R": 0.6, "I": 0.9, "A": 0.3, "S": 0.2, "E": 0.4, "C": 0.7},
                cognitive_attributes={"abstract_thinking": "high"},
                industry_outlook="Nhu cầu nhân lực cao",
                is_active=True,
                subject_blocks=[
                    MajorSubjectBlock(
                        subject_block=SubjectBlock(
                            block_code="A00",
                            name="Toán, Vật lý, Hóa học",
                            subjects=["Toán", "Vật lý", "Hóa học"],
                        )
                    )
                ],
                careers=[Career(title="Kỹ sư phần mềm", description="Phát triển hệ thống")],
            ),
            AssessmentQuestionSet(
                id=set_id,
                set_code="RIASEC_COG_V2_10",
                version="2.0",
                title="Bộ câu hỏi chuẩn V2",
                circular_ref="74/2026/TT-BGDĐT",
                config={},
                is_active=True,
            ),
            AssessmentQuestion(
                id=q1_id,
                set_id=set_id,
                code="I1",
                category="RIASEC",
                dimension="I",
                dimension_badge="Nghiên cứu",
                question_text="Thích phân tích dữ liệu",
                order_index=1,
                xp_reward=25,
                is_active=True,
            ),
        ])
        await db.commit()

    async def override_db():
        async with sessions() as db:
            yield db

    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = override_db
    try:
        yield engine, sessions, student_id, other_id, set_id, q1_id
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        await engine.dispose()


def test_orm_metadata_has_exact_26_tables():
    tables = set(Base.metadata.tables.keys())
    assert len(tables) == 26
    for removed in (
        "student_assessments",
        "student_grades",
        "recommendation_histories",
        "ai_runtime_config",
        "ai_config_audit",
    ):
        assert removed not in tables
    for kept_group_b in (
        "skills",
        "skill_prerequisites",
        "major_skills",
        "student_diagnostic_tests",
        "major_roadmaps",
        "student_roadmap_progress",
        "knowledge_embeddings",
        "staging_records",
        "careers",
    ):
        assert kept_group_b in tables


@pytest.mark.asyncio
async def test_submissions_list_and_detail_endpoints_and_snapshot_link(cleanup_env):
    _, sessions, student_id, other_id, _, q1_id = cleanup_env
    student_headers = {"Authorization": f"Bearer {create_access_token(str(student_id), role='STUDENT')}"}
    other_headers = {"Authorization": f"Bearer {create_access_token(str(other_id), role='STUDENT')}"}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Guest bị chặn 401
        assert (await client.get("/api/assessment/submissions")).status_code == 401
        assert (await client.get("/api/assessments/submissions")).status_code == 401

        submit = await client.post(
            "/api/assessment/submit",
            headers=student_headers,
            json={
                "riasec_answers": _full_riasec(2),
                "cognitive_answers": {},
                "grades_by_subject": {"Toán": 8.5, "Vật lý": 8.0, "Hóa học": 7.5},
                "aspiration": {"dream_job": "Kỹ sư AI"},
            },
        )
        assert submit.status_code == 200, submit.text
        sub_id = submit.json()["submission_id"]

        for prefix in ("/api/assessment", "/api/assessments", "/api/v1/assessment", "/api/v1/assessments"):
            listed = await client.get(f"{prefix}/submissions", headers=student_headers)
            assert listed.status_code == 200
            items = listed.json()
            assert len(items) == 1
            assert items[0]["submission_id"] == sub_id
            assert items[0]["set_code"] == "RIASEC_COG_V2_10"
            assert items[0]["version"] == "2.0"
            assert items[0]["grades_by_subject"]["Toán"] == 8.5

            detail = await client.get(f"{prefix}/submissions/{sub_id}", headers=student_headers)
            assert detail.status_code == 200
            body = detail.json()
            assert body["submission_id"] == sub_id
            assert len(body["responses"]) == 1
            assert body["responses"][0]["question_id"] == str(q1_id)
            assert body["responses"][0]["question_code"] == "I1"
            assert body["responses"][0]["likert_value"] == 5

            # Người dùng khác không được đọc hoặc xóa bài của học sinh này
            assert (await client.get(f"{prefix}/submissions/{sub_id}", headers=other_headers)).status_code == 404
            assert (await client.delete(f"{prefix}/submissions/{sub_id}", headers=other_headers)).status_code == 404

    # RecommendationSnapshot đã được pre-warm và gắn submission_id thật
    async with sessions() as db:
        snap = (
            await db.execute(
                select(RecommendationSnapshot).where(RecommendationSnapshot.user_id == student_id)
            )
        ).scalar_one()
        assert snap.submission_id == uuid.UUID(sub_id)

    # Chủ sở hữu xóa submission -> 204, responses bị cascade xóa và snapshot bị vô hiệu hóa
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        deleted = await client.delete(f"/api/assessment/submissions/{sub_id}", headers=student_headers)
        assert deleted.status_code == 204
        listed_after = await client.get("/api/assessment/submissions", headers=student_headers)
        assert listed_after.status_code == 200
        assert listed_after.json() == []
        assert (await client.delete(f"/api/assessment/submissions/{sub_id}", headers=student_headers)).status_code == 404

    async with sessions() as db:
        assert (await db.execute(select(StudentAssessmentResponse))).scalars().all() == []
        assert (await db.execute(select(RecommendationSnapshot).where(RecommendationSnapshot.user_id == student_id))).scalars().all() == []


@pytest.mark.asyncio
async def test_student_skill_insight_supports_all_three_scopes(cleanup_env):
    _, sessions, student_id, _, _, _ = cleanup_env
    async with sessions() as db:
        # 1. GENERAL scope (major_code=None trong DB, response trả major_code="")
        gen_req = StudentSkillAnalysisRequest(
            major_code=None,
            riasec_scores={"R": 0.4, "I": 0.9, "A": 0.3, "S": 0.2, "E": 0.4, "C": 0.6},
            grades_by_subject={"Toán": 8.5, "Vật lý": 6.0},
        )
        gen1 = await insight_service.analyze_student_skills(db, gen_req, student_id)
        gen2 = await insight_service.analyze_student_skills(db, gen_req, student_id)
        assert gen1.cached is False and gen2.cached is True
        assert gen1.major_code == "" and gen2.major_code == ""

        # 2. MAJOR scope (major_code="7480101" hợp lệ qua FK)
        maj_req = gen_req.model_copy(update={"major_code": "7480101"})
        maj1 = await insight_service.analyze_student_skills(db, maj_req, student_id)
        maj2 = await insight_service.analyze_student_skills(db, maj_req, student_id)
        assert maj1.cached is False and maj2.cached is True
        assert maj1.major_code == "7480101"

        # 3. ASPIRATION_AI scope (insight_scope="ASPIRATION_AI", major_code=None)
        asp_req = AspirationAIAnalysisRequest(
            dream_job="Khoa học máy tính",
            riasec_scores={"R": 0.4, "I": 0.9, "A": 0.3, "S": 0.2, "E": 0.4, "C": 0.6},
            grades_by_subject={"Toán": 8.5, "Vật lý": 8.0, "Hóa học": 8.0},
        )
        asp1 = await insight_service.analyze_aspiration_with_ai(db, asp_req, student_id)
        asp2 = await insight_service.analyze_aspiration_with_ai(db, asp_req, student_id)
        assert asp1.cached is False and asp2.cached is True

        rows = (await db.execute(select(StudentSkillInsight))).scalars().all()
        by_scope = {r.insight_scope: r for r in rows}
        assert set(by_scope.keys()) == {"GENERAL", "MAJOR", "ASPIRATION_AI"}
        assert by_scope["GENERAL"].major_code is None
        assert by_scope["ASPIRATION_AI"].major_code is None
        assert by_scope["MAJOR"].major_code == "7480101"


@pytest.mark.asyncio
async def test_purge_old_major_catalog_deletes_explanations_and_preserves_general_insights(cleanup_env):
    _, sessions, student_id, _, _, _ = cleanup_env
    async with sessions() as db:
        db.add_all([
            MajorInsight(
                major_code="7480101",
                major_name="Khoa học máy tính",
                training_content={"overview": "Test"},
                career_positions=[],
                subject_blocks=["A00"],
            ),
            MajorExplanationInsight(
                user_id=student_id,
                profile_hash="a" * 64,
                major_code="7480101",
                major_name="Khoa học máy tính",
                detailed_explanation="Giải thích ngành cũ",
                strengths=[],
                recommended_focus_areas=[],
            ),
            StudentSkillInsight(
                user_id=student_id,
                profile_hash="b" * 64,
                insight_scope="MAJOR",
                major_code="7480101",
                summary="Phân tích theo ngành",
                strengths=[],
                weaknesses=[],
                skill_gaps=[],
            ),
            StudentSkillInsight(
                user_id=student_id,
                profile_hash="c" * 64,
                insight_scope="GENERAL",
                major_code=None,
                summary="Phân tích tổng quát cần giữ lại",
                strengths=[],
                weaknesses=[],
                skill_gaps=[],
            ),
            StudentSkillInsight(
                user_id=student_id,
                profile_hash="d" * 64,
                insight_scope="ASPIRATION_AI",
                major_code=None,
                summary="Phân tích nguyện vọng cần giữ lại",
                strengths=[],
                weaknesses=[],
                skill_gaps=[],
            ),
            MajorRoadmap(
                major_code="7480101",
                title="Lộ trình CNTT",
                version="1.0",
                roadmap_data={},
                is_fallback=False,
            ),
            StudentRoadmapProgress(
                user_id=student_id,
                major_code="7480101",
                current_step=1,
                completed_milestones=[],
            ),
        ])
        await db.commit()

        deleted_count = await purge_old_major_catalog_data(db)
        await db.commit()

        assert deleted_count == 1
        assert (await db.execute(select(Major))).scalars().all() == []
        assert (await db.execute(select(MajorInsight))).scalars().all() == []
        assert (await db.execute(select(MajorExplanationInsight))).scalars().all() == []
        assert (await db.execute(select(MajorRoadmap))).scalars().all() == []
        assert (await db.execute(select(StudentRoadmapProgress))).scalars().all() == []

        remaining_skills = (await db.execute(select(StudentSkillInsight))).scalars().all()
        assert {r.insight_scope for r in remaining_skills} == {"GENERAL", "ASPIRATION_AI"}
        assert all(r.major_code is None for r in remaining_skills)


@pytest.mark.asyncio
async def test_deleting_referenced_question_is_blocked_by_restrict_fk(cleanup_env):
    _, sessions, student_id, _, set_id, q1_id = cleanup_env
    sub_id = uuid.uuid4()
    async with sessions() as db:
        db.add(
            StudentAssessmentSubmission(
                id=sub_id,
                user_id=student_id,
                set_id=set_id,
                riasec_vector={"I": 1.0},
                riasec_raw_scores={"I": 5},
                cognitive_traits={},
                cognitive_answers={},
                raw_answers={"riasec_answers": {"I1": 5}},
                dominant_traits=[],
            )
        )
        await db.flush()
        db.add(
            StudentAssessmentResponse(
                submission_id=sub_id,
                question_id=q1_id,
                question_code="I1",
                likert_value=5,
            )
        )
        await db.commit()

    # Verify ORM ForeignKey declaration is strictly RESTRICT
    q_fk = next(
        fk for fk in StudentAssessmentResponse.__table__.foreign_keys
        if fk.parent.name == "question_id"
    )
    assert q_fk.ondelete == "RESTRICT"

    async with sessions() as db:
        with pytest.raises(IntegrityError):
            await db.execute(delete(AssessmentQuestion).where(AssessmentQuestion.id == q1_id))
            await db.commit()
        await db.rollback()

        # Câu hỏi và câu trả lời lịch sử vẫn còn nguyên vẹn
        q_still_there = await db.get(AssessmentQuestion, q1_id)
        assert q_still_there is not None
        resp_count = len(
            (
                await db.execute(
                    select(StudentAssessmentResponse).where(
                        StudentAssessmentResponse.question_id == q1_id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert resp_count == 1


@pytest.mark.asyncio
async def test_migration_008_backfills_normalizes_and_is_idempotent(tmp_path):
    db_path = tmp_path / "mig008-test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    try:
        # 1. Tạo schema trước 008 (bao gồm 5 bảng Nhóm A, student_skill_insights cũ & bộ V1)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS schema_migrations "
                    "(version VARCHAR(80) PRIMARY KEY, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
                )
            )
            for v in VERSIONS[:7]:
                await conn.execute(text("INSERT INTO schema_migrations(version) VALUES (:v)"), {"v": v})
            await conn.execute(
                text(
                    """
                    CREATE TABLE student_assessments (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        riasec_scores TEXT NOT NULL,
                        cognitive_preferences TEXT NOT NULL,
                        raw_responses TEXT NOT NULL,
                        assessed_at TEXT NOT NULL
                    )
                    """
                )
            )
            await conn.execute(text("CREATE TABLE student_grades (id TEXT PRIMARY KEY)"))
            await conn.execute(text("CREATE TABLE recommendation_histories (id TEXT PRIMARY KEY)"))
            await conn.execute(text("CREATE TABLE ai_runtime_config (id INTEGER PRIMARY KEY)"))
            await conn.execute(text("CREATE TABLE ai_config_audit (id INTEGER PRIMARY KEY)"))

            user_id = str(uuid.uuid4())
            legacy_id = str(uuid.uuid4())
            v1_set_id = str(uuid.uuid4())
            v1_q_id = str(uuid.uuid4())
            now_iso = datetime.now(timezone.utc).isoformat()
            await conn.execute(
                text(
                    "INSERT INTO users (id, email, hashed_password, full_name, role, is_active, created_at, updated_at) "
                    "VALUES (:id, 'mig@example.test', 'h', 'Test', 'STUDENT', 1, :t, :t)"
                ),
                {"id": user_id, "t": now_iso},
            )
            await conn.execute(
                text(
                    "INSERT INTO majors (id, major_code, name, category, degree_level, riasec_vector, cognitive_attributes, industry_outlook, is_active, created_at, updated_at) "
                    "VALUES (:id, '7480101', 'KHMT', 'CNTT', 'Đại học', '{}', '{}', 'ok', 1, :t, :t)"
                ),
                {"id": str(uuid.uuid4()), "t": now_iso},
            )
            await conn.execute(
                text(
                    "INSERT INTO student_assessments (id, user_id, riasec_scores, cognitive_preferences, raw_responses, assessed_at) "
                    "VALUES (:id, :uid, :r, :c, :raw, :t)"
                ),
                {
                    "id": legacy_id,
                    "uid": user_id,
                    "r": json.dumps({"I": 0.9}),
                    "c": json.dumps({"abstract_thinking": "high"}),
                    "raw": json.dumps({"riasec": {"I1": 5}, "cognitive": {"COG_1": "A"}, "grades_by_subject": {"Toán": 9.0}}),
                    "t": now_iso,
                },
            )
            await conn.execute(
                text(
                    "INSERT INTO assessment_question_sets (id, set_code, version, title, circular_ref, config, is_active, created_at, updated_at) "
                    "VALUES (:id, 'RIASEC_COG_V1_8', '1.8', 'V1', '74/2026', '{}', 0, :t, :t)"
                ),
                {"id": v1_set_id, "t": now_iso},
            )
            await conn.execute(
                text(
                    "INSERT INTO assessment_questions (id, set_id, code, category, dimension, dimension_badge, icon_name, question_text, order_index, xp_reward, is_active) "
                    "VALUES (:id, :sid, 'COG_1', 'COGNITIVE', 'learning_style', 'Style', 'Brain', 'Q1', 1, 25, 1)"
                ),
                {"id": v1_q_id, "sid": v1_set_id},
            )
            for idx, (mc, ph) in enumerate([("", "1" * 64), ("ASPIRATION_AI", "2" * 64), ("7480101", "3" * 64), ("9999999", "4" * 64)]):
                await conn.execute(
                    text(
                        "INSERT INTO student_skill_insights (id, profile_hash, insight_scope, major_code, summary, strengths, weaknesses, skill_gaps, is_ai_generated, created_at) "
                        "VALUES (:id, :ph, 'MAJOR', :mc, :s, '[]', '[]', '[]', 0, :t)"
                    ),
                    {"id": str(uuid.uuid4()), "ph": ph, "mc": mc, "s": f"row-{idx}", "t": now_iso},
                )

        # 2. Chạy migrate lần 1 & lần 2 (idempotent)
        applied_1 = await migrate(engine)
        applied_2 = await migrate(engine)
        assert applied_1 == list(VERSIONS)
        assert applied_2 == list(VERSIONS)

        # 3. Kiểm tra kết quả sau migrate
        async with engine.connect() as conn:
            tbls = await conn.run_sync(lambda c: set(inspect(c).get_table_names()))
            for dropped in ("student_assessments", "student_grades", "recommendation_histories", "ai_runtime_config", "ai_config_audit"):
                assert dropped not in tbls

            sub = (await conn.execute(text("SELECT id, raw_answers FROM student_assessment_submissions WHERE id = :id"), {"id": legacy_id})).one()
            raw_ans = json.loads(sub[1]) if isinstance(sub[1], str) else sub[1]
            assert raw_ans["riasec_answers"] == {"I1": 5}
            assert raw_ans["cognitive_answers"] == {"COG_1": "A"}
            assert raw_ans["grades_by_subject"] == {"Toán": 9.0}

            v1_active = (await conn.execute(text("SELECT is_active FROM assessment_questions WHERE id = :id"), {"id": v1_q_id})).scalar_one()
            assert bool(v1_active) is False

            rows = (await conn.execute(text("SELECT profile_hash, insight_scope, major_code FROM student_skill_insights"))).all()
            by_hash = {r[0]: (r[1], r[2]) for r in rows}
            assert by_hash["1" * 64] == ("GENERAL", None)
            assert by_hash["2" * 64] == ("ASPIRATION_AI", None)
            assert by_hash["3" * 64] == ("MAJOR", "7480101")
            assert by_hash["4" * 64] == ("GENERAL", None)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_update_submission_persists_db_detects_changes_and_invalidates_ai_caches(cleanup_env):
    _, sessions, student_id, other_id, _, q1_id = cleanup_env
    student_headers = {"Authorization": f"Bearer {create_access_token(str(student_id), role='STUDENT')}"}
    other_headers = {"Authorization": f"Bearer {create_access_token(str(other_id), role='STUDENT')}"}

    v1_set_id = uuid.uuid4()
    v1_cog_id = uuid.uuid4()
    async with sessions() as db:
        from app.models.assessment import CognitiveQuestionOption

        db.add(
            AssessmentQuestionSet(
                id=v1_set_id,
                set_code="RIASEC_COG_V1_8",
                version="1.8",
                title="Bộ câu hỏi V1",
                circular_ref="74/2026/TT-BGDĐT",
                config={},
                is_active=False,
            )
        )
        await db.flush()
        db.add(
            AssessmentQuestion(
                id=v1_cog_id,
                set_id=v1_set_id,
                code="COG_1",
                category="COGNITIVE",
                dimension="learning_style",
                dimension_badge="Học tập",
                question_text="Cách tiếp cận bài toán",
                order_index=1,
                xp_reward=25,
                is_active=False,
                cognitive_options=[
                    CognitiveQuestionOption(
                        option_key="A",
                        trait_code="LEARN_VISUAL_SPATIAL",
                        title="Trực quan",
                        description="Mô hình",
                        order_index=1,
                    ),
                    CognitiveQuestionOption(
                        option_key="B",
                        trait_code="LEARN_THEORETICAL_ANALYTICAL",
                        title="Phân tích",
                        description="Lý thuyết",
                        order_index=2,
                    ),
                ],
            )
        )
        await db.commit()

    base_payload = {
        "riasec_answers": _full_riasec(2),
        "cognitive_answers": {},
        "grades_by_subject": {"Toán": 8.5, "Vật lý": 8.0, "Hóa học": 7.5},
        "aspiration": {"dream_job": "Kỹ sư AI"},
    }

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        submit = await client.post("/api/assessment/submit", headers=student_headers, json=base_payload)
        assert submit.status_code == 200, submit.text
        sub_id = submit.json()["submission_id"]

        # Seed stale AI insights for this student
        async with sessions() as db:
            db.add_all([
                StudentSkillInsight(
                    user_id=student_id,
                    profile_hash="e" * 64,
                    insight_scope="GENERAL",
                    major_code=None,
                    summary="Stale skill insight",
                    strengths=[],
                    weaknesses=[],
                    skill_gaps=[],
                    is_ai_generated=True,
                ),
                MajorExplanationInsight(
                    user_id=student_id,
                    profile_hash="f" * 64,
                    major_code="7480101",
                    major_name="Khoa học máy tính",
                    detailed_explanation="Stale explanation",
                    strengths=[],
                    recommended_focus_areas=[],
                    is_ai_generated=True,
                ),
            ])
            await db.commit()

        # 1. Guest & other user rejected
        assert (await client.put(f"/api/assessment/submissions/{sub_id}", json=base_payload)).status_code == 401
        assert (await client.put(f"/api/assessment/submissions/{sub_id}", headers=other_headers, json=base_payload)).status_code == 404

        # 2. Unchanged payload -> changed=False, preserves AI insights
        same_res = await client.put(
            f"/api/assessment/submissions/{sub_id}",
            headers=student_headers,
            json=base_payload,
        )
        assert same_res.status_code == 200, same_res.text
        same_body = same_res.json()
        assert same_body["changed"] is False
        assert same_body["ai_cache_invalidated"] is False

        async with sessions() as db:
            assert len((await db.execute(select(StudentSkillInsight).where(StudentSkillInsight.user_id == student_id))).scalars().all()) == 1
            assert len((await db.execute(select(MajorExplanationInsight).where(MajorExplanationInsight.user_id == student_id))).scalars().all()) == 1

        # 3. Changed RIASEC + grades -> updates in-place, clears AI insights, refreshes snapshot
        changed_riasec = {**base_payload["riasec_answers"], "I1": 1, "R1": 5}
        changed_payload = {
            **base_payload,
            "riasec_answers": changed_riasec,
            "grades_by_subject": {"Toán": 9.5, "Vật lý": 9.0, "Hóa học": 8.5},
        }
        upd_res = await client.put(
            f"/api/assessment/submissions/{sub_id}",
            headers=student_headers,
            json=changed_payload,
        )
        assert upd_res.status_code == 200, upd_res.text
        upd_body = upd_res.json()
        assert upd_body["submission_id"] == sub_id
        assert upd_body["changed"] is True
        assert upd_body["ai_cache_invalidated"] is True

        # Still only 1 submission row, with updated grades & RIASEC
        listed = await client.get("/api/assessment/submissions", headers=student_headers)
        assert listed.status_code == 200
        items = listed.json()
        assert len(items) == 1
        assert items[0]["submission_id"] == sub_id
        assert items[0]["grades_by_subject"]["Toán"] == 9.5
        assert items[0]["riasec_answers"]["I1"] == 1
        assert items[0]["riasec_answers"]["R1"] == 5

        async with sessions() as db:
            # Granular response replaced in-place without duplicates
            responses = (
                await db.execute(
                    select(StudentAssessmentResponse).where(
                        StudentAssessmentResponse.submission_id == uuid.UUID(sub_id)
                    )
                )
            ).scalars().all()
            assert len(responses) == 1
            assert responses[0].question_id == q1_id
            assert responses[0].likert_value == 1

            # Old AI caches wiped so AI features regenerate cleanly
            assert (await db.execute(select(StudentSkillInsight).where(StudentSkillInsight.user_id == student_id))).scalars().all() == []
            assert (await db.execute(select(MajorExplanationInsight).where(MajorExplanationInsight.user_id == student_id))).scalars().all() == []

            # RecommendationSnapshot recomputed & linked
            snap = (
                await db.execute(
                    select(RecommendationSnapshot).where(RecommendationSnapshot.user_id == student_id)
                )
            ).scalar_one()
            assert snap.submission_id == uuid.UUID(sub_id)

        # 4. V1 submission edit preserves set_id and updates COG_1 response
        v1_sub_id = uuid.uuid4()
        async with sessions() as db:
            db.add(
                StudentAssessmentSubmission(
                    id=v1_sub_id,
                    user_id=student_id,
                    set_id=v1_set_id,
                    riasec_vector={"I": 0.5},
                    riasec_raw_scores={"I": 15},
                    cognitive_traits={"learning_environment": "structured"},
                    cognitive_answers={"learning_style": "A"},
                    raw_answers={
                        "assessment_version": "v1_8q",
                        "riasec_answers": base_payload["riasec_answers"],
                        "cognitive_answers": {"COG_1": "A"},
                        "grades_by_subject": {"Toán": 8.0, "Vật lý": 8.0, "Hóa học": 8.0},
                    },
                    dominant_traits=[],
                )
            )
            await db.commit()

        v1_upd = await client.put(
            f"/api/assessments/submissions/{v1_sub_id}",
            headers=student_headers,
            json={
                "riasec_answers": base_payload["riasec_answers"],
                "cognitive_answers": {"COG_1": "B"},
                "grades_by_subject": {"Toán": 8.0, "Vật lý": 8.0, "Hóa học": 8.0},
            },
        )
        assert v1_upd.status_code == 200, v1_upd.text
        assert v1_upd.json()["changed"] is True

        async with sessions() as db:
            v1_row = await db.get(StudentAssessmentSubmission, v1_sub_id)
            assert v1_row is not None
            assert v1_row.set_id == v1_set_id
            assert v1_row.cognitive_answers == {"learning_style": "B"}
            v1_resp = (
                await db.execute(
                    select(StudentAssessmentResponse).where(
                        StudentAssessmentResponse.submission_id == v1_sub_id,
                        StudentAssessmentResponse.question_code == "COG_1",
                    )
                )
            ).scalar_one()
            assert v1_resp.option_key == "B"
            assert v1_resp.selected_trait_code == "LEARN_THEORETICAL_ANALYTICAL"
