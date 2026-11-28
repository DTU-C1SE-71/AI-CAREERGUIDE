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
        yield "Chào em, "
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
                "Chào em, ",
                "ngành An toàn thông tin ",
                "rất phù hợp với tư duy phân tích.",
            ]
            assert len(dones) == 1
            assert dones[0]["is_ai_generated"] is True
            assert dones[0]["reply"] == "Chào em, ngành An toàn thông tin rất phù hợp với tư duy phân tích."
            assert dones[0]["session_id"] is not None
    finally:
        app.dependency_overrides.pop(get_db, None)
        await engine.dispose()
