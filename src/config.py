from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

COLUMNS = ("대본", "장면", "사이즈", "자막", "코멘트")


def _resolve_path(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    return path


def get_spreadsheet_id() -> str:
    sheet_id = os.getenv("SPREADSHEET_ID", "").strip()
    if not sheet_id:
        raise RuntimeError("SPREADSHEET_ID가 .env에 설정되지 않았습니다.")
    return sheet_id


def get_worksheet_name() -> str:
    return os.getenv("WORKSHEET_NAME", "Sheet1").strip() or "Sheet1"


def get_auth_mode() -> str:
    return os.getenv("GOOGLE_AUTH_MODE", "auto").strip().lower() or "auto"


def get_oauth_client_path() -> Path:
    raw = os.getenv("GOOGLE_OAUTH_CLIENT_PATH", "credentials/oauth-client.json").strip()
    return _resolve_path(raw)


def get_oauth_token_path() -> Path:
    raw = os.getenv("GOOGLE_TOKEN_PATH", "credentials/token.json").strip()
    return _resolve_path(raw)


def get_service_account_path() -> Path:
    raw = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials/service-account.json").strip()
    return _resolve_path(raw)
