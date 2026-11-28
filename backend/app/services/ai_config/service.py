"""Cấu hình AI chỉ đọc từ ENV/.env và cung cấp snapshot bất biến cho adapter."""
import hashlib
import hmac
import os
from pathlib import Path
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.ai_runtime import AIConfigError, ConfigSnapshot, canonical_target, digest, validate_model, validate_credential


_ENV_CANDIDATES: tuple[Path, ...] = (
    Path(".env"),
    Path("backend/.env"),
    Path("/app/.env"),
    Path(__file__).resolve().parents[3] / ".env",
)


def _safe_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime if path.is_file() else -1.0
    except OSError:
        return -1.0


_BOOT_ENV_MTIMES: dict[Path, float] = {p: _safe_mtime(p) for p in _ENV_CANDIDATES}


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return values
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, raw_val = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        val = raw_val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in {"'", '"'}:
            val = val[1:-1]
        elif val.startswith(("'", '"')):
            quote = val[0]
            end = val.find(quote, 1)
            val = val[1:end] if end != -1 else val.split("#", 1)[0].strip()
        else:
            val = val.split("#", 1)[0].strip()
        values[key] = val
    return values


def _read_env_setting(name: str, fallback: str) -> str:
    if getattr(settings, "ENVIRONMENT", "") == "test":
        val = getattr(settings, name, fallback)
        return fallback if val is None else str(val)

    parsed_file_value: str | None = None
    for path in _ENV_CANDIDATES:
        mtime = _safe_mtime(path)
        if mtime < 0:
            continue
        parsed = _parse_env_file(path)
        candidate = parsed.get(name, "")
        if mtime > _BOOT_ENV_MTIMES.get(path, -1.0):
            if candidate:
                return candidate
        elif parsed_file_value is None and candidate:
            parsed_file_value = candidate

    return os.environ.get(name) or parsed_file_value or getattr(settings, name, fallback) or fallback


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
    protocol = _read_env_setting("LLM_PROTOCOL", settings.LLM_PROTOCOL)
    base_url = _read_env_setting("LLM_BASE_URL", settings.LLM_BASE_URL)
    base, binding = canonical_target(base_url, protocol)
    auth = _read_env_setting("LLM_AUTH_MODE", settings.LLM_AUTH_MODE)
    if auth not in {"BEARER", "NONE"}:
        raise AIConfigError("INVALID_AUTH_MODE", "Chế độ xác thực trong ENV không được hỗ trợ.")
    model = validate_model(_read_env_setting("LLM_MODEL", settings.LLM_MODEL))
    api_key = _read_env_setting("LLM_API_KEY", settings.LLM_API_KEY)
    return {
        "source_mode": "ENV", "protocol": protocol,
        "base_url": base, "model": model,
        "auth_mode": auth, "credential_binding": binding,
    }, (api_key or None) if auth == "BEARER" else None


def _fingerprint(secret: str | None) -> str | None:
    return hashlib.sha256(secret.encode()).hexdigest() if secret else None


def _current() -> dict:
    profile, secret = _env_profile()
    if profile["auth_mode"] == "NONE":
        secret = None
        state = "CLEARED"
    else:
        state = "SET" if secret else "MISSING"
    token = digest({
        "profile": profile,
        "credential_fingerprint": _fingerprint(secret),
        "embedding_model": settings.EMBEDDING_MODEL,
    })
    return {
        "profile": profile,
        "credential": secret,
        "credential_state": state,
        "revision_token": token,
    }


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
    del db
    state = _current()
    return _snapshot(state["profile"], state["credential"], state["revision_token"], not allow_unconfigured)


def _available_models() -> list[str]:
    raw = _read_env_setting("LLM_AVAILABLE_MODELS", settings.LLM_AVAILABLE_MODELS or "")
    items: list[str] = []
    for part in raw.replace("\n", ",").split(","):
        model_id = part.strip()
        if model_id and model_id not in items:
            items.append(model_id)
    default_model = _read_env_setting("LLM_MODEL", settings.LLM_MODEL or "").strip()
    if default_model and default_model not in items:
        items.insert(0, default_model)
    return items


def _public_status(state: dict, last_probe: dict | None = None) -> dict:
    cipher, configured_id, _ = _key_info()
    credential_set = state["credential_state"] == "SET"
    return {
        "persisted": None,
        "active": state["profile"],
        "revision_token": state["revision_token"],
        "runtime_revision_token": state["revision_token"],
        "sync_state": "current",
        "credential": {
            "state": state["credential_state"],
            "source": state["profile"]["source_mode"] if credential_set else "NONE",
            "masked": "••••••••" if credential_set else None,
            "reveal_supported": False,
        },
        "encryption": {"available": cipher is not None, "key_id": None, "configured_key_id": configured_id},
        "last_probe": last_probe,
        "available_models": _available_models(),
    }


async def get_status(db: AsyncSession | None = None) -> dict:
    del db
    return _public_status(_current(), None)
