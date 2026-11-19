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
    score_breakdown = getattr(item, 'score_breakdown', None) or {}
    subfacet = score_breakdown.get('subfacet_gate') or {}
    if not isinstance(subfacet, dict):
        subfacet = {}
    riasec_pct = round(item.score_riasec * 100) if interest_complete else None
    subfacet_status = subfacet.get('status', 'NEUTRAL') if interest_complete else 'NEUTRAL'
    subfacet_note = subfacet.get('note') if interest_complete else None
    trait_warning = None
    if interest_complete:
        if subfacet_status in ('STRONG_VETO', 'SOFT_PENALTY'):
            trait_warning = (
                subfacet_note
                or 'Ngành mục tiêu này đang mâu thuẫn với câu trả lời Không thích trong bài trắc nghiệm sở thích của bạn.'
            )
        elif riasec_pct is not None and riasec_pct < 45:
            trait_warning = (
                f'Độ tương thích sở thích RIASEC khá thấp ({riasec_pct}%): '
                'Đặc trưng nghề nghiệp này lệch khá nhiều so với nhóm sở thích nổi trội của bạn.'
            )
    return {
        'major_code': item.major_code, 'major_name': item.major_name,
        'category': item.category or 'Khác',
        'overall_match': round(item.overall_score * 100) if interest_complete and academic_known else None,
        'riasec_fit': riasec_pct,
        'academic_fit': round(item.score_academic * 100) if academic_known else None,
        'cognitive_fit': (getattr(item, 'fit', None) or {}).get('cognitive'),
        'preference_evidence': score_breakdown.get('aspiration_preferences', {}),
        'subfacet_status': subfacet_status,
        'subfacet_note': subfacet_note,
        'trait_warning': trait_warning,
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
    'DENTIST': ({'7720101', '7720601'}, 'Cùng khối ngành Sức khỏe nhưng văn bằng và phạm vi hành nghề khác Nha sĩ.'),
    'PHARMACIST': ({'7720601', '7420201', '7440112'}, 'Cùng nền tảng Hóa - Sinh ứng dụng; Công nghệ sinh học/Hóa học không cấp bằng Dược sĩ.'),
    'NURSE': ({'7720603', '7720601', '7720401'}, 'Cùng nhóm chăm sóc và hỗ trợ điều trị trong hệ thống y tế.'),
    'LAB_TECH': ({'7420201', '7720301'}, 'Cùng làm việc trong lĩnh vực xét nghiệm và sinh học y sinh.'),
    'REHABILITATION': ({'7720301', '7720401'}, 'Cùng nhóm chăm sóc phục hồi và sức khỏe cộng đồng.'),
    'NUTRITION': ({'7540101', '7720301'}, 'Cùng nghiên cứu dinh dưỡng và an toàn thực phẩm cho sức khỏe.'),
    'CYBER': ({'7480102', '7480201', '7480103'}, 'Cùng nhóm Máy tính và CNTT; có thể định hướng chuyên sâu bảo mật từ nền tảng mạng và phần mềm.'),
    'CHIP': ({'7440180', '7480106', '7510301', '7510302'}, 'Cùng lĩnh vực bán dẫn, phần cứng, điện tử và hệ thống nhúng; phù hợp làm lộ trình nền tảng vào ngành vi mạch.'),
    'AUTOMOTIVE': ({'7510205', '7520103', '7520114'}, 'Cùng nhóm cơ khí động lực và cơ điện tử ứng dụng trong công nghiệp ô tô.'),
    'ACCOUNTANT': ({'7340302', '7340201', '7340101'}, 'Cùng khối Kinh doanh - Tài chính; kiến thức nền tảng có tính liên thông cao.'),
    'AUDITOR': ({'7340301', '7340201'}, 'Cùng nhóm Kế toán - Kiểm toán và phân tích tài chính doanh nghiệp.'),
    'FINANCE': ({'7340205', '7340301', '7310101'}, 'Cùng lĩnh vực tài chính, công nghệ tài chính (Fintech) và kinh tế học.'),
    'MARKETING': ({'7340122', '7320104', '7340101'}, 'Cùng nhóm tiếp thị số, thương mại điện tử và truyền thông thương hiệu.'),
    'LOGISTICS': ({'7340120', '7840101', '7340101'}, 'Cùng lĩnh vực chuỗi cung ứng, kinh doanh quốc tế và khai thác vận tải.'),
    'ECOMMERCE': ({'7340115', '7480104', '7340101'}, 'Cùng kết hợp quản trị kinh doanh, tiếp thị số và hệ thống thông tin.'),
    'GRAPHIC_DESIGN': ({'7320104', '7210402', '7480201'}, 'Cùng nhóm thiết kế sáng tạo, truyền thông đa phương tiện và giao diện số.'),
    'ARCHITECT': ({'7580201', '7580102', '7210403'}, 'Cùng lĩnh vực quy hoạch, xây dựng công trình và thiết kế không gian.'),
    'FASHION': ({'7210403', '7210402', '7540204'}, 'Cùng lĩnh vực mỹ thuật ứng dụng và công nghệ dệt may - thời trang.'),
    'PSYCHOLOGIST': ({'7760101', '7310301', '7140114'}, 'Cùng nhóm khoa học hành vi, tham vấn học đường và hỗ trợ cộng đồng.'),
    'SOCIAL_WORK': ({'7310301', '7310401'}, 'Cùng lĩnh vực hỗ trợ xã hội, tâm lý và phát triển cộng đồng.'),
    'HUMAN_RESOURCES': ({'7340101', '7340406', '7310401'}, 'Cùng khối quản trị tổ chức, nhân sự và tâm lý lao động.'),
    'LAWYER': ({'7380108', '7380103', '7310205'}, 'Cùng khối Pháp luật và hành chính; cần lưu ý nghề Luật sư/Thẩm phán yêu cầu đào tạo nghiệp vụ sau cử nhân Luật.'),
    'DIPLOMAT': ({'7310205', '7220201', '7380107'}, 'Cùng nhóm đối ngoại, quốc tế học, ngoại ngữ và luật quốc tế.'),
    'SINGER': ({'7210201', '7140221'}, 'Cùng lĩnh vực nghệ thuật âm nhạc và sư phạm âm nhạc.'),
    'ACTOR': ({'7210222', '7210332', '7320104'}, 'Cùng lĩnh vực nghệ thuật sân khấu, điện ảnh và truyền thông.'),
    'TOUR_GUIDE': ({'7810201', '7220201', '7310630'}, 'Cùng nhóm du lịch, lữ hành, khách sạn và văn hóa - ngoại ngữ.'),
    'INFORMATION_TECH': ({'7480103', '7480104', '7480101'}, 'Cùng nhóm Máy tính và Công nghệ thông tin với khả năng chuyển đổi vị trí linh hoạt.'),
    'TEACHER': ({'7140101', '7140114', '7220201'}, 'Cùng lĩnh vực khoa học giáo dục, quản lý giáo dục và đào tạo.'),
    'BUSINESS': ({'7340120', '7340115', '7340122'}, 'Cùng khối Kinh doanh và Quản lý với nền tảng kiến thức chung.'),
    'AUTOMATION': ({'7510303', '7520201', '7520107'}, 'Cùng lĩnh vực điều khiển tự động, robot và công nghệ kỹ thuật điện - điện tử.'),
    'MECHANICAL': ({'7510201', '7520114', '7520130'}, 'Cùng nhóm cơ khí chế tạo, công nghệ kỹ thuật cơ khí và cơ điện tử.'),
    'ELECTRONICS': ({'7510301', '7510302', '7520202'}, 'Cùng nhóm kỹ thuật điện tử, viễn thông và công nghệ kỹ thuật ứng dụng.'),
    'JOURNALIST': ({'7320104', '7320105', '7320108'}, 'Cùng lĩnh vực báo chí, truyền thông đại chúng, đa phương tiện và quan hệ công chúng.'),
    'MEDIA': ({'7320101', '7340115', '7210403'}, 'Cùng nhóm truyền thông số, sáng tạo nội dung, báo chí và thiết kế.'),
    'SPORTS': ({'7140206', '7720603'}, 'Cùng lĩnh vực giáo dục thể chất, huấn luyện và phục hồi vận động.'),
    'POLICE': ({'7380101', '7480208'}, 'Lưu ý: Khối trường Công an xét tuyển theo quy chế sơ tuyển riêng; có thể tham khảo ngành Luật hoặc An toàn thông tin dân sự.'),
    'MILITARY': ({'7520207', '7480208'}, 'Lưu ý: Khối trường Quân đội xét tuyển theo quy chế sơ tuyển riêng; có thể tham khảo các ngành kỹ thuật/công nghệ dân sự tương ứng.'),
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
    elif match_status == 'MATCHED' and candidates[0]['id'].startswith('MAJOR_') and goals:
        goal_codes = {_code(item.major_code) for item in goals}
        goal_prefixes4 = {_code(item.major_code)[:4] for item in goals if len(_code(item.major_code)) >= 4}
        related = [
            item for item in all_ranked_majors
            if _code(item.major_code) not in goal_codes and _code(item.major_code)[:4] in goal_prefixes4
        ][:4]
        if related:
            relation = 'Cùng nhóm ngành đào tạo cấp III theo danh mục Bộ GD&ĐT; cần đối chiếu chương trình chi tiết.'
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
    dream_briefs = [brief(item, 'DREAM') for item in goals]
    primary = goals[0] if goals else None
    primary_brief = dream_briefs[0] if dream_briefs else None
    if primary and primary_brief and primary_brief.get('trait_warning'):
        takeaways.append(f"{primary.major_name}: {primary_brief['trait_warning']}")
    return {
        'has_aspiration': bool(dream or field), 'dream_job': dream, 'desired_field': field,
        'work_values': values, 'preferred_environment': environment, 'score_strategy': strategy,
        'preference_evidence': ((getattr(primary, 'score_breakdown', None) or {}).get('aspiration_preferences', {}) if primary else {}),
        'match_status': match_status, 'intent_candidates': candidates,
        'interest_evidence': evidence, 'alignment_status': status, 'alignment_label': label,
        'alignment_score': primary_brief['overall_match'] if primary_brief else None,
        'holland_code': holland, 'best_block_summary': '',
        'dream_majors': dream_briefs,
        'current_options': [brief(item, 'CURRENT') for item in current[:6]],
        'exploration_options': [brief(item, 'EXPLORATION') for item in exploration[:6]],
        'recommended_substitutes': [brief(item, 'SUBSTITUTE') for item in substitutes[:2]],
        'bridge_majors': [], 'agent_verdict': verdict, 'key_takeaways': takeaways,
        'is_llm_enriched': False,
    }
