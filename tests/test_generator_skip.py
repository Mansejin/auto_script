from __future__ import annotations

from unittest.mock import patch

from src.saenggibu.generator import generate_for_student
from src.saenggibu.models import StudentInput


@patch("src.saenggibu.generator._load_style_guide", return_value="스타일")
@patch("src.saenggibu.generator.check_generation_allowed")
@patch("src.saenggibu.generator.save_student", side_effect=lambda student: student)
@patch("src.saenggibu.generator.record_generation")
@patch("src.saenggibu.generator.generate_text", return_value="새로 생성된 본문")
def test_generate_setuk_skips_existing_subjects(
    mock_generate,
    _record,
    _save,
    _check,
    _style,
) -> None:
    student = StudentInput(
        id="s1",
        name="김민수",
        grade=2,
        class_num=1,
        number=1,
        notes={"write_targets": ["세특"]},
        subjects={
            "윤사": {"activities": ["토론"], "notes": ""},
            "윤리": {"activities": ["발표"], "notes": ""},
        },
        generated={"세특": {"윤사": "기존 윤사 세특"}},
        status="partial",
    )
    updated = generate_for_student(student, sections=["세특"])
    assert updated.generated["세특"]["윤사"] == "기존 윤사 세특"
    assert updated.generated["세특"]["윤리"] == "새로 생성된 본문"
    assert mock_generate.call_count == 1
