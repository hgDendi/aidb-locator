"""API router aggregator."""

from __future__ import annotations

from fastapi import APIRouter

from aidb_locator.ui.api import devices, snapshot

api_router = APIRouter(prefix="/api")
api_router.include_router(devices.router)
api_router.include_router(snapshot.router)
