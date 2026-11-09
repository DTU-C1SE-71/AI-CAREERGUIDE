from typing import Dict, List, Set, Tuple, Any, Optional

# Standard domain-level subject mastery thresholds
SUBJECT_MASTERY_THRESHOLDS = {
    "Toán": {
        "SKILL_PRE_CALCULUS": 8.0,
        "SKILL_PRE_LOGIC_DISCRETE": 7.5,
        "SKILL_PRE_STAT_BASIC": 7.5
    },
    "Vật lí": {
        "SKILL_PRE_PHYSICS_MECH": 8.0
    },
    "Hóa học": {
        "SKILL_PRE_CHEM_GEN": 8.0
    },
    "Sinh học": {
        "SKILL_PRE_BIO_CELL": 8.0
    },
    "Tiếng Anh": {
        "SKILL_PRE_ENG_ACADEMIC": 7.5
    },
    "Ngữ văn": {
        "SKILL_PRE_VIET_ESSAY": 7.5
    }
}


def infer_mastered_skills_from_grades(
    grades_by_subject: Dict[str, float]
) -> Set[str]:
    """
    Infers mastered prerequisite competencies from student high school academic grades.
    Grade scale: 0.0 to 10.0.
    """
    mastered: Set[str] = set()
    if not grades_by_subject:
        return mastered

    for subject, grade in grades_by_subject.items():
        grade_val = float(grade)
        rules = SUBJECT_MASTERY_THRESHOLDS.get(subject, {})
        for skill_code, threshold in rules.items():
            if grade_val >= threshold:
                mastered.add(skill_code)

    return mastered


def infer_mastered_skills_from_diagnostic_tests(
    diagnostic_tests: List[Dict[str, Any]]
) -> Set[str]:
    """
    Extracts mastered skills from optional diagnostic skill checks.
    Pass condition: test score >= 7.0 (on 10-point scale) or >= 0.70 (on 1-point scale) or is_passed == True.
    """
    mastered: Set[str] = set()
    if not diagnostic_tests:
        return mastered

    for test in diagnostic_tests:
        skill_code = str(test.get("skill_code", "")).strip()
        score = float(test.get("score", 0.0))
        is_passed = bool(test.get("is_passed", False))

        # Accept if score >= 7.0 (10-scale) or >= 0.70 (1-scale) or explicitly passed
        if is_passed or score >= 7.0 or (0.70 <= score <= 1.0):
            if skill_code:
                mastered.add(skill_code)

    return mastered


def analyze_competency_gaps(
    required_major_skills: List[Dict[str, Any]],
    skill_prerequisites_map: Dict[str, List[str]],
    mastered_skill_codes: Set[str]
) -> Tuple[List[str], List[str], List[str]]:
    """
    Deterministic Competency Gap Analysis Engine.
    
    Arguments:
    - required_major_skills: List of dicts representing skills linked to the major:
        [{"skill_code": "SKILL_TAR_PROG_PYTHON", "name": "Lập trình Python", "skill_type": "TARGET", "importance": "MANDATORY"}, ...]
    - skill_prerequisites_map: Dict mapping skill_code -> list of prerequisite skill_codes.
    - mastered_skill_codes: Set of skill_codes already mastered by the student.
    
    Returns:
    - overall_competency_gaps: Combined list of missing skill names for display.
    - missing_prerequisites: List of missing prerequisite skill names.
    - missing_target_skills: List of missing target skill names.
    """
    missing_prerequisites: List[str] = []
    missing_target_skills: List[str] = []
    overall_gaps: List[str] = []

    seen_skills: Set[str] = set()

    for item in required_major_skills:
        code = item.get("skill_code", "")
        name = item.get("name", code)
        s_type = str(item.get("skill_type", "TARGET")).upper()
        importance = str(item.get("importance", "MANDATORY")).upper()

        if code in seen_skills:
            continue
        seen_skills.add(code)

        # 1. Check if prerequisite dependencies are satisfied
        prereqs = skill_prerequisites_map.get(code, [])
        for p_code in prereqs:
            if p_code not in mastered_skill_codes and p_code not in seen_skills:
                seen_skills.add(p_code)
                missing_prerequisites.append(p_code)
                overall_gaps.append(f"Kiến thức tiên quyết cần bổ sung: {p_code}")

        # 2. Check the skill itself
        if code not in mastered_skill_codes:
            if "PREREQUISITE" in s_type:
                missing_prerequisites.append(name)
                overall_gaps.append(f"Tiên quyết: {name}")
            else:
                missing_target_skills.append(name)
                overall_gaps.append(f"Kỹ năng mục tiêu: {name}")

    return overall_gaps, missing_prerequisites, missing_target_skills
