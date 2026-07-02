#!/usr/bin/env python3
"""생기부 관리자 웹 서버."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.getenv("SGB_HOST", "127.0.0.1")
    port = int(os.getenv("SGB_PORT", "8787"))
    uvicorn.run("src.web.app:app", host=host, port=port, reload=os.getenv("SGB_RELOAD") == "1")


if __name__ == "__main__":
    main()
