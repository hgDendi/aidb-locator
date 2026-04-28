# aidb-locator UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a local web GUI for `aidb-locator` (`pip install` + `aidb-ui`) that lets non-CLI users visualize Android screenshots, click to inspect view layouts, edit view properties, jump via schema, and export — all from a browser.

**Architecture:** FastAPI single-process server thinly wrapping the existing `aidb_locator.commands` API. Frontend is a Vue 3 SPA loaded from CDN (no build step) shipped as static assets in the wheel. Snapshot model: one refresh fetches screenshot + layout together; all hover / click / edit operations work off the cached snapshot.

**Tech Stack:** FastAPI, uvicorn, Vue 3 (CDN), Tailwind (CDN), pytest + httpx, node:test for the frontend hit-test.

**Spec:** `docs/superpowers/specs/2026-04-28-aidb-locator-ui-design.md`

---

## File Structure

```
pyproject.toml                          MODIFY: deps + aidb-ui script
src/aidb_locator/ui/
  __init__.py                           CREATE: empty
  server.py                             CREATE: FastAPI app + main() entry
  deps.py                               CREATE: CodeLocator/NativeAdb factories per device
  errors.py                             CREATE: exception → HTTP mapping
  api/
    __init__.py                         CREATE: router aggregator
    devices.py                          CREATE: GET /api/devices
    snapshot.py                         CREATE: GET /api/snapshot|screenshot|layout|activity
    edit.py                             CREATE: POST /api/edit|schema|touch
    capture.py                          CREATE: GET /api/capture/{view_addr}
  static/
    index.html                          CREATE: Vue 3 root + Tailwind/Vue CDN
    app.js                              CREATE: Vue app
    findViewAt.js                       CREATE: pure hit-test function (ES module)
    style.css                           CREATE: small overrides

tests/ui/
  __init__.py                           CREATE: empty
  conftest.py                           CREATE: TestClient + monkeypatch helpers
  test_devices.py                       CREATE
  test_snapshot.py                      CREATE
  test_edit.py                          CREATE
  test_capture.py                       CREATE
  test_errors.py                        CREATE
  test_findViewAt.mjs                   CREATE: node:test
  MANUAL.md                             CREATE: e2e checklist

README.md                               MODIFY: add UI section
```

---

## Task 1: Project scaffolding (deps + console script + empty package)

**Files:**
- Modify: `pyproject.toml`
- Create: `src/aidb_locator/ui/__init__.py`
- Create: `src/aidb_locator/ui/api/__init__.py`
- Create: `tests/ui/__init__.py`

- [ ] **Step 1: Update `pyproject.toml`**

Replace the `dependencies` block and `[project.scripts]` block with:

```toml
dependencies = [
    "click>=8.0",
    "mcp>=1.0",
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "httpx>=0.27",
]

[project.scripts]
aidb = "aidb_locator.cli:main"
aidb-ui = "aidb_locator.ui.server:main"
```

Add right before `[tool.pytest.ini_options]`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
]
```

- [ ] **Step 2: Create empty package files**

Create `src/aidb_locator/ui/__init__.py` with content:

```python
"""Local web UI for aidb-locator."""
```

Create `src/aidb_locator/ui/api/__init__.py` empty (will be filled later).

Create `tests/ui/__init__.py` empty.

- [ ] **Step 3: Reinstall in editable mode**

Run:

```bash
pip3 install -e ".[dev]"
```

Expected: install succeeds, fastapi + uvicorn pulled in.

- [ ] **Step 4: Verify aidb-ui script registered**

Run:

```bash
which aidb-ui
```

Expected: prints a path under your Python `bin/` directory. (The script will fail to run because `main` isn't defined yet — that's OK for now.)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/aidb_locator/ui/__init__.py src/aidb_locator/ui/api/__init__.py tests/ui/__init__.py
git commit -m "chore: scaffold aidb_locator.ui package + FastAPI/uvicorn deps"
```

---

## Task 2: Backend deps + error mapping (no endpoints yet)

**Files:**
- Create: `src/aidb_locator/ui/deps.py`
- Create: `src/aidb_locator/ui/errors.py`

- [ ] **Step 1: Create `src/aidb_locator/ui/deps.py`**

```python
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
```

- [ ] **Step 2: Create `src/aidb_locator/ui/errors.py`**

```python
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
```

- [ ] **Step 3: Commit**

```bash
git add src/aidb_locator/ui/deps.py src/aidb_locator/ui/errors.py
git commit -m "feat(ui): add per-device factory + AdbError → HTTP mapping"
```

---

## Task 3: Backend — devices endpoint (TDD)

**Files:**
- Create: `tests/ui/conftest.py`
- Create: `tests/ui/test_devices.py`
- Create: `src/aidb_locator/ui/api/devices.py`
- Create: `src/aidb_locator/ui/server.py` (skeleton)
- Modify: `src/aidb_locator/ui/api/__init__.py`

- [ ] **Step 1: Create `tests/ui/conftest.py`**

```python
"""Shared pytest fixtures for UI API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    from aidb_locator.ui.server import build_app
    return build_app()


@pytest.fixture
def client(app):
    return TestClient(app)
```

- [ ] **Step 2: Write the failing test — `tests/ui/test_devices.py`**

```python
from aidb_locator.adb import Device


def test_list_devices_returns_serials_and_states(client, monkeypatch):
    fake = [
        Device(serial="emulator-5554", state="device"),
        Device(serial="ABCD1234", state="unauthorized"),
    ]
    monkeypatch.setattr(
        "aidb_locator.ui.api.devices.AdbClient.list_devices",
        lambda self: fake,
    )

    resp = client.get("/api/devices")
    assert resp.status_code == 200
    assert resp.json() == [
        {"serial": "emulator-5554", "state": "device"},
        {"serial": "ABCD1234", "state": "unauthorized"},
    ]


def test_list_devices_empty(client, monkeypatch):
    monkeypatch.setattr(
        "aidb_locator.ui.api.devices.AdbClient.list_devices",
        lambda self: [],
    )
    resp = client.get("/api/devices")
    assert resp.status_code == 200
    assert resp.json() == []
```

- [ ] **Step 3: Run test to verify it fails**

```bash
pytest tests/ui/test_devices.py -v
```

Expected: ImportError (no `aidb_locator.ui.server` module yet).

- [ ] **Step 4: Create `src/aidb_locator/ui/api/devices.py`**

```python
"""GET /api/devices — list connected ADB devices."""

from __future__ import annotations

from fastapi import APIRouter

from aidb_locator.adb import AdbClient

router = APIRouter()


@router.get("/devices")
def list_devices() -> list[dict]:
    devices = AdbClient().list_devices()
    return [{"serial": d.serial, "state": d.state} for d in devices]
```

- [ ] **Step 5: Update `src/aidb_locator/ui/api/__init__.py`**

```python
"""API router aggregator."""

from __future__ import annotations

from fastapi import APIRouter

from aidb_locator.ui.api import devices

api_router = APIRouter(prefix="/api")
api_router.include_router(devices.router)
```

- [ ] **Step 6: Create `src/aidb_locator/ui/server.py` skeleton**

```python
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
```

- [ ] **Step 7: Run test to verify it passes**

```bash
pytest tests/ui/test_devices.py -v
```

Expected: 2 PASSED.

- [ ] **Step 8: Commit**

```bash
git add tests/ui/conftest.py tests/ui/test_devices.py \
        src/aidb_locator/ui/api/devices.py \
        src/aidb_locator/ui/api/__init__.py \
        src/aidb_locator/ui/server.py
git commit -m "feat(ui): GET /api/devices endpoint"
```

---

## Task 4: Backend — snapshot endpoint (TDD)

**Files:**
- Create: `tests/ui/test_snapshot.py`
- Create: `src/aidb_locator/ui/api/snapshot.py`
- Modify: `src/aidb_locator/ui/api/__init__.py`

- [ ] **Step 1: Write the failing test — `tests/ui/test_snapshot.py`**

```python
import base64
from pathlib import Path

from aidb_locator.models import (
    SchemaInfo,
    WActivity,
    WApplication,
    WFragment,
    WView,
)


def _fake_app() -> WApplication:
    root = WView(class_name="DecorView", left=0, top=0, right=1080, bottom=2340)
    child = WView(
        class_name="TextView",
        id_str="tv_title",
        text="hello",
        left=100, top=200, right=400, bottom=280,
        mem_addr="abc123",
    )
    root.children.append(child)
    return WApplication(
        package_name="com.example",
        activity=WActivity(
            class_name="HomeActivity",
            decor_views=[root],
            fragments=[WFragment(class_name="HomeFragment", is_visible=True)],
        ),
        screen_width=1080,
        screen_height=2340,
        density=2.75,
        schemas=[SchemaInfo(schema="demo://home")],
    )


def test_snapshot_returns_screenshot_layout_activity(client, monkeypatch, tmp_path):
    png_bytes = b"\x89PNG\r\n\x1a\nFAKE"
    png_file = tmp_path / "shot.png"
    png_file.write_bytes(png_bytes)

    monkeypatch.setattr(
        "aidb_locator.ui.api.snapshot.CodeLocator.grab_layout",
        lambda self: _fake_app(),
    )
    monkeypatch.setattr(
        "aidb_locator.ui.api.snapshot.NativeAdb.screenshot",
        lambda self, output=None: png_file,
    )

    resp = client.get("/api/snapshot")
    assert resp.status_code == 200
    body = resp.json()

    assert base64.b64decode(body["screenshot_png_b64"]) == png_bytes
    assert body["device_size"] == {"width": 1080, "height": 2340}
    assert body["activity"]["activity"] == "HomeActivity"
    assert body["activity"]["fragments"] == ["HomeFragment"]
    assert body["layout"]["class_name"] == "DecorView"
    assert body["layout"]["children"][0]["id_str"] == "tv_title"
    assert body["schemas"] == ["demo://home"]


def test_screenshot_returns_png(client, monkeypatch, tmp_path):
    png_bytes = b"\x89PNG\r\n\x1a\nDATA"
    png_file = tmp_path / "s.png"
    png_file.write_bytes(png_bytes)
    monkeypatch.setattr(
        "aidb_locator.ui.api.snapshot.NativeAdb.screenshot",
        lambda self, output=None: png_file,
    )

    resp = client.get("/api/screenshot")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/png")
    assert resp.content == png_bytes


def test_layout_returns_tree(client, monkeypatch):
    monkeypatch.setattr(
        "aidb_locator.ui.api.snapshot.CodeLocator.grab_layout",
        lambda self: _fake_app(),
    )
    resp = client.get("/api/layout")
    assert resp.status_code == 200
    body = resp.json()
    assert body["class_name"] == "DecorView"
    assert len(body["children"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/ui/test_snapshot.py -v
```

Expected: 404s (endpoints don't exist).

- [ ] **Step 3: Create `src/aidb_locator/ui/api/snapshot.py`**

```python
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


def _view_to_full_dict(v: WView) -> dict:
    """Serialize WView with everything the UI needs (richer than to_dict())."""
    return {
        "class_name": v.class_name,
        "visibility": v.visibility,
        "id_str": v.id_str,
        "mem_addr": v.mem_addr,
        "text": v.text,
        "bounds": {"left": v.left, "top": v.top, "right": v.right, "bottom": v.bottom},
        "padding": [v.padding_left, v.padding_top, v.padding_right, v.padding_bottom],
        "margin": [v.margin_left, v.margin_top, v.margin_right, v.margin_bottom],
        "alpha": v.alpha,
        "background_color": v.background_color,
        "text_color": v.text_color,
        "text_size": v.text_size,
        "is_clickable": v.is_clickable,
        "children": [_view_to_full_dict(c) for c in v.children],
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
```

- [ ] **Step 4: Register router in `src/aidb_locator/ui/api/__init__.py`**

Replace the file with:

```python
"""API router aggregator."""

from __future__ import annotations

from fastapi import APIRouter

from aidb_locator.ui.api import devices, snapshot

api_router = APIRouter(prefix="/api")
api_router.include_router(devices.router)
api_router.include_router(snapshot.router)
```

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/ui/test_snapshot.py -v
```

Expected: 3 PASSED.

- [ ] **Step 6: Commit**

```bash
git add tests/ui/test_snapshot.py \
        src/aidb_locator/ui/api/snapshot.py \
        src/aidb_locator/ui/api/__init__.py
git commit -m "feat(ui): /api/snapshot|screenshot|layout|activity endpoints"
```

---

## Task 5: Backend — edit/schema/touch endpoints (TDD)

**Files:**
- Create: `tests/ui/test_edit.py`
- Create: `src/aidb_locator/ui/api/edit.py`
- Modify: `src/aidb_locator/ui/api/__init__.py`

- [ ] **Step 1: Write the failing test — `tests/ui/test_edit.py`**

```python
from aidb_locator.models import WView


def test_edit_view_calls_codelocator(client, monkeypatch):
    captured = {}

    def fake_edit(self, addr, edit_type, value):
        captured.update(addr=addr, edit_type=edit_type, value=value)
        return True

    monkeypatch.setattr(
        "aidb_locator.ui.api.edit.CodeLocator.edit_view",
        fake_edit,
    )

    resp = client.post(
        "/api/edit",
        json={"view_addr": "abc123", "edit_type": "T", "value": "Hello"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert captured == {"addr": "abc123", "edit_type": "T", "value": "Hello"}


def test_edit_view_failure_returns_502(client, monkeypatch):
    monkeypatch.setattr(
        "aidb_locator.ui.api.edit.CodeLocator.edit_view",
        lambda self, a, t, v: False,
    )
    resp = client.post(
        "/api/edit",
        json={"view_addr": "abc", "edit_type": "T", "value": "x"},
    )
    assert resp.status_code == 502
    assert resp.json()["error"] == "edit_failed"


def test_schema_calls_codelocator(client, monkeypatch):
    captured = {}

    def fake_schema(self, url):
        captured["url"] = url
        return "OK"

    monkeypatch.setattr(
        "aidb_locator.ui.api.edit.CodeLocator.send_schema",
        fake_schema,
    )
    resp = client.post("/api/schema", json={"schema": "demo://home"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "msg": "OK"}
    assert captured == {"url": "demo://home"}


def test_touch_returns_view(client, monkeypatch):
    fake_view = WView(
        class_name="TextView", id_str="tv_title", mem_addr="abc",
        left=10, top=20, right=110, bottom=60,
    )
    monkeypatch.setattr(
        "aidb_locator.ui.api.edit.CodeLocator.get_touch_view",
        lambda self, x, y: fake_view,
    )
    resp = client.post("/api/touch", json={"x": 50, "y": 40})
    assert resp.status_code == 200
    body = resp.json()
    assert body["class_name"] == "TextView"
    assert body["id_str"] == "tv_title"
    assert body["mem_addr"] == "abc"
    assert body["bounds"] == {"left": 10, "top": 20, "right": 110, "bottom": 60}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/ui/test_edit.py -v
```

Expected: 404s.

- [ ] **Step 3: Create `src/aidb_locator/ui/api/edit.py`**

```python
"""Edit / schema / touch endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from aidb_locator.commands import CodeLocator
from aidb_locator.ui.deps import make_codelocator

router = APIRouter()


class EditBody(BaseModel):
    view_addr: str
    edit_type: str
    value: str


class SchemaBody(BaseModel):
    schema: str


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
    msg = make_codelocator(device).send_schema(body.schema)
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
```

- [ ] **Step 4: Register router**

Update `src/aidb_locator/ui/api/__init__.py`:

```python
"""API router aggregator."""

from __future__ import annotations

from fastapi import APIRouter

from aidb_locator.ui.api import devices, edit, snapshot

api_router = APIRouter(prefix="/api")
api_router.include_router(devices.router)
api_router.include_router(snapshot.router)
api_router.include_router(edit.router)
```

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/ui/test_edit.py -v
```

Expected: 4 PASSED.

- [ ] **Step 6: Commit**

```bash
git add tests/ui/test_edit.py \
        src/aidb_locator/ui/api/edit.py \
        src/aidb_locator/ui/api/__init__.py
git commit -m "feat(ui): /api/edit|schema|touch endpoints"
```

---

## Task 6: Backend — capture endpoint (TDD)

**Files:**
- Create: `tests/ui/test_capture.py`
- Create: `src/aidb_locator/ui/api/capture.py`
- Modify: `src/aidb_locator/ui/api/__init__.py`

- [ ] **Step 1: Write the failing test — `tests/ui/test_capture.py`**

```python
def test_capture_returns_png(client, monkeypatch, tmp_path):
    png_bytes = b"\x89PNG\r\n\x1a\nVIEWIMG"
    png_file = tmp_path / "view.png"
    png_file.write_bytes(png_bytes)

    monkeypatch.setattr(
        "aidb_locator.ui.api.capture.CodeLocator.capture_view",
        lambda self, addr, output=None: png_file,
    )

    resp = client.get("/api/capture/abc123")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/png")
    assert resp.content == png_bytes
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/ui/test_capture.py -v
```

Expected: 404.

- [ ] **Step 3: Create `src/aidb_locator/ui/api/capture.py`**

```python
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
```

- [ ] **Step 4: Register router**

Update `src/aidb_locator/ui/api/__init__.py`:

```python
"""API router aggregator."""

from __future__ import annotations

from fastapi import APIRouter

from aidb_locator.ui.api import capture, devices, edit, snapshot

api_router = APIRouter(prefix="/api")
api_router.include_router(devices.router)
api_router.include_router(snapshot.router)
api_router.include_router(edit.router)
api_router.include_router(capture.router)
```

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/ui/test_capture.py -v
```

Expected: 1 PASSED.

- [ ] **Step 6: Commit**

```bash
git add tests/ui/test_capture.py \
        src/aidb_locator/ui/api/capture.py \
        src/aidb_locator/ui/api/__init__.py
git commit -m "feat(ui): /api/capture/{view_addr} endpoint"
```

---

## Task 7: Backend — error mapping integration (TDD)

**Files:**
- Create: `tests/ui/test_errors.py`

- [ ] **Step 1: Write the failing test — `tests/ui/test_errors.py`**

```python
import pytest

from aidb_locator.adb import AdbError


def test_no_device_returns_409(client, monkeypatch):
    def boom(self):
        raise AdbError("no devices/emulators found")
    monkeypatch.setattr(
        "aidb_locator.ui.api.devices.AdbClient.list_devices",
        boom,
    )
    resp = client.get("/api/devices")
    assert resp.status_code == 409
    body = resp.json()
    assert body["error"] == "no_device"


def test_timeout_returns_504(client, monkeypatch):
    def boom(self):
        raise AdbError("ADB command timed out after 10s: ['adb', 'devices']")
    monkeypatch.setattr(
        "aidb_locator.ui.api.devices.AdbClient.list_devices",
        boom,
    )
    resp = client.get("/api/devices")
    assert resp.status_code == 504
    assert resp.json()["error"] == "adb_timeout"


def test_generic_adb_error_returns_502(client, monkeypatch):
    def boom(self):
        raise AdbError("protocol fault: malformed response")
    monkeypatch.setattr(
        "aidb_locator.ui.api.devices.AdbClient.list_devices",
        boom,
    )
    resp = client.get("/api/devices")
    assert resp.status_code == 502
    assert resp.json()["error"] == "adb_error"


def test_device_offline_returns_409(client, monkeypatch):
    def boom(self):
        raise AdbError("device offline")
    monkeypatch.setattr(
        "aidb_locator.ui.api.devices.AdbClient.list_devices",
        boom,
    )
    resp = client.get("/api/devices")
    assert resp.status_code == 409
    assert resp.json()["error"] == "no_device"
```

- [ ] **Step 2: Run test to verify behavior**

```bash
pytest tests/ui/test_errors.py -v
```

Expected: all 3 PASSED (the handler from Task 2 is already wired through `build_app`).

- [ ] **Step 3: Commit**

```bash
git add tests/ui/test_errors.py
git commit -m "test(ui): cover AdbError → HTTP status mapping"
```

---

## Task 8: Server entry — port pick + browser open + uvicorn

**Files:**
- Modify: `src/aidb_locator/ui/server.py`

- [ ] **Step 1: Replace `src/aidb_locator/ui/server.py`**

```python
"""FastAPI server + uvicorn entry."""

from __future__ import annotations

import socket
import threading
import time
import webbrowser
from pathlib import Path

import click
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from aidb_locator.ui import errors
from aidb_locator.ui.api import api_router

STATIC_DIR = Path(__file__).parent / "static"


def build_app() -> FastAPI:
    app = FastAPI(title="aidb-locator UI", version="0.1.0")
    errors.install(app)
    app.include_router(api_router)
    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
    return app


def _pick_port(host: str, start: int) -> int:
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No free port found in {start}..{start + 100}")


def _open_browser_when_ready(url: str) -> None:
    def _open() -> None:
        time.sleep(0.6)
        webbrowser.open(url)
    threading.Thread(target=_open, daemon=True).start()


@click.command()
@click.option("--host", default="127.0.0.1", help="Bind host.")
@click.option("--port", default=0, type=int, help="Bind port (0 = auto-pick from 8765+).")
@click.option("--no-browser", is_flag=True, help="Do not auto-open browser.")
def main(host: str, port: int, no_browser: bool) -> None:
    """Start the aidb-locator local web UI."""
    chosen = _pick_port(host, port if port else 8765)
    url = f"http://{host}:{chosen}"
    click.echo(f"aidb-ui listening on {url}")
    if not no_browser:
        _open_browser_when_ready(url)
    uvicorn.run(build_app(), host=host, port=chosen, log_level="info")
```

- [ ] **Step 2: Manual smoke check (no static yet)**

```bash
aidb-ui --no-browser --port 8765
```

Expected: prints `aidb-ui listening on http://127.0.0.1:8765`, server starts. In another terminal:

```bash
curl -s http://127.0.0.1:8765/api/devices
```

Expected: `[]` (or 409 if no `adb` installed — both fine). Stop server with Ctrl-C.

- [ ] **Step 3: Run all backend tests still pass**

```bash
pytest tests/ui/ -v
```

Expected: all PASSED.

- [ ] **Step 4: Commit**

```bash
git add src/aidb_locator/ui/server.py
git commit -m "feat(ui): aidb-ui CLI entry with port-pick + browser auto-open"
```

---

## Task 9: Frontend — findViewAt pure function + node test

**Files:**
- Create: `src/aidb_locator/ui/static/findViewAt.js`
- Create: `tests/ui/test_findViewAt.mjs`

- [ ] **Step 1: Write the failing test — `tests/ui/test_findViewAt.mjs`**

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { findViewAt } from '../../src/aidb_locator/ui/static/findViewAt.js';

const tree = {
  class_name: 'Root',
  bounds: { left: 0, top: 0, right: 100, bottom: 100 },
  children: [
    {
      class_name: 'A',
      bounds: { left: 0, top: 0, right: 50, bottom: 50 },
      children: [
        { class_name: 'A.leaf', bounds: { left: 10, top: 10, right: 20, bottom: 20 }, children: [] },
      ],
    },
    { class_name: 'B', bounds: { left: 50, top: 0, right: 100, bottom: 50 }, children: [] },
    { class_name: 'Overlay', bounds: { left: 0, top: 0, right: 100, bottom: 50 }, children: [] },
  ],
};

test('returns deepest node containing point', () => {
  const v = findViewAt(tree, 15, 15);
  assert.equal(v.class_name, 'A.leaf');
});

test('returns last drawn child when overlapping at same depth', () => {
  // (60,10) is in B and Overlay (both depth 1, same parent). Overlay drawn last.
  const v = findViewAt(tree, 60, 10);
  assert.equal(v.class_name, 'Overlay');
});

test('returns root when point only in root', () => {
  const v = findViewAt(tree, 80, 80);
  assert.equal(v.class_name, 'Root');
});

test('returns null when point outside root', () => {
  const v = findViewAt(tree, 500, 500);
  assert.equal(v, null);
});

test('returns null on empty tree', () => {
  assert.equal(findViewAt(null, 0, 0), null);
});

test('point on right/bottom edge is excluded (half-open bounds)', () => {
  const v = findViewAt(tree, 50, 50);
  // (50,50) is the right/bottom edge of A and A.leaf (excluded);
  // it IS inside Root (0..100). So we expect Root.
  assert.equal(v.class_name, 'Root');
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
node --test tests/ui/test_findViewAt.mjs
```

Expected: ERR_MODULE_NOT_FOUND.

- [ ] **Step 3: Create `src/aidb_locator/ui/static/findViewAt.js`**

```js
// Pure hit-test for the layout tree.
// Bounds are half-open: x in [left, right), y in [top, bottom).
// Returns the deepest node containing the point. Among siblings at the same
// depth that all contain the point, returns the last one (z-order: later
// siblings are drawn on top).

export function findViewAt(node, x, y) {
  if (!node) return null;
  if (!_contains(node, x, y)) return null;
  return _walk(node, x, y);
}

function _contains(node, x, y) {
  const b = node.bounds;
  if (!b) return false;
  return x >= b.left && x < b.right && y >= b.top && y < b.bottom;
}

function _walk(node, x, y) {
  const children = node.children || [];
  // Walk in reverse so later (top-most) siblings win.
  for (let i = children.length - 1; i >= 0; i--) {
    const c = children[i];
    if (_contains(c, x, y)) {
      return _walk(c, x, y);
    }
  }
  return node;
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
node --test tests/ui/test_findViewAt.mjs
```

Expected: 6 PASSED.

- [ ] **Step 5: Commit**

```bash
git add src/aidb_locator/ui/static/findViewAt.js tests/ui/test_findViewAt.mjs
git commit -m "feat(ui): findViewAt hit-test pure function + node tests"
```

---

## Task 10: Frontend — index.html shell + Vue app skeleton

**Files:**
- Create: `src/aidb_locator/ui/static/index.html`
- Create: `src/aidb_locator/ui/static/style.css`
- Create: `src/aidb_locator/ui/static/app.js`

- [ ] **Step 1: Create `src/aidb_locator/ui/static/style.css`**

```css
html, body, #app { height: 100%; margin: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.tree-node { user-select: none; }
.tree-node.selected > .tree-row { background: rgba(59,130,246,0.15); }
.tree-row { padding: 2px 4px; cursor: pointer; white-space: nowrap; }
.tree-row:hover { background: rgba(0,0,0,0.05); }
canvas.screenshot { cursor: crosshair; max-width: 100%; }
```

- [ ] **Step 2: Create `src/aidb_locator/ui/static/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>aidb-locator UI</title>
  <script src="https://unpkg.com/vue@3/dist/vue.global.prod.js"></script>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="/style.css" />
</head>
<body class="bg-gray-50 text-gray-900">
  <div id="app" class="flex flex-col h-screen">
    <!-- Top bar -->
    <header class="flex items-center gap-4 px-4 py-2 bg-white border-b">
      <select v-model="device" class="border rounded px-2 py-1 text-sm" @change="refresh">
        <option v-for="d in devices" :key="d.serial" :value="d.serial">
          {{ d.serial }} ({{ d.state }})
        </option>
        <option v-if="devices.length === 0" :value="null">(no device)</option>
      </select>
      <div class="flex-1 text-sm">
        <div><b>Activity:</b> {{ snapshot?.activity?.activity || '—' }}</div>
        <div class="text-gray-500"><b>Fragments:</b> {{ snapshot?.activity?.fragments?.join(' › ') || '—' }}</div>
      </div>
      <button @click="refresh" :disabled="loading"
              class="bg-blue-600 text-white text-sm px-3 py-1 rounded disabled:opacity-50">
        {{ loading ? '加载中…' : '🔄 刷新' }}
      </button>
    </header>

    <!-- Error banner -->
    <div v-if="error" class="bg-red-100 text-red-800 text-sm px-4 py-2 border-b border-red-200">
      {{ error }} <button class="underline ml-2" @click="error=null">关闭</button>
    </div>

    <!-- Main 3-column -->
    <main class="flex flex-1 min-h-0">
      <!-- Left: tree -->
      <aside class="w-72 border-r bg-white flex flex-col">
        <input v-model="search" placeholder="🔍 搜索 view (id/class/text)"
               class="m-2 px-2 py-1 border rounded text-sm" />
        <div class="flex-1 overflow-auto px-2 pb-2 text-xs font-mono">
          <tree-node v-if="snapshot?.layout"
                     :node="snapshot.layout"
                     :selected="selected"
                     :search="search"
                     :path="[]"
                     @pick="onPickFromTree" />
        </div>
      </aside>

      <!-- Center: canvas -->
      <section class="flex-1 flex items-center justify-center bg-gray-100 overflow-auto">
        <canvas ref="canvasRef" class="screenshot border bg-white shadow"
                @mousemove="onCanvasMove" @mouseleave="onCanvasLeave"
                @click="onCanvasClick"></canvas>
      </section>

      <!-- Right: details -->
      <aside class="w-80 border-l bg-white overflow-auto">
        <view-details v-if="selected"
                      :node="selected"
                      :device="device"
                      @edit-applied="refresh"
                      @error="msg => error = msg" />
        <div v-else class="p-4 text-sm text-gray-500">
          点击截图或左侧树选中一个 View 查看详情。
        </div>
      </aside>
    </main>

    <!-- Bottom bar -->
    <footer class="flex items-center gap-2 px-4 py-2 bg-white border-t text-sm">
      <span>Schema:</span>
      <input v-model="schemaInput" placeholder="myapp://home"
             class="flex-1 px-2 py-1 border rounded" />
      <button @click="sendSchema" class="bg-blue-600 text-white px-3 py-1 rounded">🚀 跳转</button>
      <button @click="exportLayoutJson" class="bg-gray-200 px-3 py-1 rounded">📥 导出 JSON</button>
    </footer>
  </div>

  <script type="module" src="/app.js"></script>
</body>
</html>
```

- [ ] **Step 3: Create `src/aidb_locator/ui/static/app.js`** (state + refresh + Vue components, all in one file)

```js
import { findViewAt } from '/findViewAt.js';

const { createApp, ref, reactive, computed, watch, onMounted, nextTick, defineComponent, h } = Vue;

// ----- Tree node component -----
const TreeNode = defineComponent({
  name: 'tree-node',
  props: ['node', 'selected', 'search', 'path'],
  emits: ['pick'],
  setup(props, { emit }) {
    const expanded = ref(true);

    const matchesSelf = computed(() => {
      if (!props.search) return true;
      const s = props.search.toLowerCase();
      return [props.node.class_name, props.node.id_str, props.node.text]
        .filter(Boolean).some(x => String(x).toLowerCase().includes(s));
    });

    const hasMatchingDescendant = (n) => {
      if (!props.search) return true;
      const s = props.search.toLowerCase();
      const hit = [n.class_name, n.id_str, n.text]
        .filter(Boolean).some(x => String(x).toLowerCase().includes(s));
      if (hit) return true;
      return (n.children || []).some(hasMatchingDescendant);
    };

    const visible = computed(() => matchesSelf.value || hasMatchingDescendant(props.node));

    // When searching, auto-expand to reveal matches
    watch(() => props.search, () => { if (props.search) expanded.value = true; });

    const isSelected = computed(() =>
      props.selected && props.selected.mem_addr && props.selected.mem_addr === props.node.mem_addr
    );

    return () => {
      if (!visible.value) return null;
      const label = `${props.node.class_name}${props.node.id_str ? '#' + props.node.id_str : ''}`;
      const children = props.node.children || [];
      return h('div', { class: ['tree-node', { selected: isSelected.value }] }, [
        h('div', {
          class: 'tree-row',
          onClick: () => emit('pick', props.node, [...props.path]),
        }, [
          children.length
            ? h('span', { onClick: (e) => { e.stopPropagation(); expanded.value = !expanded.value; } },
                expanded.value ? '▾ ' : '▸ ')
            : h('span', null, '• '),
          label,
        ]),
        expanded.value && children.length
          ? h('div', { style: 'margin-left: 12px' },
              children.map((c, i) => h(TreeNode, {
                node: c, selected: props.selected, search: props.search,
                path: [...props.path, i], onPick: (n, p) => emit('pick', n, p),
              })))
          : null,
      ]);
    };
  },
});

// ----- View details / edit form -----
const EDIT_FIELDS = [
  { code: 'T',    label: '文字',     type: 'text',   from: n => n.text || '' },
  { code: 'P',    label: 'Padding',  type: 'box4',   from: n => (n.padding || [0,0,0,0]).join(',') },
  { code: 'M',    label: 'Margin',   type: 'box4',   from: n => (n.margin  || [0,0,0,0]).join(',') },
  { code: 'A',    label: '透明度',   type: 'alpha',  from: n => String(n.alpha ?? 1) },
  { code: 'B',    label: '背景色',   type: 'color',  from: n => n.background_color || '#ffffff' },
  { code: 'TC',   label: '文字色',   type: 'color',  from: n => n.text_color || '#000000' },
  { code: 'TS',   label: '文字大小', type: 'number', from: n => String(n.text_size || 0) },
  { code: 'VF',   label: '可见性',   type: 'visibility', from: n => n.visibility || 'V' },
];

const ViewDetails = defineComponent({
  name: 'view-details',
  props: ['node', 'device'],
  emits: ['edit-applied', 'error'],
  setup(props, { emit }) {
    const editValues = reactive({});

    watch(() => props.node, (n) => {
      for (const f of EDIT_FIELDS) editValues[f.code] = f.from(n);
    }, { immediate: true });

    const copy = (text) => navigator.clipboard.writeText(text).catch(() => {});

    async function applyEdit(code) {
      try {
        const url = '/api/edit' + (props.device ? `?device=${encodeURIComponent(props.device)}` : '');
        const r = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            view_addr: props.node.mem_addr,
            edit_type: code,
            value: editValues[code],
          }),
        });
        if (!r.ok) {
          const body = await r.json().catch(() => ({}));
          throw new Error(body.message || `HTTP ${r.status}`);
        }
        emit('edit-applied');
      } catch (e) {
        emit('error', `编辑失败: ${e.message}`);
      }
    }

    function exportViewPng() {
      const url = `/api/capture/${encodeURIComponent(props.node.mem_addr)}` +
        (props.device ? `?device=${encodeURIComponent(props.device)}` : '');
      window.open(url, '_blank');
    }

    return () => {
      const n = props.node;
      const b = n.bounds || {};
      const path = (n.class_name || '') + (n.id_str ? `#${n.id_str}` : '');
      return h('div', { class: 'p-3 text-sm space-y-3' }, [
        h('div', { class: 'space-y-1' }, [
          h('div', null, [h('b', null, 'class: '), n.class_name]),
          n.id_str ? h('div', null, [h('b', null, 'id: '), n.id_str]) : null,
          h('div', null, [h('b', null, 'bounds: '), `${b.left},${b.top} → ${b.right},${b.bottom} (${b.right - b.left}×${b.bottom - b.top})`]),
          n.text ? h('div', null, [h('b', null, 'text: '), n.text]) : null,
          n.mem_addr ? h('div', null, [h('b', null, 'mem_addr: '), n.mem_addr]) : null,
        ]),
        h('div', { class: 'flex gap-2 flex-wrap' }, [
          h('button', { class: 'bg-gray-200 px-2 py-1 rounded text-xs', onClick: () => copy(n.id_str || '') }, '📋 复制 id'),
          h('button', { class: 'bg-gray-200 px-2 py-1 rounded text-xs', onClick: () => copy(path) }, '📋 复制路径'),
          h('button', { class: 'bg-gray-200 px-2 py-1 rounded text-xs', onClick: () => copy(`${b.left},${b.top},${b.right},${b.bottom}`) }, '📋 复制坐标'),
        ]),
        h('hr'),
        h('div', { class: 'space-y-2' }, [
          h('div', { class: 'font-bold' }, '编辑属性'),
          ...EDIT_FIELDS.map(f => h('div', { class: 'flex items-center gap-2' }, [
            h('label', { class: 'w-16 text-xs text-gray-600' }, f.label),
            f.type === 'color'
              ? h('input', { type: 'color', value: editValues[f.code],
                  onInput: e => editValues[f.code] = e.target.value,
                  class: 'w-12 h-6' })
              : f.type === 'visibility'
              ? h('select', { value: editValues[f.code],
                  onChange: e => editValues[f.code] = e.target.value,
                  class: 'flex-1 border rounded px-1 text-xs' },
                  ['V','I','G'].map(o => h('option', { value: o }, o)))
              : f.type === 'alpha'
              ? h('input', { type: 'range', min: 0, max: 1, step: 0.01,
                  value: editValues[f.code],
                  onInput: e => editValues[f.code] = e.target.value,
                  class: 'flex-1' })
              : h('input', { type: f.type === 'number' ? 'number' : 'text',
                  value: editValues[f.code],
                  onInput: e => editValues[f.code] = e.target.value,
                  class: 'flex-1 border rounded px-1 text-xs' }),
            h('button', { class: 'bg-blue-600 text-white px-2 py-1 rounded text-xs',
                          onClick: () => applyEdit(f.code) }, '应用'),
          ])),
        ]),
        h('hr'),
        n.mem_addr
          ? h('button', { class: 'bg-gray-200 px-3 py-1 rounded text-xs',
                          onClick: exportViewPng }, '📥 导出该 view 截图')
          : null,
      ]);
    };
  },
});

// ----- Root app -----
createApp({
  components: { 'tree-node': TreeNode, 'view-details': ViewDetails },
  setup() {
    const devices = ref([]);
    const device = ref(null);
    const snapshot = ref(null);
    const selected = ref(null);
    const search = ref('');
    const error = ref(null);
    const loading = ref(false);
    const schemaInput = ref('');
    const canvasRef = ref(null);
    const hover = ref(null);
    const imageEl = ref(null);
    let scale = 1;

    async function fetchJson(url, init) {
      const r = await fetch(url, init);
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        throw new Error(body.message || `HTTP ${r.status}`);
      }
      return r.json();
    }

    async function loadDevices() {
      try {
        devices.value = await fetchJson('/api/devices');
        if (devices.value.length && !device.value) device.value = devices.value[0].serial;
      } catch (e) {
        error.value = `获取设备失败: ${e.message}`;
      }
    }

    async function refresh() {
      if (!device.value && devices.value.length === 0) {
        await loadDevices();
      }
      loading.value = true;
      error.value = null;
      try {
        const url = '/api/snapshot' + (device.value ? `?device=${encodeURIComponent(device.value)}` : '');
        snapshot.value = await fetchJson(url);
        selected.value = null;
        await nextTick();
        renderImage();
      } catch (e) {
        error.value = `刷新失败: ${e.message}`;
      } finally {
        loading.value = false;
      }
    }

    function renderImage() {
      if (!snapshot.value || !canvasRef.value) return;
      const canvas = canvasRef.value;
      const ctx = canvas.getContext('2d');
      const img = new Image();
      img.onload = () => {
        const maxW = 480;
        scale = Math.min(1, maxW / img.naturalWidth);
        canvas.width = img.naturalWidth * scale;
        canvas.height = img.naturalHeight * scale;
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        imageEl.value = img;
        drawOverlays();
      };
      img.src = 'data:image/png;base64,' + snapshot.value.screenshot_png_b64;
    }

    function drawOverlays() {
      if (!canvasRef.value || !imageEl.value) return;
      const canvas = canvasRef.value;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(imageEl.value, 0, 0, canvas.width, canvas.height);
      // hover
      if (hover.value) drawBox(ctx, hover.value, 'rgba(220,38,38,0.9)', true);
      // selected
      if (selected.value) drawBox(ctx, selected.value, 'rgba(37,99,235,0.95)', false);
    }

    function drawBox(ctx, node, color, dashed) {
      const b = node.bounds; if (!b) return;
      ctx.save();
      ctx.lineWidth = 2;
      ctx.strokeStyle = color;
      if (dashed) ctx.setLineDash([6, 4]); else ctx.setLineDash([]);
      ctx.strokeRect(b.left * scale, b.top * scale,
                     (b.right - b.left) * scale, (b.bottom - b.top) * scale);
      ctx.restore();
    }

    let lastMove = 0;
    function onCanvasMove(e) {
      const now = performance.now();
      if (now - lastMove < 33) return;
      lastMove = now;
      const rect = canvasRef.value.getBoundingClientRect();
      const x = (e.clientX - rect.left) / scale;
      const y = (e.clientY - rect.top) / scale;
      hover.value = findViewAt(snapshot.value?.layout, x, y);
      drawOverlays();
    }
    function onCanvasLeave() { hover.value = null; drawOverlays(); }
    function onCanvasClick(e) {
      const rect = canvasRef.value.getBoundingClientRect();
      const x = (e.clientX - rect.left) / scale;
      const y = (e.clientY - rect.top) / scale;
      const hit = findViewAt(snapshot.value?.layout, x, y);
      if (hit) selected.value = hit;
      drawOverlays();
    }

    function onPickFromTree(node) {
      selected.value = node;
      drawOverlays();
    }

    async function sendSchema() {
      if (!schemaInput.value) return;
      try {
        const url = '/api/schema' + (device.value ? `?device=${encodeURIComponent(device.value)}` : '');
        await fetchJson(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ schema: schemaInput.value }),
        });
        await refresh();
      } catch (e) {
        error.value = `Schema 跳转失败: ${e.message}`;
      }
    }

    function exportLayoutJson() {
      if (!snapshot.value?.layout) return;
      const blob = new Blob([JSON.stringify(snapshot.value.layout, null, 2)],
                            { type: 'application/json' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `layout_${Date.now()}.json`;
      a.click();
    }

    onMounted(loadDevices);

    return {
      devices, device, snapshot, selected, search, error, loading,
      schemaInput, canvasRef, hover,
      refresh, onCanvasMove, onCanvasLeave, onCanvasClick,
      onPickFromTree, sendSchema, exportLayoutJson,
    };
  },
}).mount('#app');
```

- [ ] **Step 4: Manual smoke check**

```bash
aidb-ui --no-browser
```

Visit `http://127.0.0.1:8765` in your browser. Expected:
- Page loads with empty state
- "未检测到设备" or empty device dropdown if no device connected
- No JS console errors
- 🔄 button is clickable

Stop server with Ctrl-C.

- [ ] **Step 5: Run all tests still pass**

```bash
pytest tests/ui/ -v && node --test tests/ui/test_findViewAt.mjs
```

Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add src/aidb_locator/ui/static/
git commit -m "feat(ui): Vue 3 frontend — tree, canvas, edit form, schema, export"
```

---

## Task 11: Real-device manual end-to-end

**Files:**
- Create: `tests/ui/MANUAL.md`

- [ ] **Step 1: Create `tests/ui/MANUAL.md`**

```markdown
# Manual e2e checklist for aidb-locator UI

Run these against a real Android device (or emulator) with CodeLocator SDK
integrated into a debug build. Tick each before considering a release ready.

Prereqs:
- `adb devices` shows your device as `device`
- A debug app built with CodeLocator SDK is foreground

## Smoke
- [ ] `aidb-ui` opens browser to `http://127.0.0.1:<port>`
- [ ] Top-right device dropdown shows the connected serial
- [ ] Activity / Fragment names render in top bar
- [ ] Screenshot renders in center panel
- [ ] Left tree renders with `DecorView` at top

## Core: click → layout
- [ ] Click any visible widget on the screenshot → blue box appears around it
- [ ] Left tree expands and highlights the same node
- [ ] Right panel shows class / id / bounds / text / mem_addr

## Hover (A1)
- [ ] Move mouse over screenshot → red dashed box follows the deepest view
- [ ] Move mouse off screenshot → red box disappears

## Search (A3)
- [ ] Type partial id / class / text in left search box → tree filters
- [ ] Parent chain auto-expands to reveal matches
- [ ] Clear search → full tree returns

## Refresh (A4)
- [ ] After app changes screen, click 🔄 → screenshot + tree update

## Edit (B1)
- [ ] Select a TextView → change 文字 → 应用 → screenshot reflects new text
- [ ] Change 透明度 slider to 0.5 → 应用 → view becomes translucent
- [ ] Change 可见性 to G → 应用 → view disappears
- [ ] Set 可见性 back to V → 应用 → view returns

## Activity (B2)
- [ ] Switch app to a different Activity → 🔄 → top bar updates

## Schema (B3)
- [ ] Type a known deep link → 🚀 跳转 → app navigates and snapshot refreshes

## Copy (B4)
- [ ] 📋 复制 id → paste somewhere → matches selected view's id

## Export
- [ ] 📥 导出 JSON → file downloads, contains the layout tree
- [ ] 📥 导出该 view 截图 (C3) → PNG downloads, shows just that view

## Multi-device (D1)
- [ ] With two devices connected, dropdown shows both
- [ ] Switching dropdown auto-refreshes the snapshot for the other device

## Error states
- [ ] Disconnect device → 🔄 → red banner: "未检测到设备"
- [ ] Reconnect → 🔄 → recovers
- [ ] Foreground a non-SDK app → 🔄 → red banner about SDK
```

- [ ] **Step 2: Commit**

```bash
git add tests/ui/MANUAL.md
git commit -m "test(ui): manual e2e checklist for real-device verification"
```

---

## Task 12: README — UI section

**Files:**
- Modify: `README.md` (insert after "## CLI 使用" section, before "## MCP Server")

- [ ] **Step 1: Read current README to find exact insertion point**

```bash
grep -n "^## " README.md
```

Note the line number of `## MCP Server`.

- [ ] **Step 2: Insert UI section before `## MCP Server`**

Add this block:

```markdown
## Web UI (本地浏览器)

```bash
aidb-ui                         # 启动本地服务，自动打开浏览器
aidb-ui --port 8888             # 指定端口
aidb-ui --no-browser            # 只起服务不开浏览器
```

功能：
- 三栏布局：左侧 view 树 + 中间设备截图 + 右侧属性 / 编辑面板
- 点击截图任意位置 → 拉出对应 view（鼠标悬停红框预览，点击蓝框选中）
- 左侧搜索框按 id / class / text 过滤
- 右侧编辑面板可改 padding / margin / 文字 / 颜色 / 可见性 / 透明度等，所见即所得
- 顶部多设备切换；底部 Schema 跳转 + 导出 layout JSON / 单 view 截图
- 手动 🔄 刷新（不做轮询，避免污染设备状态）

```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add Web UI section with aidb-ui usage"
```

---

## Task 13: Final verification

- [ ] **Step 1: Reinstall to pick up packaged static assets**

```bash
pip3 install -e .
```

- [ ] **Step 2: Confirm static files are reachable from the installed package**

```bash
python3 -c "from aidb_locator.ui.server import STATIC_DIR; print(STATIC_DIR.exists()); print(list(STATIC_DIR.iterdir()))"
```

Expected: `True` and a list containing `index.html`, `app.js`, `findViewAt.js`, `style.css`.

- [ ] **Step 3: Run the full test suite**

```bash
pytest tests/ -v && node --test tests/ui/test_findViewAt.mjs
```

Expected: all green.

- [ ] **Step 4: Smoke test the binary**

```bash
aidb-ui --no-browser --port 8765 &
sleep 2
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8765/
curl -s http://127.0.0.1:8765/api/devices
kill %1
```

Expected: index returns `200`, `/api/devices` returns JSON (either array or 409 error body).

- [ ] **Step 5: Walk the manual checklist**

Open `tests/ui/MANUAL.md` and run through each item against a real device.

- [ ] **Step 6: Final tag commit (if anything was tweaked)**

```bash
git status
# only commit if there are uncommitted tweaks from manual testing
```

---

## Self-Review Notes

- **Spec coverage:** Every feature from the spec is mapped to a task — A1 hover (Task 10 `onCanvasMove`/`drawOverlays`), A3 search (Task 10 `TreeNode` filter), A4 manual refresh (Task 10 `refresh`), B1 edit (Task 10 `ViewDetails` + Task 5 backend), B2 Activity/Fragment (Task 4 backend + Task 10 top bar), B3 schema (Task 5 + Task 10 footer), B4 copy (Task 10 `ViewDetails`), C2 export JSON (Task 10 `exportLayoutJson`), C3 export view PNG (Task 6 backend + Task 10 button), D1 multi-device (Task 3 backend + Task 10 dropdown). Core "click → layout" via Task 9 `findViewAt` + Task 10 `onCanvasClick`.
- **Type consistency:** All endpoints accept `device` as a query param matching frontend `?device=...`. `view_addr` / `mem_addr` naming is consistent (server JSON uses `mem_addr`; edit body uses `view_addr` matching upstream `CodeLocator.edit_view` arg name). `bounds` is `{left,top,right,bottom}` everywhere.
- **No placeholders:** Every step has actual code or commands.
- **Out-of-scope items** from spec (A2/C1/D2/D3/WebSocket) are explicitly absent from tasks.
