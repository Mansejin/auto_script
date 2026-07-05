from __future__ import annotations

import re
from typing import Any

from ..models import StudentInput
from ..student_store import get_student, list_students
from .issues import InspectIssue, InspectReport, report_to_dict
from .rules import (
    EXAGGERATION_THRESHOLD,
    FORBIDDEN_PATTERNS,
    WARNING_PATTERNS,
    char_len,
    find_pattern_matches,
    get_char_limits,
    iter_generated_fields,
)


def _student_label(student: StudentInput) -> str:
    return student.display_name


def inspect_text(
    text: str,
    *,
    section_key: str = "본문",
    student_name: str = "",
) -> InspectReport:
    report = InspectReport(char_count={section_key: char_len(text)})
    _inspect_field(report, section_key, text, student_name=student_name)
    return report


def inspect_student(student: StudentInput) -> InspectReport:
    report = InspectReport(
        student_id=student.id,
        student_label=_student_label(student),
    )
    for section_key, body in iter_generated_fields(student.generated or {}):
        report.char_count[section_key] = char_len(body)
        _inspect_field(report, section_key, body, student_name=student.name.strip())
    return report


def inspect_students(students: list[StudentInput]) -> list[InspectReport]:
    return [inspect_student(student) for student in students]


def inspect_all_students() -> list[InspectReport]:
    students = [s for s in list_students() if iter_generated_fields(s.generated or {})]
    return inspect_students(students)


def inspect_students_by_ids(ids: list[str]) -> tuple[list[InspectReport], list[str]]:
    reports: list[InspectReport] = []
    not_found: list[str] = []
    for student_id in ids:
        student = get_student(student_id)
        if not student:
            not_found.append(student_id)
            continue
        if not iter_generated_fields(student.generated or {}):
            reports.append(InspectReport(student_id=student.id, student_label=_student_label(student)))
            continue
        reports.append(inspect_student(student))
    return reports, not_found


def inspect_student_by_id(student_id: str) -> InspectReport | None:
    student = get_student(student_id)
    if not student:
        return None
    return inspect_student(student)


def _inspect_field(
    report: InspectReport,
    section_key: str,
    text: str,
    *,
    student_name: str = "",
) -> None:
    if not text.strip():
        return

    limits = get_char_limits(section_key)
    length = char_len(text)

    if length > limits["hard_max"]:
        report.issues.append(
            InspectIssue(
                section=section_key,
                code="char_count_over",
                severity="error",
                message=f"글자 수 초과 ({length}자 / 권장 최대 {limits['hard_max']}자)",
                detail=f"현재 {length}자",
            )
        )
    elif length > limits["max"]:
        report.issues.append(
            InspectIssue(
                section=section_key,
                code="char_count_high",
                severity="warning",
                message=f"글자 수가 권장 상한을 넘었습니다 ({length}자 / 권장 {limits['max']}자)",
                detail=f"현재 {length}자",
            )
        )
    elif length < limits["min"]:
        report.issues.append(
            InspectIssue(
                section=section_key,
                code="char_count_low",
                severity="info",
                message=f"글자 수가 권장 하한보다 짧습니다 ({length}자 / 권장 {limits['min']}자 이상)",
                detail=f"현재 {length}자",
            )
        )

    for _, code, message, match in find_pattern_matches(text, FORBIDDEN_PATTERNS):
        report.issues.append(
            InspectIssue(
                section=section_key,
                code=code,
                severity="error",
                message=message,
                detail=match.group(0),
                offset=match.start(),
            )
        )

    exaggeration_hits = find_pattern_matches(text, WARNING_PATTERNS[:1])
    if len(exaggeration_hits) >= EXAGGERATION_THRESHOLD:
        report.issues.append(
            InspectIssue(
                section=section_key,
                code="exaggeration",
                severity="warning",
                message=WARNING_PATTERNS[0][2],
                detail=f"{len(exaggeration_hits)}회 감지",
            )
        )

    for _, code, message, match in find_pattern_matches(text, WARNING_PATTERNS[1:]):
        report.issues.append(
            InspectIssue(
                section=section_key,
                code=code,
                severity="warning",
                message=message,
                detail=match.group(0),
                offset=match.start(),
            )
        )

    if student_name and len(student_name) >= 2 and student_name in text:
        report.issues.append(
            InspectIssue(
                section=section_key,
                code="real_name",
                severity="warning",
                message="학생 실명이 본문에 포함되어 있습니다. '학생' 또는 'OO' 표기를 권장합니다.",
                detail=student_name,
            )
        )

    _check_duplicate_sentences(report, section_key, text)


def _check_duplicate_sentences(report: InspectReport, section_key: str, text: str) -> None:
    parts = [part.strip() for part in re.split(r"[.。]\s*", text) if part.strip()]
    if len(parts) < 2:
        return
    seen: dict[str, int] = {}
    for part in parts:
        if len(part) < 12:
            continue
        seen[part] = seen.get(part, 0) + 1
    duplicates = [part for part, count in seen.items() if count > 1]
    if duplicates:
        report.issues.append(
            InspectIssue(
                section=section_key,
                code="duplicate_sentence",
                severity="warning",
                message="동일·유사 문장이 반복됩니다.",
                detail=duplicates[0][:80],
            )
        )


def reports_as_dicts(reports: list[InspectReport]) -> list[dict[str, Any]]:
    return [report_to_dict(report) for report in reports]
