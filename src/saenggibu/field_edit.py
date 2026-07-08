from __future__ import annotations

from typing import Literal

from .config import skip_gemini_proofread
from .generator import (
    _generate_changche,
    _generate_haengbal,
    _generate_setuk,
    _load_style_guide,
)
from .models import StudentInput
from .spell_check import proofread_text
from .usage import check_generation_allowed, record_generation

FieldAction = Literal["regenerate", "proofread"]


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


def edit_student_field(
    student: StudentInput,
    *,
    field_key: str,
    action: FieldAction,
    text: str = "",
) -> str:
    check_generation_allowed()
    key = field_key.strip()
    if not key:
        raise ValueError("field_key가 필요합니다.")

    if action == "regenerate":
        result = regenerate_field(student, key)
        if not skip_gemini_proofread():
            result = proofread_text(result)
    elif action == "proofread":
        if not text.strip():
            raise ValueError("본문이 비어 있습니다.")
        result = proofread_text(text)
    else:
        raise ValueError(f"Unknown action: {action}")

    record_generation()
    return result
