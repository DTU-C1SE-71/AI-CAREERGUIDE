"""@blast-radius: core, api, db, integration
Hợp đồng cấu hình AI chỉ đọc từ ENV/.env, endpoint quản trị chỉ đọc, và adapter HTTP loopback thật.
"""
import asyncio
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import FrozenInstanceError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.core.config import settings
from app.core.ai_runtime import AIConfigError, canonical_target, resolve_target_addresses, validate_model
from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.models.identity import User, UserRole
from app.services.ai_config import service, adapter
from app.services.ai_config.router import router


SECRET_A = "sk-synth-test-only-00001234"
SECRET_B = "sk-synth-test-only-00005678"


class Stub:
    def __init__(self):
        self.received = []
        self.received_condition = threading.Condition()
        self.status = 200
        self.payload = None
        self.redirect = None
        self.responses = []
        self.entered = threading.Event()
        self.release = None
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))) or b"{}")
                with owner.received_condition:
                    owner.received.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
                    owner.received_condition.notify_all()
                    if owner.responses:
                        status, payload, redirect = owner.responses.pop(0)
                    else:
                        status, payload, redirect = owner.status, owner.payload, owner.redirect
                owner.entered.set()
                if owner.release is not None:
                    owner.release.wait(5)
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                if redirect:
                    self.send_header("Location", redirect)
                self.end_headers()
                final_payload = payload if payload is not None else {"choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}]}
                try:
                    self.wfile.write(json.dumps(final_payload).encode())
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass  # Client hết deadline đã đóng kết nối đúng thiết kế.

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/team-a/v1"

    def close(self):
        if self.release:
            self.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)


@pytest.fixture
def stubs(monkeypatch):
    a, b = Stub(), Stub()
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    monkeypatch.setattr(settings, "AI_LOCAL_ALLOWED_BASE_URLS", [a.url, b.url, a.url.replace("/team-a/", "/team-b/")])
    try:
        yield a, b
    finally:
        a.close()
        b.close()


@pytest_asyncio.fixture
async def db_factory(tmp_path, monkeypatch):
    path = tmp_path / "ai-config-isolated.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{path.as_posix()}")
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    monkeypatch.setattr(settings, "LLM_BASE_URL", "https://example.org/v1")
    monkeypatch.setattr(settings, "LLM_MODEL", "env-model")
    monkeypatch.setattr(settings, "LLM_PROTOCOL", "openai_compatible")
    monkeypatch.setattr(settings, "LLM_AUTH_MODE", "BEARER")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory, path
    await engine.dispose()


def _set_env(monkeypatch, *, base_url: str, model: str = "env-model", api_key: str = SECRET_A, auth_mode: str = "BEARER"):
    monkeypatch.setattr(settings, "LLM_BASE_URL", base_url)
    monkeypatch.setattr(settings, "LLM_MODEL", model)
    monkeypatch.setattr(settings, "LLM_API_KEY", api_key)
    monkeypatch.setattr(settings, "LLM_AUTH_MODE", auth_mode)


@pytest.mark.parametrize("model", ["../escape", "a..b", "/model", "model/", "a?b", "a#b", "a%2fb", "a b", "a\\b", "a\n"])
def test_model_rejects_traversal_and_control_characters(model):
    with pytest.raises(AIConfigError) as exc:
        validate_model(model)
    assert exc.value.code == "INVALID_MODEL"


@pytest.mark.parametrize("url", ["https://u:p@example.org/v1", "https://example.org/v1?x=1", "https://example.org/v1#x", "https://example.org/a/../v1", "https://example.org/a/%2e%2e/v1", "https://example.org/v1%2felse", "https://example.org/team%3Ba/v1", "https://example.org/v1?", "https://example.org:0/v1", "https://example.org/v1\\else"])
def test_target_rejects_ambiguous_tenant_paths(url):
    with pytest.raises(AIConfigError):
        canonical_target(url)


def test_target_canonicalization_keeps_exact_path_binding():
    base, binding = canonical_target("https://EXAMPLE.org:443/team-a/v1/")
    assert base == "https://example.org/team-a/v1"
    assert binding["base_path"] == "/team-a/v1"
    assert binding != canonical_target("https://example.org/team-b/v1")[1]


@pytest.mark.asyncio
async def test_env_switches_actual_http_requests_and_snapshot_is_immutable(db_factory, stubs, monkeypatch):
    factory, _ = db_factory
    a, b = stubs
    async with factory() as db:
        _set_env(monkeypatch, base_url=a.url, model="model-a", api_key=SECRET_A)
        first = await service.get_status(db)
        old = await service.resolve_snapshot(db)
        assert await adapter.chat(old, [{"role": "user", "content": "hello"}]) == "OK"

        _set_env(monkeypatch, base_url=b.url, model="model-b", api_key=SECRET_B)
        second = await service.get_status(db)
        new = await service.resolve_snapshot(db)
        await adapter.chat(new, [{"role": "user", "content": "hello"}])
        await adapter.chat(old, [{"role": "user", "content": "retry"}])

        assert old.revision_token != new.revision_token
        assert first["active"]["base_url"] == a.url and second["active"]["base_url"] == b.url
        assert first["persisted"] is None and second["persisted"] is None
        assert len(a.received) == 2 and len(b.received) == 1
        assert a.received[0]["auth"] == f"Bearer {SECRET_A}"
        assert b.received[0]["auth"] == f"Bearer {SECRET_B}"
        assert b.received[0]["body"]["model"] == "model-b"
        assert SECRET_A not in repr(old)
        assert SECRET_B not in json.dumps(second)
        with pytest.raises(FrozenInstanceError):
            old.model = "changed"


@pytest.mark.asyncio
async def test_new_process_reads_same_env_revision_regardless_of_db(db_factory, stubs, monkeypatch):
    factory, db_path = db_factory
    a, _ = stubs
    _set_env(monkeypatch, base_url=a.url, model="model-a", api_key=SECRET_A)
    async with factory() as db:
        expected = await service.get_status(db)

    env = dict(
        os.environ,
        PYTHONUTF8="1",
        PYTHONIOENCODING="utf-8",
        ENVIRONMENT="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_path.as_posix()}",
        LLM_API_KEY=SECRET_A,
        LLM_BASE_URL=a.url,
        LLM_MODEL="model-a",
        LLM_PROTOCOL="openai_compatible",
        LLM_AUTH_MODE="BEARER",
        PYTHONPATH=str(Path.cwd() / "backend"),
    )
    code = "import asyncio; from app.services.ai_config.service import resolve_snapshot; s=asyncio.run(resolve_snapshot()); print(s.model); print(s.revision_token)"
    result = await asyncio.to_thread(subprocess.run, [sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["model-a", expected["revision_token"]]
    assert SECRET_A not in result.stdout + result.stderr


@pytest.mark.asyncio
async def test_missing_bearer_never_uses_sdk_env_and_none_sends_no_auth(db_factory, stubs, monkeypatch):
    factory, _ = db_factory
    a, _ = stubs
    monkeypatch.setenv("OPENAI_API_KEY", "sk-synth-env-must-never-send")
    _set_env(monkeypatch, base_url=a.url, model="model-a", api_key="", auth_mode="BEARER")
    async with factory() as db:
        status = await service.get_status(db)
        assert status["credential"]["state"] == "MISSING"
        with pytest.raises(AIConfigError) as exc:
            await service.resolve_snapshot(db)
        assert exc.value.code == "UNCONFIGURED_CREDENTIAL"
        snap = await service.resolve_snapshot(db, allow_unconfigured=True)
        with patch("httpx.AsyncClient", side_effect=AssertionError("Must fail before HTTP client construction")):
            with pytest.raises(AIConfigError) as exc:
                await adapter.chat(snap, [{"role": "user", "content": "hello"}])
        assert exc.value.code == "UNCONFIGURED_CREDENTIAL" and not a.received

        _set_env(monkeypatch, base_url=a.url, model="model-a", api_key="", auth_mode="NONE")
        none_status = await service.get_status(db)
        assert none_status["credential"]["state"] == "CLEARED"
        await adapter.chat(await service.resolve_snapshot(db), [{"role": "user", "content": "hello"}])
        assert a.received[-1]["auth"] is None


@pytest.mark.asyncio
async def test_redirect_is_never_followed_or_leaks_auth(db_factory, stubs, monkeypatch):
    factory, _ = db_factory
    a, b = stubs
    a.status, a.redirect = 307, b.url + "/chat/completions"
    _set_env(monkeypatch, base_url=a.url, model="model-a", api_key=SECRET_A)
    async with factory() as db:
        snap = await service.resolve_snapshot(db)
    with pytest.raises(AIConfigError) as exc:
        await adapter.chat(snap, [{"role": "user", "content": "redirect-check"}])
    assert exc.value.code == "REDIRECT_BLOCKED"
    assert len(a.received) == 1 and not b.received
    assert SECRET_A not in json.dumps(exc.value.detail)


@pytest.mark.asyncio
async def test_ssrf_blocked_without_allowlist_and_dns_private_address(db_factory, stubs, monkeypatch):
    factory, _ = db_factory
    a, _ = stubs
    monkeypatch.setattr(settings, "AI_LOCAL_ALLOWED_BASE_URLS", [])
    async with factory() as db:
        for target in (a.url, "https://127.0.0.1/v1", "https://169.254.169.254/v1", "https://[::1]/v1"):
            _set_env(monkeypatch, base_url=target, model="model-a", api_key=SECRET_A)
            snap = await service.resolve_snapshot(db)
            with pytest.raises(AIConfigError) as exc:
                await adapter.chat(snap, [{"role": "user", "content": "ssrf"}])
            assert exc.value.code == "SSRF_BLOCKED"
        _set_env(monkeypatch, base_url="https://public-looking.example/v1", model="model-a", api_key=SECRET_A)
        snap = await service.resolve_snapshot(db)
        with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 443))]):
            with pytest.raises(AIConfigError) as exc:
                await adapter.chat(snap, [{"role": "user", "content": "dns-ssrf"}])
            assert exc.value.code == "SSRF_BLOCKED"
    assert not a.received


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["   ", "********", "sk-••••1234", "your-api-key", "sk-...masked"])
async def test_invalid_or_masked_env_credentials_are_rejected(db_factory, stubs, monkeypatch, key):
    factory, _ = db_factory
    a, _ = stubs
    _set_env(monkeypatch, base_url=a.url, model="model-a", api_key=key)
    async with factory() as db:
        with pytest.raises(AIConfigError) as exc:
            await service.resolve_snapshot(db)
        assert exc.value.code == "INVALID_CREDENTIAL"
    assert not a.received


@pytest.mark.asyncio
async def test_adapter_classifies_real_error_body_and_never_echoes_secret(db_factory, stubs, monkeypatch):
    factory, _ = db_factory
    a, _ = stubs
    _set_env(monkeypatch, base_url=a.url, model="model-a", api_key=SECRET_A)
    async with factory() as db:
        snap = await service.resolve_snapshot(db)
    error_cases = [
        (401, {"error": {"code": "invalid_api_key", "message": SECRET_A}}, "AUTHENTICATION_FAILED"),
        (403, {"error": {"code": "client_not_allowed", "message": SECRET_A}}, "CLIENT_NOT_ALLOWED"),
        (429, {"error": {"code": "insufficient_quota"}}, "QUOTA_EXCEEDED"),
        (200, {"foo": "bar"}, "PROTOCOL_ERROR"),
    ]
    for status, payload, expected in error_cases:
        a.status, a.payload = status, payload
        with pytest.raises(AIConfigError) as exc:
            await adapter.chat(snap, [{"role": "user", "content": "probe"}])
        assert exc.value.code == expected
        assert SECRET_A not in json.dumps(exc.value.detail)

    a.status, a.payload = 200, {"choices": [{"message": {"content": f"ok {SECRET_A}"}, "finish_reason": "stop"}]}
    reply = await adapter.chat(snap, [{"role": "user", "content": "redact"}])
    assert SECRET_A not in reply
    assert "[REDACTED]" in reply


@pytest.mark.asyncio
async def test_running_request_keeps_snapshot_when_env_changes_target(db_factory, stubs, monkeypatch):
    factory, _ = db_factory
    a, b = stubs
    a.release = threading.Event()
    _set_env(monkeypatch, base_url=a.url, model="model-a", api_key=SECRET_A)
    async with factory() as db:
        old = await service.resolve_snapshot(db)
        task = asyncio.create_task(adapter.chat(old, [{"role": "user", "content": "delayed"}]))
        assert await asyncio.to_thread(a.entered.wait, 3)
        _set_env(monkeypatch, base_url=b.url, model="model-b", api_key=SECRET_B)
        a.release.set()
        assert await task == "OK"
        await adapter.chat(await service.resolve_snapshot(db), [{"role": "user", "content": "next"}])
        assert a.received[0]["auth"] == f"Bearer {SECRET_A}"
        assert b.received[0]["auth"] == f"Bearer {SECRET_B}"


@pytest.mark.asyncio
async def test_admin_api_is_read_only_enforces_auth_no_store_and_revoked_role(db_factory, stubs, monkeypatch):
    factory, _ = db_factory
    a, _ = stubs
    _set_env(monkeypatch, base_url=a.url, model="env-model-live", api_key=SECRET_A)
    admin_id, student_id = uuid.uuid4(), uuid.uuid4()
    async with factory() as db:
        for uid, role in ((admin_id, UserRole.ADMIN), (student_id, UserRole.STUDENT)):
            db.add(User(id=uid, email=f"{uid}@example.test", hashed_password=get_password_hash("synthetic-test-pass"), full_name="Kiểm thử", role=role, is_active=True))
        await db.commit()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.include_router(router, prefix="/api")

    async def override_db():
        async with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    admin_token = create_access_token(str(admin_id), role="ADMIN")
    student_token = create_access_token(str(student_id), role="STUDENT")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        for prefix in ("/api", "/api/v1"):
            endpoint = prefix + "/admin/ai-config"
            assert (await client.get(endpoint)).status_code in {401, 403}
            assert (await client.get(endpoint, headers={"Authorization": f"Bearer {student_token}"})).status_code == 403

        headers = {"Authorization": f"Bearer {admin_token}"}
        res = await client.get("/api/v1/admin/ai-config", headers=headers)
        assert res.status_code == 200
        assert res.headers["cache-control"] == "no-store"
        body = res.json()
        assert body["active"]["base_url"] == a.url
        assert body["active"]["model"] == "env-model-live"
        assert body["active"]["source_mode"] == "ENV"
        assert body["persisted"] is None
        assert SECRET_A not in res.text

        # Các endpoint ghi / probe đã bị gỡ bỏ (chỉ đọc).
        for prefix in ("/api", "/api/v1"):
            assert (await client.put(f"{prefix}/admin/ai-config", headers=headers, json={})).status_code in {404, 405}
            assert (await client.post(f"{prefix}/admin/ai-config/probe", headers=headers, json={})).status_code in {404, 405}
            assert (await client.post(f"{prefix}/admin/ai-config/probe-active", headers=headers, json={})).status_code in {404, 405}

        async with factory() as db:
            await db.execute(update(User).where(User.id == admin_id).values(role=UserRole.STUDENT))
            await db.commit()
        assert (await client.get("/api/v1/admin/ai-config", headers=headers)).status_code == 403


@pytest.mark.asyncio
async def test_env_changes_and_live_dotenv_reload_update_status_and_snapshot_ignoring_legacy_db(db_factory, stubs, tmp_path, monkeypatch):
    factory, _ = db_factory
    a, b = stubs
    admin_id = uuid.uuid4()
    async with factory() as db:
        db.add(User(id=admin_id, email="env-admin@example.test", hashed_password=get_password_hash("synthetic-pass"), full_name="Admin", role=UserRole.ADMIN, is_active=True))
        await db.commit()

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def override_db():
        async with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    headers = {"Authorization": f"Bearer {create_access_token(str(admin_id), role='ADMIN')}"}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1) Thay đổi trực tiếp trong settings (test mode) cập nhật tức thì và bỏ qua legacy DB row.
        _set_env(monkeypatch, base_url=a.url, model="model-v1", api_key=SECRET_A)
        async with factory() as db:
            snap1 = await service.resolve_snapshot(db)
        r1 = await client.get("/api/v1/admin/ai-config", headers=headers)
        assert r1.status_code == 200
        assert r1.json()["persisted"] is None
        assert r1.json()["last_probe"] is None
        assert r1.json()["active"]["base_url"] == a.url
        assert r1.json()["active"]["model"] == "model-v1"
        assert snap1.base_url == a.url and snap1.model == "model-v1" and snap1.credential == SECRET_A

        _set_env(monkeypatch, base_url=b.url, model="model-v2", api_key=SECRET_B)
        async with factory() as db:
            snap2 = await service.resolve_snapshot(db)
        r2 = await client.get("/api/v1/admin/ai-config", headers=headers)
        assert r2.json()["active"]["base_url"] == b.url
        assert r2.json()["active"]["model"] == "model-v2"
        assert r2.json()["revision_token"] != r1.json()["revision_token"]
        assert snap2.base_url == b.url and snap2.model == "model-v2" and snap2.credential == SECRET_B

        # 2) Live reload khi file .env thay đổi mtime/nội dung ở môi trường non-test.
        dotenv_path = tmp_path / ".env"
        dotenv_path.write_text(
            f"# comment\nLLM_BASE_URL={a.url}\nLLM_MODEL=\"dotenv-model-1\" # inline\nLLM_API_KEY='{SECRET_A}'\n",
            encoding="utf-8",
        )
        future = time.time() + 10
        os.utime(dotenv_path, (future, future))
        monkeypatch.setattr(settings, "ENVIRONMENT", "development")
        monkeypatch.setattr(service, "_ENV_CANDIDATES", (dotenv_path,))
        monkeypatch.setattr(service, "_BOOT_ENV_MTIMES", {dotenv_path: future - 5})
        monkeypatch.setenv("LLM_MODEL", "stale-os-env-model")
        monkeypatch.setenv("LLM_BASE_URL", "https://stale-os-env.example/v1")

        r3 = await client.get("/api/v1/admin/ai-config", headers=headers)
        async with factory() as db:
            snap3 = await service.resolve_snapshot(db)
        assert r3.status_code == 200
        assert r3.json()["active"]["base_url"] == a.url
        assert r3.json()["active"]["model"] == "dotenv-model-1"
        assert snap3.base_url == a.url and snap3.model == "dotenv-model-1" and snap3.credential == SECRET_A

        # Sửa tiếp .env với mtime mới hơn -> reload ngay lập tức lần nữa.
        dotenv_path.write_text(
            f"LLM_BASE_URL={b.url}\nLLM_MODEL=dotenv-model-2\nLLM_API_KEY={SECRET_B}\n",
            encoding="utf-8",
        )
        os.utime(dotenv_path, (future + 5, future + 5))
        r4 = await client.get("/api/v1/admin/ai-config", headers=headers)
        async with factory() as db:
            snap4 = await service.resolve_snapshot(db)
        assert r4.json()["active"]["base_url"] == b.url
        assert r4.json()["active"]["model"] == "dotenv-model-2"
        assert snap4.base_url == b.url and snap4.model == "dotenv-model-2" and snap4.credential == SECRET_B
    assert not a.received and not b.received


@pytest.mark.asyncio
async def test_sync_consumer_uses_actual_bound_http_stack(db_factory, stubs, monkeypatch):
    factory, _ = db_factory
    a, _ = stubs
    _set_env(monkeypatch, base_url=a.url, model="model-a", api_key=SECRET_A)
    async with factory() as db:
        snap = await service.resolve_snapshot(db)
        assert await asyncio.to_thread(adapter.chat_sync, snap, [{"role": "user", "content": "vision synthetic task"}]) == "OK"
        assert a.received[-1]["auth"] == f"Bearer {SECRET_A}"
        assert a.received[-1]["body"]["model"] == "model-a"


@pytest.mark.asyncio
async def test_sync_dns_timeout_does_not_wait_for_os_resolver(db_factory, stubs, monkeypatch):
    factory, _ = db_factory
    a, _ = stubs
    _set_env(monkeypatch, base_url=a.url, model="model-a", api_key=SECRET_A)
    async with factory() as db:
        snap = await service.resolve_snapshot(db)
    release, finished = threading.Event(), threading.Event()

    def slow_dns(*args):
        try:
            release.wait(3)
            raise AIConfigError("DNS_ERROR", "Synthetic DNS failure", 503)
        finally:
            finished.set()

    monkeypatch.setattr(adapter, "resolve_target_addresses", slow_dns)
    started = time.perf_counter()
    try:
        with pytest.raises(AIConfigError) as exc:
            await asyncio.to_thread(adapter.chat_sync, snap, [{"role": "user", "content": "timeout"}], timeout=1)
        assert exc.value.code == "TIMEOUT"
        assert time.perf_counter() - started < 2
    finally:
        release.set()
        assert await asyncio.to_thread(finished.wait, 3)
    assert not a.received


@pytest.mark.asyncio
async def test_async_adapter_timeout_and_concurrency_are_bounded(db_factory, stubs, monkeypatch):
    factory, _ = db_factory
    a, _ = stubs
    a.release = threading.Event()
    _set_env(monkeypatch, base_url=a.url, model="model-a", api_key=SECRET_A)
    async with factory() as db:
        snapshot = await service.resolve_snapshot(db)

    def first_three_arrived():
        with a.received_condition:
            return a.received_condition.wait_for(lambda: len(a.received) >= 3, timeout=6)

    pending = [asyncio.create_task(adapter.chat(snapshot, [{"role": "user", "content": "bounded"}], timeout=10)) for _ in range(4)]
    try:
        assert await asyncio.to_thread(first_three_arrived)
        assert len(a.received) == 3  # Request thứ tư đang đợi slot, chưa đi ra mạng.
        a.release.set()
        assert await asyncio.gather(*pending) == ["OK"] * 4
        assert len(a.received) == 4
    finally:
        a.release.set()
        await asyncio.gather(*pending, return_exceptions=True)

    a.release = threading.Event()
    try:
        with pytest.raises(AIConfigError) as exc:
            await adapter.chat(snapshot, [{"role": "user", "content": "deadline"}], timeout=1)
        assert exc.value.code == "TIMEOUT"
    finally:
        a.release.set()


@pytest.mark.asyncio
async def test_async_chat_auto_retries_transient_5xx_and_empty_content(db_factory, stubs, monkeypatch):
    factory, _ = db_factory
    a, _ = stubs
    _set_env(monkeypatch, base_url=a.url, model="model-a", api_key=SECRET_A)
    async with factory() as db:
        snap = await service.resolve_snapshot(db)

    a.responses = [
        (503, {"error": {"code": "upstream_overloaded", "message": "busy"}}, None),
        (502, {"error": {"message": "bad gateway"}}, None),
        (200, {"choices": [{"message": {"content": "RECOVERED_ASYNC"}, "finish_reason": "stop"}]}, None),
    ]
    reply = await adapter.chat(snap, [{"role": "user", "content": "retry-5xx"}], timeout=15)
    assert reply == "RECOVERED_ASYNC"
    assert len(a.received) == 3

    a.received.clear()
    a.responses = [
        (500, {"error": {"message": "internal error"}}, None),
        (200, {"choices": [{"message": {"content": "   "}, "finish_reason": "stop"}]}, None),
        (200, {"choices": [{"message": {"content": "RECOVERED_EMPTY"}, "finish_reason": "stop"}]}, None),
    ]
    reply2 = await adapter.chat(snap, [{"role": "user", "content": "retry-empty"}], timeout=15)
    assert reply2 == "RECOVERED_EMPTY"
    assert len(a.received) == 3


@pytest.mark.asyncio
async def test_sync_chat_auto_retries_transient_503(db_factory, stubs, monkeypatch):
    factory, _ = db_factory
    a, _ = stubs
    _set_env(monkeypatch, base_url=a.url, model="model-a", api_key=SECRET_A)
    async with factory() as db:
        snap = await service.resolve_snapshot(db)

    a.responses = [
        (503, {"error": {"code": "upstream_overloaded", "message": "busy"}}, None),
        (200, {"choices": [{"message": {"content": "RECOVERED_SYNC"}, "finish_reason": "stop"}]}, None),
    ]
    reply = await asyncio.to_thread(adapter.chat_sync, snap, [{"role": "user", "content": "retry-sync"}], timeout=15)
    assert reply == "RECOVERED_SYNC"
    assert len(a.received) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("status,payload,redirect,expected_code", [
    (401, {"error": {"code": "invalid_api_key"}}, None, "AUTHENTICATION_FAILED"),
    (403, {"error": {"code": "permission_denied"}}, None, "PERMISSION_DENIED"),
    (429, {"error": {"code": "insufficient_quota"}}, None, "QUOTA_EXCEEDED"),
    (302, {}, "https://other.example/v1/chat/completions", "REDIRECT_BLOCKED"),
    (200, {"foo": "bar"}, None, "PROTOCOL_ERROR"),
])
async def test_permanent_and_security_errors_are_never_retried(db_factory, stubs, monkeypatch, status, payload, redirect, expected_code):
    factory, _ = db_factory
    a, _ = stubs
    _set_env(monkeypatch, base_url=a.url, model="model-a", api_key=SECRET_A)
    async with factory() as db:
        snap = await service.resolve_snapshot(db)

    a.status, a.payload, a.redirect = status, payload, redirect
    with pytest.raises(AIConfigError) as exc:
        await adapter.chat(snap, [{"role": "user", "content": "no-retry"}], timeout=15)
    assert exc.value.code == expected_code
    assert len(a.received) == 1
