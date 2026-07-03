#!/usr/bin/env python3
"""기존 평문 JSON 학생·샘플 파일을 암호화 형식으로 변환합니다."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.saenggibu.config import SAMPLES_DIR, STUDENTS_DIR, ensure_data_dirs
from src.saenggibu.data_crypto import ENC_MARKER, encrypt_data_enabled
from src.saenggibu.secure_io import load_secure_json, save_secure_json


def _migrate_dir(directory: Path, label: str) -> tuple[int, int]:
    converted = 0
    skipped = 0
    for path in sorted(directory.glob("*.json")):
        raw = path.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            skipped += 1
            continue
        if isinstance(data, dict) and data.get(ENC_MARKER):
            skipped += 1
            continue
        save_secure_json(path, data)
        converted += 1
        print(f"  [{label}] {path.name}")
    return converted, skipped


def main() -> int:
    if not encrypt_data_enabled():
        print("SGB_ENCRYPT_DATA=1 이고 SGB_DATA_KEY가 설정되어 있어야 합니다.", file=sys.stderr)
        return 1

    ensure_data_dirs()
    total = 0
    for directory, label in ((STUDENTS_DIR, "students"), (SAMPLES_DIR, "samples")):
        if not directory.exists():
            continue
        converted, skipped = _migrate_dir(directory, label)
        total += converted
        print(f"{label}: converted={converted}, skipped={skipped}")

    if total == 0:
        print("변환할 평문 파일이 없습니다.")
    else:
        print(f"완료: {total}개 파일 암호화")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
