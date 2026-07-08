from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.web.app import create_app


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    monkeypatch.setenv("ADMIN_PASSWORD", "testpass")
    monkeypatch.setenv("ADMIN_SESSION_SECRET", "test-secret-key-for-session-signing")
    monkeypatch.setenv("SGB_ENCRYPT_DATA", "0")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test-model")

    from src.saenggibu import config
    import src.saenggibu.student_store as student_store
    import src.saenggibu.sample_store as sample_store
    import src.saenggibu.job_queue as job_queue
    import src.saenggibu.usage as usage_mod

    config.DATA_DIR = tmp_path
    config.STUDENTS_DIR = tmp_path / "students"
    config.SAMPLES_DIR = tmp_path / "samples"
    config.OUTPUTS_DIR = tmp_path / "outputs"
    config.JOBS_DIR = tmp_path / "jobs"
    config.PATTERNS_PATH = tmp_path / "patterns.json"
    student_store.STUDENTS_DIR = config.STUDENTS_DIR
    student_store.OUTPUTS_DIR = config.OUTPUTS_DIR
    sample_store.SAMPLES_DIR = config.SAMPLES_DIR
    job_queue.JOBS_DIR = config.JOBS_DIR
    usage_mod.USAGE_PATH = tmp_path / "usage.json"

    return TestClient(create_app())


def _auth_headers(client: TestClient) -> dict[str, str]:
    res = client.post("/api/auth/login", json={"password": "testpass"})
    assert res.status_code == 200
    token = res.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_auth_me_returns_gemini_model(client: TestClient) -> None:
    res = client.get("/api/auth/me", headers=_auth_headers(client))
    assert res.status_code == 200
    data = res.json()
    assert data["gemini_model"] == "gemini-test-model"
    assert data["gemini_model_pro"] == "gemini-test-model"
    assert data["gemini_model_fast"] == "gemini-2.5-flash"
    assert data["gemini_model_profile"] == "split"
