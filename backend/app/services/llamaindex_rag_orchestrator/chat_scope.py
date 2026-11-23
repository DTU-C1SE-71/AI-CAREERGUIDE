"""Deterministic chat routing. Deciding scope never consumes provider tokens."""
from __future__ import annotations

import re
import unicodedata
from typing import Literal

ScopeDecision = Literal["allow", "redirect", "clarify", "greeting"]
ResponseLengthMode = Literal["short", "medium", "detailed"]

_EXPLICIT_SHORT = re.compile(
    r"\b(ngan gon|tom tat|noi nhanh|tra loi ngan|ngan thoi|gon lai|1 cau|mot cau|"
    r"y chinh|diem chinh|chot lai|tldr|tl;dr|briefly|brief|short answer|concise)\b"
)
_EXPLICIT_DETAILED = re.compile(
    r"\b(chi tiet|phan tich ky|phan tich sau|phan tich ro|giai thich ky|giai thich ro|"
    r"giai thich tung buoc|tung buoc|cu the hon|noi ro hon|day du|chuyen sau|"
    r"toan dien|tu a den z|step by step|detailed|in depth|comprehensive)\b"
)
_DETAILED_INTENT = re.compile(
    r"\b(lo trinh|ke hoach hoc|ke hoach on|ke hoach trai nghiem|chien luoc|"
    r"so sanh|khac nhau|khac gi|giong va khac|uu nhuoc diem|uu va nhuoc diem|"
    r"nen chon .{2,40} hay |viet cv|mau cv|viet code|"
    r"code (?:python|java|javascript|typescript|c\+\+|c#|php|sql)|"
    r"bai mau|vi du minh hoa|tu lop 10|tu lop 11|4 tuan|tuan 1)\b"
)
_SHORT_DIRECT_CUE = re.compile(
    r"\b(la gi|bang may|bao nhieu|co can .{1,35} khong|co kho khong|co nen .{1,35} khong|"
    r"co bat buoc|mat bao lau|may nam|ma nganh|to hop nao|khoi nao|mon nao|"
    r"o dau|nut nao|tab nao|muc nao|diem san|muc luong|luong bao nhieu|"
    r"luong khoi diem|dung khong|phai khong)\b"
)
_MULTI_PART_CUE = re.compile(r"\b(dong thoi|ngoai ra|voi lai|ben canh do|va cho biet|con .{2,30} thi sao)\b")


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
    return " ".join("".join(c for c in normalized if unicodedata.category(c) != "Mn").split())


# Deny the requested unrelated action even if an industry name is also present.
_UNRELATED = re.compile(
    r"\b(cong thuc nau|huong dan nau|thoi tiet.{0,40}(?:hom nay|ngay mai|cuoi tuan)|"
    r"(?:xem|cho biet).{0,15}thoi tiet|xo so|lo de|tu vi|xem boi|"
    r"uong thuoc|ke don|chan doan benh|"
    r"an gi (toi|trua|sang)|nghe nhac|"
    r"(?:ke|viet|sang tac).{0,30}(?:truyen cuoi|chuyen cuoi|bai tho)|"
    r"(?:ty so|ket qua tran|thang tran|lich thi dau)|"
    r"(?:weather|lottery|horoscope|tell me a joke|write a poem))\b"
)
_TOPIC = re.compile(
    r"\b(nganh|nghe nghiep|tim hieu nghe|chon nghe|nghe nao|nghe gi|huong nghiep|dinh huong|viec lam|cong viec|"
    r"tuyen sinh|holland|riasec|tu duy|ky nang|so thich|nguyen vong|thu nhap|"
    r"hoc|hoc tap|hoc phi|on thi|on tap|mon toan|mon ly|mon van|ky thi|bai tap|bai hoc|bai toan|dao ham|"
    r"diem so|diem thi|diem chuan|hoc ba|tot nghiep|that nghiep|"
    r"tieng anh|ielts|toefl|muc tieu|tuong lai|muon tro thanh|"
    r"cv|xin viec|thuc tap|luong|chon khoi|ra truong|"
    r"bac si|ky su|dieu duong|lap trinh|ui/ux|ux/ui|"
    r"career|major|study|studying|education|learning|exam|university|school|"
    r"skill|job|scholarship|future|homework)\b"
)
# Subject concepts and programming are valid learning topics on their own;
# students need not prepend 'học' or tie every question to a chosen major.
_ACADEMIC_CONCEPT = re.compile(
    r"\b(hoc tap|cach hoc|hoc tot|tu hoc|on thi|on tap|bai tap|bai hoc|"
    r"tieng anh|ielts|toefl|lap trinh|tin hoc|"
    r"phep (?:cong|tru|nhan|chia|tinh)|bang cuu chuong|phan so|phan thuc|"
    r"so (?:nguyen|tu nhien|thap phan|nguyen to|phuc)|luy thua|can bac|"
    r"phuong trinh|bat phuong trinh|he pt|pt\s*bac\s*\d|ham so|"
    r"dao ham|tich phan|logarit|luong giac|xac suat|thong ke|"
    r"hinh hoc|dai so|dinh ly|pytago|pythagoras|toan hoc|mon toan|"
    r"vat ly|dinh luat|newton|dien truong|tu truong|van toc|gia toc|khoi luong|trong luong|nang luong|"
    r"hoa hoc|phan ung|oxi hoa|nguyen tu|phan tu|electron|"
    r"sinh hoc|te bao|quang hop|adn|di truyen|"
    r"ngu van|van hoc|bai tho|van ban|nhan vat|bien phap tu tu|"
    r"ngu phap|danh tu|dong tu|tinh tu|thi hien tai|thi qua khu|"
    r"lich su|dia ly|khi hau|weather|"
    r"vong lap|thuat toan|cau truc du lieu|ham de quy|"
    r"code la gi|con tro|syntaxerror|typeerror|traceback|"
    r"arithmetic|algebra|geometry|equation|fraction|grammar|programming)\b"
)
_PROGRAMMING_LANGUAGE = re.compile(
    r"(?<!\w)(?:python|javascript|typescript|java|c\+\+|c\#|"
    r"sql|html|css|scratch|pascal|rust|golang|php|swift|kotlin|json|xml|"
    r"(?:ngon ngu|lap trinh|trong) c)(?!\w)"
)
_MATH_EXPRESSION = re.compile(r"[\d\s.,xyzabc+*/^()=<>:!?%\-]+")
_UNRELATED_ACTION = re.compile(
    r"\b(?:cho|xin|lay|xem|du doan).{0,25}(?:so xo so|ket qua xo so|so de)\b"
)
_CAREER_CONTEXT = re.compile(
    r"\b(nganh|nghe nghiep|chon nghe|tim hieu nghe|huong nghiep|tuyen sinh|"
    r"nguyen vong|viec lam|cong viec|ra truong|ky su|bac si|cv|xin viec|"
    r"muc luong|tien luong|luong bao nhieu|luong khoi diem|ke toan|thu nhap|career|major|job)\b"
)
_FOLLOWUP = re.compile(
    r"(?:tai sao(?: lai (?:nhu vay|the))?|vi sao(?: lai (?:nhu vay|the))?|cu the(?: hon)?|noi ro(?: hon)?|giai thich them|"
    r"cho (?:em |minh )?(?:mot )?vi du(?: de hieu)?|them vi du|con gi nua|"
    r"giai thich tung buoc|giai thich chi tiet|"
    r"(?:vay )?(?:em |minh )?(?:nen )?bat dau tu dau|mat bao lau|"
    r"co kho khong|cai nao phu hop hon|nganh do|nghe do|"
    r"why|more|tell me more|how long)(?: a| nhe| duoc khong)?[?!. ]*"
)
_GREETING = re.compile(r"(?:xin chao|chao(?: ban)?|hello|hi|alo|cam on|thank you)[!?. ]*")
# Compositional detector for AI CareerGuide UI / usage / troubleshooting questions.
_PLATFORM_ENTITY = re.compile(
    r"\b(ai careerguide|careerguide|web nay|trang web nay|trang nay|website nay|app nay|ung dung nay|"
    r"nen tang nay|he thong nay|trang web|website|giao dien|tro ly ai|co van ai|chatbot)\b|"
    r"\bhe thong\b(?!\s+(?:thong tin|mang|dien|nhung|dieu khien|phap luat|y te|giao duc|tai chinh|ke toan|van tai|nong nghiep|sinh thai|tuan hoan|than kinh|mien dich))"
)
_ASSISTANT_IDENTITY = re.compile(
    r"\b(ban la ai|bot la ai|ban lam duoc gi|ban giup duoc gi|ban ho tro(?: duoc)? gi|"
    r"co the giup gi|ho tro nhung gi|co nhung tinh nang gi|co chuc nang gi|o day co gi)\b"
)
_APP_FEATURE = re.compile(
    r"\b(ho so|profile|tai khoan|thong tin ca nhan|trac nghiem|bai test|bai danh gia|cau hoi|ket qua|"
    r"lich su|pdf|bao cao|lo trinh|4 tuan|kham pha nganh|danh muc nganh|435 nganh|de xuat|"
    r"thuat toan de xuat|phan tich ai|phan tich ky nang|nguyen vong|khoi lop|gioi tinh|"
    r"dang nhap|dang ky|dang xuat|google|mat khau|tinh nang|chuc nang|menu|thanh ben|"
    r"nut bam|nut|tab|man hinh|bieu do|radar|diem so|diem hoc ba|diem mon|nhap diem|sua diem|cap nhat diem|hoc ba|tong quan)\b"
)
_HELP_CUE = re.compile(
    r"\b(cach|lam sao|lam the nao|nhu the nao|the nao|ra sao|huong dan|chi (?:minh|em|toi|giup|dum|cach)|"
    r"o dau|vao dau|bam (?:vao )?dau|nam o dau|muc nao|nut nao|tab nao|cho nao|"
    r"kiem tra|xem|xem lai|tra cuu|tim|nhap|sua|chinh sua|cap nhat|doi|thay doi|xoa|luu|xuat|tai|mo|bat dau|lam lai|"
    r"su dung|dung|xai|thao tac|hoat dong|tro giup|giup do|"
    r"la gi|de lam gi|dung de lam gi|co tac dung gi|khac nhau|khac gi|"
    r"khong thay|khong hien|khong mo duoc|khong luu duoc|khong dang nhap duoc|khong bam duoc|"
    r"bi loi|tai sao khong|sao khong|sao lai khong|load lau|"
    r"how to|how do i|where is|where can i|what is this|user guide)\b"
)
_EXPLICIT_SYSTEM_HELP = re.compile(
    r"\b(de xuat nganh co ai|thuat toan de xuat|kham pha nganh|danh muc nganh|435 nganh|"
    r"lo trinh 4 tuan|xuat pdf|tai pdf|xem lai cau hoi|lich su lam bai|huong dan su dung|"
    r"tro giup su dung|dang nhap google|quen mat khau|doi mat khau|how to use|user guide)\b"
)
_PERSONAL_EVIDENCE_CAREER = re.compile(
    r"\b(thieu du lieu gi|bo sung (?:gi|bang chung)|doi chieu nganh|phu hop (?:voi )?(?:so thich|nganh)|"
    r"nen hoc nganh nao|nen chon nganh nao|nganh nao phu hop|chon khoi|ra truong lam gi|"
    r"muc luong|luong bao nhieu|xin viec|thuc tap|cv)\b"
)


def _has_system_help_topic(message: str) -> bool:
    text = _fold(message)
    if _PERSONAL_EVIDENCE_CAREER.search(text):
        return False
    if _PROGRAMMING_LANGUAGE.search(text) and not _PLATFORM_ENTITY.search(text):
        return False
    if _EXPLICIT_SYSTEM_HELP.search(text) or _ASSISTANT_IDENTITY.search(text):
        return True
    if _PLATFORM_ENTITY.search(text):
        return True
    if _APP_FEATURE.search(text) and _HELP_CUE.search(text):
        return True
    return False


def _has_academic_topic(message: str) -> bool:
    text = _fold(message)
    if (_ACADEMIC_CONCEPT.search(text) or _PROGRAMMING_LANGUAGE.search(text)
            or re.search(r"\btoán\b", message.casefold())):
        return True
    # Recognize notation only. Never execute user expressions or code.
    expression = unicodedata.normalize("NFKC", text).translate(str.maketrans({
        "×": "*", "÷": "/", "−": "-", "–": "-", "≤": "<=", "≥": ">=",
    }))
    expression = re.sub(r"^(?:giai|tinh|solve|calculate)(?:\s+(?:pt|phuong trinh))?\s+", "", expression)
    operators = {"cong": "+", "tru": "-", "nhan": "*", "chia": "/"}
    expression = re.sub(r"(?<=\d)\s+(cong|tru|nhan|chia)\s+(?=\d)",
                        lambda match: operators[match.group(1)], expression)
    expression = re.sub(r"\s*(?:bang (?:may|bao nhieu)|ra bao nhieu|la bao nhieu|=?\s*bao nhieu)[?!. ]*$", "", expression)
    return bool(_MATH_EXPRESSION.fullmatch(expression) and re.search(r"\d", expression)
                and re.search(r"[+*/^=:<>\-]", expression))


def _unrelated_request(text: str) -> bool:
    if _UNRELATED_ACTION.search(text):
        return True
    # Exceptions belong to the matching topic. A generic 'bài tập' prefix
    # must never authorize cooking, clinical advice or entertainment requests.
    for match in _UNRELATED.finditer(text):
        topic = match.group(0)
        if topic in {"xo so", "lottery"} and re.search(r"\b(xac suat|probability|thong ke)\b", text):
            continue
        if ("bai tho" in topic or topic == "write a poem") and re.search(
            r"\b(bai tap ngu van|bai tap mon van|mon ngu van|mon van|phan tich|cam nhan)\b", text,
        ):
            continue
        if ("weather" in topic or "thoi tiet" in topic) and not re.search(
            r"\b(hom nay|ngay mai|cuoi tuan)\b", text,
        ) and re.search(r"\b(giai thich khoa hoc|what is weather|explain weather|scientific explanation)\b", text):
            continue
        return True
    return False


def _has_topic(message: str) -> bool:
    # Preserve the accented profession word; folded 'nghe' also means 'listen'.
    return bool(_TOPIC.search(_fold(message)) or _has_academic_topic(message)
                or _has_system_help_topic(message)
                or re.search(r"\bnghề\b", message.casefold()))


def is_system_help_question(message: str, history=None) -> bool:
    """Detect user-support / UI how-to questions about AI CareerGuide."""
    text = _fold(message)
    if _unrelated_request(text):
        return False
    if _has_system_help_topic(message):
        return True
    if _FOLLOWUP.fullmatch(text):
        for entry in reversed((history or [])[-12:]):
            if entry.role != "user":
                continue
            previous = _fold(entry.content)
            if _unrelated_request(previous):
                break
            if _has_system_help_topic(entry.content):
                return True
            if not _FOLLOWUP.fullmatch(previous):
                break
    return False


def is_academic_question(message: str, history=None) -> bool:
    """Use tutoring context for subjects, while preserving career personalization."""
    text = _fold(message)
    if (_unrelated_request(text) or _has_system_help_topic(message) or _CAREER_CONTEXT.search(text)
            or re.search(r"\b(?:nghề|lương)\b", message.casefold())):
        return False
    if _has_academic_topic(message):
        return True
    if _FOLLOWUP.fullmatch(text):
        for entry in reversed((history or [])[-12:]):
            if entry.role != "user":
                continue
            previous = _fold(entry.content)
            if (_unrelated_request(previous) or _CAREER_CONTEXT.search(previous)
                    or re.search(r"\b(?:nghề|lương)\b", entry.content.casefold())):
                break
            if _has_academic_topic(entry.content):
                return True
            if not _FOLLOWUP.fullmatch(previous):
                break
    return False


def classify_chat_message(message: str, history=None) -> ScopeDecision:
    """A selected major or assistant welcome never authorizes unrelated input."""
    text = _fold(message)
    if _unrelated_request(text):
        return "redirect"
    if _has_topic(message):
        return "allow"
    if _GREETING.fullmatch(text):
        return "greeting"
    if _FOLLOWUP.fullmatch(text):
        # Follow-up chains may inherit a real user topic, but stop at an
        # unrelated/unclear turn rather than mining old assistant boilerplate.
        for entry in reversed((history or [])[-12:]):
            if entry.role != "user":
                continue
            previous = _fold(entry.content)
            if _unrelated_request(previous):
                break
            if _has_topic(entry.content):
                return "allow"
            if not _FOLLOWUP.fullmatch(previous):
                break
    return "clarify"


def classify_response_length(
    message: str,
    preference: str = "auto",
    history=None,
) -> ResponseLengthMode:
    """Deterministically choose short, medium, or detailed answer depth."""
    pref = (preference or "auto").strip().lower()
    if pref in ("short", "medium", "detailed"):
        return pref  # type: ignore[return-value]

    text = _fold(message)
    words = [w for w in text.split() if w]
    word_count = len(words)
    question_marks = message.count("?")

    if _EXPLICIT_SHORT.search(text):
        return "short"
    if _EXPLICIT_DETAILED.search(text) or _DETAILED_INTENT.search(text):
        return "detailed"

    # Multi-question or long compound prompt -> detailed response.
    if word_count >= 24 or question_marks >= 2 or (word_count >= 16 and _MULTI_PART_CUE.search(text)):
        return "detailed"

    # Quick arithmetic / pure math notation (unless asking for steps/code).
    expr = unicodedata.normalize("NFKC", text).translate(str.maketrans({
        "×": "*", "÷": "/", "−": "-", "–": "-", "≤": "<=", "≥": ">=",
    }))
    expr = re.sub(r"^(?:giai|tinh|solve|calculate)(?:\s+(?:pt|phuong trinh))?\s+", "", expr)
    expr = re.sub(r"\s*(?:bang (?:may|bao nhieu)|ra bao nhieu|la bao nhieu|=?\s*bao nhieu)[?!. ]*$", "", expr)
    if _MATH_EXPRESSION.fullmatch(expr) and re.search(r"\d", expr) and re.search(r"[+*/^=:<>\-]", expr):
        return "short"

    # Short direct lookup / yes-no / single-concept question.
    if word_count <= 13 and (_SHORT_DIRECT_CUE.search(text) or word_count <= 5):
        return "short"

    return "medium"


def response_length_guidance(mode: ResponseLengthMode) -> tuple[str, int]:
    """Return (system_prompt_directive, max_tokens_budget) for the chosen length mode."""
    if mode == "short":
        return (
            "ĐỘ DÀI PHẢN HỒI — NGẮN GỌN: Đây là câu hỏi trực tiếp/tra cứu nhanh. "
            "Trả lời thẳng trọng tâm trong khoảng 2–4 câu hoặc tối đa 3 gạch đầu dòng ngắn (khoảng 50–120 từ). "
            "Không mở bài hay kết bài dài dòng, không lặp lại câu hỏi.",
            450,
        )
    if mode == "detailed":
        return (
            "ĐỘ DÀI PHẢN HỒI — CHI TIẾT & CHUYÊN SÂU: Câu hỏi cần phân tích đầy đủ, so sánh hoặc hướng dẫn từng bước. "
            "Hãy trình bày rõ ràng theo từng mục có tiêu đề/gạch đầu dòng (dùng bảng Markdown nếu so sánh nhiều lựa chọn), "
            "kèm ví dụ thực tế và gợi ý hành động cụ thể (~350–700 từ).",
            3200,
        )
    return (
        "ĐỘ DÀI PHẢN HỒI — VỪA PHẢI: Trả lời cân đối, đủ ý chính nhưng súc tích (~150–280 từ, khoảng 3–5 gạch đầu dòng hoặc 2–3 đoạn ngắn dễ đọc).",
        1100,
    )


def local_scope_reply(decision: ScopeDecision) -> str:
    if decision == "greeting":
        return "Chào bạn! Mình hỗ trợ hướng nghiệp, học tập, tìm hiểu nghề nghiệp và hướng dẫn sử dụng các tính năng trên AI CareerGuide. Bạn muốn tìm hiểu vấn đề nào?"
    return "Mình chưa hiểu rõ câu hỏi. Bạn hãy viết rõ hơn điều muốn hỏi về học tập, chọn ngành, nghề nghiệp hoặc cách sử dụng hệ thống AI CareerGuide để mình hỗ trợ đúng nhé."
