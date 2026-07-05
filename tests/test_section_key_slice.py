from __future__ import annotations

from src.saenggibu.inspector.runner import inspect_student
from src.saenggibu.models import StudentInput


def test_inspect_long_setuk_subject_name_no_duplicate_sections() -> None:
    body = "가" * 545
    student = StudentInput(
        id="s1",
        name="오세진",
        grade=1,
        class_num=1,
        number=1,
        generated={"세특": {"현대사회와윤리": body}},
    )
    report = inspect_student(student)
    sections = [issue.section for issue in report.issues if issue.code == "char_count_over"]
    assert sections == ["세특:현대사회와윤리"]
