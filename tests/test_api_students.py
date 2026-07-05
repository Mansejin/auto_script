from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.web.app import create_app


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    monkeypatch.setenv("ADMIN_PASSWORD", "testpass")
    monkeypatch.setenv("ADMIN_SESSION_SECRET", "test-secret-key-for-session-signing")
    monkeypatch.setenv("SGB_ENCRYPT_DATA", "0")

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
    response = client.post("/api/auth/login", json={"password": "testpass"})
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_student_short_setuk_content(client: TestClient) -> None:
    headers = _auth_headers(client)
    payload = {
        "name": "김민수",
        "grade": 2,
        "class_num": 1,
        "number": 3,
        "subjects": {
            "현대사회와윤리": {
                "content": "짧음",
                "activities": ["짧음"],
                "notes": "짧음",
            }
        },
        "changche": {},
        "write_targets": ["세특"],
    }
    response = client.post("/api/students", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "김민수"
    assert "현대사회와윤리" in data["subjects"]
