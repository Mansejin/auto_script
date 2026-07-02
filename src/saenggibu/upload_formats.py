"""업로드 허용 확장자 (API·UI 공통 기준)."""

from __future__ import annotations

from pathlib import Path

SAMPLE_EXTENSIONS = frozenset({".json", ".tsv", ".csv", ".xlsx", ".docx"})
STUDENT_EXTENSIONS = frozenset({".tsv", ".csv", ".txt"})


def check_upload_extension(filename: str | None, allowed: frozenset[str]) -> None:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in allowed:
        labels = ", ".join(sorted(ext.lstrip(".") for ext in allowed))
        ext_label = suffix or "(확장자 없음)"
        raise ValueError(f"지원하지 않는 형식입니다 {ext_label}. 사용 가능: {labels}")
