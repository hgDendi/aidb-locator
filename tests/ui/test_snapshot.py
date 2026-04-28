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
