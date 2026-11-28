from types import SimpleNamespace
import json
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.database import Base, get_db
from app.core.security import get_password_hash, create_access_token
from app.models.identity import User, UserRole
from app.core.ai_runtime import ConfigSnapshot
from app.schemas.rag import AIChatRequest
from app.services.ai_config import adapter
from app.services.llamaindex_rag_orchestrator.chat_scope import local_scope_reply
from app.services.llamaindex_rag_orchestrator.guidance_rag import _build_counselor_messages
from app.services.llamaindex_rag_orchestrator.system_help import SECURITY_REFUSAL, SYSTEM_HELP_PROMPT


@pytest.mark.asyncio
async def test_chat_stream_requires_auth_and_streams_sse(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    student_id = uuid.uuid4()
    async with SessionLocal() as db:
        db.add(
            User(
                id=student_id,
                email="stream_student@example.com",
                full_name="Stream Student",
                hashed_password=get_password_hash("StrongPass!123"),
                role=UserRole.STUDENT,
                is_active=True,
            )
        )
        await db.commit()

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async def fake_verify_receipt(_db, _rev):
        return True

    async def fake_resolve_snapshot(_db):
        return SimpleNamespace(model="qwen/qwen3.8-max:free")

    async def fake_chat_stream(_snapshot, _messages, **_kwargs):
        yield "Chào bạn, "
        yield "ngành An toàn thông tin "
        yield "rất phù hợp với tư duy phân tích."

    monkeypatch.setattr(
        "app.services.llamaindex_rag_orchestrator.counselor_connection.verify_receipt",
        fake_verify_receipt,
    )
    monkeypatch.setattr("app.services.ai_config.service.resolve_snapshot", fake_resolve_snapshot)
    monkeypatch.setattr("app.services.ai_config.adapter.chat_stream", fake_chat_stream)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Guest must be rejected with 401
            guest_res = await client.post(
                "/api/v1/rag-governance/chat/stream",
                json={"message": "Ngành An toàn thông tin học gì?"},
            )
            assert guest_res.status_code == 401

            # 2. Logged-in student receives real-time SSE deltas + final done metadata
            token = create_access_token(str(student_id), "STUDENT")
            res = await client.post(
                "/api/v1/rag-governance/chat/stream",
                headers={"Authorization": f"Bearer {token}"},
                json={"message": "Ngành An toàn thông tin học gì?"},
            )
            assert res.status_code == 200
            assert "text/event-stream" in res.headers.get("content-type", "")

            events = []
            for frame in res.text.split("\n\n"):
                frame = frame.strip()
                if frame.startswith("data:"):
                    events.append(json.loads(frame[5:].strip()))

            deltas = [e["content"] for e in events if e.get("type") == "delta"]
            dones = [e["data"] for e in events if e.get("type") == "done"]
            assert deltas == [
                "Chào bạn, ",
                "ngành An toàn thông tin ",
                "rất phù hợp với tư duy phân tích.",
            ]
            assert len(dones) == 1
            assert dones[0]["is_ai_generated"] is True
            assert dones[0]["reply"] == "Chào bạn, ngành An toàn thông tin rất phù hợp với tư duy phân tích."
            assert dones[0]["session_id"] is not None
    finally:
        app.dependency_overrides.pop(get_db, None)
        await engine.dispose()


@pytest.mark.asyncio
async def test_xkiro_interleaved_sse_workaround_and_progressive_chunks(monkeypatch):
    xkiro_snapshot = ConfigSnapshot(
        source_mode="ENV",
        protocol="openai_compatible",
        canonical_base_url="https://api.xkiro.com/v1",
        model="qwen/qwen3.8-max:free",
        auth_mode="BEARER",
        credential_binding=("openai_compatible", "https", "api.xkiro.com", 443, "/v1"),
        revision_token="rev-1",
        credential="sk-test-secret",
        embedding_model="text-embedding-3-small",
    )
    assert adapter._provider_has_interleaved_sse_bug(xkiro_snapshot) is True

    markdown_answer = "Chào bạn,\n\n- **Kỹ thuật phần mềm** tập trung vào thiết kế & kiểm thử.\n- Mình luôn đồng hành cùng bạn!"
    called = {"count": 0}

    async def fake_chat(snapshot, messages, *, max_tokens=1024, timeout=20, response_format=None):
        called["count"] += 1
        assert snapshot is xkiro_snapshot
        assert response_format is None
        return markdown_answer

    monkeypatch.setattr(adapter, "chat", fake_chat)

    pieces = []
    async for piece in adapter.chat_stream(
        xkiro_snapshot,
        [{"role": "user", "content": "Hỏi ngành"}],
        max_tokens=1600,
        timeout=30.0,
    ):
        pieces.append(piece)

    assert called["count"] == 1
    assert len(pieces) > 1
    assert "".join(pieces) == markdown_answer


@pytest.mark.asyncio
async def test_native_sse_stream_pins_stream_id_and_primary_choice(monkeypatch):
    other_snapshot = ConfigSnapshot(
        source_mode="ENV",
        protocol="openai_compatible",
        canonical_base_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
        auth_mode="BEARER",
        credential_binding=("openai_compatible", "https", "api.openai.com", 443, "/v1"),
        revision_token="rev-2",
        credential="sk-test-secret",
        embedding_model="text-embedding-3-small",
    )
    assert adapter._provider_has_interleaved_sse_bug(other_snapshot) is False

    sse_lines = [
        'data: {"id":"cmpl-1","choices":[{"index":0,"delta":{"content":"Chào "},"finish_reason":null}]}',
        'data: {"id":"cmpl-2","choices":[{"index":0,"delta":{"content":"XEN_NGANG "},"finish_reason":null}]}',
        'data: {"id":"cmpl-1","choices":[{"index":1,"delta":{"content":"NHIEU_IDX "},"finish_reason":null}]}',
        'data: {"id":"cmpl-1","choices":[{"index":0,"delta":{"content":"bạn!"},"finish_reason":null}]}',
        'data: {"id":"cmpl-1","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}',
        'data: {"id":"cmpl-1","choices":[{"index":0,"delta":{"content":"SAU_STOP"},"finish_reason":null}]}',
        "data: [DONE]",
    ]

    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def aiter_lines(self):
            for line in sse_lines:
                yield line

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(adapter, "resolve_target_addresses", lambda *args, **kwargs: ["127.0.0.1"])
    monkeypatch.setattr(adapter.httpx, "AsyncClient", FakeClient)

    pieces = []
    async for piece in adapter.chat_stream(
        other_snapshot,
        [{"role": "user", "content": "Chào"}],
        max_tokens=200,
        timeout=20.0,
    ):
        pieces.append(piece)

    assert "".join(pieces) == "Chào bạn!"


def test_ai_persona_standardized_minh_ban():
    for text in (
        local_scope_reply("greeting"),
        local_scope_reply("clarify"),
        SYSTEM_HELP_PROMPT,
        SECURITY_REFUSAL,
    ):
        assert "mình" in text.lower()
        assert "bạn" in text.lower()
        assert "thầy/cô" not in text.lower()
        assert "giáo viên cố vấn" not in text.lower()

    payload = AIChatRequest(message="Ngành Kỹ thuật phần mềm học gì?")
    for system_help, academic in ((False, False), (True, False), (False, True)):
        msgs = _build_counselor_messages(payload, "Dữ liệu mẫu", "Ngắn gọn", system_help, academic)
        sys_msg = msgs[0]["content"]
        assert '"mình"' in sys_msg
        assert '"bạn"' in sys_msg
        assert "thầy/cô" not in sys_msg.lower()
        assert "giáo viên cố vấn" not in sys_msg.lower()
