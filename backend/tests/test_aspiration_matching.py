"""Behavioral guardrails for aspiration intent and current-option evidence."""
import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.recommender.aspiration_agent import analyze_career_aspiration


STRATEGIES = ['FLEXIBLE_PATHWAY', 'REALISTIC_SAFE', 'CHALLENGE_TOP']


def major(code='7720101', name='Y khoa', readiness=None, **overrides):
    data = dict(major_code=code, major_name=name, category='Sức khỏe',
                overall_score=.95, score_riasec=.95, score_academic=.95,
                score_preference=.8, feasibility_tier='TARGET', constraint_passed=True,
                best_matching_block='A00', best_block_score=29, benchmark_cutoff=25)
    if readiness is not None:
        data['readiness'] = readiness
    data.update(overrides)
    return SimpleNamespace(**data)


def ready(block='B00', score=27):
    return dict(status='READY_REFERENCE', block=block, block_score=score,
                benchmark_cutoff=26, message='Đạt mốc tham chiếu.', violations=[])


def analyze(text='Bác sĩ', majors=None, strategy='BALANCED', **kwargs):
    return asyncio.run(analyze_career_aspiration(
        {'dream_job': text, 'score_strategy': strategy},
        kwargs.pop('student_riasec', {}),
        {'block_code': 'A00', 'raw_sum': 30, 'has_academic_data': True},
        majors if majors is not None else [major()], seed_by_code={}, **kwargs))


@pytest.mark.parametrize('strategy', STRATEGIES)
@pytest.mark.parametrize('readiness', [None, {'status': 'UNKNOWN'}, {'status': 'NEEDS_IMPROVEMENT', 'violations': ['Thiếu điểm']}, {'status': 'TARGET'}])
def test_legacy_target_or_unknown_never_becomes_current(strategy, readiness):
    result = analyze(majors=[major(readiness=readiness)], strategy=strategy)
    assert result['match_status'] == 'MATCHED'
    assert result['dream_majors'][0]['major_name'] == 'Y khoa'
    for key in ['current_options', 'recommended_substitutes', 'bridge_majors']:
        assert result[key] == []
    assert result['alignment_status'] == 'NO_CURRENT_OPTIONS'


@pytest.mark.parametrize('strategy', STRATEGIES)
def test_physician_never_matches_pharmacy_or_nursing_as_same_profession(strategy):
    result = analyze(majors=[major('7720201', 'Dược học', ready()), major('7720301', 'Điều dưỡng', ready()), major()], strategy=strategy)
    assert [item['major_code'] for item in result['dream_majors']] == ['7720101']
    assert all(item['major_code'] != '7720201' for item in result['current_options'])
    if strategy == 'CHALLENGE_TOP':
        assert result['recommended_substitutes'] == []
    else:
        assert result['recommended_substitutes'][0]['major_code'] == '7720301'
        assert 'không cấp bằng bác sĩ' in result['recommended_substitutes'][0]['relation_reason']


@pytest.mark.parametrize('strategy', STRATEGIES)
def test_multiple_professions_require_choice_before_any_recommendation(strategy):
    pool = [major(readiness=ready()), major('7720201', 'Dược học', ready())]
    result = analyze('Bác sĩ và Dược sĩ', pool, strategy)
    assert result['match_status'] == 'AMBIGUOUS'
    assert {item['id'] for item in result['intent_candidates']} == {'PHYSICIAN', 'PHARMACIST'}
    assert result['dream_majors'] == result['current_options'] == []
    choice = next(item for item in result['intent_candidates'] if item['id'] == 'PHARMACIST')
    resolved = analyze(choice['canonicalDreamJob'], pool, strategy)
    assert resolved['match_status'] == 'MATCHED'
    assert [item['major_code'] for item in resolved['dream_majors']] == ['7720201']


@pytest.mark.parametrize('text,expected', [('', 'EMPTY'), ('nghề xyz chưa biết', 'UNRECOGNIZED'), ('Bác sĩ và Dược sĩ', 'AMBIGUOUS')])
@pytest.mark.parametrize('strategy', STRATEGIES)
def test_nonmatched_states_cannot_promote_unverified_catalog(text, expected, strategy):
    result = analyze(text, [major(), major('7340301', 'Kế toán')], strategy)
    assert result['match_status'] == expected
    assert result['current_options'] == result['recommended_substitutes'] == result['bridge_majors'] == []


def test_verified_reference_uses_its_own_admission_block_not_global_best():
    result = analyze(majors=[major(readiness=ready('B00', 27))])
    current = result['current_options'][0]
    assert current['best_matching_block'] == 'B00'
    assert current['best_block_score'] == 27
    assert current['benchmark_cutoff'] == 26
    assert 'B00' in ' '.join(result['key_takeaways'])
    assert 'A00' not in ' '.join(result['key_takeaways'])


@pytest.mark.parametrize('evidence', [None, {'status': 'PARTIAL', 'groups': []}, {'status': 'LEGACY_UNVERIFIED', 'groups': []}, {'status': 'MISSING', 'groups': []}])
def test_missing_or_partial_interest_never_fabricates_fit(evidence):
    result = analyze(majors=[major(readiness=ready())], student_riasec={'I': .9}, interest_evidence=evidence)
    assert result['alignment_score'] is None
    assert result['holland_code'] == ''
    assert result['current_options'][0]['riasec_fit'] is None
    assert result['current_options'][0]['overall_match'] is None
    assert result['interest_evidence']['status'] != 'COMPLETE'


def test_missing_academic_evidence_suppresses_stale_metrics():
    result = analyze(interest_evidence={'status': 'COMPLETE', 'groups': []}, student_riasec={'I': .9})
    goal = result['dream_majors'][0]
    assert goal['academic_fit'] is None
    assert goal['overall_match'] is None
    assert goal['benchmark_cutoff'] is None
    assert goal['best_block_score'] is None
    assert goal['constraint_passed'] is False


def test_unrelated_ready_major_is_not_a_bridge():
    result = analyze(majors=[major(), major('7340301', 'Kế toán', ready())])
    assert result['current_options'] == result['bridge_majors'] == []
    assert all(item['major_code'] != '7340301' for item in result['exploration_options'])


def test_empty_catalog_preserves_recognized_goal_text():
    result = analyze('Bác sĩ', [])
    assert result['dream_job'] == 'Bác sĩ'
    assert result['match_status'] == 'MATCHED'
    assert result['dream_majors'] == result['current_options'] == []


def test_matching_is_independent_of_rank_and_legacy_strategy():
    pool = [major('7340301', 'Kế toán', ready()), major('7720101', 'Y khoa', overall_score=.01)]
    assert analyze(majors=pool)['dream_majors'][0]['major_code'] == '7720101'


def test_sanitized_input_is_preserved_and_no_llm_is_called():
    with patch('httpx.AsyncClient', side_effect=AssertionError('No LLM call permitted')):
        result = analyze('Tôi muốn làm Bác sĩ, email minh@example.com', enable_llm=True)
    assert 'minh@example.com' not in result['dream_job']
    assert 'Bác sĩ' in result['dream_job']
    assert result['is_llm_enriched'] is False
    assert result['match_status'] == 'MATCHED'


def test_field_cannot_override_an_explicit_profession():
    result = asyncio.run(analyze_career_aspiration(
        {'dream_job': 'Dược sĩ', 'desired_field': 'Bác sĩ'}, {}, None,
        [major(), major('7720201', 'Dược học')], seed_by_code={}))
    assert [item['major_code'] for item in result['dream_majors']] == ['7720201']


def test_short_keywords_have_word_boundaries():
    assert analyze('Mai muốn làm nghề chưa rõ')['match_status'] == 'UNRECOGNIZED'


def test_longer_profession_phrase_does_not_inherit_incidental_profession():
    result = analyze('Thương mại điện tử', [major('7340122', 'Thương mại điện tử'), major('7520207', 'Điện tử viễn thông')])
    assert result['match_status'] == 'MATCHED'
    assert [item['major_code'] for item in result['dream_majors']] == ['7340122']


def test_general_healthcare_candidates_can_each_be_selected():
    result = analyze('Chăm sóc sức khỏe')
    assert result['match_status'] == 'AMBIGUOUS'
    assert len(result['intent_candidates']) == 7
    for choice in result['intent_candidates']:
        selected = analyze(choice['canonicalDreamJob'])
        assert selected['match_status'] == 'MATCHED'
        assert selected['intent_candidates'][0]['id'] == choice['id']


def test_blocked_goals_are_not_exploration_options():
    result = analyze(majors=[major(readiness={'status': 'NEEDS_IMPROVEMENT'})])
    assert len(result['dream_majors']) == 1
    assert result['exploration_options'] == []


def test_partial_interest_order_uses_readiness_margin_not_composite_score():
    low_margin = major('7480103', 'Phần mềm', ready(score=26), overall_score=.99)
    high_margin = major('7480201', 'CNTT', ready(score=28), overall_score=.01)
    result = analyze('Lập trình', [low_margin, high_margin], interest_evidence={'status': 'PARTIAL'})
    assert [item['major_code'] for item in result['current_options']] == ['7480201', '7480103']


def test_strategies_change_scope_without_changing_intent():
    pool = [major(), major('7720301', 'Điều dưỡng')]
    results = {strategy: analyze(majors=pool, strategy=strategy) for strategy in STRATEGIES}
    assert all(result['dream_majors'][0]['major_code'] == '7720101' for result in results.values())
    assert len(results['FLEXIBLE_PATHWAY']['exploration_options']) == 2
    assert len(results['REALISTIC_SAFE']['exploration_options']) == 1
    assert len(results['CHALLENGE_TOP']['exploration_options']) == 1


def test_pilot_does_not_claim_air_traffic_management_is_pilot_training():
    result = analyze('Phi công', [major('7840102', 'Quản lý hoạt động bay')])
    assert result['match_status'] == 'MATCHED'
    assert result['dream_majors'] == []
    assert 'không thay thế' in result['exploration_options'][0]['relation_reason']


def test_seed_careers_are_loaded_for_standalone_callers():
    with patch('app.services.taxonomy.service.load_seed_majors', return_value=[{'major_code': '1234567', 'careers': ['Nghề đặc biệt']}]) as load:
        result = asyncio.run(analyze_career_aspiration({'dream_job': 'Nghề đặc biệt'}, {}, None, [major('1234567', 'Ngành đặc biệt')]))
    load.assert_called_once()
    assert result['match_status'] == 'MATCHED'


def test_default_strategy_is_flexible_pathway():
    result = asyncio.run(analyze_career_aspiration({}, {}, None, [], seed_by_code={}))
    assert result['score_strategy'] == 'FLEXIBLE_PATHWAY'


def test_every_atomic_choice_round_trips_to_same_intent():
    from app.services.recommender.aspiration_agent import ATOMIC_CAREERS
    for intent_id, label, _, _ in ATOMIC_CAREERS:
        result = analyze(label)
        assert result['match_status'] == 'MATCHED', label
        assert result['intent_candidates'][0]['id'] == intent_id


def test_subfacet_veto_surfaces_trait_warning_on_dream_major():
    vetoed = major(
        '7210205',
        'Thanh nhạc',
        score_riasec=0.22,
        overall_score=0.31,
        score_breakdown={
            'subfacet_gate': {
                'status': 'STRONG_VETO',
                'note': 'Cổng sở thích hẹp (A4 = 1/5): Bạn chọn Rất không thích Âm nhạc.',
            }
        },
    )
    complete_interest = {'status': 'COMPLETE', 'groups': [{'code': 'A', 'percent': 75, 'answered': 5, 'total': 5}]}
    result = analyze('Ca sĩ', [vetoed], interest_evidence=complete_interest)
    assert result['match_status'] == 'MATCHED'
    dream = result['dream_majors'][0]
    assert dream['subfacet_status'] == 'STRONG_VETO'
    assert dream['riasec_fit'] == 22
    assert 'A4 = 1/5' in (dream['trait_warning'] or '')
    assert any('A4 = 1/5' in t for t in result['key_takeaways'])


@pytest.mark.parametrize('job,goal_code,goal_name,rel_code,rel_name', [
    ('Kỹ sư thiết kế vi mạch', '7520202', 'Thiết kế vi mạch', '7510301', 'Công nghệ kỹ thuật điện, điện tử'),
    ('Luật sư', '7380101', 'Luật', '7380108', 'Luật quốc tế'),
    ('Dược sĩ', '7720201', 'Dược học', '7720601', 'Kỹ thuật xét nghiệm y học'),
])
def test_expanded_related_paths_surface_ready_related_majors(job, goal_code, goal_name, rel_code, rel_name):
    pool = [
        major(goal_code, goal_name, readiness={'status': 'NEEDS_IMPROVEMENT', 'violations': ['Thiếu điểm']}),
        major(rel_code, rel_name, ready('A00', 24)),
    ]
    result = analyze(job, pool, strategy='FLEXIBLE_PATHWAY')
    assert result['match_status'] == 'MATCHED'
    assert [item['major_code'] for item in result['dream_majors']] == [goal_code]
    assert any(item['major_code'] == rel_code for item in result['current_options'])
    assert any(item['major_code'] == rel_code for item in result['recommended_substitutes'])

