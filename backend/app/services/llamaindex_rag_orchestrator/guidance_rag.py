import uuid
import re
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.roadmap import MajorRoadmap
from app.models.taxonomy import Major
from app.models.vector import KnowledgeEmbedding
from app.schemas.rag import (
    GuidancePersonalizationRequest,
    GuidancePersonalizationResponse,
    PersonalizedScheduleTask,
    SemanticSearchRequest,
    ChunkSearchResult,
    AIExplanationRequest,
    AIExplanationResponse,
    AIChatMessage,
    AIChatRequest,
    AIChatResponse,
)
from app.models.assessment import StudentAssessment, StudentGrade, StudentDiagnosticTest
from app.services.recommender.engine import RIASEC_NAMES_VI, RIASEC_DIMENSIONS, calculate_riasec_cosine_similarity
from app.services.gap_roadmap_engine.gap_engine import (
    infer_mastered_skills_from_diagnostic_tests,
    infer_mastered_skills_from_grades
)
from app.services.llamaindex_rag_orchestrator.hitl_governance import get_text_embedding
from app.services.gap_roadmap_engine.service import generate_static_fallback_roadmap

logger = logging.getLogger(__name__)

def sanitize_pii(text: str) -> str:
    """
    Sanitizes Personally Identifiable Information (PII) before passing context
    to external AI APIs to comply with OWASP ASVS Level 2 and Vietnamese Law 91/2025/QH15.
    Strictly removes emails, phone numbers, national IDs, student IDs, personal names,
    and addresses while preserving pure academic metrics (scores, test answers).
    """
    if not text:
        return ""
    # Sanitize email addresses
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[REDACTED_EMAIL]', text)
    # Sanitize Vietnamese telephone numbers
    text = re.sub(r'(\+84|0[3|5|7|8|9])([0-9]{8})\b', '[REDACTED_PHONE]', text)
    # Sanitize citizen identity card numbers (12 digits)
    text = re.sub(r'\b\d{12}\b', '[REDACTED_ID]', text)
    # Sanitize student ID sequences (10-11 digits)
    text = re.sub(r'\b\d{10,11}\b', '[REDACTED_STUDENT_ID]', text)
    # Sanitize self-introduced personal names
    text = re.sub(r'(?i)(tên tôi là|em tên là|tôi tên là|tên em là)\s+([A-ZÀ-Ỹa-zà-ỹ\s]+)', r'\1 [REDACTED_NAME]', text)
    # Sanitize addresses / locations
    text = re.sub(r'(?i)(nhà ở|địa chỉ|ở tại|sống tại|quê ở)\s+([A-ZÀ-Ỹa-zà-ỹ0-9,\s]+)', r'\1 [REDACTED_ADDRESS]', text)
    # Sanitize school names
    text = re.sub(r'(?i)(trường thpt|học sinh trường|học trường)\s+([A-ZÀ-Ỹa-zà-ỹ0-9\s]+)', r'trường [REDACTED_SCHOOL]', text)
    return text


def build_fallback_personalized_schedule(
    major_code: str,
    major_name: str,
    missing_skills: List[str],
    weekly_hours: int,
    milestones: List[Dict[str, Any]]
) -> List[PersonalizedScheduleTask]:
    """
    Deterministic rule-based schedule generator used when AI API times out (> 8s)
    or for majors awaiting full curation (NFR01, NFR05).
    """
    tasks: List[PersonalizedScheduleTask] = []
    effective_milestones = milestones if milestones else generate_static_fallback_roadmap(major_code, major_name)["milestones"]
    
    for idx, milestone in enumerate(effective_milestones[:4], start=1):
        focus = missing_skills[idx - 1] if idx - 1 < len(missing_skills) else "Kiến thức nền tảng & kỹ năng cốt lõi"
        actions = milestone.get("actions", ["Đọc tài liệu chuyên ngành", "Thực hành bài tập đánh giá năng lực"])
        tasks.append(PersonalizedScheduleTask(
            week_number=idx,
            focus_skill=focus,
            tasks=[f"[Trọng tâm {focus}] {action}" for action in actions],
            recommended_reading=milestone.get("title", f"Chuyên đề học tập tuần {idx}"),
            estimated_hours=weekly_hours
        ))
    return tasks


async def call_llm_for_personalization(*args, **kwargs):
    """Retired: free-form provider prose cannot cross the guidance boundary."""
    raise RuntimeError("Use deterministic personalize_guidance with server-owned evidence")


async def personalize_guidance(
    db: AsyncSession,
    payload: GuidancePersonalizationRequest
) -> GuidancePersonalizationResponse:
    """Build a bounded study plan from the canonical roadmap and measured gap data.

    The request's ``missing_skills`` field is legacy display input and is deliberately
    ignored.  A client must not be able to manufacture a competency gap or inject
    instructions into a study plan; gaps come from the server-owned assessment and
    catalog records.
    """
    from app.services.gap_roadmap_engine.service import (
        get_cached_major_roadmap,
        get_student_major_skill_gaps,
    )

    from app.services.llamaindex_rag_orchestrator.guidance_boundary import plain
    roadmap = await get_cached_major_roadmap(db, payload.major_code)
    data = roadmap.roadmap_data.model_dump() if hasattr(roadmap.roadmap_data, "model_dump") else dict(roadmap.roadmap_data)
    milestones = data.get("milestones") or []
    source_title = str(data.get("source_title") or "nguồn chuẩn hóa của hệ thống")

    # Only names returned by the gap engine may become a personalized focus.
    try:
        gap = await get_student_major_skill_gaps(db, payload.user_id, payload.major_code)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Could not load measured skill gaps for %s: %s", payload.major_code, type(exc).__name__)
        raise HTTPException(503, "Chưa đọc được dữ liệu kỹ năng; vui lòng thử lại.") from exc

    focus_skills: List[str] = []
    for key in ("missing_prerequisites", "missing_target_skills"):
        for item in (gap.get(key) or []):
            if isinstance(item, dict):
                value = item.get("name") or item.get("skill_name") or item.get("title")
            else:
                value = item
            if isinstance(value, str) and value.strip() and value.strip() not in focus_skills:
                focus_skills.append(value.strip()[:120])
    # A generic server-owned label is preferable to claiming an unmeasured gap.
    if not focus_skills:
        focus_skills = ["Kiến thức nền tảng và kỹ năng cốt lõi của ngành"]

    # Each schedule entry is one week with the requested total weekly budget.
    weekly = max(2, min(int(payload.weekly_hours_available), 40))
    per_week = weekly
    schedule: List[PersonalizedScheduleTask] = []
    for idx, milestone in enumerate(milestones[:4], start=1):
        if not isinstance(milestone, dict):
            milestone = {}
        focus = focus_skills[(idx - 1) % len(focus_skills)]
        title = plain(milestone.get("title") or f"Chủ đề nền tảng tuần {idx}", 160)
        actions = milestone.get("actions") or milestone.get("learning_objectives") or []
        trusted_actions = [plain(x, 180) for x in actions if isinstance(x, str) and plain(x, 180)]
        if not trusted_actions:
            trusted_actions = ["Đọc nội dung nền tảng", "Làm bài tập nhỏ và tự đánh giá kết quả"]
        schedule.append(PersonalizedScheduleTask(
            week_number=idx,
            focus_skill=focus,
            tasks=trusted_actions[:3],
            recommended_reading=title,
            estimated_hours=per_week,
        ))
    if not schedule:
        schedule = build_fallback_personalized_schedule(
            payload.major_code, str(data.get("title") or payload.major_code), focus_skills, weekly, []
        )
        schedule = [task.model_copy(update={"estimated_hours": per_week}) for task in schedule[:4]]

    # Khi tài liệu có ít hơn bốn chủ đề, tuần còn lại dành cho ôn tập chủ đề
    # đã có; đây là quy tắc lập lịch, không tuyên bố thêm nội dung học thuật.
    while len(schedule) < 4:
        previous = schedule[-1]
        schedule.append(PersonalizedScheduleTask(
            week_number=len(schedule) + 1, focus_skill=previous.focus_skill,
            tasks=[f"Ôn lại nội dung: {previous.recommended_reading}", "Tự đánh giá phần đã học và ghi lại câu hỏi cần trao đổi với cố vấn."],
            recommended_reading=previous.recommended_reading, estimated_hours=weekly,
        ))

    major_title = str(getattr(roadmap, "title", None) or data.get("title") or f"ngành {payload.major_code}")
    status_text = gap.get("readiness_summary") if isinstance(gap, dict) else None
    status_text = plain(status_text, 260) if isinstance(status_text, str) else ""
    summary = (
        f"Lộ trình 4 tuần cho {major_title}, phân bổ tối đa {weekly} giờ mỗi tuần "
        f"theo dữ liệu khoảng trống kỹ năng đã ghi nhận."
    )
    if status_text:
        summary += f" Mức sẵn sàng tham khảo: {status_text}."
    if roadmap.is_fallback:
        summary += " Đây là mẫu khám phá cần đối chiếu với chương trình của trường; chưa phải cam kết đầu ra."
    else:
        summary += f" Nguồn lộ trình: {plain(source_title, 160)}."
    return GuidancePersonalizationResponse(
        major_code=payload.major_code,
        personalization_summary=summary[:4000],
        schedule=schedule,
        is_fallback=bool(roadmap.is_fallback),
    )


async def semantic_search_chunks(
    db: AsyncSession,
    request: SemanticSearchRequest
) -> List[ChunkSearchResult]:
    """
    Performs vector similarity search on knowledge_embeddings using pgvector.
    Supports metadata filtering by major_code and skill_id.
    """
    query_vector = await get_text_embedding(request.query, db=db)
    
    # Query pgvector using cosine distance
    query = select(
        KnowledgeEmbedding,
        KnowledgeEmbedding.embedding.cosine_distance(query_vector).label("distance")
    )
    
    if request.major_code:
        query = query.where(KnowledgeEmbedding.major_code == request.major_code)
    if request.skill_id:
        query = query.where(KnowledgeEmbedding.skill_id == request.skill_id)
        
    query = query.order_by("distance").limit(request.top_k)
    
    result = await db.execute(query)
    rows = result.all()
    
    search_results: List[ChunkSearchResult] = []
    for item, dist in rows:
        similarity = max(0.0, min(1.0, 1.0 - float(dist)))
        search_results.append(ChunkSearchResult(
            id=item.id,
            major_code=item.major_code,
            chunk_text=item.chunk_text,
            similarity_score=round(similarity, 4),
            source_title=item.source_title,
            source_url=item.source_url,
            source_page=item.source_page,
            metadata_payload=item.metadata_payload
        ))
        
    return search_results


# =========================================================================
# AI EXPLANATION ENGINE (ANONYMIZED ACADEMIC PROFILE ONLY - LAW 91/2025)
# =========================================================================

async def explain_recommendation_with_ai(db, payload: AIExplanationRequest, current_user_id=None) -> AIExplanationResponse:
    """Generate an intelligent personalized explanation grounded by 3-pillar data with multi-tier caching and token optimization."""
    import hashlib
    import json
    from app.services.llamaindex_rag_orchestrator.guidance_boundary import guidance_facts, personal_facts, describe
    from app.models.insight import MajorExplanationInsight

    facts = await guidance_facts(db, payload, current_user_id)
    item = facts["items"].get(payload.major_code)
    if item is None:
        raise HTTPException(404, "Ngành không có trong danh mục đang hoạt động.")
    detail = personal_facts(payload.major_code, facts)

    profile = facts.get("profile") or {}
    canonical_profile = {
        "owner": str(current_user_id or "guest"),
        "riasec_scores": profile.get("riasec_scores") or {},
        "grades": profile.get("grades_by_subject") or {},
        "cognitive": profile.get("cognitive_preferences") or {},
        "aspiration": profile.get("aspiration") or {},
    }
    profile_hash = hashlib.sha256(
        json.dumps(canonical_profile, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()

    # 1. Check DB Cache first: 0 tokens, sub-millisecond response
    if db is not None:
        try:
            cached_exp = (
                await db.execute(
                    select(MajorExplanationInsight).where(
                        MajorExplanationInsight.profile_hash == profile_hash,
                        MajorExplanationInsight.major_code == payload.major_code,
                    )
                )
            ).scalar_one_or_none()
            if cached_exp and cached_exp.is_ai_generated:
                return AIExplanationResponse(
                    major_code=cached_exp.major_code,
                    major_name=cached_exp.major_name,
                    detailed_explanation=cached_exp.detailed_explanation,
                    riasec_alignment=cached_exp.riasec_alignment or detail["riasec"],
                    academic_alignment=cached_exp.academic_alignment or detail["academic"],
                    diagnostic_readiness=cached_exp.diagnostic_readiness or detail["diagnostic"],
                    strengths=cached_exp.strengths or detail["observed"],
                    recommended_focus_areas=cached_exp.recommended_focus_areas or detail["focus"],
                    is_ai_generated=True,
                )
        except Exception as exc:
            logger.warning("[AIExplanation] Cache read failed: %s", exc)

    static_explanation = "\n\n".join([describe(item.major_code, facts), detail["riasec"], detail["academic"], detail["cognitive"], detail["diagnostic"]])
    final_explanation = static_explanation
    is_ai = False
    snapshot = None

    if db is not None:
        try:
            from app.services.ai_config.service import resolve_snapshot
            from app.services.ai_config import adapter

            snapshot = await resolve_snapshot(db)

            # Token Optimization: Extract concise signals instead of verbose boilerplate strings
            riasec_score_pct = f"{getattr(item, 'score_riasec', 0) * 100:.0f}%"
            academic_score_pct = f"{getattr(item, 'score_academic', 0) * 100:.0f}%"
            match_score_str = f"{getattr(item, 'match_score', 0):.0f}/100"
            grades_dict = profile.get("grades_by_subject") or {}
            top_grades = ", ".join(f"{sub}: {gr}" for sub, gr in list(grades_dict.items())[:4]) or "Chưa nhập điểm cụ thể"

            system_prompt = (
                "Bạn là Chuyên gia Cố vấn Hướng nghiệp AI CareerGuide.\n"
                f"Nhiệm vụ: Phân tích ngắn gọn vì sao ngành **{item.major_name} ({item.major_code})** phù hợp với học sinh.\n\n"
                "Thông số hồ sơ đối chiếu:\n"
                f"- Khối ngành: {item.category}\n"
                f"- Điểm khớp sở thích RIASEC: {riasec_score_pct}\n"
                f"- Điểm khớp học lực: {academic_score_pct} (Các môn: {top_grades})\n"
                f"- Điểm gợi ý tổng thể: {match_score_str}\n\n"
                "Quy tắc tối ưu:\n"
                "1. Trả lời súc tích trong 2-3 đoạn ngắn (tối đa 180-220 từ).\n"
                "2. Nêu bật thế mạnh, lý do thực tế ngành phù hợp và môn/kỹ năng cần phát huy.\n"
                "3. Viết tự nhiên, truyền cảm hứng, không dùng câu rập khuôn, không bịa điểm chuẩn hay hứa hẹn đỗ."
            )
            ai_text = await adapter.chat(
                snapshot,
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Giải thích ngắn gọn lý do ngành {item.major_name} ({item.major_code}) phù hợp với hồ sơ của tôi."}
                ],
                max_tokens=min(settings.LLM_MAX_TOKENS, 450),
                timeout=min(settings.LLM_TIMEOUT_SECONDS, 45.0),
            )
            if ai_text and ai_text.strip():
                final_explanation = ai_text.strip()
                is_ai = True
        except Exception as exc:
            logger.warning("AI explanation synthesis failed, falling back to static facts: %s", exc)

    # Persist into DB cache for 0 token reuse
    if db is not None:
        try:
            stmt = select(MajorExplanationInsight).where(
                MajorExplanationInsight.profile_hash == profile_hash,
                MajorExplanationInsight.major_code == payload.major_code,
            )
            existing = (await db.execute(stmt)).scalar_one_or_none()
            model_ident = getattr(snapshot, "model", None) if is_ai and snapshot else "deterministic-fallback"
            save_payload = {
                "user_id": current_user_id,
                "profile_hash": profile_hash,
                "major_code": payload.major_code,
                "major_name": item.major_name,
                "detailed_explanation": final_explanation,
                "riasec_alignment": detail["riasec"],
                "academic_alignment": detail["academic"],
                "diagnostic_readiness": detail["diagnostic"],
                "strengths": detail["observed"],
                "recommended_focus_areas": detail["focus"],
                "is_ai_generated": is_ai,
                "model_name": model_ident,
            }
            if existing:
                for k, v in save_payload.items():
                    setattr(existing, k, v)
            else:
                db.add(MajorExplanationInsight(id=uuid.uuid4(), **save_payload))
            await db.commit()
        except Exception as exc:
            logger.warning("[AIExplanation] Persist cache failed: %s", exc)
            try:
                await db.rollback()
            except Exception:
                pass

    return AIExplanationResponse(
        major_code=item.major_code, major_name=item.major_name,
        detailed_explanation=final_explanation,
        riasec_alignment=detail["riasec"], academic_alignment=detail["academic"],
        diagnostic_readiness=detail["diagnostic"], strengths=detail["observed"],
        recommended_focus_areas=detail["focus"], is_ai_generated=is_ai,
    )


async def chat_with_career_counselor(db, payload: AIChatRequest, current_user_id=None) -> AIChatResponse:
    """Combines authoritative catalog facts with conversational LLM generation."""
    from app.services.llamaindex_rag_orchestrator.guidance_boundary import (
        guidance_facts, render_chat, forbidden_request, resolve_profile_owner, REDIRECT,
    )
    from app.services.llamaindex_rag_orchestrator.counselor_connection import verify_receipt
    from app.services.llamaindex_rag_orchestrator.chat_scope import (
        classify_chat_message, local_scope_reply, is_academic_question,
    )
    from app.services.ai_config.service import resolve_snapshot
    from app.services.ai_config import adapter

    resolve_profile_owner(payload.user_id, current_user_id)
    if payload.assessment_id and current_user_id is None:
        raise HTTPException(401, "Đăng nhập để xem bản đánh giá đã lưu.")

    connected = await verify_receipt(db, payload.connection_revision)
    scope = "redirect" if forbidden_request(payload.message) else classify_chat_message(payload.message, payload.history)
    if scope != "allow":
        return AIChatResponse(
            reply=REDIRECT if scope == "redirect" else local_scope_reply(scope),
            suggested_followups=["Tìm hiểu ngành An toàn thông tin", "Cần bổ sung gì vào hồ sơ hướng nghiệp?"],
            is_fallback=False,
            is_ai_generated=False,
            response_source="verified_guidance",
            connection_available=connected,
            connection_revision=payload.connection_revision if connected else None,
        )

    academic = is_academic_question(payload.message, payload.history)
    if academic:
        # Tutoring does not require a catalog match or a private student profile.
        static_reply = "Đây là câu hỏi học tập phù hợp. Hiện chưa nhận được lời giải từ AI; bạn có thể kiểm tra kết nối rồi gửi lại câu hỏi."
        context = payload.major_code
        followups = ["Cho mình một ví dụ dễ hiểu", "Giải thích từng bước"]
    else:
        facts = await guidance_facts(db, payload, current_user_id)
        static_reply, context, followups = render_chat(payload, facts)
    connected = await verify_receipt(db, payload.connection_revision)

    generation_failed = False
    if connected and static_reply != REDIRECT:
        try:
            snapshot = await resolve_snapshot(db)
            system_instruction = (
                "Bạn là Cố vấn AI Hướng nghiệp thông minh, thân thiện và tận tâm của hệ thống AI CareerGuide.\n"
                "Nhiệm vụ: Tư vấn, giải đáp câu hỏi của học sinh/sinh viên về định hướng nghề nghiệp, các ngành học, "
                "mức độ phù hợp với sở thích/năng lực, học tập, và mục tiêu tương lai.\n\n"
                "Quy tắc phản hồi:\n"
                "1. Trả lời bằng tiếng Việt tự nhiên, nhiệt tình, súc tích, mạch lạc, giọng điệu khuyến khích và truyền cảm hứng.\n"
                "2. Sử dụng thông tin từ [DỮ LIỆU THAM CHIẾU HỆ THỐNG] dưới đây làm căn cứ chuẩn xác "
                "(về tên ngành, mã ngành, chuẩn đầu ra, điểm tham chiếu tuyển sinh, kết quả sở thích Holland nếu có). "
                "Tuyệt đối KHÔNG tự bịa đặt thông tin tuyển sinh sai lệch.\n"
                "3. Trả lời trực tiếp vào trọng tâm câu hỏi của người dùng (ví dụ: giải thích ngắn gọn bản chất ngành nghề, so sánh các ngành liên quan, hoặc hướng dẫn lộ trình), "
                "tránh lặp lại nguyên văn tiêu đề kỹ thuật hay khuôn mẫu khô cứng của hệ thống.\n"
                "4. Định dạng Markdown rõ ràng (dùng gạch đầu dòng, in đậm tên ngành hoặc từ khóa quan trọng) để học sinh dễ đọc."
            )

            if academic:
                system_instruction = (
                    "Bạn là trợ giảng học tập trong AI CareerGuide, hỗ trợ kiến thức phổ thông và lập trình.\n"
                    "Trả lời trực tiếp câu hỏi hiện tại bằng tiếng Việt, rõ ràng, ngắn gọn và đúng trình độ câu hỏi.\n"
                    "Với phép tính hoặc biểu thức ngắn, hãy giải hoặc tính kết quả; không bắt buộc người dùng phải nói từ 'học'.\n"
                    "Với khái niệm, nêu định nghĩa dễ hiểu và một ví dụ. Với bài tập, trình bày các bước chính. "
                    "Với lập trình, cung cấp mã đúng ngôn ngữ yêu cầu và giải thích ngắn; nếu thiếu dữ kiện, nêu giả định hoặc hỏi lại cụ thể.\n"
                    "Không chuyển câu hỏi học tập sang tư vấn chọn ngành, không yêu cầu chọn ngành và không lặp lại "
                    "các lần từ chối nhầm trước đó. Không suy ra năng lực hay mức phù hợp nghề từ một câu hỏi kiến thức.\n"
                    "Không bịa dữ kiện thời sự, nguồn tài liệu hoặc thông tin chưa được cung cấp."
                )
            else:
                system_instruction += f"\n\n[DỮ LIỆU THAM CHIẾU HỆ THỐNG]:\n{static_reply}"
            messages = [{"role": "system", "content": system_instruction}]

            if payload.history:
                related_history = []
                last_user_allowed = False
                for entry in payload.history[-6:]:
                    if entry.role == "user":
                        last_user_allowed = (not forbidden_request(entry.content) and
                                             classify_chat_message(entry.content, related_history) == "allow" and
                                             (not academic or is_academic_question(entry.content, related_history)))
                    if not last_user_allowed:
                        continue
                    if entry.content and entry.role in {"user", "assistant"}:
                        clean_content = sanitize_pii(entry.content)
                        if clean_content.strip():
                            messages.append({"role": entry.role, "content": clean_content[:1500]})
                            related_history.append(entry)

            user_msg = sanitize_pii(payload.message).strip()
            messages.append({"role": "user", "content": user_msg})

            ai_reply = await adapter.chat(
                snapshot,
                messages,
                max_tokens=min(settings.LLM_MAX_TOKENS, 2048),
                timeout=min(settings.LLM_TIMEOUT_SECONDS, 60.0),
            )

            if ai_reply and ai_reply.strip():
                connected_after = await verify_receipt(db, payload.connection_revision)
                return AIChatResponse(
                    reply=ai_reply.strip(),
                    suggested_followups=followups,
                    context_major_code=context,
                    is_fallback=False,
                    is_ai_generated=True,
                    response_source="ai_advisor",
                    connection_available=connected_after,
                    connection_revision=payload.connection_revision if connected_after else None,
                )
        except Exception as exc:
            logger.warning("LLM synthesis failed in career chat, falling back to static guidance: %s", exc)
            generation_failed = True
            connected = False

    return AIChatResponse(
        reply=static_reply,
        suggested_followups=followups,
        context_major_code=context,
        is_fallback=generation_failed,
        is_ai_generated=False,
        response_source="offline_guidance" if generation_failed else "verified_guidance",
        connection_available=connected,
        connection_revision=payload.connection_revision if connected else None,
    )


async def get_llm_status(db):
    """Compatibility facade: cùng nguồn DB với Admin, không đọc settings ghép trường."""
    from app.services.ai_config.service import get_status
    return await get_status(db)


async def test_llm_connection(payload, db, actor_id):
    from app.services.ai_config.service import probe_draft
    return await probe_draft(db,payload,actor_id)


async def update_llm_config(payload, db, actor_id):
    from app.services.ai_config.service import apply_config
    return await apply_config(db,payload,actor_id)
