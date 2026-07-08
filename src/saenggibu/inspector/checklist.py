from __future__ import annotations

from typing import Any, Literal

from .issues import InspectIssue, InspectReport

CheckStatus = Literal["pass", "warn", "fail", "skip", "pending"]

INSPECT_CATEGORIES: list[dict[str, Any]] = [
    {
        "id": "char_count",
        "label": "NEIS 용량(바이트)",
        "description": "행발 900byte, 세특·창체 1500byte (neis-counter 규칙)",
        "codes": {"char_count_over", "char_count_high", "char_count_low"},
    },
    {
        "id": "forbidden",
        "label": "금지 표현",
        "description": "석차·점수·사교육·가정환경·외모·민감정보",
        "codes": {
            "ranking",
            "score",
            "private_education",
            "family",
            "appearance",
            "health_sensitive",
        },
    },
    {
        "id": "tone",
        "label": "과장·비교·단정",
        "description": "최고·탁월·다른 학생 비교·추측 표현",
        "codes": {"exaggeration", "comparison", "speculation"},
    },
    {
        "id": "real_name",
        "label": "실명 노출",
        "description": "학생 실명 대신 「학생」「OO」 권장",
        "codes": {"real_name"},
    },
    {
        "id": "duplicate",
        "label": "문장 반복",
        "description": "동일·유사 문장 중복",
        "codes": {"duplicate_sentence"},
    },
]


def _severity_rank(severity: str) -> int:
    return {"error": 3, "warning": 2, "info": 1}.get(severity, 0)


def _status_from_issues(issues: list[InspectIssue]) -> CheckStatus:
    if not issues:
        return "pass"
    if any(issue.severity == "error" for issue in issues):
        return "fail"
    if any(issue.severity == "warning" for issue in issues):
        return "warn"
    return "pass"


def build_inspect_checklist(report: InspectReport) -> list[dict[str, Any]]:
    if not report.char_count and not report.issues:
        return [
            {
                **category,
                "status": "skip",
                "message": "작성본이 없어 검사하지 않았습니다.",
            }
            for category in INSPECT_CATEGORIES
        ]

    checklist: list[dict[str, Any]] = []
    for category in INSPECT_CATEGORIES:
        codes = category["codes"]
        matched = [issue for issue in report.issues if issue.code in codes]
        status = _status_from_issues(matched)
        message = "통과"
        if matched:
            worst = max(matched, key=lambda issue: _severity_rank(issue.severity))
            message = worst.message
        checklist.append(
            {
                "id": category["id"],
                "label": category["label"],
                "description": category["description"],
                "status": status,
                "message": message,
                "issue_count": len(matched),
            }
        )
    return checklist
