-- =============================================================================
-- AI CAREERGUIDE - HỆ THỐNG ĐỊNH HƯỚNG NGHỀ NGHIỆP THÔNG MINH
-- Database Schema Definition (PostgreSQL 16 + pgvector)
-- Compliant with:
-- 1. Circular 09/2022/TT-BGDĐT (Danh mục giáo dục đào tạo cấp IV)
-- 2. Circular 74/2026/TT-BGDĐT (Định chuẩn đánh giá năng lực & khảo sát nghề)
-- 3. Law No. 91/2025/QH15 (Bảo vệ dữ liệu cá nhân & đồng thuận xử lý AI)
-- 4. OWASP ASVS Level 2 (Bảo mật định danh & mã hóa Argon2id)
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- -----------------------------------------------------------------------------
-- 0. ENUM TYPES
-- -----------------------------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE user_role_enum AS ENUM ('STUDENT', 'ADMIN');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE skill_type_enum AS ENUM ('PREREQUISITE', 'TARGET');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE staging_stream_type_enum AS ENUM ('STREAM_A_MOET', 'STREAM_B_ROADMAP');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE staging_status_enum AS ENUM ('PENDING', 'APPROVED', 'REJECTED');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- -----------------------------------------------------------------------------
-- 1. PHÂN HỆ ĐỊNH DANH & BẢO MẬT DỮ LIỆU CÁ NHÂN (IDENTITY & PRIVACY)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role user_role_enum NOT NULL DEFAULT 'STUDENT',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

CREATE TABLE IF NOT EXISTS user_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_type VARCHAR(100) NOT NULL,
    policy_version VARCHAR(50) NOT NULL DEFAULT 'v1.0-Law91/2025/QH15',
    is_granted BOOLEAN NOT NULL DEFAULT TRUE,
    ip_address VARCHAR(45),
    user_agent TEXT,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_user_consents_user_id ON user_consents(user_id);
CREATE INDEX IF NOT EXISTS idx_user_consents_type ON user_consents(consent_type);

-- -----------------------------------------------------------------------------
-- 2. PHÂN HỆ DANH MỤC GIÁO DỤC CẤP IV & NGHỀ NGHIỆP (MOET TT09 & CAREERS)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS majors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    major_code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL DEFAULT 'Khác',
    degree_level VARCHAR(50) NOT NULL DEFAULT 'Đại học',
    riasec_vector JSONB NOT NULL,
    cognitive_attributes JSONB NOT NULL,
    industry_outlook TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_majors_code ON majors(major_code);
CREATE INDEX IF NOT EXISTS idx_majors_category ON majors(category);
CREATE INDEX IF NOT EXISTS idx_majors_name ON majors(name);
CREATE INDEX IF NOT EXISTS idx_majors_riasec_gin ON majors USING GIN (riasec_vector);

CREATE TABLE IF NOT EXISTS subject_blocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    block_code VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    subjects JSONB NOT NULL,
    national_mean DOUBLE PRECISION NOT NULL DEFAULT 20.0,
    national_std DOUBLE PRECISION NOT NULL DEFAULT 3.0,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_subject_blocks_code ON subject_blocks(block_code);

CREATE TABLE IF NOT EXISTS major_subject_blocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    major_id UUID NOT NULL REFERENCES majors(id) ON DELETE CASCADE,
    subject_block_id UUID NOT NULL REFERENCES subject_blocks(id) ON DELETE CASCADE,
    weight DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    CONSTRAINT uq_major_subject_block UNIQUE (major_id, subject_block_id)
);

CREATE INDEX IF NOT EXISTS idx_msb_major ON major_subject_blocks(major_id);
CREATE INDEX IF NOT EXISTS idx_msb_block ON major_subject_blocks(subject_block_id);

CREATE TABLE IF NOT EXISTS careers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    major_id UUID NOT NULL REFERENCES majors(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    career_tree_level VARCHAR(50) NOT NULL DEFAULT 'Lá - Nghề nghiệp cụ thể',
    description TEXT NOT NULL,
    responsibilities JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_careers_major_id ON careers(major_id);
CREATE INDEX IF NOT EXISTS idx_careers_tree_level ON careers(career_tree_level);

CREATE TABLE IF NOT EXISTS skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    skill_type skill_type_enum NOT NULL,
    domain VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_skills_code ON skills(skill_code);
CREATE INDEX IF NOT EXISTS idx_skills_domain ON skills(domain);
CREATE INDEX IF NOT EXISTS idx_skills_type ON skills(skill_type);

CREATE TABLE IF NOT EXISTS skill_prerequisites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    prerequisite_skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    CONSTRAINT uq_skill_prereq UNIQUE (skill_id, prerequisite_skill_id)
);

CREATE INDEX IF NOT EXISTS idx_sp_skill ON skill_prerequisites(skill_id);
CREATE INDEX IF NOT EXISTS idx_sp_prereq ON skill_prerequisites(prerequisite_skill_id);

CREATE TABLE IF NOT EXISTS major_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    major_id UUID NOT NULL REFERENCES majors(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    importance_level VARCHAR(50) NOT NULL DEFAULT 'MANDATORY',
    CONSTRAINT uq_major_skill UNIQUE (major_id, skill_id)
);

CREATE INDEX IF NOT EXISTS idx_major_skills_major ON major_skills(major_id);
CREATE INDEX IF NOT EXISTS idx_major_skills_skill ON major_skills(skill_id);

-- -----------------------------------------------------------------------------
-- 3. PHÂN HỆ KHẢO SÁT & ĐÁNH GIÁ NĂNG LỰC (ASSESSMENT & TRANSCRIPTS)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS assessment_question_sets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    set_code VARCHAR(50) UNIQUE NOT NULL,
    version VARCHAR(20) NOT NULL DEFAULT '1.8',
    title VARCHAR(255) NOT NULL,
    description TEXT,
    circular_ref VARCHAR(100) NOT NULL DEFAULT '74/2026/TT-BGDĐT',
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_aqs_code ON assessment_question_sets(set_code);
CREATE INDEX IF NOT EXISTS idx_aqs_active ON assessment_question_sets(is_active);

CREATE TABLE IF NOT EXISTS assessment_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_set_id UUID NOT NULL REFERENCES assessment_question_sets(id) ON DELETE CASCADE,
    question_code VARCHAR(50) UNIQUE NOT NULL,
    question_text TEXT NOT NULL,
    dimension VARCHAR(20) NOT NULL,
    order_index INTEGER NOT NULL DEFAULT 1,
    category_type VARCHAR(50) NOT NULL DEFAULT 'RIASEC',
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_aq_set_id ON assessment_questions(question_set_id);
CREATE INDEX IF NOT EXISTS idx_aq_dimension ON assessment_questions(dimension);
CREATE INDEX IF NOT EXISTS idx_aq_order ON assessment_questions(order_index);

CREATE TABLE IF NOT EXISTS cognitive_question_options (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES assessment_questions(id) ON DELETE CASCADE,
    option_key VARCHAR(10) NOT NULL,
    option_text TEXT NOT NULL,
    trait_indicator VARCHAR(100) NOT NULL,
    value_weight DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_question_option UNIQUE (question_id, option_key)
);

CREATE INDEX IF NOT EXISTS idx_cqo_question ON cognitive_question_options(question_id);

CREATE TABLE IF NOT EXISTS student_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    riasec_scores JSONB NOT NULL,
    cognitive_preferences JSONB NOT NULL,
    raw_responses JSONB NOT NULL DEFAULT '{}'::jsonb,
    assessed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_sa_user_id ON student_assessments(user_id);
CREATE INDEX IF NOT EXISTS idx_sa_date ON student_assessments(assessed_at);

CREATE TABLE IF NOT EXISTS student_assessment_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_set_id UUID NOT NULL REFERENCES assessment_question_sets(id) ON DELETE RESTRICT,
    riasec_scores JSONB NOT NULL,
    dominant_traits JSONB NOT NULL,
    cognitive_profile JSONB NOT NULL DEFAULT '{}'::jsonb,
    completion_time_seconds INTEGER NOT NULL DEFAULT 360,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_subm_user ON student_assessment_submissions(user_id);
CREATE INDEX IF NOT EXISTS idx_subm_date ON student_assessment_submissions(submitted_at);

CREATE TABLE IF NOT EXISTS student_assessment_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL REFERENCES student_assessment_submissions(id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES assessment_questions(id) ON DELETE RESTRICT,
    selected_value INTEGER,
    response_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_submission_question UNIQUE (submission_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_sar_submission ON student_assessment_responses(submission_id);
CREATE INDEX IF NOT EXISTS idx_sar_question ON student_assessment_responses(question_id);

CREATE TABLE IF NOT EXISTS student_grades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    grades_by_subject JSONB NOT NULL,
    multi_semester_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    computed_block_zscores JSONB NOT NULL,
    academic_year VARCHAR(20) NOT NULL DEFAULT '2025-2026',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_sg_user ON student_grades(user_id);

CREATE TABLE IF NOT EXISTS student_diagnostic_tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    test_type VARCHAR(50) NOT NULL,
    raw_score DOUBLE PRECISION NOT NULL,
    normalized_score DOUBLE PRECISION NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_sdt_user ON student_diagnostic_tests(user_id);

-- -----------------------------------------------------------------------------
-- 4. PHÂN HỆ ĐỀ XUẤT ĐA TRỤ CỘT & GIẢI TRÌNH XAI (RECOMMENDATION ENGINE)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS recommendation_histories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    weights_applied JSONB NOT NULL,
    ranked_results JSONB NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_rec_history_user ON recommendation_histories(user_id);
CREATE INDEX IF NOT EXISTS idx_rec_history_date ON recommendation_histories(generated_at);

-- -----------------------------------------------------------------------------
-- 5. PHÂN HỆ LỘ TRÌNH PHÁT TRIỂN KỸ NĂNG & HỌC TẬP (ROADMAPS & PROGRESS)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS major_roadmaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    major_code VARCHAR(20) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    version VARCHAR(20) NOT NULL DEFAULT '1.0',
    roadmap_data JSONB NOT NULL,
    is_fallback BOOLEAN NOT NULL DEFAULT FALSE,
    fallback_template JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_roadmaps_code ON major_roadmaps(major_code);

CREATE TABLE IF NOT EXISTS student_roadmap_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    major_code VARCHAR(20) NOT NULL,
    progress_percent DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    completed_action_keys JSONB NOT NULL DEFAULT '[]'::jsonb,
    last_studied_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_student_major_progress UNIQUE (user_id, major_code)
);

CREATE INDEX IF NOT EXISTS idx_srp_user ON student_roadmap_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_srp_major ON student_roadmap_progress(major_code);

-- -----------------------------------------------------------------------------
-- 6. PHÂN HỆ KIỂM DUYỆT TRI THỨC NGƯỜI-TRONG-VÒNG-LẶP (HITL STAGING)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS staging_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stream_type staging_stream_type_enum NOT NULL,
    status staging_status_enum NOT NULL DEFAULT 'PENDING',
    major_code VARCHAR(20),
    content_hash VARCHAR(64) UNIQUE NOT NULL,
    source_title VARCHAR(255) NOT NULL,
    source_url VARCHAR(1000),
    source_page VARCHAR(50),
    extracted_payload JSONB NOT NULL,
    reviewer_id UUID REFERENCES users(id) ON DELETE SET NULL,
    review_notes TEXT,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_staging_status ON staging_records(status);
CREATE INDEX IF NOT EXISTS idx_staging_stream ON staging_records(stream_type);
CREATE INDEX IF NOT EXISTS idx_staging_hash ON staging_records(content_hash);

-- -----------------------------------------------------------------------------
-- 7. PHÂN HỆ CƠ SỞ TRI THỨC VECTOR RAG (KNOWLEDGE EMBEDDINGS)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS knowledge_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    major_code VARCHAR(20),
    skill_id UUID REFERENCES skills(id) ON DELETE SET NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    source_title VARCHAR(255),
    source_url VARCHAR(1000),
    source_page VARCHAR(50),
    metadata_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_ke_major_code ON knowledge_embeddings(major_code);
CREATE INDEX IF NOT EXISTS idx_ke_skill_id ON knowledge_embeddings(skill_id);
-- HNSW Vector Index for ultra-fast Cosine Distance Semantic Search (< 50ms)
CREATE INDEX IF NOT EXISTS idx_ke_embedding_hnsw ON knowledge_embeddings 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);
