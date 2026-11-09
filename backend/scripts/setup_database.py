"""
AI CareerGuide - Unified Database Creator & Initial Seeder
Creates:
1. Physical SQLite local database (backend/app/db/careerguide.db) for immediate offline execution.
2. Full seeding of all 108 Level-IV MOET Majors (Thông tư 09/2022/TT-BGDĐT).
3. Full seeding of National Admission Subject Blocks (A00, A01, B00, C00, D01, etc.).
4. Full seeding of Assessment Question Set v1.8 (30 RIASEC + 8 Cognitive items).
5. Pre-seeded demo accounts with Argon2id password hashing compliant with OWASP ASVS Level 2.
"""

import os
import sys
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.security import get_password_hash

DB_PATH = backend_dir / "app" / "db" / "careerguide.db"
SEEDS_DIR = backend_dir / "app" / "db" / "seeds"


def create_schema(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.executescript("""
    PRAGMA foreign_keys = ON;

    -- 1. Users & Privacy Consent
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'STUDENT',
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS user_consents (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        consent_type TEXT NOT NULL,
        policy_version TEXT NOT NULL DEFAULT 'v1.0-Law91/2025/QH15',
        is_granted INTEGER NOT NULL DEFAULT 1,
        ip_address TEXT,
        user_agent TEXT,
        granted_at TEXT NOT NULL,
        revoked_at TEXT
    );

    -- 2. MOET TT09 Majors & Subject Blocks
    CREATE TABLE IF NOT EXISTS majors (
        id TEXT PRIMARY KEY,
        major_code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'Khác',
        degree_level TEXT NOT NULL DEFAULT 'Đại học',
        riasec_vector TEXT NOT NULL,
        cognitive_attributes TEXT NOT NULL,
        industry_outlook TEXT NOT NULL,
        description TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS subject_blocks (
        id TEXT PRIMARY KEY,
        block_code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        subjects TEXT NOT NULL,
        national_mean REAL NOT NULL DEFAULT 20.0,
        national_std REAL NOT NULL DEFAULT 3.0,
        description TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS major_subject_blocks (
        id TEXT PRIMARY KEY,
        major_id TEXT NOT NULL REFERENCES majors(id) ON DELETE CASCADE,
        subject_block_id TEXT NOT NULL REFERENCES subject_blocks(id) ON DELETE CASCADE,
        weight REAL NOT NULL DEFAULT 1.0,
        UNIQUE(major_id, subject_block_id)
    );

    CREATE TABLE IF NOT EXISTS careers (
        id TEXT PRIMARY KEY,
        major_id TEXT NOT NULL REFERENCES majors(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        career_tree_level TEXT NOT NULL DEFAULT 'Lá - Nghề nghiệp cụ thể',
        description TEXT NOT NULL,
        responsibilities TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS skills (
        id TEXT PRIMARY KEY,
        skill_code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        skill_type TEXT NOT NULL,
        domain TEXT NOT NULL,
        description TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS skill_prerequisites (
        id TEXT PRIMARY KEY,
        skill_id TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
        prerequisite_skill_id TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
        UNIQUE(skill_id, prerequisite_skill_id)
    );

    CREATE TABLE IF NOT EXISTS major_skills (
        id TEXT PRIMARY KEY,
        major_id TEXT NOT NULL REFERENCES majors(id) ON DELETE CASCADE,
        skill_id TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
        importance_level TEXT NOT NULL DEFAULT 'MANDATORY',
        UNIQUE(major_id, skill_id)
    );

    -- 3. Assessment Question Sets & Questions
    CREATE TABLE IF NOT EXISTS assessment_question_sets (
        id TEXT PRIMARY KEY,
        set_code TEXT UNIQUE NOT NULL,
        version TEXT NOT NULL DEFAULT '1.8',
        title TEXT NOT NULL,
        description TEXT,
        circular_ref TEXT NOT NULL DEFAULT '74/2026/TT-BGDĐT',
        config TEXT NOT NULL DEFAULT '{}',
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS assessment_questions (
        id TEXT PRIMARY KEY,
        question_set_id TEXT NOT NULL REFERENCES assessment_question_sets(id) ON DELETE CASCADE,
        question_code TEXT UNIQUE NOT NULL,
        question_text TEXT NOT NULL,
        dimension TEXT NOT NULL,
        order_index INTEGER NOT NULL DEFAULT 1,
        category_type TEXT NOT NULL DEFAULT 'RIASEC',
        config TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS cognitive_question_options (
        id TEXT PRIMARY KEY,
        question_id TEXT NOT NULL REFERENCES assessment_questions(id) ON DELETE CASCADE,
        option_key TEXT NOT NULL,
        option_text TEXT NOT NULL,
        trait_indicator TEXT NOT NULL,
        value_weight REAL NOT NULL DEFAULT 1.0,
        created_at TEXT NOT NULL,
        UNIQUE(question_id, option_key)
    );

    CREATE TABLE IF NOT EXISTS student_assessments (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        riasec_scores TEXT NOT NULL,
        cognitive_preferences TEXT NOT NULL,
        raw_responses TEXT NOT NULL DEFAULT '{}',
        assessed_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS student_assessment_submissions (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        question_set_id TEXT NOT NULL REFERENCES assessment_question_sets(id),
        riasec_scores TEXT NOT NULL,
        dominant_traits TEXT NOT NULL,
        cognitive_profile TEXT NOT NULL DEFAULT '{}',
        completion_time_seconds INTEGER NOT NULL DEFAULT 360,
        submitted_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS student_assessment_responses (
        id TEXT PRIMARY KEY,
        submission_id TEXT NOT NULL REFERENCES student_assessment_submissions(id) ON DELETE CASCADE,
        question_id TEXT NOT NULL REFERENCES assessment_questions(id),
        selected_value INTEGER,
        response_text TEXT,
        created_at TEXT NOT NULL,
        UNIQUE(submission_id, question_id)
    );

    CREATE TABLE IF NOT EXISTS student_grades (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        grades_by_subject TEXT NOT NULL,
        multi_semester_data TEXT NOT NULL DEFAULT '{}',
        computed_block_zscores TEXT NOT NULL,
        academic_year TEXT NOT NULL DEFAULT '2025-2026',
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS student_diagnostic_tests (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        test_type TEXT NOT NULL,
        raw_score REAL NOT NULL,
        normalized_score REAL NOT NULL,
        evaluated_at TEXT NOT NULL
    );

    -- 4. Recommendations & Explainability
    CREATE TABLE IF NOT EXISTS recommendation_histories (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        weights_applied TEXT NOT NULL,
        ranked_results TEXT NOT NULL,
        generated_at TEXT NOT NULL
    );

    -- 5. Personalized Roadmaps
    CREATE TABLE IF NOT EXISTS major_roadmaps (
        id TEXT PRIMARY KEY,
        major_code TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        version TEXT NOT NULL DEFAULT '1.0',
        roadmap_data TEXT NOT NULL,
        is_fallback INTEGER NOT NULL DEFAULT 0,
        fallback_template TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS student_roadmap_progress (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        major_code TEXT NOT NULL,
        progress_percent REAL NOT NULL DEFAULT 0.0,
        completed_action_keys TEXT NOT NULL DEFAULT '[]',
        last_studied_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(user_id, major_code)
    );

    -- 6. Staging & HITL
    CREATE TABLE IF NOT EXISTS staging_records (
        id TEXT PRIMARY KEY,
        stream_type TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'PENDING',
        major_code TEXT,
        content_hash TEXT UNIQUE NOT NULL,
        source_title TEXT NOT NULL,
        source_url TEXT,
        source_page TEXT,
        extracted_payload TEXT NOT NULL,
        reviewer_id TEXT REFERENCES users(id),
        review_notes TEXT,
        reviewed_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    -- 7. Knowledge Embeddings
    CREATE TABLE IF NOT EXISTS knowledge_embeddings (
        id TEXT PRIMARY KEY,
        major_code TEXT,
        skill_id TEXT REFERENCES skills(id),
        chunk_text TEXT NOT NULL,
        embedding TEXT NOT NULL,
        source_title TEXT,
        source_url TEXT,
        source_page TEXT,
        metadata_payload TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
    );
    """)
    conn.commit()
    print("Database tables created successfully.")


def seed_data(conn: sqlite3.Connection):
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Seed Demo Users
    admin_id = str(uuid.uuid4())
    student_id = str(uuid.uuid4())

    cursor.execute("""
    INSERT OR IGNORE INTO users (id, email, hashed_password, full_name, role, is_active, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, 1, ?, ?)
    """, (admin_id, "admin@careerguide.vn", get_password_hash("AdminSecret@2026"), "Quản Trị Viên Kiểm Duyệt", "ADMIN", now_iso, now_iso))

    cursor.execute("""
    INSERT OR IGNORE INTO users (id, email, hashed_password, full_name, role, is_active, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, 1, ?, ?)
    """, (student_id, "hocsinh.genz@gmail.com", get_password_hash("StudentSecret@2026"), "Nguyễn Văn Tuấn", "STUDENT", now_iso, now_iso))

    # Seed Consent for both
    cursor.execute("""
    INSERT OR IGNORE INTO user_consents (id, user_id, consent_type, policy_version, is_granted, granted_at)
    VALUES (?, ?, 'INITIAL_ONBOARDING_TERMS_LAW91_2025', 'v1.0-Law91/2025/QH15', 1, ?)
    """, (str(uuid.uuid4()), admin_id, now_iso))

    cursor.execute("""
    INSERT OR IGNORE INTO user_consents (id, user_id, consent_type, policy_version, is_granted, granted_at)
    VALUES (?, ?, 'INITIAL_ONBOARDING_TERMS_LAW91_2025', 'v1.0-Law91/2025/QH15', 1, ?)
    """, (str(uuid.uuid4()), student_id, now_iso))

    # 2. Seed Standard Admission Subject Blocks
    STANDARD_BLOCKS = [
        ("A00", "Toán, Vật lí, Hóa học", ["Toán", "Vật lí", "Hóa học"], 20.85, 3.25),
        ("A01", "Toán, Vật lí, Tiếng Anh", ["Toán", "Vật lí", "Tiếng Anh"], 20.40, 3.35),
        ("B00", "Toán, Hóa học, Sinh học", ["Toán", "Hóa học", "Sinh học"], 19.80, 3.40),
        ("C00", "Ngữ văn, Lịch sử, Địa lí", ["Ngữ văn", "Lịch sử", "Địa lí"], 19.20, 3.15),
        ("D01", "Toán, Ngữ văn, Tiếng Anh", ["Toán", "Ngữ văn", "Tiếng Anh"], 19.95, 3.10),
        ("D07", "Toán, Hóa học, Tiếng Anh", ["Toán", "Hóa học", "Tiếng Anh"], 20.10, 3.20),
        ("A02", "Toán, Vật lí, Sinh học", ["Toán", "Vật lí", "Sinh học"], 19.50, 3.10),
        ("D08", "Toán, Sinh học, Tiếng Anh", ["Toán", "Sinh học", "Tiếng Anh"], 19.70, 3.15),
        ("M00", "Ngữ văn, Toán, Năng khiếu", ["Ngữ văn", "Toán", "Năng khiếu"], 19.00, 3.00),
        ("V00", "Toán, Vật lí, Vẽ hình họa", ["Toán", "Vật lí", "Vẽ hình họa"], 19.50, 3.00),
        ("H00", "Ngữ văn, Năng khiếu vẽ 1, Năng khiếu vẽ 2", ["Ngữ văn", "Năng khiếu vẽ 1", "Năng khiếu vẽ 2"], 19.00, 3.00),
    ]

    block_map = {}
    for code, name, subjects, mu, sigma in STANDARD_BLOCKS:
        cursor.execute("SELECT id FROM subject_blocks WHERE block_code = ?", (code,))
        row = cursor.fetchone()
        if row:
            b_id = row[0]
        else:
            b_id = str(uuid.uuid4())
            cursor.execute("""
            INSERT INTO subject_blocks (id, block_code, name, subjects, national_mean, national_std, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (b_id, code, name, json.dumps(subjects, ensure_ascii=False), mu, sigma, now_iso, now_iso))
        block_map[code] = b_id

    # 3. Seed 108 Majors from moet_taxonomy_tt09.json
    tt09_json_path = SEEDS_DIR / "moet_taxonomy_tt09.json"
    if tt09_json_path.exists():
        with open(tt09_json_path, "r", encoding="utf-8") as f:
            majors_data = json.load(f)

        print(f"Loaded {len(majors_data)} majors from moet_taxonomy_tt09.json...")
        for item in majors_data:
            m_code = item["major_code"]
            cursor.execute("SELECT id FROM majors WHERE major_code = ?", (m_code,))
            row = cursor.fetchone()
            if row:
                m_id = row[0]
            else:
                m_id = str(uuid.uuid4())
                cursor.execute("""
                INSERT INTO majors (id, major_code, name, category, degree_level, riasec_vector, cognitive_attributes, industry_outlook, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'Đại học', ?, ?, ?, ?, ?)
                """, (
                    m_id,
                    m_code,
                    item["name"],
                    item.get("category", "Khác"),
                    json.dumps(item.get("riasec", {}), ensure_ascii=False),
                    json.dumps(item.get("cognitive", {}), ensure_ascii=False),
                    item.get("outlook", "Triển vọng phát triển tốt trong kỷ nguyên số."),
                    now_iso,
                    now_iso
                ))

            # Link Subject Blocks
            for b_code in item.get("blocks", []):
                if b_code in block_map:
                    cursor.execute("""
                    INSERT OR IGNORE INTO major_subject_blocks (id, major_id, subject_block_id, weight)
                    VALUES (?, ?, ?, 1.0)
                    """, (str(uuid.uuid4()), m_id, block_map[b_code]))

            # Seed Careers
            for c_title in item.get("careers", []):
                cursor.execute("""
                INSERT OR IGNORE INTO careers (id, major_id, title, career_tree_level, description, responsibilities, created_at, updated_at)
                VALUES (?, ?, ?, 'Lá - Nghề nghiệp cụ thể', ?, '[]', ?, ?)
                """, (str(uuid.uuid4()), m_id, c_title, f"Vị trí công việc: {c_title} thuộc ngành {item['name']}", now_iso, now_iso))

    # 4. Seed Assessment Question Set v1.8
    questions_json_path = SEEDS_DIR / "assessment_questions_v1_8.json"
    if questions_json_path.exists():
        with open(questions_json_path, "r", encoding="utf-8") as f:
            q_data = json.load(f)

        set_code = "RIASEC_COG_V1_8"
        cursor.execute("SELECT id FROM assessment_question_sets WHERE set_code = ?", (set_code,))
        row = cursor.fetchone()
        if row:
            set_id = row[0]
        else:
            set_id = str(uuid.uuid4())
            cursor.execute("""
            INSERT INTO assessment_question_sets (id, set_code, version, title, description, circular_ref, config, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (
                set_id,
                set_code,
                q_data.get("version", "1.8"),
                "Bộ câu hỏi Đánh giá Sở thích & Thiên hướng Nhận thức chuẩn v1.8",
                "Chuẩn hóa 30 câu hỏi RIASEC và 8 câu hỏi Nhận thức theo Thông tư 74/2026/TT-BGDĐT",
                q_data.get("circular_ref", "74/2026/TT-BGDĐT"),
                json.dumps(q_data.get("config", {}), ensure_ascii=False),
                now_iso,
                now_iso
            ))

        # Seed RIASEC Questions (30 items)
        order_idx = 1
        for q in q_data.get("riasec_questions", []):
            q_code = q["code"]
            q_text = q.get("question_text", q.get("text", ""))
            dim = q["dimension"]
            cursor.execute("SELECT id FROM assessment_questions WHERE question_code = ?", (q_code,))
            if not cursor.fetchone():
                cursor.execute("""
                INSERT INTO assessment_questions (id, question_set_id, question_code, question_text, dimension, order_index, category_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'RIASEC', ?)
                """, (str(uuid.uuid4()), set_id, q_code, q_text, dim, q.get("order", order_idx), now_iso))
                order_idx += 1

        # Seed Cognitive Questions and Options
        for cog_q in q_data.get("cognitive_questions", []):
            q_code = cog_q["code"]
            q_text = cog_q.get("title", "")
            if cog_q.get("subtitle"):
                q_text += " - " + cog_q["subtitle"]

            cursor.execute("SELECT id FROM assessment_questions WHERE question_code = ?", (q_code,))
            row = cursor.fetchone()
            if row:
                q_id = row[0]
            else:
                q_id = str(uuid.uuid4())
                cursor.execute("""
                INSERT INTO assessment_questions (id, question_set_id, question_code, question_text, dimension, order_index, category_type, created_at)
                VALUES (?, ?, ?, ?, 'COGNITIVE', ?, 'COGNITIVE', ?)
                """, (q_id, set_id, q_code, q_text, order_idx, now_iso))
                order_idx += 1

            for opt in cog_q.get("options", []):
                opt_key = opt.get("option_key", opt.get("key", "A"))
                opt_text = opt.get("title", opt.get("text", ""))
                if opt.get("description"):
                    opt_text += f": {opt['description']}"
                trait_code = opt.get("trait_code", opt.get("trait", "general"))

                cursor.execute("""
                INSERT OR IGNORE INTO cognitive_question_options (id, question_id, option_key, option_text, trait_indicator, value_weight, created_at)
                VALUES (?, ?, ?, ?, ?, 1.0, ?)
                """, (str(uuid.uuid4()), q_id, opt_key, opt_text, trait_code, now_iso))

    # 5. Seed Major Roadmaps for representative majors
    ROADMAP_SAMPLES = [
        ("7480201", "Lộ trình Chuẩn Công nghệ Thông tin (Software Engineering)", {
            "milestones": [
                {"stage": "Giai đoạn 1 (Lớp 10-11)", "title": "Nền tảng Toán - Tin & Ngoại ngữ", "actions": ["Hoàn thành Toán giải tích THPT", "Học tư duy thuật toán cơ bản (Python/C++)", "Rèn luyện tiếng Anh B1"]},
                {"stage": "Giai đoạn 2 (Lớp 12)", "title": "Bứt phá Điểm số & Dự án mini", "actions": ["Luyện tổ hợp A00/A01 đạt Z-Score >= 1.0", "Xây dựng dự án mã nguồn mở đầu tiên trên GitHub", "Tham gia kỳ thi đánh giá năng lực ĐHQG"]},
                {"stage": "Giai đoạn 3 (Đại học Năm 1-2)", "title": "Cấu trúc dữ liệu & Lập trình mạng", "actions": ["Nắm vững Cấu trúc dữ liệu và Giải thuật", "Học Kiến trúc máy tính và Hệ điều hành Linux", "Thực tập dự án nhóm theo mô hình Agile/Scrum"]}
            ],
            "prerequisites": ["Toán học THPT vững chắc", "Tư duy logic hình thức", "Ngoại ngữ đọc hiểu tài liệu kỹ thuật"],
            "target_skills": ["Phát triển phần mềm Fullstack", "Thiết kế kiến trúc hệ thống", "Làm việc nhóm và tư duy phản biện"]
        }),
        ("7720101", "Lộ trình Chuẩn Y khoa (Bác sĩ Đa khoa)", {
            "milestones": [
                {"stage": "Giai đoạn 1 (Lớp 10-11)", "title": "Nền tảng Sinh học - Hóa học", "actions": ["Nắm chắc Sinh học tế bào và Di truyền học", "Rèn luyện tính cẩn trọng, tỉ mỉ và đồng cảm xã hội", "Học tiếng Anh chuyên ngành Sinh học"]},
                {"stage": "Giai đoạn 2 (Lớp 12)", "title": "Chinh phục Khối B00", "actions": ["Luyện tổ hợp B00 đạt điểm chuẩn tốp đầu", "Giữ vững sức khỏe thể chất và tinh thần bền bỉ", "Tìm hiểu y đức và môi trường lâm sàng thực tế"]}
            ],
            "prerequisites": ["Sinh học & Hóa học chuyên sâu", "Sức bền tâm lý và khả năng làm việc áp lực cao"],
            "target_skills": ["Chẩn đoán lâm sàng", "Y đức và giao tiếp bệnh nhân", "Nghiên cứu y sinh"]
        }),
        ("7340101", "Lộ trình Chuẩn Quản trị Kinh doanh", {
            "milestones": [
                {"stage": "Giai đoạn 1 (Lớp 10-11)", "title": "Kỹ năng Giao tiếp & Tư duy Kinh tế", "actions": ["Rèn luyện khả năng thuyết trình và hùng biện", "Đọc các ấn phẩm kinh tế vĩ mô và khởi nghiệp", "Luyện tiếng Anh giao tiếp và viết luận"]},
                {"stage": "Giai đoạn 2 (Lớp 12)", "title": "Tối ưu hóa Khối A01/D01", "actions": ["Ôn tập trọng tâm Toán, Văn, Anh", "Tham gia các cuộc thi tranh biện hoặc dự án cộng đồng"]}
            ],
            "prerequisites": ["Toán ứng dụng và thống kê", "Kỹ năng giao tiếp và ngoại ngữ lưu loát"],
            "target_skills": ["Hoạch định chiến lược", "Quản trị nhân sự và đàm phán", "Phân tích thị trường"]
        })
    ]

    for m_code, r_title, r_data in ROADMAP_SAMPLES:
        cursor.execute("SELECT id FROM major_roadmaps WHERE major_code = ?", (m_code,))
        if not cursor.fetchone():
            cursor.execute("""
            INSERT INTO major_roadmaps (id, major_code, title, version, roadmap_data, is_fallback, created_at, updated_at)
            VALUES (?, ?, ?, '1.0', ?, 1, ?, ?)
            """, (str(uuid.uuid4()), m_code, r_title, json.dumps(r_data, ensure_ascii=False), now_iso, now_iso))

    conn.commit()
    print("Sample and Seed data populated successfully.")


def main():
    print("=" * 70)
    print("AI CAREERGUIDE - DATABASE CREATOR & SEEDER")
    print("=" * 70)
    print(f"Target SQLite database path: {DB_PATH}")

    # Ensure parent directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Connect and create
    conn = sqlite3.connect(str(DB_PATH))
    try:
        create_schema(conn)
        seed_data(conn)
        
        # Verify counts
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM majors")
        n_majors = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM subject_blocks")
        n_blocks = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM assessment_questions")
        n_questions = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users")
        n_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM major_roadmaps")
        n_roadmaps = cursor.fetchone()[0]

        print("\nVerification Summary:")
        print(f" - Majors (TT09): {n_majors}")
        print(f" - Subject Blocks: {n_blocks}")
        print(f" - Assessment Questions: {n_questions}")
        print(f" - Users: {n_users}")
        print(f" - Major Roadmaps: {n_roadmaps}")
        print(f"\nDATABASE CREATED & SEEDED SUCCESSFULLY at:\n{DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
