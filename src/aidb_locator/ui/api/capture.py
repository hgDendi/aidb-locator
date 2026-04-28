"""GET /api/capture/{view_addr} — single-view rendered bitmap."""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from aidb_locator.commands import CodeLocator
from aidb_locator.ui.deps import make_codelocator

router = APIRouter()


@router.get("/capture/{view_addr}")
def capture(view_addr: str, device: str | None = Query(default=None)) -> FileResponse:
    path = make_codelocator(device).capture_view(view_addr)
    return FileResponse(path, media_type="image/png", filename=f"view_{view_addr}.png")
