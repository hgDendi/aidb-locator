"""High-level API for CodeLocator capabilities."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from aidb_locator.adb import AdbClient
from aidb_locator.models import (
    WApplication,
    WFile,
    WView,
    parse_application,
)
from aidb_locator.protocol import (
    ACTION_CHANGE_VIEW,
    ACTION_DEBUG_FILE_INFO,
    ACTION_DEBUG_FILE_OP,
    ACTION_GET_TOUCH_VIEW,
    ACTION_LAYOUT_INFO,
    ACTION_MOCK_TOUCH_VIEW,
    ACTION_PROCESS_SCHEMA,
    EDIT_GET_DATA,
    EDIT_SET_DATA,
    EDIT_VIEW_BITMAP,
    KEY_CHANGE_VIEW,
    KEY_DATA,
    KEY_FILE_OPERATE,
    KEY_MOCK_CLICK_X,
    KEY_MOCK_CLICK_Y,
    KEY_SOURCE_PATH,
    KEY_TARGET_PATH,
    RESULT_IMAGE_PATH,
    decode_inline_result,
    decode_file_result,
    extract_result_data,
)


class CodeLocator:
    def __init__(self, adb: AdbClient):
        self._adb = adb

    def _send(self, action: str, args: dict[str, str] | None = None) -> dict:
        """Send broadcast and parse response."""
        raw = self._adb.broadcast(action, args)
        data_str, is_file = extract_result_data(raw)

        if data_str is None:
            return {"code": -1, "msg": "No data in response"}

        if is_file:
            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
                local = self._adb.pull(data_str, tmp.name)
                content = local.read_bytes()
            return decode_file_result(content)

        return decode_inline_result(data_str)

    def grab_layout(self) -> WApplication:
        """Grab full layout info: View tree, Activity, Fragments, Schemas."""
        response = self._send(ACTION_LAYOUT_INFO)
        return parse_application(response)

    def edit_view(self, view_mem_addr: str, edit_type: str, value: str) -> bool:
        """Edit a View property by memory address (hex identityHashCode)."""
        operate_data = self._build_operate_data(view_mem_addr, edit_type, value)
        response = self._send(ACTION_CHANGE_VIEW, {KEY_CHANGE_VIEW: operate_data})
        return response.get("code", -1) == 0

    def get_touch_view(self, x: int, y: int) -> WView:
        """Get the View at the given touch coordinates."""
        response = self._send(
            ACTION_GET_TOUCH_VIEW,
            {KEY_MOCK_CLICK_X: str(x), KEY_MOCK_CLICK_Y: str(y)},
        )
        data = response.get("data", {})
        if isinstance(data, list):
            data = data[0] if data else {}
        return WView.from_dict(data)

    def mock_touch(self, x: int, y: int) -> bool:
        """Simulate a touch event at the given coordinates."""
        response = self._send(
            ACTION_MOCK_TOUCH_VIEW,
            {KEY_MOCK_CLICK_X: str(x), KEY_MOCK_CLICK_Y: str(y)},
        )
        return response.get("code", -1) == 0

    def send_schema(self, url: str) -> str:
        """Send a deep link (schema) to the app."""
        response = self._send(ACTION_PROCESS_SCHEMA, {KEY_DATA: url})
        return response.get("msg", "")

    def list_files(self) -> WFile:
        """List the app's file system tree."""
        response = self._send(ACTION_DEBUG_FILE_INFO)
        return WFile.from_dict(response.get("data", {}))

    def operate_file(self, source: str, target: str, op: str) -> bool:
        """Operate on a file (copy, move, delete, etc.)."""
        response = self._send(
            ACTION_DEBUG_FILE_OP,
            {KEY_SOURCE_PATH: source, KEY_TARGET_PATH: target, KEY_FILE_OPERATE: op},
        )
        return response.get("code", -1) == 0

    def _build_operate_data(self, view_mem_addr: str, edit_type: str, args: str = "") -> str:
        """Build OperateData JSON for change view actions."""
        import json as _json
        item_id = int(view_mem_addr, 16)
        return _json.dumps({
            "aa": "V",
            "d4": item_id,
            "d5": [{"d7": edit_type, "d8": args}],
        })

    def capture_view(self, view_mem_addr: str, output: str | Path | None = None) -> Path:
        """Capture a View's rendered bitmap."""
        operate_data = self._build_operate_data(view_mem_addr, EDIT_VIEW_BITMAP)
        self._send(ACTION_CHANGE_VIEW, {KEY_CHANGE_VIEW: operate_data})

        if output is None:
            output = Path(tempfile.mktemp(suffix=".png"))
        output = Path(output)
        return self._adb.pull(RESULT_IMAGE_PATH, output)

    def get_view_data(self, view_mem_addr: str) -> dict:
        """Get data bound to a View."""
        operate_data = self._build_operate_data(view_mem_addr, EDIT_GET_DATA)
        response = self._send(ACTION_CHANGE_VIEW, {KEY_CHANGE_VIEW: operate_data})
        data = response.get("data", "")
        if isinstance(data, str):
            try:
                return json.loads(data)
            except (json.JSONDecodeError, TypeError):
                return {"raw": data}
        return data if isinstance(data, dict) else {"raw": str(data)}

    def set_view_data(self, view_mem_addr: str, data: str) -> bool:
        """Set data on a View."""
        operate_data = self._build_operate_data(view_mem_addr, EDIT_SET_DATA, data)
        response = self._send(ACTION_CHANGE_VIEW, {KEY_CHANGE_VIEW: operate_data})
        return response.get("code", -1) == 0
