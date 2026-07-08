from __future__ import annotations

from dataclasses import dataclass

from .config import get_gemini_model_fast, get_gemini_model_pro


@dataclass(frozen=True)
class PlannedCall:
    step: str
    model: str
    tier: str


def plan_sample_analysis() -> list[PlannedCall]:
    return [PlannedCall("샘플 스타일 가이드", get_gemini_model_pro(), "pro")]


def plan_write_section(section: str, *, subject_count: int = 1) -> list[PlannedCall]:
    model = get_gemini_model_fast()
    steps: list[PlannedCall] = []

    if section == "행발":
        steps.append(PlannedCall("행발 작성", model, "fast"))
    elif section == "세특":
        for i in range(max(1, subject_count)):
            label = f"세특 작성 #{i + 1}" if subject_count > 1 else "세특 작성"
            steps.append(PlannedCall(label, model, "fast"))
    elif section in ("자율", "동아리", "봉사", "진로", "창체"):
        steps.append(PlannedCall(f"{section} 작성", model, "fast"))
    else:
        steps.append(PlannedCall(f"{section} 작성", model, "fast"))

    return steps


def summarize_plan(steps: list[PlannedCall]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for step in steps:
        counts[step.model] = counts.get(step.model, 0) + 1
    return counts
