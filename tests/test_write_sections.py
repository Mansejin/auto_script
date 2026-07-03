from __future__ import annotations

import pytest

from src.saenggibu.models import StudentInput
from src.saenggibu.write_sections import (
    normalize_write_sections,
    student_needs_section,
    student_sections_complete,
    students_needing_section,
)


def test_normalize_requires_single_section() -> None:
    with pytest.raises(ValueError, match="선택"):
        normalize_write_sections(None)
    with pytest.raises(ValueError, match="하나"):
        normalize_write_sections(["행발", "세특"])


def test_normalize_accepts_one_section() -> None:
    assert normalize_write_sections(["행발"]) == ["행발"]
    assert normalize_write_sections(["세특"]) == ["세특"]


def test_students_needing_section_filters_by_generated() -> None:
    pending = StudentInput(
        id="s1",
        name="김민수",
        grade=2,
        class_num=1,
        number=1,
        notes={"행발": "메모"},
        subjects={"윤사": {"activities": ["토론"], "notes": ""}},
    )
    partial = StudentInput(
        id="s2",
        name="이영희",
        grade=2,
        class_num=1,
        number=2,
        notes={"행발": "메모"},
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
