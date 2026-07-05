from __future__ import annotations

import pytest

from src.saenggibu.models import StudentInput
from src.saenggibu.write_sections import (
    normalize_write_sections,
    pending_sections_for_student,
    student_needs_section,
    student_sections_complete,
    student_write_targets,
    students_needing_section,
    students_with_any_pending,
)


def test_normalize_requires_single_section() -> None:
    with pytest.raises(ValueError, match="선택"):
        normalize_write_sections(None)
    with pytest.raises(ValueError, match="하나"):
        normalize_write_sections(["행발", "세특"])


def test_normalize_accepts_one_section() -> None:
    assert normalize_write_sections(["행발"]) == ["행발"]
    assert normalize_write_sections(["세특"]) == ["세특"]
    assert normalize_write_sections(["자율"]) == ["자율"]


def test_student_write_targets_from_notes() -> None:
    student = StudentInput(
        id="s1",
        name="김민수",
        grade=2,
        class_num=1,
        number=1,
        notes={"write_targets": ["행발", "자율"]},
        changche={"자율": "학급 회의"},
    )
    assert student_write_targets(student) == ["행발", "자율"]


def test_student_needs_section_respects_write_targets() -> None:
    student = StudentInput(
        id="s1",
        name="김민수",
        grade=2,
        class_num=1,
        number=1,
        notes={"행발": "메모", "write_targets": ["행발"]},
        subjects={"윤사": {"activities": ["토론"], "notes": ""}},
        changche={"자율": "회의"},
    )
    assert student_needs_section(student, "행발") is True
    assert student_needs_section(student, "세특") is False
    assert student_needs_section(student, "자율") is False


def test_students_needing_section_filters_by_generated() -> None:
    pending = StudentInput(
        id="s1",
        name="김민수",
        grade=2,
        class_num=1,
        number=1,
        notes={"행발": "메모", "write_targets": ["행발", "세특"]},
        subjects={"윤사": {"activities": ["토론"], "notes": ""}},
    )
    partial = StudentInput(
        id="s2",
        name="이영희",
        grade=2,
        class_num=1,
        number=2,
        notes={"행발": "메모", "write_targets": ["행발", "세특"]},
        subjects={"윤사": {"activities": ["발표"], "notes": ""}},
        generated={"행발": "작성됨"},
        status="partial",
    )
    students = [pending, partial]
    assert len(students_needing_section(students, "행발")) == 1
    assert len(students_needing_section(students, "세특")) == 2
    assert student_sections_complete(partial) is False

    partial.generated["세특"] = {"윤사": "세특 본문"}
    assert student_needs_section(partial, "세특") is False
    assert student_sections_complete(partial) is True


def test_pending_sections_for_student_in_order() -> None:
    student = StudentInput(
        id="s1",
        name="김민수",
        grade=2,
        class_num=1,
        number=1,
        notes={"행발": "메모", "write_targets": ["행발", "세특", "자율"]},
        subjects={"윤사": {"activities": ["토론"], "notes": ""}},
        changche={"자율": "회의"},
        generated={"행발": "완료"},
        status="partial",
    )
    assert pending_sections_for_student(student) == ["세특", "자율"]


def test_students_with_any_pending() -> None:
    pending = StudentInput(
        id="s1",
        name="김민수",
        grade=2,
        class_num=1,
        number=1,
        notes={"행발": "메모", "write_targets": ["행발"]},
    )
    done = StudentInput(
        id="s2",
        name="이영희",
        grade=2,
        class_num=1,
        number=2,
        notes={"행발": "메모", "write_targets": ["행발"]},
        generated={"행발": "완료"},
        status="done",
    )
    assert [s.id for s in students_with_any_pending([pending, done])] == ["s1"]
