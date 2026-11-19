"""Deterministic aspiration matching and evidence-gated current options.

Career intent is resolved before ranking. Legacy TARGET labels and heuristic
scores cannot establish readiness; only the server's readiness assessment can.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from app.schemas.recommender import MajorRecommendationItem
from app.services.llamaindex_rag_orchestrator.guidance_rag import sanitize_pii
from app.services.recommender.engine import format_block_with_subjects
from app.services.recommender.readiness import build_interest_evidence

def _strip_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt để so khớp từ khóa nghề nghiệp linh hoạt và chính xác."""
    if not text:
        return ""
    text = text.replace("đ", "d").replace("Đ", "D")
    norm = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in norm if unicodedata.category(ch) != "Mn").lower().strip()


# Atomic professions take precedence over broad legacy field vocabulary.
# Each tuple is (stable intent id, canonical display text, aliases, degree codes).
ATOMIC_CAREERS = [
    ('PHYSICIAN', 'Bác sĩ', ['bac si', 'y khoa', 'y da khoa', 'physician', 'medical doctor', 'doctor'], ['7720101']),
    ('DENTIST', 'Nha sĩ', ['nha si', 'rang ham mat', 'dentist'], ['7720501']),
    ('PHARMACIST', 'Dược sĩ', ['duoc si', 'duoc hoc', 'pharmacist', 'pharmacy'], ['7720201']),
    ('NURSE', 'Điều dưỡng', ['dieu duong', 'nurse', 'nursing'], ['7720301']),
    ('LAB_TECH', 'Kỹ thuật xét nghiệm y học', ['xet nghiem'], ['7720601']),
    ('REHABILITATION', 'Kỹ thuật phục hồi chức năng', ['phuc hoi chuc nang', 'vat ly tri lieu'], ['7720603']),
    ('NUTRITION', 'Dinh dưỡng', ['dinh duong', 'nutrition'], ['7720401']),
    ('SOFTWARE', 'Lập trình phần mềm', ['lap trinh', 'phan mem', 'software', 'coder', 'developer', 'fullstack'], ['7480103', '7480201', '7480101']),
    ('AI', 'Kỹ sư trí tuệ nhân tạo', ['tri tue nhan tao', 'machine learning', 'ai'], ['7480107', '7480101']),
    ('DATA', 'Khoa học dữ liệu', ['khoa hoc du lieu', 'data science', 'data scientist'], ['7460108']),
    ('CYBER', 'An toàn thông tin', ['an ninh mang', 'an toan thong tin', 'cyber', 'hacker'], ['7480208', '7480202']),
    ('CHIP', 'Thiết kế vi mạch', ['vi mach', 'ban dan', 'chip', 'ic design'], ['7520202', '7520207']),
    ('AUTOMOTIVE', 'Kỹ thuật ô tô', ['o to', 'xe dien', 'automotive'], ['7520130']),
    ('ACCOUNTANT', 'Kế toán', ['ke toan', 'accountant'], ['7340301']),
    ('AUDITOR', 'Kiểm toán', ['kiem toan', 'auditor'], ['7340302']),
    ('FINANCE', 'Tài chính ngân hàng', ['tai chinh', 'ngan hang', 'chung khoan'], ['7340201']),
    ('MARKETING', 'Marketing', ['marketing', 'thuong hieu'], ['7340115']),
    ('LOGISTICS', 'Logistics', ['logistics', 'chuoi cung ung'], ['7340123', '7510605']),
    ('ECOMMERCE', 'Thương mại điện tử', ['thuong mai dien tu', 'e-commerce'], ['7340122']),
    ('GRAPHIC_DESIGN', 'Thiết kế đồ họa', ['do hoa', 'ui/ux', 'ui ux'], ['7210403']),
    ('ARCHITECT', 'Kiến trúc sư', ['kien truc'], ['7580101']),
    ('FASHION', 'Thiết kế thời trang', ['thoi trang'], ['7210404']),
    ('PSYCHOLOGIST', 'Tâm lý học', ['tam ly', 'psychologist', 'tham van'], ['7310401']),
    ('SOCIAL_WORK', 'Công tác xã hội', ['cong tac xa hoi'], ['7760101']),
    ('HUMAN_RESOURCES', 'Quản trị nhân lực', ['nhan su', 'quan tri nhan luc', 'hr'], ['7340404']),
    ('LAWYER', 'Luật sư', ['luat su', 'phap che', 'tham phan', 'kiem sat'], ['7380101', '7380107']),
    ('DIPLOMAT', 'Ngoại giao', ['ngoai giao', 'quan he quoc te'], ['7310206']),
    ('SINGER', 'Ca sĩ', ['ca si', 'thanh nhac', 'idol'], ['7210205']),
    ('ACTOR', 'Diễn viên', ['dien vien', 'dien xuat'], ['7210226']),
    ('PILOT', 'Phi công', ['phi cong', 'pilot'], []),
    ('CHEF', 'Đầu bếp', ['dau bep', 'nau an', 'nau nuong', 'am thuc'], []),
    ('TOUR_GUIDE', 'Hướng dẫn viên du lịch', ['huong dan vien'], ['7810101']),
    ('INFORMATION_TECH', 'Công nghệ thông tin', ['cong nghe thong tin', 'it', 'cntt'], ['7480201']),
    ('TEACHER', 'Giáo viên', ['giao vien', 'su pham', 'giang vien', 'day hoc'], ['7140201', '7140202', '7140209', '7140210']),
    ('BUSINESS', 'Quản trị kinh doanh', ['quan tri kinh doanh', 'kinh doanh', 'khoi nghiep', 'ceo'], ['7340101']),
    ('AUTOMATION', 'Kỹ sư tự động hóa', ['tu dong hoa', 'robot', 'co dien tu'], ['7520216', '7520114']),
    ('MECHANICAL', 'Kỹ sư cơ khí', ['co khi'], ['7520103']),
    ('ELECTRONICS', 'Kỹ sư điện tử viễn thông', ['dien tu', 'vien thong', 'embedded', 'nhung'], ['7520207']),
    ('JOURNALIST', 'Nhà báo', ['nha bao', 'bao chi', 'bien tap'], ['7320101']),
    ('MEDIA', 'Truyền thông đa phương tiện', ['truyen thong', 'da phuong tien', 'youtuber', 'streamer', 'tiktoker', 'content creator', 'sang tao noi dung'], ['7320104', '7320106']),
    ('SPORTS', 'Huấn luyện viên thể thao', ['the thao', 'van dong vien', 'huan luyen vien'], ['7810301', '7810302']),
    ('POLICE', 'Công an', ['cong an', 'canh sat', 'trinh sat'], ['7860101', '7860102', '7860107']),
    ('MILITARY', 'Quân đội', ['quan doi', 'quan su', 'bo doi'], ['7860218']),
]


def _code(code: Any) -> str:
    value = str(code).strip()
    return value[1:] if len(value) == 7 and value.startswith('7') else value


def _contains(text: str, phrase: str) -> bool:
    return bool(re.search(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', text))


def _resolve_intent(dream_job, desired_field, majors, seed_by_code):
    """Match text only: scores, strategies, readiness and ranking never affect identity."""
    query = _strip_accents(dream_job or desired_field)
    if not query:
        return 'EMPTY', [], []
    matches = []
    for intent_id, label, aliases, codes in ATOMIC_CAREERS:
        evidence = [alias for alias in aliases if _contains(query, alias)]
        if evidence:
            matches.append((intent_id, label, evidence, codes))

    # A broad healthcare field offers explicit professions to choose from.
    if not matches and any(_contains(query, alias) for alias in ['y te', 'suc khoe', 'healthcare', 'benh vien']):
        matches.extend((i, label, ['Lĩnh vực chăm sóc sức khỏe'], codes) for i, label, _, codes in ATOMIC_CAREERS[:7])

    if not matches:
        # Exact catalog phrase matches are deliberately conservative: overlapping
        # generic tokens such as "kỹ thuật" cannot turn unknown text into a goal.
        for major in sorted(majors, key=lambda item: str(item.major_code)):
            seed = seed_by_code.get(str(major.major_code)) or seed_by_code.get(_code(major.major_code)) or seed_by_code.get('7' + _code(major.major_code)) or {}
            phrases = [major.major_name, *(seed.get('careers') or [])]
            evidence = [str(phrase) for phrase in phrases if len(_strip_accents(str(phrase))) >= 4 and _contains(query, _strip_accents(str(phrase)))]
            if evidence:
                matches.append(('MAJOR_' + _code(major.major_code), major.major_name, evidence, [major.major_code]))
    if len(matches) > 1:
        all_evidence = [phrase for _, _, phrases, _ in matches for phrase in phrases]
        matches = [match for match in matches if any(
            not any(phrase != longer and _contains(longer, phrase) for longer in all_evidence)
            for phrase in match[2]
        )]
    candidates = [
        {'id': intent_id, 'label': label, 'canonicalDreamJob': label, 'evidence': evidence}
        for intent_id, label, evidence, _ in matches
    ]
    if len(matches) != 1:
        return ('AMBIGUOUS' if matches else 'UNRECOGNIZED'), candidates, []
    priority = {_code(code): index for index, code in enumerate(matches[0][3])}
    goals = sorted((m for m in majors if _code(m.major_code) in priority),
                   key=lambda m: (priority[_code(m.major_code)], str(m.major_code)))
    return 'MATCHED', candidates, goals


def _match_aspiration_to_majors(dream_job, desired_field, work_values, score_strategy, all_ranked_majors, seed_by_code):
    """Compatibility entry point; preferences cannot alter the resolved profession."""
    return _resolve_intent(dream_job, desired_field, all_ranked_majors, seed_by_code)[2]


def _readiness(item):
    value = getattr(item, 'readiness', None)
    if isinstance(value, dict) and value.get('status') in {'READY_REFERENCE', 'NEEDS_IMPROVEMENT', 'UNKNOWN'}:
        return dict(value)
    return {
        'status': 'UNKNOWN', 'reason': 'MISSING_READINESS',
        'message': 'Chưa có bằng chứng học lực và mốc tham chiếu có thể đối chiếu.',
        'block': None, 'block_score': None, 'benchmark_cutoff': None,
        'min_recommended': None, 'missing_subjects': [], 'violations': [], 'gaps': [],
        'reference_kind': None, 'reference_id': None, 'reference_method': None,
        'score_kind': None, 'block_source': None, 'policy_version': 'aspiration-v1',
    }


def _serialize_major_brief(item, role_tag='DREAM', *, interest_complete=False, relation_reason=''):
    readiness = _readiness(item)
    academic_known = readiness['status'] in {'READY_REFERENCE', 'NEEDS_IMPROVEMENT'}
    block = readiness.get('block')
    return {
        'major_code': item.major_code, 'major_name': item.major_name,
        'category': item.category or 'Khác',
        'overall_match': round(item.overall_score * 100) if interest_complete and academic_known else None,
        'riasec_fit': round(item.score_riasec * 100) if interest_complete else None,
        'academic_fit': round(item.score_academic * 100) if academic_known else None,
        'cognitive_fit': (getattr(item, 'fit', None) or {}).get('cognitive'),
        'preference_evidence': (getattr(item, 'score_breakdown', None) or {}).get('aspiration_preferences', {}),
        'score_meaning': 'HEURISTIC_FIT_NOT_ADMISSION_PROBABILITY',
        'feasibility_tier': 'TARGET' if readiness['status'] == 'READY_REFERENCE' else ('REACH' if academic_known else 'UNKNOWN'),
        'feasibility_label': {'READY_REFERENCE': 'Đạt mốc tham chiếu', 'NEEDS_IMPROVEMENT': 'Cần cải thiện', 'UNKNOWN': 'Chưa đủ dữ liệu'}[readiness['status']],
        'best_matching_block': block,
        'best_matching_block_formatted': format_block_with_subjects(block) if block else None,
        'best_block_score': readiness.get('block_score'),
        'benchmark_cutoff': readiness.get('benchmark_cutoff'),
        'min_recommended': readiness.get('min_recommended'),
        'score_gap': getattr(item, 'score_gap', None),
        'constraint_passed': readiness['status'] == 'READY_REFERENCE',
        'constraint_violations': readiness.get('violations', []),
        'admission_advice': readiness.get('message'),
        'readiness': readiness, 'relation_reason': relation_reason,
        'is_trending': bool(getattr(item, 'is_trending', False)),
        'trend_tier': getattr(item, 'trend_tier', None),
        'trend_priority': getattr(item, 'trend_priority', 0) or 0,
        'trend_label': getattr(item, 'trend_label', None), 'role_tag': role_tag,
    }


# Explicit alternatives with a concrete shared area; category equality alone is
# insufficient (e.g. medicine and nursing confer different qualifications).
RELATED_PATHS = {
    'PILOT': ({'7520120', '7840102'}, 'Cùng lĩnh vực hàng không nhưng là nghề khác; ngành này không thay thế đào tạo và giấy phép phi công.'),
    'CHEF': ({'7810202'}, 'Cùng lĩnh vực dịch vụ ăn uống nhưng quản trị nhà hàng không thay thế đào tạo nghiệp vụ đầu bếp.'),
    'SOFTWARE': ({'7480208', '7480202', '7460108'}, 'Cùng lĩnh vực phát triển hệ thống số; đây là hướng nghề khác cần tìm hiểu thêm.'),
    'AI': ({'7480103', '7460108'}, 'Cùng sử dụng lập trình và xử lý dữ liệu; chương trình và vị trí nghề nghiệp khác nhau.'),
    'DATA': ({'7480101', '7480103'}, 'Cùng sử dụng lập trình và phân tích dữ liệu; cần đối chiếu chương trình đào tạo.'),
    'PHYSICIAN': ({'7720301', '7720601'}, 'Cùng môi trường chăm sóc sức khỏe nhưng là nghề khác, không cấp bằng bác sĩ hay bảo đảm liên thông.'),
}


async def analyze_career_aspiration(
    aspiration_data: Optional[Dict[str, Any]],
    student_riasec: Dict[str, float],
    best_block_stats: Optional[Dict[str, Any]],
    all_ranked_majors: List[MajorRecommendationItem],
    seed_by_code: Optional[Dict[str, Dict[str, Any]]] = None,
    enable_llm: bool = True,
    interest_evidence: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Produce a deterministic assessment; enable_llm is retained for old callers."""
    raw = aspiration_data or {}
    dream = sanitize_pii(str(raw.get('dream_job') or raw.get('dreamJob') or '').strip())
    field = sanitize_pii(str(raw.get('desired_field') or raw.get('desiredField') or '').strip())
    strategy = str(raw.get('score_strategy') or raw.get('scoreStrategy') or 'FLEXIBLE_PATHWAY')
    values = raw.get('work_values') or raw.get('workValues') or []
    values = [sanitize_pii(str(value)) for value in values] if isinstance(values, list) else []
    environment = sanitize_pii(str(raw.get('preferred_environment') or raw.get('preferredEnvironment') or ''))
    evidence = interest_evidence if isinstance(interest_evidence, dict) else build_interest_evidence(None, legacy_vector=student_riasec)
    complete = evidence.get('status') == 'COMPLETE'
    holland = ''.join(dim for dim, _ in sorted(student_riasec.items(), key=lambda pair: pair[1], reverse=True)[:3]) if complete and student_riasec else ''
    if seed_by_code is None:
        from app.services.taxonomy.service import load_seed_majors
        seed_by_code = {str(item['major_code']): item for item in load_seed_majors() if item.get('major_code')}
    match_status, candidates, goals = _resolve_intent(dream, field, all_ranked_majors, seed_by_code)
    related = []
    relation = ''
    if match_status == 'MATCHED' and candidates[0]['id'] in RELATED_PATHS:
        related_codes, relation = RELATED_PATHS[candidates[0]['id']]
        normalized_codes = {_code(code) for code in related_codes}
        goal_codes = {_code(item.major_code) for item in goals}
        related = [item for item in all_ranked_majors if _code(item.major_code) in normalized_codes - goal_codes]
    if strategy == 'CHALLENGE_TOP':
        related = []
    goal_codes = {item.major_code for item in goals}

    def option_order(item):
        readiness = _readiness(item)
        score = readiness.get('block_score')
        thresholds = [readiness.get(k) for k in ('benchmark_cutoff', 'min_recommended') if isinstance(readiness.get(k), (int, float))]
        margin = score - max(thresholds) if isinstance(score, (int, float)) and thresholds else float('-inf')
        # Incomplete interests must not inherit the upstream composite rank.
        availability = (getattr(item, 'score_breakdown', None) or {}).get('pillar_availability') or {}
        fit = item.overall_score if (complete or any(availability.values())) and strategy != 'REALISTIC_SAFE' else 0
        return (item.major_code not in goal_codes, -fit, -margin, str(item.major_code))

    if match_status == 'EMPTY':
        # Open exploration is explicit; readiness still gates every current item.
        selected = all_ranked_majors
    elif match_status == 'MATCHED':
        selected = goals + related
    else:
        selected = []
    current = sorted((item for item in selected if _readiness(item)['status'] == 'READY_REFERENCE'), key=option_order)
    exploration = sorted((item for item in selected if _readiness(item)['status'] == 'UNKNOWN'), key=option_order)
    if strategy == 'REALISTIC_SAFE':
        exploration = [item for item in exploration if item.major_code in goal_codes]
    substitutes = sorted((item for item in related if _readiness(item)['status'] == 'READY_REFERENCE'), key=option_order)

    def brief(item, role):
        reason = 'Ngành gắn với mục tiêu nghề nghiệp đã nhận diện.' if item.major_code in goal_codes else relation
        if match_status == 'EMPTY':
            reason = 'Ngành trong danh mục để khám phá; bạn chưa chọn mục tiêu nghề nghiệp.'
        return _serialize_major_brief(item, role, interest_complete=complete, relation_reason=reason)

    if match_status == 'EMPTY':
        status, label = 'EXPLORATORY_DISCOVERY', 'Khám phá nghề nghiệp'
        verdict = 'Bạn chưa chọn nghề mục tiêu. Hãy khám phá ngành và bổ sung thông tin để đối chiếu.'
    elif match_status == 'AMBIGUOUS':
        status, label = 'AMBIGUOUS_ASPIRATION', 'Cần chọn một nghề mục tiêu'
        verdict = 'Nội dung nguyện vọng có nhiều hướng nghề. Hãy chọn một nghề bên dưới để phân tích riêng.'
    elif match_status == 'UNRECOGNIZED':
        status, label = 'UNRECOGNIZED_ASPIRATION', 'Chưa nhận diện được nghề'
        verdict = 'Chưa ghép được nguyện vọng với danh mục. Hãy nhập tên nghề hoặc tên ngành cụ thể hơn.'
    elif not current:
        status, label = 'NO_CURRENT_OPTIONS', 'Chưa có lựa chọn đạt mốc tham chiếu'
        verdict = 'Đã ghi nhận mục tiêu của bạn. Hiện chưa có ngành liên quan được xác nhận đạt mốc tham chiếu; hãy xem dữ liệu còn thiếu hoặc nội dung cần cải thiện trên từng ngành.'
    else:
        status, label = 'CURRENT_REFERENCE_OPTIONS', 'Có lựa chọn đạt mốc tham chiếu'
        verdict = 'Các lựa chọn hiện tại đã đạt mốc tham chiếu được đối chiếu. Đây không phải cam kết trúng tuyển; cần kiểm tra điều kiện tuyển sinh của trường và phương thức đăng ký.'
    takeaways = []
    if evidence.get('status') == 'NON_DISCRIMINATING':
        takeaways.append('Sáu nhóm sở thích chưa phân hóa; chưa dùng kết quả này để kết luận mức phù hợp ngành.')
    elif not complete:
        takeaways.append('Chưa đủ bằng chứng bài sở thích hoàn chỉnh; chưa kết luận mức độ phù hợp RIASEC.')
    if match_status == 'MATCHED' and not goals:
        takeaways.append('Đã nhận diện nghề nhưng danh mục hiện tại chưa có ngành trực tiếp tương ứng.')
    for item in goals[:2]:
        readiness = _readiness(item)
        message = readiness.get('message') or 'Cần bổ sung dữ liệu để đối chiếu.'
        takeaways.append(f'{item.major_name}: {message}')
    for item in current[:2]:
        readiness = _readiness(item)
        block = readiness.get('block')
        takeaways.append(f"{item.major_name}: {format_block_with_subjects(block) if block else 'Tổ hợp chưa xác định'}, điểm {readiness.get('block_score')}, mốc tham chiếu {readiness.get('benchmark_cutoff')}.")
    primary = goals[0] if goals else None
    return {
        'has_aspiration': bool(dream or field), 'dream_job': dream, 'desired_field': field,
        'work_values': values, 'preferred_environment': environment, 'score_strategy': strategy,
        'preference_evidence': ((getattr(primary, 'score_breakdown', None) or {}).get('aspiration_preferences', {}) if primary else {}),
        'match_status': match_status, 'intent_candidates': candidates,
        'interest_evidence': evidence, 'alignment_status': status, 'alignment_label': label,
        'alignment_score': brief(primary, 'DREAM')['overall_match'] if primary else None,
        'holland_code': holland, 'best_block_summary': '',
        'dream_majors': [brief(item, 'DREAM') for item in goals],
        'current_options': [brief(item, 'CURRENT') for item in current[:6]],
        'exploration_options': [brief(item, 'EXPLORATION') for item in exploration[:6]],
        'recommended_substitutes': [brief(item, 'SUBSTITUTE') for item in substitutes[:2]],
        'bridge_majors': [], 'agent_verdict': verdict, 'key_takeaways': takeaways,
        'is_llm_enriched': False,
    }
