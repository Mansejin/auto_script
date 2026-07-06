from __future__ import annotations

from typing import Any, Literal

from .gemini_client import generate_text
from .generator import (
    _generate_changche,
    _generate_haengbal,
    _generate_setuk,
    _load_style_guide,
    _system_prompt,
)
from .inspector.issues import InspectIssue
from .inspector.rules import get_volume_limits, measure_volume
from .models import StudentInput
from .spell_check import proofread_text
from .usage import check_generation_allowed, record_generation

FieldAction = Literal["regenerate", "proofread", "adjust_volume", "fix_issues"]


def parse_field_key(field_key: str) -> tuple[str, str | None]:
    key = field_key.strip()
    if key == "행발":
        return "행발", None
    if ":" in key:
        kind, sub = key.split(":", 1)
        return kind.strip(), sub.strip() or None
    return key, None


def regenerate_field(student: StudentInput, field_key: str) -> str:
    kind, sub = parse_field_key(field_key)
    style_guide = _load_style_guide()
    if kind == "행발":
        return _generate_haengbal(student, style_guide)
    if kind == "세특":
        if not sub:
            raise ValueError("세특 과목이 지정되지 않았습니다.")
        info = (student.subjects or {}).get(sub) or {}
        return _generate_setuk(student, sub, info, style_guide)
    if kind == "창체":
        if not sub:
            raise ValueError("창체 영역이 지정되지 않았습니다.")
        notes = str((student.changche or {}).get(sub) or "").strip()
        if not notes:
            raise ValueError(f"{sub} 활동 메모가 없습니다.")
        return _generate_changche(student, sub, notes, style_guide)
    raise ValueError(f"지원하지 않는 항목입니다: {field_key}")


def adjust_field_volume(text: str, field_key: str) -> str:
    body = text.strip()
    if not body:
        raise ValueError("본문이 비어 있습니다.")
    limits = get_volume_limits(field_key)
    unit = limits["unit"]
    current = measure_volume(body, field_key)
    target = int(limits["max"])
    hard_max = int(limits["hard_max"])
    min_len = int(limits["min"])

    if current > hard_max:
        direction = "줄이"
        target = hard_max
    elif current > target:
        direction = "줄이"
    elif current < min_len:
        direction = "늘리"
        target = min_len
    else:
        direction = "맞추"
        target = target

    unit_label = "byte" if unit == "byte" else "자"
    user = (
        f"아래 생활기록부 문장의 분량을 {direction} 주세요.\n"
        f"- 목표: 약 {target}{unit_label} (현재 {current}{unit_label})\n"
        f"- 사실·활동 내용·문체·톤은 유지하고 표현만 조정하세요.\n"
        f"- 순위·점수·가정환경 등 기재 금지 표현은 넣지 마세요.\n"
        f"- 출력은 수정된 본문만 작성하세요.\n\n"
        f"{body}"
    )
    return generate_text(system=_system_prompt(), user=user, temperature=0.3)


def _issues_from_payload(items: list[dict[str, Any]]) -> list[InspectIssue]:
    result: list[InspectIssue] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        severity = raw.get("severity")
        if severity not in ("error", "warning", "info"):
            severity = "warning"
        result.append(
            InspectIssue(
                section=str(raw.get("section") or ""),
                code=str(raw.get("code") or ""),
                severity=severity,  # type: ignore[arg-type]
                message=str(raw.get("message") or ""),
                detail=str(raw.get("detail") or ""),
                offset=raw.get("offset"),
            )
        )
    return result


def fix_field_issues(text: str, field_key: str, issues: list[dict[str, Any]]) -> str:
    body = text.strip()
    if not body:
        raise ValueError("본문이 비어 있습니다.")
    parsed = _issues_from_payload(issues)
    if not parsed:
        raise ValueError("수정할 검사 항목이 없습니다.")

    limits = get_volume_limits(field_key)
    unit = limits["unit"]
    unit_label = "byte" if unit == "byte" else "자"
    current = measure_volume(body, field_key)
    issue_lines = []
    for issue in parsed:
        line = f"- {issue.message}"
        if issue.detail:
            line += f" (해당 표현: «{issue.detail}»)"
        issue_lines.append(line)

    user = (
        "아래 생활기록부 문장을 검사 지적 사항에 맞게 고치세요.\n"
        f"- 현재 분량: {current}{unit_label} (권장 최대 {limits['max']}{unit_label}, "
        f"절대 최대 {limits['hard_max']}{unit_label})\n"
        "- 사실 관계·관찰 내용은 유지하고, 금지·주의 표현만 제거·완화하세요.\n"
        "- 학생 실명은 '학생' 또는 'OO'로 바꾸세요.\n"
        "- 출력은 수정된 본문만 작성하세요.\n\n"
        "## 지적 사항\n"
        + "\n".join(issue_lines)
        + "\n\n## 본문\n"
        + body
    )
    return generate_text(system=_system_prompt(), user=user, temperature=0.25)


def edit_student_field(
    student: StudentInput,
    *,
    field_key: str,
    action: FieldAction,
    text: str = "",
    issues: list[dict[str, Any]] | None = None,
) -> str:
    check_generation_allowed()
    key = field_key.strip()
    if not key:
        raise ValueError("field_key가 필요합니다.")

    if action == "regenerate":
        result = regenerate_field(student, key)
        result = proofread_text(result)
    elif action == "proofread":
        if not text.strip():
            raise ValueError("본문이 비어 있습니다.")
        result = proofread_text(text)
    elif action == "adjust_volume":
        result = adjust_field_volume(text, key)
    elif action == "fix_issues":
        result = fix_field_issues(text, key, issues or [])
    else:
        raise ValueError(f"Unknown action: {action}")

    record_generation()
    return result
