import logging
import time
import uuid

logger = logging.getLogger(__name__)
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.taxonomy import Major, MajorSubjectBlock, MajorSkill, Skill, SkillPrerequisite
from app.models.assessment import StudentAssessment, StudentGrade, StudentDiagnosticTest
from app.models.recommender import RecommendationHistory
from app.core.config import settings
from app.schemas.recommender import (
    RecommendationRequest,
    MajorRecommendationItem,
    RecommendationResponse,
)
from app.services.recommender.engine import (
    calculate_riasec_cosine_similarity,
    calculate_enhanced_riasec_fit,
    evaluate_academic_readiness_for_major,
    evaluate_target_anchored_academic_fit,
    calculate_cognitive_preference_match,
    calculate_asymmetric_cognitive_fit,
    calculate_3pillar_hybrid_score,
    generate_xai_top_supporting_factors,
    classify_major_academic_benchmark,
    evaluate_admission_feasibility,
    are_majors_related_pathway,
)

# Backwards compatibility aliases
compute_cosine_similarity = calculate_riasec_cosine_similarity
compute_cognitive_match = calculate_cognitive_preference_match
from app.services.gap_roadmap_engine.gap_engine import (
    infer_mastered_skills_from_grades,
    infer_mastered_skills_from_diagnostic_tests,
    analyze_competency_gaps,
)


async def calculate_3pillar_recommendations(
    db: AsyncSession,
    user_id: uuid.UUID,
    payload: RecommendationRequest
) -> RecommendationResponse:
    """
    Executes the deterministic 3-Pillar Holistic Hybrid Recommendation Engine (NFR04, FR04).
    Guarantees performance <= 2 seconds across 80+ Level-IV MOET majors (NFR01).
    Pure Guidance Scope: strictly excludes tuition and geographic factors (NFR02).
    """
    start_time = time.perf_counter()

    # 1. Fetch Student Assessment Profile
    try:
        assess_res = await db.execute(
            select(StudentAssessment).where(StudentAssessment.user_id == user_id)
        )
        assessment = assess_res.scalar_one_or_none()

        # 2. Fetch Student Grades & Normalized Z-Scores
        grade_res = await db.execute(
            select(StudentGrade).where(StudentGrade.user_id == user_id).order_by(StudentGrade.created_at.desc())
        )
        grade = grade_res.scalar_one_or_none()

        # 3. Fetch Optional Diagnostic Skill Checks
        diag_res = await db.execute(
            select(StudentDiagnosticTest).where(StudentDiagnosticTest.user_id == user_id)
        )
        diagnostic_tests = list(diag_res.scalars().all())
    except Exception as db_err:
        assessment = None
        grade = None
        diagnostic_tests = []

    # Extract vectors & traits safely
    student_riasec = assessment.riasec_scores if assessment and assessment.riasec_scores else {
        "R": 0.5, "I": 0.5, "A": 0.5, "S": 0.5, "E": 0.5, "C": 0.5
    }
    student_pref = assessment.cognitive_preferences if assessment and assessment.cognitive_preferences else {}
    student_zscores = grade.computed_block_zscores if grade and grade.computed_block_zscores else {}
    raw_grades = grade.grades_by_subject if grade and grade.grades_by_subject else {}

    # Infer mastered skills from both grades and diagnostic tests
    mastered_skills = infer_mastered_skills_from_grades(raw_grades)
    diag_mastered = infer_mastered_skills_from_diagnostic_tests([
        {"skill_code": d.skill_code, "score": d.score, "is_passed": d.is_passed}
        for d in diagnostic_tests
    ])
    mastered_skills.update(diag_mastered)

    # 4. Resolve Weights (3-Pillar Hybrid Model)
    w_riasec = settings.WEIGHT_RIASEC
    w_academic = settings.WEIGHT_ACADEMIC
    w_pref = settings.WEIGHT_PREFERENCE
    if payload.custom_weights:
        w_riasec = float(payload.custom_weights.get("w_riasec", w_riasec))
        w_academic = float(payload.custom_weights.get("w_academic", w_academic))
        w_pref = float(payload.custom_weights.get("w_preference", w_pref))

    # 5. Fetch Skill Prerequisites Hierarchy Map
    prereq_map: Dict[str, List[str]] = {}
    try:
        prereq_res = await db.execute(
            select(SkillPrerequisite).options(
                selectinload(SkillPrerequisite.skill),
                selectinload(SkillPrerequisite.prerequisite_skill)
            )
        )
        all_prereqs = list(prereq_res.scalars().all())
        for p in all_prereqs:
            target_c = p.skill.skill_code if p.skill else ""
            source_c = p.prerequisite_skill.skill_code if p.prerequisite_skill else ""
            if target_c and source_c:
                prereq_map.setdefault(target_c, []).append(source_c)
    except Exception:
        pass

    # 6. Retrieve all Active Majors with Admitted Subject Blocks and Required Skills
    try:
        majors_query = select(Major).where(Major.is_active == True).options(
            selectinload(Major.subject_blocks).selectinload(MajorSubjectBlock.subject_block),
            selectinload(Major.major_skills).selectinload(MajorSkill.skill)
        )
        majors_res = await db.execute(majors_query)
        majors = list(majors_res.scalars().all())
    except Exception as db_err:
        logger.warning("Database query failed in recommender, falling back to seed taxonomy: %s", db_err)
        majors = []

    if not majors:
        from app.services.taxonomy.service import load_seed_majors
        seed_data = load_seed_majors()

        class MajorSeedAdapter:
            def __init__(self, d: dict, mock_id: int):
                raw_id = d.get("id")
                try:
                    self.id = uuid.UUID(str(raw_id)) if raw_id else uuid.uuid5(uuid.NAMESPACE_DNS, f"major-{d.get('major_code') or mock_id}")
                except Exception:
                    self.id = uuid.uuid5(uuid.NAMESPACE_DNS, f"major-{d.get('major_code') or mock_id}")
                self.major_code = d.get("major_code", "")
                self.name = d.get("name", "")
                self.category = d.get("category", "")
                self.riasec_vector = d.get("riasec") or d.get("riasec_vector") or {}
                self.cognitive_attributes = d.get("cognitive") or d.get("cognitive_attributes") or {}
                self.industry_outlook = d.get("outlook") or d.get("industry_outlook") or ""
                self.is_active = True
                raw_blocks = d.get("blocks", [])
                self.subject_blocks = [
                    type("MSB", (), {"subject_block": type("SB", (), {"block_code": b})()})()
                    for b in raw_blocks
                ]
                self.major_skills = []

        majors = [MajorSeedAdapter(m, idx) for idx, m in enumerate(seed_data, start=1)]

    scored_items: List[MajorRecommendationItem] = []

    for major in majors:
        # --- BENCHMARK TIER & CUTOFF RESOLUTION ---
        bm_info = classify_major_academic_benchmark(
            major.major_code, major.name, getattr(major, "category", "")
        )

        # --- PILLAR 1 (45%): Enhanced Holland RIASEC Fit (Cosine 75% + Hexagonal Peak 25%) ---
        score_riasec = calculate_enhanced_riasec_fit(student_riasec, major.riasec_vector)

        # --- PILLAR 2 (35%): Target-Anchored Academic Readiness via Z-Score & Cutoff Alignment ---
        admitted_codes = [
            msb.subject_block.block_code for msb in major.subject_blocks if msb.subject_block
        ]
        score_academic, best_block, block_breakdown = evaluate_target_anchored_academic_fit(
            admitted_codes,
            student_zscores,
            benchmark_cutoff=bm_info["benchmark_cutoff"],
            min_recommended=bm_info["min_recommended"],
        )

        # --- PILLAR 3 (20%): Asymmetric Cognitive Competency + Symmetric Cultural Fit ---
        score_pref = calculate_asymmetric_cognitive_fit(student_pref, major.cognitive_attributes)

        # --- HOLISTIC 3-PILLAR SCORE ---
        overall_score, weights_dict = calculate_3pillar_hybrid_score(
            score_riasec=score_riasec,
            score_academic=score_academic,
            score_preference=score_pref,
            w_riasec=w_riasec,
            w_academic=w_academic,
            w_preference=w_pref
        )

        # --- COMPETENCY GAP ANALYSIS ---
        major_skills_list = [
            {
                "skill_code": ms.skill.skill_code,
                "name": ms.skill.name,
                "skill_type": ms.skill.skill_type.value if hasattr(ms.skill.skill_type, "value") else str(ms.skill.skill_type),
                "importance": ms.importance_level
            }
            for ms in major.major_skills if ms.skill
        ]
        overall_gaps, missing_pre, missing_tar = analyze_competency_gaps(
            required_major_skills=major_skills_list,
            skill_prerequisites_map=prereq_map,
            mastered_skill_codes=mastered_skills
        )

        # --- ADMISSION FEASIBILITY & HARD CUTOFF EVALUATION ---
        raw_block_sum = 21.5
        if best_block and isinstance(block_breakdown, dict) and best_block in block_breakdown:
            raw_block_sum = float(block_breakdown[best_block].get("raw_sum", 21.5))
        elif student_zscores:
            # If major's blocks don't match entered blocks, take max raw_sum across student's entered blocks
            all_sums = [float(v.get("raw_sum", 18.0)) for v in student_zscores.values() if isinstance(v, dict)]
            if all_sums:
                raw_block_sum = max(all_sums)

        feasibility = evaluate_admission_feasibility(
            raw_block_sum=raw_block_sum,
            major_code=major.major_code,
            major_name=major.name,
            category=major.category
        )

        # --- DETERMINISTIC XAI EXPLANATIONS ---
        top_factors, summary_expl = generate_xai_top_supporting_factors(
            major_name=major.name,
            score_riasec=score_riasec,
            student_riasec=student_riasec,
            major_riasec=major.riasec_vector,
            score_academic=score_academic,
            best_block=best_block,
            score_pref=score_pref,
            student_pref=student_pref,
            major_attr=major.cognitive_attributes
        )

        if feasibility["feasibility_tier"] == "REACH":
            top_factors.insert(0, f"Chặn ngưỡng điểm an toàn: {feasibility['feasibility_label']}. {feasibility['admission_advice']}")
        else:
            top_factors.insert(0, f"Độ tương thích học lực an toàn: Khối {best_block or 'xét tuyển'} ({raw_block_sum}đ) đáp ứng ngưỡng chuẩn (~{feasibility['benchmark_cutoff']}đ).")

        scored_items.append(MajorRecommendationItem(
            rank=0,
            major_id=major.id,
            major_code=major.major_code,
            major_name=major.name,
            category=getattr(major, "category", "Khác") or "Khác",
            overall_score=overall_score,
            score_riasec=score_riasec,
            score_academic=score_academic,
            score_preference=score_pref,
            best_matching_block=best_block,
            score_breakdown={
                "weights": weights_dict,
                "score_riasec": score_riasec,
                "score_academic": score_academic,
                "score_preference": score_pref,
                "admitted_blocks_evaluated": block_breakdown,
                "feasibility": feasibility
            },
            top_supporting_factors=top_factors,
            competency_gaps=overall_gaps[:5],
            missing_prerequisites=missing_pre[:3],
            missing_target_skills=missing_tar[:3],
            explanation=summary_expl,
            feasibility_tier=feasibility["feasibility_tier"],
            feasibility_label=feasibility["feasibility_label"],
            benchmark_cutoff=feasibility["benchmark_cutoff"],
            score_gap=feasibility["score_gap"],
            admission_advice=feasibility["admission_advice"],
            academic_tier=feasibility["academic_tier"],
            academic_tier_label=feasibility["academic_tier_label"]
        ))

    # =========================================================================
    # HARD ACADEMIC GATEKEEPER & SMART SIBLING / PATHWAY SUBSTITUTION
    # =========================================================================
    eligible_targets = [it for it in scored_items if it.feasibility_tier == "TARGET"]
    blocked_reaches = [it for it in scored_items if it.feasibility_tier == "REACH"]

    # Sort blocked high-cutoff majors by pure interest + cognitive passion
    blocked_reaches.sort(
        key=lambda it: (0.70 * it.score_riasec + 0.30 * it.score_preference),
        reverse=True
    )

    substituted_codes = set()
    for blocked in blocked_reaches[:6]:
        if blocked.score_riasec < 0.65:
            continue
        # Find the closest eligible TARGET sibling major (same 4-digit group -> same 2-digit field -> 52->51 pathway)
        best_sub: Optional[MajorRecommendationItem] = None
        best_sub_metric = -1.0
        best_rel_tier = 0

        for cand in eligible_targets:
            if cand.major_code in substituted_codes:
                continue
            rel_tier = are_majors_related_pathway(blocked.major_code, cand.major_code)
            if rel_tier > 0 and cand.score_riasec >= 0.60:
                metric = (rel_tier * 0.25) + (cand.score_riasec * 0.50) + (cand.overall_score * 0.25)
                if metric > best_sub_metric:
                    best_sub_metric = metric
                    best_sub = cand
                    best_rel_tier = rel_tier

        if best_sub is not None:
            substituted_codes.add(best_sub.major_code)
            pathway_desc = (
                "cùng nhóm ngành" if best_rel_tier == 3 else (
                    "cùng lĩnh vực / nhánh Công nghệ Kỹ thuật ứng dụng" if best_rel_tier == 2 else "nhóm ngành liên thông gần gũi"
                )
            )
            sub_msg = (
                f"Đề xuất thay thế vừa sức cho ngành {blocked.major_name} (điểm chuẩn ~{blocked.benchmark_cutoff}đ): "
                f"Giữ trọn định hướng sở thích ({round(best_sub.score_riasec * 100, 1)}%) thuộc {pathway_desc} "
                f"nhưng có ngưỡng điểm an toàn (~{best_sub.benchmark_cutoff}đ)."
            )
            best_sub.feasibility_label = f"Thay thế vừa sức cho {blocked.major_name}"
            best_sub.admission_advice = sub_msg
            best_sub.top_supporting_factors.insert(0, sub_msg)
            # Slight priority boost so the smart substitute surfaces in Top recommendations
            best_sub.overall_score = round(min(0.99, best_sub.overall_score + 0.04), 4)

    # Strictly recommend ONLY eligible TARGET majors (fallback to all only if eligible_targets is empty)
    final_pool = eligible_targets if len(eligible_targets) >= payload.top_k else scored_items
    final_pool.sort(
        key=lambda item: (
            1 if item.feasibility_tier == "TARGET" else 0,
            1 if item.major_code in substituted_codes else 0,
            item.overall_score,
            item.score_academic,
            item.score_riasec
        ),
        reverse=True
    )

    # Assign 1-based ranks and slice top_k
    top_results: List[MajorRecommendationItem] = []
    for idx, item in enumerate(final_pool[:payload.top_k], start=1):
        item.rank = idx
        top_results.append(item)

    # Persist execution history for auditability
    generated_now = datetime.now(timezone.utc)
    try:
        history = RecommendationHistory(
            user_id=user_id,
            weights_applied=weights_dict,
            ranked_results=[it.model_dump() for it in top_results],
            generated_at=generated_now
        )
        db.add(history)
        await db.commit()
    except Exception:
        pass

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    print(f"3-Pillar Recommendation Engine evaluated {len(majors)} majors in {elapsed_ms:.2f}ms.")

    return RecommendationResponse(
        user_id=user_id,
        generated_at=generated_now,
        weights_applied=weights_dict,
        total_majors_evaluated=len(majors),
        recommendations=top_results
    )
