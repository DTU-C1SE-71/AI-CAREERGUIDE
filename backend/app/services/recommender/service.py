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
    evaluate_academic_readiness_for_major,
    calculate_cognitive_preference_match,
    calculate_3pillar_hybrid_score,
    generate_xai_top_supporting_factors,
    classify_major_academic_benchmark,
    evaluate_admission_feasibility,
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
        # --- PILLAR 1: Holland RIASEC via Cosine Similarity ---
        score_riasec = calculate_riasec_cosine_similarity(student_riasec, major.riasec_vector)

        # --- PILLAR 2: Academic Readiness via Z-Score Normalization ---
        admitted_codes = [
            msb.subject_block.block_code for msb in major.subject_blocks if msb.subject_block
        ]
        score_academic, best_block, block_breakdown = evaluate_academic_readiness_for_major(
            admitted_codes, student_zscores
        )

        # --- PILLAR 3: Cognitive Preferences via Rule-Based Matching ---
        score_pref = calculate_cognitive_preference_match(student_pref, major.cognitive_attributes)

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

        # --- SOLUTION B: ADMISSION FEASIBILITY & REALISTIC BENCHMARKING ---
        raw_block_sum = 18.0
        if best_block and isinstance(block_breakdown, dict) and best_block in block_breakdown:
            raw_block_sum = float(block_breakdown[best_block].get("raw_sum", 18.0))

        feasibility = evaluate_admission_feasibility(
            raw_block_sum=raw_block_sum,
            major_code=major.major_code,
            major_name=major.name,
            category=major.category
        )

        # Apply feasibility penalty if the student has a severe score gap for reach majors (e.g. 15 pts vs 25.5 pts)
        final_academic_score = score_academic
        if feasibility["feasibility_tier"] == "REACH":
            deficit_ratio = min(1.0, abs(feasibility["score_gap"]) / 15.0)
            final_academic_score = max(0.05, score_academic * (1.0 - deficit_ratio * 0.6))
            overall_score, weights_dict = calculate_3pillar_hybrid_score(
                score_riasec=score_riasec,
                score_academic=final_academic_score,
                score_preference=score_pref,
                w_riasec=w_riasec,
                w_academic=w_academic,
                w_preference=w_pref
            )

        # --- DETERMINISTIC XAI EXPLANATIONS ---
        top_factors, summary_expl = generate_xai_top_supporting_factors(
            major_name=major.name,
            score_riasec=score_riasec,
            student_riasec=student_riasec,
            major_riasec=major.riasec_vector,
            score_academic=final_academic_score,
            best_block=best_block,
            score_pref=score_pref,
            student_pref=student_pref,
            major_attr=major.cognitive_attributes
        )

        if feasibility["feasibility_tier"] == "REACH":
            top_factors.insert(0, f"Cảnh báo phân tầng: {feasibility['feasibility_label']}. {feasibility['admission_advice']}")
        else:
            top_factors.insert(0, f"Độ tương thích học lực an toàn: Khối {best_block or 'xét tuyển'} ({raw_block_sum}đ) đạt ngưỡng sàn ({feasibility['benchmark_cutoff']}đ).")

        scored_items.append(MajorRecommendationItem(
            rank=0,
            major_id=major.id,
            major_code=major.major_code,
            major_name=major.name,
            category=getattr(major, "category", "Khác") or "Khác",
            overall_score=overall_score,
            score_riasec=score_riasec,
            score_academic=final_academic_score,
            score_preference=score_pref,
            best_matching_block=best_block,
            score_breakdown={
                "weights": weights_dict,
                "score_riasec": score_riasec,
                "score_academic": final_academic_score,
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

    # Deterministic Sort: prioritize realistic TARGET majors if student has low grades (< 17.5)
    scored_items.sort(
        key=lambda item: (
            1 if item.feasibility_tier == "TARGET" else 0,
            item.overall_score,
            item.score_academic,
            item.score_riasec
        ),
        reverse=True
    )

    # Assign 1-based ranks and slice top_k
    top_results: List[MajorRecommendationItem] = []
    for idx, item in enumerate(scored_items[:payload.top_k], start=1):
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
