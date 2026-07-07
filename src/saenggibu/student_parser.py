from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .document_import import _docx_to_text
from .gemini_client import generate_text
from .models import StudentInput, new_id
from .student_store import add_student


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _system_prompt() -> str:
    return (
        "당신은 대한민국 고등학교 생기부 데이터 정리 도우미입니다. "
        "교사가 올린 자연어·활동지·수행평가 메모를 분석해 학생 1명분 JSON으로 구조화합니다. "
        "없는 정보는 빈 문자열·빈 배열로 두고, 추측하지 마세요. "
        "반드시 아래 스키마의 JSON만 출력하세요."
    )


def _user_prompt(raw_text: str) -> str:
    return f"""다음 내용을 학생 1명의 생기부 작성용 데이터로 정리하세요.

## 입력
{raw_text}

## 출력 JSON 스키마
{{
  "name": "이름",
  "grade": 2,
  "class_num": 3,
  "number": 12,
  "gender": "남/여 또는 빈 문자열",
  "haengbal_notes": "행동특성 작성용 관찰 메모",
  "keywords": ["키워드1", "키워드2"],
  "subjects": {{
    "현대사회와윤리": {{
      "career": "사회학과, 마케팅",
      "assessment_type": "보고서 작성, 발표",
      "topic": "마르크스의 이상사회",
      "content": "활동 내용 상세",
      "traits": "",
      "notes": ""
    }}
  }},
  "changche": {{
    "자율": "",
    "동아리": "",
    "봉사": "",
    "진로": ""
  }}
}}
"""


def _to_student(data: dict[str, Any]) -> StudentInput:
    subjects: dict[str, dict[str, Any]] = {}
    for subject, info in (data.get("subjects") or {}).items():
        if not isinstance(info, dict):
            continue
        activities = info.get("activities") or []
        if isinstance(activities, str):
            activities = [a.strip() for a in re.split(r"[;|/]", activities) if a.strip()]
        subjects[str(subject)] = {
            "career": str(info.get("career", "")).strip(),
            "assessment_type": str(info.get("assessment_type", info.get("assessment", ""))).strip(),
            "topic": str(info.get("topic", "")).strip(),
            "content": str(info.get("content", "")).strip(),
            "activities": activities,
            "traits": str(info.get("traits", "")).strip(),
            "notes": str(info.get("notes", info.get("content", ""))).strip(),
        }

    keywords = data.get("keywords") or []
    if isinstance(keywords, str):
        keywords = [k.strip() for k in re.split(r"[;|,]", keywords) if k.strip()]

    return StudentInput(
        id=new_id(),
        name=str(data.get("name", "")).strip(),
        grade=int(data.get("grade") or 1),
        class_num=int(data.get("class_num") or 1),
        number=int(data.get("number") or 1),
        gender=str(data.get("gender", "")).strip(),
        notes={
            "행발": str(data.get("haengbal_notes", data.get("행발_notes", ""))).strip(),
            "keywords": keywords,
        },
        subjects=subjects,
        changche={k: str(v) for k, v in (data.get("changche") or {}).items()},
    )


def parse_text_to_student(raw_text: str) -> StudentInput:
    raw_text = raw_text.strip()
    if len(raw_text) < 20:
        raise ValueError("내용이 너무 짧습니다. 학생 이름·활동·수행평가 메모를 조금 더 적어 주세요.")

    response = generate_text(system=_system_prompt(), user=_user_prompt(raw_text), temperature=0.1, tier="fast")
    data = _extract_json(response)
    student = _to_student(data)
    if not student.name:
        raise ValueError("학생 이름을 찾지 못했습니다. 이름을 명시해 주세요.")
    return student


def parse_file_to_student(path: Path) -> StudentInput:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return parse_text_to_student(path.read_text(encoding="utf-8"))
    if suffix == ".docx":
        return parse_text_to_student(_docx_to_text(path))
    if suffix in {".tsv", ".csv"}:
        return parse_text_to_student(path.read_text(encoding="utf-8"))
    raise ValueError(f"AI 자동 등록에 지원하지 않는 형식: {suffix}")


def parse_and_save(raw_text: str) -> StudentInput:
    return add_student(parse_text_to_student(raw_text))
