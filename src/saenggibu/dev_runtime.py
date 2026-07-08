from __future__ import annotations

import os
from typing import Literal

ProfileName = Literal["split", "flash", "pro"]

_profile_override: str | None = None
_skip_proofread_override: bool | None = None


def dev_mode_enabled() -> bool:
    return os.getenv("SGB_DEV_MODE", "").strip().lower() in ("1", "true", "yes")


def get_profile_override() -> str | None:
    if not dev_mode_enabled():
        return None
    return _profile_override


def get_skip_proofread_override() -> bool | None:
    if not dev_mode_enabled():
        return None
    return _skip_proofread_override


def set_profile_override(value: str | None) -> None:
    global _profile_override
    if value is not None and value not in ("split", "flash", "pro"):
        raise ValueError(f"Unknown profile: {value}")
    _profile_override = value


def set_skip_proofread_override(value: bool | None) -> None:
    global _skip_proofread_override
    _skip_proofread_override = value


def reset_overrides() -> None:
    set_profile_override(None)
    set_skip_proofread_override(None)
