-- =============================================================================
-- AI CAREERGUIDE - HỆ THỐNG ĐỊNH HƯỚNG NGHỀ NGHIỆP THÔNG MINH
-- Canonical PostgreSQL 16 + pgvector Schema (27 Tables = 26 ORM + schema_migrations)
-- Synchronized with SQLAlchemy ORM & Migration 20261128_008_db_architecture_cleanup
-- Compliant with:
-- 1. Circular 09/2022/TT-BGDĐT & Circular 74/2026/TT-BGDĐT (MOET Level-IV Taxonomy)
-- 2. Law No. 91/2025/QH15 (Personal Data Protection & AI Consent Tracking)
-- 3. OWASP ASVS Level 2 (Argon2id Identity & RBAC)
-- =============================================================================

-- Required PostgreSQL extension
CREATE EXTENSION IF NOT EXISTS vector;

-- -----------------------------------------------------------------------------
-- 0. ENUM TYPES (4)
-- -----------------------------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE user_role_enum AS ENUM ('STUDENT', 'ADMIN');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE skill_type_enum AS ENUM ('PREREQUISITE', 'TARGET');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE staging_stream_type_enum AS ENUM ('STREAM_A_MOET', 'STREAM_B_ROADMAP');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE staging_status_enum AS ENUM ('PENDING', 'APPROVED', 'REJECTED');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- -----------------------------------------------------------------------------
-- 1. SCHEMA MIGRATION LEDGER (Table 1/27)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(80) PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 2. IDENTITY, CONSENT & OTP VERIFICATION (Tables 2-4/27)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    gender VARCHAR(50),
    grade_level VARCHAR(50),
    school_class VARCHAR(50),
    school_name VARCHAR(255),
    role user_role_enum NOT NULL,
    is_active BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);

CREATE TABLE IF NOT EXISTS user_consents (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_type VARCHAR(100) NOT NULL,
    is_granted BOOLEAN NOT NULL,
    policy_version VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    granted_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_user_consents_user_id ON user_consents (user_id);

CREATE TABLE IF NOT EXISTS email_verification_codes (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    purpose VARCHAR(32) NOT NULL,
    code_hash VARCHAR(128) NOT NULL,
    pending_payload TEXT,
    attempts INTEGER NOT NULL,
    is_used BOOLEAN NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_email_verification_codes_email ON email_verification_codes (email);
CREATE INDEX IF NOT EXISTS ix_email_verification_codes_purpose ON email_verification_codes (purpose);
CREATE INDEX IF NOT EXISTS ix_email_otp_lookup ON email_verification_codes (email, purpose, expires_at);

-- -----------------------------------------------------------------------------
-- 3. MOET TAXONOMY, SUBJECT BLOCKS, CAREERS & SKILLS (Tables 5-11/27)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS majors (
    id UUID PRIMARY KEY,
    major_code VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL DEFAULT 'Khác',
    degree_level VARCHAR(50) NOT NULL,
    riasec_vector JSONB NOT NULL,
    cognitive_attributes JSONB NOT NULL,
    industry_outlook TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_majors_major_code ON majors (major_code);
CREATE INDEX IF NOT EXISTS ix_majors_name ON majors (name);
CREATE INDEX IF NOT EXISTS ix_majors_category ON majors (category);
CREATE INDEX IF NOT EXISTS ix_majors_is_active ON majors (is_active);

CREATE TABLE IF NOT EXISTS subject_blocks (
    id UUID PRIMARY KEY,
    block_code VARCHAR(10) NOT NULL,
    name VARCHAR(100) NOT NULL,
    subjects JSONB NOT NULL,
    national_mean DOUBLE PRECISION NOT NULL,
    national_std DOUBLE PRECISION NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_subject_blocks_block_code ON subject_blocks (block_code);

CREATE TABLE IF NOT EXISTS major_subject_blocks (
    id UUID PRIMARY KEY,
    major_id UUID NOT NULL REFERENCES majors(id) ON DELETE CASCADE,
    subject_block_id UUID NOT NULL REFERENCES subject_blocks(id) ON DELETE CASCADE,
    weight DOUBLE PRECISION NOT NULL,
    CONSTRAINT uq_major_subject_blocks_pair UNIQUE (major_id, subject_block_id)
);

CREATE INDEX IF NOT EXISTS ix_major_subject_blocks_major_id ON major_subject_blocks (major_id);
CREATE INDEX IF NOT EXISTS ix_major_subject_blocks_subject_block_id ON major_subject_blocks (subject_block_id);

CREATE TABLE IF NOT EXISTS careers (
    id UUID PRIMARY KEY,
    major_id UUID NOT NULL REFERENCES majors(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    career_tree_level VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    responsibilities JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_careers_major_id ON careers (major_id);

CREATE TABLE IF NOT EXISTS skills (
    id UUID PRIMARY KEY,
    skill_code VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    skill_type skill_type_enum NOT NULL,
    domain VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_skills_skill_code ON skills (skill_code);

CREATE TABLE IF NOT EXISTS skill_prerequisites (
    id UUID PRIMARY KEY,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    prerequisite_skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    CONSTRAINT uq_skill_prerequisites_pair UNIQUE (skill_id, prerequisite_skill_id),
    CONSTRAINT ck_skill_prerequisites_no_self CHECK (skill_id <> prerequisite_skill_id)
);

CREATE INDEX IF NOT EXISTS ix_skill_prerequisites_skill_id ON skill_prerequisites (skill_id);
CREATE INDEX IF NOT EXISTS ix_skill_prerequisites_prerequisite_skill_id ON skill_prerequisites (prerequisite_skill_id);

CREATE TABLE IF NOT EXISTS major_skills (
    id UUID PRIMARY KEY,
    major_id UUID NOT NULL REFERENCES majors(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    importance_level VARCHAR(50) NOT NULL,
    CONSTRAINT uq_major_skills_pair UNIQUE (major_id, skill_id)
);

CREATE INDEX IF NOT EXISTS ix_major_skills_major_id ON major_skills (major_id);
CREATE INDEX IF NOT EXISTS ix_major_skills_skill_id ON major_skills (skill_id);

-- -----------------------------------------------------------------------------
-- 4. ASSESSMENT QUESTIONNAIRES, SUBMISSIONS & DIAGNOSTICS (Tables 12-17/27)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS assessment_question_sets (
    id UUID PRIMARY KEY,
    set_code VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    circular_ref VARCHAR(100) NOT NULL,
    config JSONB NOT NULL,
    is_active BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_assessment_question_sets_set_code ON assessment_question_sets (set_code);
CREATE INDEX IF NOT EXISTS ix_assessment_question_sets_is_active ON assessment_question_sets (is_active);

CREATE TABLE IF NOT EXISTS assessment_questions (
    id UUID PRIMARY KEY,
    set_id UUID NOT NULL REFERENCES assessment_question_sets(id) ON DELETE CASCADE,
    code VARCHAR(20) NOT NULL,
    category VARCHAR(20) NOT NULL,
    dimension VARCHAR(50) NOT NULL,
    dimension_badge VARCHAR(100) NOT NULL,
    domain_tag VARCHAR(255),
    icon_name VARCHAR(50) NOT NULL,
    question_text TEXT NOT NULL,
    order_index INTEGER NOT NULL,
    xp_reward INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL,
    CONSTRAINT uq_assessment_questions_set_code UNIQUE (set_id, code)
);

CREATE INDEX IF NOT EXISTS ix_assessment_questions_set_id ON assessment_questions (set_id);
CREATE INDEX IF NOT EXISTS ix_assessment_questions_code ON assessment_questions (code);
CREATE INDEX IF NOT EXISTS ix_assessment_questions_category ON assessment_questions (category);
CREATE INDEX IF NOT EXISTS ix_assessment_questions_dimension ON assessment_questions (dimension);
CREATE INDEX IF NOT EXISTS ix_assessment_questions_order_index ON assessment_questions (order_index);

CREATE TABLE IF NOT EXISTS cognitive_question_options (
    id UUID PRIMARY KEY,
    question_id UUID NOT NULL REFERENCES assessment_questions(id) ON DELETE CASCADE,
    option_key VARCHAR(5) NOT NULL,
    trait_code VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    related_moet_field_codes JSONB NOT NULL,
    order_index INTEGER NOT NULL,
    CONSTRAINT uq_cognitive_options_question_key UNIQUE (question_id, option_key)
);

CREATE INDEX IF NOT EXISTS ix_cognitive_question_options_question_id ON cognitive_question_options (question_id);
CREATE INDEX IF NOT EXISTS ix_cognitive_question_options_trait_code ON cognitive_question_options (trait_code);

CREATE TABLE IF NOT EXISTS student_assessment_submissions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    set_id UUID REFERENCES assessment_question_sets(id) ON DELETE SET NULL,
    riasec_vector JSONB NOT NULL,
    riasec_raw_scores JSONB NOT NULL,
    cognitive_traits JSONB NOT NULL,
    cognitive_answers JSONB NOT NULL,
    raw_answers JSONB NOT NULL,
    dominant_traits JSONB NOT NULL,
    xp_earned INTEGER NOT NULL,
    completion_time_seconds INTEGER NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_student_assessment_submissions_user_id ON student_assessment_submissions (user_id);
CREATE INDEX IF NOT EXISTS ix_student_assessment_submissions_set_id ON student_assessment_submissions (set_id);
CREATE INDEX IF NOT EXISTS ix_submissions_user_completed ON student_assessment_submissions (user_id, completed_at);

CREATE TABLE IF NOT EXISTS student_assessment_responses (
    id UUID PRIMARY KEY,
    submission_id UUID NOT NULL REFERENCES student_assessment_submissions(id) ON DELETE CASCADE,
    question_id UUID NOT NULL CONSTRAINT fk_student_assessment_responses_question_id REFERENCES assessment_questions(id) ON DELETE RESTRICT,
    question_code VARCHAR(20) NOT NULL,
    likert_value INTEGER,
    option_key VARCHAR(5),
    selected_trait_code VARCHAR(100),
    answered_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_student_responses_submission_question UNIQUE (submission_id, question_id)
);

CREATE INDEX IF NOT EXISTS ix_student_assessment_responses_submission_id ON student_assessment_responses (submission_id);
CREATE INDEX IF NOT EXISTS ix_student_assessment_responses_question_id ON student_assessment_responses (question_id);
CREATE INDEX IF NOT EXISTS ix_student_assessment_responses_question_code ON student_assessment_responses (question_code);

CREATE TABLE IF NOT EXISTS student_diagnostic_tests (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_code VARCHAR(50) NOT NULL,
    score DOUBLE PRECISION NOT NULL,
    is_passed BOOLEAN NOT NULL,
    details JSONB NOT NULL,
    tested_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_student_diagnostic_tests_user_id ON student_diagnostic_tests (user_id);
CREATE INDEX IF NOT EXISTS ix_student_diagnostic_tests_skill_code ON student_diagnostic_tests (skill_code);

-- -----------------------------------------------------------------------------
-- 5. RECOMMENDATION SNAPSHOT CACHE (Table 18/27)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS recommendation_snapshots (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    submission_id UUID CONSTRAINT fk_recommendation_snapshots_submission_id REFERENCES student_assessment_submissions(id) ON DELETE SET NULL,
    input_hash VARCHAR(64) NOT NULL,
    algorithm_version VARCHAR(40) NOT NULL,
    top_k INTEGER NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_recommendation_snapshot_user_hash UNIQUE (user_id, input_hash)
);

CREATE INDEX IF NOT EXISTS ix_recommendation_snapshots_submission_id ON recommendation_snapshots (submission_id);
CREATE INDEX IF NOT EXISTS ix_recommendation_snapshots_input_hash ON recommendation_snapshots (input_hash);

-- -----------------------------------------------------------------------------
-- 6. AI INSIGHTS & EXPLANATION CACHES (Tables 19-21/27)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS major_insights (
    id UUID PRIMARY KEY,
    major_code VARCHAR(20) NOT NULL CONSTRAINT fk_major_insights_major_code REFERENCES majors(major_code) ON DELETE CASCADE,
    major_name VARCHAR(255) NOT NULL,
    training_content JSONB NOT NULL,
    career_positions JSONB NOT NULL,
    subject_blocks JSONB NOT NULL,
    is_ai_generated BOOLEAN NOT NULL,
    model_name VARCHAR(120),
    generated_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_major_insights_major_code ON major_insights (major_code);

CREATE TABLE IF NOT EXISTS student_skill_insights (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    profile_hash VARCHAR(64) NOT NULL,
    insight_scope VARCHAR(32) NOT NULL DEFAULT 'MAJOR',
    major_code VARCHAR(20) CONSTRAINT fk_student_skill_insights_major_code REFERENCES majors(major_code) ON DELETE SET NULL,
    summary TEXT NOT NULL,
    strengths JSONB NOT NULL,
    weaknesses JSONB NOT NULL,
    skill_gaps JSONB NOT NULL,
    is_ai_generated BOOLEAN NOT NULL,
    model_name VARCHAR(120),
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_student_skill_insight_profile_scope_major UNIQUE (profile_hash, insight_scope, major_code)
);

CREATE INDEX IF NOT EXISTS ix_student_skill_insights_user_id ON student_skill_insights (user_id);
CREATE INDEX IF NOT EXISTS ix_student_skill_insights_major_code ON student_skill_insights (major_code);
CREATE INDEX IF NOT EXISTS ix_student_skill_insights_scope ON student_skill_insights (insight_scope);
CREATE UNIQUE INDEX IF NOT EXISTS uq_student_skill_insight_profile_scope_null_major
    ON student_skill_insights (profile_hash, insight_scope)
    WHERE major_code IS NULL;

CREATE TABLE IF NOT EXISTS major_explanation_insights (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    profile_hash VARCHAR(64) NOT NULL,
    major_code VARCHAR(20) NOT NULL CONSTRAINT fk_major_explanation_insights_major_code REFERENCES majors(major_code) ON DELETE CASCADE,
    major_name VARCHAR(255) NOT NULL,
    detailed_explanation TEXT NOT NULL,
    riasec_alignment TEXT,
    academic_alignment TEXT,
    diagnostic_readiness TEXT,
    strengths JSONB NOT NULL,
    recommended_focus_areas JSONB NOT NULL,
    is_ai_generated BOOLEAN NOT NULL,
    model_name VARCHAR(120),
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_major_explanation_profile_major UNIQUE (profile_hash, major_code)
);

CREATE INDEX IF NOT EXISTS ix_major_explanation_insights_user_id ON major_explanation_insights (user_id);
CREATE INDEX IF NOT EXISTS ix_major_explanation_insights_major_code ON major_explanation_insights (major_code);

-- -----------------------------------------------------------------------------
-- 7. AI COUNSELOR CHAT HISTORY (Tables 22-23/27)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    major_code VARCHAR(20) CONSTRAINT fk_chat_sessions_major_code REFERENCES majors(major_code) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_id ON chat_sessions (user_id);
CREATE INDEX IF NOT EXISTS ix_chat_sessions_major_code ON chat_sessions (major_code);
CREATE INDEX IF NOT EXISTS ix_chat_sessions_updated_at ON chat_sessions (updated_at);
CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_updated ON chat_sessions (user_id, updated_at);

CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    response_source VARCHAR(32),
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_chat_messages_session_id ON chat_messages (session_id);
CREATE INDEX IF NOT EXISTS ix_chat_messages_created_at ON chat_messages (created_at);
CREATE INDEX IF NOT EXISTS ix_chat_messages_session_created ON chat_messages (session_id, created_at);

-- -----------------------------------------------------------------------------
-- 8. STUDY ROADMAPS & PROGRESS (Tables 24-25/27)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS major_roadmaps (
    id UUID PRIMARY KEY,
    major_code VARCHAR(20) NOT NULL CONSTRAINT fk_major_roadmaps_major_code REFERENCES majors(major_code) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    version VARCHAR(20) NOT NULL,
    roadmap_data JSONB NOT NULL,
    is_fallback BOOLEAN NOT NULL,
    fallback_template JSONB,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_major_roadmaps_major_code ON major_roadmaps (major_code);

CREATE TABLE IF NOT EXISTS student_roadmap_progress (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    major_code VARCHAR(20) NOT NULL CONSTRAINT fk_student_roadmap_progress_major_code REFERENCES majors(major_code) ON DELETE CASCADE,
    current_step INTEGER NOT NULL,
    completed_milestones JSONB NOT NULL,
    personalized_schedule JSONB,
    started_at TIMESTAMPTZ NOT NULL,
    last_activity_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_student_roadmap_progress_user_major UNIQUE (user_id, major_code)
);

CREATE INDEX IF NOT EXISTS ix_student_roadmap_progress_user_id ON student_roadmap_progress (user_id);
CREATE INDEX IF NOT EXISTS ix_student_roadmap_progress_major_code ON student_roadmap_progress (major_code);

-- -----------------------------------------------------------------------------
-- 9. HITL STAGING & VECTOR KNOWLEDGE BASE (Tables 26-27/27)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS staging_records (
    id UUID PRIMARY KEY,
    stream_type staging_stream_type_enum NOT NULL,
    status staging_status_enum NOT NULL,
    major_code VARCHAR(20) CONSTRAINT fk_staging_records_major_code REFERENCES majors(major_code) ON DELETE SET NULL,
    content_hash VARCHAR(64) NOT NULL,
    raw_content TEXT,
    extracted_payload JSONB NOT NULL,
    source_title VARCHAR(255) NOT NULL,
    source_url VARCHAR(1000) NOT NULL,
    source_page VARCHAR(50),
    retrieved_at TIMESTAMPTZ NOT NULL,
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_staging_records_status ON staging_records (status);
CREATE INDEX IF NOT EXISTS ix_staging_records_major_code ON staging_records (major_code);
CREATE UNIQUE INDEX IF NOT EXISTS ix_staging_records_content_hash ON staging_records (content_hash);
CREATE INDEX IF NOT EXISTS ix_staging_records_reviewed_by ON staging_records (reviewed_by);

CREATE TABLE IF NOT EXISTS knowledge_embeddings (
    id UUID PRIMARY KEY,
    major_code VARCHAR(20) CONSTRAINT fk_knowledge_embeddings_major_code REFERENCES majors(major_code) ON DELETE SET NULL,
    skill_id UUID REFERENCES skills(id) ON DELETE SET NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    source_title VARCHAR(255),
    source_url VARCHAR(1000),
    source_page VARCHAR(50),
    metadata_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_knowledge_embeddings_major_code ON knowledge_embeddings (major_code);
CREATE INDEX IF NOT EXISTS ix_knowledge_embeddings_skill_id ON knowledge_embeddings (skill_id);
