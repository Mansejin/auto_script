from __future__ import annotations

import logging
import os
import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Literal

from google import genai
from google.genai import types

from .api_errors import friendly_api_error
from .config import get_gemini_api_key, get_gemini_model_pro
from .pii_mask import mask_for_ai

logger = logging.getLogger(__name__)

ModelTier = Literal["pro"]

_last_call_at = 0.0
_usage_log: list["GeminiUsage"] = []


@dataclass(frozen=True)
class GeminiUsage:
    model: str
    tier: str
    prompt_tokens: int
    output_tokens: int
    total_tokens: int
    thoughts_tokens: int = 0


def clear_usage_log() -> None:
    _usage_log.clear()


def get_usage_log() -> list[GeminiUsage]:
    return list(_usage_log)


def summarize_usage_log() -> dict[str, Any]:
    calls = get_usage_log()
    totals = {
        "calls": len(calls),
        "prompt_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "thoughts_tokens": 0,
    }
    by_model: dict[str, dict[str, int]] = {}
    for entry in calls:
        totals["prompt_tokens"] += entry.prompt_tokens
        totals["output_tokens"] += entry.output_tokens
        totals["total_tokens"] += entry.total_tokens
        totals["thoughts_tokens"] += entry.thoughts_tokens
        bucket = by_model.setdefault(
            entry.model,
            {"calls": 0, "prompt_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        )
        bucket["calls"] += 1
        bucket["prompt_tokens"] += entry.prompt_tokens
        bucket["output_tokens"] += entry.output_tokens
        bucket["total_tokens"] += entry.total_tokens
    return {"totals": totals, "by_model": by_model, "calls": [asdict(c) for c in calls]}


def _parse_usage_metadata(response: Any, *, model: str, tier: str) -> GeminiUsage | None:
    meta = getattr(response, "usage_metadata", None)
    if meta is None:
        return None
    prompt = int(getattr(meta, "prompt_token_count", 0) or 0)
    output = int(getattr(meta, "candidates_token_count", 0) or 0)
    total = int(getattr(meta, "total_token_count", 0) or 0)
    thoughts = int(getattr(meta, "thoughts_token_count", 0) or 0)
    if prompt == output == total == thoughts == 0:
        return None
    if total == 0:
        total = prompt + output + thoughts
    return GeminiUsage(
        model=model,
        tier=tier,
        prompt_tokens=prompt,
        output_tokens=output,
        total_tokens=total,
        thoughts_tokens=thoughts,
    )


def _record_usage(response: Any, *, model: str, tier: str) -> None:
    entry = _parse_usage_metadata(response, model=model, tier=tier)
    if entry is not None:
        _usage_log.append(entry)


class _ErrorKind(Enum):
    RATE_LIMIT = "rate_limit"
    TRANSIENT = "transient"
    FATAL = "fatal"


def _min_interval_sec() -> float:
    raw = os.getenv("GEMINI_MIN_INTERVAL_SEC", "3").strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 3.0


def _max_retries() -> int:
    """Extra attempts after the first call. Default 0 — no automatic retries."""
    raw = os.getenv("GEMINI_MAX_RETRIES", "0").strip()
    try:
        return max(0, min(2, int(raw)))
    except ValueError:
        return 0


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


def _classify_error(exc: BaseException) -> _ErrorKind:
    text = str(exc).lower()
    if any(
        marker in text
        for marker in (
            "429",
            "resource_exhausted",
            "resource has been exhausted",
            "rate limit",
            "ratelimitexceeded",
            "quota",
            "capacity",
            "per minute",
            "tokens per minute",
        )
    ):
        return _ErrorKind.RATE_LIMIT
    if any(
        marker in text
        for marker in (
            "503",
            "unavailable",
            "high demand",
            "deadline",
            "timeout",
            "timed out",
        )
    ):
        return _ErrorKind.TRANSIENT
    return _ErrorKind.FATAL


def _retry_sleep(exc: BaseException) -> float:
    text = str(exc).lower()
    import re

    reset = re.search(r"reset after ([0-9]+)s", text, re.I)
    if reset:
        return min(60.0, max(8.0, float(reset.group(1))))
    return 8.0


def _client() -> genai.Client:
    return genai.Client(api_key=get_gemini_api_key())


def _resolve_model() -> str:
    return get_gemini_model_pro()


def generate_text(
    *,
    system: str,
    user: str,
    temperature: float = 0.4,
    student_names: list[str] | None = None,
    tier: ModelTier = "pro",
) -> str:
    client = _client()
    model = _resolve_model()
    safe_user = mask_for_ai(user, student_names=student_names)
    safe_system = mask_for_ai(system, student_names=student_names)
    last_exc: BaseException | None = None
    max_attempts = 1 + _max_retries()

    for attempt in range(1, max_attempts + 1):
        _throttle()
        try:
            response = client.models.generate_content(
                model=model,
                contents=safe_user,
                config=types.GenerateContentConfig(
                    system_instruction=safe_system,
                    temperature=temperature,
                ),
            )
            text = (response.text or "").strip()
            if not text:
                raise RuntimeError("Gemini가 빈 응답을 반환했습니다.")
            _record_usage(response, model=model, tier=tier)
            return text
        except Exception as exc:
            last_exc = exc
            kind = _classify_error(exc)
            logger.warning(
                "Gemini call failed (attempt %s/%s, kind=%s, tier=%s, model=%s): %s",
                attempt,
                max_attempts,
                kind.value,
                tier,
                model,
                exc,
            )
            if attempt >= max_attempts:
                break
            if kind is _ErrorKind.RATE_LIMIT:
                # 재시도는 RPM만 더 소모함 — 즉시 실패
                break
            if kind is not _ErrorKind.TRANSIENT:
                break
            time.sleep(_retry_sleep(exc))

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
    return generate_text(system=system, user=user, temperature=0.2, tier="pro")
