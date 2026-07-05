from __future__ import annotations

from src.saenggibu.curriculum import list_curriculum_subjects
from src.saenggibu.writing_guides import get_writing_guide


def test_list_curriculum_subjects() -> None:
    subjects = list_curriculum_subjects()
    names = {item["name"] for item in subjects}
    assert "현대사회와윤리" in names


def test_writing_guide_section() -> None:
    guide = get_writing_guide("세특")
    assert guide["section"]["title"] == "세부능력 및 특기사항"
    assert guide["common"]["checklist"]


def test_writing_guide_changche_alias() -> None:
    guide = get_writing_guide("자율")
    assert guide["section_key"] == "창체"
