"""Edit / schema / touch endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from aidb_locator.commands import CodeLocator
from aidb_locator.ui.deps import make_codelocator

router = APIRouter()


class EditBody(BaseModel):
    view_addr: str
    edit_type: str
    value: str


class SchemaBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    url: str = Field(alias="schema")


class TouchBody(BaseModel):
    x: int
    y: int


@router.post("/edit")
def edit(body: EditBody, device: str | None = Query(default=None)):
    ok = make_codelocator(device).edit_view(body.view_addr, body.edit_type, body.value)
    if not ok:
        return JSONResponse(
            status_code=502,
            content={"error": "edit_failed", "message": "device returned non-zero"},
        )
    return {"ok": True}


@router.post("/schema")
def schema(body: SchemaBody, device: str | None = Query(default=None)) -> dict:
    msg = make_codelocator(device).send_schema(body.url)
    return {"ok": True, "msg": msg}


@router.post("/touch")
def touch(body: TouchBody, device: str | None = Query(default=None)) -> dict:
    v = make_codelocator(device).get_touch_view(body.x, body.y)
    return {
        "class_name": v.class_name,
        "id_str": v.id_str,
        "mem_addr": v.mem_addr,
        "text": v.text,
        "bounds": {"left": v.left, "top": v.top, "right": v.right, "bottom": v.bottom},
    }
