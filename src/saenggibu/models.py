from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4


def new_id(prefix: str = "s") -> str:
    return f"{prefix}{uuid4().hex[:8]}"


@dataclass
class SampleRecord:
    """과거 작성 완료 생기부 샘플 (패턴 학습용)."""

    id: str
    label: str
    grade: int | None = None
    school_year: str = ""
    sections: dict[str, Any] = field(default_factory=dict)
    source_file: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SampleRecord:
        return cls(
            id=data.get("id") or new_id("sample"),
            label=data.get("label", data.get("student_label", "미명시")),
            grade=data.get("grade"),
            school_year=data.get("school_year", ""),
            sections=data.get("sections", {}),
            source_file=data.get("source_file", ""),
        )


@dataclass
class StudentInput:
    """학생 원천 정보 (작성 전 데이터)."""

    id: str
    name: str
    grade: int
    class_num: int
    number: int
    gender: str = ""
    status: str = "pending"  # pending | partial | done | error | in_progress
    notes: dict[str, Any] = field(default_factory=dict)
    subjects: dict[str, dict[str, Any]] = field(default_factory=dict)
    changche: dict[str, str] = field(default_factory=dict)
    generated: dict[str, Any] = field(default_factory=dict)
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StudentInput:
        return cls(
            id=data.get("id") or new_id(),
            name=data.get("name", ""),
            grade=int(data.get("grade", 1)),
            class_num=int(data.get("class_num", 1)),
            number=int(data.get("number", 1)),
            gender=data.get("gender", ""),
            status=data.get("status", "pending"),
            notes=data.get("notes", {}),
            subjects=data.get("subjects", {}),
            changche=data.get("changche", {}),
            generated=data.get("generated", {}),
            error_message=data.get("error_message", ""),
        )

    @property
    def display_name(self) -> str:
        return f"{self.grade}-{self.class_num} {self.number}번 {self.name}"
