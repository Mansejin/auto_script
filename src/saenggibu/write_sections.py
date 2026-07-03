from __future__ import annotations

from .models import StudentInput

WRITE_SECTIONS = ("행발", "세특", "창체")
_INCOMPATIBLE = frozenset({"행발", "세특"})


def normalize_write_sections(sections: list[str] | None) -> list[str]:
    if not sections:
        raise ValueError("작성할 영역을 선택하세요. 행발과 세특은 따로 실행합니다.")
    cleaned = [s.strip() for s in sections if s and s.strip()]
    if not cleaned:
        raise ValueError("작성할 영역을 선택하세요. 행발과 세특은 따로 실행합니다.")
    invalid = [s for s in cleaned if s not in WRITE_SECTIONS]
    if invalid:
        raise ValueError(f"지원하지 않는 영역입니다: {', '.join(invalid)}")
    if len(cleaned) > 1:
        raise ValueError("한 번에 하나의 영역만 작성할 수 있습니다. 행발과 세특은 따로 실행하세요.")
    if _INCOMPATIBLE.issubset(cleaned):
        raise ValueError("행발과 세특은 함께 작성할 수 없습니다. 영역을 하나만 선택하세요.")
    return cleaned


def _haengbal_notes(student: StudentInput) -> str:
    return str(student.notes.get("행발") or student.notes.get("행발_notes") or "").strip()


def student_needs_section(student: StudentInput, section: str) -> bool:
    generated = student.generated or {}
    if section == "행발":
        return bool(_haengbal_notes(student)) and not str(generated.get("행발") or "").strip()
    if section == "세특":
        if not student.subjects:
            return False
        setuk = generated.get("세특") or {}
        return any(not str(setuk.get(subject) or "").strip() for subject in student.subjects)
    if section == "창체":
        if not student.changche:
            return False
        changche = generated.get("창체") or {}
        return any(notes and not str(changche.get(key) or "").strip() for key, notes in student.changche.items())
    return False


def student_sections_complete(student: StudentInput) -> bool:
    return not any(student_needs_section(student, section) for section in WRITE_SECTIONS)


def students_needing_section(students: list[StudentInput], section: str) -> list[StudentInput]:
    return [student for student in students if student_needs_section(student, section)]
