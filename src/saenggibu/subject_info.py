from __future__ import annotations

from typing import Any


def setuk_activity_content(info: dict[str, Any]) -> str:
    content = str(info.get("content") or "").strip()
    if content:
        return content
    notes = str(info.get("notes") or "").strip()
    if notes:
        return notes
    activities = info.get("activities") or []
    if isinstance(activities, list):
        parts = [str(item).strip() for item in activities if str(item).strip()]
        return "\n".join(parts)
    return str(activities).strip()


def normalize_subject_info(info: dict[str, Any]) -> dict[str, str]:
    return {
        "career": str(info.get("career") or "").strip(),
        "assessment_type": str(info.get("assessment_type") or info.get("assessment") or "").strip(),
        "topic": str(info.get("topic") or "").strip(),
        "content": setuk_activity_content(info),
        "traits": str(info.get("traits") or "").strip(),
    }


def format_setuk_prompt_context(subject: str, info: dict[str, Any]) -> str:
    fields = normalize_subject_info(info)
    lines = [f"- 과목: {subject}"]
    if fields["career"]:
        lines.append(f"- 진로: {fields['career']}")
    if fields["assessment_type"]:
        lines.append(f"- 수행평가 형식: {fields['assessment_type']}")
    if fields["topic"]:
        lines.append(f"- 주제: {fields['topic']}")
    if fields["content"]:
        lines.append(f"- 활동 내용: {fields['content']}")
    elif fields["traits"]:
        lines.append(f"- 특성 메모: {fields['traits']}")
    else:
        lines.append("- 활동 내용: 없음")
    return "\n".join(lines)
