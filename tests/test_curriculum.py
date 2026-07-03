from __future__ import annotations

from src.saenggibu.curriculum import find_relevant_standards, format_curriculum_context, resolve_subject_entry


def test_resolve_subject_aliases() -> None:
    entry = resolve_subject_entry("현대사회와 윤리")
    assert entry is not None
    assert entry.get("units")


def test_find_relevant_standards_ai_ethics() -> None:
    standards = find_relevant_standards(
        "현대사회와윤리",
        {
            "topic": "인공지능 윤리",
            "content": "챗봇과 알고리즘 편향에 대해 토론하고 윤리적 해결 방안을 제시함",
        },
        limit=3,
    )
    assert standards
    codes = {item["code"] for item in standards}
    assert "12현윤03-03" in codes


def test_format_curriculum_context_includes_disclaimer() -> None:
    text = format_curriculum_context(
        [{"code": "12현윤03-03", "text": "인공지능 윤리", "unit": "과학과 디지털"}]
    )
    assert "12현윤03-03" in text
    assert "단정하지 마세요" in text
