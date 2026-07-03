from __future__ import annotations

import re
import shutil
from io import BytesIO
from pathlib import Path

from .config import OUTPUTS_DIR, STUDENTS_DIR, ensure_data_dirs
from .io_utils import load_json, read_table_file, save_json
from .models import StudentInput, new_id


def _student_path(student_id: str) -> Path:
    return STUDENTS_DIR / f"{student_id}.json"


def list_students(*, status: str | None = None) -> list[StudentInput]:
    ensure_data_dirs()
    students: list[StudentInput] = []
    for path in sorted(STUDENTS_DIR.glob("*.json")):
        student = StudentInput.from_dict(load_json(path))
        if status is None or student.status == status:
            students.append(student)
    students.sort(key=lambda s: (s.grade, s.class_num, s.number, s.name))
    return students


def get_student(student_id: str) -> StudentInput | None:
    path = _student_path(student_id)
    if not path.exists():
        return None
    return StudentInput.from_dict(load_json(path))


def save_student(student: StudentInput) -> StudentInput:
    ensure_data_dirs()
    save_json(_student_path(student.id), student.to_dict())
    return student


def add_student(student: StudentInput) -> StudentInput:
    if not student.id:
        student.id = new_id()
    return save_student(student)


def _student_output_dir(student_id: str) -> Path:
    return OUTPUTS_DIR / student_id


def delete_student(student_id: str) -> bool:
    path = _student_path(student_id)
    if not path.exists():
        return False
    path.unlink()
    output_dir = _student_output_dir(student_id)
    if output_dir.exists():
        shutil.rmtree(output_dir, ignore_errors=True)
    return True


def delete_students(student_ids: list[str]) -> dict[str, list[str] | int]:
    deleted: list[str] = []
    not_found: list[str] = []
    for student_id in student_ids:
        if delete_student(student_id):
            deleted.append(student_id)
        else:
            not_found.append(student_id)
    return {"deleted": deleted, "not_found": not_found, "count": len(deleted)}


def delete_all_students() -> int:
    ensure_data_dirs()
    students = list_students()
    count = len(students)
    for student in students:
        delete_student(student.id)
    return count


def reset_student_generated(student: StudentInput) -> StudentInput:
    student.status = "pending"
    student.generated = {}
    student.error_message = ""
    return save_student(student)


def reset_generated_for_student(student_id: str) -> bool:
    student = get_student(student_id)
    if not student:
        return False
    if not student.generated:
        return False
    reset_student_generated(student)
    return True


def reset_generated_for_students(student_ids: list[str]) -> dict[str, list[str] | int]:
    reset: list[str] = []
    not_found: list[str] = []
    for student_id in student_ids:
        student = get_student(student_id)
        if not student:
            not_found.append(student_id)
            continue
        if student.generated:
            reset_student_generated(student)
            reset.append(student_id)
    return {"reset": reset, "not_found": not_found, "count": len(reset)}


def reset_all_generated() -> int:
    count = 0
    for student in list_students():
        if student.generated:
            reset_student_generated(student)
            count += 1
    return count


def export_students_xlsx(students: list[StudentInput] | None = None) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    rows = students if students is not None else list_students()
    subjects: list[str] = []
    seen_subjects: set[str] = set()
    for student in rows:
        for subject in (student.generated.get("세특") or {}).keys():
            if subject not in seen_subjects:
                seen_subjects.add(subject)
                subjects.append(subject)

    headers = ["학년", "반", "번호", "이름", "상태", "행발", *[
        f"세특_{subject}" for subject in subjects
    ], "자율", "동아리", "봉사", "진로"]

    wb = Workbook()
    ws = wb.active
    ws.title = "생기부"
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for student in rows:
        generated = student.generated or {}
        setuk = generated.get("세특") or {}
        changche = generated.get("창체") or {}
        ws.append([
            student.grade,
            student.class_num,
            student.number,
            student.name,
            student.status,
            str(generated.get("행발") or ""),
            *[str(setuk.get(subject) or "") for subject in subjects],
            str(changche.get("자율") or ""),
            str(changche.get("동아리") or ""),
            str(changche.get("봉사") or ""),
            str(changche.get("진로") or ""),
        ])

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _split_multi(value: str) -> list[str]:
    if not value:
        return []
    parts = re.split(r"[;|/]", value)
    return [p.strip() for p in parts if p.strip()]


def student_from_row(row: dict[str, str]) -> StudentInput:
    student_id = row.get("id", "").strip() or new_id()
    subjects: dict[str, dict[str, object]] = {}
    changche: dict[str, str] = {}
    notes: dict[str, object] = {}

    for key, value in row.items():
        if not value:
            continue
        if key.startswith("세특_") or key.startswith("subject_"):
            subject = key.split("_", 1)[1]
            subjects[subject] = {
                "activities": _split_multi(value),
                "traits": row.get(f"{subject}_traits", row.get(f"세특_{subject}_특성", "")),
                "notes": row.get(f"{subject}_notes", ""),
            }
        elif key.startswith("창체_") or key.startswith("changche_"):
            subsection = key.split("_", 1)[1]
            changche[subsection] = value
        elif key in ("행발_notes", "행발_keywords", "notes"):
            notes[key] = value
        elif key.endswith("_activities"):
            subject = key.replace("_activities", "")
            subjects.setdefault(subject, {})["activities"] = _split_multi(value)

    return StudentInput(
        id=student_id,
        name=row.get("name", row.get("이름", "")).strip(),
        grade=int(row.get("grade", row.get("학년", "1")) or 1),
        class_num=int(row.get("class_num", row.get("반", "1")) or 1),
        number=int(row.get("number", row.get("번호", "1")) or 1),
        gender=row.get("gender", row.get("성별", "")).strip(),
        status=row.get("status", "pending").strip() or "pending",
        notes={
            "행발": row.get("행발_notes", row.get("행발_메모", "")),
            "keywords": _split_multi(row.get("행발_keywords", row.get("행발_키워드", ""))),
            **notes,
        },
        subjects=subjects,
        changche={
            "자율": changche.get("자율", row.get("창체_자율", "")),
            "동아리": changche.get("동아리", row.get("창체_동아리", "")),
            "봉사": changche.get("봉사", row.get("창체_봉사", "")),
            "진로": changche.get("진로", row.get("창체_진로", "")),
        },
    )


def import_students_file(path: Path) -> list[StudentInput]:
    rows = read_table_file(path)
    imported: list[StudentInput] = []
    for row in rows:
        imported.append(add_student(student_from_row(row)))
    return imported
