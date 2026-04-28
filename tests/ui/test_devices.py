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
