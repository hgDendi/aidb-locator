"""Map aidb_locator exceptions to HTTP responses."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from aidb_locator.adb import AdbError


def install(app: FastAPI) -> None:
    @app.exception_handler(AdbError)
    async def _adb_error(_: Request, exc: AdbError) -> JSONResponse:
        msg = str(exc)
        lower = msg.lower()
        if "timed out" in lower:
            status = 504
            code = "adb_timeout"
        elif "no devices" in lower or "device offline" in lower or "device not found" in lower:
            status = 409
            code = "no_device"
        elif "not found" in lower and "adb" in lower:
            status = 500
            code = "adb_missing"
        else:
            status = 502
            code = "adb_error"
        return JSONResponse(status_code=status, content={"error": code, "message": msg})

    @app.exception_handler(ValueError)
    async def _value_error(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"error": "bad_request", "message": str(exc)})
