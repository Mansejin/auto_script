from __future__ import annotations

import gspread
from google.oauth2.service_account import Credentials

from .config import COLUMNS, get_credentials_path, get_spreadsheet_id, get_worksheet_name

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def open_worksheet():
    creds = Credentials.from_service_account_file(str(get_credentials_path()), scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(get_spreadsheet_id())
    return spreadsheet.worksheet(get_worksheet_name())


def find_header_row(all_values: list[list[str]]) -> int:
    for idx, row in enumerate(all_values, start=1):
        if not row:
            continue
        head = [cell.strip() for cell in row[: len(COLUMNS)]]
        if head == list(COLUMNS):
            return idx
        if "대본" in head and "장면" in head:
            return idx
    return 1
