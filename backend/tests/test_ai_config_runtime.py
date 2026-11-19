"""@blast-radius: core, api, db, integration
Hợp đồng cấu hình AI đi qua DB và HTTP loopback thật với secret tổng hợp.
"""
import asyncio
import json
import os
import subprocess
import sys
import threading
import uuid
from dataclasses import FrozenInstanceError, replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
import httpx
import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from fastapi import FastAPI
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.core.config import settings
from app.core.ai_runtime import AIConfigError, canonical_target, validate_model
from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.models.ai_config import AIRuntimeConfig, AIConfigAudit
from app.models.identity import User, UserRole
from app.schemas.ai_config import AIConfigDraft, AIConfigProbe, AIActiveProbe
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
                owner.entered.set()
                if owner.release is not None:
                    owner.release.wait(5)
                self.send_response(owner.status)
                self.send_header("Content-Type", "application/json")
                if owner.redirect:
                    self.send_header("Location", owner.redirect)
                self.end_headers()
                payload = owner.payload if owner.payload is not None else {"choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}]}
                try:
                    self.wfile.write(json.dumps(payload).encode())
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
    monkeypatch.setattr(settings, "AI_CONFIG_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "AI_CONFIG_ENCRYPTION_KEY_ID", "test-primary")
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    monkeypatch.setattr(settings, "LLM_BASE_URL", "https://example.org/v1")
    monkeypatch.setattr(settings, "LLM_MODEL", "env-model")
    monkeypatch.setattr(settings, "LLM_PROTOCOL", "openai_compatible")
    monkeypatch.setattr(settings, "LLM_AUTH_MODE", "BEARER")
    monkeypatch.setattr(settings, "AI_PROBE_LIMIT_PER_MINUTE", 100)
    async with engine.begin() as conn:
        actual = (await conn.execute(text("PRAGMA database_list"))).all()[0][2]
        assert Path(actual).resolve() == path.resolve()
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory, path
    await engine.dispose()


async def draft_for(db, url, *, action="REPLACE", secret=SECRET_A, model="model-a", source="DATABASE", auth="BEARER"):
    status = await service.get_status(db)
    return AIConfigDraft(source_mode=source, protocol="openai_compatible", base_url=url, model=model,
                         auth_mode=auth, credential_action=action,
                         api_key=secret if action == "REPLACE" else None, base_revision_token=status["revision_token"])


def probe_for(draft):
    return AIConfigProbe(**draft.model_dump(), probe_request_id=str(uuid.uuid4()), draft_digest="synthetic-draft-1")


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
async def test_apply_switches_actual_http_requests_and_persists_encrypted(db_factory, stubs):
    factory, db_path = db_factory
    a, b = stubs
    async with factory() as db:
        first = await service.apply_config(db, await draft_for(db, a.url), "admin-one")
        old = await service.resolve_snapshot(db)
        assert await adapter.chat(old, [{"role": "user", "content": "hello"}]) == "OK"
        second = await service.apply_config(db, await draft_for(db, b.url, secret=SECRET_B, model="model-b"), "admin-one")
        new = await service.resolve_snapshot(db)
        await adapter.chat(new, [{"role": "user", "content": "hello"}])
        await adapter.chat(old, [{"role": "user", "content": "retry"}])
        assert old.revision_token != new.revision_token
        assert first["active"]["base_url"] == a.url and second["active"]["base_url"] == b.url
        assert len(a.received) == 2 and len(b.received) == 1
        assert a.received[0]["auth"] == f"Bearer {SECRET_A}"
        assert b.received[0]["auth"] == f"Bearer {SECRET_B}"
        assert b.received[0]["body"]["model"] == "model-b"
        assert SECRET_A not in repr(old)
        with pytest.raises(FrozenInstanceError):
            old.model = "changed"
        row = (await db.execute(select(AIRuntimeConfig))).scalar_one()
        assert row.secret_ciphertext != SECRET_B and row.secret_fingerprint != SECRET_B
        assert SECRET_B not in json.dumps(second)
    assert SECRET_A.encode() not in db_path.read_bytes()
    assert SECRET_B.encode() not in db_path.read_bytes()
    async with factory() as fresh_worker:
        current = await service.resolve_snapshot(fresh_worker)
        assert current.model == "model-b" and current.credential == SECRET_B


@pytest.mark.asyncio
async def test_new_process_reads_same_applied_revision_after_restart(db_factory, stubs):
    factory, db_path = db_factory
    a, _ = stubs
    async with factory() as db:
        saved = await service.apply_config(db, await draft_for(db, a.url), "admin-restart")
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", ENVIRONMENT="test", DATABASE_URL=f"sqlite+aiosqlite:///{db_path.as_posix()}",
               AI_CONFIG_ENCRYPTION_KEY=settings.AI_CONFIG_ENCRYPTION_KEY, AI_CONFIG_ENCRYPTION_KEY_ID=settings.AI_CONFIG_ENCRYPTION_KEY_ID,
               LLM_API_KEY="", LLM_BASE_URL=settings.LLM_BASE_URL, LLM_MODEL=settings.LLM_MODEL, PYTHONPATH=str(Path.cwd() / "backend"))
    code = "import asyncio; from app.services.ai_config.service import resolve_snapshot; s=asyncio.run(resolve_snapshot()); print(s.model); print(s.revision_token)"
    result = await asyncio.to_thread(subprocess.run, [sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["model-a", saved["revision_token"]]
    assert SECRET_A not in result.stdout + result.stderr


@pytest.mark.asyncio
async def test_keep_conflicts_and_direct_apply_checks_same_host_tenant(db_factory, stubs):
    factory, _ = db_factory
    a, b = stubs
    async with factory() as db:
        await service.apply_config(db, await draft_for(db, a.url), "admin-one")
        stale = await draft_for(db, a.url, action="KEEP")
        await service.apply_config(db, await draft_for(db, a.url, secret=SECRET_B), "admin-two")
        for operation in (lambda: service.apply_config(db, stale, "admin-one"), lambda: service.probe_draft(db, probe_for(stale), "admin-one")):
            with pytest.raises(AIConfigError) as exc:
                await operation()
            assert exc.value.status_code == 409
        for target in (a.url.replace("/team-a/", "/team-b/"), b.url):
            altered = await draft_for(db, target, action="KEEP")
            for operation in (lambda: service.apply_config(db, altered, "admin-one"), lambda: service.probe_draft(db, probe_for(altered), "admin-one")):
                with pytest.raises(AIConfigError) as exc:
                    await operation()
                assert exc.value.code == "TARGET_BINDING_CHANGED"
        assert not a.received and not b.received


@pytest.mark.asyncio
async def test_two_concurrent_admin_updates_have_one_winner(db_factory, stubs):
    factory, _ = db_factory
    a, _ = stubs
    async with factory() as db:
        await service.apply_config(db, await draft_for(db, a.url), "admin-one")
        one = await draft_for(db, a.url, action="KEEP", model="one")
        two = one.model_copy(update={"model": "two"})
    async def apply(payload, actor):
        async with factory() as db:
            try:
                return await service.apply_config(db, payload, actor)
            except AIConfigError as exc:
                return exc.status_code
    results = await asyncio.gather(apply(one, "one"), apply(two, "two"))
    assert sum(isinstance(item, dict) for item in results) == 1
    assert results.count(409) == 1


@pytest.mark.asyncio
async def test_clear_never_uses_sdk_env_and_none_sends_no_auth(db_factory, stubs, monkeypatch):
    factory, _ = db_factory
    a, _ = stubs
    monkeypatch.setenv("OPENAI_API_KEY", "sk-synth-env-must-never-send")
    monkeypatch.setattr(settings, "LLM_API_KEY", "sk-synth-env-must-never-send")
    async with factory() as db:
        await service.apply_config(db, await draft_for(db, a.url), "admin-one")
        cleared = await service.apply_config(db, await draft_for(db, a.url, action="CLEAR"), "admin-one")
        assert cleared["credential"]["state"] == "CLEARED"
        with pytest.raises(AIConfigError) as exc:
            await service.resolve_snapshot(db)
        assert exc.value.code == "UNCONFIGURED_CREDENTIAL"
        snap = await service.resolve_snapshot(db, allow_unconfigured=True)
        with patch("httpx.AsyncClient", side_effect=AssertionError("Must fail before HTTP client construction")):
            with pytest.raises(AIConfigError) as exc:
                await adapter.chat(snap, [{"role": "user", "content": "hello"}])
        assert exc.value.code == "UNCONFIGURED_CREDENTIAL" and not a.received
        await service.apply_config(db, await draft_for(db, a.url, action="CLEAR", auth="NONE"), "admin-one")
        await adapter.chat(await service.resolve_snapshot(db), [{"role": "user", "content": "hello"}])
        assert a.received[-1]["auth"] is None


@pytest.mark.asyncio
async def test_missing_encryption_key_preserves_existing_ciphertext(db_factory, stubs, monkeypatch):
    factory, _ = db_factory
    a, _ = stubs
    async with factory() as db:
        await service.apply_config(db, await draft_for(db, a.url), "admin-one")
        original = (await db.execute(select(AIRuntimeConfig))).scalar_one().secret_ciphertext
        monkeypatch.setattr(settings, "AI_CONFIG_ENCRYPTION_KEY", "")
        status = await service.get_status(db)
        assert status["credential"]["state"] == "LOCKED" and not status["encryption"]["available"]
        for action in ("KEEP", "CLEAR", "REPLACE"):
            with pytest.raises(AIConfigError) as exc:
                await service.apply_config(db, await draft_for(db, a.url, action=action), "admin-one")
            assert exc.value.code == "ENCRYPTION_KEY_UNAVAILABLE"
        assert (await db.execute(select(AIRuntimeConfig))).scalar_one().secret_ciphertext == original


@pytest.mark.asyncio
async def test_external_secret_change_invalidates_keep_without_version_bump(db_factory, stubs):
    factory, _ = db_factory
    a, _ = stubs
    async with factory() as db:
        await service.apply_config(db, await draft_for(db, a.url), "admin-one")
        stale = await draft_for(db, a.url, action="KEEP")
        import hashlib
        encrypted = Fernet(settings.AI_CONFIG_ENCRYPTION_KEY.encode()).encrypt(SECRET_B.encode()).decode()
        await db.execute(update(AIRuntimeConfig).values(secret_ciphertext=encrypted, secret_fingerprint=hashlib.sha256(SECRET_B.encode()).hexdigest()))
        await db.commit()
        with pytest.raises(AIConfigError) as exc:
            await service.probe_draft(db, probe_for(stale), "admin-one")
        assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_redirect_is_never_followed_or_leaks_auth(db_factory, stubs):
    factory, _ = db_factory
    a, b = stubs
    a.status, a.redirect = 307, b.url + "/chat/completions"
    async with factory() as db:
        draft = await draft_for(db, a.url)
        result = await service.probe_draft(db, probe_for(draft), "admin-one")
        assert result["code"] == "REDIRECT_BLOCKED" and not result["success"]
        assert len(a.received) == 1 and not b.received
        assert SECRET_A not in json.dumps(result)


@pytest.mark.asyncio
async def test_ssrf_blocked_without_allowlist_and_dns_private_address(db_factory, stubs, monkeypatch):
    factory, _ = db_factory
    a, _ = stubs
    monkeypatch.setattr(settings, "AI_LOCAL_ALLOWED_BASE_URLS", [])
    async with factory() as db:
        for target in (a.url, "https://127.0.0.1/v1", "https://169.254.169.254/v1", "https://[::1]/v1"):
            with pytest.raises(AIConfigError) as exc:
                await service.apply_config(db, await draft_for(db, target), "admin-one")
            assert exc.value.code == "SSRF_BLOCKED"
        with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 443))]):
            with pytest.raises(AIConfigError) as exc:
                await service.apply_config(db, await draft_for(db, "https://public-looking.example/v1"), "admin-one")
            assert exc.value.code == "SSRF_BLOCKED"
    assert not a.received


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["", "   ", "********", "sk-••••1234", "your-api-key", "sk-...masked"])
async def test_replace_rejects_empty_or_masked_values(db_factory, stubs, key):
    factory, _ = db_factory
    a, _ = stubs
    async with factory() as db:
        with pytest.raises(AIConfigError) as exc:
            await service.apply_config(db, await draft_for(db, a.url, secret=key), "admin-one")
        assert exc.value.code == "INVALID_CREDENTIAL"
    assert not a.received


@pytest.mark.asyncio
async def test_probe_classifies_real_error_body_and_never_echoes_secret(db_factory, stubs):
    factory, _ = db_factory
    a, _ = stubs
    cases = [(401, {"error": {"code": "invalid_api_key", "message": SECRET_A}}, "AUTHENTICATION_FAILED"),
             (403, {"error": {"code": "client_not_allowed", "message": SECRET_A}}, "CLIENT_NOT_ALLOWED"),
             (429, {"error": {"code": "insufficient_quota"}}, "QUOTA_EXCEEDED"),
             (200, {"foo": "bar"}, "PROTOCOL_ERROR"),
             (200, {"choices": [{"message": {"content": SECRET_A}, "finish_reason": "stop"}]}, "OK")]
    async with factory() as db:
        draft = await draft_for(db, a.url)
        for status, payload, expected in cases:
            a.status, a.payload = status, payload
            result = await service.probe_draft(db, probe_for(draft), "admin-one")
            assert result["code"] == expected
            assert SECRET_A not in json.dumps(result)


@pytest.mark.asyncio
async def test_running_request_keeps_snapshot_when_apply_changes_target(db_factory, stubs):
    factory, _ = db_factory
    a, b = stubs
    a.release = threading.Event()
    async with factory() as db:
        await service.apply_config(db, await draft_for(db, a.url), "admin-one")
        old = await service.resolve_snapshot(db)
        task = asyncio.create_task(adapter.chat(old, [{"role": "user", "content": "delayed"}]))
        assert await asyncio.to_thread(a.entered.wait, 3)
        await service.apply_config(db, await draft_for(db, b.url, secret=SECRET_B), "admin-two")
        a.release.set()
        assert await task == "OK"
        await adapter.chat(await service.resolve_snapshot(db), [{"role": "user", "content": "next"}])
        assert a.received[0]["auth"] == f"Bearer {SECRET_A}"
        assert b.received[0]["auth"] == f"Bearer {SECRET_B}"


@pytest.mark.asyncio
async def test_admin_api_auth_reveal_no_store_audit_and_revoked_role(db_factory, stubs):
    factory, _ = db_factory
    a, _ = stubs
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
        status = (await client.get("/api/v1/admin/ai-config", headers=headers)).json()
        data = {"source_mode": "DATABASE", "protocol": "openai_compatible", "base_url": a.url, "model": "model-a", "auth_mode": "BEARER", "credential_action": "REPLACE", "api_key": SECRET_A, "base_revision_token": status["revision_token"]}
        applied = await client.put("/api/v1/admin/ai-config", headers=headers, json=data)
        assert applied.status_code == 200 and SECRET_A not in applied.text
        reveal = await client.post("/api/admin/ai-config/reveal", headers=headers, json={"base_revision_token": applied.json()["revision_token"]})
        assert reveal.status_code == 200 and reveal.headers["cache-control"] == "no-store"
        assert reveal.json()["api_key"] == SECRET_A
        async with factory() as db:
            audits = (await db.execute(select(AIConfigAudit))).scalars().all()
            assert any(a.action == "REVEAL" for a in audits)
            assert all(SECRET_A not in json.dumps(a.summary) for a in audits)
            await db.execute(update(User).where(User.id == admin_id).values(role=UserRole.STUDENT))
            await db.commit()
        assert (await client.post("/api/admin/ai-config/reveal", headers=headers, json={"base_revision_token": applied.json()["revision_token"]})).status_code == 403


@pytest.mark.asyncio
async def test_env_profile_is_explicit_and_changes_invalidate_old_draft(db_factory, stubs, monkeypatch):
    factory, _ = db_factory
    a, b = stubs
    monkeypatch.setattr(settings, "LLM_BASE_URL", a.url)
    monkeypatch.setattr(settings, "LLM_API_KEY", SECRET_A)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", SECRET_B)
    async with factory() as db:
        env_snapshot = await service.resolve_snapshot(db)
        assert env_snapshot.credential == SECRET_A and env_snapshot.base_url == a.url
        stale = await draft_for(db, a.url, source="ENV", action="KEEP")
        monkeypatch.setattr(settings, "LLM_API_KEY", SECRET_B)
        with pytest.raises(AIConfigError) as exc:
            await service.probe_draft(db, probe_for(stale), "env-test")
        assert exc.value.status_code == 409
        await service.apply_config(db, await draft_for(db, b.url), "env-test")
        await service.apply_config(db, await draft_for(db, b.url, source="ENV", action="KEEP"), "env-test")
        restored = await service.resolve_snapshot(db)
        assert restored.base_url == a.url and restored.model == "env-model" and restored.credential == SECRET_B
        monkeypatch.setattr(settings, "LLM_BASE_URL", b.url)
        with pytest.raises(AIConfigError) as exc:
            await service.resolve_snapshot(db)
        assert exc.value.code == "ENV_BINDING_CHANGED"
    assert not a.received and not b.received


@pytest.mark.asyncio
async def test_encryption_bootstrap_requires_separate_valid_key_before_saving(db_factory, stubs, monkeypatch):
    factory, _ = db_factory
    a, _ = stubs
    async with factory() as db:
        for invalid in ("", "malformed", settings.SECRET_KEY):
            monkeypatch.setattr(settings, "AI_CONFIG_ENCRYPTION_KEY", invalid)
            with pytest.raises(AIConfigError) as exc:
                await service.apply_config(db, await draft_for(db, a.url), "bootstrap")
            assert exc.value.code == "ENCRYPTION_KEY_UNAVAILABLE"
            assert (await db.execute(select(AIRuntimeConfig))).scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_probe_rate_limit_is_per_actor_and_preserves_draft_metadata(db_factory, stubs, monkeypatch):
    factory, _ = db_factory
    a, _ = stubs
    monkeypatch.setattr(settings, "AI_PROBE_LIMIT_PER_MINUTE", 1)
    actor = str(uuid.uuid4())
    async with factory() as db:
        request = probe_for(await draft_for(db, a.url))
        first = await service.probe_draft(db, request, actor)
        assert first["probe_request_id"] == request.probe_request_id
        assert first["draft_digest"] == request.draft_digest
        assert first["base_revision_token"] == request.base_revision_token
        with pytest.raises(AIConfigError) as exc:
            await service.probe_draft(db, request, actor)
        assert exc.value.code == "PROBE_RATE_LIMIT" and exc.value.status_code == 429
        assert (await service.probe_draft(db, request, str(uuid.uuid4())))["success"]
        assert len(a.received) == 2


@pytest.mark.asyncio
async def test_main_aliases_share_persistence_and_validation_never_echoes_key(db_factory, stubs):
    from app.main import app
    factory, _ = db_factory
    a, _ = stubs
    admin_id = uuid.uuid4()
    async with factory() as db:
        db.add(User(id=admin_id, email="alias-admin@example.test", hashed_password=get_password_hash("synthetic-pass"), full_name="Quản trị", role=UserRole.ADMIN, is_active=True))
        await db.commit()
    async def override_db():
        async with factory() as db:
            yield db
    old = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = override_db
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            headers = {"Authorization": "Bearer " + create_access_token(str(admin_id), role="ADMIN")}
            active = (await client.get("/api/admin/ai-config", headers=headers)).json()
            data = {"source_mode": "DATABASE", "protocol": "openai_compatible", "base_url": a.url, "model": "model-a", "auth_mode": "BEARER", "credential_action": "REPLACE", "api_key": SECRET_A, "base_revision_token": active["revision_token"]}
            applied = await client.post("/api/rag-governance/update-llm-config", headers=headers, json=data)
            assert applied.status_code == 200
            alias = await client.get("/api/v1/rag-governance/llm-status", headers=headers)
            canonical = await client.get("/api/v1/admin/ai-config", headers=headers)
            assert alias.json()["revision_token"] == canonical.json()["revision_token"] == applied.json()["revision_token"]
            invalid = await client.put("/api/admin/ai-config", headers=headers, json={**data, "source_mode": "INVALID"})
            assert invalid.status_code == 422 and SECRET_A not in invalid.text
            legacy = await client.post("/api/rag-governance/update-llm-config", headers=headers, json={"api_key": SECRET_A, "model": "legacy"})
            assert legacy.status_code == 422 and SECRET_A not in legacy.text
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(old)


@pytest.mark.asyncio
async def test_sync_consumer_uses_actual_bound_http_stack(db_factory, stubs):
    factory, _ = db_factory
    a, _ = stubs
    async with factory() as db:
        await service.apply_config(db, await draft_for(db, a.url), "sync-test")
        snap = await service.resolve_snapshot(db)
        assert await asyncio.to_thread(adapter.chat_sync, snap, [{"role": "user", "content": "vision synthetic task"}]) == "OK"
        assert a.received[-1]["auth"] == f"Bearer {SECRET_A}"
        assert a.received[-1]["body"]["model"] == "model-a"


@pytest.mark.asyncio
async def test_sync_dns_timeout_does_not_wait_for_os_resolver(db_factory, stubs, monkeypatch):
    import time
    factory, _ = db_factory
    a, _ = stubs
    async with factory() as db:
        await service.apply_config(db, await draft_for(db, a.url), "sync-timeout")
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
async def test_failed_commit_keeps_previous_runtime_profile(db_factory, stubs, monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError
    from unittest.mock import AsyncMock
    factory, _ = db_factory
    a, b = stubs
    async with factory() as db:
        saved = await service.apply_config(db, await draft_for(db, a.url), "commit-one")
        replacement = await draft_for(db, b.url, secret=SECRET_B)
        monkeypatch.setattr(db, "commit", AsyncMock(side_effect=SQLAlchemyError("synthetic-db-failure")))
        with pytest.raises(SQLAlchemyError):
            await service.apply_config(db, replacement, "commit-two")
    async with factory() as db:
        active = await service.resolve_snapshot(db)
        assert active.base_url == a.url and active.credential == SECRET_A
        assert active.revision_token == saved["revision_token"]


@pytest.mark.asyncio
async def test_async_probe_timeout_and_concurrency_are_bounded(db_factory, stubs):
    factory, _ = db_factory
    a, _ = stubs
    a.release = threading.Event()
    async with factory() as db:
        await service.apply_config(db, await draft_for(db, a.url), "limit-test")
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
async def test_offline_key_rotation_preserves_credential_and_requires_new_env(db_factory, stubs, monkeypatch):
    from scripts.rotate_ai_config_key import rotate_key
    from cryptography.fernet import InvalidToken
    factory, _ = db_factory
    a, _ = stubs
    async with factory() as db:
        saved = await service.apply_config(db, await draft_for(db, a.url), "rotate-admin")
        row = (await db.execute(select(AIRuntimeConfig))).scalar_one()
        previous_ciphertext, fingerprint = row.secret_ciphertext, row.secret_fingerprint
        old_key = settings.AI_CONFIG_ENCRYPTION_KEY
        new_key = Fernet.generate_key().decode()
        assert await rotate_key(db, new_key, "rotated-test", expected_revision=saved["revision_token"]) == "rotated-test"
        await db.refresh(row)
        assert row.secret_ciphertext != previous_ciphertext and row.secret_fingerprint == fingerprint
        assert Fernet(new_key.encode()).decrypt(row.secret_ciphertext.encode()).decode() == SECRET_A
        with pytest.raises(InvalidToken):
            Fernet(old_key.encode()).decrypt(row.secret_ciphertext.encode())
        assert (await service.get_status(db))["credential"]["state"] == "LOCKED"
        monkeypatch.setattr(settings, "AI_CONFIG_ENCRYPTION_KEY", new_key)
        monkeypatch.setattr(settings, "AI_CONFIG_ENCRYPTION_KEY_ID", "rotated-test")
        restored = await service.resolve_snapshot(db)
        assert restored.credential == SECRET_A and restored.revision_token != saved["revision_token"]
        audit = (await db.execute(select(AIConfigAudit).where(AIConfigAudit.action == "ROTATE_ENCRYPTION_KEY"))).scalar_one()
        assert SECRET_A not in json.dumps(audit.summary)


@pytest.mark.asyncio
async def test_key_rotation_without_old_key_keeps_ciphertext_unchanged(db_factory, stubs, monkeypatch):
    from scripts.rotate_ai_config_key import rotate_key
    factory, _ = db_factory
    a, _ = stubs
    async with factory() as db:
        await service.apply_config(db, await draft_for(db, a.url), "rotate-admin")
        row = (await db.execute(select(AIRuntimeConfig))).scalar_one()
        before = row.secret_ciphertext
        monkeypatch.setattr(settings, "AI_CONFIG_ENCRYPTION_KEY", "")
        with pytest.raises(AIConfigError) as exc:
            await rotate_key(db, Fernet.generate_key().decode(), "new-test")
        assert exc.value.code == "ROTATION_UNAVAILABLE"
        await db.refresh(row)
        assert row.secret_ciphertext == before
        assert not (await db.execute(select(AIConfigAudit).where(AIConfigAudit.action == "ROTATE_ENCRYPTION_KEY"))).scalars().all()
