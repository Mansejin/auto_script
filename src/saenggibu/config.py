from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data" / "saenggibu"
SAMPLES_DIR = DATA_DIR / "samples"
STUDENTS_DIR = DATA_DIR / "students"
OUTPUTS_DIR = DATA_DIR / "outputs"
JOBS_DIR = DATA_DIR / "jobs"
PATTERNS_PATH = DATA_DIR / "patterns.json"
PROMPT_PATH = ROOT / "prompts" / "saenggibu.md"

SECTION_TYPES = ("행발", "세특", "창체")
CHANGCHE_SUBSECTIONS = ("자율", "동아리", "봉사", "진로")


def get_gemini_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY가 .env에 설정되지 않았습니다. "
            "https://aistudio.google.com/apikey 에서 발급 후 설정하세요."
        )
    return key


def get_gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview").strip() or "gemini-3.1-pro-preview"


def ensure_data_dirs() -> None:
    for path in (SAMPLES_DIR, STUDENTS_DIR, OUTPUTS_DIR, JOBS_DIR):
        path.mkdir(parents=True, exist_ok=True)
