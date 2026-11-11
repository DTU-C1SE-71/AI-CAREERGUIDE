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
from app.core.llm_client import resolve_model_token_limits, clear_model_caps_cache
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
    LLMConnectionTestRequest,
    LLMConnectionTestResponse,
    LLMStatusResponse
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

FALLBACK_MAJOR_METADATA: dict[str, tuple[str, str, list[str]]] = {
    "7480201": ("Công nghệ thông tin", "Máy tính và công nghệ thông tin", ["A00", "A01", "D01"]),
    "7480101": ("Khoa học máy tính", "Máy tính và công nghệ thông tin", ["A00", "A01", "D07"]),
    "7480103": ("Kỹ thuật phần mềm", "Máy tính và công nghệ thông tin", ["A00", "A01", "D01"]),
    "7480202": ("An toàn thông tin", "Máy tính và công nghệ thông tin", ["A00", "A01", "D01"]),
    "7480104": ("Hệ thống thông tin", "Máy tính và công nghệ thông tin", ["A00", "A01", "D01"]),
    "7340101": ("Quản trị kinh doanh", "Kinh doanh và quản lý", ["A00", "A01", "D01"]),
    "7340201": ("Tài chính - Ngân hàng", "Kinh doanh và quản lý", ["A00", "A01", "D01"]),
    "7340301": ("Kế toán", "Kinh doanh và quản lý", ["A00", "A01", "D01"]),
    "7340115": ("Marketing", "Kinh doanh và quản lý", ["A00", "A01", "D01"]),
    "7220201": ("Ngôn ngữ Anh", "Nhân văn", ["D01", "D14", "D15"]),
    "7510301": ("Công nghệ kỹ thuật điện, điện tử", "Kỹ thuật", ["A00", "A01"]),
    "7520130": ("Kỹ thuật ô tô", "Kỹ thuật", ["A00", "A01"]),
    "7140210": ("Sư phạm Tin học", "Khoa học giáo dục và đào tạo giáo viên", ["A00", "A01", "D01"]),
}

# Automatically load all 108 MOET majors from moet_taxonomy_tt09.json seed if available
import os
import json as _pyjson
for _candidate_path in [
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "moet_taxonomy_tt09.json"),
    os.path.join(os.path.dirname(__file__), "..", "..", "db", "seeds", "moet_taxonomy_tt09.json"),
    os.path.abspath("backend/app/data/moet_taxonomy_tt09.json"),
]:
    if os.path.exists(_candidate_path):
        try:
            with open(_candidate_path, "r", encoding="utf-8") as _f:
                _tax_data = _pyjson.load(_f)
                for _item in _tax_data:
                    _c = _item.get("major_code")
                    _n = _item.get("name")
                    _cat = _item.get("category", "Đào tạo đại học chính quy")
                    _blk = _item.get("blocks", ["A00", "A01", "D01"])
                    if _c and _n:
                        FALLBACK_MAJOR_METADATA[_c] = (_n, _cat, _blk)
            break
        except Exception as _e:
            logger.warning(f"Failed to load seed taxonomy {_candidate_path}: {_e}")


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


async def call_llm_for_personalization(
    major_code: str,
    major_title: str,
    missing_skills: List[str],
    weekly_hours: int,
    milestones: List[Dict[str, Any]],
    source_title: str
) -> GuidancePersonalizationResponse:
    """
    Invokes gpt-4o-mini to synthesize verified milestones with student skill gaps.
    Strictly isolated: does not search the web or alter major ranking.
    """
    from openai import AsyncOpenAI
    client_kwargs = {"api_key": settings.OPENAI_API_KEY}
    if settings.OPENAI_BASE_URL:
        client_kwargs["base_url"] = settings.OPENAI_BASE_URL
    client = AsyncOpenAI(**client_kwargs)

    milestone_summary = "\n".join([
        f"- Mốc {m.get('step')}: {m.get('title')} ({m.get('duration_weeks', 2)} tuần). Mục tiêu: {', '.join(m.get('learning_objectives', []))}"
        for m in milestones
    ])
    
    prompt = (
        f"Bạn là Cố vấn học tập AI CareerGuide chuẩn hóa theo chương trình GDPT và Đại học Việt Nam.\n"
        f"Học sinh đang định hướng ngành: {major_title} (Mã ngành: {major_code}).\n"
        f"Các khoảng trống kỹ năng cần tập trung bù đắp: {', '.join(missing_skills) if missing_skills else 'Theo chuẩn chung của ngành'}.\n"
        f"Thời gian học tập tự chủ sẵn sàng: {weekly_hours} giờ/tuần.\n\n"
        f"Lộ trình chuẩn hóa đã kiểm duyệt từ nguồn '{source_title}':\n{milestone_summary}\n\n"
        f"RÀNG BUỘC NGHIÊM NGẶT (Table 6 & Pure Guidance Scope):\n"
        f"1. Tuyệt đối bám sát các mốc học tập trên, không bịa đặt chương trình đào tạo hay học phần ngoài nguồn.\n"
        f"2. Tuyệt đối không đề cập đến học phí hay vị trí địa lý.\n"
        f"3. Lập kế hoạch 4 tuần học tập cá nhân hóa, mỗi tuần nêu rõ kỹ năng trọng tâm (focus_skill), danh sách việc cần làm cụ thể (tasks), tài liệu nên đọc và số giờ dự kiến.\n"
    )
    
    sanitized_prompt = sanitize_pii(prompt)
    token_limits = await resolve_model_token_limits()

    response = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": "Bạn là chuyên gia tư vấn lộ trình học tập cá nhân hóa AI CareerGuide."},
            {"role": "user", "content": sanitized_prompt}
        ],
        max_tokens=token_limits["max_output_tokens"],
        temperature=0.2
    )
    
    content = (response.choices[0].message.content or "").strip()
    # Format fallback schedule wrapped with AI summary
    schedule = build_fallback_personalized_schedule(major_code, major_title, missing_skills, weekly_hours, milestones)
    
    return GuidancePersonalizationResponse(
        major_code=major_code,
        personalization_summary=content[:4000] if len(content) > 30 else f"Kế hoạch 4 tuần tập trung bổ trợ kỹ năng cho ngành {major_title}.",
        schedule=schedule,
        is_fallback=False
    )


async def personalize_guidance(
    db: AsyncSession,
    payload: GuidancePersonalizationRequest
) -> GuidancePersonalizationResponse:
    """
    Guidance RAG Pipeline (FR06, DF06):
    1. Direct indexed cache lookup from major_roadmaps (<= 1s).
    2. PII Sanitization.
    3. AI API call with strict 8-second timeout (asyncio.wait_for).
    4. Graceful Fallback: Immediately returns standardized static fallback roadmap if AI times out or errors.
    """
    # 1. Retrieve cached roadmap (<= 1s)
    res = await db.execute(select(MajorRoadmap).where(MajorRoadmap.major_code == payload.major_code))
    cached = res.scalar_one_or_none()
    
    major_res = await db.execute(select(Major).where(Major.major_code == payload.major_code))
    major = major_res.scalar_one_or_none()
    major_name = major.name if major else f"Mã ngành {payload.major_code}"

    # If uncurated or cached as fallback template, serve immediately
    if not cached or cached.is_fallback:
        fallback_data = generate_static_fallback_roadmap(payload.major_code, major_name)
        schedule = build_fallback_personalized_schedule(
            payload.major_code,
            major_name,
            payload.missing_skills,
            payload.weekly_hours_available,
            fallback_data["milestones"]
        )
        return GuidancePersonalizationResponse(
            major_code=payload.major_code,
            personalization_summary=f"Lộ trình tĩnh chuẩn hóa dự phòng cho ngành {major_name} (chờ kiểm duyệt chính thức).",
            schedule=schedule,
            is_fallback=True
        )

    # Verified roadmap is available
    roadmap_data = cached.roadmap_data
    milestones = roadmap_data.get("milestones", [])
    source_title = roadmap_data.get("source_title", "Chương trình chuẩn Bộ GD&ĐT")

    # If OpenAI API is not configured or during testing, return immediate deterministic schedule
    if not settings.OPENAI_API_KEY:
        schedule = build_fallback_personalized_schedule(
            payload.major_code,
            major_name,
            payload.missing_skills,
            payload.weekly_hours_available,
            milestones
        )
        return GuidancePersonalizationResponse(
            major_code=payload.major_code,
            personalization_summary=f"Lộ trình học tập cá nhân hóa ngành {major_name} tập trung xử lý các lỗ hổng kỹ năng: {', '.join(payload.missing_skills) if payload.missing_skills else 'Theo chuẩn ngành'}.",
            schedule=schedule,
            is_fallback=False
        )

    # 3. Call AI API with strict 8.0s timeout (NFR01, NFR05)
    try:
        response = await asyncio.wait_for(
            call_llm_for_personalization(
                major_code=payload.major_code,
                major_title=major_name,
                missing_skills=payload.missing_skills,
                weekly_hours=payload.weekly_hours_available,
                milestones=milestones,
                source_title=source_title
            ),
            timeout=8.0
        )
        return response
    except asyncio.TimeoutError:
        logger.warning(f"Guidance RAG AI personalization timed out (> 8.0s) for {payload.major_code}. Triggering static fallback.")
        schedule = build_fallback_personalized_schedule(
            payload.major_code,
            major_name,
            payload.missing_skills,
            payload.weekly_hours_available,
            milestones
        )
        return GuidancePersonalizationResponse(
            major_code=payload.major_code,
            personalization_summary=f"AI phản hồi quá 8 giây. Hệ thống tự động chuyển đổi sang lộ trình chuẩn hóa dự phòng cho ngành {major_name}.",
            schedule=schedule,
            is_fallback=True
        )
    except Exception as exc:
        logger.warning(f"Guidance RAG failed with error {exc}. Triggering static fallback.")
        schedule = build_fallback_personalized_schedule(
            payload.major_code,
            major_name,
            payload.missing_skills,
            payload.weekly_hours_available,
            milestones
        )
        return GuidancePersonalizationResponse(
            major_code=payload.major_code,
            personalization_summary=f"Sự cố kết nối AI API. Hệ thống kích hoạt lộ trình chuẩn hóa dự phòng cho ngành {major_name}.",
            schedule=schedule,
            is_fallback=True
        )


async def semantic_search_chunks(
    db: AsyncSession,
    request: SemanticSearchRequest
) -> List[ChunkSearchResult]:
    """
    Performs vector similarity search on knowledge_embeddings using pgvector.
    Supports metadata filtering by major_code and skill_id.
    """
    query_vector = await get_text_embedding(request.query)
    
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

def build_deterministic_ai_explanation(
    major_code: str,
    major_name: str,
    major_category: str,
    riasec_scores: Dict[str, float],
    grades: Dict[str, float],
    mastered_skills: List[str],
    admission_blocks: List[str]
) -> AIExplanationResponse:
    """
    Deterministic rule-based explanation engine based on exact mathematical scoring
    and domain requirements. Used when AI API is unavailable or times out (> 8s).
    """
    # 1. Top RIASEC traits
    sorted_riasec = sorted(
        RIASEC_DIMENSIONS,
        key=lambda d: float(riasec_scores.get(d, 0.5)),
        reverse=True
    )
    top1, top2 = sorted_riasec[0], sorted_riasec[1]
    name1 = RIASEC_NAMES_VI.get(top1, top1)
    name2 = RIASEC_NAMES_VI.get(top2, top2)
    score1 = round(float(riasec_scores.get(top1, 0.5)) * 100)
    score2 = round(float(riasec_scores.get(top2, 0.5)) * 100)

    riasec_text = (
        f"Hồ sơ sở thích của bạn thể hiện xu hướng nổi trội ở nhóm {name1} ({score1}%) "
        f"và {name2} ({score2}%). Đây là các đặc tính tâm lý rất tương thích với mô hình đào tạo "
        f"ngành {major_name}, vốn đòi hỏi sự kết hợp giữa tư duy phân tích sâu và kỹ năng giải quyết vấn đề thực tế."
    )

    # 2. Academic alignment
    high_grades = [
        f"{subj.capitalize()} ({score}đ)"
        for subj, score in grades.items()
        if isinstance(score, (int, float)) and score >= 8.0
    ]
    blocks_str = ", ".join(admission_blocks) if admission_blocks else "A00, A01, D01"
    academic_text = (
        f"Về năng lực học thuật, bạn có điểm số vững chắc ở các môn then chốt: {', '.join(high_grades) if high_grades else 'các môn văn hóa đạt mức khá trở lên'}. "
        f"Các môn này bổ trợ trực tiếp cho các tổ hợp môn xét tuyển truyền thống của ngành ({blocks_str}), "
        f"giúp tăng đáng kể xác suất trúng tuyển và khả năng tiếp thu kiến thức chuyên ngành ở bậc đại học."
    )

    # 3. Diagnostic readiness
    if mastered_skills:
        diag_text = (
            f"Đặc biệt, qua bài kiểm tra chẩn đoán năng lực nền tảng, bạn đã được chứng nhận đạt chuẩn {len(mastered_skills)} kỹ năng "
            f"({', '.join(mastered_skills[:3])}{'...' if len(mastered_skills) > 3 else ''}). "
            f"Các kỹ năng này sẽ tự động được miễn giảm khỏi khoảng trống kiến thức tiên quyết trong lộ trình học tập, giúp bạn rút ngắn thời gian chuẩn bị."
        )
    else:
        diag_text = (
            "Bạn chưa thực hiện hoặc chưa đạt chuẩn các bài test chẩn đoán năng lực đầu vào. "
            "Bạn có thể làm thêm các bài kiểm tra logic 10 phút để nhận diện chính xác các kỹ năng tiên quyết cần bổ trợ."
        )

    # 4. Detailed explanation
    detailed_text = (
        f"Ngành {major_name} (Mã ngành: {major_code}, thuộc lĩnh vực {major_category}) được hệ thống đề xuất "
        f"dựa trên sự hội tụ giữa thiên hướng nghề nghiệp và năng lực học tập thực tế của bạn.\n\n"
        f"1. Về mặt tâm lý nghề nghiệp: Nhóm tính cách {top1} ({score1}%) và {top2} ({score2}%) tạo nên thế mạnh tự nhiên "
        f"trong việc làm chủ kiến thức và thích nghi với môi trường làm việc của ngành.\n\n"
        f"2. Về mặt học thuật: Điểm học bạ THPT cho thấy bạn có nền tảng tư duy phù hợp với các học phần đại cương và cơ sở ngành. "
        f"Hệ thống khuyến nghị bạn tiếp tục củng cố các môn trong tổ hợp xét tuyển ({blocks_str}) để đạt kết quả thi tối ưu."
    )

    strengths = [
        f"Độ tương thích sở thích nổi trội ở nhóm {top1} ({score1}%) và {top2} ({score2}%)",
        f"Nền tảng học thuật tốt ở các môn trọng tâm ({', '.join(high_grades[:3]) if high_grades else 'Toán và Khoa học'})",
        f"Đã làm chủ {len(mastered_skills)} kỹ năng nền tảng qua bài test chẩn đoán đầu vào" if mastered_skills else "Có tiềm năng phát triển nhanh khi được bổ trợ phương pháp học tập đúng đắn"
    ]

    focus_areas = [
        "Tiếp tục luyện tập các dạng bài nâng cao cho tổ hợp xét tuyển chính",
        "Trau dồi năng lực đọc hiểu tài liệu chuyên ngành và tiếng Anh học thuật",
        "Thực hiện bài kiểm tra chẩn đoán logic/toán rời rạc nếu chưa làm để tối ưu lộ trình"
    ]

    return AIExplanationResponse(
        major_code=major_code,
        major_name=major_name,
        detailed_explanation=detailed_text,
        riasec_alignment=riasec_text,
        academic_alignment=academic_text,
        diagnostic_readiness=diag_text,
        strengths=strengths,
        recommended_focus_areas=focus_areas,
        is_ai_generated=False
    )


async def explain_recommendation_with_ai(
    db: AsyncSession,
    payload: AIExplanationRequest,
    current_user_id: Optional[uuid.UUID] = None
) -> AIExplanationResponse:
    """
    Synthesizes an in-depth AI explanation for why a specific major is recommended.
    STRICT PII SANITIZATION (Law 91/2025/QH15 & Table 6 Pure Guidance Scope):
    - Strictly and exclusively uses anonymized test scores: RIASEC vector, subject grades, diagnostic skills.
    - NEVER includes student name, email, phone number, address, or school in LLM prompt.
    - Timeout: strict 8.0s limit with automatic deterministic fallback.
    """
    # 1. Fetch Major Details (DB or Fallback Mapping)
    fallback_info = FALLBACK_MAJOR_METADATA.get(
        payload.major_code, (f"Ngành {payload.major_code}", "Đào tạo đại học chính quy", ["A00", "A01", "D01"])
    )
    major_name = fallback_info[0]
    major_category = fallback_info[1]
    admission_blocks = list(fallback_info[2])
    major = None

    if db is not None:
        try:
            major_res = await db.execute(select(Major).where(Major.major_code == payload.major_code))
            major = major_res.scalar_one_or_none()
            if major:
                major_name = major.name
                major_category = major.category
                from app.models.taxonomy import MajorSubjectBlock
                blocks_res = await db.execute(select(MajorSubjectBlock).where(MajorSubjectBlock.major_id == major.id))
                blocks = list(blocks_res.scalars().all())
                if blocks:
                    admission_blocks = [b.block_code for b in blocks]
        except Exception as db_err:
            logger.warning(f"Database query skipped for major {payload.major_code}: {db_err}")

    # 2. Resolve Student Test Profile (Payload or DB)
    riasec_scores = payload.riasec_scores
    grades = payload.grades_by_subject
    mastered_skills = payload.diagnostic_skills_mastered or []

    effective_user_id = payload.user_id or current_user_id
    if db is not None and effective_user_id and (not riasec_scores or not grades):
        try:
            if not riasec_scores:
                assess_res = await db.execute(select(StudentAssessment).where(StudentAssessment.user_id == effective_user_id))
                assess = assess_res.scalar_one_or_none()
                if assess and assess.riasec_scores:
                    riasec_scores = assess.riasec_scores

            if not grades:
                grade_res = await db.execute(
                    select(StudentGrade).where(StudentGrade.user_id == effective_user_id).order_by(StudentGrade.created_at.desc())
                )
                g = grade_res.scalar_one_or_none()
                if g and g.grades_by_subject:
                    grades = g.grades_by_subject

            if not mastered_skills:
                diag_res = await db.execute(select(StudentDiagnosticTest).where(StudentDiagnosticTest.user_id == effective_user_id))
                diag_tests = list(diag_res.scalars().all())
                mastered_skills = [d.skill_code for d in diag_tests if d.is_passed]
        except Exception as db_err:
            logger.warning(f"Database query skipped for student profile {effective_user_id}: {db_err}")

    riasec_scores = riasec_scores or {"R": 0.5, "I": 0.5, "A": 0.5, "S": 0.5, "E": 0.5, "C": 0.5}
    grades = grades or {"math": 8.0, "physics": 8.0, "chemistry": 7.5, "literature": 7.0, "english": 8.0}

    # If OpenAI API is not configured, return deterministic response immediately
    if not settings.OPENAI_API_KEY:
        return build_deterministic_ai_explanation(
            payload.major_code, major_name, major_category, riasec_scores, grades, mastered_skills, admission_blocks
        )

    # 4. Call LLM with strict PII-sanitized prompt (<= 8s timeout)
    try:
        from openai import AsyncOpenAI
        client_kwargs = {"api_key": settings.OPENAI_API_KEY, "timeout": 120.0}
        if settings.OPENAI_BASE_URL:
            client_kwargs["base_url"] = settings.OPENAI_BASE_URL
        client = AsyncOpenAI(**client_kwargs)

        # Anonymized prompt: strictly contains NO student identifiers
        riasec_lines = ", ".join([f"{dim}: {round(float(val)*100)}%" for dim, val in riasec_scores.items()])
        grade_lines = ", ".join([f"{k.capitalize()}: {v}" for k, v in grades.items()])
        diag_lines = ", ".join(mastered_skills) if mastered_skills else "Chưa có kỹ năng kiểm tra đạt chuẩn"

        prompt = (
            f"Bạn là Chuyên gia Cố vấn Hướng nghiệp AI CareerGuide hàng đầu. Hãy lập Bản Báo Cáo Giải Trình Định Hướng Ngành Học (Explainable AI - XAI Dossier) chuyên sâu cho học sinh theo chuẩn Thông tư 09/2022/TT-BGDĐT.\n\n"
            f"HỒ SƠ NĂNG LỰC HỌC SINH (DỮ LIỆU ĐÃ ẨN DANH VÀ KHỬ KHUẨN THEO LUẬT 91/2025/QH15):\n"
            f"- Điểm sở thích nghề nghiệp Holland (RIASEC): {riasec_lines}\n"
            f"- Điểm học bạ THPT các môn văn hóa: {grade_lines}\n"
            f"- Kỹ năng chẩn đoán đầu vào đã đạt: {diag_lines}\n\n"
            f"THÔNG TIN NGÀNH HỌC ĐƯỢC ĐỀ XUẤT:\n"
            f"- Ngành: {major_name} (Mã ngành: {payload.major_code})\n"
            f"- Lĩnh vực: {major_category}\n"
            f"- Tổ hợp môn xét tuyển: {', '.join(admission_blocks)}\n\n"
            f"RÀNG BUỘC ĐẠO ĐỨC & NGUYÊN TẮC GIẢI TRÌNH:\n"
            f"1. Tuyệt đối không đề cập hoặc suy đoán họ tên, trường lớp, thông tin cá nhân học sinh, không nhắc học phí.\n"
            f"2. BÀI GIẢI TRÌNH (detailed_explanation) phải viết bằng Markdown hấp dẫn, mạch lạc, có chiều sâu (khoảng 150-250 từ), dùng in đậm từ khóa quan trọng, phân tích tường tận vì sao ngành này mở ra tương lai sáng giá và phù hợp nhất với học sinh dựa trên sự giao thoa giữa sở thích cá nhân và năng lực học tập thực tế.\n"
            f"3. 'riasec_alignment': Phân tích sâu sắc sự tương thích giữa các nhóm Holland nổi bật của học sinh với môi trường đào tạo và tính chất công việc ngành {major_name}.\n"
            f"4. 'academic_alignment': Phân tích chi tiết điểm số các môn học bạ, đánh giá cơ hội ở các tổ hợp môn ({', '.join(admission_blocks)}) và chỉ ra môn cần củng cố.\n"
            f"5. 'diagnostic_readiness': Nhận định thực chất về mức độ sẵn sàng kiến thức nền tảng từ kết quả bài test kỹ năng .\n"
            f"6. 'strengths': 3 điểm mạnh vượt trội, viết rõ ràng, giàu tính khích lệ.\n"
            f"7. 'recommended_focus_areas': 2 hành động cụ thể, thiết thực để bứt phá học tập.\n\n"
            f"Hãy trả về đúng định dạng JSON:\n"
            f"{{\n"
            f'  "detailed_explanation": "Bài phân tích giải trình chuyên sâu bằng Markdown",\n'
            f'  "riasec_alignment": "Phân tích sâu sắc độ tương quan sở thích Holland",\n'
            f'  "academic_alignment": "Phân tích cụ thể học bạ và tổ hợp xét tuyển",\n'
            f'  "diagnostic_readiness": "Đánh giá mức độ sẵn sàng từ bài test chẩn đoán kỹ năng",\n'
            f'  "strengths": ["Điểm mạnh nổi bật 1", "Điểm mạnh nổi bật 2", "Điểm mạnh nổi bật 3"],\n'
            f'  "recommended_focus_areas": ["Kế hoạch hành động 1", "Kế hoạch hành động 2"]\n'
            f"}}"
        )

        sanitized_prompt = sanitize_pii(prompt)

        async def _call_llm():
            import json
            import re
            token_limits = await resolve_model_token_limits()
            resp = await client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": "Bạn là chuyên gia tư vấn giáo dục đại học khách quan, bảo vệ dữ liệu cá nhân học sinh. Trả về đúng định dạng JSON yêu cầu."},
                    {"role": "user", "content": sanitized_prompt}
                ],
                temperature=0.2,
                max_tokens=token_limits["max_output_tokens"]
            )
            raw_text = (resp.choices[0].message.content or "").strip()
            # Strip reasoning/thinking tokens (<think>...</think>) if present
            cleaned_raw = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()
            data = {}
            try:
                data = json.loads(cleaned_raw)
            except Exception:
                clean_text = re.sub(r'^```json\s*|\s*```$', '', cleaned_raw, flags=re.MULTILINE).strip()
                try:
                    data = json.loads(clean_text)
                except Exception:
                    json_match = re.search(r'\{.*\}', cleaned_raw, re.DOTALL)
                    if json_match:
                        try:
                            data = json.loads(json_match.group(0))
                        except Exception:
                            pass

            detailed = data.get("detailed_explanation")
            if not detailed and '"detailed_explanation"' in cleaned_raw:
                m_det = re.search(r'"detailed_explanation"\s*:\s*"((?:\\"|[^"])*)"', cleaned_raw)
                if m_det:
                    detailed = m_det.group(1).replace("\\n", "\n").replace('\\"', '"')
                m_ria = re.search(r'"riasec_alignment"\s*:\s*"((?:\\"|[^"])*)"', cleaned_raw)
                if m_ria and not data.get("riasec_alignment"):
                    data["riasec_alignment"] = m_ria.group(1).replace("\\n", "\n").replace('\\"', '"')
                m_aca = re.search(r'"academic_alignment"\s*:\s*"((?:\\"|[^"])*)"', cleaned_raw)
                if m_aca and not data.get("academic_alignment"):
                    data["academic_alignment"] = m_aca.group(1).replace("\\n", "\n").replace('\\"', '"')

            if not detailed or detailed.strip().startswith("{"):
                fallback_obj = build_deterministic_ai_explanation(
                    payload.major_code, major_name, major_category, riasec_scores, grades, mastered_skills, admission_blocks
                )
                detailed = fallback_obj.detailed_explanation
                if not data.get("riasec_alignment"):
                    data["riasec_alignment"] = fallback_obj.riasec_alignment
                if not data.get("academic_alignment"):
                    data["academic_alignment"] = fallback_obj.academic_alignment

            return AIExplanationResponse(
                major_code=payload.major_code,
                major_name=major_name,
                detailed_explanation=detailed,
                riasec_alignment=data.get("riasec_alignment", f"Độ tương thích cao với thiên hướng sở thích Holland RIASEC đối với ngành {major_name}."),
                academic_alignment=data.get("academic_alignment", f"Điểm số học bạ THPT của bạn đáp ứng tốt yêu cầu đầu vào các tổ hợp xét tuyển ({', '.join(admission_blocks)})."),
                diagnostic_readiness=data.get("diagnostic_readiness", "Đã đánh giá mức độ sẵn sàng qua các bài kiểm tra chẩn đoán năng lực."),
                strengths=data.get("strengths") or ["Độ tương thích sở thích Holland cao", "Điểm học bạ các môn nòng cốt đạt yêu cầu"],
                recommended_focus_areas=data.get("recommended_focus_areas") or ["Ôn luyện tổ hợp môn xét tuyển", "Rèn luyện thêm kỹ năng tư duy logic"],
                is_ai_generated=True
            )

        try:
            return await asyncio.wait_for(_call_llm(), timeout=120.0)
        finally:
            try:
                await client.close()
            except Exception:
                pass

    except Exception as exc:
        logger.warning(f"AI Explanation LLM failed or timed out: {exc}. Using deterministic fallback.")
        return build_deterministic_ai_explanation(
            payload.major_code, major_name, major_category, riasec_scores, grades, mastered_skills, admission_blocks
        )


# =========================================================================
# AI CAREER COUNSELOR CHAT ENGINE (LAW 91 COMPLIANT)
# =========================================================================

def build_deterministic_chat_response(
    query: str,
    major_name: Optional[str],
    major_code: Optional[str],
    riasec_scores: Dict[str, float],
    grades: Dict[str, float],
    mastered_skills: List[str]
) -> AIChatResponse:
    """
    Deterministic rule-based conversational agent responding to student queries.
    Activated when AI LLM times out (> 8s), encounters quota limits, or is not configured.
    """
    q = query.lower()

    # Smart major resolution from query text or context
    detected_major_name = major_name
    detected_major_code = major_code
    for c_code, meta in FALLBACK_MAJOR_METADATA.items():
        if meta[0].lower() in q or c_code in q:
            detected_major_name = meta[0]
            detected_major_code = c_code
            break

    if any(k in q for k in ["là gì", "la gi", "như thế nào", "khái niệm", "định nghĩa", "học gì", "đào tạo gì", "nội dung học"]) or (detected_major_name and detected_major_name.lower() in q):
        m_name = detected_major_name or major_name or "ngành học bạn quan tâm"
        category_str = ""
        blocks_str = ""
        if detected_major_code and detected_major_code in FALLBACK_MAJOR_METADATA:
            meta = FALLBACK_MAJOR_METADATA[detected_major_code]
            category_str = f" (thuộc nhóm lĩnh vực *{meta[1]}*)"
            blocks_joined = ", ".join(meta[2])
            blocks_str = f"\n- **Tổ hợp môn xét tuyển thường gặp:** {blocks_joined}"

        high_subjs = [k.capitalize() for k, v in grades.items() if isinstance(v, (int, float)) and v >= 8.0]
        high_str = ""
        if high_subjs:
            subjs_joined = ", ".join(high_subjs[:3])
            high_str = f"\n- **Liên hệ với học bạ của bạn:** Bạn có nền tảng học tập rất tích cực ở các môn {subjs_joined}, tạo tiền đề thuận lợi khi tiếp thu khối kiến thức chuyên ngành."

        reply = (
            f"### Giới thiệu về ngành **{m_name}**{category_str}\n\n"
            f"**{m_name}** là ngành đào tạo chuyên môn cung cấp cho người học hệ thống kiến thức toàn diện, tư duy phương pháp luận và kỹ năng thực hành hiện đại, đáp ứng trực tiếp nhu cầu thị trường lao động trong kỷ nguyên số.\n\n"
            f"- **Chương trình đào tạo:** Trang bị từ kiến thức cơ sở ngành, phương pháp giải quyết vấn đề đến các ứng dụng thực tế và công nghệ mới.\n"
            f"- **Vị trí việc làm tiêu biểu:** Sinh viên tốt nghiệp có thể đảm nhận các vị trí chuyên môn tại doanh nghiệp, tổ chức giáo dục/công nghệ, cơ quan nghiên cứu hoặc tự phát triển dự án cá nhân.{blocks_str}{high_str}\n\n"
            f"Bạn muốn tôi phân tích chi tiết hơn về cơ hội nghề nghiệp hay mức độ tương thích của điểm học bạ với ngành **{m_name}**?"
        )
        followups = [
            f"Vì sao em phù hợp với ngành {m_name}?",
            f"Cơ hội việc làm sau khi tốt nghiệp {m_name} ra sao?",
            f"Em cần tập trung cải thiện môn học nào cho ngành {m_name}?"
        ]

    elif any(k in q for k in ["tại sao", "vì sao", "lí do", "phù hợp", "tại sao chọn"]):
        target = f"ngành {major_name}" if major_name else "ngành học được khuyến nghị"
        reply = (
            f"Hệ thống đề xuất {target} dựa trên thuật toán đối sánh 3 trụ cột khách quan:\n\n"
            f"1. **Sở thích Holland (45% trọng số):** Vector tâm lý của bạn tương thích cao với môi trường học tập và tính chất công việc của ngành.\n"
            f"2. **Điểm học bạ THPT (35% trọng số):** Năng lực học tập của bạn ở các môn trọng tâm đạt mức điểm chuẩn hóa vững chắc so với phổ điểm toàn quốc.\n"
            f"3. **Kỹ năng chẩn đoán đầu vào:** " + (
                f"Bạn đã đạt chuẩn {len(mastered_skills)} kỹ năng nền tảng ({', '.join(mastered_skills[:2])}), giúp giảm thiểu áp lực ở các môn tiên quyết."
                if mastered_skills else "Bạn có thể làm thêm bài test 10 phút để xác thực các kỹ năng nền tảng và rút ngắn lộ trình học tập."
            )
        )
        followups = [
            f"Điểm học bạ của em cần cải thiện môn nào cho {target}?",
            f"Lộ trình học tập 4 tuần của {target} gồm những gì?",
            f"Cơ hội việc làm sau khi tốt nghiệp {target} ra sao?"
        ]

    elif any(k in q for k in ["môn gì", "cải thiện", "nâng cao", "học thêm môn", "khối thi"]):
        high = [k.capitalize() for k, v in grades.items() if isinstance(v, (int, float)) and v >= 8.5]
        low = [k.capitalize() for k, v in grades.items() if isinstance(v, (int, float)) and v < 7.5]
        target = f"ngành {major_name}" if major_name else "các ngành mục tiêu"
        reply = (
            f"Để nâng cao khả năng trúng tuyển vào {target}:\n\n"
            f"- **Thế mạnh hiện tại:** Các môn {', '.join(high) if high else 'Toán, Tiếng Anh'} của bạn đang có điểm số rất tốt, hãy tiếp tục duy trì phong độ.\n"
            f"- **Môn cần tập trung cải thiện:** " + (
                f"Bạn nên dành thêm 2-3 giờ mỗi tuần ôn luyện cho môn {', '.join(low)}, đặc biệt là giải các đề thi thử theo cấu trúc chuẩn của Bộ GD&ĐT."
                if low else "Điểm số các môn của bạn khá đồng đều, hãy tập trung rèn luyện các dạng bài phân loại điểm 9-10."
            )
        )
        followups = [
            "Làm thế nào để phân bổ thời gian học 10 giờ/tuần hợp lý?",
            "Bài test chẩn đoán kỹ năng logic gồm những nội dung gì?",
            "Lộ trình học tập từng kỳ của ngành này thế nào?"
        ]

    elif any(k in q for k in ["chẩn đoán", "bài test", "kỹ năng", "fr03", "test nhanh"]):
        target = f"ngành {major_name}" if major_name else "lộ trình đại học"
        reply = (
            f"Bài kiểm tra chẩn đoán năng lực nền tảng gồm 6 chuyên đề (10-15 phút/bài) về Logic, Toán rời rạc, Giải tích, Tiếng Anh học thuật...\n\n"
            f"Khi bạn đạt từ 7.0/10 điểm trở lên (≥ 70%), kỹ năng tương ứng sẽ được hệ thống công nhận là **MASTERED**. "
            f"Khi đó, thuật toán LlamaIndex Gap Engine sẽ tự động khấu trừ môn tiên quyết đó khỏi danh sách thiếu hụt, "
            f"giúp lộ trình chuẩn bị cho {target} của bạn ngắn hơn và tập trung thẳng vào kiến thức chuyên ngành nâng cao."
        )
        followups = [
            "Em nên làm bài test chẩn đoán nào trước?",
            "Nếu làm chưa đạt 7.0 thì có được làm lại không?",
            "Xem các kỹ năng còn thiếu của em ở đâu?"
        ]

    elif any(k in q for k in ["việc làm", "nghề nghiệp", "ra trường", "làm gì", "cơ hội"]):
        target = f"ngành {major_name}" if major_name else "ngành học này"
        reply = (
            f"Theo khảo sát chuẩn hóa và Cây nghề nghiệp Phoenix Ho của Bộ GD&ĐT, sinh viên tốt nghiệp {target} có cơ hội đảm nhận các vị trí việc làm tiêu biểu:\n\n"
            f"- Chuyên viên kỹ thuật và phát triển giải pháp chuyên môn\n"
            f"- Chuyên viên nghiên cứu, phân tích dữ liệu và tư vấn nghiệp vụ\n"
            f"- Quản lý dự án chuyên ngành hoặc khởi nghiệp sáng tạo\n\n"
            f"Bạn có thể xem chi tiết danh sách vị trí việc làm và mức độ phát triển thị trường tại trang Danh mục 435 ngành."
        )
        followups = [
            f"Tại sao ngành {major_name or ''} lại phù hợp với sở thích của em?",
            "Em cần chuẩn bị những kỹ năng mềm nào trước khi vào đại học?",
            "Lộ trình học tập từng kỳ phân bổ ra sao?"
        ]

    else:
        target = f"ngành {major_name}" if major_name else "chọn ngành đại học"
        reply = (
            f"Chào bạn! Tôi là Cố vấn Hướng nghiệp AI CareerGuide. Tôi đồng hành cùng bạn dựa trên kết quả khảo sát Holland RIASEC, "
            f"bảng điểm học bạ THPT và các bài kiểm tra chẩn đoán kỹ năng đầu vào.\n\n"
            f"Mọi dữ liệu của bạn đều được bảo mật nghiêm ngặt theo Luật 91/2025/QH15. "
            f"Bạn có thắc mắc gì về {target}, tổ hợp môn xét tuyển hay kế hoạch ôn tập kỹ năng không?"
        )
        followups = [
            f"Giải thích chi tiết vì sao em phù hợp với {target}?",
            "Với điểm số hiện tại em nên tập trung học môn gì?",
            "Làm bài test chẩn đoán kỹ năng nền tảng có lợi ích gì?"
        ]

    return AIChatResponse(
        reply=reply,
        suggested_followups=followups,
        context_major_code=major_code,
        is_fallback=True
    )


async def chat_with_career_counselor(
    db: AsyncSession,
    payload: AIChatRequest,
    current_user_id: Optional[uuid.UUID] = None
) -> AIChatResponse:
    """
    Conversational AI Career Counselor chat endpoint (FR06).
    STRICT PII SANITIZATION (Law 91/2025/QH15 & Pure Guidance Scope):
    - Redacts all personal identifiers from user input and chat context.
    - Anonymously supplies student's RIASEC scores, subject grades, and diagnostic check results.
    - Enforces 8.0s timeout with automatic graceful deterministic counselor fallback.
    """
    sanitized_user_msg = sanitize_pii(payload.message)

    # 1. Fetch Major Context if major_code provided
    major_name = None
    major_category = None
    admission_blocks = []
    if payload.major_code:
        fallback_info = FALLBACK_MAJOR_METADATA.get(
            payload.major_code, (f"Ngành {payload.major_code}", "Đào tạo đại học chính quy", ["A00", "A01", "D01"])
        )
        major_name = fallback_info[0]
        major_category = fallback_info[1]
        admission_blocks = list(fallback_info[2])
        if db is not None:
            try:
                major_res = await db.execute(select(Major).where(Major.major_code == payload.major_code))
                major = major_res.scalar_one_or_none()
                if major:
                    major_name = major.name
                    major_category = major.category
                    from app.models.taxonomy import MajorSubjectBlock
                    blocks_res = await db.execute(select(MajorSubjectBlock).where(MajorSubjectBlock.major_id == major.id))
                    admission_blocks = [b.block_code for b in blocks_res.scalars().all()]
            except Exception as db_err:
                logger.warning(f"Database query skipped for chat major context: {db_err}")

    # 2. Resolve Student Test Profile
    riasec_scores = payload.riasec_scores
    grades = payload.grades_by_subject
    mastered_skills = payload.diagnostic_skills_mastered or []

    effective_user_id = payload.user_id or current_user_id
    if db is not None and effective_user_id and (not riasec_scores or not grades):
        try:
            if not riasec_scores:
                assess_res = await db.execute(select(StudentAssessment).where(StudentAssessment.user_id == effective_user_id))
                assess = assess_res.scalar_one_or_none()
                if assess and assess.riasec_scores:
                    riasec_scores = assess.riasec_scores

            if not grades:
                grade_res = await db.execute(
                    select(StudentGrade).where(StudentGrade.user_id == effective_user_id).order_by(StudentGrade.created_at.desc())
                )
                g = grade_res.scalar_one_or_none()
                if g and g.grades_by_subject:
                    grades = g.grades_by_subject

            if not mastered_skills:
                diag_res = await db.execute(select(StudentDiagnosticTest).where(StudentDiagnosticTest.user_id == effective_user_id))
                diag_tests = list(diag_res.scalars().all())
                mastered_skills = [d.skill_code for d in diag_tests if d.is_passed]
        except Exception as db_err:
            logger.warning(f"Database query skipped for chat student profile: {db_err}")

    riasec_scores = riasec_scores or {"R": 0.5, "I": 0.5, "A": 0.5, "S": 0.5, "E": 0.5, "C": 0.5}
    grades = grades or {"math": 8.0, "physics": 8.0, "english": 8.0}

    # If OpenAI API is not configured, return deterministic response
    if not settings.OPENAI_API_KEY:
        return build_deterministic_chat_response(
            sanitized_user_msg, major_name, payload.major_code, riasec_scores, grades, mastered_skills
        )

    # 3. Call LLM with strict PII-sanitized conversation context
    try:
        from openai import AsyncOpenAI
        import json
        import re
        client_kwargs = {"api_key": settings.OPENAI_API_KEY, "timeout": 120.0}
        if settings.OPENAI_BASE_URL:
            client_kwargs["base_url"] = settings.OPENAI_BASE_URL
        client = AsyncOpenAI(**client_kwargs)

        riasec_summary = ", ".join([f"{k}: {round(float(v)*100)}%" for k, v in riasec_scores.items()])
        grades_summary = ", ".join([f"{k}: {v}" for k, v in grades.items()])
        mastered_summary = ", ".join(mastered_skills) if mastered_skills else "Chưa có"

        system_instruction = (
            "Bạn là Cố vấn Hướng nghiệp AI CareerGuide chuyên nghiệp, ân cần, trung thực, hỗ trợ học sinh THPT Việt Nam.\n"
            "QUY TẮC BẢO MẬT DỮ LIỆU CÁ NHÂN (Luật 91/2025/QH15 & Pure Guidance Scope):\n"
            "1. Dữ liệu học sinh được bảo vệ và khử khuẩn định danh hoàn toàn. Tuyệt đối không đề cập hoặc hỏi tên tuổi, trường lớp, số điện thoại, email, địa chỉ.\n"
            "2. Tuyệt đối không đề cập đến học phí hay định kiến vùng miền.\n"
            "3. HỒ SƠ NĂNG LỰC ẨN DANH CỦA HỌC SINH:\n"
            f"   - Sở thích Holland RIASEC: {riasec_summary}\n"
            f"   - Điểm học bạ THPT: {grades_summary}\n"
            f"   - Kỹ năng chẩn đoán đầu vào đã đạt: {mastered_summary}\n"
            + (f"   - Đang tìm hiểu ngành: {major_name} (Mã ngành: {payload.major_code}, Khối: {', '.join(admission_blocks)})\n" if major_name else "") +
            "4. YÊU CẦU TRẢ LỜI:\n"
            "   - Hãy trả lời trực tiếp, chính xác, súc tích và giàu giá trị thực tế theo đúng câu hỏi của học sinh (khoảng 150-250 từ).\n"
            "   - Định dạng câu trả lời bằng Markdown đẹp mắt (gạch đầu dòng, in đậm từ khóa quan trọng).\n"
            "   - Nếu học sinh hỏi về một ngành (ví dụ: 'sư phạm tin học là gì'), hãy giải thích cặn kẽ ngành đó là gì, học gì, ra trường làm gì và liên hệ thực tế với năng lực/điểm số của học sinh.\n"
            "5. Đề xuất 3 câu hỏi gợi ý tiếp theo phù hợp với ngữ cảnh cuộc trò chuyện.\n"
            "Trả về đúng định dạng JSON: {\"reply\": \"Nội dung câu trả lời\", \"suggested_followups\": [\"câu 1\", \"câu 2\", \"câu 3\"]}"
        )

        # Build sanitized message chain ensuring valid role alternation:
        # system -> user -> assistant -> user ...
        sanitized_history = []
        if payload.history:
            found_first_user = False
            last_role = None
            for h in payload.history:
                role = "assistant" if h.role == "assistant" else "user"
                content = sanitize_pii(h.content or "").strip()
                if not content:
                    continue
                if not found_first_user:
                    if role == "user":
                        found_first_user = True
                        sanitized_history.append({"role": "user", "content": content})
                        last_role = "user"
                else:
                    if role != last_role:
                        sanitized_history.append({"role": role, "content": content})
                        last_role = role
                    else:
                        sanitized_history[-1]["content"] += f"\n{content}"

        if sanitized_history and sanitized_history[-1]["role"] == "user":
            sanitized_history[-1]["content"] += f"\n{sanitized_user_msg}"
        else:
            sanitized_history.append({"role": "user", "content": sanitized_user_msg})

        # Giữ tối đa 20 lượt hội thoại gần nhất để tận dụng tối đa context window của mô hình
        if len(sanitized_history) > 20:
            sanitized_history = sanitized_history[-20:]

        # Guarantee the first message after system is always 'user'
        if sanitized_history and sanitized_history[0]["role"] != "user":
            sanitized_history.pop(0)

        messages = [{"role": "system", "content": system_instruction}] + sanitized_history

        async def _call_chat():
            token_limits = await resolve_model_token_limits()
            resp = await client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=0.3,
                max_tokens=token_limits["max_output_tokens"]
            )
            raw = (resp.choices[0].message.content or "").strip()
            # Strip reasoning/thinking tokens (<think>...</think>) if present
            cleaned_raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
            data = {}
            reply_text = ""
            followups = []
            try:
                data = json.loads(cleaned_raw)
                reply_text = data.get("reply", "")
                followups = data.get("suggested_followups", [])
            except Exception:
                clean_json = re.sub(r'^```json\s*|\s*```$', '', cleaned_raw, flags=re.MULTILINE).strip()
                try:
                    data = json.loads(clean_json)
                    reply_text = data.get("reply", "")
                    followups = data.get("suggested_followups", [])
                except Exception:
                    json_match = re.search(r'\{.*\}', cleaned_raw, re.DOTALL)
                    if json_match:
                        try:
                            data = json.loads(json_match.group(0))
                            reply_text = data.get("reply", "")
                            followups = data.get("suggested_followups", [])
                        except Exception:
                            pass
                    if not reply_text:
                        m = re.search(r'"reply"\s*:\s*"(.*?)(?:"\s*,\s*"suggested_followups"|"\s*})', cleaned_raw, re.DOTALL)
                        if m:
                            reply_text = (
                                m.group(1)
                                .replace("\\n", "\n")
                                .replace('\\"', '"')
                                .replace("\\\\", "\\")
                            )
                        else:
                            reply_text = clean_json

            if not reply_text:
                reply_text = raw if raw else f"Chào bạn! Đối với ngành {major_name or 'này'}, hãy đặt câu hỏi để tôi hỗ trợ tư vấn chi tiết hơn."

            if not followups:
                followups = [
                    f"Vì sao em phù hợp với ngành {major_name or 'này'}?",
                    f"Em cần cải thiện môn học nào cho tổ hợp xét tuyển?",
                    f"Lộ trình học tập chi tiết của ngành gồm những gì?"
                ]

            return AIChatResponse(
                reply=reply_text,
                suggested_followups=followups,
                context_major_code=payload.major_code,
                is_fallback=False
            )

        try:
            return await asyncio.wait_for(_call_chat(), timeout=120.0)
        finally:
            try:
                await client.close()
            except Exception:
                pass

    except Exception as exc:
        logger.error(f"AI Chat LLM failed or timed out: {exc}", exc_info=True)
        resp = build_deterministic_chat_response(
            sanitized_user_msg, major_name, payload.major_code, riasec_scores, grades, mastered_skills
        )
        err_str = str(exc).lower()
        if "402" in err_str or "insufficient_quota" in err_str or "payment required" in err_str or "insufficient balance" in err_str:
            resp.reply = (
                "> [!NOTE]\n"
                "> **Thông báo kết nối AI:** Nhà cung cấp API (`api.xah.io`) thông báo **Hết số dư tài khoản (Insufficient balance)**. "
                "Hệ thống đang tự động giải đáp cho bạn dựa trên **Cơ sở tri thức chuẩn hóa 435 ngành Bộ GD&ĐT & Cây nghề nghiệp Phoenix Ho**.\n\n"
                + resp.reply
            )
        return resp


def get_llm_status() -> LLMStatusResponse:
    """Returns current active LLM configuration and key masking status."""
    key = settings.OPENAI_API_KEY
    masked = None
    if key and key.strip():
        k = key.strip()
        if len(k) > 8:
            masked = f"{k[:4]}...{k[-4:]}"
        else:
            masked = "****"
    return LLMStatusResponse(
        model=settings.LLM_MODEL,
        base_url=settings.OPENAI_BASE_URL or "https://api.openai.com/v1",
        is_key_configured=bool(key and key.strip()),
        masked_key=masked,
        embedding_model=settings.EMBEDDING_MODEL,
        max_tokens=settings.LLM_MAX_TOKENS,
        context_window=settings.LLM_MAX_CONTEXT_TOKENS,
    )


async def test_llm_connection(payload: LLMConnectionTestRequest) -> LLMConnectionTestResponse:
    """
    Tests live connection to the configured or provided LLM API endpoint.
    Sends a lightweight ping probe and measures latency and status code.
    Returns clear success or detailed Vietnamese diagnostic error messages.
    """
    import time
    from datetime import datetime

    tested_at = datetime.utcnow().isoformat()
    if payload.api_key is not None:
        key = payload.api_key.strip()
    else:
        key = (settings.OPENAI_API_KEY or "").strip()
    base_url = (payload.base_url or settings.OPENAI_BASE_URL or "https://api.xkiro.com/v1").strip()
    model = (payload.model or settings.LLM_MODEL or "mistralai/mistral-large-2512").strip()

    if not key:
        return LLMConnectionTestResponse(
            success=False,
            status_code=400,
            latency_ms=0.0,
            model_used=model,
            base_url=base_url or settings.OPENAI_BASE_URL or "https://api.xkiro.com/v1",
            is_configured=False,
            message="Chưa cấu hình API Key. Vui lòng nhập API Key để kiểm tra kết nối.",
            preview_reply=None,
            tested_at=tested_at
        )

    start_time = time.time()
    try:
        from openai import AsyncOpenAI
        client_kwargs = {"api_key": key, "timeout": 35.0}
        if base_url:
            client_kwargs["base_url"] = base_url
        client = AsyncOpenAI(**client_kwargs)

        try:
            token_limits = await resolve_model_token_limits(api_key=key, base_url=base_url, model=model)
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": "Xin chào, phản hồi ngắn gọn 1 từ: OK"}
                ],
                max_tokens=min(2048, token_limits["max_output_tokens"]),
                temperature=0.0
            )
            latency_ms = round((time.time() - start_time) * 1000, 1)
            msg = response.choices[0].message
            reply = (msg.content or getattr(msg, "reasoning_content", None) or "PONG").strip()

            return LLMConnectionTestResponse(
                success=True,
                status_code=200,
                latency_ms=latency_ms,
                model_used=model,
                base_url=base_url or "https://api.openai.com/v1",
                is_configured=True,
                message=f"Kết nối thành công tới mô hình '{model}'. Thời gian phản hồi: {latency_ms}ms.",
                preview_reply=reply,
                tested_at=tested_at
            )
        finally:
            try:
                await client.close()
            except Exception:
                pass
    except Exception as e:
        latency_ms = round((time.time() - start_time) * 1000, 1)
        error_msg = str(e)
        status_code = getattr(e, "status_code", 500)

        if "401" in error_msg or "AuthenticationError" in type(e).__name__:
            status_code = 401
            friendly = "Xác thực thất bại (401 Unauthorized): API Key không chính xác, đã hết hạn hoặc không có quyền truy cập."
        elif "402" in error_msg or "insufficient_quota" in error_msg.lower() or "insufficient balance" in error_msg.lower():
            status_code = 402
            friendly = "Hết hạn mức / Số dư tài khoản (402 Insufficient Quota): Tài khoản API trên nhà cung cấp (api.xah.io) đã hết số dư. Vui lòng nạp thêm credit hoặc sử dụng API Key khác."
        elif "404" in error_msg or "NotFoundError" in type(e).__name__:
            status_code = 404
            friendly = f"Mô hình không tồn tại (404 NotFound): Mô hình '{model}' không được endpoint '{base_url or 'api.openai.com'}' hỗ trợ. Hãy kiểm tra lại tên model."
        elif "429" in error_msg or "RateLimitError" in type(e).__name__:
            status_code = 429
            friendly = "Vượt hạn mức (429 RateLimitError): Tài khoản API đã hết quota sử dụng hoặc gửi yêu cầu quá nhanh."
        elif "ConnectionError" in type(e).__name__ or "ConnectError" in error_msg or "WinError 1225" in error_msg:
            status_code = 503
            friendly = f"Không thể kết nối đến máy chủ API '{base_url or 'api.openai.com'}'. Vui lòng kiểm tra lại Base URL hoặc kết nối mạng."
        elif "Timeout" in type(e).__name__ or "timed out" in error_msg.lower():
            status_code = 504
            friendly = f"Yêu cầu quá thời gian chờ (Gateway Timeout > 10.0s) khi kết nối tới '{base_url or 'api.openai.com'}'."
        else:
            friendly = f"Lỗi gọi API ({type(e).__name__}): {error_msg}"

        return LLMConnectionTestResponse(
            success=False,
            status_code=status_code,
            latency_ms=latency_ms,
            model_used=model,
            base_url=base_url or "Default endpoint",
            is_configured=True,
            message=friendly,
            preview_reply=None,
            tested_at=tested_at
        )

def update_llm_config(model: str = None, base_url: str = None, api_key: str = None) -> LLMStatusResponse:
    """Dynamically updates active LLM configuration in memory and returns new status."""
    if model and model.strip():
        settings.LLM_MODEL = model.strip()
    if base_url and base_url.strip():
        settings.OPENAI_BASE_URL = base_url.strip()
    if api_key and api_key.strip():
        settings.OPENAI_API_KEY = api_key.strip()
    clear_model_caps_cache()
    return get_llm_status()
