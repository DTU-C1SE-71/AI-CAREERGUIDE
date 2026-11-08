import re
import unicodedata
from typing import Any, Dict


def remove_vietnamese_accents(text: str) -> str:
    """Loại bỏ dấu tiếng Việt để phục vụ tìm kiếm không dấu."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    no_accent = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return no_accent.replace("đ", "d").replace("Đ", "D")


def clean_search_keyword(keyword: str) -> str:
    """Làm sạch từ khóa tìm kiếm (bỏ khoảng trắng thừa, ký tự đặc biệt)."""
    if not keyword:
        return ""
    cleaned = re.sub(r"[^\w\s\-\.]", " ", keyword)
    return " ".join(cleaned.split()).lower()


def sanitize_response_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Xóa bỏ các trường None hoặc nhạy cảm trong response payload."""
    return {k: v for k, v in data.items() if v is not None}
