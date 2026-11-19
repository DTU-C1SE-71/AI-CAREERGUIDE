"""Behavioral tests: no current option without complete, comparable evidence."""
from decimal import Decimal
from uuid import uuid4

import pytest

from app.schemas.recommender import EvaluateProfileRequest, MajorRecommendationItem
from app.services.recommender.readiness import (
    build_interest_evidence, evaluate_current_readiness, validate_readiness_grades,
)


def reference(**changes):
    # Deliberately synthetic verified policy: never persisted in the real catalog.
    value = {"id": "test-policy", "kind": "ACADEMIC_POLICY", "verified": True,
             "source": "test-fixture", "expectedScoreKind": "TRANSCRIPT",
             "calculationMethod": "SUM_THREE_SUBJECTS", "admittedBlocks": ["A00", "D01"],
             "cutoff": 24, "minimum": 20}
    return {**value, **changes}


def evaluate(grades=None, **changes):
    args = dict(raw_grades=grades if grades is not None else {"Toán": 8, "Vật lý": 8, "Hóa học": 8},
                admitted_blocks=["A00"], block_source="DATABASE", major_code="test",
                major_name="Ngành kiểm thử", reference=reference())
    args.update(changes)
    return evaluate_current_readiness(**args)


def test_cutoff_requires_full_precision_and_does_not_use_minimum_alone():
    result = evaluate({"Toán": 7.999, "Vật lý": 7.999, "Hóa học": 7.999})
    assert result["status"] == "NEEDS_IMPROVEMENT"
    assert result["block_score"] == 23.997
    assert result["gaps"][0]["amount"] == .003
    assert evaluate()["status"] == "READY_REFERENCE"
    assert evaluate({"Toán": 7, "Vật lý": 7, "Hóa học": 7})["status"] == "NEEDS_IMPROVEMENT"


@pytest.mark.parametrize("invalid", [True, False, 99, -1, float("nan"), float("inf"), "9", None, [], {}])
def test_invalid_grades_never_become_valid_through_coercion_or_clamping(invalid):
    result = evaluate({"Toán": invalid, "Vật lý": 10, "Hóa học": 10})
    assert result["status"] == "UNKNOWN"
    assert result["block_score"] is None
    assert "Toán" in result["grade_errors"]


def test_alias_conflicts_are_order_independent_and_precision_is_preserved():
    for values in ({"Vật lý": 8, "Lý": 9}, {"Lý": 9, "Vật lý": 8}):
        validated = validate_readiness_grades(values)
        assert validated["scores"] == {}
        assert validated["errors"]["Vật lý"] == "CONFLICTING_ALIASES"
    validated = validate_readiness_grades({"Toán": 7.999, "Toán học": 7.999})
    assert validated["scores"]["Toán"] == Decimal("7.999")


@pytest.mark.parametrize("ref", [None, {}, reference(verified=False), reference(source=""),
                                   reference(calculationMethod=None), reference(minimum=None),
                                   reference(kind="ADMISSION_REFERENCE")])
def test_unverified_or_incomplete_reference_is_unknown(ref):
    result = evaluate(reference=ref)
    assert result["status"] == "UNKNOWN"
    assert result["block_score"] is None
    assert result["gaps"] == []


@pytest.mark.parametrize("ref,context", [
    (reference(expectedScoreKind="EXAM"), {"kind": "TRANSCRIPT", "scale": 10}),
    (reference(examId="exam-a"), {"kind": "TRANSCRIPT", "scale": 10, "examId": "exam-b"}),
    (reference(calculationMethod="WEIGHTED_SUM"), {"kind": "TRANSCRIPT", "scale": 10}),
    (reference(), {"kind": "TRANSCRIPT", "scale": 100}),
])
def test_reference_basis_must_match(ref, context):
    assert evaluate(reference=ref, score_context=context)["reason"] == "REFERENCE_NOT_COMPARABLE"


@pytest.mark.parametrize("source", ["ASSUMED", "MISSING", None])
def test_assumed_blocks_cannot_establish_readiness(source):
    assert evaluate(block_source=source)["status"] == "UNKNOWN"


def test_only_admitted_complete_blocks_count_and_missing_is_not_zero():
    grades = {"Toán": 10, "Ngữ văn": 10, "Tiếng Anh": 10}
    result = evaluate(grades)
    assert result["status"] == "UNKNOWN"
    assert result["block_score"] is None
    assert result["missing_subjects"] == ["Hóa học", "Vật lý"]
    assert evaluate({}, admitted_blocks=[])["status"] == "UNKNOWN"
    assert evaluate({"Toán": 0, "Vật lý": 10, "Hóa học": 10})["status"] == "NEEDS_IMPROVEMENT"


def test_ready_block_wins_over_higher_total_with_subject_violation():
    grades = {"Toán": 10, "Vật lý": 3.499, "Hóa học": 10, "Ngữ văn": 6.5, "Tiếng Anh": 6.5}
    result = evaluate(grades, admitted_blocks=["A00", "D01"], reference=reference(cutoff=23))
    assert result["status"] == "READY_REFERENCE"
    assert result["block"] == "D01"
    assert result["block_score"] == 23
    assert result["evaluated_blocks"][0]["violations"]


def test_unknown_other_block_keeps_improvement_inconclusive_but_preserves_known_gap():
    result = evaluate({"Toán": 7, "Vật lý": 7, "Hóa học": 7}, admitted_blocks=["A00", "D01"])
    assert result["status"] == "UNKNOWN"
    assert result["block"] == "A00"
    assert result["gaps"][0]["amount"] == 3
    assert evaluate()["status"] == "READY_REFERENCE"
    assert evaluate({})["status"] == "UNKNOWN"


def test_all_blocks_checked_and_ready_selection_is_deterministic():
    grades = {"Toán": 8, "Vật lý": 7.5, "Hóa học": 7.5, "Ngữ văn": 8, "Tiếng Anh": 9}
    result = evaluate(grades, admitted_blocks=["D01", "A00"])
    assert result["block"] == "D01"
    assert result["block_score"] == 25
    assert result["status"] == "READY_REFERENCE"


def test_interest_six_groups_missing_partial_complete_and_legacy():
    missing = build_interest_evidence({})
    assert missing["status"] == "MISSING"
    assert [g["code"] for g in missing["groups"]] == list("RIASEC")
    assert all(g["percent"] is None and g["answered"] == 0 for g in missing["groups"])
    partial = build_interest_evidence({"R1": 4, "I1": True, "A1": float("nan"), "S1": 6})
    assert partial["status"] == "PARTIAL"
    assert partial["groups"][0]["percent"] == 75
    assert partial["groups"][1]["percent"] is None
    complete = build_interest_evidence({f"1-{i}": 3 for i in range(30)})
    assert complete["status"] == "NON_DISCRIMINATING"
    assert all(g["answered"] == 5 and g["percent"] == 50 for g in complete["groups"])
    legacy = build_interest_evidence(None, {"R": .8})
    assert legacy["status"] == "LEGACY_UNVERIFIED"
    assert all(g["answered"] is None for g in legacy["groups"])
    assert legacy["groups"][1]["percent"] is None


def test_current_and_legacy_answer_keys_are_not_double_counted():
    evidence = build_interest_evidence({"R1": 5, "1-0": 5})
    assert evidence["status"] == "PARTIAL"
    assert evidence["groups"][0]["answered"] == 1


def test_schema_fails_closed_and_preserves_boolean_for_validation():
    item = MajorRecommendationItem(rank=1, major_id=uuid4(), major_code="test", major_name="Test",
                                   overall_score=.9, score_riasec=.9, score_academic=.9,
                                   score_preference=.9, score_breakdown={}, explanation="Test")
    assert item.readiness["status"] == "UNKNOWN"
    assert item.feasibility_tier == "UNKNOWN"
    assert item.constraint_passed is False
    request = EvaluateProfileRequest(grades_by_subject={"Toán": True})
    assert request.grades_by_subject["Toán"] is True


def test_subject_gap_exposes_exact_actionable_values():
    result = evaluate({"Toán": 10, "Vật lý": 3.499, "Hóa học": 10}, reference=reference(cutoff=23))
    assert result["status"] == "NEEDS_IMPROVEMENT"
    assert result["gaps"] == [{"kind": "SUBJECT_SCORE", "subject": "Vật lý",
                               "actual": 3.499, "required": 3.5, "delta": .001}]


@pytest.mark.parametrize("invalid", [2.5, None])
def test_invalid_canonical_answer_does_not_revive_valid_legacy_answer(invalid):
    evidence = build_interest_evidence({"R1": invalid, "1-0": 5})
    assert evidence["status"] == "MISSING"
    assert evidence["groups"][0]["answered"] == 0
    assert evidence["groups"][0]["percent"] is None
