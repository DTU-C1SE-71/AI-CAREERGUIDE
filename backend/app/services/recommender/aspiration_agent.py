"""
AI Career Aspiration & Psychometric Alignment Agent (FR04, FR06, NFR04).

Agent chuyên trách phân tích nguyện vọng nghề nghiệp tương lai của học sinh sau khi hoàn thành
bài trắc nghiệm 3 trụ cột (RIASEC 45% - Học lực Z-Score 35% - Nhận thức 20%):
1. Ánh xạ nguyện vọng nghề nghiệp tự nhiên (dream_job, work_values, preferred_environment, score_strategy)
   vào danh mục 435 ngành chuẩn Bộ GD&ĐT (Thông tư 74/2026/TT-BGDĐT).
2. Đối chiếu chéo (Cross-Reference) giữa "Ước muốn chủ quan" và "Kết quả trắc nghiệm + Ràng buộc điểm khách quan":
   - Trùng khớp thiên hướng & Đạt điểm chuẩn (ALIGNED_AND_ELIGIBLE)
   - Trùng khớp đam mê nhưng thiếu điểm chuẩn / vướng môn tiên quyết (PASSION_MATCH_SCORE_GAP) -> Tự động tìm ngành liên thông vừa sức (TARGET)
   - Nguyện vọng lệch với thiên hướng thực tế (TRAIT_DIVERGENCE) -> Đề xuất ngành cầu nối (Bridge Majors) kết hợp cả hai
   - Chế độ khám phá mở (EXPLORATORY_DISCOVERY)
3. Bảo mật Zero-PII (Luật 91/2025/QH15): Khử toàn bộ thông tin định danh cá nhân trước khi gọi LLM tổng hợp nhận xét.
4. Giữ nguyên 100% công thức toán học tất định cho điểm số và phân tầng khả thi (TARGET / REACH).
"""

import asyncio
import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.schemas.recommender import MajorRecommendationItem
from app.services.llamaindex_rag_orchestrator.guidance_rag import sanitize_pii
from app.services.recommender.engine import (
    RIASEC_NAMES_VI,
    are_majors_related_pathway,
)

logger = logging.getLogger(__name__)


def _strip_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt để so khớp từ khóa nghề nghiệp linh hoạt và chính xác."""
    if not text:
        return ""
    text = text.replace("đ", "d").replace("Đ", "D")
    norm = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in norm if unicodedata.category(ch) != "Mn").lower().strip()


# Từ điển cụm nghề nghiệp mơ ước phổ biến của học sinh THPT Việt Nam -> Mã ngành TT74 & Từ khóa ngành
CAREER_SYNONYM_CLUSTERS: List[Dict[str, Any]] = [
    {
        "cluster_id": "AI_DATA_CS",
        "label": "Kỹ sư AI, Khoa học dữ liệu & Lập trình phần mềm",
        "keywords": [
            "ai", "tri tue nhan tao", "machine learning", "data", "du lieu", "khoa hoc may tinh",
            "lap trinh", "phan mem", "software", "coder", "developer", "it", "cong nghe thong tin",
            "an ninh mang", "an toan thong tin", "cyber", "hacker", "fullstack", "web", "app", "game",
        ],
        "major_codes": ["7480107", "7480101", "7480103", "7480201", "7480104", "7480202", "7480108", "7460108"],
        "dominant_riasec": ["I", "R", "C"],
    },
    {
        "cluster_id": "SEMI_CHIP_AUTO",
        "label": "Kỹ sư Thiết kế Vi mạch, Bán dẫn, Tự động hóa & Cơ điện tử",
        "keywords": [
            "vi mach", "ban dan", "chip", "ic design", "tu dong hoa", "robot", "co dien tu",
            "dien tu", "vien thong", "iot", "nhung", "embedded", "co khi", "o to", "xe dien", "hang khong",
        ],
        "major_codes": ["7520202", "7520207", "7510303", "7520114", "7520130", "7510301", "7520103"],
        "dominant_riasec": ["R", "I"],
    },
    {
        "cluster_id": "MEDICAL_HEALTH",
        "label": "Bác sĩ Y khoa, Dược sĩ & Chăm sóc Sức khỏe",
        "keywords": [
            "bac si", "y khoa", "y da khoa", "rang ham mat", "nha si", "duoc si", "duoc hoc",
            "dieu duong", "y te", "chua benh", "benh vien", "xet nghiem", "phuc hoi chuc nang", "dinh duong",
        ],
        "major_codes": ["7720101", "7720501", "7720201", "7720301", "7720601", "7720602", "7720401"],
        "dominant_riasec": ["I", "S", "R"],
    },
    {
        "cluster_id": "FINANCE_FINTECH_ACC",
        "label": "Chuyên gia Tài chính, Ngân hàng, Fintech & Kế toán - Kiểm toán",
        "keywords": [
            "tai chinh", "ngan hang", "fintech", "cong nghe tai chinh", "chung khoan", "dau tu",
            "ke toan", "kiem toan", "thue", "bao hiem", "quan tri rui ro", "cfo", "phan tich tai chinh",
        ],
        "major_codes": ["7340205", "7340201", "7340301", "7340302", "7310101", "7310106"],
        "dominant_riasec": ["C", "E", "I"],
    },
    {
        "cluster_id": "BIZ_MKT_ECOM_LOG",
        "label": "Quản trị Kinh doanh, Marketing số, Thương mại điện tử & Logistics",
        "keywords": [
            "marketing", "kinh doanh", "quan tri", "thuong mai dien tu", "e-commerce", "logistics",
            "chuoi cung ung", "xuat nhap khau", "kinh doanh quoc te", "khoi nghiep", "ceo", "sale",
            "ban hang", "thuong hieu", "digital marketing", "quan he cong chung", "pr",
        ],
        "major_codes": ["7340115", "7340120", "7340122", "7510605", "7340101", "7340121", "7320108"],
        "dominant_riasec": ["E", "S", "C"],
    },
    {
        "cluster_id": "DESIGN_MEDIA_CREATIVE",
        "label": "Nhà Thiết kế Đồ họa, UI/UX, Truyền thông Đa phương tiện & Sáng tạo",
        "keywords": [
            "thiet ke", "do hoa", "ui/ux", "ui ux", "sang tao", "nghe thuat", "truyen thong",
            "da phuong tien", "bao chi", "content", "bien tap", "quay phim", "dao dien",
            "thoi trang", "noi that", "kien truc", "kien truc su", "my thuat", "animation",
        ],
        "major_codes": ["7210403", "7320104", "7320106", "7320101", "7580101", "7210404"],
        "dominant_riasec": ["A", "E", "S"],
    },
    {
        "cluster_id": "EDU_PSYCH_SOCIAL",
        "label": "Giáo viên Sư phạm, Chuyên gia Tâm lý học & Công tác Xã hội",
        "keywords": [
            "giao vien", "su pham", "giang vien", "day hoc", "giao duc", "tam ly", "tam ly hoc",
            "tham van", "cong tac xa hoi", "xa hoi hoc", "nhan su", "hr", "quan tri nhan luc",
        ],
        "major_codes": ["7140202", "7140209", "7140231", "7140103", "7310401", "7760101", "7340404"],
        "dominant_riasec": ["S", "A", "I"],
    },
    {
        "cluster_id": "LAW_DIPLOMACY_LANG",
        "label": "Luật sư, Pháp chế, Ngoại giao & Ngôn ngữ Quốc tế",
        "keywords": [
            "luat", "luat su", "phap luat", "phap che", "tham phan", "kiem sat", "ngoai giao",
            "quan he quoc te", "bien phien dich", "ngon ngu anh", "ngon ngu trung", "ngon ngu han",
            "ngon ngu nhat",
        ],
        "major_codes": ["7380101", "7380107", "7310206", "7220201", "7220204", "7810103", "7810201"],
        "dominant_riasec": ["E", "S", "A"],
    },
    {
        "cluster_id": "PERFORMING_ARTS_MUSIC",
        "label": "Thanh nhạc, Âm nhạc, Sân khấu - Điện ảnh & Nghệ thuật biểu diễn",
        "keywords": [
            "ca si", "am nhac", "thanh nhac", "nhac si", "nhac cong", "ban nhac", "nhac rap",
            "dien vien", "dien xuat", "san khau", "khieu vu", "ballet", "dien anh", "truyen hinh",
            "nghe si", "nguoi mau", "idol",
        ],
        "major_codes": ["7210205", "7210201", "7210207", "7210210", "7210222", "7210242", "7210302", "7210332"],
        "dominant_riasec": ["A", "E", "S"],
    },
    {
        "cluster_id": "CULINARY_HOSPITALITY_TOURISM",
        "label": "Đầu bếp, Quản trị Nhà hàng - Khách sạn, Du lịch & Dịch vụ",
        "keywords": [
            "dau bep", "nau an", "nau nuong", "am thuc", "bep", "nha hang", "khach san",
            "du lich", "huong dan vien", "le tan", "barista", "quan cafe", "resort", "tiep vien hang khong",
        ],
        "major_codes": ["7810202", "7810201", "7810101"],
        "dominant_riasec": ["S", "E", "R"],
    },
    {
        "cluster_id": "AVIATION_TRANSPORT",
        "label": "Hàng không, Phi công, Khai thác Vận tải & Quản lý Hoạt động bay",
        "keywords": [
            "phi cong", "hang khong", "may bay", "khong luu", "quan ly bay",
            "khai thac van tai", "phi hanh",
        ],
        "major_codes": ["7520120", "7840102", "7840101"],
        "dominant_riasec": ["R", "I", "C"],
    },
    {
        "cluster_id": "SPORTS_PHYSICAL_EDU",
        "label": "Thể dục thể thao, Huấn luyện viên & Y sinh Thể thao",
        "keywords": [
            "the thao", "van dong vien", "huan luyen vien", "bong da", "cau long", "bong ro",
            "boi loi", "vo thuat", "giao duc the chat", "the hinh", "gym",
        ],
        "major_codes": ["7810301", "7810302", "7720607", "7729001"],
        "dominant_riasec": ["R", "S", "E"],
    },
    {
        "cluster_id": "MEDIA_CREATOR",
        "label": "Sáng tạo Nội dung số, YouTuber/TikToker & Truyền thông Mạng xã hội",
        "keywords": [
            "youtuber", "streamer", "tiktoker", "tiktok", "kol", "koc", "blogger",
            "podcast", "livestream", "sang tao noi dung", "content creator", "mxh",
        ],
        "major_codes": ["7320104", "7320105", "7320106", "7320107"],
        "dominant_riasec": ["A", "E", "S"],
    },
    {
        "cluster_id": "SECURITY_DEFENSE",
        "label": "Công an, Quân đội, An ninh & Trinh sát",
        "keywords": [
            "cong an", "canh sat", "an ninh", "bo doi", "quan doi", "quan su", "trinh sat",
            "phong chong toi pham",
        ],
        "blocked_keywords": ["an ninh mang", "an toan thong tin", "cyber"],
        "major_codes": ["7860107", "7860112", "7860114", "7860101", "7860102", "7860218"],
        "dominant_riasec": ["R", "E", "C"],
    },
]

WORK_VALUE_RIASEC_BOOST: Dict[str, List[str]] = {
    "HIGH_INCOME_GROWTH": ["E", "C"],
    "TECH_INNOVATION": ["I", "R"],
    "CREATIVE_FREEDOM": ["A", "I"],
    "SOCIAL_IMPACT": ["S", "E"],
    "STABILITY_EXPERTISE": ["C", "I"],
}


def _match_aspiration_to_majors(
    dream_job: str,
    desired_field: str,
    work_values: List[str],
    score_strategy: str,
    all_ranked_majors: List[MajorRecommendationItem],
    seed_by_code: Dict[str, Dict[str, Any]],
) -> List[MajorRecommendationItem]:
    """
    Tìm các ngành trong 435 ngành TT74 khớp nhất với nguyện vọng nghề nghiệp học sinh nhập vào.
    Kết hợp so khớp từ điển cụm nghề nghiệp (CAREER_SYNONYM_CLUSTERS), tên ngành, danh sách nghề
    nghiệp đầu ra (careers), giá trị công việc (work_values) và chiến lược điểm (score_strategy).
    """
    norm_dream = _strip_accents(dream_job)
    norm_field = _strip_accents(desired_field)
    combined_query = f"{norm_dream} {norm_field}".strip()

    if not combined_query:
        return []

    # 1. Kiểm tra khớp với các cụm từ đồng nghĩa nghề nghiệp
    matched_cluster_codes: List[str] = []
    for cluster in CAREER_SYNONYM_CLUSTERS:
        # Từ khóa chặn (blocked_keywords): nếu câu nguyện vọng chứa cụm này thì KHÔNG tính cụm nghề hiện tại.
        # Ví dụ: "an ninh mạng" phải về nhóm CNTT, không được rơi vào nhóm Công an - Quân đội.
        if any(bk in combined_query for bk in (cluster.get("blocked_keywords") or [])):
            continue
        for kw in cluster["keywords"]:
            # Dùng ranh giới từ cho từ khóa ngắn (như 'ai', 'it', 'pr') để tránh khớp nhầm
            if len(kw) <= 3:
                if re.search(rf"\b{re.escape(kw)}\b", combined_query):
                    matched_cluster_codes.extend(cluster["major_codes"])
                    break
            elif kw in combined_query:
                matched_cluster_codes.extend(cluster["major_codes"])
                break

    # Ánh xạ thứ tự ưu tiên cho cả mã 6 chữ số (TT74) và 7 chữ số (TT09)
    cluster_priority_map: Dict[str, float] = {}
    expanded_codes = set()
    for pos, code in enumerate(matched_cluster_codes):
        priority_val = max(0.2, 1.0 - (pos * 0.1))
        variants = [code]
        if len(code) == 7 and code.startswith("7"):
            variants.append(code[1:])
        elif len(code) == 6:
            variants.append("7" + code)
        for v in variants:
            expanded_codes.add(v)
            if v not in cluster_priority_map:
                cluster_priority_map[v] = priority_val

    desired_value_dims = {
        dim
        for val in (work_values or [])
        for dim in WORK_VALUE_RIASEC_BOOST.get(val, [])
    }

    tokens = [t for t in re.split(r"[^a-z0-9]+", combined_query) if len(t) >= 3]

    scored_candidates: List[tuple[float, MajorRecommendationItem]] = []
    for item in all_ranked_majors:
        relevance = 0.0
        code_str = str(item.major_code).strip()
        alt_code = code_str[1:] if (len(code_str) == 7 and code_str.startswith("7")) else f"7{code_str}"
        norm_name = _strip_accents(item.major_name)
        norm_cat = _strip_accents(item.category or "")

        seed_info = seed_by_code.get(code_str) or seed_by_code.get(alt_code) or {}
        careers_list = seed_info.get("careers") or []
        norm_careers = _strip_accents(" ".join(str(c) for c in careers_list))

        if code_str in expanded_codes:
            relevance += 2.5 + cluster_priority_map.get(code_str, 0.5)

        if norm_dream and len(norm_dream) >= 3:
            if norm_dream in norm_name:
                relevance += 3.2
            elif norm_dream in norm_careers:
                relevance += 2.4
            elif norm_dream in norm_cat:
                relevance += 1.2

        if norm_field and len(norm_field) >= 3 and norm_field in norm_cat:
            relevance += 1.5

        for tok in tokens:
            if tok in norm_name:
                relevance += 0.75
            elif tok in norm_careers:
                relevance += 0.55
            elif tok in norm_cat:
                relevance += 0.25

        if relevance >= 1.1:
            value_bonus = 0.0
            if desired_value_dims:
                seed_riasec = seed_info.get("riasec") or seed_info.get("riasec_vector") or {}
                if isinstance(seed_riasec, dict):
                    top_major_dims = [
                        k for k, _ in sorted(seed_riasec.items(), key=lambda kv: kv[1], reverse=True)[:2]
                    ]
                    if any(d in desired_value_dims for d in top_major_dims):
                        value_bonus = 0.25

            # UNKNOWN = chưa có điểm học lực -> không thưởng/phạt theo tầng khả thi (tránh xếp hạng ảo)
            if item.feasibility_tier in (None, "UNKNOWN"):
                tier_bonus = 0.0
            elif score_strategy == "REALISTIC_SAFE":
                tier_bonus = 0.85 if item.feasibility_tier == "TARGET" else -0.45
            elif score_strategy == "CHALLENGE_TOP":
                tier_bonus = 0.35 if item.feasibility_tier == "REACH" else 0.15
            else:
                tier_bonus = 0.30 if item.feasibility_tier == "TARGET" else 0.0

            composite_rank = relevance + (item.overall_score * 1.2) + tier_bonus + value_bonus
            scored_candidates.append((composite_rank, relevance, item))

    # Anchor-first: ngành có độ liên quan NỘI DUNG cao nhất phải đứng đầu danh sách "Ước mơ".
    # (Trước đây xếp theo composite nên "Bác sĩ" có thể bị "Điều dưỡng" chiếm vị trí ước mơ.)
    scored_candidates.sort(key=lambda tri: (tri[0], tri[1]), reverse=True)
    anchor = max(scored_candidates, key=lambda tri: tri[1]) if scored_candidates else None

    unique_results: List[MajorRecommendationItem] = []
    seen_codes = set()
    ordered = ([anchor] if anchor else []) + scored_candidates
    for _, _, item in ordered:
        if item.major_code not in seen_codes:
            seen_codes.add(item.major_code)
            unique_results.append(item)
        if len(unique_results) >= 4:
            break

    return unique_results


def _serialize_major_brief(item: MajorRecommendationItem, role_tag: str = "DREAM") -> Dict[str, Any]:
    """Đóng gói thông tin tóm tắt của ngành phục vụ hiển thị trực quan trên Card AI Agent."""
    return {
        "major_code": item.major_code,
        "major_name": item.major_name,
        "category": item.category or "Khác",
        "overall_match": int(round(item.overall_score * 100)),
        "riasec_fit": int(round(item.score_riasec * 100)),
        "academic_fit": int(round(item.score_academic * 100)),
        "cognitive_fit": int(round(item.score_preference * 100)),
        "feasibility_tier": item.feasibility_tier or "TARGET",
        "feasibility_label": item.feasibility_label or "Khả thi cao",
        "best_matching_block": item.best_matching_block,
        "best_block_score": item.best_block_score,
        "benchmark_cutoff": item.benchmark_cutoff,
        "score_gap": item.score_gap,
        "constraint_passed": item.constraint_passed,
        "constraint_violations": item.constraint_violations[:2] if item.constraint_violations else [],
        "admission_advice": item.admission_advice,
        "is_trending": bool(getattr(item, "is_trending", False)),
        "trend_tier": getattr(item, "trend_tier", None),
        "trend_priority": int(getattr(item, "trend_priority", 0) or 0),
        "trend_label": getattr(item, "trend_label", None),
        "role_tag": role_tag,
    }


_UNSAFE_ASSERTION_PATTERN = re.compile(
    r"(chắc chắn đỗ|chac chan do|cam kết trúng tuyển|cam ket trung tuyen|bao đậu|bao dau|"
    r"đỗ 100%|do 100%|100% đỗ|100% do|trúng tuyển tuyệt đối|trung tuyen tuyet doi)",
    re.IGNORECASE,
)

_NUMBER_PATTERN = re.compile(r"\d+(?:[.,]\d+)?")


def _is_safe_llm_verdict(text: str, allowed_numbers: set) -> bool:
    """
    Chốt chặn chống ảo giác của LLM:
    1) Không được chứa lời hứa tuyệt đối về việc trúng tuyển.
    2) Không được bịa con số mới (mọi số xuất hiện phải nằm trong dữ liệu tất định đã truyền vào).
    """
    if not text or len(text) < 25:
        return False
    if _UNSAFE_ASSERTION_PATTERN.search(text):
        return False
    for raw in _NUMBER_PATTERN.findall(text):
        normalized = raw.replace(",", ".")
        try:
            value = float(normalized)
        except ValueError:
            continue
        candidates = {normalized, f"{value:g}", str(int(value)) if value == int(value) else normalized}
        if not (candidates & allowed_numbers):
            return False
    return True


async def _try_llm_aspiration_synthesis(
    sanitized_dream: str,
    alignment_status: str,
    top_holland: str,
    best_block_str: str,
    primary_dream: Optional[MajorRecommendationItem],
    substitute_major: Optional[MajorRecommendationItem],
    bridge_major: Optional[MajorRecommendationItem],
    allowed_numbers: Optional[set] = None,
) -> Optional[str]:
    """
    Gọi LLM (với timeout ngắn 3.5 giây & Zero-PII) để viết lời khuyên cá nhân hóa ngắn gọn.
    Nếu không cấu hình key hoặc môi trường test/offline, trả về None để dùng ngay nhận xét tất định.
    """
    if (
        not settings.OPENAI_API_KEY
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

        dream_info = (
            f"{primary_dream.major_name} (Mã {primary_dream.major_code}, tương thích {int(round(primary_dream.overall_score * 100))}%, "
            f"Sở thích {int(round(primary_dream.score_riasec * 100))}%, trạng thái {primary_dream.feasibility_tier}, "
            f"chuẩn ~{primary_dream.benchmark_cutoff}đ)"
            if primary_dream
            else "Chưa xác định ngành cố định"
        )
        sub_info = (
            f"Ngành thay thế vừa sức: {substitute_major.major_name} (Mã {substitute_major.major_code}, chuẩn ~{substitute_major.benchmark_cutoff}đ)."
            if substitute_major
            else ""
        )
        bridge_info = (
            f"Ngành cầu nối kết hợp đam mê & thiên hướng: {bridge_major.major_name} (Mã {bridge_major.major_code}, tương thích {int(round(bridge_major.overall_score * 100))}%)."
            if bridge_major
            else ""
        )

        prompt = sanitize_pii(
            f"Học sinh có nguyện vọng nghề nghiệp: '{sanitized_dream}'.\n"
            f"Kết quả trắc nghiệm khách quan: Mã Holland nổi trội {top_holland}, điểm tổ hợp mạnh nhất {best_block_str}.\n"
            f"Kết quả đối chiếu ngành mơ ước: {dream_info} (Trạng thái: {alignment_status}). {sub_info} {bridge_info}\n"
            f"Hãy viết đúng 2-3 câu ngắn gọn, súc tích (tối đa 75 từ) nhận xét sự tương thích giữa ước muốn của học sinh "
            f"và kết quả bài test, đồng thời khuyên học sinh nên chọn ngành nào. Tuyệt đối không nhắc học phí hay địa lý, "
            f"CHỈ được dùng đúng các con số đã xuất hiện trong dữ liệu trên (không tự tạo số mới, không tự tính lại), "
            f"và KHÔNG được cam kết/kết luận chắc chắn học sinh sẽ trúng tuyển."
        )

        async def _call() -> str:
            from app.core.llm_client import resolve_model_token_limits

            token_limits = await resolve_model_token_limits()
            try:
                resp = await client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": "Bạn là AI Agent Phân tích Nguyện vọng & Đối chiếu Trắc nghiệm của hệ thống AI CareerGuide.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.25,
                    max_tokens=token_limits["max_output_tokens"],
                )
                return (resp.choices[0].message.content or "").strip()
            finally:
                try:
                    await client.close()
                except Exception:
                    pass

        text = await asyncio.wait_for(_call(), timeout=8.0)
        if not _is_safe_llm_verdict(text, allowed_numbers or set()):
            logger.debug("Aspiration Agent loại nhận xét LLM có số liệu lạ hoặc cam kết tuyệt đối.")
            return None
        return text
    except Exception as exc:
        logger.debug("Aspiration Agent dùng chế độ giải thích tất định (LLM skip: %s)", exc)
        return None


async def analyze_career_aspiration(
    aspiration_data: Optional[Dict[str, Any]],
    student_riasec: Dict[str, float],
    best_block_stats: Optional[Dict[str, Any]],
    all_ranked_majors: List[MajorRecommendationItem],
    seed_by_code: Optional[Dict[str, Dict[str, Any]]] = None,
    enable_llm: bool = True,
) -> Dict[str, Any]:
    """
    Thực thi AI Agent Phân tích Nguyện vọng & Đối chiếu Kết quả Trắc nghiệm:
    - Trả về cấu trúc chuẩn hóa gồm:
      * alignment_status: ALIGNED_AND_ELIGIBLE | PASSION_MATCH_SCORE_GAP | TRAIT_DIVERGENCE | EXPLORATORY_DISCOVERY
      * alignment_label, alignment_score (0..100)
      * dream_majors: Các ngành tương ứng trực tiếp với ước mơ của học sinh kèm điểm 3 trụ cột & trạng thái ràng buộc điểm
      * recommended_substitutes: Các ngành liên thông vừa sức (TARGET) nếu ngành mơ ước bị chặn điểm chuẩn (REACH)
      * bridge_majors: Các ngành cầu nối giao thoa giữa ước muốn và thiên hướng RIASEC thực tế
      * agent_verdict: Nhận xét súc tích của AI Agent
      * key_takeaways: 3 gạch đầu dòng đối chiếu rõ ràng
    """
    raw_asp = aspiration_data or {}
    raw_dream_job = str(raw_asp.get("dream_job") or raw_asp.get("dreamJob") or "").strip()
    desired_field = str(raw_asp.get("desired_field") or raw_asp.get("desiredField") or "").strip()
    work_values: List[str] = list(raw_asp.get("work_values") or raw_asp.get("workValues") or [])
    preferred_env = str(raw_asp.get("preferred_environment") or raw_asp.get("preferredEnvironment") or "").strip()
    score_strategy = str(raw_asp.get("score_strategy") or raw_asp.get("scoreStrategy") or "FLEXIBLE_PATHWAY").strip()

    sanitized_dream = sanitize_pii(raw_dream_job)
    sanitized_field = sanitize_pii(desired_field)

    # Xác định Top 3 chiều Holland của học sinh từ bài test
    sorted_riasec = sorted(
        (student_riasec or {"I": 0.5, "R": 0.5, "A": 0.5, "S": 0.5, "E": 0.5, "C": 0.5}).items(),
        key=lambda kv: kv[1],
        reverse=True,
    )
    top3_dims = [k for k, _ in sorted_riasec[:3]]
    top_holland_str = " · ".join(top3_dims)
    primary_dim = top3_dims[0] if top3_dims else "I"
    primary_dim_label = RIASEC_NAMES_VI.get(primary_dim, primary_dim)

    block_name = (best_block_stats or {}).get("block", "Khối xét tuyển")
    block_sum = (best_block_stats or {}).get("raw_sum")
    best_block_str = f"{block_name} ({block_sum}đ)" if block_sum is not None else block_name

    # Cờ chống bịa điểm: chỉ coi là có dữ liệu học lực khi thực sự có khối được xếp TARGET/REACH
    # (khi chưa nhập điểm, mọi ngành đều UNKNOWN nên cờ này = False).
    has_academic_data = (best_block_stats or {}).get("has_academic_data")
    if has_academic_data is None:
        has_academic_data = any(
            m.feasibility_tier in ("TARGET", "REACH") for m in all_ranked_majors
        )

    if seed_by_code is None:
        from app.services.taxonomy.service import load_seed_majors
        seed_list = load_seed_majors()
        seed_by_code = {str(m.get("major_code", "")): m for m in seed_list if m.get("major_code")}

    eligible_targets = [m for m in all_ranked_majors if m.feasibility_tier == "TARGET"]
    top_test_major = eligible_targets[0] if eligible_targets else (all_ranked_majors[0] if all_ranked_majors else None)

    # Tìm các ngành khớp với nguyện vọng nghề nghiệp
    dream_majors = _match_aspiration_to_majors(
        dream_job=sanitized_dream,
        desired_field=sanitized_field,
        work_values=work_values,
        score_strategy=score_strategy,
        all_ranked_majors=all_ranked_majors,
        seed_by_code=seed_by_code,
    )

    # Trường hợp học sinh chưa nhập nghề cụ thể (hoặc chọn khám phá mở)
    if not dream_majors:
        top_picks = eligible_targets[:3] if eligible_targets else all_ranked_majors[:3]
        takeaways = [
            f"Thiên hướng nổi trội từ bài test: **{top_holland_str}** (dẫn đầu là nhóm **{primary_dim_label}** - {int(round(sorted_riasec[0][1] * 100))}%).",
        ]
        if has_academic_data:
            takeaways.append(
                f"Tổ hợp học lực mạnh nhất hiện tại: **{best_block_str}** — ưu tiên các ngành có ngưỡng điểm chuẩn vừa sức (`TARGET`)."
            )
        else:
            takeaways.append(
                "Chưa có điểm học lực nên Agent **chỉ xếp hạng theo thiên hướng/sở thích**, chưa kết luận ngành nào đạt điểm chuẩn. Hãy nhập điểm môn học để nhận phân tầng `TARGET`/`REACH`."
            )
        if top_test_major:
            takeaways.append(
                f"Đề xuất dẫn đầu từ 435 ngành TT74: **{top_test_major.major_name}** (Mã `{top_test_major.major_code}`, độ khớp **{int(round(top_test_major.overall_score * 100))}%**)."
            )
        if has_academic_data:
            verdict = (
                f"Dựa trên hồ sơ trắc nghiệm khách quan (**{top_holland_str}**) và tổ hợp **{best_block_str}**, "
                f"AI Agent đề xuất bạn tập trung vào nhóm ngành **{top_test_major.category if top_test_major else 'Mũi nhọn'}** "
                f"với ngành tiêu biểu là **{top_test_major.major_name if top_test_major else 'Công nghệ thông tin'}**. "
                f"Bạn có thể nhập thêm nghề nghiệp mơ ước cụ thể để Agent đối chiếu chuyên sâu."
            )
        else:
            verdict = (
                f"Dựa trên hồ sơ trắc nghiệm khách quan (**{top_holland_str}**), AI Agent đề xuất bạn khám phá nhóm ngành "
                f"**{top_test_major.category if top_test_major else 'Mũi nhọn'}** với ngành tiêu biểu là "
                f"**{top_test_major.major_name if top_test_major else 'Công nghệ thông tin'}**. "
                f"Lưu ý: bạn chưa nhập điểm học lực, nên đây là gợi ý theo thiên hướng chứ chưa phải kết luận về khả năng trúng tuyển. "
                f"Hãy nhập điểm và nghề nghiệp mơ ước để Agent đối chiếu chính xác hơn."
            )
        return {
            "has_aspiration": bool(sanitized_dream or sanitized_field or work_values),
            "dream_job": sanitized_dream or "Khám phá theo năng lực trắc nghiệm",
            "desired_field": sanitized_field,
            "work_values": work_values,
            "preferred_environment": preferred_env,
            "score_strategy": score_strategy,
            "alignment_status": "EXPLORATORY_DISCOVERY",
            "alignment_label": "Định hướng Mở theo Hồ sơ Trắc nghiệm",
            "alignment_score": int(round(top_test_major.overall_score * 100)) if top_test_major else 80,
            "holland_code": top_holland_str,
            "best_block_summary": best_block_str,
            "dream_majors": [_serialize_major_brief(m, "TOP_TEST") for m in top_picks[:2]],
            "recommended_substitutes": [],
            "bridge_majors": [_serialize_major_brief(m, "BRIDGE") for m in top_picks[2:4]],
            "agent_verdict": verdict,
            "key_takeaways": takeaways,
            "is_llm_enriched": False,
            "has_academic_data": has_academic_data,
            "score_basis": "ACADEMIC_AND_RIASEC" if has_academic_data else "RIASEC_ONLY",
        }

    primary_dream = dream_majors[0]
    primary_is_target = (primary_dream.feasibility_tier == "TARGET")
    eligible_dreams = [m for m in dream_majors if m.feasibility_tier == "TARGET"]
    blocked_dreams = [m for m in dream_majors if m.feasibility_tier == "REACH"]

    # Chưa nhập điểm học lực: chỉ đối chiếu thiên hướng, KHÔNG kết luận đủ/thiếu điểm chuẩn.
    if not has_academic_data:
        alignment_score = int(round(primary_dream.score_riasec * 100))
        related = dream_majors[:2]
        takeaways = [
            f"Nguyện vọng **\"{sanitized_dream}\"** tương ứng với **{primary_dream.major_name}** (Mã `{primary_dream.major_code}`) — độ khớp sở thích **{int(round(primary_dream.score_riasec * 100))}%** với mã Holland **{top_holland_str}**.",
            "Bạn **chưa nhập điểm học lực**, nên Agent không thể xác nhận ngành này đạt hay thiếu điểm chuẩn (chưa có `TARGET`/`REACH`).",
            f"Ngành này có điểm chuẩn tham chiếu khoảng **{primary_dream.benchmark_cutoff}đ** — hãy nhập điểm các môn để nhận kết luận khả thi chính xác.",
        ]
        verdict = (
            f"Ước muốn trở thành **{sanitized_dream}** của bạn khớp **{int(round(primary_dream.score_riasec * 100))}%** "
            f"với thiên hướng sở thích đo được (**{top_holland_str}**), và ngành gần nhất là "
            f"**{primary_dream.major_name}** (Mã `{primary_dream.major_code}`). "
            f"Tuy nhiên bạn chưa nhập điểm học lực, nên Agent dừng ở mức đối chiếu thiên hướng và không đưa ra kết luận trúng tuyển."
        )
        return {
            "has_aspiration": True,
            "dream_job": sanitized_dream,
            "desired_field": sanitized_field,
            "work_values": work_values,
            "preferred_environment": preferred_env,
            "score_strategy": score_strategy,
            "alignment_status": "NEED_ACADEMIC_DATA",
            "alignment_label": "Khớp Thiên hướng · Chưa đủ điểm để xác nhận khả thi",
            "alignment_score": alignment_score,
            "holland_code": top_holland_str,
            "best_block_summary": best_block_str,
            "dream_majors": [_serialize_major_brief(m, "DREAM") for m in related],
            "recommended_substitutes": [],
            "bridge_majors": [],
            "agent_verdict": verdict,
            "key_takeaways": takeaways,
            "is_llm_enriched": False,
            "has_academic_data": False,
            "score_basis": "RIASEC_ONLY",
        }

    def _get_major_top2_dims(item: MajorRecommendationItem) -> List[str]:
        code_str = str(item.major_code).strip()
        alt_code = code_str[1:] if (len(code_str) == 7 and code_str.startswith("7")) else f"7{code_str}"
        seed_info = seed_by_code.get(code_str) or seed_by_code.get(alt_code) or {}
        vec = seed_info.get("riasec") or seed_info.get("riasec_vector") or {}
        if not vec:
            return []
        return [k for k, _ in sorted(vec.items(), key=lambda kv: float(kv[1]), reverse=True)[:2]]

    # Tìm ngành thay thế vừa sức (Sibling/Pathway TARGET) nếu ngành mơ ước chính bị chặn điểm chuẩn (REACH)
    substitutes: List[MajorRecommendationItem] = []
    if blocked_dreams:
        target_blocked = primary_dream if not primary_is_target else blocked_dreams[0]
        excluded_for_sub = {m.major_code for m in blocked_dreams} | (
            {primary_dream.major_code} if not primary_is_target else set()
        )
        # Nếu ngành mơ ước chính bị chặn (REACH), cho phép đưa các ngành TARGET cùng cluster làm ứng viên thay thế
        dream_target_peers = [
            m for m in dream_majors[1:] if m.feasibility_tier == "TARGET" and m.major_code not in excluded_for_sub
        ]
        scored_subs: List[tuple[float, MajorRecommendationItem]] = []
        seen_sub_codes = set()
        for cand in eligible_targets:
            if cand.major_code in excluded_for_sub or cand.major_code in seen_sub_codes:
                continue
            if primary_is_target and cand.major_code in {m.major_code for m in dream_majors}:
                continue
            rel_tier = are_majors_related_pathway(target_blocked.major_code, cand.major_code)
            same_cat = 1 if (cand.category and cand.category == target_blocked.category) else 0
            in_dream_cluster = 1 if cand in dream_target_peers else 0
            if rel_tier > 0 or same_cat > 0 or in_dream_cluster > 0:
                metric = (
                    (rel_tier * 0.25)
                    + (in_dream_cluster * 0.30)
                    + (same_cat * 0.10)
                    + (cand.score_riasec * 0.25)
                    + (cand.overall_score * 0.20)
                )
                scored_subs.append((metric, cand))
                seen_sub_codes.add(cand.major_code)
        scored_subs.sort(key=lambda x: x[0], reverse=True)
        substitutes = [m for _, m in scored_subs[:2]]

    # Tìm ngành cầu nối (Bridge Majors): các ngành TARGET giao thoa giữa thiên hướng thực tế & miền mơ ước
    used_codes = {m.major_code for m in dream_majors[:2]} | {m.major_code for m in substitutes}
    dream_alt = (
        primary_dream.major_code[1:]
        if (len(primary_dream.major_code) == 7 and primary_dream.major_code.startswith("7"))
        else f"7{primary_dream.major_code}"
    )
    dream_seed_vec = (
        seed_by_code.get(primary_dream.major_code)
        or seed_by_code.get(dream_alt)
        or {}
    ).get("riasec") or {}

    bridge_scored: List[tuple[float, MajorRecommendationItem]] = []
    for cand in eligible_targets:
        if cand.major_code in used_codes:
            continue
        c_alt = cand.major_code[1:] if (len(cand.major_code) == 7 and cand.major_code.startswith("7")) else f"7{cand.major_code}"
        c_vec = (seed_by_code.get(cand.major_code) or seed_by_code.get(c_alt) or {}).get("riasec") or {}
        dream_dims = _get_major_top2_dims(primary_dream)
        overlap_with_dream = max([float(c_vec.get(d, 0.0)) for d in dream_dims], default=0.4) if c_vec else 0.4
        if dream_seed_vec and c_vec:
            bridge_metric = (cand.overall_score * 0.65) + (overlap_with_dream * 0.35)
        else:
            bridge_metric = cand.overall_score
        bridge_scored.append((bridge_metric, cand))

    bridge_scored.sort(key=lambda x: x[0], reverse=True)
    bridge_majors: List[MajorRecommendationItem] = [m for _, m in bridge_scored[:2]]

    # Phân loại 3 kịch bản đối chiếu giữa Nguyện vọng và Kết quả bài test
    # Luôn neo vào ngành "anchor" (liên quan nội dung cao nhất tới nghề mơ ước), không hoán đổi sang ngành khác.
    best_dream_item = primary_dream
    best_dream_top2 = _get_major_top2_dims(best_dream_item)
    dream_top1_in_student_top3 = (
        bool(best_dream_top2) and any(d in top3_dims for d in best_dream_top2[:1])
    )
    is_passion_aligned = (
        best_dream_item.score_riasec >= 0.74
        or (best_dream_item.score_riasec >= 0.60 and (dream_top1_in_student_top3 or not best_dream_top2))
    )

    if is_passion_aligned and primary_is_target:
        alignment_status = "ALIGNED_AND_ELIGIBLE"
        alignment_label = "Đam mê Trùng khớp Năng lực & Đủ Điểm chuẩn"
        alignment_score = int(round(best_dream_item.overall_score * 100))
        takeaways = [
            f"Nguyện vọng **\"{sanitized_dream}\"** khớp chặt chẽ với mã Holland **{top_holland_str}** của bạn (độ tương thích sở thích **{int(round(best_dream_item.score_riasec * 100))}%**).",
            f"Đạt ngưỡng điểm chuẩn: Ngành **{best_dream_item.major_name}** (Mã `{best_dream_item.major_code}`) hoàn toàn khả thi (`TARGET`) với **{best_dream_item.best_matching_block or block_name}** (**{best_dream_item.best_block_score or block_sum}đ** vs chuẩn ~**{best_dream_item.benchmark_cutoff}đ**).",
        ]
        if blocked_dreams and blocked_dreams[0].major_code != best_dream_item.major_code:
            b0 = blocked_dreams[0]
            takeaways.append(
                f"Lưu ý phân tầng: Ngành top cùng nhóm là **{b0.major_name}** (chuẩn ~**{b0.benchmark_cutoff}đ**) đang ở ngưỡng Thử thách (`REACH`), nên đặt **{best_dream_item.major_name}** làm nguyện vọng chủ lực an toàn."
            )
        else:
            takeaways.append(
                f"Độ phù hợp tổng thể 3 trụ cột đạt **{alignment_score}%** — bạn có thể tự tin đặt làm nguyện vọng ưu tiên số 1."
            )
        default_verdict = (
            f"Ước muốn trở thành **{sanitized_dream}** của bạn đồng nhất cao với kết quả trắc nghiệm khách quan (**{top_holland_str}**). "
            f"Đặc biệt, ngành **{best_dream_item.major_name}** (Mã `{best_dream_item.major_code}`) vừa khớp đam mê (**{int(round(best_dream_item.score_riasec * 100))}%**) "
            f"vừa nằm trong vùng điểm an toàn (`TARGET`, chuẩn ~**{best_dream_item.benchmark_cutoff}đ**)."
        )

    elif is_passion_aligned and not primary_is_target:
        alignment_status = "PASSION_MATCH_SCORE_GAP"
        alignment_label = "Đúng Thiên hướng Đam mê · Cần Ngành Liên thông Vừa sức"
        alignment_score = int(round((primary_dream.score_riasec * 0.65 + primary_dream.overall_score * 0.35) * 100))
        violation_reason = (
            primary_dream.constraint_violations[0]
            if primary_dream.constraint_violations
            else f"Điểm hiện tại ({primary_dream.best_block_score or block_sum}đ) chưa đạt ngưỡng chuẩn (~{primary_dream.benchmark_cutoff}đ)"
        )
        takeaways = [
            f"Thiên hướng sở thích của bạn (**{top_holland_str}**) rất phù hợp với **\"{sanitized_dream}\"** (độ khớp sở thích đạt **{int(round(primary_dream.score_riasec * 100))}%** ở ngành **{primary_dream.major_name}**).",
            f"Rào cản điểm số (`REACH`): Ngành **{primary_dream.major_name}** (Mã `{primary_dream.major_code}`) hiện bị chặn do *{violation_reason}*.",
        ]
        if substitutes:
            sub0 = substitutes[0]
            takeaways.append(
                f"Giải pháp thay thế vừa sức (`TARGET`): Chọn ngành liên thông **{sub0.major_name}** (Mã `{sub0.major_code}`, chuẩn ~**{sub0.benchmark_cutoff}đ**, độ khớp **{int(round(sub0.overall_score * 100))}%**) để giữ trọn đam mê nghề nghiệp mà vẫn an toàn đậu đại học."
            )
            default_verdict = (
                f"Bạn có tố chất sở thích rất hợp với **{sanitized_dream}** (**{int(round(primary_dream.score_riasec * 100))}%**), "
                f"nhưng ngành **{primary_dream.major_name}** (chuẩn ~**{primary_dream.benchmark_cutoff}đ**) đang vượt ngưỡng điểm hiện tại. "
                f"AI Agent khuyến nghị chuyển sang ngành cùng nhóm liên thông là **{sub0.major_name}** (Mã `{sub0.major_code}`, chuẩn ~**{sub0.benchmark_cutoff}đ** - `TARGET`) để theo đuổi đúng nghề mơ ước một cách an toàn."
            )
        else:
            default_verdict = (
                f"Đam mê **{sanitized_dream}** khớp với thiên hướng RIASEC của bạn, nhưng ngành **{primary_dream.major_name}** đang ở ngưỡng Thử thách (`REACH`). "
                f"Hãy kết hợp đặt thêm nguyện vọng an toàn thuộc nhóm **{top_test_major.major_name if top_test_major else 'vừa sức'}**."
            )

    else:
        alignment_status = "TRAIT_DIVERGENCE"
        alignment_label = "Nguyện vọng Khác biệt Thiên hướng · Gợi ý Ngành Giao thoa"
        alignment_score = int(round(primary_dream.overall_score * 100))
        takeaways = [
            f"Phát hiện độ lệch: Nguyện vọng **\"{sanitized_dream}\"** (ngành **{primary_dream.major_name}**) chỉ khớp **{int(round(primary_dream.score_riasec * 100))}%** với sở thích thực tế đo được từ 30 câu hỏi O*NET của bạn.",
            f"Năng lực tự nhiên nổi trội của bạn nằm ở nhóm **{top_holland_str}** (**{primary_dim_label}** - {int(round(sorted_riasec[0][1] * 100))}%), phù hợp xuất sắc với **{top_test_major.major_name if top_test_major else 'ngành mũi nhọn'}** (**{int(round(top_test_major.overall_score * 100)) if top_test_major else 85}%**).",
        ]
        if bridge_majors:
            b0 = bridge_majors[0]
            takeaways.append(
                f"Ngành cầu nối giao thoa (`TARGET`): **{b0.major_name}** (Mã `{b0.major_code}`, độ khớp **{int(round(b0.overall_score * 100))}%**, chuẩn ~**{b0.benchmark_cutoff}đ**) giúp bạn phát huy đúng thế mạnh **{primary_dim}** trong môi trường gần với định hướng mong muốn."
            )
        default_verdict = (
            f"Bài trắc nghiệm phát hiện sự khác biệt thú vị: bạn mong muốn làm **{sanitized_dream}** (độ khớp sở thích **{int(round(primary_dream.score_riasec * 100))}%**), "
            f"nhưng tố chất tự nhiên mạnh nhất của bạn lại là **{top_holland_str}** ({primary_dim_label}). "
            f"AI Agent gợi ý bạn cân nhắc ngành giao thoa **{bridge_majors[0].major_name if bridge_majors else primary_dream.major_name}** "
            f"để vừa tận dụng thế mạnh bẩm sinh vừa thỏa mãn mục tiêu nghề nghiệp."
        )

    # Thử làm giàu nhận xét bằng LLM (nếu có kết nối), luôn giữ nguyên số liệu tất định
    llm_verdict = None
    if enable_llm:
        llm_verdict = await _try_llm_aspiration_synthesis(
            sanitized_dream=sanitized_dream,
            alignment_status=alignment_status,
            top_holland=top_holland_str,
            best_block_str=best_block_str,
            primary_dream=best_dream_item,
            substitute_major=substitutes[0] if substitutes else None,
            bridge_major=bridge_majors[0] if bridge_majors else None,
        )

    sub_codes = {m.major_code for m in substitutes}
    displayed_dreams = (
        (blocked_dreams[:2] if blocked_dreams else [primary_dream])
        if alignment_status == "PASSION_MATCH_SCORE_GAP"
        else [m for m in dream_majors if m.major_code not in sub_codes][:2] or [primary_dream]
    )

    return {
        "has_aspiration": True,
        "dream_job": sanitized_dream,
        "desired_field": sanitized_field,
        "work_values": work_values,
        "preferred_environment": preferred_env,
        "score_strategy": score_strategy,
        "alignment_status": alignment_status,
        "alignment_label": alignment_label,
        "alignment_score": alignment_score,
        "holland_code": top_holland_str,
        "best_block_summary": best_block_str,
        "dream_majors": [_serialize_major_brief(m, "DREAM") for m in displayed_dreams],
        "recommended_substitutes": [_serialize_major_brief(m, "SUBSTITUTE") for m in substitutes[:2]],
        "bridge_majors": [_serialize_major_brief(m, "BRIDGE") for m in bridge_majors[:2]],
        "agent_verdict": llm_verdict or default_verdict,
        "key_takeaways": takeaways,
        "is_llm_enriched": bool(llm_verdict),
    }
