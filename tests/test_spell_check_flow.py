from __future__ import annotations

from unittest.mock import patch

from src.saenggibu.generator import generate_for_student
from src.saenggibu.models import StudentInput


@patch("src.saenggibu.generator._load_style_guide", return_value="스타일")
@patch("src.saenggibu.generator.check_generation_allowed")
@patch("src.saenggibu.generator.save_student", side_effect=lambda student: student)
@patch("src.saenggibu.generator.record_generation")
@patch("src.saenggibu.generator.generate_text", return_value="초안 본문")
def test_generate_writes_without_auto_proofread(
    mock_generate,
    mock_record,
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
        notes={"행발": "메모", "write_targets": ["행발"]},
        status="pending",
    )
    updated = generate_for_student(student, sections=["행발"])
    assert updated.generated["행발"] == "초안 본문"
    mock_generate.assert_called_once()
    assert mock_record.call_count == 1
