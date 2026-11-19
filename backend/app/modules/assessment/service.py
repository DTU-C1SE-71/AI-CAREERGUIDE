import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
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


def _question_set_query(set_id=None):
    """Select one questionnaire consistently for display and submission."""
    query = select(AssessmentQuestionSet).options(
        selectinload(AssessmentQuestionSet.questions).selectinload(AssessmentQuestion.cognitive_options))
    query = query.where(AssessmentQuestionSet.id == set_id) if set_id else query.where(AssessmentQuestionSet.is_active.is_(True))
    return query.order_by(AssessmentQuestionSet.created_at.desc(), AssessmentQuestionSet.id.asc()).limit(1)


async def get_active_questionnaire_set(db: Optional[AsyncSession] = None) -> AssessmentQuestionSetResponse:
    """
    Retrieves the currently active questionnaire set with complete RIASEC items and Cognitive options.
    File spec chỉ dùng khi db=None; DB rỗng/lỗi được báo rõ, không phục hồi câu hỏi cũ.
    """
    raw_data = load_raw_seed_data()

    if db is not None:
        try:
            stmt = _question_set_query()
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
            raise HTTPException(404, "Chưa có bộ câu hỏi đang hoạt động trong cơ sở dữ liệu.")
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Database questionnaire query failed (%s)", type(exc).__name__)
            raise HTTPException(503, "Chưa tải được bộ câu hỏi; vui lòng thử lại.") from None

    return build_response_from_raw_json(raw_data)


async def process_assessment_submission(
    db: Optional[AsyncSession],
    user_id: uuid.UUID,
    payload: AssessmentSubmissionRequest,
    persist_to_db: bool = True,
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

    from app.services.recommender.readiness import build_interest_evidence
    from app.services.recommender.evidence import cognitive_evidence
    interest = build_interest_evidence(riasec_answers)
    # Preserve missingness, never extrapolate unobserved groups to a neutral score.
    normalized_vector = {g["code"]: g["percent"] / 100 for g in interest["groups"] if g["answered"]}
    raw_sums = {code: 0 for code in "RIASEC"}
    valid_riasec = {}
    for question in raw_data.get("riasec_questions", []):
        code = question["code"]
        value = riasec_answers.get(code)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value in (1, 2, 3, 4, 5):
            valid_riasec[code] = int(value)
            raw_sums[question["dimension"]] += int(value)
    cognitive = cognitive_evidence(cog_answers)
    cognitive_traits = cognitive["traits"]
    cognitive_answers_clean = {}
    selected_traits = {}
    standard_cog_dims = []
    for question in raw_data.get("cognitive_questions", []):
        code, dim = question["code"], question["dimension_key"]
        standard_cog_dims.append((code, dim))
        answer = cog_answers[code] if code in cog_answers else cog_answers.get(dim)
        answer = answer.strip().upper() if isinstance(answer, str) else None
        for option in question["options"]:
            if answer in (option["option_key"], option["trait_code"]):
                cognitive_answers_clean[dim] = option["option_key"]
                selected_traits[dim] = option["trait_code"]
                break

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
    dominant_traits = [f"{dim_names.get(d, d)} ({(val * 100):.0f}%)" for d, val in sorted_dims[:3]] if interest["status"] == "COMPLETE" else []

    # XP Calculation: 30*25 (750) + 8*25 (200) + 200 completion bonus = 1150 XP
    xp_earned = (len(valid_riasec) + len(cognitive_answers_clean)) * 25 + (200 if len(valid_riasec) == 30 and len(cognitive_answers_clean) == 8 else 0)
    submission_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # 4. Save to Database if DB Session is active and user exists
    if db is not None and persist_to_db:
        try:
            from app.models.identity import User
            owner = (await db.execute(select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
            if owner is None or not owner.is_active:
                raise HTTPException(401, "Tài khoản không còn hoạt động.")
            # Granular answers must reference real persisted questions (seed IDs are UUID4).
            selected_set = (await db.execute(_question_set_query(payload.set_id))).scalar_one_or_none()
            if payload.set_id is not None and selected_set is None:
                raise HTTPException(422, "Bộ câu hỏi đã chọn không tồn tại. Vui lòng tải lại bài đánh giá.")
            question_rows = list(selected_set.questions) if selected_set else []
            question_ids = {q.code: q.id for q in question_rows}
            persisted_set_id = selected_set.id if selected_set else None
            submission = StudentAssessmentSubmission(
                id=submission_id,
                user_id=user_id,
                set_id=persisted_set_id,
                riasec_vector=normalized_vector,
                riasec_raw_scores=raw_sums,
                cognitive_traits=cognitive_traits,
                cognitive_answers=cognitive_answers_clean,
                raw_answers={
                    "riasec_answers": riasec_answers,
                    "cognitive_answers": cog_answers,
                    "aspiration": payload.aspiration or {},
                    "grades_by_subject": payload.grades_by_subject,
                    "score_context": payload.score_context,
                },
                dominant_traits=dominant_traits,
                xp_earned=xp_earned,
                completion_time_seconds=payload.completion_time_seconds or 360,
                completed_at=now
            )
            db.add(submission)

            # Record individual granular responses
            for q_code, val in valid_riasec.items():
                if q_code not in question_ids:
                    continue
                db.add(
                    StudentAssessmentResponse(
                        id=uuid.uuid4(),
                        submission_id=submission_id,
                        question_id=question_ids[q_code],
                        question_code=q_code,
                        likert_value=int(val),
                        answered_at=now
                    )
                )

            for c_code, dim_key in standard_cog_dims:
                if dim_key not in cognitive_answers_clean or c_code not in question_ids:
                    continue
                choice = cognitive_answers_clean[dim_key]
                trait = selected_traits[dim_key]
                db.add(
                    StudentAssessmentResponse(
                        id=uuid.uuid4(),
                        submission_id=submission_id,
                        question_id=question_ids[c_code],
                        question_code=c_code,
                        option_key=choice,
                        selected_trait_code=trait,
                        answered_at=now
                    )
                )

            # Also sync to legacy student_assessments table for backward compatibility with recommender
            legacy_record = StudentAssessment(
                id=submission_id,
                user_id=user_id,
                riasec_scores=normalized_vector,
                cognitive_preferences=cognitive_traits,
                raw_responses={
                    "riasec": riasec_answers,
                    "cognitive": cog_answers,
                    "aspiration": payload.aspiration or {},
                    "grades_by_subject": payload.grades_by_subject,
                    "score_context": payload.score_context,
                },
                assessed_at=now
            )
            db.add(legacy_record)

            await db.commit()
            logger.info(f"Student assessment submission {submission_id} saved successfully for user {user_id}")
        except HTTPException:
            await db.rollback()
            raise
        except Exception as exc:
            await db.rollback()
            logger.warning("Assessment persistence failed: %s", type(exc).__name__)
            raise HTTPException(503, "Chưa lưu được bài đánh giá. Vui lòng thử lại.") from exc

    summary_text = (f"Nhóm sở thích nổi bật: {', '.join(dominant_traits)}." if dominant_traits else
                    "Đã ghi nhận câu trả lời. Sở thích chưa phân hóa hoặc bài làm chưa đủ để kết luận nhóm nổi bật.")

    return AssessmentSubmissionResponse(
        submission_id=submission_id,
        riasec_vector=normalized_vector,
        riasec_raw_scores=raw_sums,
        cognitive_traits=cognitive_traits,
        dominant_traits=dominant_traits,
        xp_earned=xp_earned,
        interest_evidence=interest,
        cognitive_evidence=cognitive,
        summary=summary_text,
        completed_at=now
    )
