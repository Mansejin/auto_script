from __future__ import annotations

import base64
import json
import os
from pathlib import Path

import pytest

from src.saenggibu.data_crypto import decrypt_json, encrypt_json, encrypt_data_enabled
from src.saenggibu.secure_io import load_secure_json, save_secure_json


@pytest.fixture()
def data_key(monkeypatch: pytest.MonkeyPatch) -> bytes:
    key = os.urandom(32)
    monkeypatch.setenv("SGB_DATA_KEY", base64.urlsafe_b64encode(key).decode())
    monkeypatch.setenv("SGB_ENCRYPT_DATA", "1")
    return key


def test_encrypt_decrypt_roundtrip(data_key: bytes) -> None:
    payload = {"name": "김민수", "notes": {"행발": "메모"}}
    wrapper = encrypt_json(payload)
    assert wrapper["__enc"] == "v1"
    restored = decrypt_json(wrapper)
    assert restored == payload


def test_secure_io_plain_when_encryption_disabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SGB_ENCRYPT_DATA", "0")
    path = tmp_path / "data.json"
    save_secure_json(path, {"hello": "world"})
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert "__enc" not in raw
    assert load_secure_json(path) == {"hello": "world"}


def test_secure_io_encrypted_when_enabled(data_key: bytes, tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    save_secure_json(path, {"secret": "value"})
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw.get("__enc") == "v1"
    assert load_secure_json(path) == {"secret": "value"}
    assert encrypt_data_enabled() is True
