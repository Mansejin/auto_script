from __future__ import annotations

import pytest

from src.saenggibu.models import StudentInput
from src.saenggibu.neis_format import format_neis_tsv, merge_parsed_into_student, parse_neis_paste


def test_parse_neis_tsv_generated_row() -> None:
    text = (
        "학년\t반\t번호\t이름\t행동특성 및 종합의견\t세특_윤사\t자율활동\t동아리활동\t봉사활동\t진로활동\n"
        "2\t1\t3\t김민수\t행발 본문\t세특 본문\t자율 본문\t동아리 본문\t봉사 본문\t진로 본문"
    )
    parsed = parse_neis_paste(text)
    assert parsed["format"] == "tsv"
    assert parsed["generated"]["행발"] == "행발 본문"
    assert parsed["generated"]["세특"]["윤사"] == "세특 본문"
    assert parsed["generated"]["창체"]["봉사"] == "봉사 본문"


def test_parse_neis_tsv_memo_row() -> None:
    text = (
        "name\tgrade\tclass_num\tnumber\t행발_notes\t세특_윤사\t창체_봉사\n"
        "김민수\t2\t1\t3\t행발 메모\t윤사 활동 메모\t도서관 봉사 4회"
    )
    parsed = parse_neis_paste(text)
    assert parsed["notes"]["행발"] == "행발 메모"
    assert parsed["subjects"]["윤사"]["content"] == "윤사 활동 메모"
    assert parsed["changche"]["봉사"] == "도서관 봉사 4회"
    assert "봉사" in parsed["notes"]["write_targets"]


def test_parse_neis_block_text() -> None:
    text = "【행동특성 및 종합의견】\n행발 본문\n\n【세특 · 윤사】\n세특 본문"
    parsed = parse_neis_paste(text)
    assert parsed["format"] == "block"
    assert parsed["generated"]["행발"] == "행발 본문"
    assert parsed["generated"]["세특"]["윤사"] == "세특 본문"


def test_format_neis_tsv_roundtrip() -> None:
    student = StudentInput(
        id="s1",
        name="김민수",
        grade=2,
        class_num=1,
        number=3,
        generated={
            "행발": "행발 본문",
            "세특": {"윤사": "세특 본문"},
            "창체": {"봉사": "봉사 본문"},
        },
    )
    tsv = format_neis_tsv(student)
    parsed = parse_neis_paste(tsv)
    assert parsed["generated"]["행발"] == "행발 본문"
    assert parsed["generated"]["세특"]["윤사"] == "세특 본문"
    assert parsed["generated"]["창체"]["봉사"] == "봉사 본문"


def test_merge_parsed_into_student() -> None:
    student = StudentInput(id="s1", name="김민수", grade=2, class_num=1, number=3)
    parsed = parse_neis_paste("name\t행발_notes\t창체_봉사\n김민수\t새 메모\t봉사 메모")
    merged = merge_parsed_into_student(student, parsed)
    assert merged.notes["행발"] == "새 메모"
    assert merged.changche["봉사"] == "봉사 메모"
