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
    find_pattern_matches,
    get_volume_limits,
    iter_generated_fields,
    measure_volume,
)


def _student_label(student: StudentInput) -> str:
    return student.display_name


def inspect_text(
    text: str,
    *,
    section_key: str = "본문",
    student_name: str = "",
) -> InspectReport:
    report = InspectReport(char_count={section_key: measure_volume(text, section_key)})
    _inspect_field(report, section_key, text, student_name=student_name)
    return report


def inspect_student(student: StudentInput) -> InspectReport:
    report = InspectReport(
        student_id=student.id,
        student_label=_student_label(student),
    )
    for section_key, body in iter_generated_fields(student.generated or {}):
        report.char_count[section_key] = measure_volume(body, section_key)
        _inspect_field(report, section_key, body, student_name=student.name.strip())
    return report


def inspect_students(students: list[StudentInput]) -> list[InspectReport]:
    return [inspect_student(student) for student in students]


def inspect_all_students(
    *,
    student_ids: list[str] | None = None,
    skip_ok_ids: set[str] | None = None,
) -> list[InspectReport]:
    skip_ok = skip_ok_ids or set()
    if student_ids:
        reports, _ = inspect_students_by_ids([sid for sid in student_ids if sid not in skip_ok])
        return reports
    students = [s for s in list_students() if iter_generated_fields(s.generated or {})]
    return inspect_students([student for student in students if student.id not in skip_ok])


def inspect_batch(
    *,
    student_ids: list[str] | None = None,
    items: list[dict[str, Any]] | None = None,
    skip_ok_ids: set[str] | None = None,
) -> dict[str, Any]:
    skip_ok = skip_ok_ids or set()
    not_found: list[str] = []
    skipped_ok = 0
    skipped_empty = 0

    if items:
        skipped_ok = sum(1 for item in items if str(item.get("id") or "") in skip_ok)
        to_inspect = [item for item in items if str(item.get("id") or "") not in skip_ok]
        reports = inspect_generated_items(to_inspect)
    elif student_ids:
        skipped_ok = sum(1 for student_id in student_ids if student_id in skip_ok)
        filtered_ids = [student_id for student_id in student_ids if student_id not in skip_ok]
        reports, not_found = inspect_students_by_ids(filtered_ids)
    else:
        for student in list_students():
            if not iter_generated_fields(student.generated or {}):
                skipped_empty += 1
                continue
            if student.id in skip_ok:
                skipped_ok += 1
        reports = inspect_all_students(skip_ok_ids=skip_ok)

    summary = {
        "total": len(reports),
        "fail": sum(1 for report in reports if report.status == "fail"),
        "warn": sum(1 for report in reports if report.status == "warn"),
        "ok": sum(1 for report in reports if report.status == "ok"),
        "skipped_ok": skipped_ok,
        "skipped_empty": skipped_empty,
    }
    return {
        "summary": summary,
        "not_found": not_found,
        "reports": reports,
    }


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


def inspect_student_by_id(student_id: str, *, generated: dict | None = None) -> InspectReport | None:
    student = get_student(student_id)
    if not student:
        return None
    if generated is not None:
        student = StudentInput(
            id=student.id,
            name=student.name,
            grade=student.grade,
            class_num=student.class_num,
            number=student.number,
            gender=student.gender,
            status=student.status,
            notes=student.notes,
            subjects=student.subjects,
            changche=student.changche,
            generated=generated,
        )
    return inspect_student(student)


def inspect_generated_items(items: list[dict[str, Any]]) -> list[InspectReport]:
    reports: list[InspectReport] = []
    for item in items:
        student_id = str(item.get("id") or "").strip()
        generated = item.get("generated") or {}
        label = str(item.get("label") or "").strip()
        name = str(item.get("name") or "").strip()
        if not student_id:
            continue
        student = get_student(student_id)
        if student:
            report = inspect_student_by_id(student_id, generated=generated)
            if report:
                if label:
                    report.student_label = label
                reports.append(report)
            continue
        if not iter_generated_fields(generated):
            reports.append(InspectReport(student_id=student_id, student_label=label or student_id))
            continue
        temp = StudentInput(
            id=student_id,
            name=name or "학생",
            grade=1,
            class_num=1,
            number=1,
            generated=generated,
        )
        report = inspect_student(temp)
        report.student_id = student_id
        if label:
            report.student_label = label
        reports.append(report)
    return reports


def _inspect_field(
    report: InspectReport,
    section_key: str,
    text: str,
    *,
    student_name: str = "",
) -> None:
    if not text.strip():
        return

    limits = get_volume_limits(section_key)
    length = measure_volume(text, section_key)

    if length > limits["hard_max"]:
        report.issues.append(
            InspectIssue(
                section=section_key,
                code="char_count_over",
                severity="error",
                message=f"NEIS 용량 초과 ({length}byte / 최대 {limits['hard_max']}byte)",
                detail=f"현재 {length}byte",
            )
        )
    elif length > limits["max"]:
        report.issues.append(
            InspectIssue(
                section=section_key,
                code="char_count_high",
                severity="warning",
                message=f"NEIS 용량이 권장 상한에 가깝습니다 ({length}byte / 권장 {limits['max']}byte)",
                detail=f"현재 {length}byte",
            )
        )
    elif length < limits["min"]:
        report.issues.append(
            InspectIssue(
                section=section_key,
                code="char_count_low",
                severity="info",
                message=f"NEIS 용량이 권장 하한보다 짧습니다 ({length}byte / 권장 {limits['min']}byte 이상)",
                detail=f"현재 {length}byte",
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

