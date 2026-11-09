import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.assessment.models import (
    AssessmentQuestionSet,
    AssessmentQuestion,
    CognitiveQuestionOption,
    StudentAssessmentSubmission,
    StudentAssessmentResponse,
)
from app.models.assessment import StudentAssessment
from app.modules.assessment.schemas import (
    AssessmentQuestionSetResponse,
    AssessmentQuestionSetConfig,
    LikertScaleItem,
    RIASECGroupMeta,
    CognitiveOptionResponse,
    QuestionItemResponse,
    AssessmentSubmissionRequest,
    AssessmentSubmissionResponse,
)
from app.db.seeds.seed_assessment_questions import load_raw_seed_data

logger = logging.getLogger(__name__)


def build_response_from_raw_json(raw_data: dict, set_id: Optional[uuid.UUID] = None) -> AssessmentQuestionSetResponse:
    """Builds a standardized Pydantic response directly from the v1.8 specification."""
    cfg = raw_data.get("config", {})
    config_obj = AssessmentQuestionSetConfig(
        xp_per_question=cfg.get("xp_per_question", 25),
        completion_bonus_xp=cfg.get("completion_bonus_xp", 200),
        estimated_minutes=cfg.get("estimated_minutes", 6),
        questions_per_riasec_page=cfg.get("questions_per_riasec_page", 5),
        total_riasec_questions=cfg.get("total_riasec_questions", 30),
        total_cognitive_questions=cfg.get("total_cognitive_questions", 8),
        weights=cfg.get("weights", {"riasec": 0.45, "academic": 0.35, "cognitive_preference": 0.20})
    )

    likert_scale = [LikertScaleItem(**item) for item in raw_data.get("likert_scale", [])]
    riasec_groups = [RIASECGroupMeta(**grp) for grp in raw_data.get("riasec_groups", [])]

    riasec_questions = []
    for item in raw_data.get("riasec_questions", []):
        riasec_questions.append(
            QuestionItemResponse(
                id=uuid.uuid5(uuid.NAMESPACE_DNS, f"riasec_{item['code']}"),
                code=item["code"],
                category="RIASEC",
                dimension=item["dimension"],
                dimension_badge=item.get("dimension_badge", f"Nhóm {item['dimension']}"),
                domain_tag=item.get("domain_tag"),
                icon_name=item.get("icon_name", "BrainCircuit"),
                question_text=item["question_text"],
                order_index=item.get("order", 1),
                xp_reward=25,
                options=[]
            )
        )

    cognitive_questions = []
    for cog_item in raw_data.get("cognitive_questions", []):
        options = []
        for opt_idx, opt in enumerate(cog_item.get("options", []), start=1):
            options.append(
                CognitiveOptionResponse(
                    id=uuid.uuid5(uuid.NAMESPACE_DNS, f"cog_opt_{cog_item['code']}_{opt['option_key']}"),
                    option_key=opt["option_key"],
                    trait_code=opt["trait_code"],
                    title=opt["title"],
                    description=opt["description"],
                    related_moet_field_codes=opt.get("related_moet_field_codes", []),
                    order_index=opt_idx
                )
            )
        cognitive_questions.append(
            QuestionItemResponse(
                id=uuid.uuid5(uuid.NAMESPACE_DNS, f"cog_{cog_item['code']}"),
                code=cog_item["code"],
                category="COGNITIVE",
                dimension=cog_item["dimension_key"],
                dimension_badge=cog_item.get("title", f"Thiên hướng {cog_item['code']}"),
                domain_tag="Thiên hướng Nhận thức & Phong cách Học tập",
                icon_name="BrainCircuit",
                question_text=f"{cog_item['title']}: {cog_item.get('subtitle', '')}",
                order_index=cog_item.get("order", 1),
                xp_reward=25,
                options=options
            )
        )

    return AssessmentQuestionSetResponse(
        set_id=set_id or uuid.uuid5(uuid.NAMESPACE_DNS, "RIASEC_COG_V1_8"),
        set_code="RIASEC_COG_V1_8",
        version=raw_data.get("version", "1.8"),
        title="Bộ câu hỏi Đánh giá Sở thích & Thiên hướng Nhận thức chuẩn v1.8",
        circular_ref=raw_data.get("circular_ref", "74/2026/TT-BGDĐT"),
        config=config_obj,
        likert_scale=likert_scale,
        riasec_groups=riasec_groups,
        riasec_questions=riasec_questions,
        cognitive_questions=cognitive_questions,
        qa_persona_presets=raw_data.get("qa_persona_presets", [])
    )


async def get_active_questionnaire_set(db: Optional[AsyncSession] = None) -> AssessmentQuestionSetResponse:
    """
    Retrieves the currently active questionnaire set with complete RIASEC items and Cognitive options.
    Gracefully falls back to embedded Circular 74/2026 specification if DB is unreachable.
    """
    raw_data = load_raw_seed_data()

    if db is not None:
        try:
            stmt = (
                select(AssessmentQuestionSet)
                .where(AssessmentQuestionSet.is_active == True)
                .options(
                    selectinload(AssessmentQuestionSet.questions).selectinload(AssessmentQuestion.cognitive_options)
                )
                .order_by(AssessmentQuestionSet.created_at.desc())
            )
            result = await db.execute(stmt)
            active_set = result.scalar_one_or_none()

            if active_set and active_set.questions:
                # Map from DB objects
                riasec_qs: List[QuestionItemResponse] = []
                cognitive_qs: List[QuestionItemResponse] = []

                for q in active_set.questions:
                    opts = [
                        CognitiveOptionResponse(
                            id=o.id,
                            option_key=o.option_key,
                            trait_code=o.trait_code,
                            title=o.title,
                            description=o.description,
                            related_moet_field_codes=o.related_moet_field_codes or [],
                            order_index=o.order_index
                        )
                        for o in q.cognitive_options
                    ]
                    item = QuestionItemResponse(
                        id=q.id,
                        code=q.code,
                        category=q.category,
                        dimension=q.dimension,
                        dimension_badge=q.dimension_badge,
                        domain_tag=q.domain_tag,
                        icon_name=q.icon_name,
                        question_text=q.question_text,
                        order_index=q.order_index,
                        xp_reward=q.xp_reward,
                        options=opts
                    )
                    if q.category == "RIASEC":
                        riasec_qs.append(item)
                    else:
                        cognitive_qs.append(item)

                riasec_qs.sort(key=lambda x: x.order_index)
                cognitive_qs.sort(key=lambda x: x.order_index)

                cfg = active_set.config or {}
                config_obj = AssessmentQuestionSetConfig(
                    xp_per_question=cfg.get("xp_per_question", 25),
                    completion_bonus_xp=cfg.get("completion_bonus_xp", 200),
                    estimated_minutes=cfg.get("estimated_minutes", 6),
                    questions_per_riasec_page=cfg.get("questions_per_riasec_page", 5),
                    total_riasec_questions=cfg.get("total_riasec_questions", len(riasec_qs)),
                    total_cognitive_questions=cfg.get("total_cognitive_questions", len(cognitive_qs)),
                    weights=cfg.get("weights", {"riasec": 0.45, "academic": 0.35, "cognitive_preference": 0.20})
                )

                return AssessmentQuestionSetResponse(
                    set_id=active_set.id,
                    set_code=active_set.set_code,
                    version=active_set.version,
                    title=active_set.title,
                    circular_ref=active_set.circular_ref,
                    config=config_obj,
                    likert_scale=[LikertScaleItem(**item) for item in raw_data.get("likert_scale", [])],
                    riasec_groups=[RIASECGroupMeta(**grp) for grp in raw_data.get("riasec_groups", [])],
                    riasec_questions=riasec_qs,
                    cognitive_questions=cognitive_qs,
                    qa_persona_presets=raw_data.get("qa_persona_presets", [])
                )
        except Exception as exc:
            logger.warning(f"Database query for active question set failed ({exc}), falling back to file spec.")

    return build_response_from_raw_json(raw_data)


async def process_assessment_submission(
    db: Optional[AsyncSession],
    user_id: uuid.UUID,
    payload: AssessmentSubmissionRequest
) -> AssessmentSubmissionResponse:
    """
    100% Deterministic Mathematical Scoring Engine (FR02, NFR04):
    1. Normalizes RIASEC items (30 items, 5 per dimension):
       Raw Sum in range [5, 25] -> Normalized score in [0.0, 1.0] via formula: (sum - 5) / 20.
    2. Maps 8 Cognitive Preference choices to trait codes.
    3. Identifies dominant traits.
    4. Persists submission into database if available.
    """
    raw_data = load_raw_seed_data()
    riasec_answers = payload.riasec_answers
    cog_answers = payload.cognitive_answers

    # Map question codes to dimensions
    q_to_dim: Dict[str, str] = {}
    for item in raw_data.get("riasec_questions", []):
        q_to_dim[item["code"]] = item["dimension"]

    # 1. Calculate raw and normalized RIASEC scores
    raw_sums: Dict[str, int] = {"R": 0, "I": 0, "A": 0, "S": 0, "E": 0, "C": 0}
    counts: Dict[str, int] = {"R": 0, "I": 0, "A": 0, "S": 0, "E": 0, "C": 0}

    for q_code, val in riasec_answers.items():
        dim = q_to_dim.get(q_code) or q_code[0].upper()
        if dim in raw_sums:
            clamped_val = max(1, min(5, int(val)))
            raw_sums[dim] += clamped_val
            counts[dim] += 1

    # Standard formula: (raw_sum - 5) / 20 maps [5, 25] to [0.0, 1.0]
    normalized_vector: Dict[str, float] = {}
    for dim in ["R", "I", "A", "S", "E", "C"]:
        cnt = counts[dim]
        if cnt == 0:
            normalized_vector[dim] = 0.50
        else:
            # If student answered fewer than 5 items, extrapolate to 5-item scale
            scale_5_sum = (raw_sums[dim] / cnt) * 5.0
            norm_val = (scale_5_sum - 5.0) / 20.0
            normalized_vector[dim] = round(max(0.0, min(1.0, norm_val)), 2)

    # 2. Map Cognitive Preference Answers
    # Build lookup of option trait codes
    cog_trait_lookup: Dict[str, Dict[str, str]] = {}
    for cog in raw_data.get("cognitive_questions", []):
        c_code = cog["code"]
        dim_key = cog["dimension_key"]
        opts_map = {opt["option_key"].upper(): opt["trait_code"] for opt in cog.get("options", [])}
        cog_trait_lookup[c_code] = opts_map
        cog_trait_lookup[dim_key] = opts_map

    cognitive_traits: Dict[str, str] = {}
    cognitive_answers_clean: Dict[str, str] = {}
    
    # 8 standard cognitive dimensions
    standard_cog_dims = [
        ("COG_1", "learning_style"),
        ("COG_2", "work_environment"),
        ("COG_3", "problem_solving"),
        ("COG_4", "interaction_target"),
        ("COG_5", "gardner_intelligence"),
        ("COG_6", "pressure_tolerance"),
        ("COG_7", "output_preference"),
        ("COG_8", "team_role"),
    ]

    for c_code, dim_key in standard_cog_dims:
        choice = cog_answers.get(c_code) or cog_answers.get(dim_key) or "A"
        choice_clean = str(choice).strip().upper()
        cognitive_answers_clean[dim_key] = choice_clean

        traits_map = cog_trait_lookup.get(c_code, {})
        trait_code = traits_map.get(choice_clean, f"TRAIT_{dim_key.upper()}_{choice_clean}")
        cognitive_traits[dim_key] = trait_code

    # 3. Identify Top Dominant Traits
    dim_names: Dict[str, str] = {
        "R": "R - Thực tế (Realistic)",
        "I": "I - Nghiên cứu (Investigative)",
        "A": "A - Nghệ thuật (Artistic)",
        "S": "S - Xã hội (Social)",
        "E": "E - Quản lý (Enterprising)",
        "C": "C - Nghiệp vụ (Conventional)",
    }
    sorted_dims = sorted(normalized_vector.items(), key=lambda kv: kv[1], reverse=True)
    dominant_traits = [f"{dim_names.get(d, d)} ({(val * 100):.0f}%)" for d, val in sorted_dims[:3]]

    # XP Calculation: 30*25 (750) + 8*25 (200) + 200 completion bonus = 1150 XP
    xp_earned = 1150
    submission_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # 4. Save to Database if DB Session is active
    if db is not None:
        try:
            submission = StudentAssessmentSubmission(
                id=submission_id,
                user_id=user_id,
                set_id=payload.set_id,
                riasec_vector=normalized_vector,
                riasec_raw_scores=raw_sums,
                cognitive_traits=cognitive_traits,
                cognitive_answers=cognitive_answers_clean,
                raw_answers={
                    "riasec_answers": riasec_answers,
                    "cognitive_answers": cog_answers
                },
                dominant_traits=dominant_traits,
                xp_earned=xp_earned,
                completion_time_seconds=payload.completion_time_seconds or 360,
                completed_at=now
            )
            db.add(submission)

            # Record individual granular responses
            for q_code, val in riasec_answers.items():
                db.add(
                    StudentAssessmentResponse(
                        id=uuid.uuid4(),
                        submission_id=submission_id,
                        question_id=uuid.uuid5(uuid.NAMESPACE_DNS, f"riasec_{q_code}"),
                        question_code=q_code,
                        likert_value=int(val),
                        answered_at=now
                    )
                )

            for c_code, dim_key in standard_cog_dims:
                choice = cognitive_answers_clean.get(dim_key, "A")
                trait = cognitive_traits.get(dim_key, "")
                db.add(
                    StudentAssessmentResponse(
                        id=uuid.uuid4(),
                        submission_id=submission_id,
                        question_id=uuid.uuid5(uuid.NAMESPACE_DNS, f"cog_{c_code}"),
                        question_code=c_code,
                        option_key=choice,
                        selected_trait_code=trait,
                        answered_at=now
                    )
                )

            # Also sync to legacy student_assessments table for backward compatibility with recommender
            legacy_record = StudentAssessment(
                id=uuid.uuid4(),
                user_id=user_id,
                riasec_scores=normalized_vector,
                cognitive_preferences=cognitive_traits,
                raw_responses={"riasec": riasec_answers, "cognitive": cog_answers},
                assessed_at=now
            )
            db.add(legacy_record)

            await db.commit()
            logger.info(f"Student assessment submission {submission_id} saved successfully for user {user_id}")
        except Exception as exc:
            logger.warning(f"Database persist failed ({exc}); returning calculated results in client mode.")

    summary_text = (
        f"Hoàn thành xuất sắc bài đánh giá chuẩn v1.8! "
        f"Hồ sơ sở thích nghề nghiệp nổi bật với 3 trụ cột: {', '.join(dominant_traits)}."
    )

    return AssessmentSubmissionResponse(
        submission_id=submission_id,
        riasec_vector=normalized_vector,
        riasec_raw_scores=raw_sums,
        cognitive_traits=cognitive_traits,
        dominant_traits=dominant_traits,
        xp_earned=xp_earned,
        summary=summary_text,
        completed_at=now
    )
