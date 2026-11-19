"""Catalog-grounded major information and evidence-limited student insights.

Public output is deterministic. Cache keys bind active catalog content and the
resolved actor-owned profile; no generative provider receives these profiles.
"""

import asyncio
import hashlib
import json
import logging
import uuid
import weakref
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.insight import MajorInsight, StudentSkillInsight
from app.schemas.insight import (
    AspirationAIAnalysisRequest,
    AspirationAIAnalysisResponse,
    AspirationMajorSuggestion,
    CareerPosition,
    InsightPoint,
    MajorInsightResponse,
    SkillGapItem,
    StudentSkillAnalysisRequest,
    StudentSkillAnalysisResponse,
    TrainingContent,
)

logger = logging.getLogger(__name__)

# In-flight lock theo (profile_hash, major_code) để chống bấm đúp / gọi trùng LLM song song.
_IN_FLIGHT_SKILL_LOCKS: "weakref.WeakValueDictionary[Tuple[str, str], asyncio.Lock]" = (
    weakref.WeakValueDictionary()
)


def _get_skill_lock(cache_key: Tuple[str, str]) -> asyncio.Lock:
    lock = _IN_FLIGHT_SKILL_LOCKS.get(cache_key)
    if lock is None:
        lock = asyncio.Lock()
        _IN_FLIGHT_SKILL_LOCKS[cache_key] = lock
    return lock

RIASEC_LABELS: Dict[str, str] = {
    "R": "Thực tế (thích làm việc cụ thể, máy móc, công cụ)",
    "I": "Nghiên cứu (thích phân tích, tìm hiểu nguyên nhân)",
    "A": "Nghệ thuật (thích sáng tạo, thể hiện cá tính)",
    "S": "Xã hội (thích giúp đỡ, kết nối con người)",
    "E": "Quản lý (thích dẫn dắt, thuyết phục)",
    "C": "Nghiệp vụ (thích quy trình, số liệu, tổ chức)",
}

# =========================================================================
# 1. MAJOR INSIGHT AGENT
# =========================================================================

async def _load_major_context(db: Optional[AsyncSession], major_code: str) -> Dict[str, Any]:
    from app.services.recommender.catalog import get_active_major_context
    return await get_active_major_context(db, major_code)


def build_deterministic_major_insight(ctx: Dict[str, Any]) -> Tuple[TrainingContent, List[CareerPosition], bool]:
    """Render catalog facts and clearly labelled study suggestions, never model prose."""
    name = ctx["name"]
    training = TrainingContent(
        overview=(f"Thông tin tham khảo về {name}. " + (ctx.get("description") or
            "Danh mục chưa có đề cương chi tiết; hãy đối chiếu chương trình của trường bạn quan tâm."))[:600],
        core_knowledge=[f"Tra cứu các học phần cơ sở và chuyên ngành của {name}",
                        "Đối chiếu môn tiên quyết trong đề cương của trường"],
        practical_skills=["Thử một bài tập nhập môn và ghi lại mức hứng thú, khó khăn",
                          "Trao đổi với giảng viên hoặc người đang làm nghề về công việc thực tế"],
        curriculum_highlights=["Các mục trên là gợi ý tìm hiểu, chưa phải chương trình đã được trường xác nhận."],
        study_duration="Chưa có dữ liệu xác minh; thời lượng phụ thuộc chương trình và trường.",
    )
    careers = [CareerPosition(title=str(title),
        description=f"Vị trí được ghi trong danh mục ngành {name}; điều kiện hành nghề cần đối chiếu riêng.",
        career_level="Tham khảo") for title in (ctx.get("careers") or [])[:6]]
    return training, careers, False


async def build_ai_major_insight(db: Optional[AsyncSession], ctx: Dict[str, Any]) -> Tuple[TrainingContent, List[CareerPosition], bool]:
    if db is None:
        return build_deterministic_major_insight(ctx)
    try:
        from app.services.ai_config.service import resolve_snapshot
        from app.services.ai_config import adapter
        from app.core.config import settings

        snapshot = await resolve_snapshot(db)
        name = ctx["name"]
        code = ctx.get("code") or ctx.get("major_code", "")
        category = ctx.get("category", "")
        existing_careers = ctx.get("careers") or []

        system_prompt = (
            "Bạn là Chuyên gia Cố vấn Học thuật & Hướng nghiệp Đại học tại Việt Nam.\n"
            f"Nhiệm vụ: Cung cấp thông tin thực tế, chuyên nghiệp và chi tiết về chương trình đào tạo và cơ hội nghề nghiệp cho ngành: **{name} (Mã ngành: {code}, Nhóm ngành: {category})**.\n"
            "Hãy trả về JSON object thuần túy (không kèm code block ```) theo đúng cấu trúc sau:\n"
            "{\n"
            '  "overview": "Mô tả 2-3 câu tổng quan về ngành, mục tiêu đào tạo và ứng dụng thực tế.",\n'
            '  "core_knowledge": ["3-4 môn học hoặc khối kiến thức nền tảng và chuyên ngành cốt lõi"],\n'
            '  "practical_skills": ["3-4 kỹ năng thực hành, công cụ hoặc kỹ năng nghề nghiệp quan trọng"],\n'
            '  "curriculum_highlights": ["2 điểm nổi bật về định hướng chương trình đào tạo"],\n'
            '  "study_duration": "4 năm (Cử nhân) hoặc 4.5 - 5 năm (Kỹ sư)",\n'
            '  "career_positions": [\n'
            '    {"title": "Tên chức danh nghề nghiệp 1", "description": "Mô tả công việc thực tế", "career_level": "Chuyên viên / Khởi điểm"},\n'
            '    {"title": "Tên chức danh 2", "description": "Mô tả công việc thực tế", "career_level": "Chuyên gia / Quản lý"}\n'
            "  ]\n"
            "}"
        )
        raw = await adapter.chat(
            snapshot,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Hãy tạo nội dung đào tạo và vị trí nghề nghiệp cho ngành {name}."},
            ],
            max_tokens=min(settings.LLM_MAX_TOKENS, 2048),
            timeout=min(settings.LLM_TIMEOUT_SECONDS, 45.0),
            response_format={"type": "json_object"},
        )
        data = json.loads(raw)
        overview = str(data.get("overview") or "").strip()
        core_knowledge = [str(k).strip() for k in data.get("core_knowledge", []) if str(k).strip()][:5]
        practical_skills = [str(s).strip() for s in data.get("practical_skills", []) if str(s).strip()][:5]
        curriculum_highlights = [str(h).strip() for h in data.get("curriculum_highlights", []) if str(h).strip()][:3]
        study_duration = str(data.get("study_duration") or "4 năm (theo quy chế đào tạo đại học)").strip()

        positions: List[CareerPosition] = []
        for p in data.get("career_positions", []):
            if isinstance(p, dict) and p.get("title"):
                positions.append(CareerPosition(
                    title=str(p["title"])[:100],
                    description=str(p.get("description") or f"Vị trí chuyên môn ngành {name}")[:300],
                    career_level=str(p.get("career_level") or "Chuyên viên")[:50],
                ))
        if not positions and existing_careers:
            positions = [CareerPosition(title=str(t), description=f"Vị trí việc làm ngành {name}", career_level="Chuyên viên") for t in existing_careers[:5]]

        if overview and (core_knowledge or practical_skills):
            training = TrainingContent(
                overview=overview[:600],
                core_knowledge=core_knowledge or ["Kiến thức nền tảng và chuyên ngành"],
                practical_skills=practical_skills or ["Kỹ năng thực hành chuyên môn"],
                curriculum_highlights=curriculum_highlights or ["Chương trình chuẩn theo quy định"],
                study_duration=study_duration[:100],
            )
            return training, positions, True
    except Exception as exc:
        logger.warning("[MajorInsight] AI generation failed for %s: %s", ctx.get("name"), exc)

    return build_deterministic_major_insight(ctx)


def _to_major_insight_response(entry: MajorInsight, cached: bool) -> MajorInsightResponse:
    training_data = entry.training_content or {}
    return MajorInsightResponse(
        major_code=entry.major_code,
        major_name=entry.major_name,
        training_content=TrainingContent(**training_data),
        career_positions=[CareerPosition(**c) for c in (entry.career_positions or [])],
        subject_blocks=list(entry.subject_blocks or []),
        is_ai_generated=bool(entry.is_ai_generated),
        cached=cached,
        generated_at=entry.generated_at.isoformat() if entry.generated_at else None,
    )


async def get_or_create_major_insight(
    db: Optional[AsyncSession],
    major_code: str,
    refresh: bool = False,
) -> MajorInsightResponse:
    """
    Cache-first: đọc `major_insights` theo major_code.
    Dựng từ danh mục hiện hành; cache chỉ dùng khi dấu vân tay nội dung còn khớp.
    """
    ctx = await _load_major_context(db, major_code)
    model_name = "catalog-v2:" + hashlib.sha256(json.dumps(ctx, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    if db is not None and not refresh:
        try:
            cached_entry = (
                await db.execute(select(MajorInsight).where(MajorInsight.major_code == major_code))
            ).scalar_one_or_none()
            if cached_entry and (cached_entry.is_ai_generated or cached_entry.model_name == model_name):
                return _to_major_insight_response(cached_entry, cached=True)
        except Exception as exc:
            logger.warning("[MajorInsight] Cache read failed for %s: %s", major_code, exc)

    training, career_positions, is_ai = await build_ai_major_insight(db, ctx)
    now = datetime.now(timezone.utc)

    if db is None:
        return MajorInsightResponse(
            major_code=major_code,
            major_name=ctx["name"],
            training_content=training,
            career_positions=career_positions,
            subject_blocks=list(ctx.get("blocks") or []),
            is_ai_generated=is_ai,
            cached=False,
            generated_at=now.isoformat(),
        )

    try:
        entry = (
            await db.execute(select(MajorInsight).where(MajorInsight.major_code == major_code))
        ).scalar_one_or_none()
        payload = {
            "major_name": ctx["name"],
            "training_content": training.model_dump(),
            "career_positions": [c.model_dump() for c in career_positions],
            "subject_blocks": list(ctx.get("blocks") or []),
            "is_ai_generated": is_ai,
            "model_name": model_name,
            "generated_at": now,
        }
        if entry:
            for key, value in payload.items():
                setattr(entry, key, value)
        else:
            entry = MajorInsight(id=uuid.uuid4(), major_code=major_code, **payload)
            db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return _to_major_insight_response(entry, cached=False)
    except Exception as exc:
        logger.warning("[MajorInsight] Persist failed for %s: %s", major_code, exc)
        try:
            await db.rollback()
        except Exception:
            pass
        return MajorInsightResponse(
            major_code=major_code,
            major_name=ctx["name"],
            training_content=training,
            career_positions=career_positions,
            subject_blocks=list(ctx.get("blocks") or []),
            is_ai_generated=is_ai,
            cached=False,
            generated_at=now.isoformat(),
        )


async def delete_major_insight(db: Optional[AsyncSession], major_code: str) -> bool:
    """Xoá bản ghi cache của một ngành. Trả về True nếu có bản ghi bị xoá."""
    if db is None:
        return False
    try:
        entry = (
            await db.execute(select(MajorInsight).where(MajorInsight.major_code == major_code))
        ).scalar_one_or_none()
        if not entry:
            return False
        await db.delete(entry)
        await db.commit()
        return True
    except Exception as exc:
        logger.warning("[MajorInsight] Delete failed for %s: %s", major_code, exc)
        try:
            await db.rollback()
        except Exception:
            pass
        return False


# =========================================================================
# 2. STUDENT SKILL AGENT
# =========================================================================

def _profile_hash(payload: StudentSkillAnalysisRequest) -> str:
    canonical = {"policy": "evidence-skills-v2", **payload.model_dump(mode="json", exclude_none=True)}
    raw = json.dumps(canonical, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_deterministic_skill_analysis(
    payload: StudentSkillAnalysisRequest,
    major_name: Optional[str] = None,
) -> Tuple[str, List[InsightPoint], List[InsightPoint], List[SkillGapItem]]:
    """Only observed scores and declared preferences; no inferred ability from interests."""
    from app.services.recommender.readiness import build_interest_evidence, validate_readiness_grades
    evidence = build_interest_evidence(getattr(payload, "riasec_answers", None), payload.riasec_scores)
    grades = validate_readiness_grades(payload.grades_by_subject)["scores"]
    strengths, weaknesses, gaps = [], [], []
    if evidence["status"] == "COMPLETE":
        groups = sorted(evidence["groups"], key=lambda group: -group["percent"])
        for group in groups[:2]:
            strengths.append(InsightPoint(title=f"Sở thích {group['code']}: {group['percent']:g}%",
                detail="Mức tự khai về hứng thú, không phải điểm đo năng lực hay xác suất trúng tuyển."))
    if grades:
        subject, score = max(grades.items(), key=lambda pair: pair[1])
        strengths.append(InsightPoint(title=f"Điểm {subject}: {score:g}",
            detail="Đây là điểm đã cung cấp; chưa đủ để khẳng định thành thạo kỹ năng chuyên ngành."))
        for subject, score in sorted(grades.items(), key=lambda pair: pair[1]):
            if score >= 7:
                continue
            weaknesses.append(InsightPoint(title=f"Cân nhắc ôn {subject}",
                detail=f"Điểm hiện có {score:g}/10. Nên làm bài chẩn đoán để biết phần nào cần ôn; đây không phải kết luận về năng lực nghề."))
            gaps.append(SkillGapItem(skill=f"Nền tảng môn {subject}",
                why="Gợi ý ôn tập từ điểm đã nhập, chưa phải lỗ hổng kỹ năng đã được đo.",
                how_to_improve=["Làm bài chẩn đoán ngắn để tìm phần chưa hiểu", "Chọn một chủ đề cần ôn và kiểm tra lại sau khi học"], priority="HIGH"))
    if not gaps and grades:
        gaps.append(SkillGapItem(skill="Kiểm tra nền tảng trước khi học chuyên ngành",
            why="Điểm học bạ không xác nhận kỹ năng tiên quyết; cần kiểm tra trước khi bỏ qua nội dung.",
            how_to_improve=["Đối chiếu đề cương môn nhập môn", "Làm bài chẩn đoán theo các môn tiên quyết"], priority="MEDIUM"))
    subject_text = f" cho ngành {major_name}" if major_name else ""
    summary = (f"Ghi nhận dữ liệu học tập{subject_text}. Sở thích và phong cách tự khai không phải phép đo năng lực. "
               "Các nội dung dưới đây là gợi ý kiểm tra/ôn tập, không kết luận đủ điều kiện tuyển sinh.")
    if not grades and evidence["status"] != "COMPLETE":
        summary = "Chưa đủ bằng chứng để phân tích cá nhân" + subject_text + ". Hãy bổ sung điểm hoặc hoàn thành bài sở thích; không suy ra điểm mạnh/yếu từ phần bỏ trống."
    else:
        aspiration = payload.aspiration if isinstance(payload.aspiration, dict) else {}
        dream_job = str(aspiration.get("dream_job") or aspiration.get("dreamJob") or "").strip()
        if dream_job:
            summary += f" Đã ghi nhận nguyện vọng nghề nghiệp '{dream_job}' để đối chiếu lộ trình ôn tập."
    return summary, strengths[:3], weaknesses[:3], gaps[:4]


_ASPIRATION_FIT_LABELS = {
    "HIGH": "Rất phù hợp",
    "MEDIUM": "Phù hợp một phần",
    "LOW": "Chưa phù hợp",
    "UNKNOWN": "Cần cân nhắc thêm",
}
_SKILL_POLICY_VERSION = "evidence-skills-v4"
_ASPIRATION_AI_MAJOR_CODE = "ASPIRATION_AI"
_ASPIRATION_POLICY_VERSION = "aspiration-ai-v1"


def _format_riasec_summary_from_payload(payload: Any) -> Tuple[str, Dict[str, Any]]:
    """Compute human-readable RIASEC scores from raw answers first, then fallback vector."""
    from app.services.recommender.readiness import build_interest_evidence

    evidence = build_interest_evidence(
        getattr(payload, "riasec_answers", None),
        getattr(payload, "riasec_scores", None),
    )
    groups = [g for g in evidence.get("groups", []) if g.get("percent") is not None]
    if groups:
        ranked = sorted(groups, key=lambda g: -float(g["percent"]))
        scores_str = ", ".join(f"{g['code']}: {round(float(g['percent']))}%" for g in ranked)
        status = evidence.get("status")
        if status == "COMPLETE":
            top3 = "".join(g["code"] for g in ranked[:3])
            return f"{scores_str} (Top 3 Holland: {top3}, hoàn thành 30/30 câu)", evidence
        if status == "NON_DISCRIMINATING":
            return f"{scores_str} (lưu ý: 6 nhóm bằng nhau, chưa phân hóa rõ)", evidence
        return f"{scores_str} (trạng thái: {status})", evidence
    raw_scores = getattr(payload, "riasec_scores", None) or {}
    if raw_scores:
        return ", ".join(f"{k}: {v}" for k, v in raw_scores.items()), evidence
    return "Chưa có điểm sở thích", evidence


async def _resolve_enriched_payload(
    db: Optional[AsyncSession],
    payload: Any,
    user_id: Optional[uuid.UUID],
) -> Tuple[Optional[uuid.UUID], Any, Optional[str], Optional[str]]:
    """Resolve authoritative owner and assessment evidence shared across insight agents."""
    from fastapi import HTTPException
    from app.services.llamaindex_rag_orchestrator.guidance_boundary import resolve_profile_owner
    from app.services.recommender.service import resolve_assessment_evidence

    resolved_user_id = resolve_profile_owner(payload.user_id, user_id)
    if payload.assessment_id and resolved_user_id is None:
        raise HTTPException(401, "Đăng nhập để xem bản đánh giá đã lưu.")
    raw = payload.model_dump(exclude_unset=True)
    evidence = await resolve_assessment_evidence(db, resolved_user_id, raw)
    eff_grade = (payload.grade_level or "").strip() or None
    eff_gender = (payload.gender or "").strip() or None
    enriched = payload.model_copy(
        update={
            "riasec_answers": evidence.get("riasec_answers") or {},
            "riasec_scores": evidence.get("riasec_scores") or {},
            "grades_by_subject": evidence.get("grades_by_subject") or {},
            "cognitive_preferences": evidence.get("cognitive_preferences") or {},
            "cognitive_answers": evidence.get("cognitive_preferences") or {},
            "aspiration": evidence.get("aspiration") or {},
            "score_context": evidence.get("score_context") or {},
            "grade_level": eff_grade,
            "gender": eff_gender,
        }
    )
    return resolved_user_id, enriched, eff_grade, eff_gender


async def _upsert_student_insight(
    db: AsyncSession,
    profile_hash: str,
    major_code: str,
    payload_data: Dict[str, Any],
) -> Optional[StudentSkillInsight]:
    """Persist or update cached StudentSkillInsight row without failing caller on DB error."""
    try:
        stmt = select(StudentSkillInsight).where(
            StudentSkillInsight.profile_hash == profile_hash,
            StudentSkillInsight.major_code == major_code,
        )
        entry = (await db.execute(stmt)).scalar_one_or_none()
        if entry:
            for key, value in payload_data.items():
                if key == "user_id" and value is None:
                    continue
                setattr(entry, key, value)
        else:
            entry = StudentSkillInsight(
                id=uuid.uuid4(),
                profile_hash=profile_hash,
                major_code=major_code,
                **payload_data,
            )
            db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry
    except Exception as exc:
        logger.warning("[InsightAgent] Persist failed (%s): %s", major_code, exc)
        try:
            await db.rollback()
        except Exception:
            pass
        return None


def _to_skill_response(entry: StudentSkillInsight, cached: bool) -> StudentSkillAnalysisResponse:
    return StudentSkillAnalysisResponse(
        profile_hash=entry.profile_hash,
        major_code=entry.major_code or "",
        summary=entry.summary,
        strengths=[InsightPoint(**p) for p in (entry.strengths or [])],
        weaknesses=[InsightPoint(**p) for p in (entry.weaknesses or [])],
        skill_gaps=sorted(
            (SkillGapItem(**g) for g in (entry.skill_gaps or [])),
            key=lambda gap: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(gap.priority, 1),
        ),
        is_ai_generated=bool(entry.is_ai_generated),
        cached=cached,
        insight_id=entry.id,
    )


def _to_aspiration_ai_response(
    entry: StudentSkillInsight,
    dream_job: str,
    cached: bool,
) -> AspirationAIAnalysisResponse:
    fit_level = "UNKNOWN"
    raw_model = entry.model_name or ""
    if ":" in raw_model:
        candidate = raw_model.split(":", 1)[1].strip().upper()
        if candidate in _ASPIRATION_FIT_LABELS:
            fit_level = candidate
    return AspirationAIAnalysisResponse(
        profile_hash=entry.profile_hash,
        dream_job=dream_job,
        fit_level=fit_level,
        fit_label=_ASPIRATION_FIT_LABELS[fit_level],
        summary=entry.summary,
        reasons_fit=[InsightPoint(**p) for p in (entry.strengths or []) if isinstance(p, dict)],
        reasons_gap=[InsightPoint(**p) for p in (entry.weaknesses or []) if isinstance(p, dict)],
        better_majors=[
            AspirationMajorSuggestion(**m) for m in (entry.skill_gaps or []) if isinstance(m, dict)
        ],
        is_ai_generated=bool(entry.is_ai_generated),
        cached=cached,
        insight_id=entry.id,
    )


async def analyze_student_skills(
    db: Optional[AsyncSession],
    payload: StudentSkillAnalysisRequest,
    user_id: Optional[uuid.UUID] = None,
) -> StudentSkillAnalysisResponse:
    """Phân tích ưu/nhược điểm kỹ năng theo hồ sơ với Smart DB Cache (evidence-skills-v4)."""
    user_id, payload, eff_grade, eff_gender = await _resolve_enriched_payload(db, payload, user_id)
    major_code = (payload.major_code or "").strip()
    major_name = None
    ctx = {}
    if major_code:
        ctx = await _load_major_context(db, major_code)
        major_name = ctx["name"]
    profile_hash = hashlib.sha256(json.dumps({
        "owner": str(user_id or "guest"),
        "profile": _profile_hash(payload),
        "grade_level": (eff_grade or "").lower(),
        "gender": (eff_gender or "").lower(),
        "catalog_context": ctx,
        "policy": _SKILL_POLICY_VERSION,
    }, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()

    async with _get_skill_lock((profile_hash, major_code)):
        if db is not None:
            try:
                stmt = select(StudentSkillInsight).where(
                    StudentSkillInsight.profile_hash == profile_hash,
                    StudentSkillInsight.major_code == major_code,
                )
                cached_entry = (await db.execute(stmt)).scalar_one_or_none()
                if cached_entry and cached_entry.model_name == _SKILL_POLICY_VERSION:
                    return _to_skill_response(cached_entry, cached=True)
            except Exception as exc:
                logger.warning("[SkillAgent] Cache read failed: %s", exc)

        summary, strengths, weaknesses, gaps = build_deterministic_skill_analysis(payload, major_name)
        is_ai = False
        has_any_evidence = bool(payload.grades_by_subject or payload.riasec_scores or payload.riasec_answers)

        if db is not None and major_name and has_any_evidence:
            try:
                from app.services.ai_config.service import resolve_snapshot
                from app.services.ai_config import adapter
                from app.core.config import settings
                from app.services.llamaindex_rag_orchestrator.guidance_rag import sanitize_pii

                snapshot = await resolve_snapshot(db)
                scores_text = ", ".join(f"{k}: {v}" for k, v in (payload.grades_by_subject or {}).items()) or "Chưa nhập điểm cụ thể"
                riasec_text, _ = _format_riasec_summary_from_payload(payload)
                context_bits = []
                if eff_grade:
                    context_bits.append(f"Khối lớp: {eff_grade}")
                if eff_gender:
                    context_bits.append(f"Giới tính: {eff_gender}")
                context_line = f"- Bối cảnh học sinh: {', '.join(context_bits)}\n" if context_bits else ""
                aspiration = payload.aspiration if isinstance(payload.aspiration, dict) else {}
                raw_dream = str(aspiration.get("dream_job") or aspiration.get("dreamJob") or "").strip()
                dream_job = sanitize_pii(raw_dream)[:120] if raw_dream else ""
                score_strategy = str(aspiration.get("score_strategy") or aspiration.get("scoreStrategy") or "").strip()
                aspiration_line = (
                    f"- Nguyện vọng nghề nghiệp mơ ước của học sinh: {dream_job} (Chiến lược: {score_strategy or 'Linh hoạt'})\n"
                    if dream_job
                    else ""
                )
                aspiration_instruction = (
                    f" Đặc biệt nhận xét trực tiếp mức độ khớp/lệch giữa hồ sơ hiện tại (điểm số, sở thích) với nghề mơ ước '{dream_job}' và ngành '{major_name}', cùng môn học hoặc kỹ năng cần ưu tiên cải thiện để tiến gần mục tiêu."
                    if dream_job
                    else ""
                )

                system_prompt = (
                    "Bạn là Chuyên gia Cố vấn Kỹ năng & Lộ trình Học tập của hệ thống AI CareerGuide.\n"
                    f"Nhiệm vụ: Phân tích kỹ năng và khoảng trống năng lực của học sinh đối với ngành **{major_name}**.\n"
                    f"{context_line}"
                    f"{aspiration_line}"
                    f"- Dữ liệu điểm học lực: {scores_text}\n"
                    f"- Dữ liệu sở thích Holland: {riasec_text}\n"
                    f"{aspiration_instruction}\n\n"
                    "Hãy trả về JSON object thuần túy theo đúng cấu trúc sau:\n"
                    "{\n"
                    '  "summary": "Tóm tắt 2-3 câu ngắn gọn về thế mạnh, mức độ phù hợp với ngành/nguyện vọng và trọng tâm cần ưu tiên.",\n'
                    '  "strengths": [{"title": "Tên điểm mạnh nổi bật", "detail": "Giải thích ngắn gọn"}],\n'
                    '  "weaknesses": [{"title": "Môn học hoặc điểm cần ôn tập", "detail": "Giải thích ngắn gọn"}],\n'
                    '  "skill_gaps": [\n'
                    '    {"skill": "Tên kỹ năng chuyên môn cốt lõi cần rèn luyện cho ngành này", "why": "Lý do kỹ năng này cần thiết", "how_to_improve": ["Cách tự rèn luyện 1", "Cách tự học 2"], "priority": "HIGH"}\n'
                    '  ]\n'
                    "}"
                )
                raw = await adapter.chat(
                    snapshot,
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Hãy phân tích kỹ năng và gợi ý rèn luyện cho tôi với ngành {major_name}."},
                    ],
                    max_tokens=min(settings.LLM_MAX_TOKENS, 1500),
                    timeout=min(settings.LLM_TIMEOUT_SECONDS, 45.0),
                    response_format={"type": "json_object"},
                )
                ai_data = json.loads(raw)
                ai_summary = str(ai_data.get("summary") or "").strip()
                ai_strengths = [InsightPoint(title=str(p.get("title") or "")[:80], detail=str(p.get("detail") or "")[:200]) for p in ai_data.get("strengths", []) if isinstance(p, dict) and p.get("title")][:3]
                ai_weaknesses = [InsightPoint(title=str(p.get("title") or "")[:80], detail=str(p.get("detail") or "")[:200]) for p in ai_data.get("weaknesses", []) if isinstance(p, dict) and p.get("title")][:3]
                ai_gaps = []
                for g in ai_data.get("skill_gaps", []):
                    if isinstance(g, dict) and g.get("skill"):
                        ai_gaps.append(SkillGapItem(
                            skill=str(g["skill"])[:100],
                            why=str(g.get("why") or f"Kỹ năng quan trọng cho ngành {major_name}")[:250],
                            how_to_improve=[str(h) for h in g.get("how_to_improve", []) if str(h).strip()][:3] or ["Tìm hiểu tài liệu chuyên ngành", "Thực hành bài tập thực tế"],
                            priority=g.get("priority") if g.get("priority") in {"HIGH", "MEDIUM", "LOW"} else "HIGH",
                        ))
                if ai_summary and (ai_strengths or ai_gaps):
                    summary = ai_summary
                    strengths = ai_strengths or strengths
                    weaknesses = ai_weaknesses or weaknesses
                    gaps = ai_gaps or gaps
                    is_ai = True
            except Exception as exc:
                logger.warning("[SkillAgent] AI skill analysis failed for %s: %s", major_name, exc)

        if db is None:
            return StudentSkillAnalysisResponse(
                profile_hash=profile_hash,
                major_code=major_code,
                summary=summary,
                strengths=strengths,
                weaknesses=weaknesses,
                skill_gaps=gaps,
                is_ai_generated=is_ai,
                cached=False,
            )

        payload_data = {
            "user_id": user_id,
            "summary": summary,
            "strengths": [p.model_dump() for p in strengths],
            "weaknesses": [p.model_dump() for p in weaknesses],
            "skill_gaps": [g.model_dump() for g in gaps],
            "is_ai_generated": is_ai,
            "model_name": _SKILL_POLICY_VERSION,
        }
        entry = await _upsert_student_insight(db, profile_hash, major_code, payload_data)
        if entry is not None:
            return _to_skill_response(entry, cached=False)
        return StudentSkillAnalysisResponse(
            profile_hash=profile_hash,
            major_code=major_code,
            summary=summary,
            strengths=strengths,
            weaknesses=weaknesses,
            skill_gaps=gaps,
            is_ai_generated=is_ai,
            cached=False,
        )


def _extract_aspiration_candidates(
    aspiration_eval: Dict[str, Any],
    top_majors: List[Any],
    exclude_codes: set[str],
) -> Tuple[List[AspirationMajorSuggestion], Dict[str, Dict[str, Any]]]:
    """Collect real verified catalog candidates for both fallback and LLM grounding."""
    candidates_map: Dict[str, Dict[str, Any]] = {}
    suggestions: List[AspirationMajorSuggestion] = []

    def _register(code: str, name: str, reason: str, match_score: Optional[int], block: Optional[str], tier: str) -> None:
        if not code or not name:
            return
        if code not in candidates_map:
            candidates_map[code] = {
                "major_code": code,
                "major_name": name,
                "match_score": match_score,
                "block": block,
                "tier": tier,
            }
        if code not in exclude_codes and len(suggestions) < 3 and all(s.major_code != code for s in suggestions):
            suggestions.append(
                AspirationMajorSuggestion(
                    major_code=code,
                    major_name=name,
                    reason=reason[:220],
                    match_score=match_score,
                )
            )

    for b in (aspiration_eval.get("recommended_substitutes") or []):
        if isinstance(b, dict):
            score = b.get("overall_match")
            reason = str(b.get("relation_reason") or "Phù hợp đồng thời với sở thích Holland và năng lực học lực hiện tại.")
            _register(str(b.get("major_code") or ""), str(b.get("major_name") or ""), reason, score, b.get("best_matching_block"), str(b.get("feasibility_tier") or "TARGET"))

    for b in (aspiration_eval.get("current_options") or []):
        if isinstance(b, dict):
            score = b.get("overall_match")
            reason = str(b.get("relation_reason") or b.get("admission_advice") or "Đạt mốc tham chiếu và liên quan trực tiếp đến định hướng của bạn.")
            _register(str(b.get("major_code") or ""), str(b.get("major_name") or ""), reason, score, b.get("best_matching_block"), str(b.get("feasibility_tier") or "TARGET"))

    for item in (top_majors or []):
        code = str(getattr(item, "major_code", "") or (item.get("major_code") if isinstance(item, dict) else "") or "")
        name = str(getattr(item, "major_name", "") or (item.get("major_name") if isinstance(item, dict) else "") or "")
        if not code or not name:
            continue
        raw_overall = getattr(item, "overall_score", None) if not isinstance(item, dict) else item.get("overall_score")
        score = round(float(raw_overall) * 100) if raw_overall is not None else None
        tier = str((getattr(item, "feasibility_tier", None) if not isinstance(item, dict) else item.get("feasibility_tier")) or "TARGET")
        block = getattr(item, "best_matching_block", None) if not isinstance(item, dict) else item.get("best_matching_block")
        factors = (getattr(item, "top_supporting_factors", None) if not isinstance(item, dict) else item.get("top_supporting_factors")) or []
        reason = str(factors[0]) if factors else f"Khớp cao nhất với hồ sơ Holland và điểm tổ hợp {block or 'hiện có'}."
        _register(code, name, reason, score, block, tier)

    return suggestions[:3], candidates_map


def build_deterministic_aspiration_ai(
    dream_job: str,
    grades: Dict[str, Any],
    riasec_evidence: Dict[str, Any],
    aspiration_eval: Dict[str, Any],
    top_majors: List[Any],
) -> Tuple[str, str, str, List[InsightPoint], List[InsightPoint], List[AspirationMajorSuggestion], Dict[str, Dict[str, Any]], bool]:
    """Compute grounded aspiration verdict, reasons, and real catalog alternatives."""
    dream_majors = aspiration_eval.get("dream_majors") or []
    primary = dream_majors[0] if dream_majors and isinstance(dream_majors[0], dict) else None
    strong_veto = bool(primary and primary.get("subfacet_status") == "STRONG_VETO")
    reasons_fit: List[InsightPoint] = []
    reasons_gap: List[InsightPoint] = []

    if primary:
        major_name = str(primary.get("major_name") or dream_job)
        riasec_fit = primary.get("riasec_fit")
        subfacet_status = primary.get("subfacet_status")
        subfacet_note = str(primary.get("subfacet_note") or "").strip()
        trait_warning = str(primary.get("trait_warning") or "").strip()
        readiness = primary.get("readiness") if isinstance(primary.get("readiness"), dict) else {}
        tier = str(primary.get("feasibility_tier") or "UNKNOWN")

        if riasec_fit is not None and riasec_fit >= 60 and not strong_veto:
            reasons_fit.append(
                InsightPoint(
                    title="Sở thích Holland tương thích",
                    detail=f"Mức độ khớp nhóm sở thích đạt {riasec_fit}% với đặc trưng ngành {major_name}.",
                )
            )
        if subfacet_status == "AFFINITY_BOOST" and subfacet_note:
            reasons_fit.append(InsightPoint(title="Khớp câu hỏi chi tiết", detail=subfacet_note[:200]))
        if readiness.get("status") == "READY_REFERENCE":
            blk = readiness.get("block") or ""
            reasons_fit.append(
                InsightPoint(
                    title=f"Đạt mốc học lực khối {blk}".strip(),
                    detail=str(readiness.get("message") or "Điểm hiện tại đạt mốc tham chiếu.")[:200],
                )
            )

        if subfacet_status in {"STRONG_VETO", "SOFT_PENALTY"} and subfacet_note:
            reasons_gap.append(InsightPoint(title="Lệch ở hoạt động cốt lõi (Veto)", detail=subfacet_note[:200]))
        if trait_warning and not (subfacet_status in {"STRONG_VETO", "SOFT_PENALTY"} and subfacet_note):
            reasons_gap.append(InsightPoint(title="Khác biệt xu hướng Holland", detail=trait_warning[:200]))
        if readiness.get("status") == "NEEDS_IMPROVEMENT":
            blk = readiness.get("block") or "xét tuyển"
            reasons_gap.append(
                InsightPoint(
                    title=f"Chưa đạt mốc điểm khối {blk}",
                    detail=str(readiness.get("message") or "Cần cải thiện thêm điểm các môn xét tuyển.")[:200],
                )
            )
        elif readiness.get("missing_subjects"):
            reasons_gap.append(
                InsightPoint(
                    title="Thiếu điểm môn xét tuyển",
                    detail=f"Cần bổ sung điểm: {', '.join(readiness['missing_subjects'])}.",
                )
            )

        if strong_veto or (riasec_fit is not None and riasec_fit < 45):
            fit_level = "LOW"
            summary = f"Nguyện vọng '{dream_job}' (ngành {major_name}) đang có dấu hiệu lệch đáng kể so với sở thích thực tế của bạn."
        elif subfacet_status == "SOFT_PENALTY" or tier == "REACH" or (riasec_fit is not None and riasec_fit < 65):
            fit_level = "MEDIUM"
            summary = f"Nguyện vọng '{dream_job}' phù hợp một phần với hồ sơ, nhưng vẫn còn khoảng trống về điểm số hoặc sở thích chi tiết."
        else:
            fit_level = "HIGH"
            summary = f"Nguyện vọng '{dream_job}' rất phù hợp với tổ hợp sở thích Holland và nền tảng học tập hiện có của bạn."
    else:
        fit_level = "MEDIUM" if (aspiration_eval.get("current_options") or top_majors) else "UNKNOWN"
        summary = str(aspiration_eval.get("agent_verdict") or f"Đã đối chiếu nguyện vọng '{dream_job}' với hồ sơ năng lực hiện tại.")
        match_status = aspiration_eval.get("match_status")
        if match_status in {"UNRECOGNIZED", "AMBIGUOUS"}:
            reasons_gap.append(
                InsightPoint(
                    title="Tên nghề chưa khớp rõ 1 ngành",
                    detail="Hãy thử nhập tên ngành cụ thể hơn (ví dụ: Công nghệ thông tin, Marketing, Tâm lý học).",
                )
            )

    if not reasons_fit and grades:
        top_subj, top_score = max(grades.items(), key=lambda pair: float(pair[1]))
        reasons_fit.append(
            InsightPoint(
                title=f"Thế mạnh học tập môn {top_subj} ({float(top_score):g}/10)",
                detail="Đây là nền tảng tốt có thể tận dụng cho các ngành phù hợp hơn bên dưới.",
            )
        )
    if riasec_evidence.get("status") == "NON_DISCRIMINATING":
        reasons_gap.append(
            InsightPoint(
                title="6 nhóm sở thích chưa phân hóa",
                detail="Các câu trả lời đang đồng đều nên chưa kết luận chắc chắn độ khớp sở thích.",
            )
        )

    exclude_codes = set()
    if primary and fit_level in {"LOW", "MEDIUM"} and primary.get("major_code"):
        exclude_codes.add(str(primary["major_code"]))
    better_majors, candidate_map = _extract_aspiration_candidates(aspiration_eval, top_majors, exclude_codes)
    return fit_level, _ASPIRATION_FIT_LABELS[fit_level], summary, reasons_fit[:3], reasons_gap[:3], better_majors, candidate_map, strong_veto


async def analyze_aspiration_with_ai(
    db: Optional[AsyncSession],
    payload: AspirationAIAnalysisRequest,
    user_id: Optional[uuid.UUID] = None,
) -> AspirationAIAnalysisResponse:
    """AI đánh giá mức độ phù hợp của nghề mơ ước theo hồ sơ & gợi ý ngành phù hợp hơn (Smart DB Cache)."""
    from app.services.recommender.readiness import validate_readiness_grades
    from app.services.llamaindex_rag_orchestrator.guidance_rag import sanitize_pii

    user_id, payload, eff_grade, eff_gender = await _resolve_enriched_payload(db, payload, user_id)
    aspiration_dict = dict(payload.aspiration or {})
    raw_dream = str(payload.dream_job or aspiration_dict.get("dream_job") or aspiration_dict.get("dreamJob") or "").strip()
    dream_job = sanitize_pii(raw_dream)[:180] if raw_dream else ""
    if dream_job:
        aspiration_dict["dream_job"] = dream_job
        aspiration_dict["dreamJob"] = dream_job
        payload = payload.model_copy(update={"aspiration": aspiration_dict})

    profile_hash = hashlib.sha256(json.dumps({
        "owner": str(user_id or "guest"),
        "profile": _profile_hash(payload),
        "dream_job": dream_job.lower(),
        "grade_level": (eff_grade or "").lower(),
        "gender": (eff_gender or "").lower(),
        "policy": _ASPIRATION_POLICY_VERSION,
    }, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()

    if not dream_job:
        return AspirationAIAnalysisResponse(
            profile_hash=profile_hash,
            dream_job="",
            fit_level="UNKNOWN",
            fit_label="Chưa nhập nghề mơ ước",
            summary="Hãy nhập nghề nghiệp hoặc ngành học mơ ước để AI đối chiếu với sở thích Holland và năng lực học tập của bạn.",
            reasons_fit=[],
            reasons_gap=[],
            better_majors=[],
            is_ai_generated=False,
            cached=False,
        )

    riasec_text, riasec_evidence = _format_riasec_summary_from_payload(payload)
    grades = {k: float(v) for k, v in validate_readiness_grades(payload.grades_by_subject)["scores"].items()}
    has_evidence = bool(grades or payload.riasec_answers or payload.riasec_scores)
    if not has_evidence:
        return AspirationAIAnalysisResponse(
            profile_hash=profile_hash,
            dream_job=dream_job,
            fit_level="UNKNOWN",
            fit_label="Chưa đủ dữ liệu hồ sơ",
            summary=f"Đã ghi nhận nguyện vọng '{dream_job}', nhưng hồ sơ chưa có điểm học bạ hoặc kết quả trắc nghiệm Holland để đối chiếu.",
            reasons_fit=[],
            reasons_gap=[
                InsightPoint(
                    title="Thiếu dữ liệu đánh giá",
                    detail="Hãy hoàn thành bài test Holland RIASEC và nhập điểm học bạ để AI phân tích chính xác.",
                )
            ],
            better_majors=[],
            is_ai_generated=False,
            cached=False,
        )

    async with _get_skill_lock((profile_hash, _ASPIRATION_AI_MAJOR_CODE)):
        if db is not None:
            try:
                stmt = select(StudentSkillInsight).where(
                    StudentSkillInsight.profile_hash == profile_hash,
                    StudentSkillInsight.major_code == _ASPIRATION_AI_MAJOR_CODE,
                )
                cached_entry = (await db.execute(stmt)).scalar_one_or_none()
                if cached_entry and (cached_entry.model_name or "").startswith(f"{_ASPIRATION_POLICY_VERSION}:"):
                    return _to_aspiration_ai_response(cached_entry, dream_job, cached=True)
            except Exception as exc:
                logger.warning("[AspirationAIAgent] Cache read failed: %s", exc)

        aspiration_eval: Dict[str, Any] = {}
        top_majors: List[Any] = []
        if db is not None:
            try:
                from app.services.recommender.service import evaluate_dashboard_profile_bundle

                bundle = await evaluate_dashboard_profile_bundle(
                    db=db,
                    user_id=user_id,
                    top_k=10,
                    inline_profile={
                        "riasec_answers": payload.riasec_answers or {},
                        "riasec_scores": payload.riasec_scores or {},
                        "grades_by_subject": payload.grades_by_subject or {},
                        "cognitive_preferences": payload.cognitive_preferences or {},
                        "aspiration": aspiration_dict,
                        "score_context": payload.score_context or {},
                        "gender": eff_gender,
                        "grade_level": eff_grade,
                    },
                    persist_history=False,
                    gender=eff_gender,
                    grade_level=eff_grade,
                )
                aspiration_eval = bundle.get("aspirationAnalysis") or {}
                top_majors = bundle.get("majors") or []
            except Exception as exc:
                logger.warning("[AspirationAIAgent] Recommender grounding failed: %s", exc)

        (
            fit_level,
            fit_label,
            summary,
            reasons_fit,
            reasons_gap,
            better_majors,
            candidate_map,
            strong_veto,
        ) = build_deterministic_aspiration_ai(dream_job, grades, riasec_evidence, aspiration_eval, top_majors)
        is_ai = False

        if db is not None:
            try:
                from app.services.ai_config.service import resolve_snapshot
                from app.services.ai_config import adapter
                from app.core.config import settings

                snapshot = await resolve_snapshot(db)
                scores_text = ", ".join(f"{k}: {v}" for k, v in grades.items()) or "Chưa nhập điểm"
                candidate_lines = "\n".join(
                    f"- {c['major_code']}: {c['major_name']} (Độ khớp: {c['match_score']}%, Mức khả thi: {c['tier']}, Khối: {c['block'] or 'N/A'})"
                    for c in list(candidate_map.values())[:8]
                ) or "Chưa có ứng viên cụ thể"
                primary_dream = (aspiration_eval.get("dream_majors") or [None])[0]
                dream_diag = ""
                if isinstance(primary_dream, dict):
                    dream_diag = (
                        f"- Ngành gần nhất với nguyện vọng trong danh mục: {primary_dream.get('major_code')} - {primary_dream.get('major_name')}, "
                        f"RIASEC fit: {primary_dream.get('riasec_fit')}%, Mức học lực: {primary_dream.get('feasibility_label')}, "
                        f"Veto chi tiết: {primary_dream.get('subfacet_status')} ({primary_dream.get('subfacet_note') or 'Không'}).\n"
                    )

                system_prompt = (
                    "Bạn là Chuyên gia Tư vấn Hướng nghiệp của hệ thống AI CareerGuide.\n"
                    f"Nhiệm vụ: Đánh giá trung thực xem nghề mơ ước **'{dream_job}'** có phù hợp với hồ sơ thực tế của học sinh hay không, giải thích rõ lý do, và chọn các ngành phù hợp hơn TỪ DANH SÁCH ĐƯỢC CUNG CẤP.\n"
                    f"- Điểm học lực: {scores_text}\n"
                    f"- Sở thích Holland RIASEC: {riasec_text}\n"
                    f"- Khối lớp: {eff_grade or 'Chưa rõ'}\n"
                    f"{dream_diag}"
                    f"Danh sách ngành có thật từ hệ thống (CHỈ chọn major_code từ danh sách này, KHÔNG tự bịa mã):\n{candidate_lines}\n\n"
                    "Trả về JSON thuần túy theo đúng schema:\n"
                    "{\n"
                    '  "fit_level": "HIGH | MEDIUM | LOW",\n'
                    '  "summary": "Nhận định tổng quan 2-3 câu ngắn gọn, thẳng thắn, dễ hiểu.",\n'
                    '  "reasons_fit": [{"title": "Điểm phù hợp 1", "detail": "Giải thích ngắn gọn dựa trên điểm/sở thích"}],\n'
                    '  "reasons_gap": [{"title": "Điểm chưa khớp 1", "detail": "Giải thích rõ nguyên nhân lệch sở thích hoặc thiếu điểm"}],\n'
                    '  "better_majors": [{"major_code": "Mã ngành 7 số từ danh sách trên", "reason": "1 câu giải thích vì sao ngành này hợp hồ sơ hơn hoặc dễ đạt hơn"}]\n'
                    "}"
                )
                raw = await adapter.chat(
                    snapshot,
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Hãy phân tích nguyện vọng nghề '{dream_job}' của tôi so với hồ sơ hiện tại."},
                    ],
                    max_tokens=min(settings.LLM_MAX_TOKENS, 1400),
                    timeout=min(settings.LLM_TIMEOUT_SECONDS, 45.0),
                    response_format={"type": "json_object"},
                )
                ai_data = json.loads(raw)
                ai_summary = str(ai_data.get("summary") or "").strip()
                ai_fit = str(ai_data.get("fit_level") or fit_level).strip().upper()
                if strong_veto:
                    ai_fit = "LOW"
                elif fit_level == "LOW" and ai_fit == "HIGH":
                    ai_fit = "MEDIUM"
                elif ai_fit not in {"HIGH", "MEDIUM", "LOW"}:
                    ai_fit = fit_level

                ai_reasons_fit = [
                    InsightPoint(title=str(p.get("title") or "")[:80], detail=str(p.get("detail") or "")[:200])
                    for p in ai_data.get("reasons_fit", [])
                    if isinstance(p, dict) and p.get("title")
                ][:3]
                ai_reasons_gap = [
                    InsightPoint(title=str(p.get("title") or "")[:80], detail=str(p.get("detail") or "")[:200])
                    for p in ai_data.get("reasons_gap", [])
                    if isinstance(p, dict) and p.get("title")
                ][:3]
                ai_better: List[AspirationMajorSuggestion] = []
                for m in ai_data.get("better_majors", []):
                    if not isinstance(m, dict):
                        continue
                    code = str(m.get("major_code") or "").strip()
                    if code in candidate_map and all(x.major_code != code for x in ai_better):
                        meta = candidate_map[code]
                        ai_better.append(
                            AspirationMajorSuggestion(
                                major_code=code,
                                major_name=meta["major_name"],
                                reason=str(m.get("reason") or "Phù hợp tốt với sở thích và điểm số của bạn.")[:220],
                                match_score=meta.get("match_score"),
                            )
                        )
                    if len(ai_better) >= 3:
                        break

                if ai_summary:
                    fit_level = ai_fit
                    fit_label = _ASPIRATION_FIT_LABELS[fit_level]
                    summary = ai_summary
                    reasons_fit = ai_reasons_fit or reasons_fit
                    reasons_gap = ai_reasons_gap or reasons_gap
                    better_majors = ai_better or better_majors
                    is_ai = True
            except Exception as exc:
                logger.warning("[AspirationAIAgent] LLM aspiration analysis failed for '%s': %s", dream_job, exc)

        if db is None:
            return AspirationAIAnalysisResponse(
                profile_hash=profile_hash,
                dream_job=dream_job,
                fit_level=fit_level,
                fit_label=fit_label,
                summary=summary,
                reasons_fit=reasons_fit,
                reasons_gap=reasons_gap,
                better_majors=better_majors,
                is_ai_generated=is_ai,
                cached=False,
            )

        payload_data = {
            "user_id": user_id,
            "summary": summary,
            "strengths": [p.model_dump() for p in reasons_fit],
            "weaknesses": [p.model_dump() for p in reasons_gap],
            "skill_gaps": [m.model_dump() for m in better_majors],
            "is_ai_generated": is_ai,
            "model_name": f"{_ASPIRATION_POLICY_VERSION}:{fit_level}",
        }
        entry = await _upsert_student_insight(db, profile_hash, _ASPIRATION_AI_MAJOR_CODE, payload_data)
        if entry is not None:
            return _to_aspiration_ai_response(entry, dream_job, cached=False)
        return AspirationAIAnalysisResponse(
            profile_hash=profile_hash,
            dream_job=dream_job,
            fit_level=fit_level,
            fit_label=fit_label,
            summary=summary,
            reasons_fit=reasons_fit,
            reasons_gap=reasons_gap,
            better_majors=better_majors,
            is_ai_generated=is_ai,
            cached=False,
        )
