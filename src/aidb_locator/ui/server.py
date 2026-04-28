"""FastAPI server + uvicorn entry."""

from __future__ import annotations

from fastapi import FastAPI

from aidb_locator.ui import errors
from aidb_locator.ui.api import api_router


def build_app() -> FastAPI:
    app = FastAPI(title="aidb-locator UI", version="0.1.0")
    errors.install(app)
    app.include_router(api_router)
    return app


def main() -> None:  # filled out in Task 8
    raise NotImplementedError("filled in Task 8")
