from __future__ import annotations

import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as UserCredentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow

from .config import (
    get_auth_mode,
    get_oauth_client_path,
    get_oauth_token_path,
    get_service_account_path,
    get_spreadsheet_id,
    get_worksheet_name,
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _oauth_credentials(*, interactive: bool = False):
    client_path = get_oauth_client_path()
    token_path = get_oauth_token_path()

    if not client_path.exists():
        raise FileNotFoundError(
            f"OAuth 클라이언트 파일이 없습니다: {client_path}\n"
            "Google Cloud Console → 사용자 인증 정보 → OAuth 클라이언트 ID(데스크톱) JSON을 저장하세요."
        )

    creds = None
    if token_path.exists():
        creds = UserCredentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json(), encoding="utf-8")
        return creds

    if not interactive:
        raise RuntimeError(
            "구글 로그인이 필요합니다. 아래 명령을 실행하세요:\n"
            "  python cli.py auth"
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(client_path), SCOPES)
    creds = flow.run_local_server(port=0)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def _service_account_credentials():
    path = get_service_account_path()
    if not path.exists():
        raise FileNotFoundError(
            f"서비스 계정 키 파일이 없습니다: {path}\n"
            "Google Cloud Console에서 서비스 계정 JSON을 발급받아 해당 경로에 저장하세요."
        )
    return ServiceAccountCredentials.from_service_account_file(str(path), scopes=SCOPES)


def get_credentials(*, interactive: bool = False):
    mode = get_auth_mode()
    oauth_client = get_oauth_client_path()
    service_account = get_service_account_path()

    if mode == "oauth" or (mode == "auto" and oauth_client.exists()):
        return _oauth_credentials(interactive=interactive)
    if mode == "service_account" or (mode == "auto" and service_account.exists()):
        return _service_account_credentials()

    raise FileNotFoundError(
        "인증 파일을 찾을 수 없습니다.\n"
        "- OAuth: credentials/oauth-client.json + `python cli.py auth`\n"
        "- 서비스 계정: credentials/service-account.json"
    )


def authorize_google(*, interactive: bool = False):
    return gspread.authorize(get_credentials(interactive=interactive))


def open_worksheet():
    client = authorize_google()
    spreadsheet = client.open_by_key(get_spreadsheet_id())
    return spreadsheet.worksheet(get_worksheet_name())


def find_header_row(all_values: list[list[str]]) -> int:
    from .config import COLUMNS

    for idx, row in enumerate(all_values, start=1):
        if not row:
            continue
        head = [cell.strip() for cell in row[: len(COLUMNS)]]
        if head == list(COLUMNS):
            return idx
        if "대본" in head and "장면" in head:
            return idx
    return 1
