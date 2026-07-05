from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Severity = Literal["error", "warning", "info"]


@dataclass
class InspectIssue:
    section: str
    code: str
    severity: Severity
    message: str
    detail: str = ""
    offset: int | None = None


@dataclass
class InspectReport:
    student_id: str | None = None
    student_label: str = ""
    char_count: dict[str, int] = field(default_factory=dict)
    issues: list[InspectIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "info")

    @property
    def status(self) -> str:
        if self.error_count:
            return "fail"
        if self.warning_count:
            return "warn"
        return "ok"


def issue_to_dict(issue: InspectIssue) -> dict[str, Any]:
    return asdict(issue)


def report_to_dict(report: InspectReport) -> dict[str, Any]:
    from .checklist import build_inspect_checklist

    return {
        "student_id": report.student_id,
        "student_label": report.student_label,
        "char_count": report.char_count,
        "status": report.status,
        "error_count": report.error_count,
        "warning_count": report.warning_count,
        "info_count": report.info_count,
        "issues": [issue_to_dict(issue) for issue in report.issues],
        "checklist": build_inspect_checklist(report),
    }
