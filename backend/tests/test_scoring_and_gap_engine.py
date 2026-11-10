import math
import time
import pytest
from typing import Dict, Any, List

from app.services.recommender.engine import (
    normal_cdf,
    calculate_riasec_cosine_similarity,
    calculate_z_score_and_cdf,
    evaluate_academic_readiness_for_major,
    calculate_cognitive_preference_match,
    calculate_3pillar_hybrid_score,
    generate_xai_top_supporting_factors,
    RIASEC_DIMENSIONS,
)
from app.services.gap_roadmap_engine.gap_engine import (
    infer_mastered_skills_from_grades,
    infer_mastered_skills_from_diagnostic_tests,
    analyze_competency_gaps,
)
from scripts.seed_tt09 import MAJORS_DATA, SUBJECT_BLOCKS_DATA, SKILLS_DATA


# =========================================================================
# 1. PILLAR 1: RIASEC HOLLAND COSINE SIMILARITY TESTS
# =========================================================================

class TestRIASECCosineSimilarity:
    def test_identical_vectors_return_one(self):
        vec = {"R": 0.8, "I": 0.9, "A": 0.4, "S": 0.3, "E": 0.5, "C": 0.6}
        score = calculate_riasec_cosine_similarity(vec, vec)
        assert pytest.approx(score, rel=1e-5) == 1.0

    def test_orthogonal_vectors_return_zero(self):
        vec_s = {"R": 1.0, "I": 0.0, "A": 0.0, "S": 0.0, "E": 0.0, "C": 0.0}
        vec_m = {"R": 0.0, "I": 1.0, "A": 0.0, "S": 0.0, "E": 0.0, "C": 0.0}
        score = calculate_riasec_cosine_similarity(vec_s, vec_m)
        assert score == 0.0

    def test_known_mathematical_similarity(self):
        # s = [1, 2, 0, 0, 0, 0], m = [2, 1, 0, 0, 0, 0]
        # dot = 2 + 2 = 4, ||s|| = sqrt(5), ||m|| = sqrt(5), sim = 4/5 = 0.80
        vec_s = {"R": 1.0, "I": 2.0, "A": 0.0, "S": 0.0, "E": 0.0, "C": 0.0}
        vec_m = {"R": 2.0, "I": 1.0, "A": 0.0, "S": 0.0, "E": 0.0, "C": 0.0}
        score = calculate_riasec_cosine_similarity(vec_s, vec_m)
        assert pytest.approx(score, rel=1e-5) == 0.80

    def test_zero_vector_student_handled_safely(self):
        vec_s = {"R": 0.0, "I": 0.0, "A": 0.0, "S": 0.0, "E": 0.0, "C": 0.0}
        vec_m = {"R": 0.8, "I": 0.9, "A": 0.4, "S": 0.3, "E": 0.5, "C": 0.6}
        score = calculate_riasec_cosine_similarity(vec_s, vec_m)
        assert score == 0.0

    def test_zero_vector_major_handled_safely(self):
        vec_s = {"R": 0.8, "I": 0.9, "A": 0.4, "S": 0.3, "E": 0.5, "C": 0.6}
        vec_m = {"R": 0.0, "I": 0.0, "A": 0.0, "S": 0.0, "E": 0.0, "C": 0.0}
        score = calculate_riasec_cosine_similarity(vec_s, vec_m)
        assert score == 0.0

    def test_empty_vectors_return_zero(self):
        assert calculate_riasec_cosine_similarity({}, {}) == 0.0
        assert calculate_riasec_cosine_similarity({"R": 0.5}, {}) == 0.0
        assert calculate_riasec_cosine_similarity({}, {"R": 0.5}) == 0.0

    def test_negative_values_clamped_to_zero(self):
        vec_s = {"R": -1.0, "I": 0.9, "A": 0.0, "S": 0.0, "E": 0.0, "C": 0.0}
        vec_m = {"R": 1.0, "I": 0.9, "A": 0.0, "S": 0.0, "E": 0.0, "C": 0.0}
        score = calculate_riasec_cosine_similarity(vec_s, vec_m)
        assert 0.0 <= score <= 1.0


# =========================================================================
# 2. PILLAR 2: ACADEMIC Z-SCORE & CDF NORMALIZATION TESTS
# =========================================================================

class TestAcademicReadinessZScore:
    def test_normal_cdf_at_mean_is_half(self):
        assert pytest.approx(normal_cdf(0.0), rel=1e-5) == 0.50

    def test_normal_cdf_at_one_std_dev(self):
        assert pytest.approx(normal_cdf(1.0), abs=1e-3) == 0.8413

    def test_normal_cdf_at_two_std_dev(self):
        assert pytest.approx(normal_cdf(2.0), abs=1e-3) == 0.9772

    def test_normal_cdf_nan_fallback(self):
        assert normal_cdf(float("nan")) == 0.5

    def test_z_score_calculation(self):
        z, cdf = calculate_z_score_and_cdf(24.10, 20.85, 3.25)
        assert pytest.approx(z, abs=1e-2) == 1.0
        assert pytest.approx(cdf, abs=1e-2) == 0.8413

    def test_z_score_zero_or_negative_sigma_handled_safely(self):
        z, cdf = calculate_z_score_and_cdf(25.0, 20.0, 0.0)
        assert z == 5.0
        assert cdf == 1.0

        z_neg, _ = calculate_z_score_and_cdf(25.0, 20.0, -2.0)
        assert z_neg == 5.0

    def test_evaluate_academic_readiness_best_block_selection(self):
        admitted_blocks = ["A00", "A01", "D01"]
        student_results = {
            "A00": {"score_academic": 0.85, "z_score": 1.05, "raw_sum": 24.0},
            "A01": {"score_academic": 0.92, "z_score": 1.40, "raw_sum": 24.5},
            "B00": {"score_academic": 0.99, "z_score": 2.50, "raw_sum": 28.0}
        }
        score, best_block, breakdown = evaluate_academic_readiness_for_major(
            admitted_blocks, student_results
        )
        assert score == 0.92
        assert best_block == "A01"
        assert "A00" in breakdown
        assert "A01" in breakdown
        assert "B00" not in breakdown

    def test_evaluate_academic_readiness_no_overlap_returns_default(self):
        admitted_blocks = ["C00", "D14"]
        student_results = {
            "A00": {"score_academic": 0.85, "z_score": 1.05, "raw_sum": 24.0}
        }
        score, best_block, breakdown = evaluate_academic_readiness_for_major(
            admitted_blocks, student_results, default_score=0.5
        )
        assert score == 0.5
        assert best_block == "C00"
        assert breakdown["status"] == "NO_ADMITTED_BLOCK_MATCH"

    def test_evaluate_academic_readiness_empty_inputs(self):
        score, block, _ = evaluate_academic_readiness_for_major([], {})
        assert score == 0.5
        assert block is None

        score2, block2, _ = evaluate_academic_readiness_for_major(["A00"], {})
        assert score2 == 0.5
        assert block2 == "A00"


# =========================================================================
# 3. PILLAR 3: COGNITIVE PREFERENCE MATCHING TESTS
# =========================================================================

class TestCognitivePreferenceMatching:
    def test_exact_matches_yield_perfect_score(self):
        traits = {
            "abstract_thinking": "high",
            "analytical_reasoning": "high",
            "spatial_perception": "medium",
            "linguistic_ability": "low",
            "learning_environment": "structured",
            "teamwork_intensity": "balanced"
        }
        score = calculate_cognitive_preference_match(traits, traits)
        assert pytest.approx(score, rel=1e-5) == 1.0

    def test_adjacent_matches_yield_partial_score(self):
        student_traits = {
            "abstract_thinking": "high",
            "analytical_reasoning": "high",
            "spatial_perception": "high",
            "linguistic_ability": "high",
            "learning_environment": "structured",
            "teamwork_intensity": "balanced"
        }
        major_attr = {
            "abstract_thinking": "medium",
            "analytical_reasoning": "medium",
            "spatial_perception": "medium",
            "linguistic_ability": "medium",
            "learning_environment": "structured",
            "teamwork_intensity": "balanced"
        }
        score = calculate_cognitive_preference_match(student_traits, major_attr)
        assert pytest.approx(score, abs=1e-2) == 0.6667

    def test_opposite_matches_yield_zero_for_trait(self):
        student_traits = {
            "abstract_thinking": "high",
            "analytical_reasoning": "high",
            "spatial_perception": "high",
            "linguistic_ability": "high",
            "learning_environment": "structured",
            "teamwork_intensity": "independent"
        }
        major_attr = {
            "abstract_thinking": "low",
            "analytical_reasoning": "low",
            "spatial_perception": "low",
            "linguistic_ability": "low",
            "learning_environment": "collaborative",
            "teamwork_intensity": "highly_collaborative"
        }
        score = calculate_cognitive_preference_match(student_traits, major_attr)
        assert score <= 0.10

    def test_empty_or_none_inputs_handled_safely(self):
        assert calculate_cognitive_preference_match({}, {}) == 0.5
        assert calculate_cognitive_preference_match({"abstract_thinking": "high"}, {}) == 0.5
        assert pytest.approx(calculate_cognitive_preference_match(None, {"abstract_thinking": "high"}), abs=1e-2) == 0.9167

    def test_compatible_learning_environments(self):
        # exploratory vs collaborative
        s = {"learning_environment": "collaborative"}
        m = {"learning_environment": "exploratory"}
        score = calculate_cognitive_preference_match(s, m)
        assert 0.0 < score < 1.0


# =========================================================================
# 4. HOLISTIC 3-PILLAR HYBRID MODEL TESTS
# =========================================================================

class TestThreePillarHybridModel:
    def test_default_weights_combination(self):
        score, weights = calculate_3pillar_hybrid_score(1.0, 1.0, 1.0)
        assert pytest.approx(score, rel=1e-5) == 1.0
        assert weights["w_riasec"] == 0.45
        assert weights["w_academic"] == 0.35
        assert weights["w_preference"] == 0.20

    def test_zero_scores_yield_zero(self):
        score, _ = calculate_3pillar_hybrid_score(0.0, 0.0, 0.0)
        assert score == 0.0

    def test_formula_proportionality(self):
        score, _ = calculate_3pillar_hybrid_score(0.8, 0.6, 0.9)
        assert pytest.approx(score, abs=1e-4) == 0.75

    def test_custom_weights_auto_normalization(self):
        score, weights = calculate_3pillar_hybrid_score(
            0.8, 0.6, 0.9, w_riasec=45.0, w_academic=35.0, w_preference=20.0
        )
        assert pytest.approx(score, abs=1e-4) == 0.75
        assert pytest.approx(weights["w_riasec"] + weights["w_academic"] + weights["w_preference"], rel=1e-5) == 1.0

    def test_zero_total_weights_handled_safely(self):
        score, weights = calculate_3pillar_hybrid_score(
            0.8, 0.6, 0.9, w_riasec=0.0, w_academic=0.0, w_preference=0.0
        )
        assert 0.0 <= score <= 1.0


# =========================================================================
# 5. XAI EXPLANATION GENERATION TESTS
# =========================================================================

class TestXAIExplanationGeneration:
    def test_xai_factors_high_fit_with_dim_overlap(self):
        factors, expl = generate_xai_top_supporting_factors(
            major_name="Công nghệ thông tin",
            score_riasec=0.92,
            student_riasec={"R": 0.8, "I": 0.9, "A": 0.2, "S": 0.3, "E": 0.4, "C": 0.5},
            major_riasec={"R": 0.5, "I": 0.9, "A": 0.2, "S": 0.3, "E": 0.4, "C": 0.6},
            score_academic=0.88,
            best_block="A00",
            score_pref=0.90,
            student_pref={"learning_environment": "structured"},
            major_attr={"learning_environment": "structured"}
        )
        assert len(factors) >= 2
        assert "Công nghệ thông tin" in expl
        assert "A00" in expl
        assert any("Sở thích nghề nghiệp xuất sắc" in f for f in factors)
        assert any("học thuật" in f for f in factors)

    def test_xai_factors_high_fit_without_dim_overlap(self):
        factors, _ = generate_xai_top_supporting_factors(
            major_name="Kinh tế",
            score_riasec=0.76,
            student_riasec={"R": 0.6, "I": 0.6, "A": 0.1, "S": 0.1, "E": 0.5, "C": 0.5},
            major_riasec={"R": 0.1, "I": 0.1, "A": 0.1, "S": 0.1, "E": 0.9, "C": 0.9},
            score_academic=0.60,
            best_block="D01",
            score_pref=0.75,
            student_pref={"learning_environment": "exploratory"},
            major_attr={"learning_environment": "structured"}
        )
        assert any("phù hợp cao" in f for f in factors)
        assert any("Độ thích ứng phong cách tư duy" in f for f in factors)

    def test_xai_factors_medium_riasec_fit(self):
        factors, _ = generate_xai_top_supporting_factors(
            major_name="Quản trị",
            score_riasec=0.55,
            student_riasec={"R": 0.5, "I": 0.5, "A": 0.5, "S": 0.5, "E": 0.5, "C": 0.5},
            major_riasec={"R": 0.1, "I": 0.2, "A": 0.3, "S": 0.4, "E": 0.9, "C": 0.6},
            score_academic=0.55,
            best_block="A01",
            score_pref=0.50,
            student_pref={},
            major_attr={}
        )
        assert any("mức trung bình khá" in f for f in factors)

    def test_xai_factors_low_academic_warning(self):
        factors, _ = generate_xai_top_supporting_factors(
            major_name="Y khoa",
            score_riasec=0.40,
            student_riasec={"R": 0.2, "I": 0.9, "A": 0.2, "S": 0.8, "E": 0.4, "C": 0.5},
            major_riasec={"R": 0.5, "I": 0.9, "A": 0.2, "S": 0.9, "E": 0.4, "C": 0.7},
            score_academic=0.35,
            best_block="B00",
            score_pref=0.60,
            student_pref={},
            major_attr={}
        )
        assert any("cần bổ sung" in f.lower() for f in factors)


# =========================================================================
# 6. COMPETENCY GAP ANALYSIS ENGINE TESTS
# =========================================================================

class TestCompetencyGapEngine:
    def test_infer_skills_from_high_grades(self):
        grades = {"Toán": 8.5, "Vật lí": 8.0, "Tiếng Anh": 8.0}
        mastered = infer_mastered_skills_from_grades(grades)
        assert "SKILL_PRE_CALCULUS" in mastered
        assert "SKILL_PRE_LOGIC_DISCRETE" in mastered
        assert "SKILL_PRE_PHYSICS_MECH" in mastered
        assert "SKILL_PRE_ENG_ACADEMIC" in mastered

    def test_infer_skills_from_low_grades(self):
        grades = {"Toán": 6.0, "Vật lí": 6.5}
        mastered = infer_mastered_skills_from_grades(grades)
        assert len(mastered) == 0

    def test_infer_skills_from_empty_grades(self):
        assert len(infer_mastered_skills_from_grades({})) == 0
        assert len(infer_mastered_skills_from_grades(None)) == 0

    def test_infer_skills_from_diagnostic_tests(self):
        diag_tests = [
            {"skill_code": "SKILL_TAR_PROG_PYTHON", "score": 8.5, "is_passed": True},
            {"skill_code": "SKILL_TAR_ALGORITHMS", "score": 0.80, "is_passed": False},
            {"skill_code": "SKILL_TAR_DATA_MODELING", "score": 4.0, "is_passed": False},
            {"skill_code": "", "score": 9.0, "is_passed": True}  # Empty code
        ]
        mastered = infer_mastered_skills_from_diagnostic_tests(diag_tests)
        assert "SKILL_TAR_PROG_PYTHON" in mastered
        assert "SKILL_TAR_ALGORITHMS" in mastered
        assert "SKILL_TAR_DATA_MODELING" not in mastered
        assert "" not in mastered

    def test_infer_skills_from_empty_diagnostic_tests(self):
        assert len(infer_mastered_skills_from_diagnostic_tests([])) == 0
        assert len(infer_mastered_skills_from_diagnostic_tests(None)) == 0

    def test_gap_analysis_prerequisite_chain_detection(self):
        required_skills = [
            {"skill_code": "SKILL_TAR_PROG_PYTHON", "name": "Lập trình Python", "skill_type": "TARGET", "importance": "MANDATORY"},
            {"skill_code": "SKILL_TAR_PROG_PYTHON", "name": "Lập trình Python", "skill_type": "TARGET", "importance": "MANDATORY"}  # Duplicate
        ]
        prereq_map = {
            "SKILL_TAR_PROG_PYTHON": ["SKILL_PRE_LOGIC_DISCRETE"]
        }
        mastered = set()
        overall, missing_pre, missing_tar = analyze_competency_gaps(
            required_skills, prereq_map, mastered
        )
        assert "SKILL_PRE_LOGIC_DISCRETE" in missing_pre
        assert "Lập trình Python" in missing_tar
        assert len(overall) == 2

    def test_gap_analysis_prerequisite_skill_type(self):
        required_skills = [
            {"skill_code": "SKILL_PRE_CALCULUS", "name": "Giải tích căn bản", "skill_type": "PREREQUISITE", "importance": "MANDATORY"}
        ]
        mastered = set()
        overall, missing_pre, missing_tar = analyze_competency_gaps(
            required_skills, {}, mastered
        )
        assert "Giải tích căn bản" in missing_pre
        assert len(missing_tar) == 0
        assert any("Tiên quyết" in g for g in overall)

    def test_gap_analysis_prerequisite_satisfied(self):
        required_skills = [
            {"skill_code": "SKILL_TAR_PROG_PYTHON", "name": "Lập trình Python", "skill_type": "TARGET", "importance": "MANDATORY"}
        ]
        prereq_map = {
            "SKILL_TAR_PROG_PYTHON": ["SKILL_PRE_LOGIC_DISCRETE"]
        }
        mastered = {"SKILL_PRE_LOGIC_DISCRETE"}
        overall, missing_pre, missing_tar = analyze_competency_gaps(
            required_skills, prereq_map, mastered
        )
        assert len(missing_pre) == 0
        assert "Lập trình Python" in missing_tar


# =========================================================================
# 7. DETERMINISM VERIFICATION (NFR04)
# =========================================================================

class TestDeterminismGuarantee:
    def test_100_repeated_runs_yield_identical_results(self):
        student_riasec = {"R": 0.75, "I": 0.90, "A": 0.20, "S": 0.30, "E": 0.40, "C": 0.60}
        student_pref = {"abstract_thinking": "high", "learning_environment": "structured"}

        major_a_riasec = {"R": 0.50, "I": 0.90, "A": 0.30, "S": 0.30, "E": 0.50, "C": 0.70}
        major_a_attr = {"abstract_thinking": "high", "learning_environment": "structured"}

        first_sim = calculate_riasec_cosine_similarity(student_riasec, major_a_riasec)
        first_pref = calculate_cognitive_preference_match(student_pref, major_a_attr)
        first_score, _ = calculate_3pillar_hybrid_score(first_sim, 0.85, first_pref)

        for _ in range(100):
            sim = calculate_riasec_cosine_similarity(student_riasec, major_a_riasec)
            pref = calculate_cognitive_preference_match(student_pref, major_a_attr)
            score, _ = calculate_3pillar_hybrid_score(sim, 0.85, pref)

            assert sim == first_sim, "Non-deterministic RIASEC similarity!"
            assert pref == first_pref, "Non-deterministic Cognitive match!"
            assert score == first_score, "Non-deterministic Holistic Hybrid score!"


# =========================================================================
# 8. PERFORMANCE BENCHMARK (NFR01 - <= 2 SECONDS FOR >= 80 MAJORS)
# =========================================================================

class TestPerformanceBenchmark:
    def test_scoring_over_100_majors_under_2_seconds(self):
        assert len(MAJORS_DATA) >= 80, f"Catalog must contain >= 80 majors, got {len(MAJORS_DATA)}"

        student_riasec = {"R": 0.75, "I": 0.85, "A": 0.40, "S": 0.50, "E": 0.60, "C": 0.70}
        student_pref = {"abstract_thinking": "high", "learning_environment": "structured", "teamwork_intensity": "balanced"}
        student_block_results = {
            "A00": {"score_academic": 0.85, "z_score": 1.05, "raw_sum": 24.0},
            "A01": {"score_academic": 0.88, "z_score": 1.15, "raw_sum": 24.2},
            "D01": {"score_academic": 0.78, "z_score": 0.75, "raw_sum": 21.5}
        }

        start_time = time.perf_counter()

        scored_majors = []
        for m in MAJORS_DATA:
            sim = calculate_riasec_cosine_similarity(student_riasec, m["riasec"])
            acad_score, best_block, _ = evaluate_academic_readiness_for_major(
                m.get("blocks", []), student_block_results
            )
            pref_score = calculate_cognitive_preference_match(student_pref, m["cognitive"])
            total_score, _ = calculate_3pillar_hybrid_score(sim, acad_score, pref_score)
            factors, expl = generate_xai_top_supporting_factors(
                major_name=m["name"],
                score_riasec=sim,
                student_riasec=student_riasec,
                major_riasec=m["riasec"],
                score_academic=acad_score,
                best_block=best_block,
                score_pref=pref_score,
                student_pref=student_pref,
                major_attr=m["cognitive"]
            )
            scored_majors.append((m["major_code"], total_score, factors))

        # Sort descending
        scored_majors.sort(key=lambda x: x[1], reverse=True)

        elapsed_time = time.perf_counter() - start_time
        print(f"\n[BENCHMARK] Evaluated {len(MAJORS_DATA)} majors in {elapsed_time * 1000.0:.2f}ms.")

        assert elapsed_time < 2.0, f"Scoring exceeded 2.0s limit: took {elapsed_time:.3f}s"
        assert len(scored_majors) == len(MAJORS_DATA)
        assert scored_majors[0][1] >= scored_majors[-1][1], "Sorting must be descending"


# =========================================================================
# 9. ENHANCED 3-PILLAR, HARD CUTOFF SUBSTITUTION & TT74 EXCEL IMPORTER TESTS
# =========================================================================

class TestEnhancedThreePillarAndImporter:
    def test_enhanced_riasec_fit_and_flat_profile_dampening(self):
        from app.services.recommender.engine import calculate_enhanced_riasec_fit

        focused_student = {"R": 0.85, "I": 0.95, "A": 0.15, "S": 0.20, "E": 0.25, "C": 0.40}
        flat_student = {"R": 0.50, "I": 0.50, "A": 0.50, "S": 0.50, "E": 0.50, "C": 0.50}
        cs_major = {"R": 0.80, "I": 0.95, "A": 0.20, "S": 0.25, "E": 0.30, "C": 0.65}

        score_focused = calculate_enhanced_riasec_fit(focused_student, cs_major)
        score_flat = calculate_enhanced_riasec_fit(flat_student, cs_major)
        assert score_focused > 0.90
        assert score_flat < score_focused

    def test_target_anchored_academic_fit_and_hard_cutoff(self):
        from app.services.recommender.engine import evaluate_target_anchored_academic_fit

        student_low = {
            "A00": {"score_academic": 0.45, "z_score": -0.2, "raw_sum": 20.5},
        }
        score_high, _, bd_high = evaluate_target_anchored_academic_fit(
            ["A00"], student_low, benchmark_cutoff=27.5, min_recommended=25.0
        )
        score_low, _, bd_low = evaluate_target_anchored_academic_fit(
            ["A00"], student_low, benchmark_cutoff=21.0, min_recommended=19.5
        )
        assert bd_high["safety_tier"] == "REACH"
        assert bd_low["safety_tier"] == "TARGET"
        assert score_low > score_high

    def test_asymmetric_cognitive_overqualification_is_not_penalized(self):
        from app.services.recommender.engine import calculate_asymmetric_cognitive_fit

        high_student = {
            "abstract_thinking": "high",
            "analytical_reasoning": "high",
            "spatial_perception": "high",
            "linguistic_ability": "high",
            "learning_environment": "structured",
            "teamwork_intensity": "balanced",
        }
        medium_major = {
            "abstract_thinking": "medium",
            "analytical_reasoning": "medium",
            "spatial_perception": "low",
            "linguistic_ability": "medium",
            "learning_environment": "structured",
            "teamwork_intensity": "balanced",
        }
        score = calculate_asymmetric_cognitive_fit(high_student, medium_major)
        assert pytest.approx(score, rel=1e-4) == 1.0

    def test_related_pathway_substitution_matching(self):
        from app.services.recommender.engine import are_majors_related_pathway

        # Same 4-digit group: Khoa học máy tính (7480101) vs Hệ thống thông tin (7480104)
        assert are_majors_related_pathway("7480101", "7480104") == 3
        # Engineering (52) -> Engineering Tech (51)
        assert are_majors_related_pathway("7520201", "7510301") == 2
        # Medical (720101) -> Medical Lab Tech (720601)
        assert are_majors_related_pathway("720101", "720601") >= 1
        # Unrelated: Khoa học máy tính (7480101) vs Hội họa (7210103)
        assert are_majors_related_pathway("7480101", "7210103") == 0

    def test_tt74_excel_auto_cip_and_riasec_enrichment(self):
        import importlib.util
        from pathlib import Path

        ref_path = (
            Path(__file__).resolve().parents[1]
            / "app"
            / "services"
            / "taxonomy"
            / "tt74_reference.py"
        )
        spec = importlib.util.spec_from_file_location("tt74_reference", ref_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Minimal input with only major_code & major_name
        enriched = mod.auto_enrich_major_record({
            "major_code": "480101",
            "major_name": "Khoa học máy tính",
        })
        assert enriched["field_code"] == "48"
        assert enriched["group_code"] == "4801"
        assert enriched["cip_code"].startswith("11.07")
        assert enriched["holland_code"] == "IRC"
        assert enriched["riasec_vector"]["I"] >= 0.90

        template_path = (
            Path(__file__).resolve().parents[1]
            / "app"
            / "db"
            / "seeds"
            / "MOET_Major_Import_Template_Standard.xlsx"
        )
        assert template_path.exists()
        parsed = mod.parse_excel_or_csv_majors(
            template_path.read_bytes(), template_path.name
        )
        assert len(parsed) >= 2
        assert all("cip_code" in m and "riasec_vector" in m for m in parsed)

    def test_cognitive_8_question_mapper_to_pillar3(self):
        from app.services.recommender.engine import (
            normalize_student_cognitive_traits,
            calculate_asymmetric_cognitive_fit,
        )

        # Student selecting strong analytical/STEM options across COG_1..COG_8
        raw_cog = {
            "COG_1": "B",  # LEARN_THEORETICAL_ANALYTICAL
            "COG_2": "A",  # ENV_LAB_DIGITAL_QUIET
            "COG_3": "A",  # SOLVE_QUANTITATIVE_LOGIC
            "COG_4": "A",  # TARGET_SYSTEMS_MACHINES
            "COG_5": "A",  # GARDNER_LOGICAL_MATH
            "COG_6": "C",  # PRESSURE_DEEP_RND_COMPLEXITY
            "COG_7": "A",  # OUTPUT_TANGIBLE_TECH_SYSTEM
            "COG_8": "A",  # ROLE_TECHNICAL_SPECIALIST
        }
        mapped = normalize_student_cognitive_traits(raw_cog)
        assert mapped["analytical_reasoning"] == "high"
        assert mapped["abstract_thinking"] == "high"
        assert mapped["spatial_perception"] in ("medium", "high")
        assert mapped["learning_environment"] == "independent"
        assert mapped["teamwork_intensity"] == "independent"

        cs_major_attr = {
            "abstract_thinking": "high",
            "analytical_reasoning": "high",
            "spatial_perception": "medium",
            "linguistic_ability": "medium",
            "learning_environment": "independent",
            "teamwork_intensity": "independent",
        }
        fit_score = calculate_asymmetric_cognitive_fit(raw_cog, cs_major_attr)
        assert fit_score >= 0.85


# =========================================================================
# 9. MULTI-LAYER SCORE CONSTRAINTS & SUBJECT SPELLING NORMALIZATION TESTS
# =========================================================================

class TestScoreConstraintsAndNormalization:
    def test_subject_spelling_normalization_physics_geography(self):
        from app.services.recommender.engine import compute_block_zscores_from_grades

        grades_fe = {
            "Toán": 8.5,
            "Vật lý": 8.0,
            "Hóa học": 7.5,
            "Ngữ văn": 7.0,
            "Lịch sử": 7.5,
            "Địa lý": 8.0,
            "Tiếng Anh": 8.0,
        }
        grades_db_spelling = {
            "Toán": 8.5,
            "Vật lí": 8.0,
            "Hóa học": 7.5,
            "Ngữ văn": 7.0,
            "Lịch sử": 7.5,
            "Địa lí": 8.0,
            "Tiếng Anh": 8.0,
        }
        blocks_fe = compute_block_zscores_from_grades(grades_fe)
        blocks_db = compute_block_zscores_from_grades(grades_db_spelling)

        assert blocks_fe["A00"]["raw_sum"] == pytest.approx(24.0, abs=1e-2)
        assert blocks_fe["A01"]["raw_sum"] == pytest.approx(24.5, abs=1e-2)
        assert blocks_fe["C00"]["raw_sum"] == pytest.approx(22.5, abs=1e-2)
        assert blocks_fe["D15"]["raw_sum"] == pytest.approx(23.0, abs=1e-2)
        assert blocks_fe["A00"]["raw_sum"] == blocks_db["A00"]["raw_sum"]
        assert blocks_fe["C00"]["raw_sum"] == blocks_db["C00"]["raw_sum"]

    def test_failing_grade_and_prerequisite_subject_constraints(self):
        from app.services.recommender.engine import (
            compute_block_zscores_from_grades,
            evaluate_target_anchored_academic_fit,
            evaluate_admission_feasibility,
        )

        # Trường hợp 1: Vướng điểm liệt Toán = 1.0đ dù Hóa/Sinh 9.5đ -> tổng 20.0đ
        grades_failing = {"Toán": 1.0, "Hóa học": 9.5, "Sinh học": 9.5}
        zblocks = compute_block_zscores_from_grades(grades_failing)
        acad_score, best_blk, bd = evaluate_target_anchored_academic_fit(
            ["B00"],
            zblocks,
            benchmark_cutoff=18.0,
            min_recommended=15.5,
            raw_grades=grades_failing,
            major_code="7420201",
            major_name="Công nghệ sinh học",
        )
        assert bd["safety_tier"] == "REACH"
        assert acad_score <= 0.28

        feas = evaluate_admission_feasibility(
            raw_block_sum=zblocks["B00"]["raw_sum"],
            major_code="7420201",
            major_name="Công nghệ sinh học",
            best_block=best_blk,
            raw_grades=grades_failing,
            block_subjects=zblocks["B00"]["subjects_used"],
        )
        assert feas["feasibility_tier"] == "REACH"
        assert feas["constraint_passed"] is False
        assert any("điểm liệt" in v.lower() for v in feas["constraint_violations"])

        # Trường hợp 2: Tổng D01 = 23.5đ nhưng Toán chỉ 4.5đ -> bị chặn với Khoa học máy tính
        grades_weak_math = {"Toán": 4.5, "Ngữ văn": 9.5, "Tiếng Anh": 9.5}
        zblocks_math = compute_block_zscores_from_grades(grades_weak_math)
        feas_cs = evaluate_admission_feasibility(
            raw_block_sum=zblocks_math["D01"]["raw_sum"],
            major_code="7480101",
            major_name="Khoa học máy tính",
            best_block="D01",
            raw_grades=grades_weak_math,
            block_subjects=zblocks_math["D01"]["subjects_used"],
        )
        assert feas_cs["feasibility_tier"] == "REACH"
        assert feas_cs["constraint_passed"] is False
        assert any("Toán" in v for v in feas_cs["constraint_violations"])

    def test_no_cross_block_substitution_abuse(self):
        from app.services.recommender.engine import (
            compute_block_zscores_from_grades,
            evaluate_target_anchored_academic_fit,
            evaluate_admission_feasibility,
        )

        # Học sinh chỉ nhập 3 môn khối C00 đạt 27.0đ
        grades_c00_only = {"Ngữ văn": 9.0, "Lịch sử": 9.0, "Địa lý": 9.0}
        zblocks = compute_block_zscores_from_grades(grades_c00_only)

        # Ngành Y khoa chỉ xét B00 / A00 -> KHÔNG được lấy điểm 27.0đ của C00 thay thế
        acad_score, _, bd = evaluate_target_anchored_academic_fit(
            ["B00", "A00"],
            zblocks,
            benchmark_cutoff=25.5,
            min_recommended=23.5,
            raw_grades=grades_c00_only,
            major_code="7720101",
            major_name="Y khoa",
        )
        assert bd["has_matched_block"] is False
        assert bd["cross_block_blocked"] is True
        assert bd["safety_tier"] == "REACH"
        assert acad_score <= 0.20

        feas = evaluate_admission_feasibility(
            raw_block_sum=None,
            major_code="7720101",
            major_name="Y khoa",
            has_matched_block=False,
            admitted_blocks=["B00", "A00"],
        )
        assert feas["feasibility_tier"] == "REACH"
        assert feas["constraint_passed"] is False
        assert feas["best_block_score"] is None

    def test_evaluate_endpoint_422_unassessed_and_435_majors_eval(self):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import get_db

        async def _override_get_db_none():
            yield None

        app.dependency_overrides[get_db] = _override_get_db_none
        try:
            client = TestClient(app)

            # 1) Chưa làm bài test -> 422 CHUA_HOAN_THANH_BAI_TEST
            res_empty = client.post("/api/v1/recommender/evaluate", json={})
            assert res_empty.status_code == 422
            assert res_empty.json()["detail"]["code"] == "CHUA_HOAN_THANH_BAI_TEST"

            # 2) Đầy đủ 30 câu RIASEC + 8 Nhận thức + Điểm số (Vật lý / Địa lý)
            res_ok = client.post(
                "/api/v1/recommender/evaluate",
                json={
                    "riasec_answers": {
                        "I1": 5, "I2": 5, "I3": 5, "I4": 5, "I5": 5,
                        "R1": 4, "R2": 4, "R3": 4, "R4": 4, "R5": 4,
                        "A1": 2, "S1": 2, "E1": 2, "C1": 3,
                    },
                    "cognitive_answers": {"COG_1": "B", "COG_3": "A", "COG_5": "A"},
                    "grades_by_subject": {
                        "Toán": 6.0,
                        "Vật lý": 6.0,
                        "Hóa học": 6.0,
                        "Ngữ văn": 6.5,
                        "Tiếng Anh": 6.5,
                    },
                    "top_k": 435,
                },
            )
            assert res_ok.status_code == 200
            body = res_ok.json()
            assert body["total_majors_evaluated"] >= 400
            assert body["bestBlockStats"]["raw_sum"] == pytest.approx(19.0, abs=1e-2)
            assert len(body["funnel"]["tier1_fields"]) == 3

            # Kiểm tra Khoa học máy tính (chuẩn ~25.5đ / min 23.5đ) bị chặn REACH với điểm ~19đ
            cs_item = next(
                (m for m in body["majors"] if m["major_code"] in ("7480101", "480101")),
                None,
            )
            assert cs_item is not None
            assert cs_item["feasibility_tier"] == "REACH"
            assert cs_item["constraint_passed"] is False
            assert len(cs_item["constraint_violations"]) >= 1
        finally:
            app.dependency_overrides.clear()


