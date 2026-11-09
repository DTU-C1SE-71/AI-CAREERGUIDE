import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.database import AsyncSessionLocal
from app.modules.assessment.models import (
    AssessmentQuestionSet,
    AssessmentQuestion,
    CognitiveQuestionOption,
)

logger = logging.getLogger(__name__)


def load_raw_seed_data() -> dict:
    """Loads standardized v1.8 assessment questionnaire JSON."""
    json_path = Path(__file__).resolve().parent / "assessment_questions_v1_8.json"
    if not json_path.exists():
        fallback_path = Path(r"c:\Users\dyysi\Downloads\ng_n_h_ng_c_u_h_i_nh_gi_ai_careerguide.md")
        if fallback_path.exists():
            raw_text = fallback_path.read_text(encoding="utf-8")
            cleaned = raw_text.replace(r"\[", "[").replace(r"\]", "]")
            return json.loads(cleaned)
        raise FileNotFoundError(f"Assessment seed file not found at {json_path}")
    
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


async def seed_assessment_questions(session: AsyncSession) -> AssessmentQuestionSet:
    """
    Seeds the official Circular 74/2026/TT-BGDĐT v1.8 vocational assessment question set:
    - 30 RIASEC items across 6 vocational domains (5 items/domain)
    - 8 Cognitive Preference questions with 32 structured options (A, B, C, D)
    - Complete metadata, XP rewards, and MOET 2-digit field codes.
    """
    raw_data = load_raw_seed_data()
    set_code = "RIASEC_COG_V1_8"
    version = raw_data.get("version", "1.8")
    circular_ref = raw_data.get("circular_ref", "74/2026/TT-BGDĐT")

    # Check if this set already exists
    stmt = select(AssessmentQuestionSet).where(AssessmentQuestionSet.set_code == set_code)
    result = await session.execute(stmt)
    existing_set = result.scalar_one_or_none()

    if existing_set:
        logger.info(f"Questionnaire set '{set_code}' already exists (ID: {existing_set.id}). Ensuring is_active=True.")
        existing_set.is_active = True
        await session.commit()
        return existing_set

    logger.info(f"Seeding new Questionnaire Set '{set_code}' v{version}...")

    # 1. Create AssessmentQuestionSet
    question_set = AssessmentQuestionSet(
        id=uuid.uuid4(),
        set_code=set_code,
        version=version,
        title="Bộ câu hỏi Đánh giá Sở thích & Thiên hướng Nhận thức chuẩn v1.8",
        description="Khung đánh giá trắc nghiệm sở thích nghề nghiệp Holland RIASEC (30 câu) kết hợp 8 chiều thiên hướng nhận thức và môi trường học tập theo Thông tư 74/2026/TT-BGDĐT.",
        circular_ref=circular_ref,
        config=raw_data.get("config", {
            "xp_per_question": 25,
            "completion_bonus_xp": 200,
            "estimated_minutes": 6,
            "questions_per_riasec_page": 5,
            "total_riasec_questions": 30,
            "total_cognitive_questions": 8,
            "weights": {"riasec": 0.45, "academic": 0.35, "cognitive_preference": 0.20}
        }),
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    session.add(question_set)
    await session.flush()

    # 2. Seed 30 RIASEC Questions
    riasec_items = raw_data.get("riasec_questions", [])
    for item in riasec_items:
        q_obj = AssessmentQuestion(
            id=uuid.uuid4(),
            set_id=question_set.id,
            code=item["code"],
            category="RIASEC",
            dimension=item["dimension"],
            dimension_badge=item.get("dimension_badge", f"Nhóm {item['dimension']}"),
            domain_tag=item.get("domain_tag"),
            icon_name=item.get("icon_name", "BrainCircuit"),
            question_text=item["question_text"],
            order_index=item.get("order", 1),
            xp_reward=25,
            is_active=True
        )
        session.add(q_obj)

    # 3. Seed 8 Cognitive Questions & 32 Options
    cognitive_items = raw_data.get("cognitive_questions", [])
    for cog_item in cognitive_items:
        q_obj = AssessmentQuestion(
            id=uuid.uuid4(),
            set_id=question_set.id,
            code=cog_item["code"],
            category="COGNITIVE",
            dimension=cog_item["dimension_key"],
            dimension_badge=cog_item.get("title", f"Thiên hướng {cog_item['code']}"),
            domain_tag="Thiên hướng Nhận thức & Phong cách Học tập",
            icon_name="BrainCircuit",
            question_text=f"{cog_item['title']}: {cog_item.get('subtitle', '')}",
            order_index=cog_item.get("order", 1),
            xp_reward=25,
            is_active=True
        )
        session.add(q_obj)
        await session.flush()

        # Seed 4 options per cognitive item
        options = cog_item.get("options", [])
        for opt_idx, opt in enumerate(options, start=1):
            option_obj = CognitiveQuestionOption(
                id=uuid.uuid4(),
                question_id=q_obj.id,
                option_key=opt["option_key"],
                trait_code=opt["trait_code"],
                title=opt["title"],
                description=opt["description"],
                related_moet_field_codes=opt.get("related_moet_field_codes", []),
                order_index=opt_idx
            )
            session.add(option_obj)

    await session.commit()
    logger.info(
        f"Successfully seeded '{set_code}' with {len(riasec_items)} RIASEC questions and {len(cognitive_items)} Cognitive questions (32 options)."
    )
    return question_set


async def main():
    logging.basicConfig(level=logging.INFO)
    print("Connecting to database to seed assessment questions...")
    try:
        async with AsyncSessionLocal() as session:
            q_set = await seed_assessment_questions(session)
            print(f"Seed completed successfully! QuestionSet ID: {q_set.id}")
    except Exception as e:
        print(f"Database offline or seed error: {e}")
        print("Note: In offline fallback mode, the backend service uses the embedded v1.8 JSON directly.")


if __name__ == "__main__":
    asyncio.run(main())
