import logging
import time
import uuid

logger = logging.getLogger(__name__)
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from fastapi import HTTPException, status
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
    normalize_grades_dict,
    normalize_student_cognitive_traits,
    build_radar_and_block_summary,
)

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
    if not raw_answers:
        return None
    sums = {dim: 0.0 for dim in RIASEC_DIMENSIONS}
    counts = {dim: 0 for dim in RIASEC_DIMENSIONS}
    for q_key, val in raw_answers.items():
        prefix = str(q_key).strip()[:1].upper()
        if prefix in sums:
            try:
                num = max(1.0, min(5.0, float(val)))
                sums[prefix] += num
                counts[prefix] += 1
            except (TypeError, ValueError):
                continue
    if sum(counts.values()) == 0:
        return None
    vec: Dict[str, float] = {}
    for dim in RIASEC_DIMENSIONS:
        if counts[dim] > 0:
            norm_v = (sums[dim] / counts[dim] - 1.0) / 4.0
            vec[dim] = round(max(0.0, min(1.0, norm_v)), 4)
        else:
            vec[dim] = 0.5
    if all(v <= 0.0 for v in vec.values()):
        return {dim: 0.2 for dim in RIASEC_DIMENSIONS}
    return vec


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


async def calculate_3pillar_recommendations(
    db: AsyncSession,
    user_id: uuid.UUID,
    payload: RecommendationRequest,
    inline_profile: Optional[Dict[str, Any]] = None,
    raise_if_unassessed: bool = False,
    persist_history: bool = True,
) -> RecommendationResponse:
    """
    Động cơ Khuyến nghị Tất định 3 Trụ cột (FR04, NFR04) kết hợp Ràng buộc Điểm đa tầng:
    - Chuẩn hóa tên môn ('Vật lý'/'Vật lí', 'Địa lý'/'Địa lí') và tính đủ mọi tổ hợp môn.
    - Tuyệt đối không lấy điểm khối khác thay thế khi ngành không xét khối đó.
    - Chặn điểm liệt (<= 1.0đ), ngưỡng môn tiên quyết và ngưỡng điểm chuẩn thực tế trên 435 ngành TT74.
    """
    start_time = time.perf_counter()

    # 1. Nạp hồ sơ từ DB (nếu có user trong DB) và ghép với inline_profile (nếu FE gửi trực tiếp)
    assessment = None
    grade = None
    diagnostic_tests: List[Any] = []
    if db is not None:
        try:
            assess_res = await db.execute(
                select(StudentAssessment)
                .where(StudentAssessment.user_id == user_id)
                .order_by(StudentAssessment.assessed_at.desc())
            )
            assessment = assess_res.scalars().first()

            grade_res = await db.execute(
                select(StudentGrade)
                .where(StudentGrade.user_id == user_id)
                .order_by(StudentGrade.created_at.desc())
            )
            grade = grade_res.scalars().first()

            diag_res = await db.execute(
                select(StudentDiagnosticTest).where(StudentDiagnosticTest.user_id == user_id)
            )
            diagnostic_tests = list(diag_res.scalars().all())
        except Exception:
            assessment = None
            grade = None
            diagnostic_tests = []

    inline = inline_profile or {}
    inline_riasec = inline.get("riasec_scores") or _riasec_vector_from_answers(inline.get("riasec_answers"))
    inline_pref = inline.get("cognitive_preferences") or inline.get("cognitive_answers")
    inline_grades = normalize_grades_dict(inline.get("grades_by_subject"))

    has_db_assess = bool(assessment and (assessment.riasec_scores or assessment.cognitive_preferences))
    has_db_grades = bool(grade and (grade.grades_by_subject or grade.computed_block_zscores))
    has_inline = bool(inline_riasec or inline_pref or inline_grades)

    if raise_if_unassessed and not (has_db_assess or has_db_grades or has_inline):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "CHUA_HOAN_THANH_BAI_TEST",
                "message": "Vui lòng hoàn thành bài đánh giá sở thích và điểm học lực trước khi nhận đề xuất ngành.",
            },
        )

    student_riasec = (
        inline_riasec
        or (assessment.riasec_scores if assessment and assessment.riasec_scores else None)
        or {"R": 0.5, "I": 0.5, "A": 0.5, "S": 0.5, "E": 0.5, "C": 0.5}
    )
    student_pref = normalize_student_cognitive_traits(
        inline_pref
        or (assessment.cognitive_preferences if assessment and assessment.cognitive_preferences else {})
    )

    if inline_grades:
        norm_raw_grades = inline_grades
        student_zscores = compute_block_zscores_from_grades(norm_raw_grades)
    else:
        norm_raw_grades = normalize_grades_dict(
            grade.grades_by_subject if grade and grade.grades_by_subject else {}
        )
        if norm_raw_grades:
            student_zscores = compute_block_zscores_from_grades(norm_raw_grades)
        elif grade and grade.computed_block_zscores:
            student_zscores = dict(grade.computed_block_zscores)
        else:
            student_zscores = {}

    # Suy luận kỹ năng đã đạt từ điểm học lực (đã chuẩn hóa tên môn) và bài test chẩn đoán
    mastered_skills = infer_mastered_skills_from_grades(norm_raw_grades)
    diag_mastered = infer_mastered_skills_from_diagnostic_tests([
        {"skill_code": d.skill_code, "score": d.score, "is_passed": d.is_passed}
        for d in diagnostic_tests
    ])
    mastered_skills.update(diag_mastered)

    # 2. Trọng số chuẩn 3 trụ cột (0.45, 0.35, 0.20)
    w_riasec = settings.WEIGHT_RIASEC
    w_academic = settings.WEIGHT_ACADEMIC
    w_pref = settings.WEIGHT_PREFERENCE
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

    # 4. Nạp danh mục ngành chuẩn TT74/2026 (đảm bảo đủ 435 ngành kể cả khi DB mới chỉ có 108 ngành TT09 cũ)
    from app.services.taxonomy.service import load_seed_majors
    seed_data = load_seed_majors()
    seed_by_code = {str(m.get("major_code", "")): m for m in seed_data if m.get("major_code")}

    majors: List[Any] = []
    if db is not None:
        try:
            majors_query = select(Major).where(Major.is_active == True).options(
                selectinload(Major.subject_blocks).selectinload(MajorSubjectBlock.subject_block),
                selectinload(Major.major_skills).selectinload(MajorSkill.skill)
            )
            majors_res = await db.execute(majors_query)
            majors = list(majors_res.scalars().all())
        except Exception as db_err:
            logger.warning("Truy vấn DB thất bại trong recommender, chuyển sang seed TT74: %s", db_err)
            majors = []

    if not majors:
        majors = [_MajorSeedAdapter(m, idx) for idx, m in enumerate(seed_data, start=1)]
    elif len(majors) <= 150 and len(seed_data) >= 400:
        # Bổ sung các ngành TT74 chưa được import vào DB để luôn chấm đủ 435 ngành chuẩn
        existing_codes = {m.major_code for m in majors}
        for idx, m_dict in enumerate(seed_data, start=1):
            if m_dict.get("major_code") not in existing_codes:
                majors.append(_MajorSeedAdapter(m_dict, idx))

    from app.services.taxonomy.trend_agent import (
        load_trending_registry_map,
        get_major_trend_info,
        get_trend_rank_boost,
    )
    trend_map = load_trending_registry_map()

    scored_items: List[MajorRecommendationItem] = []
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
        if not admitted_codes:
            admitted_codes = [
                str(b).strip().upper()
                for b in (seed_fallback.get("blocks") or ["A00", "A01", "D01"])
                if str(b).strip()
            ]

        score_academic, best_block, block_breakdown = evaluate_target_anchored_academic_fit(
            admitted_codes,
            student_zscores,
            benchmark_cutoff=bm_info["benchmark_cutoff"],
            min_recommended=bm_info["min_recommended"],
            raw_grades=norm_raw_grades,
            major_code=major.major_code,
            major_name=major.name,
            category=getattr(major, "category", "") or "",
        )

        # --- TRỤ CỘT 3 (20%): Thiên hướng nhận thức ---
        score_pref = calculate_asymmetric_cognitive_fit(student_pref, major.cognitive_attributes)

        # --- ĐIỂM TỔNG HỢP 3 TRỤ CỘT ---
        overall_score, weights_dict = calculate_3pillar_hybrid_score(
            score_riasec=score_riasec,
            score_academic=score_academic,
            score_preference=score_pref,
            w_riasec=w_riasec,
            w_academic=w_academic,
            w_preference=w_pref
        )

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
            # Trường hợp chỉ truyền vector RIASEC (chưa nhập điểm học tập)
            raw_block_sum = 21.5
            block_subjs = None
            effective_matched = True

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
        )

        # --- GIẢI THÍCH XAI TẤT ĐỊNH ---
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
            top_factors.insert(0, f"Chặn ràng buộc điểm: {feasibility['feasibility_label']}. {feasibility['admission_advice']}")
        else:
            disp_sum = feasibility["best_block_score"] if feasibility["best_block_score"] is not None else raw_block_sum
            top_factors.insert(0, f"Đạt ngưỡng tuyển sinh: Khối {best_block or 'xét tuyển'} ({disp_sum}đ) phù hợp mức chuẩn (~{feasibility['benchmark_cutoff']}đ).")

        if trend_info["is_trending"]:
            reason_snip = f" — {trend_info['trend_reason']}" if trend_info.get("trend_reason") else ""
            top_factors.insert(1, f"{trend_info['trend_label']}{reason_snip}")

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
                "feasibility": feasibility,
                "trend_priority_boost": get_trend_rank_boost(trend_info["trend_tier"], overall_score),
            },
            top_supporting_factors=top_factors,
            competency_gaps=overall_gaps[:5],
            missing_prerequisites=missing_pre[:3],
            missing_target_skills=missing_tar[:3],
            explanation=summary_expl,
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

    # Luôn ưu tiên sắp xếp các ngành ĐẠT ràng buộc (TARGET) trước các ngành bị chặn (REACH),
    # đồng thời ưu tiên các ngành Xu hướng theo bậc (Bậc 1 > Bậc 2 > Bậc 3 > Thường)
    final_pool = eligible_targets if len(eligible_targets) >= payload.top_k else scored_items
    final_pool.sort(
        key=lambda item: (
            1 if item.feasibility_tier == "TARGET" else 0,
            1 if item.major_code in substituted_codes else 0,
            round(item.overall_score + get_trend_rank_boost(item.trend_tier, item.overall_score), 6),
            item.trend_priority,
            item.overall_score,
            item.score_academic,
            item.score_riasec
        ),
        reverse=True
    )

    # Gán thứ hạng 1-based và cắt theo top_k
    top_results: List[MajorRecommendationItem] = []
    for idx, item in enumerate(final_pool[:payload.top_k], start=1):
        item.rank = idx
        top_results.append(item)

    # Lưu lịch sử đề xuất cho người dùng đã đăng nhập
    generated_now = datetime.now(timezone.utc)
    if persist_history and db is not None:
        try:
            history = RecommendationHistory(
                user_id=user_id,
                weights_applied=weights_dict,
                ranked_results=[it.model_dump() for it in top_results[:15]],
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


def build_two_tier_funnel_payload(
    recommendations: List[MajorRecommendationItem],
    top_fields: int = 3,
    majors_per_field: int = 3,
) -> Dict[str, Any]:
    """
    Xây dựng dữ liệu Phễu Đề xuất 2 Tầng (Tầng 1: Top 3 lĩnh vực -> Tầng 2: Top 3 ngành mỗi lĩnh vực).
    Ưu tiên đưa các ngành ĐẠT ràng buộc điểm (TARGET) lên trước trong từng lĩnh vực.
    """
    from collections import defaultdict
    from app.services.taxonomy.trend_agent import get_trend_rank_boost

    groups: Dict[str, List[MajorRecommendationItem]] = defaultdict(list)
    for item in recommendations:
        cat = item.category or "Khác"
        groups[cat].append(item)

    tier1_fields: List[Dict[str, Any]] = []
    for cat_name, items in groups.items():
        sorted_items = sorted(
            items,
            key=lambda m: (
                1 if m.feasibility_tier == "TARGET" else 0,
                round(m.overall_score + get_trend_rank_boost(m.trend_tier, m.overall_score), 6),
                m.trend_priority,
                m.overall_score,
                m.score_riasec,
            ),
            reverse=True,
        )
        sample_top = sorted_items[:majors_per_field]
        target_cnt = sum(1 for m in items if m.feasibility_tier == "TARGET")
        avg_score = sum(m.overall_score for m in sample_top) / len(sample_top)
        max_trend_boost = max(
            (
                get_trend_rank_boost(m.trend_tier, m.overall_score)
                for m in sample_top
                if m.feasibility_tier == "TARGET"
            ),
            default=0.0,
        )
        max_trend_pri = max(
            (m.trend_priority for m in sample_top if m.feasibility_tier == "TARGET"),
            default=0,
        )
        tier1_fields.append({
            "field_name": cat_name.title() if cat_name.isupper() else cat_name,
            "raw_category": cat_name,
            "icon": _resolve_field_icon(cat_name),
            "match": int(round(avg_score * 100)),
            "rank_score": avg_score + (max_trend_boost * 0.45),
            "max_trend_priority": max_trend_pri,
            "majors_count": len(items),
            "eligible_count": target_cnt,
            "has_eligible": target_cnt > 0,
            "majors": sample_top,
        })

    # Ưu tiên các lĩnh vực có ngành đạt chuẩn trước, sau đó xét % phù hợp + ưu tiên ngành xu hướng
    tier1_fields.sort(
        key=lambda f: (1 if f["has_eligible"] else 0, round(f["rank_score"], 4), f["max_trend_priority"], f["match"]),
        reverse=True,
    )
    selected_tier1 = tier1_fields[:top_fields]

    return {
        "tier1_fields": selected_tier1,
        "all_majors": recommendations[:30],
        "total_evaluated": len(recommendations),
        "total_eligible": sum(1 for m in recommendations if m.feasibility_tier == "TARGET"),
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
) -> Dict[str, Any]:
    """
    Tính toán trọn bộ dữ liệu Dashboard & Ràng buộc Điểm trên toàn bộ 435 ngành TT74:
    - Trả về 2-Tier Funnel, danh sách ngành kèm trạng thái TARGET/REACH, biểu đồ Radar và Khối mạnh nhất.
    """
    req = RecommendationRequest(top_k=max(top_k, 435), custom_weights=custom_weights)
    rec_resp = await calculate_3pillar_recommendations(
        db=db,
        user_id=user_id,
        payload=req,
        inline_profile=inline_profile,
        raise_if_unassessed=raise_if_unassessed,
        persist_history=persist_history,
    )

    # Tái sử dụng đúng vector đã chuẩn hóa để xuất Radar & Best Block Summary đồng nhất 100%
    inline = inline_profile or {}
    student_riasec = inline.get("riasec_scores") or _riasec_vector_from_answers(inline.get("riasec_answers"))
    norm_raw_grades = normalize_grades_dict(inline.get("grades_by_subject"))
    aspiration_data = inline.get("aspiration")

    if db is not None and (not student_riasec or not norm_raw_grades or not aspiration_data):
        try:
            if not student_riasec or not aspiration_data:
                a_res = await db.execute(
                    select(StudentAssessment)
                    .where(StudentAssessment.user_id == user_id)
                    .order_by(StudentAssessment.assessed_at.desc())
                )
                assess_row = a_res.scalars().first()
                if assess_row:
                    if not student_riasec and assess_row.riasec_scores:
                        student_riasec = assess_row.riasec_scores
                    if not aspiration_data and isinstance(assess_row.raw_responses, dict):
                        aspiration_data = assess_row.raw_responses.get("aspiration")
            if not norm_raw_grades:
                g_res = await db.execute(
                    select(StudentGrade)
                    .where(StudentGrade.user_id == user_id)
                    .order_by(StudentGrade.created_at.desc())
                )
                grade_row = g_res.scalars().first()
                if grade_row and grade_row.grades_by_subject:
                    norm_raw_grades = normalize_grades_dict(grade_row.grades_by_subject)
        except Exception:
            pass

    effective_riasec = student_riasec or {"R": 0.5, "I": 0.5, "A": 0.5, "S": 0.5, "E": 0.5, "C": 0.5}
    student_zscores = compute_block_zscores_from_grades(norm_raw_grades) if norm_raw_grades else {}
    riasec_data, best_block_stats = build_radar_and_block_summary(
        effective_riasec,
        student_zscores,
        norm_raw_grades,
    )

    funnel_payload = build_two_tier_funnel_payload(rec_resp.recommendations)

    # Thực thi AI Agent Phân tích Nguyện vọng & Đối chiếu Trắc nghiệm 3 Trụ cột
    from app.services.recommender.aspiration_agent import analyze_career_aspiration
    aspiration_analysis = await analyze_career_aspiration(
        aspiration_data=aspiration_data,
        student_riasec=effective_riasec,
        best_block_stats=best_block_stats,
        all_ranked_majors=rec_resp.recommendations,
        enable_llm=True,
    )

    return {
        "has_assessment": True,
        "user_name": user_name or "Học sinh",
        "total_majors_evaluated": rec_resp.total_majors_evaluated,
        "weights_applied": rec_resp.weights_applied,
        "riasecData": riasec_data,
        "bestBlockStats": best_block_stats,
        "majors": rec_resp.recommendations[:top_k],
        "funnel": funnel_payload,
        "aspirationAnalysis": aspiration_analysis,
    }
