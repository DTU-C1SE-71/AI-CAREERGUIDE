"""Giá trị bất biến, xác thực đích và ranh giới lỗi cho runtime AI."""
import hashlib
import ipaddress
import json
import re
import socket
from dataclasses import dataclass, field
from urllib.parse import urlsplit
from fastapi import HTTPException
from app.core.config import settings


class AIConfigError(HTTPException):
    def __init__(self, code: str, message: str, status_code: int = 422):
        self.code = code
        self.message = message
        super().__init__(status_code=status_code, detail={"code": code, "message": message})


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def validate_model(value: str) -> str:
    if not isinstance(value, str) or len(value) > 160 or ".." in value or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]*(?:/[A-Za-z0-9][A-Za-z0-9._:-]*)*", value):
        raise AIConfigError("INVALID_MODEL", "Tên model chứa ký tự không được phép.")
    return value



def validate_credential(value: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or not 8 <= len(value) <= 4096 or any(ord(c) < 33 or ord(c) > 126 for c in value) or any(mask in value for mask in ("*", "•", "...", "<", ">")) or value.lower().startswith(("your-", "your_", "placeholder", "redacted", "masked")) or value.lower() in {"undefined", "null", "none"}:
        raise AIConfigError("INVALID_CREDENTIAL", "Credential phải là giá trị tường minh, không rỗng, khoảng trắng hoặc chuỗi che.")
    return value


def canonical_target(value: str, protocol: str = "openai_compatible") -> tuple[str, dict]:
    if protocol != "openai_compatible":
        raise AIConfigError("UNSUPPORTED_PROTOCOL", "Giao thức AI chưa được hỗ trợ.")
    if not isinstance(value, str) or value != value.strip() or re.search(r"[\\\s\x00-\x1f\x7f]", value):
        raise AIConfigError("INVALID_BASE_URL", "Địa chỉ API không hợp lệ.")
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username is not None or parsed.password is not None or "?" in value or "#" in value:
            raise ValueError()
        host = parsed.hostname.encode("idna").decode("ascii").lower().rstrip(".")
        if not host or "%" in host:
            raise ValueError()
        port = parsed.port if parsed.port is not None else (443 if parsed.scheme == "https" else 80)
        if not 1 <= port <= 65535:
            raise ValueError()
        path = parsed.path or "/"
        if re.search(r"%(?![A-Fa-f0-9]{2})", path):
            raise ValueError()
        # Chỉ giải mã các ký tự unreserved; không cho mã hóa slash/dot để đổi tenant.
        if re.search(r"%(?:2f|5c)", path, re.I):
            raise ValueError()
        def unreserved_escape(match):
            char = chr(int(match.group(1), 16))
            if not re.fullmatch(r"[A-Za-z0-9._~-]", char):
                raise ValueError()
            return char
        path = re.sub(r"%([A-Fa-f0-9]{2})", unreserved_escape, path)
        if not re.fullmatch(r"/[A-Za-z0-9._~!$&'()+,;=:@/-]*", path) or "//" in path or any(p in {".", ".."} for p in path.split("/")):
            raise ValueError()
        path = path.rstrip("/") or "/"
        host_url = f"[{host}]" if ":" in host else host
        default_port = 443 if parsed.scheme == "https" else 80
        authority = host_url if port == default_port else f"{host_url}:{port}"
        base = f"{parsed.scheme}://{authority}" + ("" if path == "/" else path)
    except (ValueError, UnicodeError):
        raise AIConfigError("INVALID_BASE_URL", "Địa chỉ API phải có host/path hợp lệ, không chứa tài khoản, query, fragment hoặc đường dẫn nhảy cấp.") from None
    return base, {"protocol": protocol, "scheme": parsed.scheme, "host": host, "port": port, "base_path": path}


def target_is_allowlisted(base_url: str) -> bool:
    if settings.ENVIRONMENT not in {"test", "development"}:
        return False
    for value in settings.AI_LOCAL_ALLOWED_BASE_URLS:
        try:
            if canonical_target(value)[0] == base_url:
                return True
        except AIConfigError:
            continue
    return False


def resolve_target_addresses(base_url: str, binding: dict) -> tuple[str, ...]:
    canonical, actual = canonical_target(base_url, binding["protocol"])
    if actual != binding:
        raise AIConfigError("TARGET_BINDING_MISMATCH", "Đích API không còn khớp với credential.")
    allowed = target_is_allowlisted(canonical)
    if binding["scheme"] != "https" and not allowed:
        raise AIConfigError("SSRF_BLOCKED", "Chỉ cho phép API HTTPS công khai hoặc endpoint test được cho phép chính xác.")
    host = binding["host"]
    if not allowed and (host == "localhost" or host.endswith((".localhost", ".local", ".internal"))):
        raise AIConfigError("SSRF_BLOCKED", "Không gửi yêu cầu AI tới địa chỉ nội bộ.")
    try:
        records = socket.getaddrinfo(host, binding["port"], type=socket.SOCK_STREAM)
        addresses = tuple(dict.fromkeys(record[4][0] for record in records))
    except OSError:
        raise AIConfigError("DNS_ERROR", "Không phân giải được địa chỉ máy chủ AI.", 503) from None
    if not addresses or (not allowed and any(not ipaddress.ip_address(address).is_global for address in addresses)):
        raise AIConfigError("SSRF_BLOCKED", "DNS của endpoint AI trỏ tới vùng mạng không được phép.")
    return addresses


@dataclass(frozen=True)
class ConfigSnapshot:
    source_mode: str
    protocol: str
    canonical_base_url: str
    model: str
    auth_mode: str
    credential_binding: tuple[str, str, str, int, str]
    revision_token: str
    credential: str | None = field(repr=False)
    embedding_model: str = "text-embedding-3-small"

    @property
    def base_url(self) -> str:
        return self.canonical_base_url

    @property
    def binding(self) -> dict:
        return dict(zip(("protocol", "scheme", "host", "port", "base_path"), self.credential_binding))
