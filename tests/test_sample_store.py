from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.saenggibu import sample_store
from src.saenggibu.sample_store import (
    add_sample,
    delete_sample,
    list_samples,
    reconcile_sample_index,
)
from src.saenggibu.models import SampleRecord


@pytest.fixture
def samples_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "samples"
    path.mkdir()
    monkeypatch.setattr(sample_store, "SAMPLES_DIR", path)
    return path


def test_reconcile_removes_ghost_without_json_or_sections(samples_dir: Path) -> None:
    index_path = samples_dir / "index.json"
    index_path.write_text(
        json.dumps(
            [
                {"id": "sample63ee8476", "label": "", "sections": {}},
                {
                    "id": "samplealive01",
                    "label": "ok",
                    "sections": {"행발": "내용 있음"},
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    removed = reconcile_sample_index()
    assert removed == ["sample63ee8476"]
    items = json.loads(index_path.read_text(encoding="utf-8"))
    assert len(items) == 1
    assert items[0]["id"] == "samplealive01"


def test_list_samples_auto_prunes_ghosts(samples_dir: Path) -> None:
    index_path = samples_dir / "index.json"
    index_path.write_text(
        json.dumps([{"id": "sampleghost99", "label": "미명시", "sections": {}}]),
        encoding="utf-8",
    )

    assert list_samples() == []
    assert json.loads(index_path.read_text(encoding="utf-8")) == []


def test_delete_sample_works_when_only_index_entry_exists(samples_dir: Path) -> None:
    record = SampleRecord(id="sampledel01", label="del", sections={"행발": "x"})
    add_sample(record)
    (samples_dir / "sampledel01.json").unlink()

    assert delete_sample("sampledel01") is True
    assert list_samples() == []


def test_delete_sample_works_when_only_json_exists(samples_dir: Path) -> None:
    record = SampleRecord(id="samplejson01", label="json", sections={"행발": "y"})
    add_sample(record)
    index_path = samples_dir / "index.json"
    index_path.write_text("[]", encoding="utf-8")

    assert delete_sample("samplejson01") is True
    assert not (samples_dir / "samplejson01.json").exists()
