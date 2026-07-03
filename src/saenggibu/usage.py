from __future__ import annotations

import os
from datetime import datetime, timezone

from .config import DATA_DIR, ensure_data_dirs
from .io_utils import load_json, save_json

USAGE_PATH = DATA_DIR / "usage.json"


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _free_limit() -> int:
    return int(os.getenv("SGB_FREE_GENERATIONS", "10"))


def _plan() -> str:
    return os.getenv("SGB_PLAN", "free").strip().lower() or "free"


def load_usage() -> dict:
    ensure_data_dirs()
    if not USAGE_PATH.exists():
        return {"month": _month_key(), "generations": 0}
    data = load_json(USAGE_PATH)
    if data.get("month") != _month_key():
        return {"month": _month_key(), "generations": 0}
    return data


def usage_summary() -> dict:
    used = load_usage()["generations"]
    limit = _free_limit()
    plan = _plan()
    unlimited = plan in ("pro", "paid", "admin")
    return {
        "plan": plan,
        "month": _month_key(),
        "generations_used": used,
        "generations_limit": None if unlimited else limit,
        "generations_remaining": None if unlimited else max(0, limit - used),
        "unlimited": unlimited,
    }


def check_generation_allowed() -> None:
    summary = usage_summary()
    if summary["unlimited"]:
        return
    remaining = summary["generations_remaining"]
    if remaining is not None and remaining <= 0:
        raise RuntimeError(
            f"이번 달 무료 작성 한도({summary['generations_limit']}건)를 모두 사용했습니다. "
            "Pro 플랜으로 업그레이드하거나 다음 달에 다시 시도하세요."
        )


def record_generation(count: int = 1) -> dict:
    data = load_usage()
    data["generations"] = int(data.get("generations", 0)) + count
    save_json(USAGE_PATH, data)
    return usage_summary()
