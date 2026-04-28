"""Snapshot endpoints — combine screenshot + layout + activity."""

from __future__ import annotations

import asyncio
import base64
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from aidb_locator.commands import CodeLocator, NativeAdb
from aidb_locator.models import WApplication, WView
from aidb_locator.ui.deps import make_codelocator, make_native

router = APIRouter()


def _view_to_full_dict(v: WView, parent_abs_left: int = 0, parent_abs_top: int = 0) -> dict:
    """Serialize WView with absolute bounds (CodeLocator returns parent-relative).

    `v.left/right/top/bottom` are `view.getLeft/Right/Top/Bottom()` — relative
    to the immediate parent. Walking the tree and accumulating gives the screen-
    absolute rectangle the UI needs for hit-testing.
    """
    abs_left = parent_abs_left + v.left
    abs_top = parent_abs_top + v.top
    abs_right = parent_abs_left + v.right
    abs_bottom = parent_abs_top + v.bottom
    return {
        "class_name": v.class_name,
        "visibility": v.visibility,
        "id_str": v.id_str,
        "mem_addr": v.mem_addr,
        "text": v.text,
        "bounds": {"left": abs_left, "top": abs_top, "right": abs_right, "bottom": abs_bottom},
        "padding": [v.padding_left, v.padding_top, v.padding_right, v.padding_bottom],
        "margin": [v.margin_left, v.margin_top, v.margin_right, v.margin_bottom],
        "alpha": v.alpha,
        "background_color": v.background_color,
        "text_color": v.text_color,
        "text_size": v.text_size,
        "is_clickable": v.is_clickable,
        "children": [_view_to_full_dict(c, abs_left, abs_top) for c in v.children],
    }


def _activity_block(app: WApplication) -> dict:
    return {
        "activity": app.activity.class_name,
        "package": app.package_name,
        "fragments": [f.class_name for f in app.activity.fragments if f.is_visible or f.is_added],
    }


def _root_view(app: WApplication) -> WView | None:
    return app.activity.decor_views[0] if app.activity.decor_views else None


@router.get("/snapshot")
async def snapshot(device: str | None = Query(default=None)) -> dict:
    cl = make_codelocator(device)
    nat = make_native(device)

    layout_task = asyncio.to_thread(cl.grab_layout)
    shot_task = asyncio.to_thread(nat.screenshot)
    app, png_path = await asyncio.gather(layout_task, shot_task)

    png_bytes = Path(png_path).read_bytes()
    root = _root_view(app)
    return {
        "screenshot_png_b64": base64.b64encode(png_bytes).decode("ascii"),
        "device_size": {"width": app.screen_width, "height": app.screen_height},
        "density": app.density,
        "activity": _activity_block(app),
        "layout": _view_to_full_dict(root) if root else None,
        "schemas": [s.schema for s in app.schemas],
    }


@router.get("/screenshot")
def screenshot_png(device: str | None = Query(default=None)) -> FileResponse:
    path = make_native(device).screenshot()
    return FileResponse(path, media_type="image/png")


@router.get("/layout")
def layout(device: str | None = Query(default=None)) -> dict:
    app = make_codelocator(device).grab_layout()
    root = _root_view(app)
    return _view_to_full_dict(root) if root else {}


@router.get("/activity")
def activity(device: str | None = Query(default=None)) -> dict:
    app = make_codelocator(device).grab_layout()
    return _activity_block(app)
