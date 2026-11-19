"""Deterministic chat routing. Deciding scope never consumes provider tokens."""
from __future__ import annotations

import re
import unicodedata
from typing import Literal

ScopeDecision = Literal["allow", "redirect", "clarify", "greeting"]


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
                or re.search(r"\bnghề\b", message.casefold()))


def is_academic_question(message: str, history=None) -> bool:
    """Use tutoring context for subjects, while preserving career personalization."""
    text = _fold(message)
    if (_unrelated_request(text) or _CAREER_CONTEXT.search(text)
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


def local_scope_reply(decision: ScopeDecision) -> str:
    if decision == "greeting":
        return "Chào bạn! Mình hỗ trợ hướng nghiệp, học tập, tìm hiểu nghề nghiệp và mục tiêu tương lai. Bạn muốn tìm hiểu vấn đề nào?"
    return "Mình chưa hiểu rõ câu hỏi. Bạn hãy viết rõ hơn điều muốn hỏi về học tập, chọn ngành, nghề nghiệp hoặc mục tiêu tương lai để mình hỗ trợ đúng nhé."
