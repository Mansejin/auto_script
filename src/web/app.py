from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.saenggibu.config import ensure_data_dirs
from src.web.routes import router

ROOT = Path(__file__).resolve().parent.parent.parent
ADMIN_STATIC = ROOT / "web" / "admin"


def _allowed_origins() -> list[str]:
    raw = os.getenv(
        "SGB_ALLOWED_ORIGINS",
        "https://mansejin.com,https://www.mansejin.com,http://localhost:8080,http://127.0.0.1:8080",
    )
    return [item.strip() for item in raw.split(",") if item.strip()]


def create_app() -> FastAPI:
    ensure_data_dirs()

    app = FastAPI(title="생기부 작성 머신", docs_url=None, redoc_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(router)

    if ADMIN_STATIC.is_dir():
        app.mount("/admin-static", StaticFiles(directory=ADMIN_STATIC), name="admin-static")

        @app.get("/admin/saenggibu")
        def admin_page() -> FileResponse:
            return FileResponse(ADMIN_STATIC / "index.html")

        privacy_doc = ROOT / "docs" / "privacy-policy.md"

        @app.get("/docs/privacy-policy.md")
        def privacy_policy() -> FileResponse:
            return FileResponse(privacy_doc, media_type="text/markdown; charset=utf-8")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
