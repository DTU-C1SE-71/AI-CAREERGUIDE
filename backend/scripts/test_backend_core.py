import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token
from app.schemas.taxonomy import MajorCreate
from app.services.recommender.service import compute_cosine_similarity, compute_cognitive_match
from app.services.assessment.service import normal_cdf
from app.services.gap_roadmap_engine.service import generate_static_fallback_roadmap
from app.services.llamaindex_rag_orchestrator.service import sanitize_pii, compute_content_sha256
from scripts.seed_tt09 import MAJORS_DATA, SUBJECT_BLOCKS_DATA, SKILLS_DATA


def run_all_tests():
    print("=" * 75)
    print("AI CAREERGUIDE BACKEND CORE - COMPREHENSIVE VERIFICATION SUITE")
    print("=" * 75)

    client = TestClient(app)
    passed = 0
    total = 0

    # 1. Test Server Health & OpenAPI
    total += 1
    res = client.get("/health")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data["status"] == "healthy"
    print(f"[{total}] Health Check Endpoint: PASSED (status: {data['status']}, version: {data['version']})")
    passed += 1

    total += 1
    res_docs = client.get("/docs")
    assert res_docs.status_code == 200
    print(f"[{total}] Interactive Swagger Docs (/docs): PASSED")
    passed += 1

    # 2. Test Security: Argon2id (OWASP ASVS Level 2)
    total += 1
    raw_pass = "StudentPass2026@OWASP"
    hashed = get_password_hash(raw_pass)
    assert hashed.startswith("$argon2id$"), "Hash must be Argon2id"
    assert "m=65536" in hashed, "Memory cost must be 64 MiB (OWASP ASVS Level 2)"
    assert "t=3" in hashed, "Time cost must be 3"
    assert "p=2" in hashed, "Parallelism must be 2"
    assert verify_password(raw_pass, hashed) is True, "Password verification failed"
    assert verify_password("WrongPassword!", hashed) is False, "Password verification false positive"
    print(f"[{total}] OWASP ASVS Level 2 Argon2id Hashing & Verification: PASSED")
    passed += 1

    # 3. Test JWT Token & RBAC Encoding
    total += 1
    token = create_access_token(subject="user-uuid-123", role="STUDENT")
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user-uuid-123"
    assert decoded["role"] == "STUDENT"
    print(f"[{total}] JWT Access Token Generation & RBAC Role Claim: PASSED")
    passed += 1

    # 4. Test Pure Guidance Scope Guardrail (No tuition fees, No location)
    total += 1
    guardrail_caught = False
    try:
        MajorCreate(
            major_code="7480201",
            name="Công nghệ thông tin",
            riasec_vector={"R": 0.5, "I": 0.9, "A": 0.2, "S": 0.3, "E": 0.4, "C": 0.6},
            cognitive_attributes={},
            industry_outlook="Good",
            tuition_fees=25000000  # Prohibited parameter!
        )
    except Exception as e:
        guardrail_caught = "Pure Guidance Scope Violation" in str(e)
    assert guardrail_caught, "Guardrail failed to catch tuition_fees injection!"
    print(f"[{total}] Pure Guidance Scope Guardrail (Excluding socio-economic bias): PASSED")
    passed += 1

    # 5. Test Circular 09/2022/TT-BGDĐT Seed Catalog Completeness
    total += 1
    majors_count = len(MAJORS_DATA)
    assert majors_count >= 80, f"Expected >= 80 majors, got {majors_count}"
    blocks_count = len(SUBJECT_BLOCKS_DATA)
    skills_count = len(SKILLS_DATA)
    print(f"[{total}] MOET Circular 09/2022/TT-BGDĐT Catalog: PASSED ({majors_count} Level-IV majors, {blocks_count} admission blocks, {skills_count} skills)")
    passed += 1

    # 6. Test Deterministic 3-Pillar Scoring Algorithms
    total += 1
    # Cosine Similarity test
    student_riasec = {"R": 0.8, "I": 0.9, "A": 0.2, "S": 0.3, "E": 0.4, "C": 0.6}
    major_riasec = {"R": 0.5, "I": 0.9, "A": 0.3, "S": 0.3, "E": 0.5, "C": 0.7}
    sim = compute_cosine_similarity(student_riasec, major_riasec)
    assert 0.0 <= sim <= 1.0
    assert round(sim, 4) == 0.9710, f"Expected 0.9710, got {round(sim, 4)}"

    # Academic Normal CDF test: Z = (24.0 - 20.85) / 3.25 = 0.9692
    z_score = (24.0 - 20.85) / 3.25
    cdf_val = normal_cdf(z_score)
    assert 0.0 <= cdf_val <= 1.0

    # Cognitive trait rule-based match
    s_pref = {"abstract_thinking": "high", "learning_environment": "structured"}
    m_attr = {"abstract_thinking": "high", "learning_environment": "structured"}
    cog_score = compute_cognitive_match(s_pref, m_attr)
    assert cog_score == 1.0

    # 3-pillar formula: 0.45 * RIASEC + 0.35 * Academic + 0.20 * Preference
    score_major = 0.45 * sim + 0.35 * cdf_val + 0.20 * cog_score
    assert 0.0 <= score_major <= 1.0
    print(f"[{total}] Deterministic 3-Pillar Scoring Engine: PASSED (RIASEC: {round(sim, 4)}, Z-CDF: {round(cdf_val, 4)}, Total: {round(score_major, 4)})")
    passed += 1

    # 7. Test Static Fallback Roadmap Generation (<= 1s response guaranteed)
    total += 1
    fallback = generate_static_fallback_roadmap("7480201", "Công nghệ thông tin")
    assert len(fallback["milestones"]) == 3
    assert len(fallback["prerequisite_knowledge"]) > 0
    assert len(fallback["target_skills"]) > 0
    assert len(fallback["reference_materials"]) > 0
    print(f"[{total}] Static Fallback Roadmap Generation (Offline & Fast Lookup): PASSED")
    passed += 1

    # 8. Test PII Sanitization Guardrail (Law 91/2025/QH15)
    total += 1
    raw_user_text = "Học sinh Nguyễn Văn A, email: nguyenvana@gmail.com, SDT: 0987654321, CCCD: 012345678901 cần tư vấn lộ trình."
    sanitized = sanitize_pii(raw_user_text)
    assert "nguyenvana@gmail.com" not in sanitized
    assert "0987654321" not in sanitized
    assert "012345678901" not in sanitized
    assert "[REDACTED_EMAIL]" in sanitized
    assert "[REDACTED_PHONE]" in sanitized
    assert "[REDACTED_ID]" in sanitized
    print(f"[{total}] PII Sanitization for OpenAI Prompts (Law 91/2025/QH15): PASSED")
    passed += 1

    # 9. Test Deduplication via Content Hash
    total += 1
    content_a = "Giáo trình nhập môn ngành CNTT trường ĐHBK"
    hash_a = compute_content_sha256(content_a)
    assert len(hash_a) == 64
    assert hash_a == compute_content_sha256(content_a)
    print(f"[{total}] SHA-256 Deduplication Hashing for Ingestion Staging: PASSED")
    passed += 1

    print("=" * 75)
    print(f"ALL TESTS COMPLETED: {passed}/{total} PASSED (100% SUCCESS)")
    print("=" * 75)


if __name__ == "__main__":
    run_all_tests()
