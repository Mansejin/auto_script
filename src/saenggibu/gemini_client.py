from __future__ import annotations

import logging
import os
import time
from typing import Any

from google import genai
from google.genai import types

from .api_errors import friendly_api_error
from .config import get_gemini_api_key, get_gemini_model
from .pii_mask import mask_for_ai

logger = logging.getLogger(__name__)

_RETRYABLE_MARKERS = (
    "503",
    "429",
    "unavailable",
    "resource_exhausted",
    "high demand",
    "rate limit",
    "capacity",
    "deadline",
    "timeout",
)

_last_call_at = 0.0


def _min_interval_sec() -> float:
    raw = os.getenv("GEMINI_MIN_INTERVAL_SEC", "2").strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 2.0


def _throttle() -> None:
    global _last_call_at
    interval = _min_interval_sec()
    if interval <= 0:
        return
    now = time.monotonic()
    wait = interval - (now - _last_call_at)
    if wait > 0:
        time.sleep(wait)
    _last_call_at = time.monotonic()


def _retry_sleep(attempt: int, exc: BaseException) -> float:
    text = str(exc).lower()
    if "429" in text or "rate limit" in text or "resource_exhausted" in text:
        return min(30.0, 5.0 * attempt)
    return min(12.0, 2.0 ** attempt)


def _client() -> genai.Client:
    return genai.Client(api_key=get_gemini_api_key())


def _is_retryable(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _RETRYABLE_MARKERS)


def generate_text(
    *,
    system: str,
    user: str,
    temperature: float = 0.4,
    student_names: list[str] | None = None,
    max_attempts: int = 4,
) -> str:
    client = _client()
    safe_user = mask_for_ai(user, student_names=student_names)
    safe_system = mask_for_ai(system, student_names=student_names)
    last_exc: BaseException | None = None

    for attempt in range(1, max_attempts + 1):
        _throttle()
        try:
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
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "Gemini call failed (attempt %s/%s, model=%s): %s",
                attempt,
                max_attempts,
                get_gemini_model(),
                exc,
            )
            if attempt >= max_attempts or not _is_retryable(exc):
                break
            time.sleep(_retry_sleep(attempt, exc))

    assert last_exc is not None
    raise RuntimeError(friendly_api_error(last_exc)) from last_exc


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
