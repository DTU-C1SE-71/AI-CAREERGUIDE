import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from fastapi import HTTPException
from sqlalchemy.orm import selectinload

from app.modules.assessment.models import (
    AssessmentQuestionSet,
    AssessmentQuestion,
    CognitiveQuestionOption,
    StudentAssessmentSubmission,
    StudentAssessmentResponse,
)
from app.modules.assessment.schemas import (
    AssessmentQuestionSetResponse,
    AssessmentQuestionSetConfig,
    LikertScaleItem,
    RIASECGroupMeta,
    CognitiveOptionResponse,
    QuestionItemResponse,
    AssessmentSubmissionRequest,
    AssessmentSubmissionResponse,
    AssessmentResponseItem,
    AssessmentSubmissionSummary,
    AssessmentSubmissionDetail,
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
        total_cognitive_questions=cfg.get("total_cognitive_questions", 10),
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
                dimension_badge=cog_item.get("title", f"Câu {cog_item.get('order', 1)}"),
                domain_tag="Phong cách Tư duy & Môi trường Học tập",
                icon_name="BrainCircuit",
                question_text=cog_item.get("subtitle", ""),
                order_index=cog_item.get("order", 1),
                xp_reward=25,
                options=options
            )
        )

    return AssessmentQuestionSetResponse(
        set_id=set_id or uuid.uuid5(uuid.NAMESPACE_DNS, "RIASEC_COG_V2_10"),
        set_code="RIASEC_COG_V2_10",
        version=raw_data.get("version", "2.0"),
        title="Bộ câu hỏi Đánh giá Sở thích & Phong cách Tư duy chuẩn v2.0",
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

    # XP Calculation: 30*25 + 10*25 + 200 completion bonus
    total_cog = len(standard_cog_dims) or 10
    xp_earned = (len(valid_riasec) + len(cognitive_answers_clean)) * 25 + (200 if len(valid_riasec) == 30 and len(cognitive_answers_clean) == total_cog else 0)
    submission_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # 4. Save to Database if DB Session is active and user exists
    owner_name: Optional[str] = None
    owner_gender: Optional[str] = None
    owner_grade_level: Optional[str] = None
    if db is not None and persist_to_db:
        try:
            from app.models.identity import User
            owner = (await db.execute(select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
            if owner is None or not owner.is_active:
                raise HTTPException(401, "Tài khoản không còn hoạt động.")
            owner_name = getattr(owner, "full_name", None)
            owner_gender = getattr(owner, "gender", None)
            owner_grade_level = getattr(owner, "grade_level", None)
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
                    "assessment_version": "v2_10q",
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

            await db.commit()
            logger.info(f"Student assessment submission {submission_id} saved successfully for user {user_id}")
        except HTTPException:
            await db.rollback()
            raise
        except Exception as exc:
            await db.rollback()
            logger.warning("Assessment persistence failed: %s", type(exc).__name__)
            raise HTTPException(503, "Chưa lưu được bài đánh giá. Vui lòng thử lại.") from exc

        if valid_riasec or payload.grades_by_subject:
            try:
                from app.services.recommender.service import evaluate_dashboard_profile_bundle

                await evaluate_dashboard_profile_bundle(
                    db=db,
                    user_id=user_id,
                    top_k=435,
                    inline_profile={
                        "assessment_id": str(submission_id),
                        "riasec_answers": riasec_answers,
                        "cognitive_answers": cog_answers,
                        "aspiration": payload.aspiration or {},
                        "grades_by_subject": payload.grades_by_subject or {},
                        "score_context": payload.score_context or {"kind": "TRANSCRIPT", "scale": 10},
                        "gender": owner_gender,
                        "grade_level": owner_grade_level,
                    },
                    raise_if_unassessed=False,
                    persist_history=False,
                    user_name=owner_name,
                    gender=owner_gender,
                    grade_level=owner_grade_level,
                    use_cache=True,
                )
            except Exception as cache_exc:
                logger.warning("Recommendation snapshot precompute skipped (%s)", type(cache_exc).__name__)

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


def _submission_to_summary_dict(row: StudentAssessmentSubmission) -> Dict[str, Any]:
    raw = row.raw_answers if isinstance(row.raw_answers, dict) else {}
    riasec_answers = raw.get("riasec_answers")
    if not isinstance(riasec_answers, dict):
        riasec_answers = raw.get("riasec") if isinstance(raw.get("riasec"), dict) else {}
    raw_cog = raw.get("cognitive_answers")
    if not isinstance(raw_cog, dict):
        raw_cog = raw.get("cognitive") if isinstance(raw.get("cognitive"), dict) else {}
    if not raw_cog and isinstance(row.cognitive_answers, dict):
        raw_cog = dict(row.cognitive_answers)
    grades = raw.get("grades_by_subject") if isinstance(raw.get("grades_by_subject"), dict) else {}
    aspiration = raw.get("aspiration") if isinstance(raw.get("aspiration"), dict) else {}
    score_context = (
        raw.get("score_context")
        if isinstance(raw.get("score_context"), dict)
        else {"kind": "TRANSCRIPT", "scale": 10}
    )
    qset = getattr(row, "question_set", None)
    return {
        "submission_id": row.id,
        "set_id": row.set_id,
        "set_code": qset.set_code if qset is not None else None,
        "version": qset.version if qset is not None else None,
        "riasec_vector": dict(row.riasec_vector or {}),
        "riasec_raw_scores": dict(row.riasec_raw_scores or {}),
        "cognitive_traits": dict(row.cognitive_traits or {}),
        "cognitive_answers": dict(row.cognitive_answers or {}),
        "riasec_answers": dict(riasec_answers),
        "raw_cognitive_answers": dict(raw_cog),
        "grades_by_subject": dict(grades),
        "aspiration": dict(aspiration),
        "score_context": dict(score_context),
        "dominant_traits": list(row.dominant_traits or []),
        "xp_earned": int(row.xp_earned or 0),
        "completion_time_seconds": int(row.completion_time_seconds or 360),
        "completed_at": row.completed_at,
    }


async def list_student_submissions(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 20,
) -> List[AssessmentSubmissionSummary]:
    """Liệt kê lịch sử nộp bài đánh giá của học sinh (mới nhất trước)."""
    safe_limit = max(1, min(int(limit or 20), 100))
    stmt = (
        select(StudentAssessmentSubmission)
        .options(selectinload(StudentAssessmentSubmission.question_set))
        .where(StudentAssessmentSubmission.user_id == user_id)
        .order_by(StudentAssessmentSubmission.completed_at.desc(), StudentAssessmentSubmission.id.desc())
        .limit(safe_limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [AssessmentSubmissionSummary(**_submission_to_summary_dict(r)) for r in rows]


async def get_student_submission_detail(
    db: AsyncSession,
    user_id: uuid.UUID,
    submission_id: uuid.UUID,
) -> AssessmentSubmissionDetail:
    """Trả về chi tiết một lượt làm bài kèm toàn bộ câu trả lời chi tiết (chỉ chủ sở hữu)."""
    stmt = (
        select(StudentAssessmentSubmission)
        .options(
            selectinload(StudentAssessmentSubmission.question_set),
            selectinload(StudentAssessmentSubmission.responses),
        )
        .where(
            StudentAssessmentSubmission.id == submission_id,
            StudentAssessmentSubmission.user_id == user_id,
        )
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Không tìm thấy bản đánh giá đã chọn.")
    ordered_responses = sorted(
        list(row.responses or []),
        key=lambda r: (r.answered_at, r.question_code, str(r.id)),
    )
    return AssessmentSubmissionDetail(
        **_submission_to_summary_dict(row),
        raw_answers=dict(row.raw_answers or {}),
        responses=[AssessmentResponseItem.model_validate(item) for item in ordered_responses],
    )


def _score_submission_inputs(
    riasec_answers: Dict[str, Any],
    cog_answers: Dict[str, Any],
    question_set: Optional[AssessmentQuestionSet] = None,
) -> Dict[str, Any]:
    raw_data = load_raw_seed_data()
    from app.services.recommender.readiness import build_interest_evidence
    from app.services.recommender.evidence import cognitive_evidence

    interest = build_interest_evidence(riasec_answers)
    normalized_vector = {g["code"]: g["percent"] / 100 for g in interest["groups"] if g["answered"]}
    raw_sums = {code: 0 for code in "RIASEC"}
    valid_riasec: Dict[str, int] = {}
    for question in raw_data.get("riasec_questions", []):
        code = question["code"]
        value = riasec_answers.get(code)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value in (1, 2, 3, 4, 5):
            valid_riasec[code] = int(value)
            raw_sums[question["dimension"]] += int(value)

    cognitive = cognitive_evidence(cog_answers)
    cognitive_traits = cognitive["traits"]
    cognitive_answers_clean: Dict[str, str] = {}
    selected_traits: Dict[str, str] = {}
    standard_cog_dims: List[tuple[str, str]] = []

    db_cog_questions = sorted(
        [q for q in (getattr(question_set, "questions", None) or []) if getattr(q, "category", "") == "COGNITIVE"],
        key=lambda q: (int(getattr(q, "order_index", 0) or 0), str(getattr(q, "code", ""))),
    )
    if db_cog_questions:
        cog_specs = [
            {
                "code": q.code,
                "dimension_key": q.dimension,
                "options": [
                    {"option_key": opt.option_key, "trait_code": opt.trait_code}
                    for opt in (getattr(q, "cognitive_options", None) or [])
                ],
            }
            for q in db_cog_questions
        ]
    else:
        cog_specs = raw_data.get("cognitive_questions", [])

    for question in cog_specs:
        code, dim = question["code"], question["dimension_key"]
        standard_cog_dims.append((code, dim))
        answer = cog_answers[code] if code in cog_answers else cog_answers.get(dim)
        answer = answer.strip().upper() if isinstance(answer, str) else None
        for option in question["options"]:
            if answer in (option["option_key"], option["trait_code"]):
                cognitive_answers_clean[dim] = option["option_key"]
                selected_traits[dim] = option["trait_code"]
                break

    dim_names: Dict[str, str] = {
        "R": "R - Thực tế (Realistic)",
        "I": "I - Nghiên cứu (Investigative)",
        "A": "A - Nghệ thuật (Artistic)",
        "S": "S - Xã hội (Social)",
        "E": "E - Quản lý (Enterprising)",
        "C": "C - Nghiệp vụ (Conventional)",
    }
    sorted_dims = sorted(normalized_vector.items(), key=lambda kv: kv[1], reverse=True)
    dominant_traits = (
        [f"{dim_names.get(d, d)} ({(val * 100):.0f}%)" for d, val in sorted_dims[:3]]
        if interest["status"] == "COMPLETE"
        else []
    )

    total_cog = len(standard_cog_dims) or 10
    xp_earned = (len(valid_riasec) + len(cognitive_answers_clean)) * 25 + (
        200 if len(valid_riasec) == 30 and len(cognitive_answers_clean) == total_cog else 0
    )
    summary_text = (
        f"Nhóm sở thích nổi bật: {', '.join(dominant_traits)}."
        if dominant_traits
        else "Đã ghi nhận câu trả lời. Sở thích chưa phân hóa hoặc bài làm chưa đủ để kết luận nhóm nổi bật."
    )
    return {
        "interest": interest,
        "normalized_vector": normalized_vector,
        "raw_sums": raw_sums,
        "valid_riasec": valid_riasec,
        "cognitive": cognitive,
        "cognitive_traits": cognitive_traits,
        "cognitive_answers_clean": cognitive_answers_clean,
        "selected_traits": selected_traits,
        "standard_cog_dims": standard_cog_dims,
        "dominant_traits": dominant_traits,
        "xp_earned": xp_earned,
        "summary_text": summary_text,
    }


def _submission_change_fingerprint(
    valid_riasec: Dict[str, int],
    cognitive_answers_clean: Dict[str, str],
    grades_by_subject: Optional[Dict[str, Any]],
    aspiration: Optional[Dict[str, Any]],
    score_context: Optional[Dict[str, Any]],
) -> str:
    norm_grades: Dict[str, float] = {}
    for k, v in (grades_by_subject or {}).items():
        if isinstance(k, str) and k.strip():
            try:
                num = float(v)
                if num == num:
                    norm_grades[k.strip()] = round(num, 4)
            except (TypeError, ValueError):
                continue
    asp = aspiration if isinstance(aspiration, dict) else {}
    norm_asp = {
        "dream_job": str(asp.get("dream_job") or asp.get("dreamJob") or "").strip(),
        "desired_field": str(asp.get("desired_field") or asp.get("desiredField") or "").strip(),
        "work_values": sorted(
            str(x).strip()
            for x in (asp.get("work_values") or asp.get("workValues") or [])
            if str(x).strip()
        ),
        "preferred_environment": str(
            asp.get("preferred_environment") or asp.get("preferredEnvironment") or ""
        ).strip(),
        "score_strategy": str(
            asp.get("score_strategy") or asp.get("scoreStrategy") or "FLEXIBLE_PATHWAY"
        ).strip() or "FLEXIBLE_PATHWAY",
    }
    ctx = score_context if isinstance(score_context, dict) else {"kind": "TRANSCRIPT", "scale": 10}
    return json.dumps(
        {
            "riasec": {k: valid_riasec[k] for k in sorted(valid_riasec)},
            "cognitive": {k: cognitive_answers_clean[k] for k in sorted(cognitive_answers_clean)},
            "grades": {k: norm_grades[k] for k in sorted(norm_grades)},
            "aspiration": norm_asp,
            "score_context": ctx,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


async def delete_student_submission(
    db: AsyncSession,
    user_id: uuid.UUID,
    submission_id: uuid.UUID,
) -> None:
    """Xóa vĩnh viễn một lượt nộp bài khỏi DB (kèm responses cascade) và vô hiệu hóa cache snapshot."""
    stmt = select(StudentAssessmentSubmission).where(
        StudentAssessmentSubmission.id == submission_id,
        StudentAssessmentSubmission.user_id == user_id,
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Không tìm thấy bản đánh giá đã chọn.")

    from app.services.recommender.service import invalidate_user_recommendation_snapshots

    await invalidate_user_recommendation_snapshots(db, user_id)
    await db.delete(row)
    await db.commit()


async def update_student_submission(
    db: AsyncSession,
    user_id: uuid.UUID,
    submission_id: uuid.UUID,
    payload: AssessmentSubmissionRequest,
) -> AssessmentSubmissionResponse:
    """Cập nhật tại chỗ một hồ sơ đã lưu; nếu phát hiện thay đổi thì xóa cache AI và chạy lại thuật toán."""
    from app.models.identity import User
    from app.models.insight import MajorExplanationInsight, StudentSkillInsight
    from app.services.recommender.service import (
        evaluate_dashboard_profile_bundle,
        invalidate_user_recommendation_snapshots,
    )

    stmt = (
        select(StudentAssessmentSubmission)
        .options(
            selectinload(StudentAssessmentSubmission.question_set)
            .selectinload(AssessmentQuestionSet.questions)
            .selectinload(AssessmentQuestion.cognitive_options)
        )
        .where(
            StudentAssessmentSubmission.id == submission_id,
            StudentAssessmentSubmission.user_id == user_id,
        )
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Không tìm thấy bản đánh giá đã chọn.")

    owner = (
        await db.execute(
            select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if owner is None or not owner.is_active:
        raise HTTPException(401, "Tài khoản không còn hoạt động.")

    owner_name = getattr(owner, "full_name", None)
    owner_gender = getattr(owner, "gender", None)
    owner_grade_level = getattr(owner, "grade_level", None)

    prev_raw = row.raw_answers if isinstance(row.raw_answers, dict) else {}
    prev_riasec = prev_raw.get("riasec_answers")
    if not isinstance(prev_riasec, dict):
        prev_riasec = prev_raw.get("riasec") if isinstance(prev_raw.get("riasec"), dict) else {}
    prev_cog = prev_raw.get("cognitive_answers")
    if not isinstance(prev_cog, dict):
        prev_cog = prev_raw.get("cognitive") if isinstance(prev_raw.get("cognitive"), dict) else {}
    if not prev_cog and isinstance(row.cognitive_answers, dict):
        prev_cog = dict(row.cognitive_answers)

    prev_scored = _score_submission_inputs(prev_riasec, prev_cog, row.question_set)
    prev_cog_clean = prev_scored["cognitive_answers_clean"] or dict(row.cognitive_answers or {})
    prev_fp = _submission_change_fingerprint(
        prev_scored["valid_riasec"],
        prev_cog_clean,
        prev_raw.get("grades_by_subject") if isinstance(prev_raw.get("grades_by_subject"), dict) else {},
        prev_raw.get("aspiration") if isinstance(prev_raw.get("aspiration"), dict) else {},
        prev_raw.get("score_context") if isinstance(prev_raw.get("score_context"), dict) else {"kind": "TRANSCRIPT", "scale": 10},
    )

    scored = _score_submission_inputs(payload.riasec_answers, payload.cognitive_answers, row.question_set)
    new_fp = _submission_change_fingerprint(
        scored["valid_riasec"],
        scored["cognitive_answers_clean"],
        payload.grades_by_subject,
        payload.aspiration,
        payload.score_context,
    )

    if new_fp == prev_fp:
        return AssessmentSubmissionResponse(
            submission_id=row.id,
            riasec_vector=dict(row.riasec_vector or scored["normalized_vector"]),
            riasec_raw_scores=dict(row.riasec_raw_scores or scored["raw_sums"]),
            cognitive_traits=dict(row.cognitive_traits or scored["cognitive_traits"]),
            dominant_traits=list(row.dominant_traits or scored["dominant_traits"]),
            xp_earned=int(row.xp_earned or scored["xp_earned"]),
            interest_evidence=scored["interest"],
            cognitive_evidence=scored["cognitive"],
            summary=scored["summary_text"],
            completed_at=row.completed_at,
            changed=False,
            ai_cache_invalidated=False,
        )

    now = datetime.now(timezone.utc)
    try:
        row.riasec_vector = scored["normalized_vector"]
        row.riasec_raw_scores = scored["raw_sums"]
        row.cognitive_traits = scored["cognitive_traits"]
        row.cognitive_answers = scored["cognitive_answers_clean"]
        row.dominant_traits = scored["dominant_traits"]
        row.xp_earned = scored["xp_earned"]
        row.completion_time_seconds = payload.completion_time_seconds or row.completion_time_seconds or 360
        row.raw_answers = {
            "assessment_version": prev_raw.get("assessment_version")
            or ("v1_8q" if row.question_set and row.question_set.set_code == "RIASEC_COG_V1_8" else "v2_10q"),
            "riasec_answers": payload.riasec_answers,
            "cognitive_answers": payload.cognitive_answers,
            "aspiration": payload.aspiration or {},
            "grades_by_subject": payload.grades_by_subject,
            "score_context": payload.score_context,
            "updated_at": now.isoformat(),
        }

        await db.execute(
            delete(StudentAssessmentResponse).where(StudentAssessmentResponse.submission_id == row.id)
        )
        await db.flush()

        question_rows = list(row.question_set.questions) if row.question_set else []
        question_ids = {q.code: q.id for q in question_rows}

        for q_code, val in scored["valid_riasec"].items():
            if q_code not in question_ids:
                continue
            db.add(
                StudentAssessmentResponse(
                    id=uuid.uuid4(),
                    submission_id=row.id,
                    question_id=question_ids[q_code],
                    question_code=q_code,
                    likert_value=int(val),
                    answered_at=now,
                )
            )

        for c_code, dim_key in scored["standard_cog_dims"]:
            if dim_key not in scored["cognitive_answers_clean"] or c_code not in question_ids:
                continue
            db.add(
                StudentAssessmentResponse(
                    id=uuid.uuid4(),
                    submission_id=row.id,
                    question_id=question_ids[c_code],
                    question_code=c_code,
                    option_key=scored["cognitive_answers_clean"][dim_key],
                    selected_trait_code=scored["selected_traits"][dim_key],
                    answered_at=now,
                )
            )

        await invalidate_user_recommendation_snapshots(db, user_id)
        await db.execute(delete(StudentSkillInsight).where(StudentSkillInsight.user_id == user_id))
        await db.execute(delete(MajorExplanationInsight).where(MajorExplanationInsight.user_id == user_id))

        await db.commit()
        logger.info("Student assessment submission %s updated for user %s; caches invalidated", row.id, user_id)
    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        logger.warning("Assessment submission update failed: %s", type(exc).__name__)
        raise HTTPException(503, "Chưa cập nhật được hồ sơ đánh giá. Vui lòng thử lại.") from exc

    if scored["valid_riasec"] or payload.grades_by_subject:
        try:
            await evaluate_dashboard_profile_bundle(
                db=db,
                user_id=user_id,
                top_k=435,
                inline_profile={
                    "assessment_id": str(row.id),
                    "riasec_answers": payload.riasec_answers,
                    "cognitive_answers": payload.cognitive_answers,
                    "aspiration": payload.aspiration or {},
                    "grades_by_subject": payload.grades_by_subject or {},
                    "score_context": payload.score_context or {"kind": "TRANSCRIPT", "scale": 10},
                    "gender": owner_gender,
                    "grade_level": owner_grade_level,
                },
                raise_if_unassessed=False,
                persist_history=False,
                user_name=owner_name,
                gender=owner_gender,
                grade_level=owner_grade_level,
                use_cache=True,
            )
        except Exception as cache_exc:
            logger.warning("Recommendation snapshot recompute skipped (%s)", type(cache_exc).__name__)

    return AssessmentSubmissionResponse(
        submission_id=row.id,
        riasec_vector=scored["normalized_vector"],
        riasec_raw_scores=scored["raw_sums"],
        cognitive_traits=scored["cognitive_traits"],
        dominant_traits=scored["dominant_traits"],
        xp_earned=scored["xp_earned"],
        interest_evidence=scored["interest"],
        cognitive_evidence=scored["cognitive"],
        summary=scored["summary_text"],
        completed_at=row.completed_at,
        changed=True,
        ai_cache_invalidated=True,
    )
