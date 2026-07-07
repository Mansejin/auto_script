from __future__ import annotations

import re
from typing import Any


def _extract_message(text: str) -> str | None:
    quoted = re.search(r"['\"]message['\"]\s*:\s*['\"]([^'\"]+)['\"]", text)
    if quoted:
        return quoted.group(1).strip()
    return None


def friendly_api_error(exc: BaseException | str | Any) -> str:
    """Turn provider/SDK errors into short Korean messages for teachers."""
    raw = str(exc).strip()
    if not raw:
        return "알 수 없는 오류가 발생했습니다."

    lowered = raw.lower()
    provider_message = _extract_message(raw)

    if "high demand" in lowered or "spikes in demand" in lowered:
        return "AI 모델이 일시적으로 과부하 상태입니다. 1~2분 후 다시 시도해 주세요."

    if "resource_exhausted" in lowered or "quota" in lowered or "rate limit" in lowered:
        return "AI 사용 한도에 도달했습니다. 잠시 후 다시 시도하거나 관리자에게 문의하세요."

    if "503" in lowered or "unavailable" in lowered:
        if provider_message:
            return f"AI 서비스를 일시적으로 사용할 수 없습니다. ({provider_message})"
        return "AI 서비스를 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해 주세요."

    if "429" in lowered or "too many requests" in lowered:
        return "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요."

    if "deadline" in lowered or "timeout" in lowered or "timed out" in lowered:
        return "AI 응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요."

    if "api key" in lowered or "apikey" in lowered or "gemini_api_key" in lowered:
        return "Gemini API 키가 설정되지 않았거나 올바르지 않습니다."

    if "connection" in lowered or "connect" in lowered or "network" in lowered:
        return "네트워크 연결에 실패했습니다. NAS·인터넷 상태를 확인하세요."

    if provider_message and len(provider_message) < 160 and "{" not in provider_message:
        return provider_message

    if len(raw) > 160 or "{" in raw or "error" in lowered[:40]:
        return "작성 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."

    return raw
