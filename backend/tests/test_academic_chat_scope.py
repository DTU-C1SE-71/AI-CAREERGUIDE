"""@blast-radius: core — short academic questions are valid chat requests."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.schemas.rag import AIChatRequest
from app.services.ai_config import adapter, service as config_service
from app.services.llamaindex_rag_orchestrator import counselor_connection, guidance_boundary, guidance_rag


@pytest.fixture
def connected_academic_chat(monkeypatch):
    # The connection was checked when chat opened; these tests never probe a provider.
    monkeypatch.setattr(counselor_connection, "verify_receipt", AsyncMock(return_value=True))
    monkeypatch.setattr(config_service, "resolve_snapshot", AsyncMock(return_value=SimpleNamespace()))
    generate = AsyncMock(return_value="ACADEMIC_ANSWER")
    monkeypatch.setattr(adapter, "chat", generate)
    return generate


@pytest.mark.asyncio
@pytest.mark.parametrize("major_code", [None, "7480107"])
@pytest.mark.parametrize("message", [
    "phép chia là gì",
    "code python là gì",
    "code python hệ pt bậc 2",
    "1+1=",
])
async def test_reported_academic_questions_are_answered_with_or_without_selected_major(
    connected_academic_chat, major_code, message,
):
    answer = await guidance_rag.chat_with_career_counselor(None, AIChatRequest(
        message=message, major_code=major_code, connection_revision="s" * 65,
    ))

    assert answer.is_ai_generated is True
    assert answer.reply == "ACADEMIC_ANSWER"
    connected_academic_chat.assert_awaited_once()
    # The real question must reach generation, rather than just a career summary.
    assert connected_academic_chat.await_args.args[1][-1] == {"role": "user", "content": message}


@pytest.mark.asyncio
@pytest.mark.parametrize("message", [
    "phep chia la gi",
    "phân số là gì",
    "pt bậc2 giải ntn",
    "định lý Pytago là gì",
    "phản ứng hóa học là gì",
    "ngữ pháp thì hiện tại đơn",
    "C++ con trỏ là gì",
    "JavaScript promise là gì",
    "vòng lặp for trong Python hoạt động thế nào",
    "2 × (3 + 4) = ?",
    "x² - 5x + 6 = 0",
    "1+1 bằng mấy?",
    "2 + 3 = bao nhiêu",
    "5 trừ 2 bằng mấy",
    "giải pt x^2 - 4 = 0",
    "em cần ôn lại phép tính 1+1",
    "code PHP là gì",
    "hàm trong C là gì",
    "so sánh JSON và XML",
])
async def test_school_concepts_programming_and_math_notation_reach_generation(connected_academic_chat, message):
    answer = await guidance_rag.chat_with_career_counselor(None, AIChatRequest(
        message=message, connection_revision="s" * 65,
    ))

    assert answer.is_ai_generated is True
    assert answer.reply == "ACADEMIC_ANSWER"
    connected_academic_chat.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("message", [
    "vậy còn phép nhân?",
    "cho ví dụ bằng python",
    "cụ thể hơn?",
    "tại sao lại như vậy",
])
async def test_academic_followups_keep_the_related_user_context(connected_academic_chat, message):
    answer = await guidance_rag.chat_with_career_counselor(None, AIChatRequest(
        message=message, connection_revision="s" * 65,
        history=[
            {"role": "user", "content": "phép chia là gì"},
            {"role": "assistant", "content": "Phép chia cho biết mỗi nhóm có bao nhiêu phần tử."},
        ],
    ))

    assert answer.is_ai_generated is True
    connected_academic_chat.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("message", [
    "Python viết công thức nấu mì cho tôi",
    "C++ thời tiết hôm nay thế nào?",
    "phép cộng và số xổ số hôm nay",
    "asdf qwer",
])
async def test_study_history_or_selected_major_does_not_authorize_unrelated_requests(connected_academic_chat, message):
    answer = await guidance_rag.chat_with_career_counselor(None, AIChatRequest(
        message=message, major_code="7480107", connection_revision="s" * 65,
        history=[
            {"role": "user", "content": "code python là gì"},
            {"role": "assistant", "content": "Python là một ngôn ngữ lập trình."},
        ],
    ))

    assert answer.is_ai_generated is False
    assert answer.reply.strip()
    assert answer.connection_available is True
    connected_academic_chat.assert_not_awaited()


@pytest.mark.asyncio
async def test_assistant_education_boilerplate_cannot_authorize_unclear_followup(connected_academic_chat):
    answer = await guidance_rag.chat_with_career_counselor(None, AIChatRequest(
        message="cụ thể hơn?", connection_revision="s" * 65,
        history=[
            {"role": "user", "content": "asdf qwer"},
            {"role": "assistant", "content": "Bạn hãy hỏi rõ hơn về học tập, ngành học hoặc mục tiêu nghề nghiệp."},
        ],
    ))

    assert answer.is_ai_generated is False
    connected_academic_chat.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("message", [
    "phép chia là gì",
    "code python là gì",
    "code python hệ pt bậc 2",
    "1+1=",
    "Phân tích hình tượng sóng trong bài thơ Sóng của Xuân Quỳnh",
    "Giải thích xác suất trúng xổ số trong bài tập xác suất",
    "hàm lượng giác là gì",
    "khối lượng và trọng lượng khác nhau thế nào",
    "định luật bảo toàn năng lượng là gì",
])
async def test_pure_tutoring_ignores_selected_major_and_does_not_score_private_profile(
    monkeypatch, connected_academic_chat, message,
):
    facts = AsyncMock(side_effect=AssertionError("Pure tutoring must not load or score a career profile"))
    monkeypatch.setattr(guidance_boundary, "guidance_facts", facts)

    answer = await guidance_rag.chat_with_career_counselor(None, AIChatRequest(
        message=message, major_code="7480107", connection_revision="s" * 65,
    ))

    assert answer.is_ai_generated is True
    facts.assert_not_awaited()
    connected_academic_chat.assert_awaited_once()
    sent = connected_academic_chat.await_args.args[1]
    system_prompt = "\n".join(item["content"] for item in sent if item["role"] == "system")
    assert "[DỮ LIỆU THAM CHIẾU HỆ THỐNG]" not in system_prompt
    assert "Mức khớp sở thích" not in system_prompt
    assert sent[-1] == {"role": "user", "content": message}


@pytest.mark.asyncio
async def test_mixed_learning_and_career_question_keeps_profile_grounding(monkeypatch, connected_academic_chat):
    facts = AsyncMock(wraps=guidance_boundary.guidance_facts)
    monkeypatch.setattr(guidance_boundary, "guidance_facts", facts)
    message = "Em nên học Python thế nào để làm kỹ sư AI?"

    answer = await guidance_rag.chat_with_career_counselor(None, AIChatRequest(
        message=message, major_code="7480107", connection_revision="s" * 65,
    ))

    assert answer.is_ai_generated is True
    facts.assert_awaited_once()
    connected_academic_chat.assert_awaited_once()
    assert connected_academic_chat.await_args.args[1][-1] == {"role": "user", "content": message}


@pytest.mark.asyncio
async def test_requesting_actual_lottery_numbers_is_not_probability_tutoring(connected_academic_chat):
    answer = await guidance_rag.chat_with_career_counselor(None, AIChatRequest(
        message="Cho em số xổ số hôm nay", connection_revision="s" * 65,
        history=[{"role": "user", "content": "Giải thích xác suất trúng xổ số trong bài tập xác suất"}],
    ))

    assert answer.is_ai_generated is False
    connected_academic_chat.assert_not_awaited()
