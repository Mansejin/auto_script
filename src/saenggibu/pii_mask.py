from __future__ import annotations

import os
import re

MaskRule = tuple[str, re.Pattern[str], str]

# Gemini 전송 전 마스킹 (왓퀴즈 PII 마스킹 벤치마크)
_MASK_RULES: list[MaskRule] = [
    (
        "phone",
        re.compile(
            r"(?<!\d)"
            r"(?:"
            r"01[016789][-\s]?\d{3,4}[-\s]?\d{4}"
            r"|0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4}"
            r")"
            r"(?!\d)"
        ),
        "[전화번호]",
    ),
    (
        "email",
        re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
        "[이메일]",
    ),
    (
        "rrn",
        re.compile(r"\d{6}[-\s]?\d{7}"),
        "[주민등록번호]",
    ),
    (
        "address",
        re.compile(
            r"(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)"
            r"(?:특별시|광역시|도)?\s*"
            r"[^\s,]{1,20}(?:시|군|구)\s*"
            r"[^\s,]{1,40}(?:동|읍|면|로|길)\s*\d*"
        ),
        "[주소]",
    ),
]


def mask_pii_enabled() -> bool:
    return os.getenv("SGB_MASK_PII", "1").strip().lower() not in ("0", "false", "no")


def mask_student_names_enabled() -> bool:
    return os.getenv("SGB_MASK_STUDENT_NAMES", "0").strip().lower() in ("1", "true", "yes")


def mask_text(text: str, *, extra_replacements: list[tuple[re.Pattern[str], str]] | None = None) -> str:
    if not text:
        return text
    masked = text
    for _name, pattern, token in _MASK_RULES:
        masked = pattern.sub(token, masked)
    for pattern, token in extra_replacements or []:
        masked = pattern.sub(token, masked)
    return masked


def mask_for_ai(
    text: str,
    *,
    student_names: list[str] | None = None,
) -> str:
    if not mask_pii_enabled():
        return text
    extra: list[tuple[re.Pattern[str], str]] = []
    if mask_student_names_enabled() and student_names:
        for name in student_names:
            cleaned = name.strip()
            if len(cleaned) >= 2:
                extra.append((re.compile(re.escape(cleaned)), "학생"))
    return mask_text(text, extra_replacements=extra or None)


def mask_summary(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name, pattern, _token in _MASK_RULES:
        counts[name] = len(pattern.findall(text))
    return {key: value for key, value in counts.items() if value}
