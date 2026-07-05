from __future__ import annotations

from typing import Any

from google import genai
from google.genai import types

from .config import get_gemini_api_key, get_gemini_model
from .pii_mask import mask_for_ai


def _client() -> genai.Client:
    return genai.Client(api_key=get_gemini_api_key())


def generate_text(
    *,
    system: str,
    user: str,
    temperature: float = 0.4,
    student_names: list[str] | None = None,
) -> str:
    client = _client()
    safe_user = mask_for_ai(user, student_names=student_names)
    safe_system = mask_for_ai(system, student_names=student_names)
    response = client.models.generate_content(
        model=get_gemini_model(),
        contents=safe_user,
        config=types.GenerateContentConfig(
            system_instruction=safe_system,
            temperature=temperature,
        ),
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini가 빈 응답을 반환했습니다.")
    return text


def refine_style_guide(patterns: dict[str, Any], draft_guide: str) -> str:
    system = (
        "당신은 대한민국 고등학교 생활기록부(생기부) 작성 전문가입니다. "
        "제공된 통계와 예시 문장을 바탕으로, 이후 AI가 동일한 톤·문체·분량으로 "
        "생기부를 작성할 수 있도록 구체적인 스타일 가이드를 한국어로 정리하세요. "
        "금지 표현(과장, 허위, 평가적 형용사 남발)과 권장 문장 패턴도 포함하세요."
    )
    user = (
        f"## 통계\n{patterns}\n\n"
        f"## 초안 가이드\n{draft_guide}\n\n"
        "위 내용을 하나의 실행 가능한 스타일 가이드로 다듬어 주세요."
    )
    return generate_text(system=system, user=user, temperature=0.2)
