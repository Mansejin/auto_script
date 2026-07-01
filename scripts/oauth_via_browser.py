#!/usr/bin/env python3
"""VNC Chrome 프로필로 OAuth 토큰 발급."""
from __future__ import annotations

import json
import socket
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = Path(__file__).resolve().parent.parent
CLIENT = ROOT / "credentials/oauth-client.json"
TOKEN = ROOT / "credentials/token.json"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

auth_code: dict[str, str] = {}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if "code" in params:
            auth_code["code"] = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<h1>OK</h1><p>You can close this tab.</p>")
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, *_args) -> None:
        return


def pick_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> None:
    port = pick_port()
    redirect_uri = f"http://127.0.0.1:{port}/"
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT), SCOPES)
    flow.redirect_uri = redirect_uri
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")

    server = HTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    print("AUTH_URL=" + auth_url)

    from playwright.sync_api import sync_playwright

    profile = Path.home() / ".config/google-chrome-playwright"
    profile.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            channel="chrome",
            args=["--no-sandbox"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(auth_url, wait_until="domcontentloaded", timeout=120_000)
        for _ in range(120):
            if auth_code.get("code"):
                break
            page.wait_for_timeout(1000)
        context.close()

    server.server_close()
    if not auth_code.get("code"):
        raise SystemExit("인증 코드를 받지 못했습니다.")

    flow.fetch_token(code=auth_code["code"])
    TOKEN.parent.mkdir(parents=True, exist_ok=True)
    TOKEN.write_text(flow.credentials.to_json(), encoding="utf-8")
    print("TOKEN_SAVED=" + str(TOKEN))


if __name__ == "__main__":
    main()
