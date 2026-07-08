from __future__ import annotations

from dataclasses import dataclass

from .config import (
    get_gemini_model_fast,
    get_gemini_model_profile,
    get_gemini_model_pro,
    skip_gemini_proofread,
)


@dataclass(frozen=True)
class PlannedCall:
    step: str
    model: str
    tier: str


def resolve_model_for_tier(tier: str, profile: str | None = None) -> str:
    profile = profile or get_gemini_model_profile()
    if profile == "flash":
        return get_gemini_model_fast()
    if profile == "pro":
        return get_gemini_model_pro()
    if tier == "fast":
        return get_gemini_model_fast()
    return get_gemini_model_pro()


def plan_write_section(
    section: str,
    *,
    subject_count: int = 1,
    profile: str | None = None,
    skip_proofread: bool | None = None,
) -> list[PlannedCall]:
    profile = profile or get_gemini_model_profile()
    skip = skip_gemini_proofread() if skip_proofread is None else skip_proofread
    steps: list[PlannedCall] = []

    if section == "행발":
        steps.append(PlannedCall("행발 작성", resolve_model_for_tier("pro", profile), "pro"))
        if not skip:
            steps.append(PlannedCall("행발 맞춤법", resolve_model_for_tier("fast", profile), "fast"))
    elif section == "세특":
        for i in range(max(1, subject_count)):
            label = f"세특 작성 #{i + 1}" if subject_count > 1 else "세특 작성"
            steps.append(PlannedCall(label, resolve_model_for_tier("pro", profile), "pro"))
            if not skip:
                steps.append(
                    PlannedCall(
                        f"세특 맞춤법 #{i + 1}" if subject_count > 1 else "세특 맞춤법",
                        resolve_model_for_tier("fast", profile),
                        "fast",
                    )
                )
    elif section in ("자율", "동아리", "봉사", "진로", "창체"):
        steps.append(PlannedCall(f"{section} 작성", resolve_model_for_tier("pro", profile), "pro"))
        if not skip:
            steps.append(PlannedCall(f"{section} 맞춤법", resolve_model_for_tier("fast", profile), "fast"))
    else:
        steps.append(PlannedCall(f"{section} 작성", resolve_model_for_tier("pro", profile), "pro"))

    return steps


def summarize_plan(steps: list[PlannedCall]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for step in steps:
        counts[step.model] = counts.get(step.model, 0) + 1
    return counts
