"""
AI Trend Hunter Agent (Tìm kiếm Ngành Xu Hướng trên Internet & Phân Bậc Ưu Tiên).

NGUYÊN TẮC BẮT BUỘC:
1. Chỉ thực thi tìm kiếm web khi Quản trị viên (ADMIN) bấm nút kích hoạt thủ công
   (`POST /api/v1/taxonomy/trend-agent/run`). Tuyệt đối không tự chạy ngầm hay tự chạy khi học sinh đánh giá.
2. Phân thành 3 bậc ưu tiên rõ ràng và đánh dấu trực tiếp vào dữ liệu ngành (CSDL + Active Catalog + Registry):
   - TIER_1 (priority=3, rank_boost=+0.08): Xu hướng Bậc 1 · Ưu tiên Cao nhất
   - TIER_2 (priority=2, rank_boost=+0.045): Xu hướng Bậc 2 · Tăng trưởng Mạnh
   - TIER_3 (priority=1, rank_boost=+0.02): Xu hướng Bậc 3 · Triển vọng Ổn định
3. Động cơ gợi ý sử dụng bậc ưu tiên này để đẩy các ngành xu hướng (đạt ngưỡng tương thích)
   lên đầu danh sách đề xuất mà vẫn giữ nguyên công thức 3 trụ cột (0.45 / 0.35 / 0.20) và
   tuyệt đối tuân thủ rào cản học thuật (TARGET trước REACH).
"""

import asyncio
import hashlib
import html
import json
import logging
import re
import time
import unicodedata
import urllib.parse
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.staging import StagingRecord, StagingStatus, StagingStreamType
from app.models.taxonomy import Major

logger = logging.getLogger(__name__)

SEEDS_DIR = Path(__file__).resolve().parent.parent.parent / "db" / "seeds"

TREND_TIER_CONFIG: Dict[str, Dict[str, Any]] = {
    "TIER_1": {
        "tier": "TIER_1",
        "priority": 3,
        "rank_boost": 0.08,
        "label": "Xu hướng Bậc 1 · Ưu tiên Cao nhất",
        "short_label": "Xu hướng Bậc 1",
    },
    "TIER_2": {
        "tier": "TIER_2",
        "priority": 2,
        "rank_boost": 0.045,
        "label": "Xu hướng Bậc 2 · Tăng trưởng Mạnh",
        "short_label": "Xu hướng Bậc 2",
    },
    "TIER_3": {
        "tier": "TIER_3",
        "priority": 1,
        "rank_boost": 0.02,
        "label": "Xu hướng Bậc 3 · Triển vọng Ổn định",
        "short_label": "Xu hướng Bậc 3",
    },
    "NONE": {
        "tier": "NONE",
        "priority": 0,
        "rank_boost": 0.0,
        "label": "Ngành tiêu chuẩn",
        "short_label": "",
    },
}


# Ánh xạ cụm chủ đề xu hướng trên báo chí / thị trường lao động -> Mã ngành TT74/TT09 & Từ khóa chuẩn
TREND_TOPIC_CLUSTERS: List[Dict[str, Any]] = [
    {
        "topic": "Trí tuệ nhân tạo & Học máy (AI / GenAI)",
        "keywords": ["tri tue nhan tao", "artificial intelligence", "ai", "genai", "machine learning", "deep learning"],
        "major_codes": ["7480107", "7480101"],
    },
    {
        "topic": "Vi mạch Bán dẫn & Thiết kế Chip",
        "keywords": ["vi mach", "ban dan", "semiconductor", "chip", "ic design"],
        "major_codes": ["7520202", "7520207", "7510301", "7510302"],
    },
    {
        "topic": "Khoa học dữ liệu & Big Data",
        "keywords": ["khoa hoc du lieu", "data science", "phan tich du lieu", "big data", "data analyst"],
        "major_codes": ["7460108", "7480104"],
    },
    {
        "topic": "An toàn thông tin & An ninh mạng",
        "keywords": ["an toan thong tin", "an ninh mang", "cybersecurity", "bao mat"],
        "major_codes": ["7480202", "7480102"],
    },
    {
        "topic": "Kỹ thuật phần mềm & Công nghệ thông tin",
        "keywords": ["ky thuat phan mem", "cong nghe thong tin", "lap trinh", "chuyen doi so", "phan mem", "cloud"],
        "major_codes": ["7480103", "7480201"],
    },
    {
        "topic": "Công nghệ tài chính (Fintech) & Ngân hàng số",
        "keywords": ["fintech", "cong nghe tai chinh", "tai chinh so", "ngan hang so", "tai chinh"],
        "major_codes": ["7340205", "7340201"],
    },
    {
        "topic": "Logistics & Quản lý chuỗi cung ứng",
        "keywords": ["logistics", "chuoi cung ung", "xuat nhap khau", "supply chain"],
        "major_codes": ["7510605", "7340120"],
    },
    {
        "topic": "Thương mại điện tử & Digital Marketing",
        "keywords": ["thuong mai dien tu", "e-commerce", "digital marketing", "marketing so", "marketing"],
        "major_codes": ["7340122", "7340115", "7320104"],
    },
    {
        "topic": "Tự động hóa, Robot & Xe điện",
        "keywords": ["tu dong hoa", "robot", "co dien tu", "xe dien", "o to", "cong nghe o to"],
        "major_codes": ["7510303", "7520114", "7520130", "7510205"],
    },
    {
        "topic": "Năng lượng tái tạo & Phát triển bền vững (ESG)",
        "keywords": ["nang luong tai tao", "nang luong xanh", "esg", "net zero", "dien gio", "moi truong"],
        "major_codes": ["7520212", "7510406", "7850101"],
    },
    {
        "topic": "Y khoa, Điều dưỡng & Công nghệ Sinh học",
        "keywords": ["y khoa", "bac si", "dieu duong", "y te", "duoc", "cong nghe sinh hoc", "cham soc suc khoe"],
        "major_codes": ["7720101", "7720301", "7720201", "7420201", "7720601"],
    },
    {
        "topic": "Tâm lý học, Sư phạm & Thiết kế Đa phương tiện",
        "keywords": ["tam ly hoc", "tham van", "su pham", "thiet ke do hoa", "ui/ux", "truyen thong da phuong tien"],
        "major_codes": ["7310401", "7210403", "7320106", "7140209"],
    },
]


def _strip_accents(text: str) -> str:
    if not text:
        return ""
    text = text.replace("đ", "d").replace("Đ", "D")
    norm = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in norm if unicodedata.category(ch) != "Mn").lower().strip()


def _clean_html_text(raw: str) -> str:
    if not raw:
        return ""
    unescaped = html.unescape(raw)
    cleaned = re.sub(r"<[^>]+>", " ", unescaped)
    return " ".join(cleaned.split()).strip()


def _get_registry_path() -> Path:
    if settings.ENVIRONMENT == "test":
        return SEEDS_DIR / "trending_majors_registry.test.json"
    return SEEDS_DIR / "trending_majors_registry.json"


def _code_variants(major_code: str) -> List[str]:
    c = str(major_code or "").strip()
    if not c:
        return []
    variants = [c]
    if len(c) == 7 and c.startswith("7"):
        variants.append(c[1:])
    elif len(c) == 6:
        variants.append(f"7{c}")
    return variants


def load_trending_registry() -> Dict[str, Any]:
    """Đọc sổ đăng ký ngành xu hướng đã được Admin chạy Agent (không kích hoạt tìm kiếm)."""
    path = _get_registry_path()
    if not path.exists():
        return {
            "last_run_at": None,
            "triggered_by": None,
            "focus_query": "",
            "articles_scanned": 0,
            "search_sources": [],
            "majors": {},
        }
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("majors"), dict):
                return data
    except Exception as exc:
        logger.warning("Không đọc được registry ngành xu hướng (%s): %s", path, exc)
    return {
        "last_run_at": None,
        "triggered_by": None,
        "focus_query": "",
        "articles_scanned": 0,
        "search_sources": [],
        "majors": {},
    }


def load_trending_registry_map() -> Dict[str, Dict[str, Any]]:
    """Trả về ánh xạ tra cứu nhanh cho cả mã ngành 6 chữ số (TT74) và 7 chữ số (TT09)."""
    reg = load_trending_registry()
    raw_majors = reg.get("majors") or {}
    lookup: Dict[str, Dict[str, Any]] = {}
    for code, entry in raw_majors.items():
        if not isinstance(entry, dict):
            continue
        tier = str(entry.get("trend_tier") or "NONE").upper()
        if tier not in ("TIER_1", "TIER_2", "TIER_3"):
            continue
        for v in _code_variants(code):
            lookup[v] = entry
    return lookup


def get_major_trend_info(
    major_code: str,
    trend_map: Optional[Dict[str, Dict[str, Any]]] = None,
    cognitive_attributes: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Lấy thông tin bậc ưu tiên xu hướng chuẩn hóa cho 1 mã ngành."""
    entry = None
    if trend_map:
        for v in _code_variants(major_code):
            if v in trend_map:
                entry = trend_map[v]
                break

    # Chỉ fallback sang _trend nhúng trong cognitive_attributes khi chưa có file registry ở môi trường thực tế
    if (
        not entry
        and settings.ENVIRONMENT != "test"
        and not _get_registry_path().exists()
        and isinstance(cognitive_attributes, dict)
    ):
        embedded = cognitive_attributes.get("_trend")
        if isinstance(embedded, dict) and embedded.get("trend_tier") in ("TIER_1", "TIER_2", "TIER_3"):
            entry = embedded

    if not entry:
        return {
            "is_trending": False,
            "trend_tier": None,
            "trend_priority": 0,
            "trend_label": None,
            "trend_reason": None,
            "trend_sources": [],
        }

    tier = str(entry.get("trend_tier") or "NONE").upper()
    cfg = TREND_TIER_CONFIG.get(tier, TREND_TIER_CONFIG["NONE"])
    if cfg["priority"] <= 0:
        return {
            "is_trending": False,
            "trend_tier": None,
            "trend_priority": 0,
            "trend_label": None,
            "trend_reason": None,
            "trend_sources": [],
        }

    return {
        "is_trending": True,
        "trend_tier": tier,
        "trend_priority": int(cfg["priority"]),
        "trend_label": entry.get("trend_label") or cfg["label"],
        "trend_reason": entry.get("trend_reason"),
        "trend_sources": entry.get("trend_sources") or [],
    }


def get_trend_rank_boost(
    trend_tier: Optional[str],
    overall_score: float,
) -> float:
    """
    Tính hệ số cộng ưu tiên xếp hạng (chỉ dùng cho thứ tự sắp xếp, không làm biến dạng % điểm 3 trụ cột).
    Guardrail: Chỉ cộng ưu tiên xu hướng khi ngành đạt ngưỡng phù hợp nền tảng tối thiểu (>= 0.45).
    """
    if not trend_tier or overall_score < 0.45:
        return 0.0
    cfg = TREND_TIER_CONFIG.get(str(trend_tier).upper())
    if not cfg:
        return 0.0
    return float(cfg["rank_boost"])


async def _fetch_rss_articles(client: httpx.AsyncClient, url: str, engine_name: str) -> List[Dict[str, Any]]:
    articles: List[Dict[str, Any]] = []
    try:
        resp = await client.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AI-CareerGuide-TrendAgent/1.0)"},
        )
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.text)
        for item in root.findall(".//item")[:15]:
            title = _clean_html_text(item.findtext("title") or "")
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            src_el = item.find("source")
            source_name = _clean_html_text(src_el.text if src_el is not None and src_el.text else engine_name)
            desc = _clean_html_text(item.findtext("description") or "")
            if title and link:
                articles.append({
                    "title": title,
                    "url": link,
                    "source": source_name or engine_name,
                    "published_at": pub_date,
                    "snippet": desc[:400],
                    "engine": engine_name,
                })
    except Exception as exc:
        logger.warning("Trend Agent RSS fetch failed (%s): %s", engine_name, exc)
    return articles


async def search_trending_majors_online(
    focus_query: str = "ngành nghề xu hướng khát nhân lực Việt Nam",
) -> List[Dict[str, Any]]:
    """
    Thực thi tìm kiếm trực tuyến về các ngành đang là xu hướng thị trường.
    Hỗ trợ kết hợp Tavily API (nếu có key hợp lệ), Google News RSS và Bing News RSS.
    """
    base_q = focus_query.strip() or "ngành nghề xu hướng khát nhân lực Việt Nam"
    queries = [
        base_q,
        f"{base_q} trí tuệ nhân tạo vi mạch bán dẫn logistics fintech",
        "ngành học hot dễ xin việc thiếu nhân lực Việt Nam 2026",
    ]

    all_articles: List[Dict[str, Any]] = []

    # 1. Tavily Search API (nếu đã cấu hình key thực tế)
    tavily_key = (settings.TAVILY_API_KEY or "").strip()
    if tavily_key and tavily_key != "your_tavily_api_key_here" and not tavily_key.startswith("your_"):
        try:
            from tavily import TavilyClient

            tavily = TavilyClient(api_key=tavily_key)
            resp = tavily.search(query=base_q, search_depth="advanced", max_results=10)
            for r in resp.get("results", []):
                all_articles.append({
                    "title": _clean_html_text(r.get("title") or ""),
                    "url": r.get("url") or "",
                    "source": "Tavily Web Search",
                    "published_at": "",
                    "snippet": _clean_html_text(r.get("content") or "")[:450],
                    "engine": "Tavily",
                })
        except Exception as exc:
            logger.warning("Tavily trend search fallback sang RSS (%s)", exc)

    # 2. Google News RSS & Bing News RSS song song
    tasks = []
    async with httpx.AsyncClient(timeout=8.5, follow_redirects=True) as client:
        for q in queries:
            encoded = urllib.parse.quote(q)
            gn_url = f"https://news.google.com/rss/search?q={encoded}&hl=vi&gl=VN&ceid=VN:vi"
            tasks.append(_fetch_rss_articles(client, gn_url, "Google News"))
        bn_url = f"https://www.bing.com/news/search?q={urllib.parse.quote(base_q)}&format=rss"
        tasks.append(_fetch_rss_articles(client, bn_url, "Bing News"))

        batches = await asyncio.gather(*tasks, return_exceptions=True)
        for b in batches:
            if isinstance(b, list):
                all_articles.extend(b)

    # Khử trùng lặp bài viết theo tiêu đề chuẩn hóa
    deduped: List[Dict[str, Any]] = []
    seen_titles = set()
    for art in all_articles:
        norm_t = _strip_accents(art.get("title", ""))[:80]
        if not norm_t or norm_t in seen_titles:
            continue
        seen_titles.add(norm_t)
        deduped.append(art)

    return deduped[:35]


def _extract_candidates_from_articles(
    articles: List[Dict[str, Any]],
    catalog_majors: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Đối chiếu dữ liệu tìm kiếm thực tế trên mạng vào 435 ngành chuẩn Bộ GD&ĐT (TT74/TT09),
    chấm điểm chứng cứ từ tiêu đề/tóm tắt bài báo và tổng hợp danh sách ứng viên ngành xu hướng.
    """
    norm_articles: List[Tuple[Dict[str, Any], str, str]] = []
    for art in articles:
        norm_title = _strip_accents(art.get("title", ""))
        norm_snip = _strip_accents(art.get("snippet", ""))
        norm_articles.append((art, norm_title, norm_snip))

    # Bước 1: Tính điểm tín hiệu của từng cụm chủ đề xu hướng trên các bài báo thực tế
    cluster_hits_by_code: Dict[str, List[Tuple[str, float, Dict[str, Any]]]] = {}
    for cluster in TREND_TOPIC_CLUSTERS:
        topic_name = cluster["topic"]
        kws = cluster["keywords"]
        for art, n_title, n_snip in norm_articles:
            score = 0.0
            for kw in kws:
                if len(kw) <= 3:
                    if re.search(rf"\b{re.escape(kw)}\b", n_title):
                        score += 2.2
                    elif re.search(rf"\b{re.escape(kw)}\b", n_snip):
                        score += 1.0
                else:
                    if kw in n_title:
                        score += 2.5
                    elif kw in n_snip:
                        score += 1.2
            if score > 0:
                for pos, code in enumerate(cluster["major_codes"]):
                    pos_weight = max(0.55, 1.0 - pos * 0.12)
                    for v in _code_variants(code):
                        cluster_hits_by_code.setdefault(v, []).append((topic_name, score * pos_weight, art))

    # Bước 2: Chấm điểm từng ngành trong danh mục chuẩn 435 ngành
    candidates: List[Dict[str, Any]] = []
    seen_major_codes = set()
    for m in catalog_majors:
        code = str(m.get("major_code") or "").strip()
        name = str(m.get("name") or "").strip()
        if not code or not name or code in seen_major_codes:
            continue
        seen_major_codes.add(code)

        norm_name = _strip_accents(name)
        evidence_score = 0.0
        matched_articles: List[Dict[str, Any]] = []
        matched_topics: List[str] = []
        seen_urls = set()

        # Khớp trực tiếp tên ngành trong bài báo
        if len(norm_name) >= 5:
            for art, n_title, n_snip in norm_articles:
                if norm_name in n_title:
                    evidence_score += 4.0
                    if art["url"] not in seen_urls:
                        seen_urls.add(art["url"])
                        matched_articles.append(art)
                elif norm_name in n_snip:
                    evidence_score += 2.0
                    if art["url"] not in seen_urls:
                        seen_urls.add(art["url"])
                        matched_articles.append(art)

        # Khớp qua cụm chủ đề xu hướng thị trường
        for topic_name, c_score, art in cluster_hits_by_code.get(code, []):
            evidence_score += c_score
            if topic_name not in matched_topics:
                matched_topics.append(topic_name)
            if art["url"] not in seen_urls:
                seen_urls.add(art["url"])
                matched_articles.append(art)

        if evidence_score >= 1.5 and matched_articles:
            candidates.append({
                "major_code": code,
                "major_name": name,
                "category": m.get("category") or "Khác",
                "evidence_score": round(evidence_score, 2),
                "matched_topics": matched_topics,
                "sources": [
                    {
                        "title": a["title"],
                        "url": a["url"],
                        "source": a.get("source", "Web Search"),
                    }
                    for a in matched_articles[:3]
                ],
            })

    candidates.sort(key=lambda c: c["evidence_score"], reverse=True)
    return candidates[:24]


async def _refine_tiers_with_llm(
    focus_query: str,
    articles: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
) -> Optional[Dict[str, Dict[str, Any]]]:
    """
    Tùy chọn dùng LLM để phân bậc TIER_1 / TIER_2 / TIER_3 và tổng hợp lý do xu hướng
    từ các bài báo thực tế tìm được trên mạng. Trả về None để fallback tất định nếu LLM offline/lỗi.
    """
    if (
        not candidates
        or not settings.OPENAI_API_KEY
        or settings.ENVIRONMENT == "test"
        or settings.OPENAI_API_KEY.startswith("sk-test")
        or settings.OPENAI_API_KEY == "your-openai-api-key"
    ):
        return None

    try:
        from openai import AsyncOpenAI

        client_kwargs: Dict[str, Any] = {"api_key": settings.OPENAI_API_KEY}
        if settings.OPENAI_BASE_URL:
            client_kwargs["base_url"] = settings.OPENAI_BASE_URL
        client = AsyncOpenAI(**client_kwargs)

        headlines = "\n".join(
            f"- [{a.get('source', 'Báo')}] {a['title']}" + (f" ({a['snippet'][:220]})" if a.get("snippet") else "")
            for a in articles[:35]
        )
        cand_lines = "\n".join(
            f"- {c['major_code']} | {c['major_name']} | Điểm chứng cứ web: {c['evidence_score']} | Chủ đề: {', '.join(c['matched_topics']) or 'Trực tiếp'}"
            for c in candidates[:30]
        )

        prompt = (
            f"Bạn là Trend Hunter Agent của hệ thống hướng nghiệp AI CareerGuide.\n"
            f"Truy vấn tìm kiếm của Admin: '{focus_query}'.\n\n"
            f"CÁC TIÊU ĐỀ BÀI BÁO THỰC TẾ VỪA TÌM ĐƯỢC TRÊN MẠNG:\n{headlines}\n\n"
            f"DANH SÁCH NGÀNH CHUẨN TT74/TT09 TƯƠNG ỨNG CHỨNG CỨ:\n{cand_lines}\n\n"
            f"NHIỆM VỤ:\n"
            f"Phân loại các ngành thực sự đang là xu hướng vào 3 bậc ưu tiên và trả về DUY NHẤT JSON array (không bọc markdown thừa nếu không cần):\n"
            f'[{{"major_code": "...", "trend_tier": "TIER_1"|"TIER_2"|"TIER_3", "trend_reason": "1 câu súc tích tiếng Việt nêu xu hướng thị trường"}}]\n'
            f"Quy tắc:\n"
            f"- TIER_1 (tối đa 6 ngành): Nhóm đột phá, xuất hiện dày đặc nhất (AI, Vi mạch/Bán dẫn, Dữ liệu, An toàn thông tin, Fintech...).\n"
            f"- TIER_2 (tối đa 7 ngành): Nhóm tăng trưởng mạnh (Phần mềm, Tự động hóa, Logistics, TMĐT, Y khoa/Y tế...).\n"
            f"- TIER_3 (tối đa 7 ngành): Nhóm nhu cầu ổn định/mở rộng (Năng lượng tái tạo, Tâm lý học, Thiết kế, Sư phạm...).\n"
            f"- Chỉ dùng đúng major_code có trong danh sách trên. Tuyệt đối không nhắc học phí hay địa lý."
        )

        async def _call() -> str:
            from app.core.llm_client import resolve_model_token_limits

            token_limits = await resolve_model_token_limits()
            try:
                resp = await client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": "Phân bậc ngành học xu hướng bằng JSON chuẩn xác dựa trên chứng cứ thị trường."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.15,
                    max_tokens=token_limits["max_output_tokens"],
                )
                return (resp.choices[0].message.content or "").strip()
            finally:
                try:
                    await client.close()
                except Exception:
                    pass

        raw = await asyncio.wait_for(_call(), timeout=30.0)
        m = re.search(r"\[.*\]", raw, flags=re.DOTALL)
        if not m:
            return None
        parsed_list = json.loads(m.group(0))
        if not isinstance(parsed_list, list):
            return None

        refined: Dict[str, Dict[str, Any]] = {}
        for item in parsed_list:
            if not isinstance(item, dict):
                continue
            c = str(item.get("major_code") or "").strip()
            t = str(item.get("trend_tier") or "").upper()
            r = str(item.get("trend_reason") or "").strip()
            if c and t in ("TIER_1", "TIER_2", "TIER_3") and r:
                refined[c] = {"trend_tier": t, "trend_reason": r}
        return refined or None
    except Exception as exc:
        logger.debug("Trend Agent chuyển sang phân bậc tất định theo chứng cứ web (%s)", exc)
        return None


def _build_classified_trend_map(
    candidates: List[Dict[str, Any]],
    llm_refined: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Kết hợp chứng cứ tìm kiếm web (+ kết quả LLM nếu có) thành từ điển ngành xu hướng phân 3 bậc."""
    now_iso = datetime.now(timezone.utc).isoformat()
    llm_map = llm_refined or {}

    max_score = max((c["evidence_score"] for c in candidates), default=1.0) or 1.0
    classified: Dict[str, Dict[str, Any]] = {}

    # Nhóm top 20 ngành giàu chứng cứ nhất vào Bậc 1 (top 6), Bậc 2 (tiếp 7), Bậc 3 (tiếp 7)
    for idx, cand in enumerate(candidates[:20]):
        code = cand["major_code"]
        llm_entry = None
        for v in _code_variants(code):
            if v in llm_map:
                llm_entry = llm_map[v]
                break

        if llm_entry:
            tier = llm_entry["trend_tier"]
            reason = llm_entry["trend_reason"]
        else:
            if idx < 6:
                tier = "TIER_1"
            elif idx < 13:
                tier = "TIER_2"
            else:
                tier = "TIER_3"
            topics_str = ", ".join(cand["matched_topics"][:2]) if cand["matched_topics"] else cand["major_name"]
            top_headline = cand["sources"][0]["title"] if cand["sources"] else ""
            reason = (
                f"Nhóm ngành {topics_str} ghi nhận nhu cầu nhân lực nổi bật trên thị trường"
                + (f" (nguồn: \"{top_headline[:90]}\")." if top_headline else ".")
            )

        cfg = TREND_TIER_CONFIG[tier]
        norm_score = min(99, max(65, int(round(65 + (cand["evidence_score"] / max_score) * 34))))

        classified[code] = {
            "major_code": code,
            "major_name": cand["major_name"],
            "category": cand["category"],
            "trend_tier": tier,
            "trend_priority": cfg["priority"],
            "trend_label": cfg["label"],
            "trend_score": norm_score,
            "trend_reason": reason,
            "trend_sources": cand["sources"],
            "updated_at": now_iso,
        }

    return classified


def _strip_old_trend_prefix(outlook: str) -> str:
    if not outlook:
        return ""
    return re.sub(r"^\[XU HƯỚNG BẬC [123][^\]]*\]\s*[^\n]*\n*", "", outlook).strip()


async def apply_trending_markers(
    db: Optional[AsyncSession],
    registry_payload: Dict[str, Any],
    sync_active_json: Optional[bool] = None,
) -> None:
    """
    Đánh dấu trực tiếp các ngành xu hướng (kèm bậc ưu tiên) vào:
    1. File persistent registry (`trending_majors_registry.json`)
    2. Danh mục active (`moet_taxonomy_active.json`) nếu không chạy test cô lập
    3. CSDL `majors` (cột JSONB `cognitive_attributes["_trend"]` và `industry_outlook`)
    """
    reg_path = _get_registry_path()
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(registry_payload, f, ensure_ascii=False, indent=2)

    majors_map: Dict[str, Dict[str, Any]] = registry_payload.get("majors") or {}
    expanded_lookup: Dict[str, Dict[str, Any]] = {}
    for code, entry in majors_map.items():
        for v in _code_variants(code):
            expanded_lookup[v] = entry

    should_sync_active = sync_active_json if sync_active_json is not None else (settings.ENVIRONMENT != "test")
    if should_sync_active:
        from app.services.taxonomy.service import load_seed_majors

        active_path = SEEDS_DIR / "moet_taxonomy_active.json"
        seed_majors = load_seed_majors()
        if seed_majors:
            for m in seed_majors:
                c = str(m.get("major_code") or "").strip()
                t_info = expanded_lookup.get(c)
                cog = dict(m.get("cognitive") or m.get("cognitive_attributes") or {})
                base_outlook = _strip_old_trend_prefix(m.get("outlook") or m.get("industry_outlook") or "")

                if t_info and t_info.get("trend_tier") in ("TIER_1", "TIER_2", "TIER_3"):
                    tier = t_info["trend_tier"]
                    cog["_trend"] = t_info
                    m["is_trending"] = True
                    m["trend_tier"] = tier
                    m["trend_priority"] = t_info["trend_priority"]
                    m["trend_label"] = t_info["trend_label"]
                    m["trend_reason"] = t_info["trend_reason"]
                    m["trend_sources"] = t_info.get("trend_sources", [])
                    tier_num = tier.replace("TIER_", "")
                    new_outlook = f"[XU HƯỚNG BẬC {tier_num}] {t_info['trend_reason']}" + (
                        f"\n{base_outlook}" if base_outlook else ""
                    )
                    m["outlook"] = new_outlook
                else:
                    cog.pop("_trend", None)
                    m.pop("is_trending", None)
                    m.pop("trend_tier", None)
                    m.pop("trend_priority", None)
                    m.pop("trend_label", None)
                    m.pop("trend_reason", None)
                    m.pop("trend_sources", None)
                    if base_outlook:
                        m["outlook"] = base_outlook

                if cog:
                    m["cognitive"] = cog

            # Bảo toàn header metadata nếu file active đang tồn tại
            wrapper_meta: Dict[str, Any] = {
                "circular_title": "Thông tư 74/2026/TT-BGDĐT",
                "circular_code": "74/2026/TT-BGDĐT",
                "total_majors": len(seed_majors),
                "majors": seed_majors,
            }
            if active_path.exists():
                try:
                    with open(active_path, "r", encoding="utf-8") as rf:
                        prev_data = json.load(rf)
                        if isinstance(prev_data, dict):
                            wrapper_meta["circular_title"] = prev_data.get("circular_title", wrapper_meta["circular_title"])
                            wrapper_meta["circular_code"] = prev_data.get("circular_code", wrapper_meta["circular_code"])
                except Exception:
                    pass
            with open(active_path, "w", encoding="utf-8") as wf:
                json.dump(wrapper_meta, wf, ensure_ascii=False, indent=2)

    # Cập nhật trực tiếp bảng majors trong PostgreSQL/SQLite (giữ nguyên 7 module DB)
    if db is not None:
        try:
            res = await db.execute(select(Major))
            db_majors = list(res.scalars().all())
            for db_m in db_majors:
                t_info = expanded_lookup.get(str(db_m.major_code).strip())
                cog = dict(db_m.cognitive_attributes or {})
                base_outlook = _strip_old_trend_prefix(db_m.industry_outlook or "")

                if t_info and t_info.get("trend_tier") in ("TIER_1", "TIER_2", "TIER_3"):
                    cog["_trend"] = t_info
                    tier_num = str(t_info["trend_tier"]).replace("TIER_", "")
                    db_m.cognitive_attributes = cog
                    db_m.industry_outlook = f"[XU HƯỚNG BẬC {tier_num}] {t_info['trend_reason']}" + (
                        f"\n{base_outlook}" if base_outlook else ""
                    )
                else:
                    if "_trend" in cog:
                        cog.pop("_trend", None)
                        db_m.cognitive_attributes = cog
                    if base_outlook != (db_m.industry_outlook or ""):
                        db_m.industry_outlook = base_outlook or "Đào tạo chuẩn Bộ GD&ĐT"

            await db.commit()
        except Exception as exc:
            logger.warning("Cập nhật dấu xu hướng vào DB majors gặp cảnh báo (%s)", exc)


async def run_trend_discovery_agent(
    db: Optional[AsyncSession],
    focus_query: str = "ngành nghề xu hướng khát nhân lực Việt Nam",
    triggered_by: str = "admin",
    override_articles: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Điểm chạy chính của AI Trend Hunter Agent (CHỈ gọi khi Admin bấm nút kích hoạt).
    1. Tìm kiếm tin tức/thị trường lao động trực tuyến.
    2. Đối chiếu với 435 ngành chuẩn Bộ GD&ĐT và phân 3 bậc ưu tiên (TIER_1 > TIER_2 > TIER_3).
    3. Đánh dấu trực tiếp vào dữ liệu ngành và ghi nhật ký HITL.
    """
    t0 = time.perf_counter()

    from app.services.taxonomy.service import load_seed_majors

    catalog_majors = load_seed_majors()
    if not catalog_majors and db is not None:
        res = await db.execute(select(Major).where(Major.is_active == True))
        catalog_majors = [
            {
                "major_code": m.major_code,
                "name": m.name,
                "category": m.category,
                "outlook": m.industry_outlook,
            }
            for m in res.scalars().all()
        ]

    articles = (
        override_articles
        if override_articles is not None
        else await search_trending_majors_online(focus_query=focus_query)
    )

    if not articles:
        return {
            "status": "no_web_results",
            "message": "Không thu thập được dữ liệu tìm kiếm trực tuyến mới (kiểm tra kết nối mạng). Dữ liệu ngành hiện tại được giữ nguyên.",
            "articles_scanned": 0,
            "total_trending_marked": len(load_trending_registry().get("majors") or {}),
            "tier_counts": {"TIER_1": 0, "TIER_2": 0, "TIER_3": 0},
            "trending_majors": [],
            "search_sources": [],
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }

    candidates = _extract_candidates_from_articles(articles, catalog_majors)
    llm_refined = await _refine_tiers_with_llm(focus_query, articles, candidates)
    classified_majors = _build_classified_trend_map(candidates, llm_refined=llm_refined)

    now_iso = datetime.now(timezone.utc).isoformat()
    source_summaries = [
        {
            "title": a["title"],
            "url": a["url"],
            "source": a.get("source", "Web Search"),
            "published_at": a.get("published_at", ""),
        }
        for a in articles[:12]
    ]

    registry_payload = {
        "last_run_at": now_iso,
        "triggered_by": triggered_by,
        "focus_query": focus_query,
        "articles_scanned": len(articles),
        "llm_refined": bool(llm_refined),
        "search_sources": source_summaries,
        "majors": classified_majors,
    }

    await apply_trending_markers(db, registry_payload)

    # Ghi nhật ký Audit vào bảng staging_records (APPROVED) nếu DB sẵn sàng
    if db is not None:
        try:
            digest = hashlib.sha256(f"trend-{focus_query}-{now_iso}".encode("utf-8")).hexdigest()
            tier_1_names = [v["major_name"] for v in classified_majors.values() if v["trend_tier"] == "TIER_1"]
            staging_entry = StagingRecord(
                id=uuid.uuid4(),
                stream_type=StagingStreamType.STREAM_B_ROADMAP,
                status=StagingStatus.APPROVED,
                major_code="TREND-AGENT",
                content_hash=digest,
                raw_content=f"Quét {len(articles)} bài báo cho truy vấn: {focus_query}",
                extracted_payload={
                    "type": "TREND_DISCOVERY",
                    "focus_query": focus_query,
                    "articles_scanned": len(articles),
                    "total_marked": len(classified_majors),
                    "tier_1_sample": tier_1_names[:6],
                },
                source_title=f"AI Trend Agent ({len(classified_majors)} ngành xu hướng)",
                source_url=source_summaries[0]["url"] if source_summaries else "https://news.google.com",
                source_page=f"{len(articles)} nguồn tin trực tuyến",
                reviewed_at=datetime.now(timezone.utc),
                review_notes=f"Kích hoạt thủ công bởi Admin ({triggered_by})",
            )
            db.add(staging_entry)
            await db.commit()
        except Exception as exc:
            logger.debug("Không ghi staging audit cho Trend Agent (%s)", exc)

    ordered_list = sorted(
        classified_majors.values(),
        key=lambda item: (item["trend_priority"], item["trend_score"]),
        reverse=True,
    )
    tier_counts = {
        "TIER_1": sum(1 for m in ordered_list if m["trend_tier"] == "TIER_1"),
        "TIER_2": sum(1 for m in ordered_list if m["trend_tier"] == "TIER_2"),
        "TIER_3": sum(1 for m in ordered_list if m["trend_tier"] == "TIER_3"),
    }

    return {
        "status": "success",
        "message": f"Agent đã quét {len(articles)} nguồn tin trên mạng và đánh dấu {len(ordered_list)} ngành xu hướng theo 3 bậc ưu tiên.",
        "last_run_at": now_iso,
        "triggered_by": triggered_by,
        "focus_query": focus_query,
        "articles_scanned": len(articles),
        "llm_refined": bool(llm_refined),
        "total_trending_marked": len(ordered_list),
        "tier_counts": tier_counts,
        "trending_majors": ordered_list,
        "search_sources": source_summaries,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


async def update_single_major_trend_tier(
    db: Optional[AsyncSession],
    major_code: str,
    trend_tier: str,
    trend_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Cho phép Admin tinh chỉnh bậc ưu tiên xu hướng của 1 ngành trực tiếp trong dữ liệu."""
    tier_norm = str(trend_tier or "NONE").upper().strip()
    if tier_norm not in TREND_TIER_CONFIG:
        tier_norm = "NONE"

    reg = load_trending_registry()
    majors_map = dict(reg.get("majors") or {})
    variants = _code_variants(major_code)

    # Tìm mã ngành chính xác trong catalog
    from app.services.taxonomy.service import load_seed_majors

    seed_majors = load_seed_majors()
    seed_lookup = {str(m.get("major_code") or "").strip(): m for m in seed_majors}
    matched_seed = next((seed_lookup[v] for v in variants if v in seed_lookup), None)
    canonical_code = matched_seed["major_code"] if matched_seed else str(major_code).strip()
    major_name = matched_seed["name"] if matched_seed else f"Ngành {canonical_code}"
    category = matched_seed.get("category", "Khác") if matched_seed else "Khác"

    # Xóa các biến thể cũ trước khi cập nhật
    existing_entry = None
    for v in variants:
        if v in majors_map:
            existing_entry = majors_map.pop(v)

    if tier_norm != "NONE":
        cfg = TREND_TIER_CONFIG[tier_norm]
        majors_map[canonical_code] = {
            "major_code": canonical_code,
            "major_name": (existing_entry or {}).get("major_name") or major_name,
            "category": (existing_entry or {}).get("category") or category,
            "trend_tier": tier_norm,
            "trend_priority": cfg["priority"],
            "trend_label": cfg["label"],
            "trend_score": (existing_entry or {}).get("trend_score") or (95 if tier_norm == "TIER_1" else 85 if tier_norm == "TIER_2" else 75),
            "trend_reason": trend_reason or (existing_entry or {}).get("trend_reason") or "Quản trị viên phân bậc ưu tiên xu hướng.",
            "trend_sources": (existing_entry or {}).get("trend_sources") or [],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    reg["majors"] = majors_map
    await apply_trending_markers(db, reg)
    return get_trending_status()


async def clear_trending_markers(db: Optional[AsyncSession]) -> Dict[str, Any]:
    """Xóa toàn bộ đánh dấu xu hướng trên dữ liệu ngành."""
    empty_reg = {
        "last_run_at": None,
        "triggered_by": None,
        "focus_query": "",
        "articles_scanned": 0,
        "search_sources": [],
        "majors": {},
    }
    await apply_trending_markers(db, empty_reg)
    return get_trending_status()


def get_trending_status() -> Dict[str, Any]:
    """Trả về trạng thái hiện tại của các ngành xu hướng (chỉ đọc, không chạy tìm kiếm)."""
    reg = load_trending_registry()
    majors_map = reg.get("majors") or {}
    ordered_list = sorted(
        [m for m in majors_map.values() if isinstance(m, dict) and m.get("trend_tier") in ("TIER_1", "TIER_2", "TIER_3")],
        key=lambda item: (int(item.get("trend_priority", 0)), int(item.get("trend_score", 0))),
        reverse=True,
    )
    return {
        "has_run": bool(reg.get("last_run_at")),
        "trigger_mode": "MANUAL_ADMIN_ONLY",
        "last_run_at": reg.get("last_run_at"),
        "triggered_by": reg.get("triggered_by"),
        "focus_query": reg.get("focus_query") or "",
        "articles_scanned": int(reg.get("articles_scanned") or 0),
        "total_trending_marked": len(ordered_list),
        "tier_counts": {
            "TIER_1": sum(1 for m in ordered_list if m.get("trend_tier") == "TIER_1"),
            "TIER_2": sum(1 for m in ordered_list if m.get("trend_tier") == "TIER_2"),
            "TIER_3": sum(1 for m in ordered_list if m.get("trend_tier") == "TIER_3"),
        },
        "trending_majors": ordered_list,
        "search_sources": reg.get("search_sources") or [],
    }
