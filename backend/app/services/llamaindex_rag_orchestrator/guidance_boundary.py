"""Closed rendering boundary: user text chooses topics, never executable instructions.

No generative model receives private evidence or supplies student-facing prose on this
path. Catalog identifiers and the recommendation engine are the only sources of facts.
"""
from __future__ import annotations

import re
import unicodedata
import uuid
from typing import Any
from fastapi import HTTPException
from app.schemas.rag import GuidanceEvidenceRequest
from app.schemas.recommender import RecommendationRequest
from app.services.recommender.readiness import build_interest_evidence, validate_readiness_grades

EVIDENCE_FIELDS = {
    "riasec_answers", "riasec_scores", "cognitive_answers", "cognitive_preferences",
    "grades_by_subject", "score_context", "aspiration", "assessment_id", "gender", "grade_level",
}
POLICY_VERSION = "guidance-evidence-v1"
REDIRECT = "Mình chỉ hỗ trợ chọn ngành, tìm hiểu nghề, đối chiếu hồ sơ và kế hoạch học tập trong AI CareerGuide. Mình không cung cấp khóa, cấu hình nội bộ, lời nhắc hệ thống hay hồ sơ của người khác. Bạn có thể hỏi về ngành hoặc kỹ năng muốn tìm hiểu."


def fold(value: Any) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(value).casefold().replace("đ", "d")) if unicodedata.category(c) != "Mn")


def plain(value: Any, limit: int = 400) -> str:
    # Catalog data is plain display data, never commands/HTML/links.
    value = re.sub(r"https?://\S+|<[^>]*>", "", str(value or ""))
    value = re.sub(r"[\[\]`*_#<>]", "", value)
    return " ".join(value.split())[:limit]


def resolve_profile_owner(requested: uuid.UUID | None, current: uuid.UUID | None) -> uuid.UUID | None:
    if requested is not None and current is None:
        raise HTTPException(401, "Đăng nhập để dùng hồ sơ đã lưu.")
    if requested is not None and requested != current:
        raise HTTPException(403, "Chỉ được dùng hồ sơ của tài khoản đang đăng nhập.")
    return current


async def guidance_facts(db, payload: GuidanceEvidenceRequest, current_user_id=None) -> dict:
    """Same authoritative snapshot and scorer as Dashboard, no writes or LLM calls."""
    from app.services.recommender.service import resolve_assessment_evidence, calculate_3pillar_recommendations
    owner = resolve_profile_owner(payload.user_id, current_user_id)
    if payload.assessment_id and owner is None:
        raise HTTPException(401, "Đăng nhập để xem bản đánh giá đã lưu.")
    raw = payload.model_dump(exclude_unset=True, include=EVIDENCE_FIELDS)
    profile = await resolve_assessment_evidence(db, owner, raw)
    # Guest identity remains None; it never authorizes a private query.
    result = await calculate_3pillar_recommendations(
        db=db, user_id=owner, payload=RecommendationRequest(top_k=500),
        inline_profile=profile, resolved_profile=profile, include_all_candidates=True,
        raise_if_unassessed=False, persist_history=False,
    )
    items = {it.major_code: it for it in result.recommendations}
    return {
        "profile": profile, "items": items,
        "interest": build_interest_evidence(profile.get("riasec_answers"), profile.get("riasec_scores")),
        "grades": validate_readiness_grades(profile.get("grades_by_subject") or {}),
        "diagnostic_count": len(payload.diagnostic_skills_mastered or []),
        "policy_version": POLICY_VERSION,
    }


def mentioned_codes(message: str, items: dict) -> list[str]:
    text = fold(message)
    found = []
    for code, item in items.items():
        name = fold(item.major_name)
        if re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text) or re.search(r"(?<!\d)" + re.escape(code) + r"(?!\d)", text):
            found.append(code)
    return sorted(found, key=lambda c: (-len(items[c].major_name), c))[:3]


def career_intent(message: str, items: dict):
    # Shared profession resolver only selects members of the active scored catalog.
    # Never union seed codes into items or substitute a different licensed profession.
    from app.services.recommender.aspiration_agent import _resolve_intent
    return _resolve_intent(message, "", list(items.values()), {})


def strongest_pillar(item) -> str:
    available = (item.score_breakdown or {}).get("pillar_availability", {})
    measured = [
        (item.score_riasec, "sở thích", "w_riasec"),
        (item.score_academic, "đối chiếu học lực tham khảo", "w_academic"),
        (item.score_preference, "thiên hướng học tập tự khai", "w_preference"),
    ]
    measured = [(score, label) for score, label, key in measured if available.get(key)]
    if not measured:
        return "Chưa có trụ cột đủ dữ liệu để xếp mức phù hợp cá nhân; hãy hoàn thành bài sở thích, tư duy và điểm số."
    _, label = max(measured, key=lambda entry: entry[0])
    return f"Căn cứ nổi bật nhất trong các trụ cột có dữ liệu của ngành này: {label}. Đây là so sánh điểm khớp theo quy tắc hệ thống, không chứng minh năng lực nghề."


def forbidden_request(message: str) -> bool:
    text = fold(message)
    # Controls refusal UX only. Security does not depend on detecting these strings:
    # rendering cannot read secrets, execute tools or display user/model instructions.
    # 1. Explicit reveal/bypass verbs targeting prompts, secrets, internal architecture or other users.
    if re.search(
        r"(reveal|print|show|dump|leak|expose|list|ignore|bypass|override|disclose|extract|"
        r"hien|tiet lo|in ra|bo qua|quen di|dua|cho xem|xem|lay|liet ke|cung cap|mo ta|giai thich)"
        r".{0,70}"
        r"(system prompt|developer prompt|developer message|developer instruction|"
        r"api.?key|khoa api|khoa bao mat|secret.?key|access.?token|refresh.?token|jwt|bearer token|"
        r"mat khau (?:admin|he thong|db|database|csdl|server|nguoi khac|user)|"
        r"huong dan he thong|quy tac noi bo|cau hinh noi bo|cau hinh server|bien moi truong|\b\.env\b|"
        r"database schema|db schema|schema csdl|cau truc (?:co so du lieu|csdl|database|db)|"
        r"ten bang|cac bang|danh sach bang|ten truong|ten cot|"
        r"api endpoint|cac endpoint|danh sach endpoint|route backend|"
        r"source code|ma nguon|code backend|code frontend|"
        r"lo hong (?:he thong|bao mat)|co che (?:kiem duyet|bao mat)|"
        r"(?:ho so|du lieu|lich su|thong tin|tai khoan|diem so).{0,35}(?:nguoi khac|nguoi dung khac|ban khac|user khac|hoc sinh khac|tai khoan khac|tat ca nguoi dung))",
        text,
    ):
        return True
    # 2. Direct prompt-injection / rule-override / fake-admin escalation.
    if re.search(
        r"(bo qua (?:moi |tat ca )?(?:quy tac|gioi han|chi thi|lenh)|"
        r"ignore (?:all |any )?(?:previous |prior )?(?:rules|instructions|prompts|boundaries)|"
        r"prompt injection|jailbreak|"
        r"(?:toi la|minh la|gia danh|voi tu cach|i am|act as).{0,30}(?:admin|quan tri vien|developer|dev|chu he thong).{0,45}"
        r"(?:cho xem|cung cap|tiet lo|lay|bo qua|truy cap|in ra|show|reveal|give|dump))",
        text,
    ):
        return True
    # 3. Direct or indirect probing of this system's internal DB/code/server/secrets/vulnerabilities.
    if re.search(
        r"\b(system prompt|developer prompt|database schema|db schema|cau truc co so du lieu|cau truc csdl|"
        r"ten bang trong (?:db|csdl|database|he thong)|api endpoint(?:s)? cua he thong|"
        r"ma nguon cua (?:he thong|web|trang)|source code cua (?:he thong|web|trang)|cau hinh server|"
        r"lo hong (?:bao mat|he thong)|co che kiem duyet|co che bao mat phia sau|"
        r"khoa api|api key|secret key|jwt secret)\b|"
        r"(?:web|trang web|trang|he thong|app|ung dung)(?: nay)?\s+(?:dung|su dung|chay|viet bang|deploy|host).{0,25}"
        r"(?:database|csdl|co so du lieu|server|backend|source code|ma nguon|api key|secret)|"
        r"(?:database|csdl|co so du lieu|backend|server|schema|ma nguon|source code|api endpoint).{0,25}"
        r"(?:cua (?:web|trang|he thong|app)|nay la gi|gom nhung gi)",
        text,
    ):
        return True
    return False


def in_scope(message: str, codes: list[str], history=None) -> bool:
    from app.services.llamaindex_rag_orchestrator.chat_scope import classify_chat_message
    decision = classify_chat_message(message, history)
    return decision == "allow" or (decision == "clarify" and bool(codes))


def personal_facts(code: str, facts: dict) -> dict:
    item = facts["items"][code]
    interest = facts["interest"]
    if interest["status"] == "COMPLETE":
        riasec = f"Đã có đủ bài sở thích. Mức khớp sở thích với ngành theo công thức hệ thống: {item.score_riasec * 100:.1f}%. Đây không phải điểm năng lực hay xác suất trúng tuyển."
    elif interest["status"] == "NON_DISCRIMINATING":
        riasec = "Bạn đã hoàn thành đủ 30 câu sở thích nhưng sáu nhóm Holland có mức điểm ngang nhau; kết quả chưa phân biệt được nhóm sở thích nổi bật. Hệ thống chưa dùng kết quả này để khẳng định tỷ lệ phù hợp ngành. Bạn có thể xem lại câu trả lời theo trải nghiệm thực tế hoặc thử hoạt động ở từng nhóm."
    elif interest["status"] == "PARTIAL":
        riasec = "Bài sở thích còn thiếu câu trả lời; chưa kết luận mức phù hợp Holland của bạn."
    elif interest["status"] == "LEGACY_UNVERIFIED":
        riasec = "Có vector sở thích lưu trước đây nhưng thiếu đáp án gốc để xác nhận độ đầy đủ; chưa kết luận mức phù hợp."
    else:
        riasec = "Chưa có bằng chứng sở thích trong hồ sơ đang xét; hãy bổ sung bài đánh giá để đối chiếu."
    ready = item.readiness or {}
    ready_status = ready.get("status", "UNKNOWN")
    if ready_status == "READY_REFERENCE":
        academic = f"Điểm {ready.get('block_score')} ở tổ hợp {plain(ready.get('block'))} đạt mốc tham chiếu {ready.get('benchmark_cutoff')}. Đây không phải cam kết trúng tuyển; vẫn cần kiểm tra điều kiện của trường và phương thức."
    elif ready_status == "NEEDS_IMPROVEMENT":
        academic = "Chưa đạt điều kiện đối chiếu hiện tại. " + plain(ready.get("message"), 700)
    else:
        academic = "Chưa đủ bằng chứng tuyển sinh tương thích để kết luận ngành vừa sức. " + plain(ready.get("message"), 700)
    if facts["grades"]["errors"]:
        academic += " Có điểm môn không hợp lệ hoặc tên môn trùng nhưng mâu thuẫn cần sửa."
    profile = facts["profile"]
    cognitive = profile.get("cognitive_preferences") or {}
    cognition = "Thiên hướng học tập là tự khai, không phải bài đo năng lực chuẩn hóa. " + ("Đã nhận dữ liệu để hệ thống đối chiếu; cần xem trạng thái đầy đủ trong kết quả đánh giá." if cognitive else "Chưa có dữ liệu tư duy trong hồ sơ này.")
    diagnosis = (f"Bạn tự khai {facts['diagnostic_count']} kỹ năng; chưa coi đây là kết quả kiểm tra đã xác minh." if facts["diagnostic_count"] else "Chưa có kết quả chẩn đoán kỹ năng đã xác minh trong yêu cầu này.")
    focus = [plain(g, 220) for g in (item.competency_gaps or [])[:4]]
    if not focus:
        focus = ["Đối chiếu môn học và điều kiện chính thức của chương trình bạn chọn.", "Thử một bài nhập môn của ngành và tự ghi nhận mức hứng thú; chưa suy ra đã thành thạo."]
    observed = [riasec, f"Đã nhận điểm hợp lệ của {len(facts['grades']['scores'])} môn; học bạ không chứng minh thành thạo nghề."]
    return {"riasec": riasec, "academic": academic, "cognitive": cognition, "diagnostic": diagnosis, "focus": focus, "observed": observed}


def describe(code: str, facts: dict) -> str:
    item = facts["items"][code]
    return f"**{plain(item.major_name)} ({code})** — nhóm {plain(item.category)}. Bạn có thể đối chiếu chương trình đào tạo, yêu cầu môn học và vị trí nghề của ngành trên trang chi tiết. Các điều kiện cụ thể phụ thuộc chương trình và trường."


def render_chat(payload, facts: dict) -> tuple[str, str | None, list[str]]:
    from app.services.llamaindex_rag_orchestrator.chat_scope import classify_chat_message
    items = facts["items"]
    text = fold(payload.message)
    # A career word embedded in an unrelated task does not authorize that task.
    if classify_chat_message(payload.message, payload.history) == "redirect":
        return REDIRECT, None, ["Tìm hiểu nghề kỹ sư AI", "Đối chiếu hồ sơ chọn ngành"]
    direct = mentioned_codes(payload.message, items)
    intent_status, candidates, goals = career_intent(payload.message, items)
    if not direct and goals:
        direct = [item.major_code for item in goals[:3]]
    if forbidden_request(payload.message):
        return REDIRECT, None, ["Tìm hiểu ngành An toàn thông tin", "Cần bổ sung gì vào hồ sơ hướng nghiệp?"]
    if not in_scope(payload.message, direct, payload.history) and not candidates:
        return REDIRECT, None, ["Ngành nào trong hệ thống phù hợp sở thích của mình?", "Cần bổ sung gì vào hồ sơ hướng nghiệp?"]
    if not direct and candidates:
        if intent_status == "AMBIGUOUS":
            labels = [plain(candidate["label"]) for candidate in candidates[:5]]
            return ("Bạn muốn tìm hiểu nghề nào cụ thể: " + "; ".join(labels) + "? Mỗi nghề có yêu cầu đào tạo riêng, mình cần phân biệt trước khi đối chiếu.", None, labels[:3])
        return ("Mình đã nhận diện hướng nghề nhưng chưa có ngành đang hoạt động được liên kết trực tiếp trong danh mục. Bạn có thể làm rõ vai trò hoặc tên chương trình; mình không tự chuyển sang nghề khác hay suy ra điều kiện hành nghề.", None, ["Xem các ngành trong danh mục", "Cần bổ sung bằng chứng gì để chọn ngành?"])
    if not direct and intent_status == "UNRECOGNIZED" and re.search(r"muon (lam|tro thanh)|tim hieu nghe\s+", text):
        return ("Mình chưa xác định được ngành liên quan từ tên nghề này. Bạn hãy nêu nghề cụ thể, công việc muốn làm hoặc tên chương trình để mình đối chiếu danh mục, không tự chuyển sang ngành đang được chọn.", None, ["Tìm hiểu nghề kỹ sư AI", "Tìm hiểu nghề bác sĩ"])
    codes = direct
    exploratory = False
    if not codes and payload.major_code in items:
        codes = [payload.major_code]
    if not codes:
        for entry in reversed(payload.history or []):
            if entry.role == "user":
                codes = mentioned_codes(entry.content, items)
                if not codes:
                    _, _, previous_goals = career_intent(entry.content, items)
                    codes = [item.major_code for item in previous_goals[:3]]
                if codes:
                    break
    text = fold(payload.message)
    if not codes:
        ready = [i for i in items.values() if i.readiness.get("status") == "READY_REFERENCE"]
        if any(word in text for word in ("de xuat", "goi y", "chon nganh", "nganh nao", "recommend")):
            if ready:
                codes = [i.major_code for i in ready[:3]]
            else:
                # No arbitrary alphabetical recommendations for a completely empty profile.
                supported = [i for i in items.values() if any((i.score_breakdown or {}).get("pillar_availability", {}).values())]
                supported.sort(key=lambda i: (-i.overall_score, i.major_code))
                codes = [i.major_code for i in supported[:3]]
                exploratory = bool(codes)
            if not codes:
                return ("Chưa có dữ liệu đủ để gợi ý ngành phù hợp cá nhân. Bạn hãy hoàn thành bài sở thích gồm 6 nhóm Holland, phần tư duy và điểm số, hoặc nêu nghề muốn khám phá. Mình có thể giới thiệu nghề trước mà không khẳng định bạn đã đủ năng lực.", None,
                        ["Tìm hiểu nghề kỹ sư AI", "Tìm hiểu nghề bác sĩ", "Tìm hiểu nghề UI/UX"])
        else:
            return ("Bạn hãy chọn một ngành trong danh mục hoặc nêu nghề muốn tìm hiểu. Mình có thể giải thích sở thích, học lực, nguyện vọng và kế hoạch trải nghiệm ngành; khi thiếu nguồn đối chiếu sẽ không khẳng định ngành vừa sức.", None,
                    ["Tìm hiểu ngành Khoa học máy tính", "Tìm hiểu ngành Điều dưỡng", "Cần bổ sung gì vào hồ sơ hướng nghiệp?"])
    planning = any(t in text for t in ("ke hoach", "lo trinh", "tuan", "tu hoc", "study plan"))
    if planning:
        codes = codes[:1]
    output = []
    if exploratory:
        output.append("Gợi ý khám phá theo phần hồ sơ hiện có — chưa xác minh vừa sức và chưa phải lựa chọn đã đạt điều kiện tuyển sinh. Cần bổ sung bài đánh giá còn thiếu, điểm môn và nguồn tuyển sinh cùng phương thức/thang điểm trước khi kết luận.")
    if goals and direct:
        output.append("Các ngành dưới đây có liên hệ với hướng nghề bạn hỏi để tìm hiểu chương trình. Tên nghề và bằng tốt nghiệp không tự xác nhận quyền hành nghề; cần kiểm tra chương trình, chuẩn đầu ra và điều kiện nghề cụ thể.")
    for code in codes[:3]:
        item = items[code]
        detail = personal_facts(code, facts)
        output.extend([describe(code, facts), detail["riasec"], detail["academic"], detail["cognitive"], strongest_pillar(item)])
        if any(t in text for t in ("ke hoach", "lo trinh", "tuan", "tu hoc", "study plan")):
            hours = payload.weekly_hours_available
            # One week's exploratory plan, explicit time budget, no claim of mastery.
            reading = max(1, hours // 3)
            practice = max(1, hours // 3)
            reflection = hours - reading - practice
            output.append(f"Kế hoạch trải nghiệm Tuần 1 ({hours} giờ, theo ngân sách bạn chọn): đọc chương trình và yêu cầu nhập môn {reading} giờ; thử bài nhập môn phù hợp ngành {practice} giờ; ghi nhận hứng thú, câu hỏi và nội dung cần hỗ trợ {reflection} giờ. Đây là kế hoạch khám phá, không chứng nhận đã đủ kỹ năng hay đủ điều kiện tuyển sinh.")
        elif "ky nang" in text:
            output.append(detail["diagnostic"] + " " + " ".join(detail["focus"]))
        if any(t in text for t in ("hoc phi", "thu nhap", "luong", "dia phuong", "suc khoe")):
            output.append("Hệ thống chưa có dữ liệu đã xác minh cho chi phí, mức lương hoặc điều kiện riêng bạn hỏi. Hãy đối chiếu nguồn của trường/đơn vị nghề nghiệp; mình không tự tạo con số hay điều kiện loại trừ.")
    code = codes[0]
    name = plain(items[code].major_name)
    return "\n\n".join(output), code, [f"Đối chiếu ngành {name} với hồ sơ của mình", f"Lập kế hoạch trải nghiệm Tuần 1 ngành {name}", "Cần bổ sung bằng chứng gì để đối chiếu học lực?"]
