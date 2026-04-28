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
