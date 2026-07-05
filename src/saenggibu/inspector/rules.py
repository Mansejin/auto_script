from __future__ import annotations

import re
from typing import Any

from ..config import CHANGCHE_SUBSECTIONS
from ..pattern_analyzer import load_patterns

# NEIS·기재요령 기본 분량 (샘플 분석 없을 때)
DEFAULT_CHAR_LIMITS: dict[str, dict[str, int]] = {
    "행발": {"min": 400, "max": 700, "hard_max": 750},
    "세특": {"min": 300, "max": 500, "hard_max": 500},
    "창체": {"min": 100, "max": 300, "hard_max": 350},
}

# 금지·주의 표현 (prompts/saenggibu.md 기반)
FORBIDDEN_PATTERNS: list[tuple[str, str, str]] = [
    (r"석차|등수|\d+\s*등|\d+\s*위", "ranking", "순위·석차 언급은 기재할 수 없습니다."),
    (r"\d+\s*점", "score", "평가 점수는 기재하지 않습니다."),
    (r"사교육|학원|과외|인강", "private_education", "사교육 유무는 기재하지 않습니다."),
    (r"가정환경|경제적\s*어려움|부모님\s*직업|맞벌이|한부모", "family", "가정환경·가족 사정은 기재하지 않습니다."),
    (r"외모|키가|몸무게|잘생|예쁘", "appearance", "외모 관련 기재는 피합니다."),
    (r"우울|자해|정신과|ADHD|장애", "health_sensitive", "건강·정신 민감 정보는 신중히 다루어야 합니다."),
]

WARNING_PATTERNS: list[tuple[str, str, str]] = [
    (r"최고|최상|1등|탁월|뛰어난|우수한|뛰어남", "exaggeration", "과장·평가적 형용사가 많습니다."),
    (r"다른\s*학생|타\s*학생|반\s*에서\s*유일", "comparison", "다른 학생과의 비교 표현이 있습니다."),
    (r"반드시|확실히|틀림없이", "speculation", "추측·단정적 표현이 있습니다."),
]

EXAGGERATION_THRESHOLD = 3


def char_len(text: str) -> int:
    return len(text.strip())


def section_kind(section_key: str) -> str:
    if section_key == "행발":
        return "행발"
    if section_key.startswith("세특:"):
        return "세특"
    if section_key.startswith("창체:"):
        return "창체"
    return section_key.split(":", 1)[0]


def get_char_limits(section_key: str) -> dict[str, int]:
    kind = section_kind(section_key)
    patterns = load_patterns() or {}
    sections = patterns.get("sections") or {}

    if kind == "세특" and ":" in section_key:
        subject = section_key.split(":", 1)[1]
        setuk = sections.get("세특")
        if isinstance(setuk, dict) and subject in setuk:
            cc = setuk[subject].get("char_count") or {}
            if cc:
                return {
                    "min": int(cc.get("min", DEFAULT_CHAR_LIMITS["세특"]["min"])),
                    "max": int(cc.get("max", DEFAULT_CHAR_LIMITS["세특"]["max"])),
                    "hard_max": int(cc.get("max", DEFAULT_CHAR_LIMITS["세특"]["hard_max"])),
                }

    info = sections.get(kind)
    if isinstance(info, dict) and "char_count" in info:
        cc = info["char_count"]
        return {
            "min": int(cc.get("min", DEFAULT_CHAR_LIMITS[kind]["min"])),
            "max": int(cc.get("max", DEFAULT_CHAR_LIMITS[kind]["max"])),
            "hard_max": int(cc.get("max", DEFAULT_CHAR_LIMITS.get(kind, DEFAULT_CHAR_LIMITS["창체"])["hard_max"])),
        }

    return dict(DEFAULT_CHAR_LIMITS.get(kind, DEFAULT_CHAR_LIMITS["창체"]))


def iter_generated_fields(generated: dict[str, Any]) -> list[tuple[str, str]]:
    """(section_key, text) — 예: ('행발', '...'), ('세특:수학', '...')."""
    if not generated:
        return []

    fields: list[tuple[str, str]] = []
    haengbal = str(generated.get("행발") or "").strip()
    if haengbal:
        fields.append(("행발", haengbal))

    setuk = generated.get("세특") or {}
    if isinstance(setuk, dict):
        for subject, text in setuk.items():
            cleaned = str(text or "").strip()
            if cleaned:
                fields.append((f"세특:{subject}", cleaned))

    changche = generated.get("창체") or {}
    if isinstance(changche, dict):
        for key in CHANGCHE_SUBSECTIONS:
            cleaned = str(changche.get(key) or "").strip()
            if cleaned:
                fields.append((f"창체:{key}", cleaned))
        for key, text in changche.items():
            if key in CHANGCHE_SUBSECTIONS:
                continue
            cleaned = str(text or "").strip()
            if cleaned:
                fields.append((f"창체:{key}", cleaned))

    return fields


def find_pattern_matches(text: str, patterns: list[tuple[str, str, str]]) -> list[tuple[str, str, str, re.Match[str]]]:
    matches: list[tuple[str, str, str, re.Match[str]]] = []
    for pattern, code, message in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            matches.append((pattern, code, message, match))
    return matches
