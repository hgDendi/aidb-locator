"""Per-request dependency factories — build CodeLocator/NativeAdb for a serial."""

from __future__ import annotations

from aidb_locator.adb import AdbClient
from aidb_locator.commands import CodeLocator, NativeAdb


def make_adb(serial: str | None) -> AdbClient:
    return AdbClient(device_serial=serial or None, timeout=10)


def make_codelocator(serial: str | None) -> CodeLocator:
    return CodeLocator(make_adb(serial))


def make_native(serial: str | None) -> NativeAdb:
    return NativeAdb(make_adb(serial))
