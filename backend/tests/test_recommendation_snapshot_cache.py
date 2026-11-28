"""Tests for RecommendationSnapshot DB caching, invalidation, and assessment submission pre-warming."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.database import Base
from app.core.security import get_password_hash
from app.models.identity import User, UserRole
from app.models.recommender import RecommendationSnapshot
from app.models.taxonomy import Career, Major, MajorSubjectBlock, SubjectBlock
from app.modules.assessment.schemas import AssessmentSubmissionRequest
from app.modules.assessment.service import process_assessment_submission
from app.schemas.identity import UserProfileUpdateRequest
from app.services.identity.service import update_user_profile
from app.services.recommender import service as rec_service


def _full_riasec(default_val: int = 4) -> dict[str, int]:
    return {
        f"{dim}{idx}": default_val
        for dim in "RIASEC"
        for idx in range(1, 6)
    }


def _full_cognitive(choice: str = "A") -> dict[str, str]:
    return {f"COG_{i}": choice for i in range(1, 9)}


async def _seed_user_and_catalog(session_factory):
    user_id = uuid.uuid4()
    async with session_factory() as db:
        user = User(
            id=user_id,
            email=f"cache-student-{user_id.hex[:8]}@example.com",
            full_name="Nguyễn Văn A",
            hashed_password=get_password_hash("StrongPass@2026"),
            role=UserRole.STUDENT,
            is_active=True,
            gender="Nam",
            grade_level="Lớp 11",
        )
        block_a00 = SubjectBlock(
            block_code="A00",
            name="Toán, Vật lý, Hóa học",
            subjects=["Toán", "Vật lý", "Hóa học"],
        )
        block_d01 = SubjectBlock(
            block_code="D01",
            name="Toán, Ngữ văn, Tiếng Anh",
            subjects=["Toán", "Ngữ văn", "Tiếng Anh"],
        )
        major_cs = Major(
            major_code="7480101",
            name="Khoa học máy tính",
            category="Máy tính & Công nghệ thông tin",
            riasec_vector={"R": 0.6, "I": 0.9, "A": 0.3, "S": 0.2, "E": 0.4, "C": 0.7},
            cognitive_attributes={"abstract_thinking": "high", "analytical_reasoning": "high"},
            industry_outlook="Nhu cầu nhân lực cao",
            is_active=True,
            subject_blocks=[MajorSubjectBlock(subject_block=block_a00)],
            careers=[Career(title="Kỹ sư phần mềm", description="Phát triển phần mềm và hệ thống")],
        )
        major_biz = Major(
            major_code="7340101",
            name="Quản trị kinh doanh",
            category="Kinh doanh và quản lý",
            riasec_vector={"R": 0.2, "I": 0.5, "A": 0.4, "S": 0.7, "E": 0.9, "C": 0.7},
            cognitive_attributes={"learning_environment": "collaborative", "teamwork_intensity": "highly_collaborative"},
            industry_outlook="Phát triển ổn định",
            is_active=True,
            subject_blocks=[MajorSubjectBlock(subject_block=block_d01)],
            careers=[Career(title="Chuyên viên quản trị", description="Quản trị vận hành doanh nghiệp")],
        )
        db.add_all([user, block_a00, block_d01, major_cs, major_biz])
        await db.commit()
    return user_id


@pytest.mark.asyncio
async def test_recommendation_snapshot_cache_hit_and_miss_rules(tmp_path, monkeypatch):
    db_path = tmp_path / "rec-cache-hit-miss.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    sessions = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    user_id = await _seed_user_and_catalog(sessions)

    spy_calls = {"count": 0}
    real_calc = rec_service.calculate_3pillar_recommendations

    async def tracked_calc(*args, **kwargs):
        spy_calls["count"] += 1
        return await real_calc(*args, **kwargs)

    monkeypatch.setattr(rec_service, "calculate_3pillar_recommendations", tracked_calc)

    base_profile = {
        "riasec_answers": {**_full_riasec(2), "I1": 5, "I2": 5, "I3": 5, "I4": 5, "I5": 5},
        "cognitive_answers": _full_cognitive("A"),
        "grades_by_subject": {"Toán": 8.5, "Vật lý": 8.0, "Hóa học": 7.5},
        "aspiration": {"dream_job": "", "desired_field": "", "work_values": [], "preferred_environment": "", "score_strategy": "FLEXIBLE_PATHWAY"},
        "score_context": {"kind": "TRANSCRIPT", "scale": 10},
    }

    async with sessions() as db:
        # 1. First evaluation computes and writes snapshot
        first = await rec_service.evaluate_dashboard_profile_bundle(
            db=db,
            user_id=user_id,
            top_k=435,
            inline_profile=dict(base_profile),
            raise_if_unassessed=True,
            user_name="Nguyễn Văn A",
            gender="Nam",
            grade_level="Lớp 11",
        )
        assert first["from_cache"] is False
        assert spy_calls["count"] == 1

        # Second identical call hits DB cache without recomputing
        second = await rec_service.evaluate_dashboard_profile_bundle(
            db=db,
            user_id=user_id,
            top_k=435,
            inline_profile=dict(base_profile),
            raise_if_unassessed=True,
            user_name="Nguyễn Văn A",
            gender="Nam",
            grade_level="Lớp 11",
        )
        assert second["from_cache"] is True
        assert spy_calls["count"] == 1

        # 2. Non-scoring profile edits (user_name, gender) still hit DB cache
        non_scoring = await rec_service.evaluate_dashboard_profile_bundle(
            db=db,
            user_id=user_id,
            top_k=435,
            inline_profile=dict(base_profile),
            raise_if_unassessed=True,
            user_name="Nguyễn Tên Mới",
            gender="Nữ",
            grade_level="Lớp 11",
        )
        assert non_scoring["from_cache"] is True
        assert non_scoring["user_name"] == "Nguyễn Tên Mới"
        assert spy_calls["count"] == 1

        # 3. Changing scoring-relevant profile grade_level misses cache and recomputes
        grade_changed = await rec_service.evaluate_dashboard_profile_bundle(
            db=db,
            user_id=user_id,
            top_k=435,
            inline_profile=dict(base_profile),
            raise_if_unassessed=True,
            user_name="Nguyễn Tên Mới",
            gender="Nữ",
            grade_level="Lớp 12",
        )
        assert grade_changed["from_cache"] is False
        assert grade_changed["grade_level"] == "Lớp 12"
        assert spy_calls["count"] == 2

        # 4. Changing assessment scores / answers / aspiration misses cache and recomputes
        edited_scores_profile = {
            **base_profile,
            "grades_by_subject": {"Toán": 9.5, "Vật lý": 9.0, "Hóa học": 9.0},
        }
        score_changed = await rec_service.evaluate_dashboard_profile_bundle(
            db=db,
            user_id=user_id,
            top_k=435,
            inline_profile=edited_scores_profile,
            raise_if_unassessed=True,
            user_name="Nguyễn Tên Mới",
            grade_level="Lớp 12",
        )
        assert score_changed["from_cache"] is False
        assert spy_calls["count"] == 3

        # 5. Updating active Major catalog (updated_at / is_active) invalidates fingerprint
        major_row = (
            await db.execute(select(Major).where(Major.major_code == "7480101"))
        ).scalar_one()
        major_row.updated_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        await db.commit()

        after_catalog_update = await rec_service.evaluate_dashboard_profile_bundle(
            db=db,
            user_id=user_id,
            top_k=435,
            inline_profile=edited_scores_profile,
            raise_if_unassessed=True,
            user_name="Nguyễn Tên Mới",
            grade_level="Lớp 12",
        )
        assert after_catalog_update["from_cache"] is False
        assert spy_calls["count"] == 4

    await engine.dispose()


@pytest.mark.asyncio
async def test_profile_update_invalidation_and_submit_prewarm(tmp_path, monkeypatch):
    db_path = tmp_path / "rec-cache-submit.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    sessions = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    user_id = await _seed_user_and_catalog(sessions)

    spy_calls = {"count": 0}
    real_calc = rec_service.calculate_3pillar_recommendations

    async def tracked_calc(*args, **kwargs):
        spy_calls["count"] += 1
        return await real_calc(*args, **kwargs)

    monkeypatch.setattr(rec_service, "calculate_3pillar_recommendations", tracked_calc)

    async with sessions() as db:
        # 7. Submitting an assessment pre-warms RecommendationSnapshot in DB
        submission_payload = AssessmentSubmissionRequest(
            riasec_answers={**_full_riasec(2), "I1": 5, "I2": 5, "I3": 5, "I4": 5, "I5": 5},
            cognitive_answers=_full_cognitive("A"),
            grades_by_subject={"Toán": 8.5, "Vật lý": 8.5, "Hóa học": 8.5},
            aspiration={"score_strategy": "FLEXIBLE_PATHWAY"},
            score_context={"kind": "TRANSCRIPT", "scale": 10},
        )
        await process_assessment_submission(db, user_id, submission_payload, persist_to_db=True)
        assert spy_calls["count"] == 1

        snaps = (
            await db.execute(select(RecommendationSnapshot).where(RecommendationSnapshot.user_id == user_id))
        ).scalars().all()
        assert len(snaps) == 1

        # Subsequent Dashboard evaluation (even with extra '2-0..2-7' cognitive alias keys) hits DB cache!
        cog_with_aliases = {**_full_cognitive("A"), **{f"2-{i}": "A" for i in range(8)}}
        dashboard_bundle = await rec_service.evaluate_dashboard_profile_bundle(
            db=db,
            user_id=user_id,
            top_k=435,
            inline_profile={
                "riasec_answers": submission_payload.riasec_answers,
                "cognitive_answers": cog_with_aliases,
                "grades_by_subject": submission_payload.grades_by_subject,
                "aspiration": submission_payload.aspiration,
                "score_context": submission_payload.score_context,
            },
            raise_if_unassessed=True,
            user_name="Nguyễn Văn A",
            grade_level="Lớp 11",
        )
        assert dashboard_bundle["from_cache"] is True
        assert spy_calls["count"] == 1

        # 6a. Updating non-scoring profile fields preserves RecommendationSnapshot
        await update_user_profile(
            db,
            user_id,
            UserProfileUpdateRequest(
                full_name="Nguyễn Văn B",
                gender="Nữ",
                school_name="THPT Lê Quý Đôn",
                school_class="11A1",
            ),
        )
        snaps_after_non_scoring = (
            await db.execute(select(RecommendationSnapshot).where(RecommendationSnapshot.user_id == user_id))
        ).scalars().all()
        assert len(snaps_after_non_scoring) == 1

        # 6b. Updating grade_level invalidates RecommendationSnapshot
        await update_user_profile(
            db,
            user_id,
            UserProfileUpdateRequest(grade_level="Lớp 12"),
        )
        snaps_after_grade_change = (
            await db.execute(select(RecommendationSnapshot).where(RecommendationSnapshot.user_id == user_id))
        ).scalars().all()
        assert len(snaps_after_grade_change) == 0

    await engine.dispose()
