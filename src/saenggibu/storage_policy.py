from __future__ import annotations

import os
from typing import Any

from .models import StudentInput


def store_generated_on_server() -> bool:
    return os.getenv("SGB_STORE_GENERATED", "0").strip().lower() in ("1", "true", "yes")


def student_dict_for_disk(student: StudentInput) -> dict[str, Any]:
    data = student.to_dict()
    if not store_generated_on_server():
        data["generated"] = {}
        if student.generated and student.status in ("done", "partial"):
            data["status"] = "pending"
    return data


def merge_generated_for_response(student: StudentInput, generated: dict[str, Any] | None) -> StudentInput:
    if store_generated_on_server() or not generated:
        return student
    student.generated = generated
    if generated:
        from .write_sections import student_sections_complete

        student.status = "done" if student_sections_complete(student) else "partial"
    return student
