from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.saenggibu import usage as usage_mod


def test_free_limit_empty_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SGB_FREE_GENERATIONS", "")
    assert usage_mod._free_limit() == 10


def test_free_limit_invalid_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SGB_FREE_GENERATIONS", "many")
    assert usage_mod._free_limit() == 10


def test_load_usage_corrupt_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    usage_path = tmp_path / "usage.json"
    usage_path.write_text("{not-json", encoding="utf-8")
    monkeypatch.setattr(usage_mod, "USAGE_PATH", usage_path)
    data = usage_mod.load_usage()
    assert data["generations"] == 0


def test_load_usage_encrypted_without_decrypt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    usage_path = tmp_path / "usage.json"
    usage_path.write_text(json.dumps({"__enc": "v1", "payload": "abc"}), encoding="utf-8")
    monkeypatch.setattr(usage_mod, "USAGE_PATH", usage_path)
    data = usage_mod.load_usage()
    assert data["generations"] == 0
