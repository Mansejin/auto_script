from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .data_crypto import decrypt_json, encrypt_data_enabled, encrypt_json


def load_secure_json(path: Path) -> Any:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if isinstance(data, dict) and data.get("__enc"):
        return decrypt_json(data)
    return data


def save_secure_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if encrypt_data_enabled():
        payload = encrypt_json(data)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
