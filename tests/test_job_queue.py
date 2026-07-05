from __future__ import annotations

from pathlib import Path

import pytest

from src.saenggibu.job_queue import RunJob, create_run_job, execute_run_job, get_job, save_job


@pytest.fixture()
def jobs_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    root = tmp_path / "data" / "saenggibu" / "jobs"
    root.mkdir(parents=True)
    monkeypatch.setattr("src.saenggibu.job_queue.JOBS_DIR", root)
    return root


def test_create_and_get_job(jobs_dir: Path) -> None:
    job = create_run_job(sections=["행발"])
    loaded = get_job(job.id)
    assert loaded is not None
    assert loaded.section == "행발"
    assert loaded.status == "pending"


def test_execute_run_job_empty_batch(jobs_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.saenggibu.job_queue.list_students", lambda status=None: [])
    job = create_run_job(sections=["행발"])
    finished = execute_run_job(job.id)
    assert finished.status == "done"
    assert finished.processed == 0
    assert finished.result["mode"] == "batch"
