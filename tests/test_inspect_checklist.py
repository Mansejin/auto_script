from __future__ import annotations

from src.saenggibu.inspector.checklist import build_inspect_checklist
from src.saenggibu.inspector.issues import InspectIssue, InspectReport, report_to_dict
from src.saenggibu.inspector.runner import inspect_batch, inspect_generated_items
from src.saenggibu.models import StudentInput


def test_build_inspect_checklist_passes_clean_report() -> None:
    report = InspectReport(
        student_id="s1",
        char_count={"행발": 420},
        issues=[],
    )
    checklist = build_inspect_checklist(report)
    assert len(checklist) == 5
    assert all(item["status"] == "pass" for item in checklist)


def test_build_inspect_checklist_marks_forbidden_fail() -> None:
    report = InspectReport(
        student_id="s1",
        char_count={"행발": 420},
        issues=[
            InspectIssue(
                section="행발",
                code="ranking",
                severity="error",
                message="석차 표현",
            )
        ],
    )
    forbidden = next(item for item in build_inspect_checklist(report) if item["id"] == "forbidden")
    assert forbidden["status"] == "fail"
    assert forbidden["issue_count"] == 1


def test_report_to_dict_includes_checklist() -> None:
    report = InspectReport(student_id="s1", char_count={"행발": 100})
    payload = report_to_dict(report)
    assert "checklist" in payload
    assert len(payload["checklist"]) == 5


def test_inspect_generated_items_uses_client_body() -> None:
    student = StudentInput(
        id="client-1",
        name="홍길동",
        grade=2,
        class_num=1,
        number=1,
        generated={"행발": "수학 성적이 반에서 1등이며 석차가 높다." * 20},
    )
    reports = inspect_generated_items(
        [
            {
                "id": student.id,
                "name": student.name,
                "label": "2-1-1 홍길동",
                "generated": student.generated,
            }
        ]
    )
    assert len(reports) == 1
    assert reports[0].status == "fail"


def test_inspect_batch_skips_ok_ids() -> None:
    result = inspect_batch(
        items=[
            {
                "id": "a",
                "generated": {"행발": "학생은 수업에 성실히 참여한다." * 30},
            },
            {
                "id": "b",
                "generated": {"행발": "학생은 모둠 활동에 적극적으로 참여한다." * 30},
            },
        ],
        skip_ok_ids={"a"},
    )
    assert result["summary"]["skipped_ok"] == 1
    assert result["summary"]["total"] == 1
    assert len(result["reports"]) == 1
    assert result["reports"][0].student_id == "b"
