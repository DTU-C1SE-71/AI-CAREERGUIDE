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
    Seeds the official Circular 74/2026/TT-BGDĐT v2.0 vocational assessment question set:
    - 30 RIASEC items across 6 vocational domains (5 items/domain)
    - 10 Cognitive & Learning Environment questions (PA3-10)
    - Complete metadata, XP rewards, and MOET 2-digit field codes.
    """
    raw_data = load_raw_seed_data()
    set_code = "RIASEC_COG_V2_10"
    version = raw_data.get("version", "2.0")
    circular_ref = raw_data.get("circular_ref", "74/2026/TT-BGDĐT")

    # Deactivate older questionnaire sets without deleting them so historical submissions stay valid
    other_sets_res = await session.execute(
        select(AssessmentQuestionSet).where(AssessmentQuestionSet.set_code != set_code)
    )
    for old_set in other_sets_res.scalars().all():
        old_set.is_active = False

    # Check if this set already exists
    stmt = select(AssessmentQuestionSet).where(AssessmentQuestionSet.set_code == set_code)
    result = await session.execute(stmt)
    existing_set = result.scalar_one_or_none()

    if existing_set:
        logger.info(f"Questionnaire set '{set_code}' already exists (ID: {existing_set.id}). Synchronizing latest question texts...")
        existing_set.is_active = True
        existing_set.version = version
        existing_set.config = raw_data.get("config", existing_set.config)
        existing_set.updated_at = datetime.now(timezone.utc)

        # Load existing questions for this set
        q_res = await session.execute(
            select(AssessmentQuestion).where(AssessmentQuestion.set_id == existing_set.id)
        )
        existing_q_map = {q.code: q for q in q_res.scalars().all()}

        # Sync 30 RIASEC questions in-place
        for item in raw_data.get("riasec_questions", []):
            q_obj = existing_q_map.get(item["code"])
            if q_obj:
                q_obj.question_text = item["question_text"]
                q_obj.dimension_badge = item.get("dimension_badge", q_obj.dimension_badge)
                q_obj.domain_tag = item.get("domain_tag", q_obj.domain_tag)

        # Sync 10 Cognitive questions & their options cleanly
        for cog_item in raw_data.get("cognitive_questions", []):
            q_obj = existing_q_map.get(cog_item["code"])
            if q_obj:
                q_obj.dimension = cog_item["dimension_key"]
                q_obj.dimension_badge = cog_item.get("title", q_obj.dimension_badge)
                q_obj.question_text = cog_item.get("subtitle", "")
                q_obj.order_index = cog_item.get("order", q_obj.order_index)
                opt_res = await session.execute(
                    select(CognitiveQuestionOption).where(CognitiveQuestionOption.question_id == q_obj.id)
                )
                existing_opt_map = {o.option_key: o for o in opt_res.scalars().all()}
                new_keys = set()
                for opt_idx, opt in enumerate(cog_item.get("options", []), start=1):
                    new_keys.add(opt["option_key"])
                    opt_obj = existing_opt_map.get(opt["option_key"])
                    if opt_obj:
                        opt_obj.trait_code = opt["trait_code"]
                        opt_obj.title = opt["title"]
                        opt_obj.description = opt["description"]
                        opt_obj.order_index = opt_idx
                    else:
                        session.add(
                            CognitiveQuestionOption(
                                id=uuid.uuid4(),
                                question_id=q_obj.id,
                                option_key=opt["option_key"],
                                trait_code=opt["trait_code"],
                                title=opt["title"],
                                description=opt["description"],
                                related_moet_field_codes=opt.get("related_moet_field_codes", []),
                                order_index=opt_idx,
                            )
                        )
                for key, old_opt in existing_opt_map.items():
                    if key not in new_keys:
                        await session.delete(old_opt)

        await session.commit()
        return existing_set

    logger.info(f"Seeding new Questionnaire Set '{set_code}' v{version}...")

    # 1. Create AssessmentQuestionSet
    question_set = AssessmentQuestionSet(
        id=uuid.uuid4(),
        set_code=set_code,
        version=version,
        title="Bộ câu hỏi Đánh giá Sở thích & Phong cách Tư duy chuẩn v2.0",
        description="Khung đánh giá trắc nghiệm sở thích nghề nghiệp Holland RIASEC (30 câu) kết hợp 10 câu phong cách tư duy và môi trường học tập theo Thông tư 74/2026/TT-BGDĐT.",
        circular_ref=circular_ref,
        config=raw_data.get("config", {
            "xp_per_question": 25,
            "completion_bonus_xp": 200,
            "estimated_minutes": 6,
            "questions_per_riasec_page": 5,
            "total_riasec_questions": 30,
            "total_cognitive_questions": 10,
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

    # 3. Seed 10 Cognitive Questions & Options
    cognitive_items = raw_data.get("cognitive_questions", [])
    for cog_item in cognitive_items:
        q_obj = AssessmentQuestion(
            id=uuid.uuid4(),
            set_id=question_set.id,
            code=cog_item["code"],
            category="COGNITIVE",
            dimension=cog_item["dimension_key"],
            dimension_badge=cog_item.get("title", f"Câu {cog_item.get('order', 1)}"),
            domain_tag="Phong cách Tư duy & Môi trường Học tập",
            icon_name="BrainCircuit",
            question_text=cog_item.get("subtitle", ""),
            order_index=cog_item.get("order", 1),
            xp_reward=25,
            is_active=True
        )
        session.add(q_obj)
        await session.flush()

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
        f"Successfully seeded '{set_code}' with {len(riasec_items)} RIASEC questions and {len(cognitive_items)} Cognitive questions."
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
