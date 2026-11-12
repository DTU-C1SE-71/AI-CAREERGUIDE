"""
Agent "Phân tích ngành" & Agent "Phân tích kỹ năng học sinh".

1. Major Insight Agent
   - Học sinh bấm phân tích ngành -> trả về Nội dung đào tạo + Vị trí nghề nghiệp.
   - Cache-first: bản ghi được lưu theo major_code trong bảng `major_insights`.
     Lần xem đầu tiên mới gọi AI, các lần sau đọc thẳng từ DB (không tốn token).

2. Student Skill Agent
   - Dựa trên dữ liệu bài test (RIASEC, điểm học bạ, thiên hướng nhận thức), chỉ ra
     ưu điểm / điểm cần cải thiện trong cách học, kỹ năng cần bổ sung và cách cải thiện.
   - Cache theo (profile_hash, major_code) trong bảng `student_skill_insights`.
   - Mọi output đều ngắn gọn, dễ hiểu; AI không khả dụng thì dùng bản dựng tất định.
"""

import asyncio
import hashlib
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.insight import MajorInsight, StudentSkillInsight
from app.models.taxonomy import Major, MajorSubjectBlock
from app.schemas.insight import (
    CareerPosition,
    InsightPoint,
    MajorInsightResponse,
    SkillGapItem,
    StudentSkillAnalysisRequest,
    StudentSkillAnalysisResponse,
    TrainingContent,
)

logger = logging.getLogger(__name__)

RIASEC_LABELS: Dict[str, str] = {
    "R": "Thực tế (thích làm việc cụ thể, máy móc, công cụ)",
    "I": "Nghiên cứu (thích phân tích, tìm hiểu nguyên nhân)",
    "A": "Nghệ thuật (thích sáng tạo, thể hiện cá tính)",
    "S": "Xã hội (thích giúp đỡ, kết nối con người)",
    "E": "Quản lý (thích dẫn dắt, thuyết phục)",
    "C": "Nghiệp vụ (thích quy trình, số liệu, tổ chức)",
}

# Kỹ năng nên bổ sung theo nhóm sở thích nổi bật
RIASEC_SKILL_HINTS: Dict[str, Tuple[str, str, List[str]]] = {
    "R": (
        "Kỹ năng thực hành & sử dụng công cụ",
        "Ngành này học qua làm, thiếu thực hành sẽ khó theo kịp bài tập và đồ án.",
        ["Mỗi tuần làm 1 bài thực hành nhỏ (30-45 phút)", "Học 1 công cụ cơ bản của ngành qua video hướng dẫn"],
    ),
    "I": (
        "Tư duy phân tích & giải quyết vấn đề",
        "Đây là kỹ năng lõi để hiểu bài lý thuyết và xử lý bài tập chuyên ngành.",
        ["Luyện 2-3 bài tập tình huống mỗi tuần", "Viết lại cách giải bằng lời của mình sau mỗi bài"],
    ),
    "A": (
        "Tư duy sáng tạo & cảm thụ thẩm mỹ",
        "Giúp bạn tạo sản phẩm khác biệt thay vì chỉ làm đúng yêu cầu.",
        ["Tham khảo 5 sản phẩm tốt mỗi tuần và ghi lại điểm hay", "Tập làm 1 sản phẩm nhỏ mỗi tháng"],
    ),
    "S": (
        "Giao tiếp & thấu hiểu con người",
        "Phần lớn công việc ngành này cần trao đổi, trình bày và phối hợp nhóm.",
        ["Tập trình bày 3 phút mỗi tuần trước gương hoặc nhóm", "Chủ động hỏi thầy cô/cựu sinh viên 1 câu mỗi tuần"],
    ),
    "E": (
        "Lãnh đạo & thuyết trình thuyết phục",
        "Càng lên cao, công việc càng cần dẫn dắt nhóm và bảo vệ ý tưởng.",
        ["Nhận 1 vai trò nhóm trưởng trong dự án gần nhất", "Luyện trả lời phản biện cho bài thuyết trình"],
    ),
    "C": (
        "Tổ chức dữ liệu & quản lý thời gian",
        "Khối lượng bài tập lớn, thiếu kỷ luật sẽ dễ trễ hạn.",
        ["Dùng lịch tuần, chia việc lớn thành việc 30 phút", "Ghi chú theo mẫu cố định để dễ ôn lại"],
    ),
}

COGNITIVE_LABELS: Dict[str, str] = {
    "VISUAL": "học tốt nhất qua hình ảnh, sơ đồ",
    "THEORETICAL": "học tốt nhất qua lý thuyết, đọc tài liệu",
    "HANDS_ON": "học tốt nhất khi được làm trực tiếp",
    "INTERACTIVE": "học tốt nhất khi trao đổi với người khác",
    "CREATIVE": "học tốt nhất khi được tự do sáng tạo",
    "PROCEDURAL": "học tốt nhất theo quy trình từng bước",
    "DYNAMIC": "thích môi trường năng động, thay đổi",
    "STABLE": "thích môi trường ổn định, rõ ràng",
    "HUMAN": "quan tâm yếu tố con người",
    "SYSTEMS": "quan tâm hệ thống và quy luật",
    "ANALYTICAL": "thích mổ xẻ vấn đề bằng số liệu",
    "LINGUISTIC": "mạnh về ngôn ngữ, diễn đạt",
    "SPATIAL": "mạnh về không gian, hình khối",
    "LOGICAL": "mạnh về logic, lập luận",
}

MAJOR_INSIGHT_PROMPT_VERSION = "v1"


# =========================================================================
# LLM helper
# =========================================================================

async def _call_llm_json(system_prompt: str, user_prompt: str, max_tokens: int = 4000) -> Optional[Dict[str, Any]]:
    """Gọi LLM (OpenAI-compatible) và trả về dict JSON. Trả None nếu thất bại."""
    if not (settings.OPENAI_API_KEY or "").strip():
        return None

    try:
        from openai import AsyncOpenAI

        client_kwargs: Dict[str, Any] = {
            "api_key": settings.OPENAI_API_KEY,
            "timeout": settings.LLM_TIMEOUT_SECONDS,
        }
        if settings.OPENAI_BASE_URL:
            client_kwargs["base_url"] = settings.OPENAI_BASE_URL
        client = AsyncOpenAI(**client_kwargs)

        async def _call() -> Optional[Dict[str, Any]]:
            resp = await client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=max_tokens,
            )
            raw = (resp.choices[0].message.content or "").strip()
            raw = re.sub(r"</?think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            return _parse_json_object(raw)

        try:
            return await asyncio.wait_for(_call(), timeout=45.0)
        finally:
            try:
                await client.close()
            except Exception:
                pass
    except Exception as exc:
        logger.warning("[InsightAgent] LLM call failed: %s", exc)
        return None


def _parse_json_object(raw_text: str) -> Optional[Dict[str, Any]]:
    text = raw_text.strip()
    candidates = [text]
    candidates.append(re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip())
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        candidates.append(match.group(0))

    for candidate in candidates:
        if not candidate:
            continue
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except Exception:
            continue
    return None


def _as_str_list(value: Any, limit: int = 6, max_len: int = 160) -> List[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            out.append(text[:max_len])
        if len(out) >= limit:
            break
    return out


# =========================================================================
# 1. MAJOR INSIGHT AGENT
# =========================================================================

async def _load_major_context(db: Optional[AsyncSession], major_code: str) -> Dict[str, Any]:
    """Lấy thông tin ngành từ DB, fallback về dữ liệu seed chuẩn."""
    ctx: Dict[str, Any] = {
        "major_code": major_code,
        "name": f"Ngành đào tạo (mã {major_code})",
        "category": "Khác",
        "description": "",
        "careers": [],
        "blocks": [],
    }

    if db is not None:
        try:
            stmt = (
                select(Major)
                .where(Major.major_code == major_code)
                .options(
                    selectinload(Major.careers),
                    selectinload(Major.subject_blocks).selectinload(MajorSubjectBlock.subject_block),
                )
            )
            major = (await db.execute(stmt)).scalar_one_or_none()
            if major:
                ctx.update(
                    {
                        "name": major.name,
                        "category": major.category or "Khác",
                        "description": major.description or "",
                        "careers": [c.title for c in major.careers if getattr(c, "title", None)],
                        "blocks": [
                            msb.subject_block.block_code
                            for msb in major.subject_blocks
                            if getattr(msb, "subject_block", None) is not None
                        ],
                    }
                )
                return ctx
        except Exception as exc:
            logger.warning("[MajorInsight] DB lookup failed for %s: %s", major_code, exc)

    try:
        from app.services.taxonomy.service import load_seed_majors

        for item in load_seed_majors():
            if str(item.get("major_code")) == major_code:
                ctx.update(
                    {
                        "name": item.get("name") or ctx["name"],
                        "category": item.get("category") or "Khác",
                        "description": item.get("description") or "",
                        "careers": [str(c) for c in (item.get("careers") or [])],
                        "blocks": [str(b) for b in (item.get("blocks") or [])],
                    }
                )
                break
    except Exception as exc:
        logger.debug("[MajorInsight] Seed fallback skipped: %s", exc)

    return ctx


def build_deterministic_major_insight(ctx: Dict[str, Any]) -> Tuple[TrainingContent, List[CareerPosition], bool]:
    """Nội dung chuẩn hoá dựng từ dữ liệu ngành khi AI không khả dụng."""
    name = ctx["name"]
    category = ctx["category"]

    overview = ctx.get("description") or (
        f"Chương trình đào tạo {name} kết hợp kiến thức nền tảng, kỹ năng thực hành "
        f"và dự án thực tế, giúp sinh viên làm được việc ngay sau tốt nghiệp."
    )

    training = TrainingContent(
        overview=overview[:600],
        core_knowledge=[
            f"Kiến thức nền tảng và nguyên lý cốt lõi của {name}",
            "Phương pháp phân tích, đọc tài liệu và giải quyết vấn đề chuyên ngành",
            "Kiến thức bổ trợ: ngoại ngữ chuyên ngành, tin học, pháp luật và kỹ năng mềm",
            "Thực tập, đồ án và nghiên cứu ứng dụng gắn với thực tế",
        ],
        practical_skills=[
            "Sử dụng công cụ, phần mềm đặc thù của ngành",
            "Phân tích dữ liệu và trình bày kết quả bằng báo cáo, thuyết trình",
            "Làm việc nhóm, quản lý tiến độ dự án",
            "Viết báo cáo và bảo vệ sản phẩm trước hội đồng",
        ],
        curriculum_highlights=[
            "Học qua dự án (project-based) ở các học kỳ chuyên ngành",
            "Thực tập doanh nghiệp và kiến tập nghề nghiệp",
            "Được chọn môn chuyên sâu theo định hướng nghề",
            f"Chương trình thuộc lĩnh vực {category} theo chuẩn Bộ GD&ĐT",
        ],
        study_duration="4 năm (8 học kỳ), khoảng 120-140 tín chỉ",
    )

    titles = [c for c in ctx.get("careers") or [] if c]
    if not titles:
        titles = [
            f"Chuyên viên {name.lower()}",
            "Chuyên viên phân tích & nghiên cứu",
            "Quản lý dự án chuyên ngành",
            "Giảng viên / nghiên cứu viên",
        ]

    career_positions = [
        CareerPosition(
            title=title,
            description=f"Đảm nhận công việc chuyên môn thuộc ngành {name}.",
            career_level="Chuyên viên" if idx > 0 else "Khởi điểm",
        )
        for idx, title in enumerate(titles[:6])
    ]
    return training, career_positions, False


async def _generate_major_insight_with_ai(ctx: Dict[str, Any]) -> Optional[Tuple[TrainingContent, List[CareerPosition]]]:
    system_prompt = (
        "Bạn là chuyên gia tư vấn giáo dục đại học Việt Nam. "
        "Bạn trả về JSON hợp lệ, tiếng Việt, ngắn gọn và dễ hiểu với học sinh cấp 3."
    )
    user_prompt = (
        f"Hãy mô tả NGẮN GỌN ngành đào tạo sau theo chuẩn Thông tư 09/2022/TT-BGDĐT.\n"
        f"- Tên ngành: {ctx['name']}\n"
        f"- Mã ngành: {ctx['major_code']}\n"
        f"- Lĩnh vực: {ctx['category']}\n"
        f"- Mô tả hiện có: {ctx.get('description') or 'chưa có'}\n"
        f"- Nghề nghiệp gợi ý hiện có: {', '.join(ctx.get('careers') or []) or 'chưa có'}\n\n"
        "QUY TẮC:\n"
        "1. Mỗi gạch đầu dòng tối đa 20 từ, học sinh lớp 12 đọc hiểu ngay.\n"
        "2. Không bịa học phí, không nêu tên trường cụ thể, không hứa mức lương.\n"
        "3. 'overview' 2-3 câu: ngành này học gì và ra làm gì.\n"
        "4. 'core_knowledge' và 'practical_skills': 4 mục mỗi loại.\n"
        "5. 'curriculum_highlights': 3 mục (dự án, thực tập, chứng chỉ/định hướng).\n"
        "6. 'career_positions': 5 vị trí thực tế, mỗi vị trí 1 câu mô tả ngắn.\n\n"
        "Trả về đúng JSON:\n"
        "{\n"
        '  "training_content": {\n'
        '    "overview": "...",\n'
        '    "core_knowledge": ["...", "..."],\n'
        '    "practical_skills": ["...", "..."],\n'
        '    "curriculum_highlights": ["...", "..."],\n'
        '    "study_duration": "..."\n'
        "  },\n"
        '  "career_positions": [{"title": "...", "description": "...", "career_level": "..."}]\n'
        "}"
    )

    data = await _call_llm_json(system_prompt, user_prompt, max_tokens=3000)
    if not data:
        return None

    raw_training = data.get("training_content")
    if not isinstance(raw_training, dict):
        return None
    overview = str(raw_training.get("overview") or "").strip()
    if not overview:
        return None

    training = TrainingContent(
        overview=overview[:800],
        core_knowledge=_as_str_list(raw_training.get("core_knowledge"), limit=6),
        practical_skills=_as_str_list(raw_training.get("practical_skills"), limit=6),
        curriculum_highlights=_as_str_list(raw_training.get("curriculum_highlights"), limit=5),
        study_duration=(str(raw_training.get("study_duration")).strip()[:80] if raw_training.get("study_duration") else None),
    )

    career_positions: List[CareerPosition] = []
    for item in (data.get("career_positions") or [])[:6]:
        if isinstance(item, str):
            title = item.strip()
            if title:
                career_positions.append(CareerPosition(title=title[:160]))
        elif isinstance(item, dict):
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            career_positions.append(
                CareerPosition(
                    title=title[:160],
                    description=(str(item.get("description")).strip()[:240] if item.get("description") else None),
                    career_level=(str(item.get("career_level")).strip()[:60] if item.get("career_level") else None),
                )
            )
    if not career_positions:
        return None
    return training, career_positions


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
    Chỉ sinh bằng AI khi chưa có (hoặc refresh=True), sau đó lưu lại cho mọi học sinh dùng chung.
    """
    if db is not None and not refresh:
        try:
            cached_entry = (
                await db.execute(select(MajorInsight).where(MajorInsight.major_code == major_code))
            ).scalar_one_or_none()
            if cached_entry:
                return _to_major_insight_response(cached_entry, cached=True)
        except Exception as exc:
            logger.warning("[MajorInsight] Cache read failed for %s: %s", major_code, exc)

    ctx = await _load_major_context(db, major_code)

    ai_result = await _generate_major_insight_with_ai(ctx)
    if ai_result:
        training, career_positions = ai_result
        is_ai = True
    else:
        training, career_positions, is_ai = build_deterministic_major_insight(ctx)

    model_name = settings.LLM_MODEL if is_ai else None
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
    canonical = {
        "major_code": payload.major_code or "",
        "riasec": {k: round(float(v), 3) for k, v in sorted(payload.riasec_scores.items())},
        "grades": {k: round(float(v), 2) for k, v in sorted(payload.grades_by_subject.items())},
        "cognitive": {k: str(v) for k, v in sorted(payload.cognitive_preferences.items())},
    }
    raw = json.dumps(canonical, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cognitive_label(value: str) -> str:
    upper = str(value).upper()
    for key, label in COGNITIVE_LABELS.items():
        if key in upper:
            return label
    return ""


def build_deterministic_skill_analysis(
    payload: StudentSkillAnalysisRequest,
    major_name: Optional[str] = None,
) -> Tuple[str, List[InsightPoint], List[InsightPoint], List[SkillGapItem]]:
    """Phân tích tất định từ dữ liệu bài test - luôn chạy được, không tốn token."""
    riasec = {k: float(v) for k, v in (payload.riasec_scores or {}).items() if k in RIASEC_LABELS}
    sorted_dims = sorted(riasec.items(), key=lambda kv: kv[1], reverse=True)
    top_dims = [d for d, score in sorted_dims[:2] if score > 0] or ["I"]
    low_dims = [d for d, score in sorted_dims[-2:] if score > 0] or ["C"]

    strengths: List[InsightPoint] = []
    for dim in top_dims[:2]:
        label = RIASEC_LABELS[dim]
        score_pct = round(riasec.get(dim, 0) * 100)
        strengths.append(
            InsightPoint(
                title=f"Mạnh về {label.split('(')[0].strip().lower()}",
                detail=f"Điểm sở thích {dim} đạt {score_pct}% - bạn học tốt khi nội dung gắn với sở thích này.",
            )
        )

    grades = {k: float(v) for k, v in (payload.grades_by_subject or {}).items()}
    if grades:
        best_subject, best_score = max(grades.items(), key=lambda kv: kv[1])
        strengths.append(
            InsightPoint(
                title=f"Học tốt môn {best_subject}",
                detail=f"Điểm {best_score:g} cho thấy nền tảng môn này khá vững, có thể dùng làm lợi thế khi chọn tổ hợp.",
            )
        )

    learning_style = _cognitive_label(str(payload.cognitive_preferences.get("learning_style", "")))
    if learning_style and len(strengths) < 3:
        strengths.append(
            InsightPoint(title="Biết cách học phù hợp", detail=f"Bạn {learning_style}; nên học theo đúng cách này để nhớ lâu hơn.")
        )
    while len(strengths) < 2:
        strengths.append(
            InsightPoint(title="Có sở thích nghề nghiệp rõ ràng", detail="Bài test đã cho thấy nhóm ngành bạn thực sự quan tâm.")
        )

    weaknesses: List[InsightPoint] = []
    for dim in low_dims[:2]:
        label = RIASEC_LABELS[dim].split("(")[0].strip().lower()
        weaknesses.append(
            InsightPoint(
                title=f"Còn yếu phần {label}",
                detail=f"Nhóm {dim} có điểm thấp nhất. Bài tập cần sự {label} sẽ tốn thời gian hơn mức trung bình.",
            )
        )
    if grades:
        worst_subject, worst_score = min(grades.items(), key=lambda kv: kv[1])
        weaknesses.append(
            InsightPoint(
                title=f"Môn {worst_subject} cần củng cố",
                detail=f"Điểm {worst_score:g} thấp nhất trong học bạ; nên ôn lại kiến thức gốc trước khi học phần nâng cao.",
            )
        )

    skill_gaps: List[SkillGapItem] = []
    for idx, dim in enumerate(top_dims[:2] + low_dims[:1]):
        hint = RIASEC_SKILL_HINTS.get(dim)
        if not hint:
            continue
        skill, why, how = hint
        skill_gaps.append(
            SkillGapItem(
                skill=skill,
                why=why,
                how_to_improve=how,
                priority="HIGH" if idx == 0 else ("MEDIUM" if idx == 1 else "LOW"),
            )
        )

    if grades and min(grades.values()) < 7.0:
        subject = min(grades.items(), key=lambda kv: kv[1])[0]
        skill_gaps.append(
            SkillGapItem(
                skill=f"Nền tảng môn {subject}",
                why="Điểm dưới 7.0 dễ làm chậm các học phần chuyên ngành.",
                how_to_improve=["Ôn lại 1 chương mỗi tuần và làm đề kiểm tra 20 phút", "Nhờ giáo viên chỉ rõ phần đang mất gốc"],
                priority="HIGH",
            )
        )

    if len(skill_gaps) < 3:
        skill_gaps.append(
            SkillGapItem(
                skill="Tiếng Anh chuyên ngành",
                why="Tài liệu và công cụ tốt nhất của ngành hầu hết bằng tiếng Anh.",
                how_to_improve=["Học 10 từ chuyên ngành mỗi ngày", "Đọc 1 trang tài liệu tiếng Anh mỗi tuần"],
                priority="MEDIUM",
            )
        )

    priority_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    skill_gaps.sort(key=lambda gap: priority_rank.get(gap.priority, 1))

    major_text = f" cho ngành {major_name}" if major_name else ""
    summary = (
        f"Bạn mạnh về {RIASEC_LABELS[top_dims[0]].split('(')[0].strip().lower()} và cần bổ sung "
        f"{skill_gaps[0].skill.lower()}{major_text}. "
        f"Ưu tiên 4 tuần tới: học đúng cách phù hợp và lấp 1 kỹ năng yếu nhất."
    )

    return summary, strengths[:3], weaknesses[:3], skill_gaps[:4]


async def _generate_skill_analysis_with_ai(
    payload: StudentSkillAnalysisRequest,
    major_name: Optional[str],
) -> Optional[Tuple[str, List[InsightPoint], List[InsightPoint], List[SkillGapItem]]]:
    system_prompt = (
        "Bạn là cố vấn học tập cho học sinh THPT Việt Nam. Bạn nói ngắn, thẳng, dễ hiểu, "
        "không phán xét và không dùng thuật ngữ khó. Trả về JSON hợp lệ."
    )
    profile = {
        "riasec": payload.riasec_scores,
        "grades_by_subject": payload.grades_by_subject,
        "cognitive_preferences": payload.cognitive_preferences,
        "dominant_traits": payload.dominant_traits,
        "aspiration": payload.aspiration or {},
    }
    user_prompt = (
        f"HỒ SƠ HỌC SINH (đã ẩn danh, chỉ gồm số liệu bài test):\n"
        f"{json.dumps(profile, ensure_ascii=False)}\n\n"
        f"NGÀNH MỤC TIÊU: {major_name or 'chưa chọn cụ thể'}\n\n"
        "Hãy phân tích cách học của học sinh. QUY TẮC BẮT BUỘC:\n"
        "1. Mỗi câu tối đa 20 từ, không lan man, không lặp ý.\n"
        "2. 'summary': 2 câu, nêu điểm mạnh nhất và việc cần làm trước tiên.\n"
        "3. 'strengths': đúng 3 mục, mỗi mục 'title' ngắn (<=8 từ) + 'detail' 1 câu.\n"
        "4. 'weaknesses': đúng 3 mục, nói thẳng điểm yếu nhưng kèm hướng khắc phục trong 'detail'.\n"
        "5. 'skill_gaps': 3 mục kỹ năng cần bổ sung, mỗi mục có 'why' 1 câu và "
        "'how_to_improve' 2 việc làm được ngay trong 1-2 tuần.\n"
        "6. 'priority' chỉ nhận HIGH, MEDIUM hoặc LOW.\n"
        "7. Không nhắc tên, trường, địa chỉ hay thông tin cá nhân.\n\n"
        "Trả về đúng JSON:\n"
        "{\n"
        '  "summary": "...",\n'
        '  "strengths": [{"title": "...", "detail": "..."}],\n'
        '  "weaknesses": [{"title": "...", "detail": "..."}],\n'
        '  "skill_gaps": [{"skill": "...", "why": "...", "how_to_improve": ["...", "..."], "priority": "HIGH"}]\n'
        "}"
    )

    data = await _call_llm_json(system_prompt, user_prompt, max_tokens=2500)
    if not data:
        return None

    summary = str(data.get("summary") or "").strip()
    if not summary:
        return None

    def _points(raw: Any) -> List[InsightPoint]:
        points: List[InsightPoint] = []
        for item in (raw or [])[:4]:
            if isinstance(item, str) and item.strip():
                points.append(InsightPoint(title=item.strip()[:90], detail=""))
            elif isinstance(item, dict):
                title = str(item.get("title") or "").strip()
                if title:
                    points.append(
                        InsightPoint(title=title[:90], detail=str(item.get("detail") or "").strip()[:260])
                    )
        return points

    strengths = _points(data.get("strengths"))
    weaknesses = _points(data.get("weaknesses"))

    gaps: List[SkillGapItem] = []
    for item in (data.get("skill_gaps") or [])[:4]:
        if not isinstance(item, dict):
            continue
        skill = str(item.get("skill") or "").strip()
        if not skill:
            continue
        priority = str(item.get("priority") or "MEDIUM").upper()
        if priority not in ("HIGH", "MEDIUM", "LOW"):
            priority = "MEDIUM"
        gaps.append(
            SkillGapItem(
                skill=skill[:90],
                why=str(item.get("why") or "").strip()[:240],
                how_to_improve=_as_str_list(item.get("how_to_improve"), limit=3),
                priority=priority,
            )
        )

    if not (strengths and weaknesses and gaps):
        return None
    return summary[:600], strengths, weaknesses, gaps


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


async def analyze_student_skills(
    db: Optional[AsyncSession],
    payload: StudentSkillAnalysisRequest,
    user_id: Optional[uuid.UUID] = None,
) -> StudentSkillAnalysisResponse:
    """
    Cache theo (profile_hash, major_code): một hồ sơ + một ngành chỉ gọi AI một lần.
    """
    major_code = (payload.major_code or "").strip()
    profile_hash = _profile_hash(payload)

    if db is not None:
        try:
            stmt = select(StudentSkillInsight).where(
                StudentSkillInsight.profile_hash == profile_hash,
                StudentSkillInsight.major_code == major_code,
            )
            cached_entry = (await db.execute(stmt)).scalar_one_or_none()
            if cached_entry:
                return _to_skill_response(cached_entry, cached=True)
        except Exception as exc:
            logger.warning("[SkillAgent] Cache read failed: %s", exc)

    major_name: Optional[str] = None
    if major_code:
        ctx = await _load_major_context(db, major_code)
        major_name = ctx.get("name")

    ai_result = await _generate_skill_analysis_with_ai(payload, major_name)
    if ai_result:
        summary, strengths, weaknesses, gaps = ai_result
        is_ai = True
    else:
        summary, strengths, weaknesses, gaps = build_deterministic_skill_analysis(payload, major_name)
        is_ai = False

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

    try:
        stmt = select(StudentSkillInsight).where(
            StudentSkillInsight.profile_hash == profile_hash,
            StudentSkillInsight.major_code == major_code,
        )
        entry = (await db.execute(stmt)).scalar_one_or_none()
        payload_data = {
            "user_id": user_id,
            "summary": summary,
            "strengths": [p.model_dump() for p in strengths],
            "weaknesses": [p.model_dump() for p in weaknesses],
            "skill_gaps": [g.model_dump() for g in gaps],
            "is_ai_generated": is_ai,
            "model_name": settings.LLM_MODEL if is_ai else None,
        }
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
        return _to_skill_response(entry, cached=False)
    except Exception as exc:
        logger.warning("[SkillAgent] Persist failed: %s", exc)
        try:
            await db.rollback()
        except Exception:
            pass
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
