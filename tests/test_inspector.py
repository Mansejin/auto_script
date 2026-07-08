from __future__ import annotations

import pytest

from src.saenggibu.inspector import inspect_student, inspect_text
from src.saenggibu.models import StudentInput


def test_inspect_text_detects_forbidden_ranking() -> None:
    report = inspect_text("수학 성적이 반에서 1등이며 석차가 높다.", section_key="행발")
    codes = {issue.code for issue in report.issues}
    assert "ranking" in codes
    assert report.status == "fail"


def test_inspect_text_detects_score() -> None:
    report = inspect_text("중간고사에서 95점을 받았다.", section_key="세특:수학")
    assert any(issue.code == "score" for issue in report.issues)


def test_inspect_text_char_count_warning() -> None:
    long_text = "가" * 760
    report = inspect_text(long_text, section_key="세특:수학")
    assert any(issue.code in {"char_count_over", "char_count_high"} for issue in report.issues)


def test_inspect_setuk_uses_neis_counter_byte_limit() -> None:
    text = "가" * 545
    report = inspect_text(text, section_key="세특:수학")
    assert any(issue.code == "char_count_over" for issue in report.issues)
    assert report.char_count["세특:수학"] == 1635


def test_inspect_text_char_count_low_info() -> None:
    report = inspect_text("짧은 문장.", section_key="행발")
    assert any(issue.code == "char_count_low" for issue in report.issues)
    assert report.status == "warn" or report.info_count >= 1


def test_inspect_student_real_name_warning() -> None:
    student = StudentInput(
        id="s1",
        name="김민수",
        grade=2,
        class_num=1,
        number=3,
        generated={"행발": "김민수는 수업에 성실히 참여하며 책임감 있게 학교생활을 한다." * 20},
    )
    report = inspect_student(student)
    assert any(issue.code == "real_name" for issue in report.issues)
    assert report.char_count["행발"] > 0


def test_inspect_student_ok_clean_text() -> None:
    body = (
        "학생은 수업 시간에 교사의 설명을 주의 깊게 듣고 질문을 통해 내용을 정리하려는 태도를 보인다. "
        "모둠 활동에서 역할을 성실히 수행하며 자료를 정리해 발표를 준비했다. "
        "어려운 개념을 스스로 복습하는 습관을 갖추어 과목 이해를 넓혀 가고 있다. "
    ) * 2
    student = StudentInput(
        id="s2",
        name="이서연",
        grade=2,
        class_num=1,
        number=4,
        generated={"행발": body},
    )
    report = inspect_student(student)
    assert report.error_count == 0


def test_inspect_student_multiple_sections() -> None:
    student = StudentInput(
        id="s3",
        name="박지훈",
        grade=2,
        class_num=1,
        number=5,
        generated={
            "행발": "x" * 450,
            "세특": {"현대사회와윤리": "y" * 400},
            "창체": {"자율": "z" * 150},
        },
    )
    report = inspect_student(student)
    assert set(report.char_count.keys()) == {"행발", "세특:현대사회와윤리", "창체:자율"}
