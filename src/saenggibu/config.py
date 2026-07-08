from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / ".env.local", override=True)

DATA_DIR = ROOT / "data" / "saenggibu"
SAMPLES_DIR = DATA_DIR / "samples"
STUDENTS_DIR = DATA_DIR / "students"
OUTPUTS_DIR = DATA_DIR / "outputs"
JOBS_DIR = DATA_DIR / "jobs"
PATTERNS_PATH = DATA_DIR / "patterns.json"
PROMPT_PATH = ROOT / "prompts" / "saenggibu.md"

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
    """샘플 분석·다시 쓰기(Pro 선택)용."""
    explicit = os.getenv("GEMINI_MODEL_PRO", "").strip()
    if explicit:
        return explicit
    legacy = os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview").strip()
    return legacy or "gemini-3.1-pro-preview"


def get_gemini_model_fast() -> str:
    """일괄 작성·맞춤법·메모 파싱 기본 모델."""
    return os.getenv("GEMINI_MODEL_FAST", "gemini-2.5-flash").strip() or "gemini-2.5-flash"


def get_gemini_model() -> str:
    """기본 작성 모델 (Flash)."""
    return get_gemini_model_fast()


def gemini_models_for_api() -> dict[str, str]:
    return {
        "gemini_model": get_gemini_model_fast(),
        "gemini_model_pro": get_gemini_model_pro(),
        "gemini_model_fast": get_gemini_model_fast(),
        "gemini_model_default": "fast",
    }


def ensure_data_dirs() -> None:
    for path in (SAMPLES_DIR, STUDENTS_DIR, OUTPUTS_DIR, JOBS_DIR):
        path.mkdir(parents=True, exist_ok=True)
