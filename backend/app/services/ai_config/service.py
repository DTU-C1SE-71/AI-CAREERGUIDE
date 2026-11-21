"""Lưu hồ sơ AI nguyên khối, CAS revision và giải mã credential theo snapshot."""
import asyncio
import hashlib
import hmac
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import and_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.ai_runtime import AIConfigError, ConfigSnapshot, canonical_target, digest, resolve_target_addresses, validate_model, validate_credential
from app.models.ai_config import AIRuntimeConfig, AIConfigAudit
from app.schemas.ai_config import AIConfigDraft, AIConfigProbe, AIActiveProbe


_RATE_LOCK = Lock()
_PROBE_STARTS: dict[str, deque] = defaultdict(deque)


def _key_info() -> tuple[Fernet | None, str | None, str]:
    raw = settings.AI_CONFIG_ENCRYPTION_KEY
    configured_id = settings.AI_CONFIG_ENCRYPTION_KEY_ID or "primary"
    state = digest({"id": configured_id, "key_digest": hashlib.sha256(raw.encode()).hexdigest() if raw else None})
    if not raw or hmac.compare_digest(raw, settings.SECRET_KEY):
        return None, None, state
    try:
        return Fernet(raw.encode("ascii")), configured_id, state
    except (ValueError, UnicodeError):
        return None, None, state


def _env_profile() -> tuple[dict, str | None]:
    base, binding = canonical_target(settings.LLM_BASE_URL, settings.LLM_PROTOCOL)
    auth = settings.LLM_AUTH_MODE
    if auth not in {"BEARER", "NONE"}:
        raise AIConfigError("INVALID_AUTH_MODE", "Chế độ xác thực trong ENV không được hỗ trợ.")
    return {
        "source_mode": "ENV", "protocol": settings.LLM_PROTOCOL,
        "base_url": base, "model": validate_model(settings.LLM_MODEL),
        "auth_mode": auth, "credential_binding": binding,
    }, (settings.LLM_API_KEY or None) if auth == "BEARER" else None


def _fingerprint(secret: str | None) -> str | None:
    return hashlib.sha256(secret.encode()).hexdigest() if secret else None


def _copy_row(row: AIRuntimeConfig | None) -> dict | None:
    if row is None:
        return None
    return {name: getattr(row, name) for name in (
        "id", "version", "profile", "credential_state", "secret_ciphertext",
        "secret_fingerprint", "encryption_key_id",
    )}


async def _read_row(db: AsyncSession) -> dict | None:
    row = (await db.execute(select(AIRuntimeConfig).where(AIRuntimeConfig.id == 1).execution_options(populate_existing=True))).scalar_one_or_none()
    return _copy_row(row)


def _current(row: dict | None) -> dict:
    cipher, configured_key_id, key_state = _key_info()
    if row is None:
        profile, secret = _env_profile()
        state = "SET" if secret else "MISSING"
        if profile["auth_mode"] == "NONE":
            state = "CLEARED"
        env_state = {"profile": profile, "credential_fingerprint": _fingerprint(secret)}
        locked_code = None
    else:
        profile = dict(row["profile"])
        state = row["credential_state"]
        secret = None
        env_state = None
        locked_code = None
        # Một reference ENV luôn giữ binding đã được áp dụng. Đổi ENV host/path
        # không cho phép credential cũ tự chạy sang tenant khác sau restart.
        if profile["source_mode"] == "ENV":
            current_env, env_secret = _env_profile()
            env_state = {"profile": current_env, "credential_fingerprint": _fingerprint(env_secret)}
            if current_env["credential_binding"] != profile["credential_binding"]:
                locked_code = "ENV_BINDING_CHANGED"
                state = "LOCKED"
            else:
                profile = current_env
                if row["credential_state"] != "CLEARED":
                    secret = env_secret
                    state = "SET" if secret else "MISSING"
        elif state == "SET":
            if cipher is None or configured_key_id != row["encryption_key_id"]:
                state, locked_code = "LOCKED", "ENCRYPTION_KEY_UNAVAILABLE"
            else:
                try:
                    secret = cipher.decrypt((row["secret_ciphertext"] or "").encode()).decode()
                    if not hmac.compare_digest(_fingerprint(secret) or "", row["secret_fingerprint"] or ""):
                        state, locked_code = "LOCKED", "CREDENTIAL_INTEGRITY_ERROR"
                        secret = None
                except (InvalidToken, UnicodeError, ValueError):
                    state, locked_code = "LOCKED", "ENCRYPTION_KEY_UNAVAILABLE"
        if profile["auth_mode"] == "NONE":
            secret = None
    token = digest({"row": row, "env": env_state, "encryption": key_state, "embedding_model": settings.EMBEDDING_MODEL})
    return {"profile": profile, "credential": secret, "credential_state": state,
            "revision_token": token, "locked_code": locked_code, "row": row}


def _check_revision(state: dict, expected: str) -> None:
    if not hmac.compare_digest(state["revision_token"], expected):
        raise AIConfigError("REVISION_CONFLICT", "Cấu hình hoặc credential đã đổi. Hãy tải lại trước khi tiếp tục.", 409)


def _require_unlocked(state: dict) -> None:
    if state["locked_code"]:
        raise AIConfigError(state["locked_code"], "Không đọc được credential đã lưu; khôi phục đúng khóa mã hóa hoặc binding ENV trước khi tiếp tục.", 503)


def _snapshot(profile: dict, secret: str | None, revision: str, require_credential: bool = True) -> ConfigSnapshot:
    base, binding = canonical_target(profile["base_url"], profile["protocol"])
    if binding != profile["credential_binding"]:
        raise AIConfigError("TARGET_BINDING_MISMATCH", "Hồ sơ và đích credential không đồng nhất.")
    model = validate_model(profile["model"])
    if profile["auth_mode"] == "BEARER" and not secret and require_credential:
        raise AIConfigError("UNCONFIGURED_CREDENTIAL", "Chưa cấu hình credential; cấu hình CLEAR không dùng lại khóa ENV.", 409)
    if profile["auth_mode"] == "BEARER" and secret:
        validate_credential(secret)
    return ConfigSnapshot(
        source_mode=profile["source_mode"], protocol=profile["protocol"],
        canonical_base_url=base, model=model, auth_mode=profile["auth_mode"],
        credential_binding=tuple(binding[k] for k in ("protocol", "scheme", "host", "port", "base_path")),
        revision_token=revision, credential=secret if profile["auth_mode"] == "BEARER" else None,
        embedding_model=validate_model(settings.EMBEDDING_MODEL),
    )


async def resolve_snapshot(db: AsyncSession | None = None, *, allow_unconfigured: bool = False) -> ConfigSnapshot:
    """Đọc một lần lúc bắt đầu tác vụ; caller truyền snapshot cho mọi bước con."""
    if db is None:
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as own_db:
            return await resolve_snapshot(own_db, allow_unconfigured=allow_unconfigured)
    state = _current(await _read_row(db))
    _require_unlocked(state)
    return _snapshot(state["profile"], state["credential"], state["revision_token"], not allow_unconfigured)


def _available_models() -> list[str]:
    raw = settings.LLM_AVAILABLE_MODELS or ""
    items: list[str] = []
    for part in raw.replace("\n", ",").split(","):
        model_id = part.strip()
        if model_id and model_id not in items:
            items.append(model_id)
    default_model = (settings.LLM_MODEL or "").strip()
    if default_model and default_model not in items:
        items.insert(0, default_model)
    return items


def _public_status(state: dict, last_probe: dict | None = None) -> dict:
    cipher, configured_id, _ = _key_info()
    row = state["row"]
    credential_set = state["credential_state"] == "SET"
    return {
        "persisted": dict(row["profile"]) if row else None,
        "active": state["profile"],
        "revision_token": state["revision_token"],
        "runtime_revision_token": state["revision_token"],
        "sync_state": "current",
        "credential": {
            "state": state["credential_state"],
            "source": state["profile"]["source_mode"] if credential_set or state["credential_state"] == "LOCKED" else "NONE",
            "masked": "••••••••" if credential_set or state["credential_state"] == "LOCKED" else None,
            "reveal_supported": False,
        },
        "encryption": {"available": cipher is not None, "key_id": row["encryption_key_id"] if row else None, "configured_key_id": configured_id},
        "last_probe": last_probe,
        "available_models": _available_models(),
    }


async def get_status(db: AsyncSession) -> dict:
    state = _current(await _read_row(db))
    record = (await db.execute(select(AIConfigAudit).where(AIConfigAudit.action.in_(["PROBE_DRAFT", "PROBE_ACTIVE"])).order_by(AIConfigAudit.id.desc()).limit(1))).scalar_one_or_none()
    return _public_status(state, record.summary if record else None)


def _new_credential(payload: AIConfigDraft) -> str:
    return validate_credential(payload.api_key.get_secret_value() if payload.api_key is not None else "")


def _draft(state: dict, payload: AIConfigDraft) -> tuple[dict, str | None, str]:
    _check_revision(state, payload.base_revision_token)
    _require_unlocked(state)
    if payload.credential_action != "REPLACE" and payload.api_key is not None:
        raise AIConfigError("UNEXPECTED_CREDENTIAL", "Chỉ truyền credential mới khi chọn REPLACE.")
    if payload.source_mode == "ENV":
        profile, env_secret = _env_profile()
        if payload.credential_action == "REPLACE":
            raise AIConfigError("ENV_REPLACE_NOT_ALLOWED", "Để thay credential trong ứng dụng, hãy chọn nguồn DATABASE.")
        if payload.credential_action == "CLEAR":
            secret, credential_state = None, "CLEARED"
        elif state["profile"]["source_mode"] == "ENV" and state["credential_state"] == "CLEARED":
            secret, credential_state = None, "CLEARED"
        else:
            secret, credential_state = env_secret, "SET" if env_secret else "MISSING"
    else:
        base, binding = canonical_target(payload.base_url, payload.protocol)
        profile = {"source_mode": "DATABASE", "protocol": payload.protocol, "base_url": base,
                   "model": validate_model(payload.model), "auth_mode": payload.auth_mode, "credential_binding": binding}
        if payload.credential_action == "KEEP":
            if profile["credential_binding"] != state["profile"]["credential_binding"] or state["profile"]["source_mode"] != "DATABASE" or profile["auth_mode"] != state["profile"]["auth_mode"]:
                raise AIConfigError("TARGET_BINDING_CHANGED", "Đổi nguồn, giao thức, host, port, path hoặc auth yêu cầu REPLACE/CLEAR credential.")
            secret, credential_state = state["credential"], state["credential_state"]
        elif payload.credential_action == "REPLACE":
            if payload.auth_mode == "NONE":
                raise AIConfigError("UNEXPECTED_CREDENTIAL", "Chế độ NONE không nhận credential; chọn CLEAR.")
            secret, credential_state = _new_credential(payload), "SET"
        else:
            secret, credential_state = None, "CLEARED"
    if profile["auth_mode"] == "NONE":
        secret, credential_state = None, "CLEARED"
    return profile, secret, credential_state


async def _validate_network(profile: dict) -> None:
    try:
        await asyncio.wait_for(asyncio.to_thread(resolve_target_addresses, profile["base_url"], profile["credential_binding"]), timeout=5)
    except asyncio.TimeoutError:
        raise AIConfigError("DNS_TIMEOUT", "Phân giải địa chỉ API quá thời gian chờ.", 504) from None


def _audit(db: AsyncSession, actor_id: Any, action: str, revision: str, summary: dict | None = None) -> None:
    db.add(AIConfigAudit(actor_id=str(actor_id), action=action, revision_token=revision, summary=summary or {}))


async def apply_config(db: AsyncSession, payload: AIConfigDraft, actor_id: Any) -> dict:
    old = await _read_row(db)
    state = _current(old)
    profile, secret, credential_state = _draft(state, payload)
    await _validate_network(profile)
    cipher, key_id, _ = _key_info()
    ciphertext = None
    if profile["source_mode"] == "DATABASE" and secret:
        if cipher is None:
            raise AIConfigError("ENCRYPTION_KEY_UNAVAILABLE", "Cần khóa mã hóa riêng trước khi lưu credential; không lưu plaintext.", 503)
        ciphertext = cipher.encrypt(secret.encode()).decode()
    else:
        key_id = None
    values = {"version": (old["version"] + 1) if old else 1, "profile": profile,
              "credential_state": credential_state, "secret_ciphertext": ciphertext,
              "secret_fingerprint": _fingerprint(secret), "encryption_key_id": key_id,
              "updated_at": datetime.now(timezone.utc)}
    try:
        _check_revision(_current(await _read_row(db)), payload.base_revision_token)
        # CAS so sánh toàn bộ cột quan trọng: đổi secret trực tiếp mà quên tăng
        # version cũng không thể ghép credential mới vào draft cũ.
        if old:
            conditions = [getattr(AIRuntimeConfig, k) == old[k] for k in ("id", "version", "profile", "credential_state", "secret_ciphertext", "secret_fingerprint", "encryption_key_id")]
            result = await db.execute(update(AIRuntimeConfig).where(and_(*conditions)).values(**values).execution_options(synchronize_session=False))
            if result.rowcount != 1:
                raise AIConfigError("REVISION_CONFLICT", "Một quản trị viên khác vừa áp dụng cấu hình; hãy tải lại.", 409)
        else:
            db.add(AIRuntimeConfig(id=1, **values))
            await db.flush()
        revision = _current({"id": 1, **{k: v for k, v in values.items() if k != "updated_at"}})["revision_token"]
        _audit(db, actor_id, "APPLY", revision, {"source_mode": profile["source_mode"], "credential_action": payload.credential_action})
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AIConfigError("REVISION_CONFLICT", "Cấu hình đã được tạo bởi phiên khác; hãy tải lại.", 409) from None
    except Exception:
        await db.rollback()
        raise
    return _public_status(_current({"id": 1, **{k: v for k, v in values.items() if k != "updated_at"}}))


def _rate_limit(actor_id: Any) -> None:
    now = time.monotonic()
    with _RATE_LOCK:
        entries = _PROBE_STARTS[str(actor_id)]
        while entries and entries[0] <= now - 60:
            entries.popleft()
        if len(entries) >= max(1, settings.AI_PROBE_LIMIT_PER_MINUTE):
            raise AIConfigError("PROBE_RATE_LIMIT", "Đã đạt giới hạn kiểm tra kết nối; thử lại sau một phút.", 429)
        entries.append(now)
        # Chặn bộ nhớ tăng vô hạn khi có nhiều tài khoản.
        if len(_PROBE_STARTS) > 4096:
            for key in list(_PROBE_STARTS):
                if not _PROBE_STARTS[key] or _PROBE_STARTS[key][-1] <= now - 60:
                    del _PROBE_STARTS[key]


async def _run_probe(db: AsyncSession, snapshot: ConfigSnapshot, payload, actor_id: Any, action: str) -> dict:
    from app.services.ai_config.adapter import chat
    _rate_limit(actor_id)
    start = time.perf_counter()
    success, code, message, status_code = False, "PROBE_FAILED", "Không thể kiểm tra kết nối AI.", 502
    try:
        await chat(snapshot, [{"role": "user", "content": "Reply OK."}], max_tokens=8, timeout=8)
        success, code, message, status_code = True, "OK", "Kết nối AI thành công qua adapter đã cấu hình.", 200
    except AIConfigError as exc:
        code, message, status_code = exc.code, exc.message, exc.status_code
    result = {"success": success, "code": code, "message": message, "status_code": status_code,
              "latency_ms": round((time.perf_counter() - start) * 1000, 1), "model_used": snapshot.model,
              "base_url": snapshot.base_url, "tested_at": datetime.now(timezone.utc).isoformat(),
              "probe_request_id": payload.probe_request_id, "draft_digest": payload.draft_digest,
              "base_revision_token": payload.base_revision_token}
    _audit(db, actor_id, action, snapshot.revision_token, result)
    await db.commit()
    return result


async def probe_draft(db: AsyncSession, payload: AIConfigProbe, actor_id: Any) -> dict:
    state = _current(await _read_row(db))
    profile, secret, _ = _draft(state, payload)
    snapshot = _snapshot(profile, secret, payload.base_revision_token, require_credential=False)
    return await _run_probe(db, snapshot, payload, actor_id, "PROBE_DRAFT")


async def probe_active(db: AsyncSession, payload: AIActiveProbe, actor_id: Any) -> dict:
    state = _current(await _read_row(db))
    _check_revision(state, payload.base_revision_token)
    _require_unlocked(state)
    snapshot = _snapshot(state["profile"], state["credential"], state["revision_token"], require_credential=False)
    return await _run_probe(db, snapshot, payload, actor_id, "PROBE_ACTIVE")
