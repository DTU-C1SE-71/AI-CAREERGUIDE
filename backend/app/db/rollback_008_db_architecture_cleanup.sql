-- =============================================================================
-- ROLLBACK SCRIPT FOR MIGRATION: 20261128_008_db_architecture_cleanup
-- Target: PostgreSQL 16 (careerguide1_dev)
-- =============================================================================
-- LƯU Ý KHÔI PHỤC ĐẦY ĐỦ DỮ LIỆU:
--   Script này hạ cấp sạch cấu trúc schema 27 -> 32 bảng và tái tạo dữ liệu
--   `student_assessments` từ `student_assessment_submissions`.
--   Các dòng lịch sử cũ của `ai_runtime_config` (1 dòng) và `ai_config_audit`
--   (21 dòng) chỉ khôi phục nguyên trạng đầy đủ từ bản sao lưu vật lý Phase 3:
--     backups/db_before_cleanup_*.sql
--   Ví dụ khôi phục toàn bộ DB từ bản backup:
--     psql -U postgres -d careerguide1_dev -f backups/db_before_cleanup_<timestamp>.sql
-- =============================================================================

BEGIN;

-- 1. Tái tạo 5 bảng Nhóm A đã xóa ở Bước 10
CREATE TABLE IF NOT EXISTS student_assessments (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    riasec_scores JSONB NOT NULL,
    cognitive_preferences JSONB NOT NULL,
    raw_responses JSONB NOT NULL,
    assessed_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_student_assessments_user_id ON student_assessments (user_id);

CREATE TABLE IF NOT EXISTS student_grades (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    grades_by_subject JSONB NOT NULL,
    multi_semester_data JSONB NOT NULL,
    computed_block_zscores JSONB NOT NULL,
    academic_year VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_student_grades_user_id ON student_grades (user_id);

CREATE TABLE IF NOT EXISTS recommendation_histories (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    weights_applied JSONB NOT NULL,
    ranked_results JSONB NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_recommendation_histories_user_id ON recommendation_histories (user_id);

CREATE TABLE IF NOT EXISTS ai_runtime_config (
    id INTEGER PRIMARY KEY,
    version INTEGER NOT NULL,
    profile JSONB NOT NULL,
    credential_state VARCHAR(16) NOT NULL,
    secret_ciphertext TEXT,
    secret_fingerprint VARCHAR(64),
    encryption_key_id VARCHAR(64),
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_ai_runtime_singleton CHECK (id = 1)
);

CREATE TABLE IF NOT EXISTS ai_config_audit (
    id SERIAL PRIMARY KEY,
    actor_id VARCHAR(64) NOT NULL,
    action VARCHAR(32) NOT NULL,
    revision_token VARCHAR(64) NOT NULL,
    summary JSON NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ai_config_audit_actor_id ON ai_config_audit (actor_id);
CREATE INDEX IF NOT EXISTS ix_ai_config_audit_created_at ON ai_config_audit (created_at);

-- 2. Khôi phục dữ liệu student_assessments từ student_assessment_submissions
INSERT INTO student_assessments (
    id, user_id, riasec_scores, cognitive_preferences, raw_responses, assessed_at
)
SELECT
    s.id,
    s.user_id,
    s.riasec_vector,
    s.cognitive_traits,
    jsonb_build_object(
        'riasec', COALESCE(s.raw_answers->'riasec_answers', s.raw_answers->'riasec', '{}'::jsonb),
        'cognitive', COALESCE(s.raw_answers->'cognitive_answers', s.raw_answers->'cognitive', '{}'::jsonb),
        'aspiration', COALESCE(s.raw_answers->'aspiration', '{}'::jsonb),
        'grades_by_subject', COALESCE(s.raw_answers->'grades_by_subject', '{}'::jsonb),
        'score_context', COALESCE(s.raw_answers->'score_context', '{"kind":"TRANSCRIPT","scale":10}'::jsonb)
    ),
    s.completed_at
FROM student_assessment_submissions s
WHERE NOT EXISTS (
    SELECT 1 FROM student_assessments sa WHERE sa.id = s.id
);

-- 3. Hoàn tác Bước 9 (default majors.category)
ALTER TABLE majors ALTER COLUMN category DROP DEFAULT;

-- 4. Hoàn tác Bước 8 (gỡ 8 index nóng & tái tạo 3 index cũ)
DROP INDEX IF EXISTS ix_chat_sessions_major_code;
DROP INDEX IF EXISTS ix_chat_sessions_user_updated;
DROP INDEX IF EXISTS ix_chat_messages_session_created;
DROP INDEX IF EXISTS ix_submissions_user_completed;
DROP INDEX IF EXISTS ix_email_otp_lookup;
DROP INDEX IF EXISTS ix_majors_is_active;
DROP INDEX IF EXISTS ix_staging_records_reviewed_by;
DROP INDEX IF EXISTS ix_student_skill_insights_scope;

CREATE INDEX IF NOT EXISTS ix_major_explanation_insights_profile_hash ON major_explanation_insights (profile_hash);
CREATE INDEX IF NOT EXISTS ix_student_skill_insights_profile_hash ON student_skill_insights (profile_hash);
CREATE INDEX IF NOT EXISTS ix_recommendation_snapshots_user_id ON recommendation_snapshots (user_id);

-- 5. Hoàn tác Bước 7 (7 composite UNIQUE & 1 CHECK)
ALTER TABLE major_subject_blocks DROP CONSTRAINT IF EXISTS uq_major_subject_blocks_pair;
ALTER TABLE assessment_questions DROP CONSTRAINT IF EXISTS uq_assessment_questions_set_code;
ALTER TABLE cognitive_question_options DROP CONSTRAINT IF EXISTS uq_cognitive_options_question_key;
ALTER TABLE student_assessment_responses DROP CONSTRAINT IF EXISTS uq_student_responses_submission_question;
ALTER TABLE major_skills DROP CONSTRAINT IF EXISTS uq_major_skills_pair;
ALTER TABLE skill_prerequisites DROP CONSTRAINT IF EXISTS uq_skill_prerequisites_pair;
ALTER TABLE skill_prerequisites DROP CONSTRAINT IF EXISTS ck_skill_prerequisites_no_self;
ALTER TABLE student_roadmap_progress DROP CONSTRAINT IF EXISTS uq_student_roadmap_progress_user_major;

-- 6. Hoàn tác Bước 6 (8 FK major_code -> majors)
ALTER TABLE major_insights DROP CONSTRAINT IF EXISTS fk_major_insights_major_code;
ALTER TABLE major_explanation_insights DROP CONSTRAINT IF EXISTS fk_major_explanation_insights_major_code;
ALTER TABLE chat_sessions DROP CONSTRAINT IF EXISTS fk_chat_sessions_major_code;
ALTER TABLE student_skill_insights DROP CONSTRAINT IF EXISTS fk_student_skill_insights_major_code;
ALTER TABLE staging_records DROP CONSTRAINT IF EXISTS fk_staging_records_major_code;
ALTER TABLE major_roadmaps DROP CONSTRAINT IF EXISTS fk_major_roadmaps_major_code;
ALTER TABLE student_roadmap_progress DROP CONSTRAINT IF EXISTS fk_student_roadmap_progress_major_code;
ALTER TABLE knowledge_embeddings DROP CONSTRAINT IF EXISTS fk_knowledge_embeddings_major_code;

-- 7. Hoàn tác Bước 5 (FK student_assessment_responses.question_id -> ON DELETE CASCADE)
ALTER TABLE student_assessment_responses DROP CONSTRAINT IF EXISTS fk_student_assessment_responses_question_id;
ALTER TABLE student_assessment_responses
    ADD CONSTRAINT student_assessment_responses_question_id_fkey
    FOREIGN KEY (question_id) REFERENCES assessment_questions(id) ON DELETE CASCADE;

-- 8. Hoàn tác Bước 4 (recommendation_snapshots.submission_id)
ALTER TABLE recommendation_snapshots DROP CONSTRAINT IF EXISTS fk_recommendation_snapshots_submission_id;
DROP INDEX IF EXISTS ix_recommendation_snapshots_submission_id;
ALTER TABLE recommendation_snapshots DROP COLUMN IF EXISTS submission_id;

-- 9. Hoàn tác Bước 3 (khôi phục is_active = TRUE cho câu hỏi thuộc bộ cũ nếu cần)
UPDATE assessment_questions
SET is_active = TRUE
WHERE set_id IN (SELECT id FROM assessment_question_sets WHERE is_active = FALSE);

-- 10. Hoàn tác Bước 2 (student_skill_insights)
DROP INDEX IF EXISTS uq_student_skill_insight_profile_scope_null_major;
ALTER TABLE student_skill_insights DROP CONSTRAINT IF EXISTS uq_student_skill_insight_profile_scope_major;

UPDATE student_skill_insights
SET major_code = 'ASPIRATION_AI'
WHERE insight_scope = 'ASPIRATION_AI' AND major_code IS NULL;

UPDATE student_skill_insights
SET major_code = ''
WHERE major_code IS NULL;

ALTER TABLE student_skill_insights ALTER COLUMN major_code SET NOT NULL;
ALTER TABLE student_skill_insights DROP COLUMN IF EXISTS insight_scope;
ALTER TABLE student_skill_insights
    ADD CONSTRAINT uq_student_skill_insight_profile_major UNIQUE (profile_hash, major_code);

-- 11. Xóa dấu vết version 008 khỏi schema_migrations
DELETE FROM schema_migrations WHERE version = '20261128_008_db_architecture_cleanup';

COMMIT;
