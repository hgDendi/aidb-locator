from __future__ import annotations

import base64
import json
import zlib
from unittest.mock import MagicMock, patch

from aidb_locator.commands import CodeLocator
from aidb_locator.adb import AdbClient
from aidb_locator.models import WApplication


def _make_broadcast_output(data: dict) -> str:
    """Helper: wrap a dict into a broadcast inline result string."""
    json_str = json.dumps(data)
    compressed = zlib.compress(json_str.encode("utf-8"))
    b64 = base64.b64encode(compressed).decode("ascii")
    return f'Broadcasting: ...\nresult=0\ndata="{b64}"'


class TestGrabLayout:
    def test_grab_layout_returns_application(self):
        app_data = {
            "code": 0,
            "data": {
                "bd": "com.example.app",
                "b7": {
                    "ag": "com.example.MainActivity",
                    "cj": [{"ag": "FrameLayout", "ab": "V", "d": 0, "e": 1080, "f": 0, "g": 2340}],
                    "ck": [{"ag": "HomeFragment", "cd": True, "ce": True}],
                },
                "bc": [],
            },
        }
        mock_adb = MagicMock(spec=AdbClient)
        mock_adb.broadcast.return_value = _make_broadcast_output(app_data)

        locator = CodeLocator(mock_adb)
        result = locator.grab_layout()

        assert isinstance(result, WApplication)
        assert result.package_name == "com.example.app"
        assert result.activity.class_name == "com.example.MainActivity"
        assert len(result.activity.fragments) == 1


class TestGetTouchView:
    def test_get_touch_view(self):
        view_data = {
            "code": 0,
            "data": {
                "ag": "android.widget.Button",
                "ab": "V",
                "ac": "submit_btn",
                "d": 100, "e": 300, "f": 500, "g": 580,
            },
        }
        mock_adb = MagicMock(spec=AdbClient)
        mock_adb.broadcast.return_value = _make_broadcast_output(view_data)

        locator = CodeLocator(mock_adb)
        view = locator.get_touch_view(200, 540)

        assert view.class_name == "android.widget.Button"
        assert view.id_str == "submit_btn"


class TestMockTouch:
    def test_mock_touch_success(self):
        result_data = {"code": 0, "msg": "success"}
        mock_adb = MagicMock(spec=AdbClient)
        mock_adb.broadcast.return_value = _make_broadcast_output(result_data)

        locator = CodeLocator(mock_adb)
        assert locator.mock_touch(540, 960) is True


class TestSendSchema:
    def test_send_schema(self):
        result_data = {"code": 0, "msg": "success", "data": "navigated"}
        mock_adb = MagicMock(spec=AdbClient)
        mock_adb.broadcast.return_value = _make_broadcast_output(result_data)

        locator = CodeLocator(mock_adb)
        result = locator.send_schema("myapp://home")
        assert result is not None


class TestEditView:
    def test_edit_view_text(self):
        result_data = {"code": 0, "msg": "success"}
        mock_adb = MagicMock(spec=AdbClient)
        mock_adb.broadcast.return_value = _make_broadcast_output(result_data)

        locator = CodeLocator(mock_adb)
        assert locator.edit_view("0x1234", "T", "New Text") is True
