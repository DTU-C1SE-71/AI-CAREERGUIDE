"""Conservative aspiration evidence, independent of heuristic ranking scores."""
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .engine import (
    FAILING_SUBJECT_THRESHOLD, STANDARD_SUBJECT_BLOCKS,
    get_major_subject_requirements, normalize_subject_name,
)

RIASEC_ORDER = "RIASEC"
POLICY_VERSION = "aspiration-v1"


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        return None
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def validate_readiness_grades(raw):
    """Keep original precision and invalidate every conflicting subject alias."""
    scores, errors = {}, {}
    if raw is None:
        return {"scores": scores, "errors": errors}
    if not isinstance(raw, Mapping):
        return {"scores": {}, "errors": {"__input__": "INVALID_GRADES"}}
    for key, value in raw.items():
        subject = normalize_subject_name(key)
        number = _number(value)
        if not subject or number is None or not Decimal(0) <= number <= Decimal(10):
            errors[subject or "__input__"] = "INVALID_GRADE"
            scores.pop(subject, None)
        elif subject in errors:
            continue
        elif subject in scores and scores[subject] != number:
            errors[subject] = "CONFLICTING_ALIASES"
            scores.pop(subject)
        else:
            scores[subject] = number
    return {"scores": scores, "errors": errors}


def build_interest_evidence(answers, legacy_vector=None):
    """Count valid raw answers; a stored vector cannot establish completion."""
    answers = answers if isinstance(answers, Mapping) else {}
    groups = []
    for group_index, code in enumerate(RIASEC_ORDER):
        values = []
        for index in range(5):
            key = f"{code}{index + 1}"
            value = answers.get(key, answers.get(f"1-{group_index * 5 + index}"))
            number = _number(value)
            if number is not None and 1 <= number <= 5 and number == number.to_integral_value():
                values.append(number)
        groups.append({"code": code, "percent": float((sum(values) / len(values) - 1) * 25) if values else None,
                       "answered": len(values), "total": 5})
    count = sum(group["answered"] for group in groups)
    status = "COMPLETE" if count == 30 else "PARTIAL" if count else "MISSING"
    if count == 30 and len({group["percent"] for group in groups}) == 1:
        status = "NON_DISCRIMINATING"
    if not count and isinstance(legacy_vector, Mapping) and legacy_vector:
        status = "LEGACY_UNVERIFIED"
        for group in groups:
            value = _number(legacy_vector.get(group["code"]))
            group["percent"] = float(value * 100) if value is not None and 0 <= value <= 1 else None
            group["answered"] = None
    return {"status": status, "groups": groups}


def unknown_readiness():
    return {"status": "UNKNOWN", "reason": "EVIDENCE_MISSING",
            "message": "Chưa đủ bằng chứng để đối chiếu học lực hiện tại.",
            "block": None, "block_score": None, "benchmark_cutoff": None,
            "min_recommended": None, "missing_subjects": [], "violations": [], "gaps": [],
            "reference_kind": None, "reference_id": None, "reference_method": None,
            "score_kind": None, "block_source": "MISSING", "policy_version": POLICY_VERSION}


def evaluate_current_readiness(*, raw_grades, admitted_blocks, block_source,
                               major_code, major_name, category="", score_context=None,
                               reference=None):
    """Compare only server-owned verified references with declared, complete blocks.

    Supported reference calculationMethod is SUM_THREE_SUBJECTS. References use
    expectedScoreKind/admittedBlocks/cutoff/minimum and verified/source/id/kind.
    ADMISSION_REFERENCE additionally requires institution/program/year.
    """
    result = unknown_readiness()
    context = score_context if isinstance(score_context, Mapping) else {"kind": "TRANSCRIPT", "scale": 10}
    result.update(score_kind=context.get("kind"), block_source=block_source)
    validated = validate_readiness_grades(raw_grades)
    result["grade_errors"] = validated["errors"]
    scores = validated["scores"]

    def unknown(reason, message):
        result.update(reason=reason, message=message)
        return result

    if block_source not in {"DATABASE", "SEED_DECLARED"} or not admitted_blocks:
        return unknown("BLOCK_PROVENANCE_MISSING", "Chưa xác minh tổ hợp được ngành chấp nhận.")
    if not isinstance(reference, Mapping):
        return unknown("REFERENCE_BASIS_MISSING", "Chưa có mức tham chiếu phù hợp loại điểm đã nhập.")
    result.update(reference_kind=reference.get("kind"), reference_id=reference.get("id"),
                  reference_method=reference.get("calculationMethod"))
    required = ("id", "source", "kind", "expectedScoreKind", "calculationMethod", "admittedBlocks")
    if (reference.get("verified") is not True or any(not reference.get(key) for key in required)
            or reference.get("kind") not in {"ACADEMIC_POLICY", "ADMISSION_REFERENCE"}):
        return unknown("REFERENCE_BASIS_MISSING", "Mức tham chiếu chưa đủ nguồn và phương thức xác minh.")
    if reference["kind"] == "ADMISSION_REFERENCE" and any(not reference.get(key) for key in ("institution", "program", "year")):
        return unknown("REFERENCE_BASIS_MISSING", "Thiếu trường, chương trình hoặc năm của mốc tuyển sinh.")
    if (context.get("kind") not in {"TRANSCRIPT", "EXAM"}
            or context.get("kind") != reference["expectedScoreKind"]
            or _number(context.get("scale")) != Decimal(10)
            or reference["calculationMethod"] != "SUM_THREE_SUBJECTS"
            or (reference.get("examId") and context.get("examId") != reference["examId"])):
        return unknown("REFERENCE_NOT_COMPARABLE", "Loại điểm hoặc phương thức chưa tương thích với mức tham chiếu.")
    cutoff, minimum = _number(reference.get("cutoff")), _number(reference.get("minimum"))
    if cutoff is None or minimum is None or not (0 <= cutoff <= 30 and 0 <= minimum <= 30):
        return unknown("REFERENCE_BASIS_MISSING", "Thiếu mức điểm tham chiếu đã xác minh.")
    result.update(benchmark_cutoff=float(cutoff), min_recommended=float(minimum))
    threshold = max(cutoff, minimum)
    floor, required_subjects = get_major_subject_requirements(major_code, major_name, category)
    evaluations = []
    reference_blocks = reference["admittedBlocks"]
    if not isinstance(reference_blocks, (list, tuple, set)):
        return unknown("REFERENCE_BASIS_MISSING", "Thiếu danh sách tổ hợp trong mức tham chiếu.")
    for block in sorted(set(admitted_blocks)):
        entry = {"block": block, "status": "UNKNOWN", "reason": "BLOCK_NOT_COMPARABLE",
                 "block_score": None, "missing_subjects": [], "violations": [], "gaps": []}
        definition = STANDARD_SUBJECT_BLOCKS.get(block)
        if block not in reference_blocks or not definition or len(definition["subjects"]) != 3:
            evaluations.append(entry)
            continue
        subjects = definition["subjects"]
        missing = [subject for subject in subjects if subject not in scores]
        entry["missing_subjects"] = missing
        if missing or "__input__" in validated["errors"]:
            entry["reason"] = "INVALID_GRADES" if validated["errors"] else "MISSING_SUBJECTS"
            evaluations.append(entry)
            continue
        total = sum((scores[subject] for subject in subjects), Decimal(0))
        for subject in subjects:
            score = scores[subject]
            required = Decimal(str(max(floor, required_subjects.get(subject, 0))))
            if score < required:
                entry["gaps"].append({"kind": "SUBJECT_SCORE", "subject": subject,
                                      "actual": float(score), "required": float(required),
                                      "delta": float(required - score)})
            if score <= Decimal(str(FAILING_SUBJECT_THRESHOLD)):
                entry["violations"].append(f"Điểm môn {subject} không vượt ngưỡng điểm liệt.")
            elif score < required:
                entry["violations"].append(f"Môn {subject} chưa đạt ngưỡng {required} điểm.")
        deficit = max(Decimal(0), threshold - total)
        if deficit:
            entry["gaps"].append({"kind": "TOTAL_SCORE", "amount": float(deficit)})
        ready = not entry["violations"] and total >= threshold
        entry.update(block_score=float(total), status="READY_REFERENCE" if ready else "NEEDS_IMPROVEMENT",
                     reason="REFERENCE_MET" if ready else "BELOW_REFERENCE_OR_CONSTRAINT")
        evaluations.append(entry)
    ready = [entry for entry in evaluations if entry["status"] == "READY_REFERENCE"]
    complete = [entry for entry in evaluations if entry["block_score"] is not None]
    selected = sorted(ready or complete, key=lambda entry: (-entry["block_score"], entry["block"]))
    if selected:
        result.update(selected[0])
    if not ready and any(entry["status"] == "UNKNOWN" for entry in evaluations):
        result.update(status="UNKNOWN", reason="INCOMPLETE_BLOCK_EVIDENCE")
    if not selected:
        result["missing_subjects"] = sorted({subject for entry in evaluations for subject in entry["missing_subjects"]})
        result["reason"] = "INCOMPLETE_BLOCK_EVIDENCE"
    result["evaluated_blocks"] = evaluations
    result["message"] = {
        "READY_REFERENCE": "Đạt mốc tham chiếu học thuật; đây không phải cam kết trúng tuyển.",
        "NEEDS_IMPROVEMENT": "Cần cải thiện điểm hoặc điều kiện môn của các tổ hợp đã đối chiếu.",
        "UNKNOWN": "Cần bổ sung bằng chứng cho tổ hợp hoặc mức tham chiếu phù hợp.",
    }[result["status"]]
    return result
