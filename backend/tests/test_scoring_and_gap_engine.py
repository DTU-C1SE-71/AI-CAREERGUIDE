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
    compute_adaptive_weights,
    build_compact_xai_explanation,
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


# =========================================================================
# 10. AI CAREER ASPIRATION & PSYCHOMETRIC ALIGNMENT AGENT TESTS
# =========================================================================

class TestCareerAspirationAgent:
    def test_aspiration_aligned_and_eligible(self):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import get_db

        async def _override_get_db_none():
            yield None

        app.dependency_overrides[get_db] = _override_get_db_none
        try:
            client = TestClient(app)
            res = client.post(
                "/api/v1/recommender/evaluate",
                json={
                    "riasec_answers": {
                        "I1": 5, "I2": 5, "I3": 5, "I4": 5, "I5": 5,
                        "R1": 4, "R2": 4, "R3": 4, "R4": 4, "R5": 4,
                        "C1": 4, "C2": 4, "A1": 1, "S1": 2, "E1": 2,
                    },
                    "cognitive_answers": {"COG_1": "B", "COG_3": "A", "COG_5": "A"},
                    "grades_by_subject": {
                        "Toán": 9.0,
                        "Vật lý": 8.6,
                        "Hóa học": 8.2,
                        "Tiếng Anh": 8.5,
                        "Ngữ văn": 7.5,
                    },
                    "aspiration": {
                        "dream_job": "Kỹ sư Trí tuệ nhân tạo & Lập trình phần mềm",
                        "desired_field": "Máy tính và công nghệ thông tin",
                        "work_values": ["TECH_INNOVATION"],
                        "score_strategy": "FLEXIBLE_PATHWAY",
                    },
                    "top_k": 435,
                },
            )
            assert res.status_code == 200
            asp = res.json()["aspirationAnalysis"]
            assert asp["has_aspiration"] is True
            assert asp["alignment_status"] == "ALIGNED_AND_ELIGIBLE"
            assert asp["dream_majors"][0]["feasibility_tier"] == "TARGET"
            assert any(
                k in asp["dream_majors"][0]["major_name"].lower()
                for k in ("trí tuệ", "phần mềm", "khoa học máy tính", "công nghệ thông tin")
            )
        finally:
            app.dependency_overrides.clear()

    def test_aspiration_passion_match_with_score_gap_substitutes_safe_major(self):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import get_db

        async def _override_get_db_none():
            yield None

        app.dependency_overrides[get_db] = _override_get_db_none
        try:
            client = TestClient(app)
            res = client.post(
                "/api/v1/recommender/analyze-aspiration",
                json={
                    "riasec_answers": {
                        "I1": 5, "I2": 5, "I3": 5, "I4": 5, "I5": 5,
                        "S1": 4, "S2": 4, "S3": 4, "R1": 4, "R2": 4,
                        "A1": 1, "E1": 2, "C1": 3,
                    },
                    "cognitive_answers": {"COG_1": "B", "COG_3": "A", "COG_7": "C"},
                    "grades_by_subject": {
                        "Toán": 6.4,
                        "Hóa học": 6.2,
                        "Sinh học": 6.4,
                        "Ngữ văn": 6.5,
                        "Tiếng Anh": 6.5,
                    },
                    "aspiration": {
                        "dream_job": "Bác sĩ Y khoa",
                        "work_values": ["SOCIAL_IMPACT"],
                        "score_strategy": "FLEXIBLE_PATHWAY",
                    },
                    "top_k": 435,
                },
            )
            assert res.status_code == 200
            asp = res.json()
            assert asp["alignment_status"] == "PASSION_MATCH_SCORE_GAP"
            assert asp["dream_majors"][0]["feasibility_tier"] == "REACH"
            assert len(asp["recommended_substitutes"]) >= 1
            assert asp["recommended_substitutes"][0]["feasibility_tier"] == "TARGET"
        finally:
            app.dependency_overrides.clear()

    def test_aspiration_trait_divergence_and_zero_pii_sanitization(self):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import get_db

        async def _override_get_db_none():
            yield None

        app.dependency_overrides[get_db] = _override_get_db_none
        try:
            client = TestClient(app)
            # Học sinh nổi trội Nghệ thuật (A) - Xã hội (S) (I/R thấp) nhưng nhập muốn làm Kỹ sư Vi mạch
            res = client.post(
                "/api/v1/recommender/analyze-aspiration",
                json={
                    "riasec_answers": {
                        "A1": 5, "A2": 5, "A3": 5, "A4": 5, "A5": 5,
                        "S1": 5, "S2": 5, "S3": 5, "S4": 5, "S5": 5,
                        "E1": 4, "E2": 4, "I1": 1, "I2": 1, "R1": 1, "R2": 1, "C1": 2,
                    },
                    "cognitive_answers": {"COG_1": "D", "COG_3": "B", "COG_5": "B"},
                    "grades_by_subject": {
                        "Toán": 7.5,
                        "Vật lý": 7.0,
                        "Ngữ văn": 8.8,
                        "Tiếng Anh": 8.6,
                    },
                    "aspiration": {
                        "dream_job": "Em tên là Nguyễn Văn A sdt 0912345678 muốn làm Kỹ sư thiết kế vi mạch",
                        "score_strategy": "FLEXIBLE_PATHWAY",
                    },
                    "top_k": 435,
                },
            )
            assert res.status_code == 200
            asp = res.json()
            # Kiểm tra Zero-PII: tên và số điện thoại đã bị khử
            assert "0912345678" not in asp["dream_job"]
            assert "[REDACTED_PHONE]" in asp["dream_job"]
            assert asp["alignment_status"] == "TRAIT_DIVERGENCE"
            assert len(asp["bridge_majors"]) >= 1
            assert asp["bridge_majors"][0]["feasibility_tier"] == "TARGET"
        finally:
            app.dependency_overrides.clear()

    def test_aspiration_exploratory_when_no_dream_job_entered(self):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import get_db

        async def _override_get_db_none():
            yield None

        app.dependency_overrides[get_db] = _override_get_db_none
        try:
            client = TestClient(app)
            res = client.post(
                "/api/v1/recommender/analyze-aspiration",
                json={
                    "riasec_answers": {"E1": 5, "E2": 5, "S1": 4, "C1": 4, "I1": 3, "R1": 2, "A1": 3},
                    "grades_by_subject": {"Toán": 8.0, "Ngữ văn": 7.8, "Tiếng Anh": 8.2},
                    "aspiration": {"dream_job": ""},
                    "top_k": 435,
                },
            )
            assert res.status_code == 200
            asp = res.json()
            assert asp["alignment_status"] == "EXPLORATORY_DISCOVERY"
            assert len(asp["dream_majors"]) >= 1
        finally:
            app.dependency_overrides.clear()

    def test_aspiration_no_grades_returns_need_academic_data_and_unknown_tier(self):
        """Đảm bảo không bịa điểm khi học sinh chưa nhập học bạ."""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import get_db

        async def _override_get_db_none():
            yield None

        app.dependency_overrides[get_db] = _override_get_db_none
        try:
            client = TestClient(app)
            res = client.post(
                "/api/v1/recommender/analyze-aspiration",
                json={
                    "riasec_answers": {"I1": 5, "I2": 5, "R1": 4, "R2": 4, "C1": 3},
                    "grades_by_subject": {},
                    "aspiration": {"dream_job": "Kỹ sư Trí tuệ nhân tạo & Lập trình phần mềm"},
                    "top_k": 435,
                },
            )
            assert res.status_code == 200
            asp = res.json()
            assert asp["alignment_status"] == "NEED_ACADEMIC_DATA"
            assert asp["has_academic_data"] is False
            assert asp["score_basis"] == "RIASEC_ONLY"
            assert asp["dream_majors"][0]["feasibility_tier"] == "UNKNOWN"
            assert "chưa nhập điểm học lực" in asp["agent_verdict"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_aspiration_expanded_career_clusters(self):
        """Kiểm tra các cụm nghề mở rộng: phi công, ca sĩ, đầu bếp, an ninh."""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import get_db

        async def _override_get_db_none():
            yield None

        app.dependency_overrides[get_db] = _override_get_db_none
        try:
            client = TestClient(app)
            # Test phi công hàng không
            res1 = client.post(
                "/api/v1/recommender/analyze-aspiration",
                json={
                    "riasec_answers": {"R1": 5, "I1": 4, "C1": 4},
                    "grades_by_subject": {"Toán": 9.0, "Vật lý": 9.0, "Tiếng Anh": 8.5},
                    "aspiration": {"dream_job": "Phi công lái máy bay dân dụng"},
                    "top_k": 435,
                },
            )
            assert res1.status_code == 200
            majors1 = [m["major_name"].lower() for m in res1.json()["dream_majors"]]
            assert any(k in " ".join(majors1) for k in ("hàng không", "vận tải", "hoạt động bay"))

            # Test ca sĩ thanh nhạc
            res2 = client.post(
                "/api/v1/recommender/analyze-aspiration",
                json={
                    "riasec_answers": {"A1": 5, "A2": 5, "S1": 4},
                    "grades_by_subject": {"Ngữ văn": 8.0},
                    "aspiration": {"dream_job": "Ca sĩ thần tượng thanh nhạc"},
                    "top_k": 435,
                },
            )
            assert res2.status_code == 200
            majors2 = [m["major_name"].lower() for m in res2.json()["dream_majors"]]
            assert any(k in " ".join(majors2) for k in ("thanh nhạc", "âm nhạc", "biểu diễn"))
        finally:
            app.dependency_overrides.clear()


# =========================================================================
# 11. AI TREND HUNTER AGENT & MULTI-TIER PRIORITIZATION TESTS
# =========================================================================

class TestTrendHunterAgent:
    def test_trend_agent_manual_admin_guard_classification_and_recommender_boost(self, monkeypatch):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import get_db
        from app.core.security import create_access_token
        from app.services.taxonomy import trend_agent

        async def _override_get_db_none():
            yield None

        mock_articles = [
            {
                "title": "Thị trường Việt Nam khát nhân lực Trí tuệ nhân tạo AI và Thiết kế vi mạch bán dẫn 2026",
                "url": "https://vnexpress.net/ai-vi-mach-xu-huong-2026",
                "source": "VnExpress",
                "published_at": "2026-11-10",
                "snippet": "Các doanh nghiệp công nghệ săn đón kỹ sư trí tuệ nhân tạo, khoa học dữ liệu và vi mạch bán dẫn.",
            },
            {
                "title": "Top ngành tăng trưởng mạnh: An toàn thông tin, Fintech, Logistics và Thương mại điện tử",
                "url": "https://vietnamnet.vn/top-nganh-tang-truong-2026",
                "source": "VietNamNet",
                "published_at": "2026-11-10",
                "snippet": "Nhu cầu an ninh mạng, công nghệ tài chính, chuỗi cung ứng logistics và kỹ thuật phần mềm tăng cao.",
            },
            {
                "title": "Xu hướng tuyển dụng ổn định cho Điều dưỡng, Tâm lý học và Năng lượng tái tạo",
                "url": "https://tuoitre.vn/tuyen-dung-y-te-tam-ly-2026",
                "source": "Tuổi Trẻ",
                "published_at": "2026-11-10",
                "snippet": "Nhu cầu chăm sóc sức khỏe, tham vấn tâm lý học đường và chuyển dịch năng lượng xanh.",
            },
        ]

        async def _mock_online_search(focus_query: str = ""):
            return mock_articles

        monkeypatch.setattr(trend_agent, "search_trending_majors_online", _mock_online_search)

        app.dependency_overrides[get_db] = _override_get_db_none
        admin_token = create_access_token("00000000-0000-0000-0000-000000000099", role="ADMIN")
        student_token = create_access_token("00000000-0000-0000-0000-000000000002", role="STUDENT")

        try:
            client = TestClient(app)

            # Đảm bảo sạch sẽ trước khi test
            clear_res = client.delete(
                "/api/v1/taxonomy/trend-agent/clear",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert clear_res.status_code == 200

            # 1) Trước khi Admin bấm nút: không có ngành xu hướng nào tự chạy
            status_before = client.get("/api/v1/taxonomy/trend-agent/status")
            assert status_before.status_code == 200
            assert status_before.json()["has_run"] is False
            assert status_before.json()["total_trending_marked"] == 0

            # 2) Guardrail: Không có token (401) hoặc Student token (403) bị chặn tuyệt đối
            unauth_res = client.post("/api/v1/taxonomy/trend-agent/run", json={})
            assert unauth_res.status_code == 401

            student_res = client.post(
                "/api/v1/taxonomy/trend-agent/run",
                json={},
                headers={"Authorization": f"Bearer {student_token}"},
            )
            assert student_res.status_code == 403

            # Đánh giá xếp hạng gốc trước khi có đánh dấu xu hướng
            eval_payload = {
                "riasec_answers": {
                    "I1": 5, "I2": 5, "I3": 5, "I4": 5, "I5": 5,
                    "R1": 4, "R2": 4, "R3": 4, "R4": 4, "R5": 4,
                    "C1": 4, "C2": 4, "A1": 2, "S1": 2, "E1": 3,
                },
                "cognitive_answers": {"COG_1": "B", "COG_3": "A", "COG_5": "A"},
                "grades_by_subject": {
                    "Toán": 8.8,
                    "Vật lý": 8.6,
                    "Hóa học": 8.4,
                    "Tiếng Anh": 8.5,
                    "Ngữ văn": 7.8,
                },
                "top_k": 435,
            }
            rec_before = client.post("/api/v1/recommender/evaluate", json=eval_payload).json()["majors"]
            assert all(m.get("is_trending") is False for m in rec_before[:10])

            # 3) Admin bấm nút chạy Trend Hunter Agent -> trả về bản nháp 2026 (chưa ghi vào CSDL)
            run_res = client.post(
                "/api/v1/taxonomy/trend-agent/run",
                json={"focus_query": "ngành nghề xu hướng khát nhân lực Việt Nam 2026"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert run_res.status_code == 200
            run_body = run_res.json()
            assert run_body["status"] == "draft_ready"
            assert run_body["pending_save"] is True
            assert run_body["saved_to_db"] is False
            assert run_body["articles_scanned"] == 3
            assert run_body["categories_covered"] == 23
            assert run_body["total_categories"] == 23
            assert run_body["total_trending_marked"] >= 66
            assert run_body["tier_counts"]["TIER_1"] >= 1
            assert run_body["tier_counts"]["TIER_2"] >= 1

            # Kiểm tra >= 3 ngành/nhóm (trừ DỊCH VỤ XÃ HỘI = 2, THÚ Y = 1 trong TT74) & trần vĩ mô
            by_cat = {}
            for item in run_body["trending_majors"]:
                by_cat.setdefault(item.get("category"), []).append(item)
            assert len(by_cat) == 23
            for cat_name, items in by_cat.items():
                if cat_name == "THÚ Y":
                    assert len(items) == 1
                elif cat_name == "DỊCH VỤ XÃ HỘI":
                    assert len(items) == 2
                else:
                    assert len(items) >= 3, f"Nhóm {cat_name} chỉ có {len(items)} ngành (< 3)"
            assert len(by_cat["MÁY TÍNH VÀ CÔNG NGHỆ THÔNG TIN"]) >= 4
            for low_macro_cat in ("THÚ Y", "DỊCH VỤ XÃ HỘI", "NÔNG, LÂM NGHIỆP VÀ THỦY SẢN", "PHÁP LUẬT"):
                assert low_macro_cat in by_cat
                assert all(it["trend_tier"] != "TIER_1" for it in by_cat[low_macro_cat])

            # Kiểm tra chốt chặn kẹp trần vĩ mô nếu LLM lỡ đôn nhóm ít nhu cầu lên TIER_1
            clamped_map = trend_agent._build_classified_trend_map(
                [
                    {
                        "major_code": "7640101",
                        "major_name": "Thú y",
                        "category": "THÚ Y",
                        "evidence_score": 1.2,
                        "macro_suggested_tier": "TIER_3",
                        "matched_topics": ["Thú y"],
                        "sources": [],
                    }
                ],
                llm_refined={"7640101": {"trend_tier": "TIER_1", "trend_reason": "Thử nghiệm vượt trần"}},
            )
            assert clamped_map["7640101"]["trend_tier"] == "TIER_3"

            # Trước khi Admin bấm "Lưu vào CSDL": Taxonomy và Recommender chưa bị tác động bởi bản nháp
            first_trend_code = run_body["trending_majors"][0]["major_code"]
            draft_detail = client.get(f"/api/v1/taxonomy/majors/{first_trend_code}")
            assert draft_detail.status_code == 200
            assert draft_detail.json()["is_trending"] is False
            rec_draft = client.post("/api/v1/recommender/evaluate", json=eval_payload).json()["majors"]
            assert all(m.get("is_trending") is False for m in rec_draft[:10])

            # 3b) Student không được phép lưu vào CSDL (403)
            save_payload = {
                "focus_query": run_body["focus_query"],
                "articles_scanned": run_body["articles_scanned"],
                "search_sources": run_body["search_sources"],
                "majors": run_body["trending_majors"],
            }
            student_save_res = client.post(
                "/api/v1/taxonomy/trend-agent/save",
                json=save_payload,
                headers={"Authorization": f"Bearer {student_token}"},
            )
            assert student_save_res.status_code == 403

            # 3c) Admin bấm "Lưu vào CSDL" -> lưu chính thức vào DB để Recommender đọc trực tiếp
            save_res = client.post(
                "/api/v1/taxonomy/trend-agent/save",
                json=save_payload,
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert save_res.status_code == 200
            save_body = save_res.json()
            assert save_body["status"] == "saved"
            assert save_body["saved_to_db"] is True
            assert save_body["pending_save"] is False
            assert save_body["total_trending_marked"] == len(run_body["trending_majors"])

            status_after = client.get("/api/v1/taxonomy/trend-agent/status")
            assert status_after.status_code == 200
            assert status_after.json()["saved_to_db"] is True
            assert status_after.json()["total_trending_marked"] == save_body["total_trending_marked"]

            # 4) Kiểm tra dữ liệu ngành đã được đánh dấu trực tiếp trong Taxonomy API sau khi lưu CSDL
            major_detail = client.get(f"/api/v1/taxonomy/majors/{first_trend_code}")
            assert major_detail.status_code == 200
            m_data = major_detail.json()
            assert m_data["is_trending"] is True
            assert m_data["trend_tier"] in ("TIER_1", "TIER_2", "TIER_3")
            assert m_data["trend_priority"] >= 1

            # 5) Kiểm tra Recommender đọc từ CSDL, ưu tiên các ngành Xu hướng Bậc 1 mà vẫn giữ TARGET trước REACH
            rec_after = client.post("/api/v1/recommender/evaluate", json=eval_payload).json()["majors"]
            assert any(m.get("is_trending") for m in rec_after[:5])
            assert any(m.get("trend_tier") == "TIER_1" for m in rec_after[:5])
            assert all(m["feasibility_tier"] == "TARGET" for m in rec_after[:5])

            # 6) Admin chỉnh bậc ưu tiên thủ công qua PATCH & dọn dẹp sạch test registry
            patch_res = client.patch(
                f"/api/v1/taxonomy/trend-agent/majors/{first_trend_code}",
                json={"trend_tier": "TIER_1", "trend_reason": "Ưu tiên cấp quốc gia"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert patch_res.status_code == 200
            assert patch_res.json()["trending_majors"][0]["trend_tier"] == "TIER_1"

            client.delete(
                "/api/v1/taxonomy/trend-agent/clear",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        finally:
            app.dependency_overrides.clear()


class TestExcelBulkImportPersistence:
    @pytest.mark.anyio
    async def test_bulk_sync_majors_inserts_new_and_preserves_trend_without_lazy_load(self):
        import uuid
        from unittest.mock import AsyncMock, MagicMock
        from app.models.taxonomy import Major, SubjectBlock
        from app.services.taxonomy.service import bulk_sync_majors

        existing_id = uuid.uuid4()
        sb_id = uuid.uuid4()
        existing_major = Major(
            id=existing_id,
            major_code="7480107",
            name="Trí tuệ nhân tạo",
            category="MÁY TÍNH VÀ CÔNG NGHỆ THÔNG TIN",
            degree_level="Đại học",
            riasec_vector={"R": 0.4, "I": 0.9, "A": 0.2, "S": 0.3, "E": 0.3, "C": 0.7},
            cognitive_attributes={"abstract_thinking": "high", "_trend": {"trend_tier": "TIER_1"}},
            industry_outlook="Nhu cầu AI tăng mạnh",
            is_active=True,
        )
        # Ensure unloaded relationship access would raise if bulk_sync_majors regressed to lazy-load
        block_a00 = SubjectBlock(
            id=sb_id,
            block_code="A00",
            name="Toán, Vật lí, Hóa học",
            subjects=["Toán", "Vật lí", "Hóa học"],
            national_mean=20.85,
            national_std=3.25,
        )

        # Sequence of execute() calls in bulk_sync_majors:
        # 1) SubjectBlock -> [block_a00]
        # 2) Major chunk -> [existing_major]
        # 3) MajorSubjectBlock scalar links -> [(existing_id, sb_id)]
        # 4) Career scalar titles -> [(existing_id, "Kỹ sư AI")]
        sb_res = MagicMock()
        sb_res.scalars.return_value.all.return_value = [block_a00]

        maj_res = MagicMock()
        maj_res.scalars.return_value.all.return_value = [existing_major]

        msb_res = MagicMock()
        msb_res.all.return_value = [(existing_id, sb_id)]

        car_res = MagicMock()
        car_res.all.return_value = [(existing_id, "Kỹ sư AI")]

        db = AsyncMock()
        db.add = MagicMock()
        db.execute = AsyncMock(side_effect=[sb_res, maj_res, msb_res, car_res])

        payload = [
            {
                "major_code": "7480107",
                "name": "Trí tuệ nhân tạo (Cập nhật)",
                "category": "MÁY TÍNH VÀ CÔNG NGHỆ THÔNG TIN",
                "blocks": ["A00", "A00"],
                "careers": ["Kỹ sư AI", "Nhà nghiên cứu ML"],
                "riasec": {"R": 0.4, "I": 0.95, "A": 0.2, "S": 0.3, "E": 0.3, "C": 0.7},
                "cognitive": {"abstract_thinking": "high"},
                "outlook": "Cập nhật xu hướng",
            },
            {
                "major_code": "7999999",
                "name": "Ngành Mới TT74 Test",
                "category": "KỸ THUẬT",
                "blocks": ["A00", "A01", "A00"],
                "careers": ["Kỹ sư mới", "Kỹ sư mới"],
                "riasec": {"R": 0.8, "I": 0.7, "A": 0.2, "S": 0.3, "E": 0.4, "C": 0.6},
                "cognitive": {"abstract_thinking": "medium"},
                "outlook": "Triển vọng tốt",
            },
            # Duplicate row in same Excel sheet should deduplicate cleanly
            {
                "major_code": "7999999",
                "name": "Ngành Mới TT74 Test (Bản mới)",
                "category": "KỸ THUẬT",
                "blocks": ["A00"],
                "careers": ["Kỹ sư mới"],
            },
        ]

        res = await bulk_sync_majors(db, payload)
        assert res["status"] == "success"
        assert res["inserted"] == 1
        assert res["updated"] == 1
        assert res["total"] == 2
        assert existing_major.cognitive_attributes["_trend"]["trend_tier"] == "TIER_1"
        db.flush.assert_awaited()
        db.commit.assert_awaited_once()

    def test_import_excel_raises_500_instead_of_silently_faking_success_on_db_error(self, monkeypatch):
        from pathlib import Path
        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import get_db
        from app.services.taxonomy import service

        async def _fake_db():
            from unittest.mock import AsyncMock
            yield AsyncMock()

        async def _broken_bulk_sync(db, majors_data, deactivate_missing=False):
            raise RuntimeError("Simulated PostgreSQL MissingGreenlet failure")

        monkeypatch.setattr(service, "bulk_sync_majors", _broken_bulk_sync)
        app.dependency_overrides[get_db] = _fake_db

        try:
            tpl_path = Path(__file__).resolve().parents[1] / "app" / "db" / "seeds" / "MOET_Major_Import_Template_Standard.xlsx"
            client = TestClient(app)
            with open(tpl_path, "rb") as f:
                res = client.post(
                    "/api/v1/taxonomy/import-excel?preview_only=false",
                    files={"file": ("MOET_Major_Import_Template_Standard.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                )
            assert res.status_code == 500
            assert "Không thể lưu" in res.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_bulk_sync_majors_deactivates_legacy_codes_when_replace_catalog_enabled(self):
        import uuid
        from unittest.mock import AsyncMock, MagicMock
        from app.models.taxonomy import SubjectBlock
        from app.services.taxonomy.service import bulk_sync_majors

        sb_id = uuid.uuid4()
        stale_id = uuid.uuid4()
        block_a00 = SubjectBlock(
            id=sb_id,
            block_code="A00",
            name="Toán, Vật lí, Hóa học",
            subjects=["Toán", "Vật lí", "Hóa học"],
            national_mean=20.85,
            national_std=3.25,
        )
        sb_res = MagicMock()
        sb_res.scalars.return_value.all.return_value = [block_a00]
        maj_res = MagicMock()
        maj_res.scalars.return_value.all.return_value = []
        active_res = MagicMock()
        # Simulate one active incoming code and one stale TT09 code in DB
        active_res.all.return_value = [(stale_id, "7480202"), (uuid.uuid4(), "7480107")]
        update_res = MagicMock()

        db = AsyncMock()
        db.add = MagicMock()
        db.execute = AsyncMock(side_effect=[sb_res, maj_res, active_res, update_res])

        res = await bulk_sync_majors(
            db,
            [{"major_code": "7480107", "name": "Trí tuệ nhân tạo", "category": "CNTT"}],
            deactivate_missing=True,
        )
        assert res["deactivated"] == 1
        assert res["total"] == 1
        db.commit.assert_awaited_once()


# =========================================================================
# ADAPTIVE WEIGHTING & COMPACT XAI TESTS (ARENA WINNING DESIGN)
# =========================================================================

class TestAdaptiveWeightingAndCompactXAI:
    def test_adaptive_weights_when_missing_academic_scores(self):
        # Khi học sinh chưa nhập điểm, academic = 0, riasec + preference = 1.0
        weights = compute_adaptive_weights(has_academic_scores=False)
        assert weights["w_academic"] == 0.0
        assert round(weights["w_riasec"] + weights["w_preference"], 4) == 1.0
        assert weights["w_riasec"] > 0.60
        assert weights["w_preference"] > 0.25

    def test_adaptive_weights_safe_admission_strategy(self):
        # Chiến lược an toàn tăng trọng số học thuật
        weights = compute_adaptive_weights(has_academic_scores=True, strategy="safe_admission")
        assert round(sum(weights.values()), 4) == 1.0
        assert weights["w_academic"] > 0.40

    def test_adaptive_weights_passion_strategy(self):
        # Chiến lược đam mê tăng trọng số RIASEC
        weights = compute_adaptive_weights(has_academic_scores=True, strategy="passion")
        assert round(sum(weights.values()), 4) == 1.0
        assert weights["w_riasec"] > 0.50

    def test_adaptive_weights_category_multipliers(self):
        # Ngành sức khỏe / kỹ thuật tăng học thuật
        tech_weights = compute_adaptive_weights(has_academic_scores=True, category="Kỹ thuật máy tính")
        art_weights = compute_adaptive_weights(has_academic_scores=True, category="Mỹ thuật đồ họa")
        assert tech_weights["w_academic"] > art_weights["w_academic"]
        assert art_weights["w_riasec"] > tech_weights["w_riasec"]

    def test_hybrid_score_with_missing_academic_scores(self):
        # Tính điểm khi không có điểm học thuật
        score, weights = calculate_3pillar_hybrid_score(
            score_riasec=0.85,
            score_academic=0.0,
            score_preference=0.75,
            has_academic_scores=False,
        )
        assert weights["w_academic"] == 0.0
        assert round(weights["w_riasec"] + weights["w_preference"], 4) == 1.0
        # Điểm tổng hợp không bị tụt vì điểm học thuật 0.0
        assert score > 0.80

    def test_compact_xai_explanation_structure_and_clarity(self):
        # Kiểm tra giải thích 3 câu gọn gàng không biệt ngữ toán học
        expl = build_compact_xai_explanation(
            major_name="Khoa học máy tính",
            score_riasec=0.90,
            score_academic=0.82,
            score_pref=0.85,
            best_block="A00",
            admission_band="TARGET",
            has_academic_scores=True,
        )
        assert "Khoa học máy tính" in expl
        assert "A00" in expl
        assert "Vừa sức" in expl
        # 3 câu (kết thúc bằng dấu chấm)
        sentences = [s.strip() for s in expl.split(".") if s.strip()]
        assert len(sentences) == 3

    def test_compact_xai_explanation_when_missing_scores(self):
        expl = build_compact_xai_explanation(
            major_name="Thiết kế đồ họa",
            score_riasec=0.95,
            score_academic=0.0,
            score_pref=0.80,
            admission_band="UNKNOWN",
            has_academic_scores=False,
        )
        assert "Thiết kế đồ họa" in expl
        assert "Chưa đủ dữ liệu điểm" in expl
        assert "nhập điểm" in expl.lower()





