from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import ROOT
from .subject_info import normalize_subject_info

CURRICULUM_DIR = ROOT / "data" / "curriculum"
DEFAULT_CURRICULUM_PATH = CURRICULUM_DIR / "dogok-2022.json"


def _normalize_subject_name(name: str) -> str:
    return re.sub(r"[\s·]+", "", name.strip().lower())


@lru_cache(maxsize=4)
def load_curriculum(path: str | None = None) -> dict[str, Any]:
    curriculum_path = Path(path) if path else DEFAULT_CURRICULUM_PATH
    if not curriculum_path.exists():
        return {"subjects": {}}
    return json.loads(curriculum_path.read_text(encoding="utf-8"))


def resolve_subject_entry(subject_name: str, curriculum: dict[str, Any] | None = None) -> dict[str, Any] | None:
    data = curriculum or load_curriculum()
    subjects = data.get("subjects") or {}
    target = _normalize_subject_name(subject_name)
    for key, entry in subjects.items():
        if _normalize_subject_name(key) == target:
            return entry
        for alias in entry.get("aliases") or []:
            if _normalize_subject_name(str(alias)) == target:
                return entry
    return None


def _tokenize(text: str) -> set[str]:
    cleaned = re.sub(r"[^\w가-힣]+", " ", text.lower())
    return {token for token in cleaned.split() if len(token) >= 2}


def _score_standard(
  *,
  standard: dict[str, str],
  unit: dict[str, Any],
  memo_tokens: set[str],
) -> float:
    score = 0.0
    blob = " ".join(
        [
            standard.get("code", ""),
            standard.get("text", ""),
            unit.get("title", ""),
            " ".join(unit.get("key_ideas") or []),
            " ".join(unit.get("keywords") or []),
            " ".join(unit.get("process_skills") or []),
        ]
    )
    blob_tokens = _tokenize(blob)
    overlap = memo_tokens & blob_tokens
    score += len(overlap) * 2.0
    if any(keyword.lower() in " ".join(memo_tokens) for keyword in unit.get("keywords") or []):
        score += 1.5
    return score


def find_relevant_standards(
    subject_name: str,
    info: dict[str, Any],
    *,
    limit: int = 3,
    curriculum: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    entry = resolve_subject_entry(subject_name, curriculum)
    if not entry:
        return []

    fields = normalize_subject_info(info)
    memo_text = " ".join(
        [
            subject_name,
            fields["career"],
            fields["assessment_type"],
            fields["topic"],
            fields["content"],
        ]
    )
    memo_tokens = _tokenize(memo_text)
    if not memo_tokens:
        return []

    ranked: list[tuple[float, dict[str, str]]] = []
    for unit in entry.get("units") or []:
        for standard in unit.get("standards") or []:
            if not isinstance(standard, dict):
                continue
            code = str(standard.get("code") or "").strip()
            text = str(standard.get("text") or "").strip()
            if not code or not text:
                continue
            score = _score_standard(standard={"code": code, "text": text}, unit=unit, memo_tokens=memo_tokens)
            if score <= 0:
                continue
            ranked.append(
                (
                    score,
                    {
                        "code": code,
                        "text": text,
                        "unit": str(unit.get("title") or ""),
                    },
                )
            )

    ranked.sort(key=lambda item: item[0], reverse=True)
    seen: set[str] = set()
    results: list[dict[str, str]] = []
    for _, item in ranked:
        if item["code"] in seen:
            continue
        seen.add(item["code"])
        results.append(item)
        if len(results) >= limit:
            break
    return results


def format_curriculum_context(standards: list[dict[str, str]]) -> str:
    if not standards:
        return ""
    lines = ["[교육과정 맥락 — 성취기준 참고, 달성 여부 단정 금지]"]
    for item in standards:
        unit = item.get("unit")
        prefix = f"({unit}) " if unit else ""
        lines.append(f"- {item['code']}: {prefix}{item['text']}")
    lines.append("위 성취기준은 수업·활동 맥락 참고용이며, 학생이 달성했다고 단정하지 마세요.")
    return "\n".join(lines)


def list_curriculum_subjects(curriculum: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    data = curriculum or load_curriculum()
    subjects = data.get("subjects") or {}
    items: list[dict[str, Any]] = []
    for name, entry in subjects.items():
        if not isinstance(entry, dict):
            continue
        items.append(
            {
                "name": name,
                "aliases": list(entry.get("aliases") or []),
                "unit_count": len(entry.get("units") or []),
            }
        )
    items.sort(key=lambda item: item["name"])
    return items


def curriculum_meta(curriculum: dict[str, Any] | None = None) -> dict[str, Any]:
    data = curriculum or load_curriculum()
    return dict(data.get("meta") or {})
