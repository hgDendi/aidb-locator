"""Map aidb_locator exceptions to HTTP responses."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from aidb_locator.adb import AdbError

# Substrings (lowercase) of adb error messages that mean "device is not usable".
# Order matters: timeout is checked first, then "adb missing", then no_device,
# falling through to a generic adb_error.
_NO_DEVICE_HINTS = (
    "no devices",
    "no device",
    "device offline",
    "device not found",
    "device unauthorized",
    "device authorizing",
    "device disconnected",
    "unauthorized",
)


def install(app: FastAPI) -> None:
    @app.exception_handler(AdbError)
    async def _adb_error(_: Request, exc: AdbError) -> JSONResponse:
        msg = str(exc)
        lower = msg.lower()
        if "timed out" in lower:
            status, code = 504, "adb_timeout"
        elif "adb not found" in lower:
            status, code = 500, "adb_missing"
        elif any(h in lower for h in _NO_DEVICE_HINTS):
            status, code = 409, "no_device"
        else:
            status, code = 502, "adb_error"
        return JSONResponse(status_code=status, content={"error": code, "message": msg})
