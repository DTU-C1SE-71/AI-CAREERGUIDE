from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .engine import normalize_student_cognitive_traits

COGNITIVE_DIMENSIONS = {
    'abstract_thinking': {'low', 'medium', 'high'},
    'analytical_reasoning': {'low', 'medium', 'high'},
    'spatial_perception': {'low', 'medium', 'high'},
    'linguistic_ability': {'low', 'medium', 'high'},
    'learning_environment': {'structured', 'exploratory', 'collaborative', 'independent'},
    'teamwork_intensity': {'independent', 'balanced', 'highly_collaborative'},
}
WORK_VALUES = {'HIGH_INCOME_GROWTH', 'TECH_INNOVATION', 'SOCIAL_IMPACT', 'STABILITY_EXPERTISE'}
STRATEGIES = {'REALISTIC_SAFE': (0.8, 1.4, 0.9), 'CHALLENGE_TOP': (1.2, 0.9, 1.0), 'FLEXIBLE_PATHWAY': (1.0, 1.0, 1.0)}


@lru_cache(maxsize=1)
def _cognitive_questions():
    data = json.loads((Path(__file__).parents[2] / 'db/seeds/assessment_questions_v1_8.json').read_text(encoding='utf-8'))
    # Load exact answer identities rather than accepting substring matches.
    return data['cognitive_questions']


LEGACY_V1_COG_SPECS = (
    ("COG_1", "learning_style", {"LEARN_VISUAL_SPATIAL", "LEARN_THEORETICAL_ANALYTICAL", "LEARN_HANDS_ON_PRACTICAL", "LEARN_INTERACTIVE_CASE"}),
    ("COG_2", "work_environment", {"ENV_LAB_DIGITAL_QUIET", "ENV_DYNAMIC_CORPORATE", "ENV_FIELD_INDUSTRIAL", "ENV_INSTITUTIONAL_SERVICE"}),
    ("COG_3", "problem_solving", {"SOLVE_QUANTITATIVE_LOGIC", "SOLVE_CREATIVE_DIVERGENT", "SOLVE_HUMAN_EMPATHY", "SOLVE_PROCEDURAL_STRATEGIC"}),
    ("COG_4", "interaction_target", {"TARGET_SYSTEMS_MACHINES", "TARGET_DATA_FINANCE_LAW", "TARGET_PEOPLE_COMMUNITY", "TARGET_NATURE_BIO_ART"}),
    ("COG_5", "gardner_intelligence", {"GARDNER_LOGICAL_MATH", "GARDNER_LINGUISTIC_INTERPERSONAL", "GARDNER_SPATIAL_MUSICAL", "GARDNER_NATURALIST_KINESTHETIC"}),
    ("COG_6", "pressure_tolerance", {"PRESSURE_HIGH_STAKES_VITAL", "PRESSURE_MARKET_DEADLINE", "PRESSURE_DEEP_RND_COMPLEXITY", "PRESSURE_STABLE_SUSTAINABLE"}),
    ("COG_7", "output_preference", {"OUTPUT_TANGIBLE_TECH_SYSTEM", "OUTPUT_ECONOMIC_LEGAL_VALUE", "OUTPUT_HUMAN_WELLBEING", "OUTPUT_CREATIVE_SCIENTIFIC_WORK"}),
    ("COG_8", "team_role", {"ROLE_TECHNICAL_SPECIALIST", "ROLE_STRATEGIC_LEADER", "ROLE_CREATIVE_COMMUNICATOR", "ROLE_QUALITY_CONTROLLER"}),
)


def cognitive_evidence(raw: Any) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    questions = _cognitive_questions()
    v2_exclusive_keys = {q['code'] for q in questions} | {
        q['dimension_key']
        for q in questions
        if q['dimension_key'] not in ('learning_environment', 'teamwork_intensity')
    }
    if any(key in raw for key in v2_exclusive_keys):
        valid = {}
        for question in questions:
            code, dim = question['code'], question['dimension_key']
            answer = raw[code] if code in raw else raw.get(dim)
            if not isinstance(answer, str):
                continue
            answer = answer.strip().upper()
            for option in question['options']:
                if answer in {option['option_key'], option['trait_code']}:
                    valid[code] = option['option_key']
                    break
        count = len(valid)
        total = len(questions)
        traits = normalize_student_cognitive_traits(valid) if count == total else {}
        return {'status': 'COMPLETE' if count == total else 'PARTIAL' if count else 'MISSING',
                'answered': count, 'total': total, 'basis': 'SELF_REPORTED_PREFERENCES',
                'traits': {k: traits[k] for k in COGNITIVE_DIMENSIONS if k in traits}}

    legacy_keys = {code for code, _, _ in LEGACY_V1_COG_SPECS} | {dim for _, dim, _ in LEGACY_V1_COG_SPECS}
    if any(key in raw for key in legacy_keys):
        valid = {}
        for code, dim, trait_codes in LEGACY_V1_COG_SPECS:
            answer = raw[code] if code in raw else raw.get(dim)
            if not isinstance(answer, str):
                continue
            answer = answer.strip().upper()
            if answer in {"A", "B", "C", "D"} or answer in trait_codes:
                valid[code] = answer
        count = len(valid)
        traits = normalize_student_cognitive_traits(valid) if count == 8 else {}
        return {'status': 'COMPLETE' if count == 8 else 'PARTIAL' if count else 'MISSING',
                'answered': count, 'total': 8, 'basis': 'SELF_REPORTED_PREFERENCES',
                'traits': {k: traits[k] for k in COGNITIVE_DIMENSIONS if k in traits}}

    valid = {k: v for k, v in raw.items() if k in COGNITIVE_DIMENSIONS and isinstance(v, str) and v in COGNITIVE_DIMENSIONS[k]}
    count = len(valid)
    return {'status': 'COMPLETE' if count == 6 else 'PARTIAL' if count else 'MISSING',
            'answered': count, 'total': 6, 'basis': 'SELF_REPORTED_PREFERENCES', 'traits': valid if count == 6 else {}}


def score_observed_pillars(scores: dict, available: dict, base: dict, strategy: str) -> tuple[float, dict]:
    multipliers = STRATEGIES.get(strategy, STRATEGIES['FLEXIBLE_PATHWAY'])
    keys = ('w_riasec', 'w_academic', 'w_preference')
    raw = {key: max(0.0, float(base[key])) * factor if available[key] else 0.0
           for key, factor in zip(keys, multipliers)}
    total = sum(raw.values())
    weights = {key: raw[key] / total if total else 0.0 for key in keys}
    return round(sum(scores[k] * weights[k] for k in keys), 4), weights


def aspiration_preference_evidence(aspiration: dict, attributes: dict) -> dict:
    """Only compare explicitly declared catalog attributes; never infer salary/stability."""
    values = aspiration.get('work_values', aspiration.get('workValues', []))
    values = list(dict.fromkeys(v for v in values if isinstance(v, str) and v in WORK_VALUES))[:2] if isinstance(values, list) else []
    declared = attributes.get('work_values')
    declared = {v for v in declared if isinstance(v, str) and v in WORK_VALUES} if isinstance(declared, list) else set()
    env = aspiration.get('preferred_environment', aspiration.get('preferredEnvironment', ''))
    env = env if isinstance(env, str) else ''
    major_env = attributes.get('learning_environment')
    env_supported = env in COGNITIVE_DIMENSIONS['learning_environment'] and major_env in COGNITIVE_DIMENSIONS['learning_environment']
    value_score = len(set(values) & declared) / len(values) if values and declared else None
    env_score = float(env == major_env) if env_supported else None
    parts = [v for v in (value_score, env_score) if v is not None]
    return {'work_values': {'requested': values, 'status': 'USED' if value_score is not None else 'UNSUPPORTED_CATALOG' if values else 'NOT_REQUESTED', 'score': value_score},
            'environment': {'requested': env, 'status': 'USED' if env_score is not None else 'UNSUPPORTED_CATALOG' if env else 'NOT_REQUESTED', 'score': env_score},
            'score': sum(parts) / len(parts) if parts else None,
            'meaning': 'Đối chiếu thuộc tính được khai báo trong danh mục; không cam kết thu nhập hay việc làm.'}
