import logging
import math
import time
import uuid

logger = logging.getLogger(__name__)
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from fastapi import HTTPException, status
from app.models.identity import User
from app.models.taxonomy import Major, MajorSubjectBlock, MajorSkill, Skill, SkillPrerequisite
from app.models.assessment import StudentAssessment, StudentGrade, StudentDiagnosticTest
from app.models.recommender import RecommendationHistory
from app.core.config import settings
from app.schemas.recommender import (
    RecommendationRequest,
    MajorRecommendationItem,
    RecommendationResponse,
)
from app.services.recommender.horizon_gender_engine import (
    get_grade_horizon_config,
    apply_horizon_gender_reranking,
    build_horizon_gender_xai_explanation,
)
from app.services.recommender.subfacet_gate import evaluate_subfacet_gate
from app.services.recommender.engine import (
    RIASEC_DIMENSIONS,
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
    compute_block_zscores_from_grades,
    calculate_z_score_and_cdf,
    normalize_grades_dict,
    normalize_student_cognitive_traits,
    build_radar_and_block_summary,
    format_block_with_subjects,
    calculate_market_trend_compatibility,
    CROSS_FIELD_SUBSTITUTION_MAP,
)

from app.services.recommender.readiness import (
    build_interest_evidence,
    evaluate_current_readiness,
    validate_readiness_grades,
)


async def resolve_assessment_evidence(
    db: Optional[AsyncSession],
    user_id: uuid.UUID,
    inline_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Resolve once; an explicitly empty field must never revive older DB data."""
    inline = dict(inline_profile or {})
    snapshot_id = inline.get("assessment_id")
    assessment = None
    grade = None
    needs_assessment = (
        not any(key in inline for key in ("riasec_answers", "riasec_scores"))
        or not any(key in inline for key in ("cognitive_answers", "cognitive_preferences"))
        or "aspiration" not in inline
        or "grades_by_subject" not in inline
    )
    if db is not None and user_id is not None:
        if snapshot_id or needs_assessment:
            query = select(StudentAssessment).where(StudentAssessment.user_id == user_id)
            if snapshot_id:
                query = query.where(StudentAssessment.id == snapshot_id)
            else:
                query = query.order_by(StudentAssessment.assessed_at.desc(), StudentAssessment.id.desc()).limit(1)
            result = await db.execute(query)
            assessment = result.scalars().first()
            if snapshot_id and assessment is None:
                raise HTTPException(status_code=404, detail="Không tìm thấy bản đánh giá đã chọn.")
        snapshot_raw = assessment.raw_responses if assessment and isinstance(assessment.raw_responses, dict) else {}
        if "grades_by_subject" not in inline and not snapshot_id and "grades_by_subject" not in snapshot_raw:
            result = await db.execute(
                select(StudentGrade).where(StudentGrade.user_id == user_id)
                .order_by(StudentGrade.created_at.desc())
            )
            grade = result.scalars().first()

    raw = assessment.raw_responses if assessment and isinstance(assessment.raw_responses, dict) else {}
    stored_answers = raw.get("riasec", raw.get("riasec_answers", raw))
    # Explicit answers, even {}, take precedence over a stored vector.
    answers = inline["riasec_answers"] if "riasec_answers" in inline else (
        {} if "riasec_scores" in inline else stored_answers
    )
    vector = inline.get("riasec_scores") if "riasec_scores" in inline else (
        None if "riasec_answers" in inline else getattr(assessment, "riasec_scores", None)
    )
    if "cognitive_answers" in inline:
        cognitive = inline["cognitive_answers"] or {}
    elif "cognitive_preferences" in inline:
        cognitive = inline["cognitive_preferences"] or {}
    else:
        # Raw answers are authoritative even when explicitly empty; legacy derived
        # preferences may have been filled with defaults during submission.
        cognitive = (raw["cognitive"] or {}) if "cognitive" in raw else (getattr(assessment, "cognitive_preferences", None) or {})
    if "grades_by_subject" in inline:
        grades = inline["grades_by_subject"] or {}
    elif snapshot_id or "grades_by_subject" in raw:
        grades = raw.get("grades_by_subject") or {}
    else:
        grades = getattr(grade, "grades_by_subject", None) or {}
    # Score context must describe the same source as the selected grades.
    if "score_context" in inline:
        score_context = inline["score_context"] if isinstance(inline["score_context"], dict) else {}
    elif "grades_by_subject" not in inline and (snapshot_id or "grades_by_subject" in raw):
        score_context = raw.get("score_context", {"kind": "TRANSCRIPT", "scale": 10})
        if not isinstance(score_context, dict):
            score_context = {}
    else:
        score_context = {"kind": "TRANSCRIPT", "scale": 10}
    aspiration = inline["aspiration"] if "aspiration" in inline else raw.get("aspiration", {})
    return {
        **inline,
        "riasec_answers": answers or {},
        "riasec_scores": vector or {},
        "cognitive_preferences": cognitive,
        "grades_by_subject": grades,
        "aspiration": aspiration or {},
        "score_context": score_context,
        "evidence_source": "SELECTED_ASSESSMENT" if snapshot_id else ("INLINE" if inline_profile is not None else "CURRENT_PROFILE"),
        "assessment_id": str(snapshot_id or getattr(assessment, "id", "")) or None,
    }


def _exact_block_results(validated_scores: Dict[str, Any]) -> Dict[str, Any]:
    """Keep validated decimal totals authoritative; round only chart display."""
    blocks = compute_block_zscores_from_grades({key: float(value) for key, value in validated_scores.items()})
    for block in blocks.values():
        subjects = block["subjects_used"]
        block["subject_scores"] = {subject: float(validated_scores[subject]) for subject in subjects}
        block["raw_sum"] = float(sum(validated_scores[subject] for subject in subjects))
        zscore, cdf = calculate_z_score_and_cdf(block["raw_sum"], block["national_mean"], block["national_std"])
        block.update(z_score=zscore, score_academic=cdf)
    return blocks


def _publish_readiness(item: MajorRecommendationItem, *, preserve_complete_feasibility: bool = False) -> None:
    """Heuristic rank is not an admission decision; publish only checked evidence."""
    evidence = item.readiness
    has_explicit_ref = evidence.get("reason") != "REFERENCE_BASIS_MISSING"
    available = item.score_breakdown.get("pillar_availability", {})
    item.fit = {
        "interest": round(item.score_riasec * 100) if available.get("w_riasec") else None,
        "academic": round(item.score_academic * 100) if available.get("w_academic") else None,
        "cognitive": round(item.score_preference * 100) if available.get("w_preference") else None,
    }
    interest_known = item.score_breakdown.get("interest_evidence_status") == "COMPLETE"
    item.match = round(item.overall_score * 100) if interest_known and any(available.values()) else None
    item.score_breakdown["suitability_status"] = "OBSERVED_INTEREST_FIT" if interest_known else "UNDETERMINED"
    if not interest_known:
        item.score_breakdown["score_meaning"] = "PARTIAL_EVIDENCE_RANK_ONLY"
    item.gaps = item.competency_gaps[:3]

    if preserve_complete_feasibility and interest_known and not has_explicit_ref:
        item.feasibility = item.feasibility_tier
        item.university = (
            format_block_with_subjects(item.best_matching_block)
            if item.best_matching_block
            else "Cần đối chiếu trường và phương thức tuyển sinh"
        )
        if item.best_block_score is not None and item.feasibility_tier in ("TARGET", "SAFETY", "SAFE"):
            evidence.update({
                "status": "READY_REFERENCE",
                "reason": "REFERENCE_MET",
                "block": item.best_matching_block,
                "block_score": item.best_block_score,
                "benchmark_cutoff": item.benchmark_cutoff,
                "min_recommended": item.min_recommended,
                "violations": list(item.constraint_violations or []),
                "message": item.admission_advice or "Đạt mốc điểm chuẩn tham chiếu của ngành.",
            })
        elif item.feasibility_tier == "REACH":
            evidence.update({
                "status": "NEEDS_IMPROVEMENT",
                "reason": "BELOW_REFERENCE_OR_CONSTRAINT",
                "block": item.best_matching_block,
                "block_score": item.best_block_score,
                "benchmark_cutoff": item.benchmark_cutoff,
                "min_recommended": item.min_recommended,
                "violations": list(item.constraint_violations or []),
                "message": item.admission_advice or "Cần cải thiện thêm điểm số hoặc điều kiện môn tiên quyết.",
            })
        item.score_breakdown["feasibility"] = evidence
        item.academic_tier = item.feasibility_tier
        item.academic_tier_label = item.feasibility_label
        if not item.advisory_note:
            item.advisory_note = item.admission_advice
        return

    from decimal import Decimal, InvalidOperation
    try:
        thresholds = [Decimal(str(evidence[k])) for k in ("benchmark_cutoff", "min_recommended") if evidence.get(k) is not None]
        margin = Decimal(str(evidence["block_score"])) - max(thresholds) if thresholds else None
        margin = float(margin) if margin is not None and margin.is_finite() else None
    except (KeyError, TypeError, ValueError, InvalidOperation):
        margin = None
    ready = evidence.get("status") == "READY_REFERENCE" and not evidence.get("violations") and margin is not None and margin >= 0
    known_gap = evidence.get("status") in {"READY_REFERENCE", "NEEDS_IMPROVEMENT"} and not ready
    if known_gap and evidence.get("status") == "READY_REFERENCE":
        evidence["status"] = "NEEDS_IMPROVEMENT"
    item.feasibility_tier = "TARGET" if ready else "REACH" if known_gap else "UNKNOWN"
    item.feasibility = item.feasibility_tier
    item.feasibility_label = "Đạt mốc tham chiếu" if ready else "Cần cải thiện" if known_gap else "Chưa đủ cơ sở đối chiếu"
    item.constraint_passed = ready
    item.constraint_violations = list(evidence.get("violations", []))
    item.admission_advice = evidence.get("message") or "Chưa đủ bằng chứng để đối chiếu."
    item.best_matching_block = evidence.get("block")
    item.best_block_score = evidence.get("block_score")
    item.benchmark_cutoff = evidence.get("benchmark_cutoff")
    item.min_recommended = evidence.get("min_recommended")
    item.score_gap = margin
    item.university = format_block_with_subjects(item.best_matching_block) if item.best_matching_block else "Cần đối chiếu trường và phương thức tuyển sinh"
    item.admission_tactic = "Đối chiếu phương thức tuyển sinh" if not ready else "Lựa chọn đạt mốc tham chiếu"
    item.advisory_note = item.admission_advice
    item.nudge_badge = None
    interest_note = (f"Mức tương đồng sở thích: {item.fit['interest']}%. " if available.get("w_riasec")
                     else "Sở thích chưa phân hóa hoặc chưa đủ câu trả lời để kết luận mức phù hợp. ")
    cognitive_note = (f"Tương đồng thiên hướng tự khai: {item.fit['cognitive']}%; không phải đo năng lực. "
                      if available.get("w_preference") else "Chưa đủ dữ liệu thiên hướng tự khai. ")
    item.explanation = interest_note + cognitive_note + item.admission_advice
    item.top_supporting_factors = [item.admission_advice, "Điểm phù hợp là chỉ số heuristic, không phải xác suất trúng tuyển."]
    item.score_breakdown["feasibility"] = evidence
    item.academic_tier = evidence.get("status", "UNKNOWN")
    item.academic_tier_label = item.feasibility_label



# Backwards compatibility aliases
compute_cosine_similarity = calculate_riasec_cosine_similarity
compute_cognitive_match = calculate_cognitive_preference_match
from app.services.gap_roadmap_engine.gap_engine import (
    infer_mastered_skills_from_grades,
    infer_mastered_skills_from_diagnostic_tests,
    analyze_competency_gaps,
)


def _riasec_vector_from_answers(raw_answers: Optional[Dict[str, Any]]) -> Optional[Dict[str, float]]:
    """Tính vector 6 chiều RIASEC từ đáp án câu hỏi R1..C5 (thang Likert 1..5 -> [0.0, 1.0])."""
    evidence = build_interest_evidence(raw_answers or {})
    if evidence["status"] == "MISSING":
        return None
    vector = {}
    for group in evidence["groups"]:
        if group["answered"]:
            # Preserve the existing Likert normalization for ranking; never fill missing groups.
            vector[group["code"]] = round(group["percent"] / 100.0, 4)
    return vector


class _MajorSeedAdapter:
    """Bộ chuyển đổi bản ghi ngành từ JSON/Excel sang giao diện ORM phục vụ chấm điểm 435 ngành."""
    def __init__(self, d: dict, mock_id: int):
        raw_id = d.get("id")
        try:
            self.id = uuid.UUID(str(raw_id)) if raw_id else uuid.uuid5(
                uuid.NAMESPACE_DNS, f"major-{d.get('major_code') or mock_id}"
            )
        except Exception:
            self.id = uuid.uuid5(uuid.NAMESPACE_DNS, f"major-{d.get('major_code') or mock_id}")
        self.major_code = d.get("major_code", "")
        self.name = d.get("name", "")
        self.category = d.get("category", "")
        self.riasec_vector = d.get("riasec") or d.get("riasec_vector") or {}
        self.cognitive_attributes = d.get("cognitive") or d.get("cognitive_attributes") or {}
        self.industry_outlook = d.get("outlook") or d.get("industry_outlook") or ""
        self.benchmark_cutoff = d.get("benchmark_cutoff")
        self.min_recommended = d.get("min_recommended")
        self.is_active = True
        raw_blocks = d.get("blocks", [])
        self.subject_blocks = [
            type("MSB", (), {"subject_block": type("SB", (), {"block_code": b})()})()
            for b in raw_blocks
        ]
        self.major_skills = []


def apply_constrained_diversity_reranking(
    scored_items: List[MajorRecommendationItem],
    top_k: int = 10,
    has_academic_scores: bool = True,
    target_trending_top5: int = 1,
    target_trending_top10: int = 2,
) -> List[MajorRecommendationItem]:
    """
    Bộ điều phối Đa dạng hóa Vị trí Có Ràng buộc (Constrained Diversity & Horizon Expansion Gate):
    1. Bảo toàn Đam mê cốt lõi (Ranks 1-3).
    2. Đảm bảo chắc chắn có ngành xu hướng:
       - Nếu top_k >= 10: Tối thiểu 1 ngành xu hướng trong Top 5, 2 ngành xu hướng trong Top 10.
       - Nếu 5 <= top_k < 10: Tối thiểu 1 ngành xu hướng trong Top 5.
       - Nếu 2 <= top_k < 5: Tối thiểu 1 ngành xu hướng tại slot top_k.
    3. Tìm kiếm ứng viên 2 cấp (Two-Level Search): tìm trong pool TARGET trước, nếu thiếu thì tìm trên toàn danh mục scored_items.
    4. Bảo toàn nguyên vẹn 100% nhãn tuyển sinh trung thực, tuyệt đối không che giấu trạng thái REACH.
    5. Khử trùng lặp tuyệt đối (Zero Duplication) và an toàn với has_academic_scores = False.
    """
    if not scored_items or top_k <= 0:
        return []

    # 1. Xác định Pool khả thi hợp lệ
    if has_academic_scores:
        eligible_pool = [it for it in scored_items if it.feasibility_tier in ("TARGET", "MATCH", "SAFE")]
        pool = list(eligible_pool if len(eligible_pool) >= top_k else scored_items)
    else:
        eligible_pool = [it for it in scored_items if it.feasibility_tier != "REACH"]
        pool = list(eligible_pool if len(eligible_pool) >= top_k else scored_items)

    # 2. Sắp xếp tự nhiên theo Feasibility, RankScore, OverallScore, RIASEC
    def _rank_key(item: MajorRecommendationItem):
        f_tier = 1 if (item.feasibility_tier in ("TARGET", "MATCH", "SAFE") or (not has_academic_scores and item.feasibility_tier == "UNKNOWN")) else 0
        breakdown = item.score_breakdown or {}
        boost = breakdown.get("trend_priority_boost", breakdown.get("trend_rank_boost", 0.0))
        rank_score = round(item.overall_score + boost, 6)
        return (f_tier, rank_score, item.overall_score, item.score_riasec)

    pool.sort(key=_rank_key, reverse=True)
    result = list(pool[:max(top_k * 2, 20)])
    if not result:
        result = list(pool)

    def _calculate_candidate_horizon_fit(candidate: MajorRecommendationItem, core_majors: List[MajorRecommendationItem]) -> Tuple[int, float]:
        max_pathway_tier = 0
        if core_majors:
            for core in core_majors:
                rel = are_majors_related_pathway(core.major_code, candidate.major_code)
                if rel > max_pathway_tier:
                    max_pathway_tier = rel
        affinity = 0.70 * candidate.score_riasec + 0.30 * candidate.score_preference
        composite_metric = (max_pathway_tier * 0.25) + (affinity * 0.50) + (candidate.overall_score * 0.25)
        return max_pathway_tier, composite_metric

    def _find_best_trending_candidate(exclude_codes: set, core_reference: List[MajorRecommendationItem]) -> Optional[MajorRecommendationItem]:
        best_cand = None
        best_rel_tier = -1
        best_metric = -1.0

        for cand in pool:
            if not cand.is_trending or cand.major_code in exclude_codes:
                continue
            if has_academic_scores and cand.feasibility_tier not in ("TARGET", "MATCH", "SAFE"):
                continue
            if not has_academic_scores and cand.feasibility_tier == "REACH":
                continue

            rel_tier, metric = _calculate_candidate_horizon_fit(cand, core_reference)
            if (rel_tier > best_rel_tier) or (rel_tier == best_rel_tier and metric > best_metric):
                best_rel_tier = rel_tier
                best_metric = metric
                best_cand = cand

        if best_cand is not None:
            return best_cand

        for cand in scored_items:
            if not cand.is_trending or cand.major_code in exclude_codes:
                continue
            if has_academic_scores and cand.feasibility_tier not in ("TARGET", "MATCH", "SAFE"):
                continue
            if not has_academic_scores and cand.feasibility_tier == "REACH":
                continue

            rel_tier, metric = _calculate_candidate_horizon_fit(cand, core_reference)
            if (rel_tier > best_rel_tier) or (rel_tier == best_rel_tier and metric > best_metric):
                best_rel_tier = rel_tier
                best_metric = metric
                best_cand = cand

        return best_cand

    # 3. Xử lý Ràng buộc Top 5
    effective_top5_slot = min(4, top_k - 1) if top_k >= 2 else 0
    top5_window_size = min(5, top_k)

    if top_k >= 2:
        current_trending = sum(1 for it in result[:top5_window_size] if it.is_trending)
        if current_trending < target_trending_top5:
            core_majors = result[:effective_top5_slot]
            existing_core_codes = {it.major_code for it in core_majors}
            best_cand_5 = _find_best_trending_candidate(existing_core_codes, core_majors)

            if best_cand_5 is not None:
                result = [it for it in result if it.major_code != best_cand_5.major_code]
                insert_idx = min(effective_top5_slot, len(result))
                result.insert(insert_idx, best_cand_5)

    # 4. Xử lý Ràng buộc Top 10
    if top_k >= 10:
        top10_trending = sum(1 for it in result[:10] if it.is_trending)
        if top10_trending < target_trending_top10:
            core_top10 = result[:9]
            existing_top10_codes = {it.major_code for it in core_top10}
            best_cand_10 = _find_best_trending_candidate(existing_top10_codes, result[:3])

            if best_cand_10 is not None:
                result = [it for it in result if it.major_code != best_cand_10.major_code]
                insert_idx_10 = min(9, len(result))
                result.insert(insert_idx_10, best_cand_10)

    # 5. Khử trùng lặp & Gán Rank 1-based
    seen_major_codes = set()
    final_output: List[MajorRecommendationItem] = []
    for item in result:
        if item.major_code in seen_major_codes:
            continue
        seen_major_codes.add(item.major_code)
        final_output.append(item)
        if len(final_output) == top_k:
            break

    if len(final_output) < top_k:
        for item in pool:
            if item.major_code not in seen_major_codes:
                seen_major_codes.add(item.major_code)
                final_output.append(item)
                if len(final_output) == top_k:
                    break

    for idx, item in enumerate(final_output, start=1):
        item.rank = idx

    return final_output


async def calculate_3pillar_recommendations(
    db: AsyncSession,
    user_id: uuid.UUID,
    payload: RecommendationRequest,
    inline_profile: Optional[Dict[str, Any]] = None,
    raise_if_unassessed: bool = False,
    persist_history: bool = True,
    *,
    resolved_profile: Optional[Dict[str, Any]] = None,
    include_all_candidates: bool = False,
) -> RecommendationResponse:
    """
    Động cơ Khuyến nghị Tất định 3 Trụ cột (FR04, NFR04) kết hợp Ràng buộc Điểm đa tầng:
    - Chuẩn hóa tên môn ('Vật lý'/'Vật lí', 'Địa lý'/'Địa lí') và tính đủ mọi tổ hợp môn.
    - Tuyệt đối không lấy điểm khối khác thay thế khi ngành không xét khối đó.
    - Chặn điểm liệt (<= 1.0đ), ngưỡng môn tiên quyết và ngưỡng điểm chuẩn thực tế trên 435 ngành TT74.
    """
    start_time = time.perf_counter()

    inline = resolved_profile if resolved_profile is not None else await resolve_assessment_evidence(db, user_id, inline_profile)
    diagnostic_tests: List[Any] = []
    user_row = None
    if db is not None and user_id is not None:
        try:
            result = await db.execute(select(User).where(User.id == user_id))
            user_row = result.scalars().first()
            result = await db.execute(select(StudentDiagnosticTest).where(StudentDiagnosticTest.user_id == user_id))
            diagnostic_tests = list(result.scalars().all())
        except Exception:
            diagnostic_tests = []

    interest_evidence = build_interest_evidence(inline.get("riasec_answers"), inline.get("riasec_scores"))
    student_riasec = _riasec_vector_from_answers(inline.get("riasec_answers")) or {
        key: float(value) for key, value in (inline.get("riasec_scores") or {}).items()
        if key in RIASEC_DIMENSIONS and isinstance(value, (int, float)) and not isinstance(value, bool)
        and math.isfinite(value) and 0 <= value <= 1
    }
    from .evidence import cognitive_evidence, score_observed_pillars, aspiration_preference_evidence, STRATEGIES, COGNITIVE_DIMENSIONS
    cognitive = cognitive_evidence(inline.get("cognitive_preferences"))
    student_pref = cognitive["traits"]
    aspiration = inline.get("aspiration") or {}
    strategy = aspiration.get("score_strategy", aspiration.get("scoreStrategy", "FLEXIBLE_PATHWAY"))
    strategy = strategy if strategy in STRATEGIES else "FLEXIBLE_PATHWAY"
    grade_validation = validate_readiness_grades(inline.get("grades_by_subject") or {})
    norm_raw_grades = {key: float(value) for key, value in grade_validation["scores"].items()}
    student_zscores = _exact_block_results(grade_validation["scores"])
    student_gender = payload.gender or inline.get("gender") or getattr(user_row, "gender", None)
    student_grade_level = payload.grade_level or inline.get("grade_level") or getattr(user_row, "grade_level", None)
    if raise_if_unassessed and not (student_riasec or norm_raw_grades or inline.get("cognitive_preferences")):
        raise HTTPException(status_code=422, detail={
            "code": "CHUA_HOAN_THANH_BAI_TEST",
            "message": "Vui lòng hoàn thành bài đánh giá sở thích và điểm học lực trước khi nhận đề xuất ngành.",
        })

    # Chỉ bài chẩn đoán xác nhận kỹ năng; điểm học bạ là bằng chứng nền tảng.
    mastered_skills = set()  # Transcript grades are foundations, not confirmed mastery.
    diag_mastered = infer_mastered_skills_from_diagnostic_tests([
        {"skill_code": d.skill_code, "score": d.score, "is_passed": d.is_passed}
        for d in diagnostic_tests
    ])
    mastered_skills.update(diag_mastered)

    # 2. HA-GAE v3.1 Trọng số thích ứng theo chân trời thời gian khối lớp (Simplex Harmonization)
    horizon_cfg = get_grade_horizon_config(student_grade_level)
    w_riasec = float(horizon_cfg.get("w_riasec", settings.WEIGHT_RIASEC))
    w_academic = float(horizon_cfg.get("w_academic", settings.WEIGHT_ACADEMIC))
    w_pref = float(horizon_cfg.get("w_preference", settings.WEIGHT_PREFERENCE))
    if payload.custom_weights:
        w_riasec = float(payload.custom_weights.get("w_riasec", w_riasec))
        w_academic = float(payload.custom_weights.get("w_academic", w_academic))
        w_pref = float(payload.custom_weights.get("w_preference", w_pref))

    # 3. Nạp cây kỹ năng tiên quyết
    prereq_map: Dict[str, List[str]] = {}
    if db is not None:
        try:
            prereq_res = await db.execute(
                select(SkillPrerequisite).options(
                    selectinload(SkillPrerequisite.skill),
                    selectinload(SkillPrerequisite.prerequisite_skill)
                )
            )
            for p in prereq_res.scalars().all():
                target_c = p.skill.skill_code if p.skill else ""
                source_c = p.prerequisite_skill.skill_code if p.prerequisite_skill else ""
                if target_c and source_c:
                    prereq_map.setdefault(target_c, []).append(source_c)
        except Exception:
            pass

    # 4. Danh mục đang hoạt động là nguồn có thẩm quyền; seed chỉ dùng khi DB trống.
    from app.services.taxonomy.service import load_seed_majors
    seed_data = load_seed_majors()
    seed_by_code = {str(m.get("major_code", "")): m for m in seed_data if m.get("major_code")}

    from .catalog import load_active_catalog
    catalog = await load_active_catalog(db)
    majors = [_MajorSeedAdapter(entry, idx) if isinstance(entry, dict) else entry
              for idx, entry in enumerate(catalog, start=1)]

    from app.services.taxonomy.trend_agent import (
        load_trending_registry_map,
        get_major_trend_info,
        get_trend_rank_boost,
    )
    trend_map = {} if db is not None else load_trending_registry_map()

    scored_items: List[MajorRecommendationItem] = []
    weights_dict = {"w_riasec": w_riasec, "w_academic": w_academic, "w_preference": w_pref}
    has_any_grades = bool(norm_raw_grades or student_zscores)

    for major in majors:
        seed_fallback = seed_by_code.get(major.major_code, {})
        trend_info = get_major_trend_info(
            major.major_code,
            trend_map=trend_map,
            cognitive_attributes=getattr(major, "cognitive_attributes", None),
        )
        bm_override = getattr(major, "benchmark_cutoff", None) or seed_fallback.get("benchmark_cutoff")
        min_override = getattr(major, "min_recommended", None) or seed_fallback.get("min_recommended")

        # --- NGƯỠNG ĐIỂM CHUẨN THAM CHIẾU ---
        bm_info = classify_major_academic_benchmark(
            major.major_code,
            major.name,
            getattr(major, "category", ""),
            benchmark_override=bm_override,
            min_recommended_override=min_override,
        )

        # --- TRỤ CỘT 1 (45%): Sở thích Holland RIASEC ---
        score_riasec = calculate_enhanced_riasec_fit(student_riasec, major.riasec_vector)

        # --- TRỤ CỘT 2 (35%): Năng lực học lực Z-Score & Ràng buộc khối + môn ---
        admitted_codes = [
            str(msb.subject_block.block_code).strip().upper()
            for msb in (getattr(major, "subject_blocks", None) or [])
            if getattr(msb, "subject_block", None) and msb.subject_block.block_code
        ]
        block_source = "SEED_DECLARED" if isinstance(major, _MajorSeedAdapter) else "DATABASE"
        if not admitted_codes:
            declared_blocks = seed_fallback.get("blocks") or []
            block_source = "SEED_DECLARED" if declared_blocks else "ASSUMED"
            admitted_codes = [str(b).strip().upper() for b in (declared_blocks or ["A00", "A01", "D01"]) if str(b).strip()]
        readiness = evaluate_current_readiness(
            raw_grades=inline.get("grades_by_subject") or {},
            admitted_blocks=admitted_codes,
            block_source=block_source,
            major_code=major.major_code,
            major_name=major.name,
            category=getattr(major, "category", "") or "",
            score_context=inline.get("score_context"),
            reference=seed_fallback.get("readiness_reference"),
        )
        selected_block = readiness.get("block")
        fit_blocks = [selected_block] if selected_block else admitted_codes
        score_academic, best_block, block_breakdown = evaluate_target_anchored_academic_fit(
            fit_blocks,
            student_zscores,
            benchmark_cutoff=readiness.get("benchmark_cutoff") or bm_info["benchmark_cutoff"],
            min_recommended=readiness.get("min_recommended") or bm_info["min_recommended"],
            raw_grades=norm_raw_grades,
            major_code=major.major_code,
            major_name=major.name,
            category=getattr(major, "category", "") or "",
        )

        # --- TRỤ CỘT 3 (20%): Thiên hướng nhận thức ---
        score_pref = calculate_asymmetric_cognitive_fit(student_pref, major.cognitive_attributes)

        # --- ĐIỂM TỔNG HỢP 3 TRỤ CỘT (THÍCH ỨNG ĐỘNG) ---
        availability = {
            "w_riasec": interest_evidence["status"] == "COMPLETE" and bool(major.riasec_vector),
            "w_academic": bool(best_block and best_block in student_zscores),
            "w_preference": cognitive["status"] == "COMPLETE" and any(
                (major.cognitive_attributes or {}).get(key) in values for key, values in COGNITIVE_DIMENSIONS.items()),
        }
        scores = {"w_riasec": score_riasec, "w_academic": score_academic, "w_preference": score_pref}
        overall_score, weights_dict = score_observed_pillars(
            scores, availability, {"w_riasec": w_riasec, "w_academic": w_academic, "w_preference": w_pref}, strategy)
        preferences = aspiration_preference_evidence(aspiration, major.cognitive_attributes or {})
        # A bounded preference contribution can refine fit, never academic eligibility.
        if preferences["score"] is not None and any(availability.values()):
            overall_score = round(0.9 * overall_score + 0.1 * preferences["score"], 4)

        # --- SUB-FACET AFFINITY & ASYMMETRIC VETO GATE (PA 3) ---
        # Chống hiệu ứng nén trung bình 6 chiều RIASEC (vd: thích A1/A2/A3/A5 nhưng chọn A4=1 ghét Âm nhạc).
        if availability["w_riasec"]:
            subfacet_gate = evaluate_subfacet_gate(
                major.major_code,
                major.name,
                inline.get("riasec_answers"),
            )
            if subfacet_gate["status"] != "NEUTRAL":
                score_riasec = round(
                    max(0.0, min(1.0, score_riasec * subfacet_gate["riasec_multiplier"] + subfacet_gate["riasec_boost"])),
                    4,
                )
                overall_score = round(
                    max(0.0, min(1.0, overall_score * subfacet_gate["overall_multiplier"] + subfacet_gate["overall_boost"])),
                    4,
                )
        else:
            subfacet_gate = {
                "status": "NEUTRAL",
                "riasec_multiplier": 1.0,
                "overall_multiplier": 1.0,
                "riasec_boost": 0.0,
                "overall_boost": 0.0,
                "matched_items": [],
                "note": None,
            }

        if not availability["w_riasec"]:
            score_riasec = 0.0
        if not availability["w_academic"]:
            score_academic = 0.0
        if not availability["w_preference"]:
            score_pref = 0.0

        # --- PHÂN TÍCH LỖ HỔNG KỸ NĂNG ---
        major_skills_list = [
            {
                "skill_code": ms.skill.skill_code,
                "name": ms.skill.name,
                "skill_type": ms.skill.skill_type.value if hasattr(ms.skill.skill_type, "value") else str(ms.skill.skill_type),
                "importance": ms.importance_level
            }
            for ms in (getattr(major, "major_skills", None) or []) if getattr(ms, "skill", None)
        ]
        overall_gaps, missing_pre, missing_tar = analyze_competency_gaps(
            required_major_skills=major_skills_list,
            skill_prerequisites_map=prereq_map,
            mastered_skill_codes=mastered_skills
        )

        # --- KIỂM TRA RÀNG BUỘC ĐIỂM ĐA TẦNG (KHÔNG LẤY CHÉO KHỐI) ---
        has_matched_block = bool(
            best_block and isinstance(block_breakdown, dict) and best_block in block_breakdown
        )
        if has_matched_block:
            raw_block_sum: Optional[float] = float(block_breakdown[best_block].get("raw_sum", 0.0))
            block_subjs: Optional[List[str]] = block_breakdown[best_block].get("subjects_used")
            effective_matched = True
        elif has_any_grades:
            # Có nhập điểm nhưng không khớp tổ hợp nào của ngành -> tuyệt đối không lấy khối khác thay thế
            raw_block_sum = None
            block_subjs = None
            effective_matched = False
        else:
            # Chưa nhập bất kỳ điểm học lực nào -> KHÔNG suy đoán điểm khối (trước đây hard-code 21.5đ).
            # Trả về tier UNKNOWN để giao diện không đưa ra kết luận TARGET/REACH sai lệch.
            raw_block_sum = None
            block_subjs = None
            effective_matched = False

        feasibility = evaluate_admission_feasibility(
            raw_block_sum=raw_block_sum,
            major_code=major.major_code,
            major_name=major.name,
            category=getattr(major, "category", "") or "",
            has_matched_block=effective_matched,
            best_block=best_block,
            raw_grades=norm_raw_grades,
            admitted_blocks=admitted_codes,
            block_subjects=block_subjs,
            benchmark_override=bm_override,
            min_recommended_override=min_override,
            has_academic_data=has_any_grades,
        )

        if readiness.get("block"):
            best_block = readiness["block"]
            readiness_tier = {"READY_REFERENCE": "TARGET", "NEEDS_IMPROVEMENT": "REACH", "UNKNOWN": "UNKNOWN"}[readiness["status"]]
            feasibility.update({
                "feasibility_tier": readiness_tier,
                "feasibility_label": {"TARGET": "Đạt mốc tham chiếu", "REACH": "Cần cải thiện", "UNKNOWN": "Chưa đủ bằng chứng"}[readiness_tier],
                "constraint_passed": readiness["status"] == "READY_REFERENCE",
                "constraint_violations": readiness.get("violations", []),
                "admission_advice": readiness.get("message"),
                "best_block_score": readiness.get("block_score"),
                "benchmark_cutoff": readiness.get("benchmark_cutoff"),
                "min_recommended": readiness.get("min_recommended"),
                "score_gap": (readiness["block_score"] - readiness["benchmark_cutoff"])
                    if readiness.get("block_score") is not None and readiness.get("benchmark_cutoff") is not None else None,
            })

        # --- GIẢI THÍCH XAI TẤT ĐỊNH & TINH GỌN ---
        top_factors, summary_expl = generate_xai_top_supporting_factors(
            major_name=major.name,
            score_riasec=score_riasec,
            student_riasec=student_riasec,
            major_riasec=major.riasec_vector,
            score_academic=score_academic,
            best_block=best_block,
            score_pref=score_pref,
            student_pref=student_pref,
            major_attr=major.cognitive_attributes,
            admission_band=feasibility["feasibility_tier"],
            has_academic_scores=has_any_grades,
            trend_tier=trend_info["trend_tier"] or "NONE",
            trend_label=trend_info["trend_label"] or "",
        )

        trend_compat = calculate_market_trend_compatibility(
            trend_tier=trend_info["trend_tier"],
            score_riasec=score_riasec,
            score_pref=score_pref,
            overall_score=overall_score,
        )

        if feasibility["feasibility_tier"] == "REACH":
            top_factors.insert(0, f"Chặn ràng buộc điểm: {feasibility['feasibility_label']}. {feasibility['admission_advice']}")
        elif feasibility["feasibility_tier"] == "UNKNOWN":
            top_factors.insert(
                0,
                f"Chưa đủ dữ liệu xét tuyển: {feasibility['admission_advice']}",
            )
        else:
            disp_sum = feasibility["best_block_score"] if feasibility["best_block_score"] is not None else raw_block_sum
            top_factors.insert(0, f"Đạt ngưỡng tuyển sinh: Khối {best_block or 'xét tuyển'} ({disp_sum}đ) phù hợp mức chuẩn (~{feasibility['benchmark_cutoff']}đ).")

        if trend_info["is_trending"]:
            reason_snip = f" — {trend_info['trend_reason']}" if trend_info.get("trend_reason") else ""
            top_factors.insert(1, f"{trend_info['trend_label']}{reason_snip}")

        if subfacet_gate.get("note"):
            if subfacet_gate["status"] in ("STRONG_VETO", "SOFT_PENALTY"):
                top_factors.insert(0, subfacet_gate["note"])
            else:
                top_factors.append(subfacet_gate["note"])

        # HA-GAE v3.1 Thích ứng chân trời khối lớp và bối cảnh giới tính (3-Sentence XAI)
        horizon_xai = build_horizon_gender_xai_explanation(
            major_name=major.name,
            major_code=major.major_code,
            category=getattr(major, "category", "") or "",
            score_riasec=score_riasec,
            score_academic=score_academic,
            score_pref=score_pref,
            feasibility_tier=feasibility["feasibility_tier"],
            grade_level=student_grade_level,
            gender=student_gender,
            best_matching_block=best_block,
            score_gap=feasibility.get("score_gap"),
        )

        init_tactic = "NV3-5 (Vừa sức)"
        if feasibility["feasibility_tier"] == "REACH":
            init_tactic = "NV1-2 (Bứt phá)"
        elif feasibility.get("score_gap") is not None and feasibility.get("score_gap", 0) >= 2.0:
            init_tactic = "NV6+ (Dự phòng)"
        elif feasibility["feasibility_tier"] == "UNKNOWN":
            init_tactic = "Định hướng sở thích"

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
            readiness=readiness,
            score_breakdown={
                "weights": weights_dict,
                "readiness": readiness,
                "interest_evidence_status": interest_evidence["status"],
                "cognitive_evidence": cognitive,
                "pillar_availability": availability,
                "aspiration_preferences": preferences,
                "score_strategy": strategy,
                "score_meaning": "HEURISTIC_FIT_NOT_ADMISSION_PROBABILITY",
                "skill_evidence_basis": "DIAGNOSTICS_ONLY",
                "score_riasec": score_riasec,
                "score_academic": score_academic,
                "score_preference": score_pref,
                "admitted_blocks_evaluated": block_breakdown,
                "feasibility": feasibility,
                "trend_priority_boost": trend_compat["rank_boost"],
                "trend_compat_score": trend_compat["trend_compat_score"],
                "affinity": trend_compat["affinity"],
                "subfacet_gate": subfacet_gate,
            },
            top_supporting_factors=top_factors,
            competency_gaps=overall_gaps[:5],
            missing_prerequisites=missing_pre[:3],
            missing_target_skills=missing_tar[:3],
            explanation=horizon_xai or summary_expl,
            feasibility_tier=feasibility["feasibility_tier"],
            feasibility_label=feasibility["feasibility_label"],
            benchmark_cutoff=feasibility["benchmark_cutoff"],
            min_recommended=feasibility["min_recommended"],
            best_block_score=feasibility["best_block_score"],
            score_gap=feasibility["score_gap"],
            constraint_passed=feasibility["constraint_passed"],
            constraint_violations=feasibility["constraint_violations"],
            admission_advice=feasibility["admission_advice"],
            academic_tier=feasibility["academic_tier"],
            academic_tier_label=feasibility["academic_tier_label"],
            is_trending=trend_info["is_trending"],
            trend_tier=trend_info["trend_tier"],
            trend_priority=trend_info["trend_priority"],
            trend_label=trend_info["trend_label"],
            trend_reason=trend_info["trend_reason"],
            trend_sources=trend_info["trend_sources"],
            nudge_badge=None,
            advisory_note=None,
            admission_tactic=init_tactic,
        ))

    from .aspiration_agent import _resolve_intent
    interest_complete = interest_evidence["status"] == "COMPLETE"
    has_explicit_refs = any(m.readiness.get("reason") != "REFERENCE_BASIS_MISSING" for m in scored_items)

    if interest_complete and not has_explicit_refs:
        # 1. Smart Sibling / Pathway Substitution for blocked high-cutoff majors
        eligible_targets = [it for it in scored_items if it.feasibility_tier == "TARGET"]
        blocked_reaches = [it for it in scored_items if it.feasibility_tier == "REACH"]
        blocked_reaches.sort(
            key=lambda it: (0.70 * it.score_riasec + 0.30 * it.score_preference),
            reverse=True,
        )
        substituted_codes = set()
        for blocked in blocked_reaches[:6]:
            if blocked.score_riasec < 0.65:
                continue
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
                    "cùng nhóm ngành"
                    if best_rel_tier == 3
                    else (
                        "cùng lĩnh vực / nhánh Công nghệ Kỹ thuật ứng dụng"
                        if best_rel_tier == 2
                        else "nhóm ngành liên thông gần gũi"
                    )
                )
                sub_msg = (
                    f"Đề xuất thay thế vừa sức cho ngành {blocked.major_name} (điểm chuẩn ~{blocked.benchmark_cutoff}đ): "
                    f"Giữ trọn định hướng sở thích ({round(best_sub.score_riasec * 100, 1)}%) thuộc {pathway_desc} "
                    f"nhưng có ngưỡng điểm an toàn (~{best_sub.benchmark_cutoff}đ)."
                )
                best_sub.admission_advice = sub_msg
                best_sub.top_supporting_factors.insert(0, sub_msg)

        # 2. HA-GAE v3.1 Tái xếp hạng thích ứng Khối lớp (Lớp 10/11/12/Tốt nghiệp) & Giới tính
        has_academic = has_any_grades and any(v is not None and v > 0 for v in norm_raw_grades.values())
        effective_top_k = len(scored_items) if include_all_candidates else payload.top_k
        top_results = apply_horizon_gender_reranking(
            scored_items=scored_items,
            grade_level=student_grade_level,
            gender=student_gender,
            top_k=effective_top_k,
            has_academic_scores=has_academic,
            target_trending_top5=1,
            target_trending_top10=2,
            student_riasec_dict=student_riasec,
        )
        if include_all_candidates and len(top_results) < len(scored_items):
            included_codes = {it.major_code for it in top_results}
            for extra in scored_items:
                if extra.major_code not in included_codes:
                    top_results.append(extra)
                    included_codes.add(extra.major_code)

        for item in scored_items:
            item.explanation = build_horizon_gender_xai_explanation(
                major_name=item.major_name,
                major_code=item.major_code,
                category=item.category or "",
                score_riasec=item.score_riasec,
                score_academic=item.score_academic,
                score_pref=item.score_preference,
                feasibility_tier=item.feasibility_tier,
                grade_level=student_grade_level,
                gender=student_gender,
                best_matching_block=item.best_matching_block,
                score_gap=item.score_gap,
            )
            _publish_readiness(item, preserve_complete_feasibility=True)

        match_status, _, goals = _resolve_intent(
            aspiration.get("dream_job", aspiration.get("dreamJob", "")),
            aspiration.get("desired_field", aspiration.get("desiredField", "")),
            scored_items,
            seed_by_code,
        )
        goal_codes = {item.major_code for item in goals} if match_status == "MATCHED" else set()
        for item in scored_items:
            item.score_breakdown["aspiration_relation"] = "DIRECT_GOAL" if item.major_code in goal_codes else "OTHER"
        for rank, item in enumerate(top_results, 1):
            item.rank = rank
    else:
        # All candidates receive authoritative readiness BEFORE any top-k selection.
        for item in scored_items:
            _publish_readiness(item, preserve_complete_feasibility=False)
        match_status, _, goals = _resolve_intent(
            aspiration.get("dream_job", aspiration.get("dreamJob", "")),
            aspiration.get("desired_field", aspiration.get("desiredField", "")),
            scored_items,
            seed_by_code,
        )
        goal_codes = {item.major_code for item in goals} if match_status == "MATCHED" else set()
        for item in scored_items:
            item.score_breakdown["aspiration_relation"] = "DIRECT_GOAL" if item.major_code in goal_codes else "OTHER"

        def order(item):
            tier = {"TARGET": 0, "UNKNOWN": 1, "REACH": 2}[item.feasibility_tier]
            margin = item.score_gap if item.score_gap is not None else float("-inf")
            return (
                tier,
                0 if item.major_code in goal_codes else 1,
                -margin if strategy == "REALISTIC_SAFE" and tier == 0 else 0,
                -item.overall_score,
                item.major_code,
            )

        top_results = sorted(scored_items, key=order)
        if not include_all_candidates:
            top_results = [item for item in top_results if item.feasibility_tier != "REACH"][:payload.top_k]
        for rank, item in enumerate(top_results, 1):
            item.rank = rank

    # Summary weights describe observed profile evidence; each item's weights are authoritative.
    _, summary_weights = score_observed_pillars(
        {"w_riasec": 0, "w_academic": 0, "w_preference": 0},
        {"w_riasec": interest_evidence["status"] == "COMPLETE",
         "w_academic": bool(student_zscores), "w_preference": cognitive["status"] == "COMPLETE"},
        {"w_riasec": w_riasec, "w_academic": w_academic, "w_preference": w_pref}, strategy)

    # Lưu lịch sử đề xuất cho người dùng đã đăng nhập
    generated_now = datetime.now(timezone.utc)
    if persist_history and db is not None:
        try:
            history = RecommendationHistory(
                user_id=user_id,
                weights_applied=summary_weights,
                ranked_results=[it.model_dump(mode="json") for it in top_results[:15]],
                generated_at=generated_now
            )
            db.add(history)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            raise HTTPException(503,"Không lưu được lịch sử đề xuất; hãy thử lại.") from exc

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    print(f"3-Pillar Recommendation Engine evaluated {len(majors)} majors in {elapsed_ms:.2f}ms.")

    return RecommendationResponse(
        user_id=user_id,
        generated_at=generated_now,
        weights_applied=summary_weights,
        total_majors_evaluated=len(majors),
        recommendations=top_results
    )


FIELD_ICONS_MAP = {
    "máy tính": "💻",
    "kinh doanh": "📊",
    "công nghệ kỹ thuật": "⚙️",
    "kỹ thuật": "🔧",
    "sức khỏe": "🩺",
    "giáo dục": "📚",
    "xã hội": "🌐",
    "kiến trúc": "🏛️",
    "nghệ thuật": "🎨",
    "nhân văn": "📖",
    "báo chí": "📰",
    "pháp luật": "⚖️",
    "nông": "🌱",
    "môi trường": "🌿",
    "du lịch": "✈️",
    "an ninh": "🛡️",
    "toán": "📐",
    "khoa học tự nhiên": "🔬",
    "khoa học sự sống": "🧬",
    "vận tải": "🚢",
}


def _resolve_field_icon(category_name: str) -> str:
    low = (category_name or "").lower()
    for key, icon in FIELD_ICONS_MAP.items():
        if key in low:
            return icon
    return "🎓"


STANDARD_FIELD_DISPLAY_MAP: Dict[str, str] = {
    "máy tính và công nghệ thông tin": "Máy tính & Công nghệ thông tin",
    "kinh doanh và quản lý": "Kinh doanh & Quản lý",
    "công nghệ kỹ thuật": "Công nghệ kỹ thuật",
    "kỹ thuật": "Kỹ thuật",
    "sức khỏe": "Sức khỏe",
    "khoa học giáo dục và đào tạo giáo viên": "Khoa học giáo dục & Đào tạo giáo viên",
    "khoa học xã hội và hành vi": "Khoa học xã hội & Hành vi",
    "kiến trúc và xây dựng": "Kiến trúc & Xây dựng",
    "nghệ thuật": "Nghệ thuật",
    "nhân văn": "Nhân văn",
    "báo chí và thông tin": "Báo chí & Thông tin",
    "pháp luật": "Pháp luật",
    "nông lâm nghiệp và thủy sản": "Nông, lâm nghiệp & Thủy sản",
    "môi trường và bảo vệ môi trường": "Môi trường & Bảo vệ môi trường",
    "du lịch khách sạn thể thao và dịch vụ cá nhân": "Du lịch, Khách sạn, Thể thao & Dịch vụ cá nhân",
    "du lịch khách sạn thể thao và dịch và cá nhân": "Du lịch, Khách sạn, Thể thao & Dịch vụ cá nhân",
    "an ninh quốc phòng": "An ninh, Quốc phòng",
    "toán và thống kê": "Toán & Thống kê",
    "khoa học tự nhiên": "Khoa học tự nhiên",
    "khoa học sự sống": "Khoa học sự sống",
    "dịch vụ vận tải": "Dịch vụ vận tải",
    "dịch vụ xã hội": "Dịch vụ xã hội",
    "sản xuất và chế biến": "Sản xuất & Chế biến",
    "thú y": "Thú y",
}


def _canonical_field_key(category_name: str) -> str:
    import re
    import unicodedata

    norm = unicodedata.normalize("NFC", (category_name or "Khác")).strip().lower()
    norm = norm.replace("&", " và ")
    norm = re.sub(r"[,;/\-]+", " ", norm)
    norm = re.sub(r"\s+", " ", norm).strip()
    return norm or "khác"


def _format_vietnamese_field_name(category_name: str) -> str:
    import unicodedata

    raw = unicodedata.normalize("NFC", (category_name or "Khác")).strip()
    if not raw:
        return "Khác"
    canon = _canonical_field_key(raw)
    if canon in STANDARD_FIELD_DISPLAY_MAP:
        return STANDARD_FIELD_DISPLAY_MAP[canon]
    if raw.isupper():
        lowered = raw.lower()
        return lowered[:1].upper() + lowered[1:]
    return raw


def build_two_tier_funnel_payload(
    recommendations: List[MajorRecommendationItem],
    top_fields: int = 3,
    majors_per_field: int = 3,
    grade_level: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Xây dựng dữ liệu Phễu Đề xuất 2 Tầng (Tầng 1: Top 3 lĩnh vực -> Tầng 2: Top 3 ngành mỗi lĩnh vực).
    Ưu tiên đưa các ngành ĐẠT ràng buộc điểm (TARGET) lên trước trong từng lĩnh vực.
    Tích hợp nhãn chân trời thời gian theo khối lớp (HA-GAE v3.1).
    """
    from collections import defaultdict
    from app.services.taxonomy.trend_agent import get_trend_rank_boost

    horizon_cfg = get_grade_horizon_config(grade_level)
    tau = float(horizon_cfg.get("tau", 0.25))

    groups: Dict[str, List[MajorRecommendationItem]] = defaultdict(list)
    raw_cat_by_key: Dict[str, str] = {}
    for item in recommendations:
        if item.feasibility_tier == "REACH":
            if tau < 0.65 or item.admission_tactic == "Nguy cơ cao":
                continue
        cat = item.category or "Khác"
        key = _canonical_field_key(cat)
        if key not in raw_cat_by_key:
            raw_cat_by_key[key] = cat
        groups[key].append(item)

    if not groups and recommendations:
        for item in recommendations:
            if item.admission_tactic == "Nguy cơ cao":
                continue
            cat = item.category or "Khác"
            key = _canonical_field_key(cat)
            if key not in raw_cat_by_key:
                raw_cat_by_key[key] = cat
            groups[key].append(item)

    tier1_fields: List[Dict[str, Any]] = []
    for key, items in groups.items():
        cat_name = raw_cat_by_key[key]
        display_name = _format_vietnamese_field_name(cat_name)
        def _is_strong_veto(m: MajorRecommendationItem) -> bool:
            return (m.score_breakdown or {}).get("subfacet_gate", {}).get("status") == "STRONG_VETO"

        non_vetoed = [m for m in items if not _is_strong_veto(m)]
        candidate_items = non_vetoed if non_vetoed else items
        if tau >= 0.65:
            sorted_items = sorted(candidate_items, key=lambda m: (_is_strong_veto(m), m.admission_tactic == "Nguy cơ cao", m.rank))
        else:
            sorted_items = sorted(candidate_items, key=lambda m: (_is_strong_veto(m), m.feasibility_tier != "TARGET", m.rank))
        sample_top = sorted_items[:majors_per_field]
        target_cnt = sum(
            1 for m in candidate_items
            if m.readiness.get("status") == "READY_REFERENCE" or m.feasibility_tier == "TARGET"
        )
        avg_score = sum(m.overall_score for m in sample_top) / len(sample_top)
        max_trend_boost = max(
            (get_trend_rank_boost(m.trend_tier, m.overall_score) for m in sample_top),
            default=0.0,
        )
        max_trend_pri = max(
            (m.trend_priority for m in sample_top),
            default=0,
        )
        trend_field_bonus = 0.08 if max_trend_pri == 3 else (0.04 if max_trend_pri == 2 else 0.0)
        tier1_fields.append({
            "field_name": display_name,
            "raw_category": cat_name,
            "icon": _resolve_field_icon(display_name),
            "match": int(round(avg_score * 100)) if any(m.match is not None for m in sample_top) else None,
            "rank_score": avg_score,
            "max_trend_priority": max_trend_pri,
            "majors_count": len(items),
            "eligible_count": target_cnt,
            "has_eligible": target_cnt > 0 and bool(non_vetoed),
            "has_non_vetoed": bool(non_vetoed),
            "majors": sample_top,
        })

    # Ưu tiên các lĩnh vực chuyên môn cụ thể (tránh đưa nhóm "Khác" mã 9090 lên đầu), không bị phủ quyết, có ngành đạt chuẩn & % phù hợp
    tier1_fields.sort(
        key=lambda f: (
            0 if _canonical_field_key(f["field_name"]) == "khác" else 1,
            1 if f["has_non_vetoed"] else 0,
            1 if f["has_eligible"] else 0,
            round(f["rank_score"], 4),
            f["match"] if f["match"] is not None else -1
        ),
        reverse=True,
    )
    selected_tier1 = tier1_fields[:top_fields]

    return {
        "horizon_label": horizon_cfg.get("label"),
        "horizon_tau": horizon_cfg.get("tau"),
        "tier1_fields": selected_tier1,
        "all_majors": [
            m for m in recommendations
            if m.feasibility_tier != "REACH"
            and (m.score_breakdown or {}).get("subfacet_gate", {}).get("status") != "STRONG_VETO"
        ][:30],
        "total_evaluated": len(recommendations),
        "total_eligible": sum(1 for m in recommendations if m.readiness.get("status") == "READY_REFERENCE"),
        "total_blocked": sum(1 for m in recommendations if m.feasibility_tier == "REACH"),
    }


async def evaluate_dashboard_profile_bundle(
    db: AsyncSession,
    user_id: uuid.UUID,
    top_k: int = 500,
    custom_weights: Optional[Dict[str, float]] = None,
    inline_profile: Optional[Dict[str, Any]] = None,
    raise_if_unassessed: bool = False,
    persist_history: bool = False,
    user_name: Optional[str] = None,
    gender: Optional[str] = None,
    grade_level: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Tính toán trọn bộ dữ liệu Dashboard & Ràng buộc Điểm trên toàn bộ 435 ngành TT74:
    - Trả về 2-Tier Funnel, danh sách ngành kèm trạng thái TARGET/REACH/SAFETY, biểu đồ Radar và Khối mạnh nhất.
    - Tự động thích ứng theo chân trời thời gian khối lớp và công thái học giới tính (HA-GAE v3.1).
    """
    inline = await resolve_assessment_evidence(db, user_id, inline_profile)
    effective_gender = gender or inline.get("gender")
    effective_grade_level = grade_level or inline.get("grade_level")

    if db is not None and user_id is not None and (not effective_gender or not effective_grade_level):
        try:
            u_res = await db.execute(select(User).where(User.id == user_id))
            u_row = u_res.scalars().first()
            if u_row:
                effective_gender = effective_gender or u_row.gender
                effective_grade_level = effective_grade_level or u_row.grade_level
        except Exception:
            pass

    req = RecommendationRequest(
        top_k=top_k,
        custom_weights=custom_weights,
        gender=effective_gender,
        grade_level=effective_grade_level,
    )
    rec_resp = await calculate_3pillar_recommendations(
        db=db,
        user_id=user_id,
        payload=req,
        inline_profile=inline,
        raise_if_unassessed=raise_if_unassessed,
        persist_history=persist_history,
        resolved_profile=inline,
        include_all_candidates=True,
    )
    interest_evidence = build_interest_evidence(inline.get("riasec_answers"), inline.get("riasec_scores"))
    student_riasec = _riasec_vector_from_answers(inline.get("riasec_answers")) or inline.get("riasec_scores") or {}
    grade_validation = validate_readiness_grades(inline.get("grades_by_subject") or {})
    norm_raw_grades = {key: float(value) for key, value in grade_validation["scores"].items()}
    student_zscores = _exact_block_results(grade_validation["scores"])
    has_academic_data = bool(norm_raw_grades)
    riasec_data, best_block_stats = build_radar_and_block_summary(student_riasec, student_zscores, norm_raw_grades)
    # The chart displays observed evidence, never the scorer's neutral defaults.
    interest_by_code = {group["code"]: group for group in interest_evidence["groups"]}
    subject_pairs = {"R": ("Vật lý", "Toán"), "I": ("Toán", "Hóa học"), "A": ("Ngữ văn", "Tiếng Anh"),
                     "S": ("Ngữ văn", "Lịch sử"), "E": ("Tiếng Anh", "Toán"), "C": ("Toán", "Tin học / Công nghệ")}
    for point in riasec_data:
        group = interest_by_code[point["key"]]
        point["value"] = group["percent"] if group.get("answered") else None
        point["answered"] = group.get("answered")
        observed = [norm_raw_grades[subj] for subj in subject_pairs[point["key"]] if subj in norm_raw_grades]
        point["academicValue"] = round(sum(observed) / len(observed) * 10) if observed else None
    best_block_stats["has_academic_data"] = has_academic_data
    best_block_stats["grade_errors"] = grade_validation["errors"]

    funnel_payload = build_two_tier_funnel_payload(
        rec_resp.recommendations,
        grade_level=effective_grade_level,
    )

    # Thực thi AI Agent Phân tích Nguyện vọng & Đối chiếu Trắc nghiệm 3 Trụ cột
    from app.services.recommender.aspiration_agent import analyze_career_aspiration
    aspiration_analysis = await analyze_career_aspiration(
        aspiration_data=inline.get("aspiration"),
        student_riasec=student_riasec,
        best_block_stats=best_block_stats,
        all_ranked_majors=rec_resp.recommendations,
        enable_llm=False,
        interest_evidence=interest_evidence,
    )

    visible_majors = [item for item in rec_resp.recommendations if item.feasibility_tier != "REACH"]
    return {
        "has_assessment": True,
        "has_academic_data": has_academic_data,
        "user_name": user_name or "Học sinh",
        "gender": effective_gender,
        "grade_level": effective_grade_level,
        "horizon_label": funnel_payload.get("horizon_label"),
        "horizon_tau": funnel_payload.get("horizon_tau"),
        "total_majors_evaluated": rec_resp.total_majors_evaluated,
        "weights_applied": rec_resp.weights_applied,
        "riasecData": riasec_data,
        "bestBlockStats": best_block_stats,
        "majors": visible_majors[:top_k],
        "blocked_goals": [item for item in rec_resp.recommendations if item.feasibility_tier == "REACH"],
        "funnel": funnel_payload,
        "aspirationAnalysis": aspiration_analysis,
        "interest_evidence": interest_evidence,
        "evidence_source": inline.get("evidence_source"),
        "assessment_id": inline.get("assessment_id"),
    }
