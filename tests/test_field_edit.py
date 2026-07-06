from unittest.mock import patch

from src.saenggibu.field_edit import (
    adjust_field_volume,
    edit_student_field,
    fix_field_issues,
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


@patch("src.saenggibu.field_edit.proofread_text", return_value="교정됨")
@patch("src.saenggibu.field_edit.record_generation")
@patch("src.saenggibu.field_edit.check_generation_allowed")
def test_edit_proofread(mock_check, mock_record, mock_proof) -> None:
    student = StudentInput(id="s1", name="김", grade=2, class_num=1, number=1)
    text = edit_student_field(student, field_key="행발", action="proofread", text="원문")
    assert text == "교정됨"


@patch("src.saenggibu.field_edit.generate_text", return_value="줄인 본문")
def test_adjust_field_volume_over_limit(mock_gen) -> None:
    long_text = "가" * 1600
    result = adjust_field_volume(long_text, "세특:수학")
    assert result == "줄인 본문"
    user_prompt = mock_gen.call_args.kwargs.get("user") or mock_gen.call_args[1].get("user", "")
    assert "줄이" in user_prompt


@patch("src.saenggibu.field_edit.generate_text", return_value="수정 본문")
def test_fix_field_issues(mock_gen) -> None:
    result = fix_field_issues(
        "반에서 1등이다.",
        "행발",
        [{"severity": "error", "message": "순위 표현 제거", "detail": "1등"}],
    )
    assert result == "수정 본문"


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
