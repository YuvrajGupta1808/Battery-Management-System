"""FastAPI application factory."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .core.config import get_settings
from .routes import register_routes


def _static_dir(settings_dir: str | None) -> Path | None:
    if settings_dir:
        candidate = Path(settings_dir).expanduser().resolve()
        if candidate.is_dir() and (candidate / "index.html").is_file():
            return candidate
    return None


def _maybe_mount_static(app: FastAPI) -> None:
    if os.getenv("WORKBENCH_SERVE_STATIC", "").lower() not in {"1", "true", "yes"}:
        return
    static_root = _static_dir(os.getenv("WORKBENCH_STATIC_DIR")) or _static_dir("apps/web/dist")
    if static_root is None:
        return
    app.mount("/", StaticFiles(directory=static_root, html=True), name="frontend")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Local Deep Coding Agent Workbench", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    register_routes(app)
    _maybe_mount_static(app)
    return app
