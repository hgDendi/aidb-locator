"""GET /api/devices — list connected ADB devices."""

from __future__ import annotations

from fastapi import APIRouter

from aidb_locator.adb import AdbClient

router = APIRouter()


@router.get("/devices")
def list_devices() -> list[dict]:
    devices = AdbClient().list_devices()
    return [{"serial": d.serial, "state": d.state} for d in devices]
