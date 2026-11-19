"""Item-level Sub-facet Affinity & Asymmetric Veto Gate (PA 3).

Prevents RIASEC 6-dimension averaging collapse (e.g., liking A1/A2/A3/A5 while
strongly disliking A4=1 Music, yet still receiving Music majors in top recommendations).

Maps high-specificity items among the 30 high-school RIASEC questions (R1..C5) to
Vietnam MOET Circular 09/74 major code prefixes (3-7 digits) plus folded name
keywords for interdisciplinary majors (e.g., Sư phạm Âm nhạc 7140221).
100% deterministic, zero LLM calls, gracefully no-ops when raw R1..C5 answers are absent.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class SubfacetRule:
    question_code: str
    label: str
    code_prefixes: Tuple[str, ...]
    keywords: Tuple[str, ...] = ()


# Only high-specificity domain questions participate in Veto/Affinity.
# General/cross-cutting traits (e.g. A5, E1, C5) contribute solely through the 6-dim RIASEC vector.
SUBFACET_RULES: Tuple[SubfacetRule, ...] = (
    # --- Group A (Artistic) ---
    SubfacetRule(
        question_code="A4",
        label="Âm nhạc, thanh nhạc & biểu diễn",
        code_prefixes=("72102",),
        keywords=(
            "am nhac", "thanh nhac", "nhac cu", "bieu dien", "dien vien",
            "san khau", "nghe thuat mua", "su pham am nhac", "piano", "guitar",
            "dan ca", "chi huy am nhac", "sang tac am nhac",
        ),
    ),
    SubfacetRule(
        question_code="A1",
        label="Mỹ thuật, đồ họa & thiết kế thời trang",
        code_prefixes=("72101", "72104"),
        keywords=(
            "hoi hoa", "my thuat", "thiet ke do hoa", "thiet ke thoi trang",
            "su pham my thuat", "dieu khac", "do hoa", "gom",
        ),
    ),
    SubfacetRule(
        question_code="A2",
        label="Kiến trúc, nội thất & không gian",
        code_prefixes=("75801",),
        keywords=("kien truc", "noi that", "canh quan", "quy hoach do thi"),
    ),
    SubfacetRule(
        question_code="A3",
        label="Báo chí, truyền thông & điện ảnh",
        code_prefixes=("73201", "72103"),
        keywords=("bao chi", "truyen thong da phuong tien", "dien anh", "nhiep anh", "dao dien", "quay phim"),
    ),
    # --- Group R (Realistic) ---
    SubfacetRule(
        question_code="R1",
        label="Cơ khí, điện - điện tử & tự động hóa",
        code_prefixes=("751", "752"),
        keywords=("co khi", "dien tu", "tu dong hoa", "co dien tu", "ky thuat o to", "ky thuat nhiet"),
    ),
    SubfacetRule(
        question_code="R2",
        label="Xây dựng & kỹ thuật công trình",
        code_prefixes=("75802", "75803"),
        keywords=("ky thuat xay dung", "xay dung dan dung", "cau duong", "trac dia"),
    ),
    SubfacetRule(
        question_code="R3",
        label="Nông - Lâm - Thủy sản & Thú y",
        code_prefixes=("762", "764"),
        keywords=("nong hoc", "lam nghiep", "thuy san", "chan nuoi", "thu y", "bao ve thuc vat", "trong trot"),
    ),
    SubfacetRule(
        question_code="R4",
        label="Xét nghiệm & công nghệ thực phẩm",
        code_prefixes=("75401", "77206"),
        keywords=("xet nghiem", "cong nghe thuc pham", "hoa duoc"),
    ),
    SubfacetRule(
        question_code="R5",
        label="Thể chất, thể thao & An ninh - Quốc phòng",
        code_prefixes=("786", "78103", "7140206", "7140208"),
        keywords=(
            "the duc the thao", "huan luyen the thao", "giao duc the chat",
            "quoc phong", "an ninh", "canh sat", "quan su", "phong chay",
        ),
    ),
    # --- Group I (Investigative) ---
    SubfacetRule(
        question_code="I1",
        label="Toán học, thống kê & khoa học tính toán",
        code_prefixes=("746",),
        keywords=("toan hoc", "toan ung dung", "thong ke", "su pham toan"),
    ),
    SubfacetRule(
        question_code="I2",
        label="Công nghệ thông tin, phần mềm & AI",
        code_prefixes=("748", "7460108"),
        keywords=(
            "cong nghe thong tin", "khoa hoc may tinh", "ky thuat phan mem",
            "tri tue nhan tao", "khoa hoc du lieu", "an toan thong tin",
        ),
    ),
    SubfacetRule(
        question_code="I3",
        label="Y khoa, Dược học & Công nghệ sinh học",
        code_prefixes=("772", "742"),
        keywords=("y khoa", "duoc hoc", "rang ham mat", "y hoc", "cong nghe sinh hoc", "sinh hoc"),
    ),
    SubfacetRule(
        question_code="I4",
        label="Vật lý, Hóa học, Bán dẫn & Khoa học tự nhiên",
        code_prefixes=("744",),
        keywords=("vat ly", "hoa hoc", "ban dan", "khi tuong", "thien van", "dia chat"),
    ),
    # --- Group S (Social) ---
    SubfacetRule(
        question_code="S1",
        label="Sư phạm & Khoa học giáo dục",
        code_prefixes=("714",),
        keywords=("su pham", "giao duc mam non", "giao duc tieu hoc", "giao duc dac biet"),
    ),
    SubfacetRule(
        question_code="S2",
        label="Điều dưỡng, chăm sóc y tế & công tác xã hội",
        code_prefixes=("77203", "776", "73104"),
        keywords=("dieu duong", "ho sinh", "cong tac xa hoi", "tam ly hoc"),
    ),
    # --- Group E (Enterprising) ---
    SubfacetRule(
        question_code="E4",
        label="Pháp luật & tranh biện",
        code_prefixes=("738",),
        keywords=("luat", "phap luat", "kiem sat"),
    ),
    # --- Group C (Conventional) ---
    SubfacetRule(
        question_code="C1",
        label="Kế toán, Kiểm toán & Tài chính",
        code_prefixes=("73403", "73402"),
        keywords=("ke toan", "kiem toan", "tai chinh", "ngan hang"),
    ),
    SubfacetRule(
        question_code="C4",
        label="Logistics, chuỗi cung ứng & vận tải",
        code_prefixes=("7510605", "784"),
        keywords=("logistics", "chuoi cung ung", "khai thac van tai", "hang hai", "hang khong"),
    ),
)

_QUESTION_ORDER = [f"{g}{i}" for g in ("R", "I", "A", "S", "E", "C") for i in range(1, 6)]


def _fold_text(text: str) -> str:
    normalized = unicodedata.normalize("NFD", str(text or "").casefold().replace("đ", "d"))
    return " ".join("".join(c for c in normalized if unicodedata.category(c) != "Mn").split())


def extract_item_ratings(raw_answers: Optional[Dict[str, Any]]) -> Dict[str, int]:
    """Normalize raw RIASEC answers (R1..C5 or numeric index 0..29) into {question_code: 1..5}."""
    if not isinstance(raw_answers, dict) or not raw_answers:
        return {}
    ratings: Dict[str, int] = {}
    for key, val in raw_answers.items():
        if isinstance(val, bool):
            continue
        try:
            num = int(round(float(val)))
        except (TypeError, ValueError):
            continue
        if num < 1 or num > 5:
            continue

        skey = str(key).strip().upper()
        if skey in _QUESTION_ORDER:
            ratings[skey] = num
        elif skey.isdigit():
            idx = int(skey)
            if 0 <= idx < len(_QUESTION_ORDER):
                ratings[_QUESTION_ORDER[idx]] = num
    return ratings


def match_major_subfacets(major_code: str, major_name: str) -> List[SubfacetRule]:
    """Return all SubfacetRules matching a major by MOET prefix or folded name keywords."""
    code = str(major_code or "").strip()
    folded_name = _fold_text(major_name)
    matched: List[SubfacetRule] = []
    for rule in SUBFACET_RULES:
        if any(code.startswith(prefix) for prefix in rule.code_prefixes):
            matched.append(rule)
            continue
        if rule.keywords and any(kw in folded_name for kw in rule.keywords):
            matched.append(rule)
    return matched


def evaluate_subfacet_gate(
    major_code: str,
    major_name: str,
    raw_answers: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Evaluate Asymmetric Sub-facet Veto & Affinity Gate for a candidate major.

    Returns dict with:
      - status: "STRONG_VETO" | "SOFT_PENALTY" | "AFFINITY_BOOST" | "NEUTRAL"
      - riasec_multiplier: float
      - overall_multiplier: float
      - riasec_boost: float
      - overall_boost: float
      - matched_items: list of {question_code, label, rating}
      - note: optional Vietnamese XAI explanation
    """
    ratings = extract_item_ratings(raw_answers)
    if not ratings:
        return {
            "status": "NEUTRAL",
            "riasec_multiplier": 1.0,
            "overall_multiplier": 1.0,
            "riasec_boost": 0.0,
            "overall_boost": 0.0,
            "matched_items": [],
            "note": None,
        }

    rules = match_major_subfacets(major_code, major_name)
    matched_items = [
        {"question_code": r.question_code, "label": r.label, "rating": ratings[r.question_code]}
        for r in rules
        if r.question_code in ratings
    ]
    if not matched_items:
        return {
            "status": "NEUTRAL",
            "riasec_multiplier": 1.0,
            "overall_multiplier": 1.0,
            "riasec_boost": 0.0,
            "overall_boost": 0.0,
            "matched_items": [],
            "note": None,
        }

    # Strictest-veto-wins (min rating): e.g. Sư phạm Âm nhạc with S1=5 & A4=1 is still vetoed by A4=1.
    lowest = min(matched_items, key=lambda x: x["rating"])
    highest = max(matched_items, key=lambda x: x["rating"])

    if lowest["rating"] == 1:
        return {
            "status": "STRONG_VETO",
            "riasec_multiplier": 0.30,
            "overall_multiplier": 0.45,
            "riasec_boost": 0.0,
            "overall_boost": 0.0,
            "matched_items": matched_items,
            "note": (
                f"Hạ thứ hạng mạnh vì bạn chọn 'Rất không thích' hoạt động đặc thù của ngành "
                f"({lowest['label']} — câu {lowest['question_code']})."
            ),
        }

    if lowest["rating"] == 2:
        return {
            "status": "SOFT_PENALTY",
            "riasec_multiplier": 0.65,
            "overall_multiplier": 0.78,
            "riasec_boost": 0.0,
            "overall_boost": 0.0,
            "matched_items": matched_items,
            "note": (
                f"Giảm mức ưu tiên vì bạn chọn 'Không thích' hoạt động liên quan "
                f"({lowest['label']} — câu {lowest['question_code']})."
            ),
        }

    if lowest["rating"] >= 4 and highest["rating"] == 5:
        return {
            "status": "AFFINITY_BOOST",
            "riasec_multiplier": 1.0,
            "overall_multiplier": 1.0,
            "riasec_boost": 0.06,
            "overall_boost": 0.05,
            "matched_items": matched_items,
            "note": (
                f"Cộng hưởng tích cực với hoạt động bạn chọn 'Rất thích' "
                f"({highest['label']} — câu {highest['question_code']})."
            ),
        }

    return {
        "status": "NEUTRAL",
        "riasec_multiplier": 1.0,
        "overall_multiplier": 1.0,
        "riasec_boost": 0.0,
        "overall_boost": 0.0,
        "matched_items": matched_items,
        "note": None,
    }
