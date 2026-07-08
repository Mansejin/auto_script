#!/usr/bin/env python3
"""Playwright로 구글 시트 편집 시도 (로그인 세션 필요)."""
from __future__ import annotations

import json
import time
from pathlib import Path

import os

from playwright.sync_api import sync_playwright


def _sheet_url() -> str:
    sheet_id = os.getenv("SPREADSHEET_ID", "").strip()
    if not sheet_id:
        raise RuntimeError("SPREADSHEET_ID 환경 변수를 설정하세요 (.env 참고)")
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
PROFILE = Path.home() / ".config/google-chrome"


def main() -> None:
    updates = json.loads(Path("changes/idea_tab11_update.json").read_text(encoding="utf-8"))
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE),
            headless=True,
            channel="chrome",
            args=["--no-sandbox"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(_sheet_url(), wait_until="networkidle", timeout=120_000)
        title = page.title()
        print("title:", title)
        if "Sign in" in title or "로그인" in page.content():
            raise SystemExit("구글 로그인 필요")
        # 간단 검증: 시트 로드 여부만 확인
        time.sleep(3)
        print("loaded ok")
        context.close()


if __name__ == "__main__":
    main()
