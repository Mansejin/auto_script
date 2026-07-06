from __future__ import annotations

from src.saenggibu.models import StudentInput
from src.saenggibu.storage_policy import apply_run_draft, apply_run_drafts, draft_map_from_items
from src.saenggibu.write_sections import student_needs_section, students_needing_section


def test_apply_run_draft_marks_setuk_complete() -> None:
    student = StudentInput(
        id="s1",
        name="김민수",
        grade=2,
        class_num=1,
        number=1,
        notes={"write_targets": ["세특"]},
        subjects={"윤사": {"activities": ["토론"], "notes": ""}},
        generated={},
        status="pending",
    )
    merged = apply_run_draft(
        student,
        {"세특": {"윤사": "이미 작성된 세특 본문입니다." * 20}},
    )
    assert student_needs_section(merged, "세특") is False
    assert merged.status == "done"


def test_students_needing_section_uses_drafts() -> None:
    done = StudentInput(
        id="done",
        name="완료",
        grade=2,
        class_num=1,
        number=1,
        notes={"write_targets": ["세특"]},
        subjects={"윤사": {"activities": ["토론"], "notes": ""}},
    )
    pending = StudentInput(
        id="pending",
        name="대기",
        grade=2,
        class_num=1,
        number=2,
        notes={"write_targets": ["세특"]},
        subjects={"윤사": {"activities": ["발표"], "notes": ""}},
    )
    draft_map = draft_map_from_items(
        [
            {
                "student_id": "done",
                "generated": {"세특": {"윤사": "작성 완료" * 30}},
            }
        ]
    )
    needing = students_needing_section(apply_run_drafts([done, pending], draft_map), "세특")
    assert [student.id for student in needing] == ["pending"]
