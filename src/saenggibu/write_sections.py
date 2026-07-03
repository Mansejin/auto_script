from __future__ import annotations

from .config import CHANGCHE_SUBSECTIONS
from .models import StudentInput

# 등록·일괄 작성에 쓰는 영역 (창체는 소분류별로 분리)
WRITE_SECTIONS = ("행발", "세특", *CHANGCHE_SUBSECTIONS)
REGISTRATION_TARGETS = ("행발", "세특", "자율", "동아리", "진로")


def normalize_write_sections(sections: list[str] | None) -> list[str]:
    if not sections:
        raise ValueError("작성할 영역을 선택하세요.")
    cleaned = [s.strip() for s in sections if s and s.strip()]
    if not cleaned:
        raise ValueError("작성할 영역을 선택하세요.")
    if cleaned == ["창체"]:
        raise ValueError("자율·동아리·진로·봉사 중 하나를 선택하세요.")
    invalid = [s for s in cleaned if s not in WRITE_SECTIONS]
    if invalid:
        raise ValueError(f"지원하지 않는 영역입니다: {', '.join(invalid)}")
    if len(cleaned) > 1:
        raise ValueError("한 번에 하나의 영역만 작성할 수 있습니다.")
    return cleaned


def _haengbal_notes(student: StudentInput) -> str:
    return str(student.notes.get("행발") or student.notes.get("행발_notes") or "").strip()


def student_write_targets(student: StudentInput) -> list[str]:
    raw = student.notes.get("write_targets")
    if isinstance(raw, list) and raw:
        return [str(item) for item in raw if str(item) in WRITE_SECTIONS]
    inferred: list[str] = []
    if _haengbal_notes(student):
        inferred.append("행발")
    if student.subjects:
        inferred.append("세특")
    for key in CHANGCHE_SUBSECTIONS:
        if str(student.changche.get(key) or "").strip():
            inferred.append(key)
    return inferred


def _targets_include(student: StudentInput, section: str) -> bool:
    targets = student_write_targets(student)
    return not targets or section in targets


def student_needs_section(student: StudentInput, section: str) -> bool:
    if not _targets_include(student, section):
        return False
    generated = student.generated or {}
    if section == "행발":
        return bool(_haengbal_notes(student)) and not str(generated.get("행발") or "").strip()
    if section == "세특":
        if not student.subjects:
            return False
        setuk = generated.get("세특") or {}
        return any(not str(setuk.get(subject) or "").strip() for subject in student.subjects)
    if section in CHANGCHE_SUBSECTIONS:
        notes = str(student.changche.get(section) or "").strip()
        if not notes:
            return False
        changche = generated.get("창체") or {}
        return not str(changche.get(section) or "").strip()
    return False


def student_sections_complete(student: StudentInput) -> bool:
    targets = student_write_targets(student)
    if not targets:
        return False
    return not any(student_needs_section(student, section) for section in targets)


def students_needing_section(students: list[StudentInput], section: str) -> list[StudentInput]:
    return [student for student in students if student_needs_section(student, section)]
