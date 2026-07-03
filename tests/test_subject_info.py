from __future__ import annotations

from src.saenggibu.subject_info import format_setuk_prompt_context, setuk_activity_content


def test_setuk_activity_content_prefers_content_field() -> None:
    info = {"content": "본문", "notes": "옛메모", "activities": ["a"]}
    assert setuk_activity_content(info) == "본문"


def test_format_setuk_prompt_omits_empty_optional_fields() -> None:
    text = format_setuk_prompt_context(
        "현대사회와윤리",
        {
            "career": "",
            "assessment_type": "토론",
            "topic": "",
            "content": "활동 상세",
        },
    )
    assert "진로" not in text
    assert "수행평가 형식: 토론" in text
    assert "주제" not in text
    assert "활동 내용: 활동 상세" in text


def test_format_setuk_prompt_shows_none_when_empty() -> None:
    text = format_setuk_prompt_context("윤리와사상", {})
    assert "활동 내용: 없음" in text
