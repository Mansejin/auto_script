from __future__ import annotations

import json
from pathlib import Path

import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as UserCredentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow

from .config import (
    ROOT,
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


def _load_saved_oauth_credentials():
    token_path = get_oauth_token_path()
    if not token_path.exists():
        return None
    return UserCredentials.from_authorized_user_file(str(token_path), SCOPES)


def _save_oauth_credentials(creds) -> None:
    token_path = get_oauth_token_path()
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")


def _oauth_redirect_uri() -> str:
    client_path = get_oauth_client_path()
    data = json.loads(client_path.read_text(encoding="utf-8"))
    installed = data.get("installed") or data.get("web") or {}
    redirect_uris = installed.get("redirect_uris") or ["http://localhost"]
    return redirect_uris[0]


def _oauth_flow() -> InstalledAppFlow:
    client_path = get_oauth_client_path()
    if not client_path.exists():
        raise FileNotFoundError(
            f"OAuth 클라이언트 파일이 없습니다: {client_path}\n"
            "Google Cloud Console → 사용자 인증 정보 → OAuth 클라이언트 ID(데스크톱) JSON을 저장하세요."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(client_path), SCOPES)
    flow.redirect_uri = _oauth_redirect_uri()
    return flow


def _oauth_credentials(*, interactive: bool = False):
    creds = _load_saved_oauth_credentials()

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_oauth_credentials(creds)
        return creds

    if not interactive:
        raise RuntimeError(
            "구글 로그인이 필요합니다.\n"
            "  로컬: python cli.py auth\n"
            "  클라우드: python cli.py auth-url → 브라우저 로그인 → python cli.py auth-code <코드>"
        )

    flow = _oauth_flow()
    creds = flow.run_local_server(port=0)
    _save_oauth_credentials(creds)
    return creds


def _oauth_pending_path() -> Path:
    return get_oauth_token_path().parent / "oauth-pending.json"


def get_oauth_authorization_url() -> str:
    flow = _oauth_flow()
    redirect_uri = flow.redirect_uri
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        redirect_uri=redirect_uri,
    )
    pending = {
        "state": state,
        "redirect_uri": redirect_uri,
        "code_verifier": flow.oauth2session._client.code_verifier,
    }
    _oauth_pending_path().write_text(json.dumps(pending), encoding="utf-8")
    return auth_url


def exchange_oauth_code(code: str):
    pending_path = _oauth_pending_path()
    if not pending_path.exists():
        raise RuntimeError(
            "먼저 `python cli.py auth-url`을 실행해 로그인 URL을 받으세요."
        )

    pending = json.loads(pending_path.read_text(encoding="utf-8"))
    flow = _oauth_flow()
    flow.redirect_uri = pending["redirect_uri"]
    flow.oauth2session._client.code_verifier = pending["code_verifier"]
    flow.fetch_token(
        code=code.strip(),
        state=pending["state"],
        redirect_uri=pending["redirect_uri"],
    )
    _save_oauth_credentials(flow.credentials)
    pending_path.unlink(missing_ok=True)
    return flow.credentials


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
