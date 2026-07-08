from __future__ import annotations

import json

import pytest

from src.saenggibu.dev_seed import DEV_DEMO_ID, FIXTURE_PATH, seed_dev_demo_student
from src.saenggibu.student_store import get_student, list_students


def test_seed_dev_demo_skipped_without_flag(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    students_dir = tmp_path / "students"
    students_dir.mkdir()
    monkeypatch.setenv("SGB_DEV", "0")
    monkeypatch.setattr("src.saenggibu.student_store.STUDENTS_DIR", students_dir)
    assert seed_dev_demo_student() is False
    assert list_students() == []


def test_seed_dev_demo_creates_student(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    students_dir = tmp_path / "students"
    students_dir.mkdir()
    monkeypatch.setenv("SGB_DEV", "1")
    monkeypatch.setenv("SGB_ENCRYPT_DATA", "0")
    monkeypatch.setenv("SGB_STORE_GENERATED", "1")
    monkeypatch.setattr("src.saenggibu.student_store.STUDENTS_DIR", students_dir)
    assert FIXTURE_PATH.is_file()
    assert seed_dev_demo_student() is True
    student = get_student(DEV_DEMO_ID)
    assert student is not None
    assert student.name == "김테스트"
    assert student.status == "done"
    assert "행발" in student.generated
    assert "현대 사회와 윤리" in student.generated.get("세특", {})
    assert seed_dev_demo_student() is False


def test_dev_fixture_has_generated_sections() -> None:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    generated = data["generated"]
    assert generated["행발"]
    assert generated["세특"]["현대 사회와 윤리"]
    assert generated["창체"]["자율"]
