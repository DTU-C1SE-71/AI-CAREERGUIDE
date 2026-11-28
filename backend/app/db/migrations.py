"""Migration cộng thêm có phiên bản; không chạy tự động trong HTTP startup."""
import json
from typing import Any
from sqlalchemy import inspect, text
from app.core.database import Base
import app.models

VERSIONS = (
    "20261116_001_base",
    "20261116_002_profile_columns",
    "20261116_003_ai_runtime",
    "20261117_004_major_explanation",
    "20261119_005_email_otp",
    "20261123_006_chat_history",
    "20261126_007_recommendation_snapshots",
    "20261128_008_db_architecture_cleanup",
)

_DROPPED_GROUP_A_TABLES = (
    "student_assessments",
    "student_grades",
    "recommendation_histories",
    "ai_runtime_config",
    "ai_config_audit",
)


def _as_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


async def _pg_constraint_exists(conn, table_name: str, constraint_name: str) -> bool:
    row = (
        await conn.execute(
            text(
                """
                SELECT 1
                FROM pg_constraint con
                JOIN pg_class rel ON rel.oid = con.conrelid
                JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
                WHERE nsp.nspname = current_schema()
                  AND rel.relname = :tbl
                  AND con.conname = :conname
                LIMIT 1
                """
            ),
            {"tbl": table_name, "conname": constraint_name},
        )
    ).first()
    return row is not None


async def _pg_fk_exists(conn, table_name: str, column_name: str, ref_table: str) -> bool:
    row = (
        await conn.execute(
            text(
                """
                SELECT 1
                FROM pg_constraint con
                JOIN pg_class rel ON rel.oid = con.conrelid
                JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
                JOIN pg_class ref_rel ON ref_rel.oid = con.confrelid
                JOIN pg_attribute att ON att.attrelid = rel.oid AND att.attnum = ANY(con.conkey)
                WHERE nsp.nspname = current_schema()
                  AND rel.relname = :tbl
                  AND con.contype = 'f'
                  AND att.attname = :col
                  AND ref_rel.relname = :ref_tbl
                LIMIT 1
                """
            ),
            {"tbl": table_name, "col": column_name, "ref_tbl": ref_table},
        )
    ).first()
    return row is not None


async def _apply_008_db_architecture_cleanup(conn) -> None:
    is_pg = conn.dialect.name == "postgresql"
    tables = await conn.run_sync(lambda c: set(inspect(c).get_table_names()))

    # Bước 1: Backfill an toàn từ student_assessments -> student_assessment_submissions
    if "student_assessments" in tables and "student_assessment_submissions" in tables:
        missing_rows = (
            await conn.execute(
                text(
                    """
                    SELECT sa.id, sa.user_id, sa.riasec_scores, sa.cognitive_preferences,
                           sa.raw_responses, sa.assessed_at
                    FROM student_assessments sa
                    WHERE NOT EXISTS (
                        SELECT 1 FROM student_assessment_submissions s WHERE s.id = sa.id
                    )
                    """
                )
            )
        ).mappings().all()

        for row in missing_rows:
            riasec_vec = _as_dict(row["riasec_scores"])
            cog_traits = _as_dict(row["cognitive_preferences"])
            raw_resp = _as_dict(row["raw_responses"])

            riasec_ans = (
                raw_resp["riasec_answers"]
                if "riasec_answers" in raw_resp
                else raw_resp.get("riasec", {})
            )
            cog_ans = (
                raw_resp["cognitive_answers"]
                if "cognitive_answers" in raw_resp
                else raw_resp.get("cognitive", {})
            )
            normalized_raw = dict(raw_resp)
            normalized_raw["riasec_answers"] = riasec_ans if isinstance(riasec_ans, dict) else {}
            normalized_raw["cognitive_answers"] = cog_ans if isinstance(cog_ans, dict) else {}
            normalized_raw["aspiration"] = (
                raw_resp["aspiration"] if isinstance(raw_resp.get("aspiration"), dict) else {}
            )
            normalized_raw["grades_by_subject"] = (
                raw_resp["grades_by_subject"]
                if isinstance(raw_resp.get("grades_by_subject"), dict)
                else {}
            )
            normalized_raw["score_context"] = (
                raw_resp["score_context"]
                if isinstance(raw_resp.get("score_context"), dict)
                else {"kind": "TRANSCRIPT", "scale": 10}
            )

            params = {
                "id": row["id"],
                "user_id": row["user_id"],
                "riasec_vector": json.dumps(riasec_vec, ensure_ascii=False),
                "riasec_raw_scores": "{}",
                "cognitive_traits": json.dumps(cog_traits, ensure_ascii=False),
                "cognitive_answers": "{}",
                "raw_answers": json.dumps(normalized_raw, ensure_ascii=False),
                "dominant_traits": "[]",
                "xp_earned": 0,
                "completion_time_seconds": 360,
                "completed_at": row["assessed_at"],
            }
            if is_pg:
                await conn.execute(
                    text(
                        """
                        INSERT INTO student_assessment_submissions (
                            id, user_id, set_id, riasec_vector, riasec_raw_scores,
                            cognitive_traits, cognitive_answers, raw_answers,
                            dominant_traits, xp_earned, completion_time_seconds, completed_at
                        ) VALUES (
                            :id, :user_id, NULL,
                            CAST(:riasec_vector AS jsonb), CAST(:riasec_raw_scores AS jsonb),
                            CAST(:cognitive_traits AS jsonb), CAST(:cognitive_answers AS jsonb),
                            CAST(:raw_answers AS jsonb), CAST(:dominant_traits AS jsonb),
                            :xp_earned, :completion_time_seconds, :completed_at
                        )
                        ON CONFLICT (id) DO NOTHING
                        """
                    ),
                    params,
                )
            else:
                await conn.execute(
                    text(
                        """
                        INSERT OR IGNORE INTO student_assessment_submissions (
                            id, user_id, set_id, riasec_vector, riasec_raw_scores,
                            cognitive_traits, cognitive_answers, raw_answers,
                            dominant_traits, xp_earned, completion_time_seconds, completed_at
                        ) VALUES (
                            :id, :user_id, NULL,
                            :riasec_vector, :riasec_raw_scores,
                            :cognitive_traits, :cognitive_answers,
                            :raw_answers, :dominant_traits,
                            :xp_earned, :completion_time_seconds, :completed_at
                        )
                        """
                    ),
                    params,
                )

        # Đối soát chặt chẽ trước khi cho phép drop ở cuối migration
        remaining = (
            await conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM student_assessments sa
                    WHERE NOT EXISTS (
                        SELECT 1 FROM student_assessment_submissions s WHERE s.id = sa.id
                    )
                    """
                )
            )
        ).scalar_one()
        if int(remaining or 0) != 0:
            raise RuntimeError(
                f"Backfill đối soát thất bại: còn {remaining} bản ghi student_assessments chưa có trong student_assessment_submissions."
            )

    # Bước 2: Chuẩn hóa student_skill_insights (insight_scope + major_code nullable + unique)
    if "student_skill_insights" in tables:
        ssi_cols = await conn.run_sync(
            lambda c: {col["name"] for col in inspect(c).get_columns("student_skill_insights")}
        )
        if "insight_scope" not in ssi_cols:
            await conn.execute(
                text(
                    "ALTER TABLE student_skill_insights "
                    "ADD COLUMN insight_scope VARCHAR(32) NOT NULL DEFAULT 'MAJOR'"
                )
            )
        if is_pg:
            await conn.execute(
                text("ALTER TABLE student_skill_insights ALTER COLUMN major_code DROP NOT NULL")
            )
            await conn.execute(
                text("ALTER TABLE student_skill_insights ALTER COLUMN major_code DROP DEFAULT")
            )

        await conn.execute(
            text(
                """
                UPDATE student_skill_insights
                SET insight_scope = 'ASPIRATION_AI', major_code = NULL
                WHERE major_code = 'ASPIRATION_AI'
                """
            )
        )
        await conn.execute(
            text(
                """
                UPDATE student_skill_insights
                SET insight_scope = 'GENERAL', major_code = NULL
                WHERE major_code = ''
                   OR (major_code IS NULL AND insight_scope NOT IN ('GENERAL', 'ASPIRATION_AI'))
                """
            )
        )
        if "majors" in tables:
            await conn.execute(
                text(
                    """
                    UPDATE student_skill_insights
                    SET insight_scope = 'GENERAL', major_code = NULL
                    WHERE major_code IS NOT NULL
                      AND NOT EXISTS (
                          SELECT 1 FROM majors m WHERE m.major_code = student_skill_insights.major_code
                      )
                    """
                )
            )

        if is_pg:
            await conn.execute(
                text(
                    "ALTER TABLE student_skill_insights "
                    "DROP CONSTRAINT IF EXISTS uq_student_skill_insight_profile_major"
                )
            )
            await conn.execute(text("DROP INDEX IF EXISTS ix_student_skill_insights_profile_hash"))
            if not await _pg_constraint_exists(
                conn, "student_skill_insights", "uq_student_skill_insight_profile_scope_major"
            ):
                await conn.execute(
                    text(
                        "ALTER TABLE student_skill_insights "
                        "ADD CONSTRAINT uq_student_skill_insight_profile_scope_major "
                        "UNIQUE (profile_hash, insight_scope, major_code)"
                    )
                )
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_student_skill_insight_profile_scope_null_major "
                    "ON student_skill_insights (profile_hash, insight_scope) "
                    "WHERE major_code IS NULL"
                )
            )
        else:
            await conn.execute(text("DROP INDEX IF EXISTS ix_student_skill_insights_profile_hash"))
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_student_skill_insight_profile_scope_null_major "
                    "ON student_skill_insights (profile_hash, insight_scope) "
                    "WHERE major_code IS NULL"
                )
            )

    # Bước 3: Đồng bộ cờ is_active = false cho câu hỏi thuộc bộ câu hỏi đã tắt (giữ nguyên toàn bộ 38 câu V1)
    if "assessment_questions" in tables and "assessment_question_sets" in tables:
        await conn.execute(
            text(
                """
                UPDATE assessment_questions
                SET is_active = FALSE
                WHERE set_id IN (
                    SELECT id FROM assessment_question_sets WHERE is_active = FALSE
                ) AND is_active = TRUE
                """
            )
        )

    # Bước 4: recommendation_snapshots.submission_id + index + FK SET NULL
    if "recommendation_snapshots" in tables:
        rs_cols = await conn.run_sync(
            lambda c: {col["name"] for col in inspect(c).get_columns("recommendation_snapshots")}
        )
        if "submission_id" not in rs_cols:
            col_type = "UUID NULL" if is_pg else "TEXT NULL"
            await conn.execute(
                text(f"ALTER TABLE recommendation_snapshots ADD COLUMN submission_id {col_type}")
            )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_recommendation_snapshots_submission_id "
                "ON recommendation_snapshots (submission_id)"
            )
        )
        if is_pg and "student_assessment_submissions" in tables:
            if not await _pg_fk_exists(
                conn, "recommendation_snapshots", "submission_id", "student_assessment_submissions"
            ):
                await conn.execute(
                    text(
                        "ALTER TABLE recommendation_snapshots "
                        "ADD CONSTRAINT fk_recommendation_snapshots_submission_id "
                        "FOREIGN KEY (submission_id) "
                        "REFERENCES student_assessment_submissions(id) ON DELETE SET NULL"
                    )
                )

    # Bước 5: Bảo vệ lịch sử làm bài — đổi FK student_assessment_responses.question_id -> ON DELETE RESTRICT
    if is_pg and "student_assessment_responses" in tables and "assessment_questions" in tables:
        fk_rows = (
            await conn.execute(
                text(
                    """
                    SELECT con.conname, con.confdeltype
                    FROM pg_constraint con
                    JOIN pg_class rel ON rel.oid = con.conrelid
                    JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
                    JOIN pg_attribute att ON att.attrelid = rel.oid AND att.attnum = ANY(con.conkey)
                    WHERE nsp.nspname = current_schema()
                      AND rel.relname = 'student_assessment_responses'
                      AND con.contype = 'f'
                      AND att.attname = 'question_id'
                    """
                )
            )
        ).all()
        has_restrict_fk = False
        for conname, confdeltype in fk_rows:
            if confdeltype == "r":
                has_restrict_fk = True
            else:
                await conn.execute(
                    text(f'ALTER TABLE student_assessment_responses DROP CONSTRAINT "{conname}"')
                )
        if not has_restrict_fk:
            await conn.execute(
                text(
                    "ALTER TABLE student_assessment_responses "
                    "ADD CONSTRAINT fk_student_assessment_responses_question_id "
                    "FOREIGN KEY (question_id) "
                    "REFERENCES assessment_questions(id) ON DELETE RESTRICT"
                )
            )

    # Bước 6: Bổ sung 8 FK major_code -> majors(major_code) còn thiếu (bao gồm bảng Nhóm B giữ lại)
    if is_pg and "majors" in tables:
        major_code_fks = (
            ("major_insights", "major_code", "fk_major_insights_major_code", "CASCADE"),
            ("major_explanation_insights", "major_code", "fk_major_explanation_insights_major_code", "CASCADE"),
            ("chat_sessions", "major_code", "fk_chat_sessions_major_code", "SET NULL"),
            ("student_skill_insights", "major_code", "fk_student_skill_insights_major_code", "SET NULL"),
            ("staging_records", "major_code", "fk_staging_records_major_code", "SET NULL"),
            ("major_roadmaps", "major_code", "fk_major_roadmaps_major_code", "CASCADE"),
            ("student_roadmap_progress", "major_code", "fk_student_roadmap_progress_major_code", "CASCADE"),
            ("knowledge_embeddings", "major_code", "fk_knowledge_embeddings_major_code", "SET NULL"),
        )
        for tbl, col, conname, on_delete in major_code_fks:
            if tbl in tables and not await _pg_fk_exists(conn, tbl, col, "majors"):
                await conn.execute(
                    text(
                        f'ALTER TABLE "{tbl}" ADD CONSTRAINT "{conname}" '
                        f'FOREIGN KEY ("{col}") REFERENCES majors(major_code) ON DELETE {on_delete}'
                    )
                )

    # Bước 7: Bổ sung 7 composite UNIQUE & 1 CHECK còn thiếu
    if is_pg:
        unique_defs = (
            ("major_subject_blocks", "uq_major_subject_blocks_pair", "major_id, subject_block_id"),
            ("assessment_questions", "uq_assessment_questions_set_code", "set_id, code"),
            ("cognitive_question_options", "uq_cognitive_options_question_key", "question_id, option_key"),
            ("student_assessment_responses", "uq_student_responses_submission_question", "submission_id, question_id"),
            ("major_skills", "uq_major_skills_pair", "major_id, skill_id"),
            ("skill_prerequisites", "uq_skill_prerequisites_pair", "skill_id, prerequisite_skill_id"),
            ("student_roadmap_progress", "uq_student_roadmap_progress_user_major", "user_id, major_code"),
        )
        for tbl, conname, cols in unique_defs:
            if tbl in tables and not await _pg_constraint_exists(conn, tbl, conname):
                await conn.execute(
                    text(f'ALTER TABLE "{tbl}" ADD CONSTRAINT "{conname}" UNIQUE ({cols})')
                )
        if "skill_prerequisites" in tables and not await _pg_constraint_exists(
            conn, "skill_prerequisites", "ck_skill_prerequisites_no_self"
        ):
            await conn.execute(
                text(
                    'ALTER TABLE "skill_prerequisites" '
                    'ADD CONSTRAINT "ck_skill_prerequisites_no_self" '
                    "CHECK (skill_id <> prerequisite_skill_id)"
                )
            )

    # Bước 8: Dọn 3 index thừa & tạo 8 index nóng
    for redundant_idx in (
        "ix_major_explanation_insights_profile_hash",
        "ix_student_skill_insights_profile_hash",
        "ix_recommendation_snapshots_user_id",
    ):
        await conn.execute(text(f"DROP INDEX IF EXISTS {redundant_idx}"))

    hot_indexes = (
        ("chat_sessions", "CREATE INDEX IF NOT EXISTS ix_chat_sessions_major_code ON chat_sessions (major_code)"),
        ("chat_sessions", "CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_updated ON chat_sessions (user_id, updated_at)"),
        ("chat_messages", "CREATE INDEX IF NOT EXISTS ix_chat_messages_session_created ON chat_messages (session_id, created_at)"),
        ("student_assessment_submissions", "CREATE INDEX IF NOT EXISTS ix_submissions_user_completed ON student_assessment_submissions (user_id, completed_at)"),
        ("email_verification_codes", "CREATE INDEX IF NOT EXISTS ix_email_otp_lookup ON email_verification_codes (email, purpose, expires_at)"),
        ("majors", "CREATE INDEX IF NOT EXISTS ix_majors_is_active ON majors (is_active)"),
        ("staging_records", "CREATE INDEX IF NOT EXISTS ix_staging_records_reviewed_by ON staging_records (reviewed_by)"),
        ("student_skill_insights", "CREATE INDEX IF NOT EXISTS ix_student_skill_insights_scope ON student_skill_insights (insight_scope)"),
    )
    for tbl, ddl in hot_indexes:
        if tbl in tables:
            await conn.execute(text(ddl))

    # Bước 9: Đảm bảo default cột majors.category trên PG
    if is_pg and "majors" in tables:
        await conn.execute(text("ALTER TABLE majors ALTER COLUMN category SET DEFAULT 'Khác'"))

    # Bước 10: Drop 5 bảng Nhóm A sau cùng (chỉ sau khi đối soát backfill đã thành công)
    if is_pg:
        await conn.execute(
            text(
                "DROP TABLE IF EXISTS "
                + ", ".join(_DROPPED_GROUP_A_TABLES)
                + " CASCADE"
            )
        )
    else:
        for tbl in _DROPPED_GROUP_A_TABLES:
            await conn.execute(text(f'DROP TABLE IF EXISTS "{tbl}"'))


async def migrate(engine):
    async with engine.begin() as conn:
        if conn.dialect.name == "postgresql":
            await conn.execute(text("SELECT pg_advisory_xact_lock(2026111601)"))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version VARCHAR(80) PRIMARY KEY, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
        )
        applied = set((await conn.execute(text("SELECT version FROM schema_migrations"))).scalars())
        if VERSIONS[0] not in applied:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(
                text("INSERT INTO schema_migrations(version) VALUES (:v) ON CONFLICT (version) DO NOTHING"),
                {"v": VERSIONS[0]},
            )
        if VERSIONS[1] not in applied:
            columns = await conn.run_sync(
                lambda c: {t: {x["name"] for x in inspect(c).get_columns(t)} for t in ("users", "majors")}
            )
            additions = {
                "users": {
                    "gender": "VARCHAR(50)",
                    "grade_level": "VARCHAR(50)",
                    "school_class": "VARCHAR(50)",
                    "school_name": "VARCHAR(255)",
                },
                "majors": {"category": "VARCHAR(100) NOT NULL DEFAULT 'Khác'"},
            }
            for table, fields in additions.items():
                for name, ddl in fields.items():
                    if name not in columns[table]:
                        await conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {ddl}'))
            await conn.execute(
                text("INSERT INTO schema_migrations(version) VALUES (:v) ON CONFLICT (version) DO NOTHING"),
                {"v": VERSIONS[1]},
            )
        if VERSIONS[2] not in applied:
            # Tombstone: ai_runtime_config & ai_config_audit đã bị gỡ ở 20261128_008_db_architecture_cleanup.
            await conn.execute(
                text("INSERT INTO schema_migrations(version) VALUES (:v) ON CONFLICT (version) DO NOTHING"),
                {"v": VERSIONS[2]},
            )
        if VERSIONS[3] not in applied:
            from app.models.insight import MajorExplanationInsight
            await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=[MajorExplanationInsight.__table__]))
            await conn.execute(
                text("INSERT INTO schema_migrations(version) VALUES (:v) ON CONFLICT (version) DO NOTHING"),
                {"v": VERSIONS[3]},
            )
        if VERSIONS[4] not in applied:
            from app.models.identity import EmailVerificationCode
            await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=[EmailVerificationCode.__table__]))
            await conn.execute(
                text("INSERT INTO schema_migrations(version) VALUES (:v) ON CONFLICT (version) DO NOTHING"),
                {"v": VERSIONS[4]},
            )
        if VERSIONS[5] not in applied:
            from app.models.chat import ChatSession, ChatMessage
            await conn.run_sync(
                lambda c: Base.metadata.create_all(c, tables=[ChatSession.__table__, ChatMessage.__table__])
            )
            await conn.execute(
                text("INSERT INTO schema_migrations(version) VALUES (:v) ON CONFLICT (version) DO NOTHING"),
                {"v": VERSIONS[5]},
            )
        if VERSIONS[6] not in applied:
            from app.models.recommender import RecommendationSnapshot
            await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=[RecommendationSnapshot.__table__]))
            await conn.execute(
                text("INSERT INTO schema_migrations(version) VALUES (:v) ON CONFLICT (version) DO NOTHING"),
                {"v": VERSIONS[6]},
            )
        if VERSIONS[7] not in applied:
            await _apply_008_db_architecture_cleanup(conn)
            await conn.execute(
                text("INSERT INTO schema_migrations(version) VALUES (:v) ON CONFLICT (version) DO NOTHING"),
                {"v": VERSIONS[7]},
            )
        return list((await conn.execute(text("SELECT version FROM schema_migrations ORDER BY version"))).scalars())
