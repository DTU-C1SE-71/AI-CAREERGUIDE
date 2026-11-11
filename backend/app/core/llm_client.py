"""
Quản lý kết nối OpenAI-compatible LLM & Tự động tối đa hóa giới hạn Token theo API Key / Model.

- Tự động truy vấn `/v1/models` (có cache TTL 10 phút) để lấy đúng `maxOutput` /
  `max_completion_tokens` và `contextWindow` lớn nhất mà API key & model đang dùng hỗ trợ.
- Cho phép mọi prompt (Explainable AI, Chat Cố vấn, Aspiration Agent, Trend Hunter Agent,
  Stream A Vision OCR, Stream B Discovery) sử dụng trọn vẹn ngưỡng token tối đa thay vì bị cắt cụt.
"""

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_CAPS_CACHE_TTL_SECONDS = 600.0
_MODEL_CAPS_CACHE: Dict[str, Tuple[float, Dict[str, int]]] = {}


def _cache_key(base_url: str, api_key: str, model: str) -> str:
    key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12]
    return f"{base_url.rstrip('/')}|{key_hash}|{model.strip().lower()}"


def _is_mock_or_test_key(api_key: str) -> bool:
    k = (api_key or "").strip()
    if not k or settings.ENVIRONMENT == "test":
        return True
    if k.startswith(("sk-test", "mock", "your-", "your_")):
        return True
    return False


def _match_model_record(models: List[Dict[str, Any]], target_model: str) -> Optional[Dict[str, Any]]:
    t = (target_model or "").strip().lower()
    if not t:
        return None
    # 1. Khớp chính xác hoàn toàn
    for m in models:
        mid = str(m.get("id") or "").strip().lower()
        if mid == t:
            return m
    # 2. Khớp hậu tố có tiền tố nhà cung cấp (vd 'cx/gpt-6-luna' <-> 'gpt-6-luna')
    for m in models:
        mid = str(m.get("id") or "").strip().lower()
        if mid.endswith(f"/{t}") or t.endswith(f"/{mid}"):
            return m
    return None


def _parse_capabilities(entry: Optional[Dict[str, Any]]) -> Dict[str, int]:
    default_max_out = max(1024, int(getattr(settings, "LLM_MAX_TOKENS", 128000)))
    default_ctx = max(16384, int(getattr(settings, "LLM_MAX_CONTEXT_TOKENS", 272000)))
    if not isinstance(entry, dict):
        return {
            "max_output_tokens": default_max_out,
            "context_window": default_ctx,
            "max_context_chars": max(60000, int(getattr(settings, "LLM_MAX_CONTEXT_CHARS", 240000))),
        }

    caps = entry.get("capabilities") if isinstance(entry.get("capabilities"), dict) else {}
    raw_out = (
        caps.get("maxOutput")
        or entry.get("max_completion_tokens")
        or entry.get("max_output_tokens")
        or entry.get("max_tokens")
    )
    raw_ctx = (
        caps.get("contextWindow")
        or entry.get("context_length")
        or entry.get("max_model_len")
    )

    try:
        max_out = int(raw_out) if raw_out else default_max_out
    except (TypeError, ValueError):
        max_out = default_max_out

    try:
        ctx_win = int(raw_ctx) if raw_ctx else default_ctx
    except (TypeError, ValueError):
        ctx_win = default_ctx

    # Đảm bảo an toàn biên tối thiểu & tối đa theo model thực tế
    max_out = max(1024, max_out)
    ctx_win = max(max_out, ctx_win)
    # Ước lượng an toàn số ký tự input cho tiếng Việt (~2.2-2.5 ký tự/token, chừa chỗ cho output)
    usable_input_tokens = max(8192, ctx_win - min(max_out, ctx_win // 2))
    max_ctx_chars = max(int(getattr(settings, "LLM_MAX_CONTEXT_CHARS", 240000)), usable_input_tokens * 2)

    return {
        "max_output_tokens": max_out,
        "context_window": ctx_win,
        "max_context_chars": min(max_ctx_chars, 900000),
    }


async def resolve_model_token_limits(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, int]:
    """
    Lấy giới hạn token đầu ra tối đa (`max_output_tokens`) và ngữ cảnh (`context_window`)
    cho API Key & Model hiện tại (tự động đọc từ `/v1/models`, cache 10 phút).
    """
    eff_key = (api_key if api_key is not None else settings.OPENAI_API_KEY) or ""
    eff_base = ((base_url if base_url is not None else settings.OPENAI_BASE_URL) or "https://api.openai.com/v1").rstrip("/")
    eff_model = (model if model is not None else settings.LLM_MODEL) or ""

    if _is_mock_or_test_key(eff_key):
        return _parse_capabilities(None)

    ck = _cache_key(eff_base, eff_key, eff_model)
    now = time.monotonic()
    cached = _MODEL_CAPS_CACHE.get(ck)
    if cached and (now - cached[0]) < _CAPS_CACHE_TTL_SECONDS:
        return dict(cached[1])

    parsed = _parse_capabilities(None)
    try:
        async with httpx.AsyncClient(timeout=4.0) as http:
            resp = await http.get(
                f"{eff_base}/models",
                headers={"Authorization": f"Bearer {eff_key.strip()}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                models_list = data.get("data") if isinstance(data, dict) else None
                if isinstance(models_list, list):
                    matched = _match_model_record(models_list, eff_model)
                    parsed = _parse_capabilities(matched)
    except Exception as exc:
        logger.debug("Không truy vấn được /models (%s), dùng giới hạn cấu hình tối đa: %s", exc, parsed["max_output_tokens"])

    _MODEL_CAPS_CACHE[ck] = (now, parsed)
    return dict(parsed)


def resolve_model_token_limits_sync(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, int]:
    """Phiên bản đồng bộ dùng cho pipeline OCR Vision / Stream A."""
    eff_key = (api_key if api_key is not None else settings.OPENAI_API_KEY) or ""
    eff_base = ((base_url if base_url is not None else settings.OPENAI_BASE_URL) or "https://api.openai.com/v1").rstrip("/")
    eff_model = (model if model is not None else settings.VISION_LLM_MODEL) or settings.LLM_MODEL

    if _is_mock_or_test_key(eff_key):
        return _parse_capabilities(None)

    ck = _cache_key(eff_base, eff_key, eff_model)
    now = time.monotonic()
    cached = _MODEL_CAPS_CACHE.get(ck)
    if cached and (now - cached[0]) < _CAPS_CACHE_TTL_SECONDS:
        return dict(cached[1])

    parsed = _parse_capabilities(None)
    try:
        resp = httpx.get(
            f"{eff_base}/models",
            headers={"Authorization": f"Bearer {eff_key.strip()}"},
            timeout=4.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            models_list = data.get("data") if isinstance(data, dict) else None
            if isinstance(models_list, list):
                matched = _match_model_record(models_list, eff_model)
                parsed = _parse_capabilities(matched)
    except Exception as exc:
        logger.debug("Sync /models check skip (%s), dùng mặc định %s", exc, parsed["max_output_tokens"])

    _MODEL_CAPS_CACHE[ck] = (now, parsed)
    return dict(parsed)


def clear_model_caps_cache() -> None:
    """Xóa cache khi Admin cập nhật API Key / Base URL / Model mới."""
    _MODEL_CAPS_CACHE.clear()
