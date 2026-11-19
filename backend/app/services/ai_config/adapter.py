"""HTTP adapter với DNS pinning, không redirect, ngân sách và lỗi đã khử bí mật."""
import asyncio
import json
import math
import queue
import threading
import time
import weakref
from urllib.parse import quote, urlsplit
import httpx
from app.core.ai_runtime import AIConfigError, ConfigSnapshot, canonical_target, resolve_target_addresses, validate_model, validate_credential


_MAX_BODY_BYTES = 2 * 1024 * 1024
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_SEMAPHORES: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
_SYNC_SLOTS = threading.BoundedSemaphore(3)


def _semaphore() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    if loop not in _SEMAPHORES:
        _SEMAPHORES[loop] = asyncio.Semaphore(3)
    return _SEMAPHORES[loop]


def _validate_snapshot(snapshot: ConfigSnapshot) -> None:
    _, actual = canonical_target(snapshot.base_url, snapshot.protocol)
    if actual != snapshot.binding:
        raise AIConfigError("TARGET_BINDING_MISMATCH", "Đích gửi không khớp credential đã chụp.")
    validate_model(snapshot.model)
    if snapshot.auth_mode not in {"NONE", "BEARER"}:
        raise AIConfigError("INVALID_AUTH_MODE", "Chế độ xác thực chưa được hỗ trợ.")
    if snapshot.auth_mode == "BEARER" and snapshot.credential:
        validate_credential(snapshot.credential)
    if snapshot.auth_mode == "BEARER" and not snapshot.credential:
        raise AIConfigError("UNCONFIGURED_CREDENTIAL", "Credential đang trống hoặc đã CLEAR; không dùng lại ENV.", 409)


def _pinned_request(snapshot: ConfigSnapshot, address: str, suffix: str) -> tuple[str, dict, dict]:
    host = snapshot.binding["host"]
    port = snapshot.binding["port"]
    scheme = snapshot.binding["scheme"]
    ip_host = f"[{address}]" if ":" in address else address
    named_host = f"[{host}]" if ":" in host else host
    default_port = 443 if scheme == "https" else 80
    authority = named_host if port == default_port else f"{named_host}:{port}"
    path = urlsplit(snapshot.base_url).path
    url = f"{scheme}://{ip_host}:{port}{path}{suffix}"
    headers = {"Host": authority, "Accept": "application/json", "Content-Type": "application/json"}
    if snapshot.auth_mode == "BEARER":
        headers["Authorization"] = f"Bearer {snapshot.credential}"
    # DNS không được gọi lần hai sau kiểm tra: kết nối IP đã xác thực nhưng
    # giữ hostname gốc cho TLS SNI/certificate verification và virtual host.
    return url, headers, {"sni_hostname": host}


def _safe_json(raw: bytes, status_code: int):
    if 300 <= status_code < 400:
        raise AIConfigError("REDIRECT_BLOCKED", "API trả redirect; request không được chuyển tiếp và credential không được gửi tới đích mới.", 502)
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError):
        data = None
    error = data.get("error") if isinstance(data, dict) else None
    if status_code >= 400 or error:
        # Chỉ dùng provider body để phân loại, không bao giờ trả body/message thô.
        text = json.dumps(error or {}, ensure_ascii=True).lower()
        if "insufficient_quota" in text or "insufficient balance" in text or status_code == 402:
            raise AIConfigError("QUOTA_EXCEEDED", "Provider báo hết hạn mức hoặc số dư.", 429)
        if status_code == 401 or "invalid_api_key" in text or "authentication" in text:
            raise AIConfigError("AUTHENTICATION_FAILED", "Provider từ chối credential.", 401)
        if isinstance(error, dict) and error.get("code") == "client_not_allowed":
            raise AIConfigError("CLIENT_NOT_ALLOWED", "Nhà cung cấp chỉ cho phép các công cụ lập trình, chưa cho ứng dụng này gọi API trực tiếp. Hãy dùng endpoint hoặc quyền truy cập dành cho ứng dụng.", 403)
        if status_code == 403 or "permission" in text:
            raise AIConfigError("PERMISSION_DENIED", "Credential không có quyền thực hiện tác vụ/model.", 403)
        if status_code == 404 or "model_not_found" in text or "invalid_model" in text:
            raise AIConfigError("MODEL_NOT_FOUND", "Provider không hỗ trợ model hoặc đường dẫn cấu hình.", 404)
        if status_code == 429 or "rate_limit" in text:
            raise AIConfigError("RATE_LIMITED", "Provider đang giới hạn tốc độ request.", 429)
        if status_code in {400, 422}:
            raise AIConfigError("PROTOCOL_ERROR", "Provider không chấp nhận giao thức hoặc schema request.", 502)
        raise AIConfigError("PROVIDER_ERROR", "Provider trả lỗi; chưa có kết quả hợp lệ.", 502)
    if not isinstance(data, dict):
        raise AIConfigError("PROTOCOL_ERROR", "Provider trả dữ liệu không đúng JSON object.", 502)
    return data


def _redact(value, secret: str | None):
    if not secret:
        return value
    if isinstance(value, str):
        return value.replace(secret, "[REDACTED]")
    if isinstance(value, list):
        return [_redact(item, secret) for item in value]
    if isinstance(value, dict):
        return {str(key).replace(secret, "[REDACTED]"): _redact(item, secret) for key, item in value.items()}
    return value


def _body(data: dict | None) -> bytes | None:
    if data is None:
        return None
    try:
        body = json.dumps(data, ensure_ascii=False, allow_nan=False).encode()
    except (ValueError, TypeError):
        raise AIConfigError("INVALID_REQUEST", "Nội dung request AI không hợp lệ.") from None
    if len(body) > _MAX_BODY_BYTES:
        raise AIConfigError("CONTEXT_LIMIT", "Nội dung request vượt ngân sách AI.", 413)
    return body


async def _request_json(snapshot: ConfigSnapshot, suffix: str, data: dict | None = None, *, timeout: float = 20) -> dict:
    _validate_snapshot(snapshot)
    body = _body(data)
    async def run():
        async with _semaphore():
            addresses = await asyncio.to_thread(resolve_target_addresses, snapshot.base_url, snapshot.binding)
            url, headers, extensions = _pinned_request(snapshot, addresses[0], suffix)
            async with httpx.AsyncClient(timeout=httpx.Timeout(min(max(timeout, 1), 30)), follow_redirects=False, trust_env=False) as client:
                async with client.stream("POST" if data is not None else "GET", url, headers=headers, content=body, extensions=extensions) as response:
                    # Cấm redirect trước cả khi đọc body.
                    if 300 <= response.status_code < 400:
                        return _safe_json(b"{}", response.status_code)
                    chunks = bytearray()
                    async for chunk in response.aiter_bytes():
                        chunks.extend(chunk)
                        if len(chunks) > _MAX_RESPONSE_BYTES:
                            raise AIConfigError("RESPONSE_LIMIT", "Phản hồi provider vượt giới hạn.", 502)
                    return _redact(_safe_json(bytes(chunks), response.status_code), snapshot.credential)
    try:
        return await asyncio.wait_for(run(), timeout=min(max(timeout, 1), 30))
    except (asyncio.TimeoutError, httpx.TimeoutException):
        raise AIConfigError("TIMEOUT", "API AI quá thời gian chờ.", 504) from None
    except httpx.RequestError:
        raise AIConfigError("NETWORK_ERROR", "Không kết nối được máy chủ AI.", 503) from None


def _request_json_sync_worker(snapshot: ConfigSnapshot, suffix: str, data: dict | None = None, *, timeout: float = 20) -> dict:
    _validate_snapshot(snapshot)
    body = _body(data)
    deadline = time.monotonic() + min(max(timeout, 1), 30)
    addresses = resolve_target_addresses(snapshot.base_url, snapshot.binding)
    if time.monotonic() >= deadline:
        raise AIConfigError("TIMEOUT", "API AI quá thời gian chờ trước khi kết nối.", 504)
    url, headers, extensions = _pinned_request(snapshot, addresses[0], suffix)
    try:
        with httpx.Client(timeout=httpx.Timeout(min(max(timeout, 1), 30)), follow_redirects=False, trust_env=False) as client:
            with client.stream("POST" if data is not None else "GET", url, headers=headers, content=body, extensions=extensions) as response:
                if 300 <= response.status_code < 400:
                    return _safe_json(b"{}", response.status_code)
                chunks = bytearray()
                for chunk in response.iter_bytes():
                    if time.monotonic() >= deadline:
                        raise AIConfigError("TIMEOUT", "API AI quá thời gian chờ.", 504)
                    chunks.extend(chunk)
                    if len(chunks) > _MAX_RESPONSE_BYTES:
                        raise AIConfigError("RESPONSE_LIMIT", "Phản hồi provider vượt giới hạn.", 502)
                return _redact(_safe_json(bytes(chunks), response.status_code), snapshot.credential)
    except httpx.TimeoutException:
        raise AIConfigError("TIMEOUT", "API AI quá thời gian chờ.", 504) from None
    except httpx.RequestError:
        raise AIConfigError("NETWORK_ERROR", "Không kết nối được máy chủ AI.", 503) from None



def _request_json_sync(snapshot: ConfigSnapshot, suffix: str, data: dict | None = None, *, timeout: float = 20) -> dict:
    # Cả DNS lẫn HTTP sync phải có deadline. Worker daemon giữ slot tới khi
    # đóng client; DNS hệ điều hành bị treo không sinh vô hạn worker mới.
    _validate_snapshot(snapshot)
    budget = min(max(timeout, 1), 30)
    started = time.monotonic()
    if not _SYNC_SLOTS.acquire(timeout=min(budget, 1)):
        raise AIConfigError("AI_BUSY", "Đã đạt giới hạn tác vụ AI đồng thời.", 429)
    outcome = queue.Queue(maxsize=1)
    def work():
        try:
            outcome.put((_request_json_sync_worker(snapshot, suffix, data, timeout=budget), None))
        except AIConfigError as error:
            outcome.put((None, error))
        except Exception:
            outcome.put((None, AIConfigError("PROVIDER_ERROR", "Không thể xử lý phản hồi AI.", 502)))
        finally:
            _SYNC_SLOTS.release()
    threading.Thread(target=work, daemon=True, name="ai-http-bounded").start()
    try:
        result, error = outcome.get(timeout=max(0.01, budget - (time.monotonic() - started)))
    except queue.Empty:
        raise AIConfigError("TIMEOUT", "API AI quá thời gian chờ.", 504) from None
    if error:
        raise error
    return result


def _chat_body(snapshot: ConfigSnapshot, messages: list[dict], max_tokens: int, response_format: dict | None) -> dict:
    if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= 4096:
        raise AIConfigError("TOKEN_BUDGET", "Ngân sách đầu ra phải từ 1 đến 4096 token.")
    if not isinstance(messages, list) or not 1 <= len(messages) <= 32:
        raise AIConfigError("CONTEXT_LIMIT", "Số lượt hội thoại AI vượt giới hạn.")
    for message in messages:
        if not isinstance(message, dict) or message.get("role") not in {"system", "user", "assistant"}:
            raise AIConfigError("INVALID_REQUEST", "Vai trò hội thoại AI không được hỗ trợ.")
        if isinstance(message.get("content"), str) and len(message["content"]) > 64000:
            raise AIConfigError("CONTEXT_LIMIT", "Ngữ cảnh văn bản vượt giới hạn.")
    body = {"model": snapshot.model, "messages": messages, "max_tokens": max_tokens, "temperature": 0}
    if response_format is not None:
        if response_format != {"type": "json_object"}:
            raise AIConfigError("INVALID_REQUEST", "Chỉ hỗ trợ JSON object cho đầu ra có cấu trúc.")
        body["response_format"] = response_format
    return body


def _chat_text(data: dict) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise AIConfigError("PROTOCOL_ERROR", "Provider thiếu choices trong phản hồi chat.", 502)
    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str) or not message["content"].strip():
        raise AIConfigError("PROTOCOL_ERROR", "Provider không trả nội dung chat hợp lệ.", 502)
    if choice.get("finish_reason") in {"length", "content_filter", "tool_calls", "function_call"}:
        raise AIConfigError("INCOMPLETE_OUTPUT", "Phản hồi AI chưa hoàn tất hoặc bị chặn; không dùng như kết quả hoàn chỉnh.", 502)
    return message["content"]


async def chat(snapshot: ConfigSnapshot, messages: list[dict], *, max_tokens: int = 1024, timeout: float = 20, response_format: dict | None = None) -> str:
    return _chat_text(await _request_json(snapshot, "/chat/completions", _chat_body(snapshot, messages, max_tokens, response_format), timeout=timeout))


def chat_sync(snapshot: ConfigSnapshot, messages: list[dict], *, max_tokens: int = 1024, timeout: float = 20, response_format: dict | None = None) -> str:
    return _chat_text(_request_json_sync(snapshot, "/chat/completions", _chat_body(snapshot, messages, max_tokens, response_format), timeout=timeout))


async def embeddings(snapshot: ConfigSnapshot, text: str, *, dimensions: int = 1536) -> list[float]:
    if not isinstance(text, str) or not text.strip() or len(text) > 16000:
        raise AIConfigError("CONTEXT_LIMIT", "Văn bản embedding phải có nội dung và không quá 16000 ký tự.")
    data = await _request_json(snapshot, "/embeddings", {"model": validate_model(snapshot.embedding_model), "input": text})
    records = data.get("data")
    vector = records[0].get("embedding") if isinstance(records, list) and records and isinstance(records[0], dict) else None
    if not isinstance(vector, list) or len(vector) != dimensions or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in vector):
        raise AIConfigError("PROTOCOL_ERROR", "Vector embedding không đúng số chiều hoặc kiểu dữ liệu.", 502)
    return vector


async def list_models(snapshot: ConfigSnapshot) -> list[dict]:
    data = await _request_json(snapshot, "/models")
    models = data.get("data")
    if not isinstance(models, list) or len(models) > 10000 or any(not isinstance(m, dict) or not isinstance(m.get("id"), str) for m in models):
        raise AIConfigError("PROTOCOL_ERROR", "Danh sách model không đúng schema.", 502)
    return models


async def model_details(snapshot: ConfigSnapshot) -> dict:
    return await _request_json(snapshot, "/models/" + quote(validate_model(snapshot.model), safe=""))
