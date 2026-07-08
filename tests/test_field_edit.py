from unittest.mock import patch

from src.saenggibu.field_edit import (
    edit_student_field,
    parse_field_key,
    regenerate_field,
)
from src.saenggibu.models import StudentInput


def test_parse_field_key() -> None:
    assert parse_field_key("행발") == ("행발", None)
    assert parse_field_key("세특:수학") == ("세특", "수학")


@patch("src.saenggibu.field_edit.proofread_text", side_effect=lambda t: t)
@patch("src.saenggibu.field_edit._load_style_guide", return_value="guide")
@patch("src.saenggibu.field_edit._generate_haengbal", return_value="행발 본문")
@patch("src.saenggibu.field_edit.record_generation")
@patch("src.saenggibu.field_edit.check_generation_allowed")
def test_edit_regenerate_haengbal(mock_check, mock_record, mock_gen, mock_style, mock_proof) -> None:
    student = StudentInput(id="s1", name="김", grade=2, class_num=1, number=1)
    text = edit_student_field(student, field_key="행발", action="regenerate")
    assert text == "행발 본문"
    mock_gen.assert_called_once()
    mock_proof.assert_called_once()


@patch("src.saenggibu.field_edit.skip_gemini_proofread", return_value=True)
@patch("src.saenggibu.field_edit.proofread_text", side_effect=lambda t: t + "!")
@patch("src.saenggibu.field_edit._load_style_guide", return_value="guide")
@patch("src.saenggibu.field_edit._generate_haengbal", return_value="행발 본문")
@patch("src.saenggibu.field_edit.record_generation")
@patch("src.saenggibu.field_edit.check_generation_allowed")
def test_edit_regenerate_skips_proofread_when_configured(
    mock_check, mock_record, mock_gen, mock_style, mock_proof, mock_skip
) -> None:
    student = StudentInput(id="s1", name="김", grade=2, class_num=1, number=1)
    text = edit_student_field(student, field_key="행발", action="regenerate")
    assert text == "행발 본문"
    mock_proof.assert_not_called()


@patch("src.saenggibu.field_edit.proofread_text", return_value="교정됨")
@patch("src.saenggibu.field_edit.record_generation")
@patch("src.saenggibu.field_edit.check_generation_allowed")
def test_edit_proofread(mock_check, mock_record, mock_proof) -> None:
    student = StudentInput(id="s1", name="김", grade=2, class_num=1, number=1)
    text = edit_student_field(student, field_key="행발", action="proofread", text="원문")
    assert text == "교정됨"


@patch("src.saenggibu.field_edit._generate_setuk", return_value="세특 본문")
@patch("src.saenggibu.field_edit._load_style_guide", return_value="guide")
def test_regenerate_setuk(mock_style, mock_gen) -> None:
    student = StudentInput(
        id="s1",
        name="김",
        grade=2,
        class_num=1,
        number=1,
        subjects={"수학": {"content": "활동"}},
    )
    text = regenerate_field(student, "세특:수학")
    assert text == "세특 본문"
    mock_gen.assert_called_once()
