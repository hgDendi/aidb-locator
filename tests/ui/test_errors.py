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


def test_unauthorized_device_returns_409(client, monkeypatch):
    def boom(self):
        raise AdbError("error: device unauthorized. Please check the confirmation dialog.")
    monkeypatch.setattr(
        "aidb_locator.ui.api.devices.AdbClient.list_devices",
        boom,
    )
    resp = client.get("/api/devices")
    assert resp.status_code == 409
    assert resp.json()["error"] == "no_device"


def test_adb_missing_returns_500(client, monkeypatch):
    def boom(self):
        raise AdbError("adb not found. Make sure Android SDK platform-tools is in your PATH.")
    monkeypatch.setattr(
        "aidb_locator.ui.api.devices.AdbClient.list_devices",
        boom,
    )
    resp = client.get("/api/devices")
    assert resp.status_code == 500
    assert resp.json()["error"] == "adb_missing"
