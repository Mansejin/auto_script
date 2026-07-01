from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

COLUMNS = ("대본", "장면", "사이즈", "자막", "코멘트")


def get_spreadsheet_id() -> str:
    sheet_id = os.getenv("SPREADSHEET_ID", "").strip()
    if not sheet_id:
        raise RuntimeError("SPREADSHEET_ID가 .env에 설정되지 않았습니다.")
    return sheet_id


def get_worksheet_name() -> str:
    return os.getenv("WORKSHEET_NAME", "Sheet1").strip() or "Sheet1"


def get_credentials_path() -> Path:
    raw = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials/service-account.json").strip()
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        raise FileNotFoundError(
            f"서비스 계정 키 파일이 없습니다: {path}\n"
            "Google Cloud Console에서 서비스 계정 JSON을 발급받아 해당 경로에 저장하세요."
        )
    return path
