"""HTTP adapter với DNS pinning, không redirect, retry lỗi tạm thời, ngân sách và lỗi đã khử bí mật."""
import asyncio
import json
import logging
import math
import queue
import random
import threading
import time
import weakref
from typing import AsyncIterator, Callable, TypeVar
from urllib.parse import quote, urlsplit
import httpx
from app.core.ai_runtime import AIConfigError, ConfigSnapshot, canonical_target, resolve_target_addresses, validate_model, validate_credential


logger = logging.getLogger(__name__)
_T = TypeVar("_T")

_MAX_BODY_BYTES = 2 * 1024 * 1024
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_MAX_TRANSIENT_RETRIES = 2
_TRANSIENT_RETRY_CODES = frozenset({"PROVIDER_ERROR", "RATE_LIMITED", "NETWORK_ERROR"})
_SEMAPHORES: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
_SYNC_SLOTS = threading.BoundedSemaphore(3)


class _EmptyContentError(Exception):
    """Tín hiệu nội bộ khi provider trả HTTP 200 nhưng content trống để retry an toàn."""


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


def _compute_retry_delay(attempt: int, err_code: str, deadline: float) -> float | None:
    if attempt >= _MAX_TRANSIENT_RETRIES:
        return None
    if err_code not in _TRANSIENT_RETRY_CODES and err_code not in {"TIMEOUT", "EMPTY_RESPONSE"}:
        return None
    remaining = deadline - time.monotonic()
    if remaining < 2.5:
        return None
    if err_code == "TIMEOUT" and remaining < 4.0:
        return None
    base_delay = 0.8 if attempt == 0 else 1.8
    jitter = random.uniform(0.0, 0.25)
    max_delay = remaining - 2.0
    if max_delay <= 0:
        return None
    return min(base_delay + jitter, max_delay)


async def _single_async_attempt(snapshot: ConfigSnapshot, suffix: str, body: bytes | None, attempt_timeout: float) -> dict:
    async with _semaphore():
        addresses = await asyncio.to_thread(resolve_target_addresses, snapshot.base_url, snapshot.binding)
        url, headers, extensions = _pinned_request(snapshot, addresses[0], suffix)
        async with httpx.AsyncClient(timeout=httpx.Timeout(min(max(attempt_timeout, 0.1), 90)), follow_redirects=False, trust_env=False) as client:
            async with client.stream("POST" if body is not None else "GET", url, headers=headers, content=body, extensions=extensions) as response:
                # Cấm redirect trước cả khi đọc body.
                if 300 <= response.status_code < 400:
                    return _safe_json(b"{}", response.status_code)
                chunks = bytearray()
                async for chunk in response.aiter_bytes():
                    chunks.extend(chunk)
                    if len(chunks) > _MAX_RESPONSE_BYTES:
                        raise AIConfigError("RESPONSE_LIMIT", "Phản hồi provider vượt giới hạn.", 502)
                return _redact(_safe_json(bytes(chunks), response.status_code), snapshot.credential)


async def _request_json(
    snapshot: ConfigSnapshot,
    suffix: str,
    data: dict | None = None,
    *,
    timeout: float = 20,
    post_process: Callable[[dict], _T] | None = None,
) -> dict | _T:
    _validate_snapshot(snapshot)
    body = _body(data)
    budget = min(max(timeout, 1), 90)
    deadline = time.monotonic() + budget
    for attempt in range(_MAX_TRANSIENT_RETRIES + 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AIConfigError("TIMEOUT", "API AI quá thời gian chờ.", 504)
        attempt_timeout = min(remaining, budget)
        err: AIConfigError | None = None
        err_code: str = ""
        try:
            payload = await asyncio.wait_for(_single_async_attempt(snapshot, suffix, body, attempt_timeout), timeout=attempt_timeout)
            return post_process(payload) if post_process is not None else payload
        except _EmptyContentError:
            err = AIConfigError("PROTOCOL_ERROR", "Provider không trả nội dung chat hợp lệ.", 502)
            err_code = "EMPTY_RESPONSE"
        except (asyncio.TimeoutError, httpx.TimeoutException):
            err = AIConfigError("TIMEOUT", "API AI quá thời gian chờ.", 504)
            err_code = "TIMEOUT"
        except httpx.RequestError:
            err = AIConfigError("NETWORK_ERROR", "Không kết nối được máy chủ AI.", 503)
            err_code = "NETWORK_ERROR"
        except AIConfigError as exc:
            err = exc
            err_code = exc.code

        delay = _compute_retry_delay(attempt, err_code, deadline)
        if delay is None:
            raise err from None
        logger.warning(
            "Transient AI miss (%s) on %s (attempt %d/%d); retrying in %.2fs",
            err_code, suffix, attempt + 1, _MAX_TRANSIENT_RETRIES + 1, delay,
        )
        # Semaphore đã được giải phóng trước khi ngủ backoff để không làm nghẽn request khác.
        await asyncio.sleep(delay)
    raise AIConfigError("PROVIDER_ERROR", "Không thể xử lý phản hồi AI.", 502)


def _request_json_sync_worker(
    snapshot: ConfigSnapshot,
    suffix: str,
    data: dict | None = None,
    *,
    timeout: float = 20,
    post_process: Callable[[dict], _T] | None = None,
) -> dict | _T:
    _validate_snapshot(snapshot)
    body = _body(data)
    budget = min(max(timeout, 1), 90)
    deadline = time.monotonic() + budget
    for attempt in range(_MAX_TRANSIENT_RETRIES + 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AIConfigError("TIMEOUT", "API AI quá thời gian chờ.", 504)
        attempt_timeout = min(remaining, budget)
        err: AIConfigError | None = None
        err_code: str = ""
        try:
            addresses = resolve_target_addresses(snapshot.base_url, snapshot.binding)
            if time.monotonic() >= deadline:
                raise AIConfigError("TIMEOUT", "API AI quá thời gian chờ trước khi kết nối.", 504)
            url, headers, extensions = _pinned_request(snapshot, addresses[0], suffix)
            with httpx.Client(timeout=httpx.Timeout(min(max(attempt_timeout, 0.1), 90)), follow_redirects=False, trust_env=False) as client:
                with client.stream("POST" if body is not None else "GET", url, headers=headers, content=body, extensions=extensions) as response:
                    if 300 <= response.status_code < 400:
                        payload = _safe_json(b"{}", response.status_code)
                    else:
                        chunks = bytearray()
                        for chunk in response.iter_bytes():
                            if time.monotonic() >= deadline:
                                raise AIConfigError("TIMEOUT", "API AI quá thời gian chờ.", 504)
                            chunks.extend(chunk)
                            if len(chunks) > _MAX_RESPONSE_BYTES:
                                raise AIConfigError("RESPONSE_LIMIT", "Phản hồi provider vượt giới hạn.", 502)
                        payload = _redact(_safe_json(bytes(chunks), response.status_code), snapshot.credential)
            return post_process(payload) if post_process is not None else payload
        except _EmptyContentError:
            err = AIConfigError("PROTOCOL_ERROR", "Provider không trả nội dung chat hợp lệ.", 502)
            err_code = "EMPTY_RESPONSE"
        except httpx.TimeoutException:
            err = AIConfigError("TIMEOUT", "API AI quá thời gian chờ.", 504)
            err_code = "TIMEOUT"
        except httpx.RequestError:
            err = AIConfigError("NETWORK_ERROR", "Không kết nối được máy chủ AI.", 503)
            err_code = "NETWORK_ERROR"
        except AIConfigError as exc:
            err = exc
            err_code = exc.code

        delay = _compute_retry_delay(attempt, err_code, deadline)
        if delay is None:
            raise err from None
        logger.warning(
            "Transient AI sync miss (%s) on %s (attempt %d/%d); retrying in %.2fs",
            err_code, suffix, attempt + 1, _MAX_TRANSIENT_RETRIES + 1, delay,
        )
        time.sleep(delay)
    raise AIConfigError("PROVIDER_ERROR", "Không thể xử lý phản hồi AI.", 502)



def _request_json_sync(
    snapshot: ConfigSnapshot,
    suffix: str,
    data: dict | None = None,
    *,
    timeout: float = 20,
    post_process: Callable[[dict], _T] | None = None,
) -> dict | _T:
    # Cả DNS lẫn HTTP sync phải có deadline. Worker daemon giữ slot tới khi
    # đóng client; DNS hệ điều hành bị treo không sinh vô hạn worker mới.
    _validate_snapshot(snapshot)
    budget = min(max(timeout, 1), 90)
    started = time.monotonic()
    if not _SYNC_SLOTS.acquire(timeout=min(budget, 1)):
        raise AIConfigError("AI_BUSY", "Đã đạt giới hạn tác vụ AI đồng thời.", 429)
    outcome = queue.Queue(maxsize=1)
    def work():
        try:
            outcome.put((_request_json_sync_worker(snapshot, suffix, data, timeout=budget, post_process=post_process), None))
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
    if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= 65536:
        raise AIConfigError("TOKEN_BUDGET", "Ngân sách đầu ra phải từ 1 đến 65536 token.")
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


def _chat_text(data: dict, *, allow_empty_retry: bool = False) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise AIConfigError("PROTOCOL_ERROR", "Provider thiếu choices trong phản hồi chat.", 502)
    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict):
        raise AIConfigError("PROTOCOL_ERROR", "Provider không trả nội dung chat hợp lệ.", 502)
    if choice.get("finish_reason") in {"length", "content_filter", "tool_calls", "function_call"}:
        raise AIConfigError("INCOMPLETE_OUTPUT", "Phản hồi AI chưa hoàn tất hoặc bị chặn; không dùng như kết quả hoàn chỉnh.", 502)
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        if allow_empty_retry:
            raise _EmptyContentError()
        raise AIConfigError("PROTOCOL_ERROR", "Provider không trả nội dung chat hợp lệ.", 502)
    return content


async def chat(snapshot: ConfigSnapshot, messages: list[dict], *, max_tokens: int = 1024, timeout: float = 20, response_format: dict | None = None) -> str:
    return await _request_json(
        snapshot,
        "/chat/completions",
        _chat_body(snapshot, messages, max_tokens, response_format),
        timeout=timeout,
        post_process=lambda payload: _chat_text(payload, allow_empty_retry=True),
    )


async def chat_stream(
    snapshot: ConfigSnapshot,
    messages: list[dict],
    *,
    max_tokens: int = 1024,
    timeout: float = 90,
) -> AsyncIterator[str]:
    """Stream chat completion text deltas over OpenAI-compatible SSE with DNS pinning & secret redaction."""
    _validate_snapshot(snapshot)
    req_data = _chat_body(snapshot, messages, max_tokens, None)
    req_data["stream"] = True
    body = _body(req_data)
    read_timeout = min(max(timeout, 5.0), 120.0)

    async with _semaphore():
        addresses = await asyncio.to_thread(resolve_target_addresses, snapshot.base_url, snapshot.binding)
        url, headers, extensions = _pinned_request(snapshot, addresses[0], "/chat/completions")
        headers["Accept"] = "text/event-stream"
        http_timeout = httpx.Timeout(connect=15.0, read=read_timeout, write=30.0, pool=15.0)
        try:
            async with httpx.AsyncClient(timeout=http_timeout, follow_redirects=False, trust_env=False) as client:
                async with client.stream("POST", url, headers=headers, content=body, extensions=extensions) as response:
                    if 300 <= response.status_code < 400:
                        _safe_json(b"{}", response.status_code)
                    if response.status_code >= 400:
                        err_chunks = bytearray()
                        async for raw_chunk in response.aiter_bytes():
                            err_chunks.extend(raw_chunk)
                            if len(err_chunks) > 65536:
                                break
                        _safe_json(bytes(err_chunks), response.status_code)

                    total_bytes = 0
                    yielded_any = False
                    async for raw_line in response.aiter_lines():
                        line = raw_line.strip()
                        if not line or line.startswith(":"):
                            continue
                        if not line.startswith("data:"):
                            continue
                        payload_str = line[5:].strip()
                        if not payload_str:
                            continue
                        if payload_str == "[DONE]":
                            break
                        try:
                            event = json.loads(payload_str)
                        except ValueError:
                            continue
                        if not isinstance(event, dict):
                            continue
                        if event.get("error"):
                            _safe_json(payload_str.encode("utf-8"), 502)
                        choices = event.get("choices")
                        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
                            continue
                        delta = choices[0].get("delta")
                        if not isinstance(delta, dict):
                            continue
                        content = delta.get("content")
                        if not isinstance(content, str) or not content:
                            continue
                        safe_piece = _redact(content, snapshot.credential)
                        total_bytes += len(safe_piece.encode("utf-8"))
                        if total_bytes > _MAX_RESPONSE_BYTES:
                            raise AIConfigError("RESPONSE_LIMIT", "Phản hồi provider vượt giới hạn.", 502)
                        yielded_any = True
                        yield safe_piece

                    if not yielded_any:
                        raise AIConfigError("PROTOCOL_ERROR", "Provider không trả nội dung chat hợp lệ.", 502)
        except (asyncio.TimeoutError, httpx.TimeoutException):
            raise AIConfigError("TIMEOUT", "API AI quá thời gian chờ.", 504) from None
        except httpx.RequestError:
            raise AIConfigError("NETWORK_ERROR", "Không kết nối được máy chủ AI.", 503) from None


def chat_sync(snapshot: ConfigSnapshot, messages: list[dict], *, max_tokens: int = 1024, timeout: float = 20, response_format: dict | None = None) -> str:
    return _request_json_sync(
        snapshot,
        "/chat/completions",
        _chat_body(snapshot, messages, max_tokens, response_format),
        timeout=timeout,
        post_process=lambda payload: _chat_text(payload, allow_empty_retry=True),
    )


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
