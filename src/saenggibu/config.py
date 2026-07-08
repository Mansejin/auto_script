from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT / ".env")
# Local experiments (model profile, skip proofread) — not for NAS production
load_dotenv(ROOT / ".env.local", override=True)

DATA_DIR = ROOT / "data" / "saenggibu"
SAMPLES_DIR = DATA_DIR / "samples"
STUDENTS_DIR = DATA_DIR / "students"
OUTPUTS_DIR = DATA_DIR / "outputs"
JOBS_DIR = DATA_DIR / "jobs"
PATTERNS_PATH = DATA_DIR / "patterns.json"
PROMPT_PATH = ROOT / "prompts" / "saenggibu.md"

from .dev_runtime import dev_mode_enabled, get_profile_override, get_skip_proofread_override

CHANGCHE_SUBSECTIONS = ("자율", "동아리", "봉사", "진로")


def get_gemini_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY가 .env에 설정되지 않았습니다. "
            "https://aistudio.google.com/apikey 에서 발급 후 설정하세요."
        )
    return key


def get_gemini_model_pro() -> str:
    explicit = os.getenv("GEMINI_MODEL_PRO", "").strip()
    if explicit:
        return explicit
    legacy = os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview").strip()
    return legacy or "gemini-3.1-pro-preview"


def get_gemini_model_fast() -> str:
    return os.getenv("GEMINI_MODEL_FAST", "gemini-2.5-flash").strip() or "gemini-2.5-flash"


def _normalize_profile(raw: str) -> str:
    value = raw.strip().lower()
    if value in ("flash", "all-flash", "fast"):
        return "flash"
    if value in ("pro", "all-pro"):
        return "pro"
    return "split"


def env_gemini_model_profile() -> str:
    """Profile from .env / .env.local only."""
    return _normalize_profile(os.getenv("GEMINI_MODEL_PROFILE", "split"))


def get_gemini_model_profile() -> str:
    """split (default) | flash | pro — see docs/model-cost-local.md"""
    override = get_profile_override()
    if override is not None:
        return override
    return env_gemini_model_profile()


def env_skip_gemini_proofread() -> bool:
    return os.getenv("GEMINI_SKIP_PROOFREAD", "").strip().lower() in ("1", "true", "yes")


def skip_gemini_proofread() -> bool:
    override = get_skip_proofread_override()
    if override is not None:
        return override
    return env_skip_gemini_proofread()


def get_gemini_model() -> str:
    """Primary writing model (backward compatible alias for pro)."""
    return get_gemini_model_pro()


def gemini_models_for_api() -> dict[str, str | bool]:
    profile = get_gemini_model_profile()
    return {
        "gemini_model": get_gemini_model_pro(),
        "gemini_model_pro": get_gemini_model_pro(),
        "gemini_model_fast": get_gemini_model_fast(),
        "gemini_model_profile": profile,
        "gemini_skip_proofread": skip_gemini_proofread(),
        "dev_mode": dev_mode_enabled(),
    }


def ensure_data_dirs() -> None:
    for path in (SAMPLES_DIR, STUDENTS_DIR, OUTPUTS_DIR, JOBS_DIR):
        path.mkdir(parents=True, exist_ok=True)
