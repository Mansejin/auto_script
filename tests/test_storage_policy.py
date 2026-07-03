from __future__ import annotations

from pathlib import Path

import pytest

from src.saenggibu.models import StudentInput
from src.saenggibu.storage_policy import store_generated_on_server, student_dict_for_disk


def test_store_generated_defaults_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SGB_STORE_GENERATED", raising=False)
    assert store_generated_on_server() is False


def test_student_dict_for_disk_strips_generated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SGB_STORE_GENERATED", "0")
    student = StudentInput(
        id="stu001",
        name="A",
        grade=1,
        class_num=1,
        number=1,
        generated={"행발": "본문"},
        status="done",
    )
    data = student_dict_for_disk(student)
    assert data["generated"] == {}
    assert data["status"] == "pending"


def test_student_dict_for_disk_keeps_generated_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SGB_STORE_GENERATED", "1")
    student = StudentInput(
        id="stu001",
        name="A",
        grade=1,
        class_num=1,
        number=1,
        generated={"행발": "본문"},
        status="done",
    )
    data = student_dict_for_disk(student)
    assert data["generated"]["행발"] == "본문"
    assert data["status"] == "done"
