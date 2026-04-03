# aidb-locator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI + MCP Server that wraps the CodeLocator ADB protocol, enabling AI agents to inspect and manipulate Android UI without Android Studio.

**Architecture:** Single-package architecture with layered dependencies: `cli/mcp_server → commands → protocol → adb`. All code lives in `src/aidb_locator/`. JSON field names from the upstream SDK use abbreviated 2-3 char codes (e.g., `"ag"` for className) — models must handle this mapping.

**Tech Stack:** Python 3.10+, Click (CLI), MCP SDK (server), subprocess (ADB), pytest (testing)

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/aidb_locator/__init__.py`
- Create: `tests/__init__.py`
- Create: `LICENSE`
- Create: `README.md`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "aidb-locator"
version = "0.1.0"
description = "AI-powered Android Debug Bridge — CLI & MCP Server for Android UI inspection"
readme = "README.md"
license = "Apache-2.0"
requires-python = ">=3.10"
authors = [
    { name = "dendi" },
]
keywords = ["android", "adb", "mcp", "ui-inspection", "ai"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3",
    "Topic :: Software Development :: Debuggers",
]
dependencies = [
    "click>=8.0",
    "mcp>=1.0",
]

[project.scripts]
aidb = "aidb_locator.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.hatch.build.targets.wheel]
packages = ["src/aidb_locator"]
```

- [ ] **Step 2: Create src/aidb_locator/__init__.py**

```python
"""aidb-locator: AI-powered Android Debug Bridge."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Create tests/__init__.py**

```python
```

(Empty file.)

- [ ] **Step 4: Create LICENSE**

Copy the Apache 2.0 license text. Set copyright line:

```
Copyright 2026 aidb-locator contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

- [ ] **Step 5: Create README.md**

```markdown
# aidb-locator

AI-powered Android Debug Bridge — CLI & MCP Server for Android UI inspection and manipulation.

> Built on the [CodeLocator](https://github.com/bytedance/CodeLocator) protocol by ByteDance. Licensed under Apache 2.0.

## Features

- Grab full View hierarchy with Activity/Fragment info
- Edit View properties in real-time (padding, margin, text, visibility, etc.)
- Locate Views by touch coordinates
- Simulate touch events
- Send deep links (schemas)
- Browse and operate on app files
- Capture View screenshots
- Get/set View-bound data
- MCP Server for AI agent integration

## Install

```bash
pip install aidb-locator
```

## Prerequisites

- Android device with CodeLocator SDK integrated (debug build)
- `adb` available in PATH

## CLI Usage

```bash
aidb devices                          # List connected devices
aidb layout [--json]                  # View tree + Activity/Fragment info
aidb touch 540 500                    # Find View at coordinates
aidb click 540 500                    # Simulate tap
aidb edit <view_id> T "Hello"         # Edit View text
aidb schema "myapp://home"            # Send deep link
aidb files                            # Browse app files
aidb capture <view_id> -o shot.png    # Screenshot a View
aidb view-data <view_id>              # Get View-bound data
```

## MCP Server

```bash
aidb serve
```

Configure in Claude Code / Cursor:

```json
{
  "mcpServers": {
    "aidb-locator": {
      "command": "aidb",
      "args": ["serve"]
    }
  }
}
```

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.

This project is a CLI/MCP client for the [CodeLocator](https://github.com/bytedance/CodeLocator) protocol, originally developed by ByteDance.
```

- [ ] **Step 6: Install project in dev mode and verify**

Run: `cd ~/Desktop/CodeLocator_CLI && pip install -e ".[dev]" 2>&1 | tail -5`

Expected: Successfully installed aidb-locator

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/ tests/ LICENSE README.md
git commit -m "chore: project scaffolding with pyproject.toml, README, LICENSE"
```

---

### Task 2: Protocol Layer — Constants & Encoding

**Files:**
- Create: `src/aidb_locator/protocol.py`
- Create: `tests/test_protocol.py`

- [ ] **Step 1: Write failing tests for encode/decode**

```python
# tests/test_protocol.py
import base64
import json
import zlib

from aidb_locator.protocol import (
    ACTION_LAYOUT_INFO,
    ACTION_CHANGE_VIEW,
    KEY_SHELL_ARGS,
    encode_args,
    decode_inline_result,
    extract_result_data,
)


class TestConstants:
    def test_action_layout_info_value(self):
        assert ACTION_LAYOUT_INFO == "com.bytedance.tools.codelocator.action_debug_layout_info"

    def test_action_change_view_value(self):
        assert ACTION_CHANGE_VIEW == "com.bytedance.tools.codelocator.action_change_view_info"

    def test_key_shell_args_value(self):
        assert KEY_SHELL_ARGS == "codeLocator_shell_args"


class TestEncodeArgs:
    def test_encode_empty_dict(self):
        result = encode_args({})
        decoded = json.loads(base64.b64decode(result))
        assert decoded == {}

    def test_encode_simple_args(self):
        args = {"key1": "value1", "key2": "value2"}
        result = encode_args(args)
        decoded = json.loads(base64.b64decode(result))
        assert decoded == args

    def test_encode_with_unicode(self):
        args = {"name": "测试"}
        result = encode_args(args)
        decoded = json.loads(base64.b64decode(result))
        assert decoded["name"] == "测试"


class TestDecodeResult:
    def _make_inline(self, data: dict) -> str:
        """Helper: dict → compressed base64 inline result string."""
        json_str = json.dumps(data)
        compressed = zlib.compress(json_str.encode("utf-8"))
        b64 = base64.b64encode(compressed).decode("ascii")
        return f'data="{b64}"'

    def test_decode_inline_result(self):
        original = {"code": 0, "msg": "success", "data": {"activity": "MainActivity"}}
        raw = self._make_inline(original)
        result = decode_inline_result(raw)
        assert result == original

    def test_extract_result_data_inline(self):
        original = {"code": 0, "data": "hello"}
        raw = f'Broadcasting: ... result=0\n{self._make_inline(original)}'
        data, is_file = extract_result_data(raw)
        assert not is_file
        assert data is not None

    def test_extract_result_data_file_path(self):
        raw = 'Broadcasting: ... result=0\nFP:/sdcard/Download/codeLocator_data.txt'
        data, is_file = extract_result_data(raw)
        assert is_file
        assert data == "/sdcard/Download/codeLocator_data.txt"

    def test_extract_result_data_no_data(self):
        raw = "Broadcasting: ... result=-1"
        data, is_file = extract_result_data(raw)
        assert data is None
        assert not is_file
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/Desktop/CodeLocator_CLI && python -m pytest tests/test_protocol.py -v 2>&1 | head -20`

Expected: FAILED — ModuleNotFoundError: No module named 'aidb_locator.protocol'

- [ ] **Step 3: Implement protocol.py**

```python
# src/aidb_locator/protocol.py
"""CodeLocator ADB broadcast protocol — constants, encoding, decoding."""

from __future__ import annotations

import base64
import json
import re
import zlib

# --- Broadcast Actions ---

_PREFIX = "com.bytedance.tools.codelocator"

ACTION_LAYOUT_INFO = f"{_PREFIX}.action_debug_layout_info"
ACTION_CHANGE_VIEW = f"{_PREFIX}.action_change_view_info"
ACTION_GET_TOUCH_VIEW = f"{_PREFIX}.action_get_touch_view"
ACTION_MOCK_TOUCH_VIEW = f"{_PREFIX}.action_mock_touch_view"
ACTION_PROCESS_SCHEMA = f"{_PREFIX}.action_process_schema"
ACTION_DEBUG_FILE_INFO = f"{_PREFIX}.action_debug_file_info"
ACTION_DEBUG_FILE_OP = f"{_PREFIX}.action_debug_file_operate"
ACTION_OPERATE_CUSTOM = f"{_PREFIX}.action_operate_custom_file"
ACTION_USE_TOOLS_INFO = f"{_PREFIX}.action_use_tools_info"
ACTION_PROCESS_CONFIG = f"{_PREFIX}.action_process_config_list"
ACTION_CONFIG_SDK = f"{_PREFIX}.action_config_sdk"

# --- Argument Keys ---

KEY_SHELL_ARGS = "codeLocator_shell_args"
KEY_ASYNC = "codeLocator_save_async"
KEY_CHANGE_VIEW = "codeLocator_change_view"
KEY_MOCK_CLICK_X = "codeLocator_mock_click_x"
KEY_MOCK_CLICK_Y = "codeLocator_mock_click_y"
KEY_DATA = "codeLocator_data"
KEY_SAVE_TO_FILE = "codeLocator_save_to_file"
KEY_ACTION = "codeLocator_action"
KEY_SOURCE_PATH = "codeLocator_process_source_file_path"
KEY_TARGET_PATH = "codeLocator_process_target_file_path"
KEY_FILE_OPERATE = "codeLocator_process_file_operate"

# --- EditType Constants ---

EDIT_PADDING = "P"
EDIT_MARGIN = "M"
EDIT_BACKGROUND = "B"
EDIT_VIEW_FLAG = "VF"
EDIT_LAYOUT_PARAMS = "LP"
EDIT_TRANSLATION = "TXY"
EDIT_SCROLL = "SXY"
EDIT_SCALE = "SCXY"
EDIT_PIVOT = "PXY"
EDIT_TEXT = "T"
EDIT_TEXT_COLOR = "TC"
EDIT_TEXT_SIZE = "TS"
EDIT_LINE_SPACE = "LS"
EDIT_SHADOW_XY = "SA"
EDIT_SHADOW_RADIUS = "SR"
EDIT_SHADOW_COLOR = "SC"
EDIT_MIN_HEIGHT = "MH"
EDIT_MIN_WIDTH = "MW"
EDIT_ALPHA = "A"
EDIT_VIEW_BITMAP = "VB"
EDIT_LAYER_BITMAP = "DLB"
EDIT_FOREGROUND = "OF"
EDIT_BACKGROUND_ONLY = "OB"
EDIT_GET_DATA = "GVD"
EDIT_SET_DATA = "SVD"
EDIT_GET_CLASS = "GVCI"
EDIT_GET_INTENT = "GI"
EDIT_CLOSE_ACTIVITY = "CA"
EDIT_INVOKE = "IK"
EDIT_IGNORE = "X"

# --- Result Paths ---

RESULT_DATA_PATH = "/sdcard/Download/codeLocator_data.txt"
RESULT_IMAGE_PATH = "/sdcard/Download/codeLocator_image.png"
BASE_DIR = "/sdcard/codeLocator"
BASE_TMP_DIR = "/data/local/tmp/codeLocator"

# --- Inline data pattern ---

_DATA_PATTERN = re.compile(r'data="([^"]+)"')
_FP_PATTERN = re.compile(r"FP:(\S+)")


def encode_args(args: dict[str, str]) -> str:
    """Encode argument dict to Base64 JSON string for broadcast extras."""
    json_str = json.dumps(args, ensure_ascii=False)
    return base64.b64encode(json_str.encode("utf-8")).decode("ascii")


def decode_inline_result(raw: str) -> dict:
    """Decode an inline result string: extract data="...", Base64 decode, decompress, JSON parse."""
    match = _DATA_PATTERN.search(raw)
    if not match:
        raise ValueError(f"No inline data found in: {raw[:200]}")
    b64_data = match.group(1)
    compressed = base64.b64decode(b64_data)
    json_bytes = zlib.decompress(compressed)
    return json.loads(json_bytes)


def decode_file_result(file_content: bytes) -> dict:
    """Decode a file-based result: Base64 decode, decompress, JSON parse."""
    compressed = base64.b64decode(file_content)
    json_bytes = zlib.decompress(compressed)
    return json.loads(json_bytes)


def extract_result_data(raw_output: str) -> tuple[str | None, bool]:
    """Extract result data from broadcast output.

    Returns:
        (data, is_file) where:
        - If inline: data is the raw inline string, is_file=False
        - If file path: data is the file path, is_file=True
        - If no data: data is None, is_file=False
    """
    fp_match = _FP_PATTERN.search(raw_output)
    if fp_match:
        return fp_match.group(1), True

    data_match = _DATA_PATTERN.search(raw_output)
    if data_match:
        return raw_output, False

    return None, False


def build_broadcast_command(action: str, args: dict[str, str] | None = None) -> list[str]:
    """Build the ADB shell broadcast command args list.

    Returns the args after 'adb shell', e.g.:
    ['am', 'broadcast', '-a', ACTION, '--es', KEY, ENCODED_ARGS]
    """
    cmd = ["am", "broadcast", "-a", action]
    if args:
        encoded = encode_args(args)
        cmd.extend(["--es", KEY_SHELL_ARGS, encoded])
    return cmd
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/Desktop/CodeLocator_CLI && python -m pytest tests/test_protocol.py -v`

Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/CodeLocator_CLI
git add src/aidb_locator/protocol.py tests/test_protocol.py
git commit -m "feat: protocol layer with constants, encode/decode, and tests"
```

---

### Task 3: ADB Client Layer

**Files:**
- Create: `src/aidb_locator/adb.py`
- Create: `tests/test_adb.py`

- [ ] **Step 1: Write failing tests for AdbClient**

```python
# tests/test_adb.py
from __future__ import annotations

import subprocess
from unittest.mock import patch, MagicMock
from pathlib import Path

from aidb_locator.adb import AdbClient, AdbError, Device


class TestAdbClientBuildCmd:
    def test_no_serial(self):
        client = AdbClient()
        cmd = client._build_cmd(["shell", "ls"])
        assert cmd == ["adb", "shell", "ls"]

    def test_with_serial(self):
        client = AdbClient(device_serial="abc123")
        cmd = client._build_cmd(["shell", "ls"])
        assert cmd == ["adb", "-s", "abc123", "shell", "ls"]


class TestAdbClientShell:
    @patch("aidb_locator.adb.subprocess.run")
    def test_shell_success(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="output\n", stderr=""
        )
        client = AdbClient()
        result = client.shell("ls /sdcard")
        assert result == "output\n"
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ["adb", "shell", "ls /sdcard"]

    @patch("aidb_locator.adb.subprocess.run")
    def test_shell_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="adb", timeout=10)
        client = AdbClient()
        try:
            client.shell("hang")
            assert False, "Should have raised AdbError"
        except AdbError as e:
            assert "timed out" in str(e).lower()


class TestListDevices:
    @patch("aidb_locator.adb.subprocess.run")
    def test_parse_devices(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="List of devices attached\nabc123\tdevice\ndef456\toffline\n\n",
            stderr="",
        )
        client = AdbClient()
        devices = client.list_devices()
        assert len(devices) == 2
        assert devices[0] == Device(serial="abc123", state="device")
        assert devices[1] == Device(serial="def456", state="offline")

    @patch("aidb_locator.adb.subprocess.run")
    def test_no_devices(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="List of devices attached\n\n",
            stderr="",
        )
        client = AdbClient()
        devices = client.list_devices()
        assert devices == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/Desktop/CodeLocator_CLI && python -m pytest tests/test_adb.py -v 2>&1 | head -20`

Expected: FAILED — ModuleNotFoundError: No module named 'aidb_locator.adb'

- [ ] **Step 3: Implement adb.py**

```python
# src/aidb_locator/adb.py
"""ADB client — subprocess wrapper for adb commands."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


class AdbError(Exception):
    """Raised when an ADB command fails."""


@dataclass(frozen=True)
class Device:
    serial: str
    state: str


class AdbClient:
    def __init__(self, device_serial: str | None = None, timeout: int = 10):
        self._serial = device_serial
        self._timeout = timeout

    def _build_cmd(self, args: list[str]) -> list[str]:
        cmd = ["adb"]
        if self._serial:
            cmd.extend(["-s", self._serial])
        cmd.extend(args)
        return cmd

    def _run(self, args: list[str], timeout: int | None = None) -> str:
        cmd = self._build_cmd(args)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout or self._timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise AdbError(f"ADB command timed out after {self._timeout}s: {cmd}") from e
        except FileNotFoundError as e:
            raise AdbError(
                "adb not found. Make sure Android SDK platform-tools is in your PATH."
            ) from e

        if result.returncode != 0 and result.stderr.strip():
            raise AdbError(f"ADB error: {result.stderr.strip()}")
        return result.stdout

    def shell(self, command: str) -> str:
        """Run an adb shell command and return stdout."""
        return self._run(["shell", command])

    def broadcast(self, action: str, args: dict[str, str] | None = None) -> str:
        """Send a broadcast via adb shell am broadcast."""
        from aidb_locator.protocol import build_broadcast_command

        shell_args = build_broadcast_command(action, args)
        shell_cmd = " ".join(f"'{a}'" if " " in a else a for a in shell_args)
        return self._run(["shell", shell_cmd], timeout=30)

    def pull(self, remote_path: str, local_path: str | Path) -> Path:
        """Pull a file from device to local path."""
        local = Path(local_path)
        local.parent.mkdir(parents=True, exist_ok=True)
        self._run(["pull", remote_path, str(local)])
        if not local.exists():
            raise AdbError(f"Pull succeeded but file not found: {local}")
        return local

    def list_devices(self) -> list[Device]:
        """List connected ADB devices."""
        output = self._run(["devices"])
        devices = []
        for line in output.strip().splitlines()[1:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) == 2:
                devices.append(Device(serial=parts[0], state=parts[1]))
        return devices
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/Desktop/CodeLocator_CLI && python -m pytest tests/test_adb.py -v`

Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/CodeLocator_CLI
git add src/aidb_locator/adb.py tests/test_adb.py
git commit -m "feat: ADB client layer with subprocess wrapper and tests"
```

---

### Task 4: Data Models

**Files:**
- Create: `src/aidb_locator/models.py`
- Create: `tests/test_models.py`

The upstream SDK uses abbreviated JSON field names (e.g., `"ag"` for className, `"a"` for children). Models must map these to readable Python field names.

- [ ] **Step 1: Write failing tests for model parsing**

```python
# tests/test_models.py
from aidb_locator.models import (
    WView,
    WFragment,
    WActivity,
    WFile,
    WApplication,
    parse_application,
)


class TestWView:
    def test_parse_minimal_view(self):
        raw = {
            "ag": "android.widget.TextView",
            "ab": "V",
            "d": 0, "e": 100, "f": 0, "g": 50,
        }
        view = WView.from_dict(raw)
        assert view.class_name == "android.widget.TextView"
        assert view.visibility == "V"
        assert view.left == 0
        assert view.right == 100
        assert view.top == 0
        assert view.bottom == 50

    def test_parse_view_with_text(self):
        raw = {
            "ag": "android.widget.TextView",
            "ab": "V",
            "ac": "title",
            "aq": "Hello World",
            "d": 0, "e": 200, "f": 0, "g": 48,
        }
        view = WView.from_dict(raw)
        assert view.id_str == "title"
        assert view.text == "Hello World"

    def test_parse_view_with_children(self):
        raw = {
            "ag": "android.widget.FrameLayout",
            "ab": "V",
            "d": 0, "e": 1080, "f": 0, "g": 2340,
            "a": [
                {"ag": "android.widget.TextView", "ab": "V", "d": 0, "e": 100, "f": 0, "g": 50},
                {"ag": "android.widget.Button", "ab": "V", "d": 0, "e": 200, "f": 50, "g": 100},
            ],
        }
        view = WView.from_dict(raw)
        assert len(view.children) == 2
        assert view.children[0].class_name == "android.widget.TextView"
        assert view.children[1].class_name == "android.widget.Button"

    def test_view_to_dict(self):
        raw = {
            "ag": "android.widget.TextView",
            "ab": "V",
            "ac": "btn",
            "aq": "Click me",
            "d": 10, "e": 200, "f": 20, "g": 80,
        }
        view = WView.from_dict(raw)
        d = view.to_dict()
        assert d["class_name"] == "android.widget.TextView"
        assert d["id"] == "btn"
        assert d["text"] == "Click me"
        assert d["bounds"] == {"left": 10, "top": 20, "right": 200, "bottom": 80}


class TestWFragment:
    def test_parse_fragment(self):
        raw = {
            "ag": "com.example.HomeFragment",
            "cd": True,
            "ce": True,
            "af": "0x1234",
        }
        frag = WFragment.from_dict(raw)
        assert frag.class_name == "com.example.HomeFragment"
        assert frag.is_visible is True
        assert frag.is_added is True

    def test_parse_nested_fragments(self):
        raw = {
            "ag": "ParentFragment",
            "cd": True,
            "ce": True,
            "a": [
                {"ag": "ChildFragment", "cd": True, "ce": True},
            ],
        }
        frag = WFragment.from_dict(raw)
        assert len(frag.children) == 1
        assert frag.children[0].class_name == "ChildFragment"


class TestWFile:
    def test_parse_file(self):
        raw = {
            "c6": "config.json",
            "c7": "/data/data/com.example/files/config.json",
            "c1": 1024,
            "c2": False,
            "c3": True,
        }
        f = WFile.from_dict(raw)
        assert f.name == "config.json"
        assert f.absolute_path == "/data/data/com.example/files/config.json"
        assert f.size == 1024
        assert f.is_directory is False

    def test_parse_directory_with_children(self):
        raw = {
            "c6": "files",
            "c7": "/data/data/com.example/files",
            "c1": 0,
            "c2": True,
            "c3": True,
            "a": [
                {"c6": "a.txt", "c7": "/data/data/com.example/files/a.txt", "c1": 100, "c2": False, "c3": True},
            ],
        }
        f = WFile.from_dict(raw)
        assert f.is_directory is True
        assert len(f.children) == 1
        assert f.children[0].name == "a.txt"


class TestWApplication:
    def test_parse_application(self):
        raw = {
            "code": 0,
            "msg": "success",
            "data": {
                "bd": "com.example.app",
                "b7": {
                    "ag": "com.example.MainActivity",
                    "cj": [
                        {
                            "ag": "android.widget.FrameLayout",
                            "ab": "V",
                            "d": 0, "e": 1080, "f": 0, "g": 2340,
                        }
                    ],
                    "ck": [
                        {"ag": "HomeFragment", "cd": True, "ce": True},
                    ],
                },
                "bc": [
                    {"db": "myapp://home", "dc": "Home page"},
                ],
            },
        }
        app = parse_application(raw)
        assert app.package_name == "com.example.app"
        assert app.activity.class_name == "com.example.MainActivity"
        assert len(app.activity.decor_views) == 1
        assert len(app.activity.fragments) == 1
        assert app.activity.fragments[0].class_name == "HomeFragment"
        assert len(app.schemas) == 1
        assert app.schemas[0].schema == "myapp://home"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/Desktop/CodeLocator_CLI && python -m pytest tests/test_models.py -v 2>&1 | head -20`

Expected: FAILED — ModuleNotFoundError: No module named 'aidb_locator.models'

- [ ] **Step 3: Implement models.py**

```python
# src/aidb_locator/models.py
"""Data models for CodeLocator protocol responses.

Upstream SDK uses abbreviated JSON field names for compression.
Each model maps short keys to readable Python attributes.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WView:
    class_name: str = ""
    visibility: str = "V"
    id_str: str | None = None
    id_int: int = 0
    mem_addr: str | None = None
    text: str | None = None
    # Bounds
    left: int = 0
    right: int = 0
    top: int = 0
    bottom: int = 0
    # Offsets
    left_offset: int = 0
    top_offset: int = 0
    # Draw bounds
    draw_left: int = 0
    draw_right: int = 0
    draw_top: int = 0
    draw_bottom: int = 0
    # Spacing
    padding_left: int = 0
    padding_right: int = 0
    padding_top: int = 0
    padding_bottom: int = 0
    margin_left: int = 0
    margin_right: int = 0
    margin_top: int = 0
    margin_bottom: int = 0
    # Layout
    layout_width: int = 0
    layout_height: int = 0
    # Transform
    scroll_x: int = 0
    scroll_y: int = 0
    scale_x: float = 1.0
    scale_y: float = 1.0
    translation_x: float = 0.0
    translation_y: float = 0.0
    pivot_x: float = 0.0
    pivot_y: float = 0.0
    alpha: float = 1.0
    # Flags
    is_clickable: bool = False
    is_enabled: bool = True
    is_focusable: bool = False
    is_selected: bool = False
    can_provide_data: bool = False
    # Style
    background_color: str | None = None
    text_color: str | None = None
    text_size: float = 0.0
    # Tags
    click_tag: str | None = None
    touch_tag: str | None = None
    xml_tag: str | None = None
    view_holder_tag: str | None = None
    # Type
    view_type: int = 0
    # Children
    children: list[WView] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> WView:
        children_raw = d.get("a", [])
        children = [WView.from_dict(c) for c in children_raw] if children_raw else []
        return cls(
            class_name=d.get("ag", ""),
            visibility=d.get("ab", "V"),
            id_str=d.get("ac"),
            id_int=d.get("ad", 0),
            mem_addr=d.get("af"),
            text=d.get("aq"),
            left=d.get("d", 0),
            right=d.get("e", 0),
            top=d.get("f", 0),
            bottom=d.get("g", 0),
            left_offset=d.get("c", 0),
            top_offset=d.get("b", 0),
            draw_left=d.get("p", 0),
            draw_right=d.get("q", 0),
            draw_top=d.get("n", 0),
            draw_bottom=d.get("o", 0),
            padding_left=d.get("t", 0),
            padding_right=d.get("u", 0),
            padding_top=d.get("r", 0),
            padding_bottom=d.get("s", 0),
            margin_left=d.get("x", 0),
            margin_right=d.get("y", 0),
            margin_top=d.get("v", 0),
            margin_bottom=d.get("w", 0),
            layout_width=d.get("z", 0),
            layout_height=d.get("a0", 0),
            scroll_x=d.get("h", 0),
            scroll_y=d.get("i", 0),
            scale_x=d.get("j", 1.0),
            scale_y=d.get("k", 1.0),
            translation_x=d.get("l", 0.0),
            translation_y=d.get("m", 0.0),
            pivot_x=d.get("df", 0.0),
            pivot_y=d.get("dg", 0.0),
            alpha=d.get("ae", 1.0),
            is_clickable=d.get("a1", False),
            is_enabled=d.get("a7", True),
            is_focusable=d.get("a3", False),
            is_selected=d.get("a5", False),
            can_provide_data=d.get("a9", False),
            background_color=d.get("ap"),
            text_color=d.get("as"),
            text_size=d.get("at", 0.0),
            click_tag=d.get("ah"),
            touch_tag=d.get("ai"),
            xml_tag=d.get("ak"),
            view_holder_tag=d.get("an"),
            view_type=d.get("aa", 0),
            children=children,
        )

    def to_dict(self) -> dict:
        """Convert to a human-readable dict for CLI/MCP output."""
        d: dict = {
            "class_name": self.class_name,
            "visibility": self.visibility,
            "bounds": {
                "left": self.left,
                "top": self.top,
                "right": self.right,
                "bottom": self.bottom,
            },
        }
        if self.id_str:
            d["id"] = self.id_str
        if self.text:
            d["text"] = self.text
        if self.mem_addr:
            d["mem_addr"] = self.mem_addr
        if self.is_clickable:
            d["clickable"] = True
        if self.background_color:
            d["background_color"] = self.background_color
        if self.text_color:
            d["text_color"] = self.text_color
        if self.text_size:
            d["text_size"] = self.text_size
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d


@dataclass
class WFragment:
    class_name: str = ""
    tag: str | None = None
    id: int = 0
    mem_addr: str | None = None
    view_mem_addr: str | None = None
    is_visible: bool = False
    is_added: bool = False
    user_visible_hint: bool = True
    children: list[WFragment] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> WFragment:
        children_raw = d.get("a", [])
        children = [WFragment.from_dict(c) for c in children_raw] if children_raw else []
        return cls(
            class_name=d.get("ag", ""),
            tag=d.get("cc"),
            id=d.get("ad", 0),
            mem_addr=d.get("af"),
            view_mem_addr=d.get("cb"),
            is_visible=d.get("cd", False),
            is_added=d.get("ce", False),
            user_visible_hint=d.get("cf", True),
            children=children,
        )

    def to_dict(self) -> dict:
        d: dict = {
            "class_name": self.class_name,
            "visible": self.is_visible,
            "added": self.is_added,
        }
        if self.tag:
            d["tag"] = self.tag
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d


@dataclass
class WActivity:
    class_name: str = ""
    mem_addr: str | None = None
    start_info: str | None = None
    decor_views: list[WView] = field(default_factory=list)
    fragments: list[WFragment] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> WActivity:
        decor_raw = d.get("cj", [])
        frag_raw = d.get("ck", [])
        return cls(
            class_name=d.get("ag", ""),
            mem_addr=d.get("af"),
            start_info=d.get("cl"),
            decor_views=[WView.from_dict(v) for v in decor_raw],
            fragments=[WFragment.from_dict(f) for f in frag_raw],
        )

    def to_dict(self) -> dict:
        d: dict = {
            "class_name": self.class_name,
            "fragments": [f.to_dict() for f in self.fragments],
        }
        if self.decor_views:
            d["view_tree"] = [v.to_dict() for v in self.decor_views]
        return d


@dataclass
class WFile:
    name: str = ""
    absolute_path: str = ""
    size: int = 0
    is_directory: bool = False
    is_exists: bool = True
    in_sdcard: bool = False
    last_modified: int = 0
    custom_tag: str | None = None
    editable: bool = False
    is_json: bool = False
    children: list[WFile] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> WFile:
        children_raw = d.get("a", [])
        children = [WFile.from_dict(c) for c in children_raw] if children_raw else []
        return cls(
            name=d.get("c6", ""),
            absolute_path=d.get("c7", ""),
            size=d.get("c1", 0),
            is_directory=d.get("c2", False),
            is_exists=d.get("c3", True),
            in_sdcard=d.get("c4", False),
            last_modified=d.get("c5", 0),
            custom_tag=d.get("c8"),
            editable=d.get("c9", False),
            is_json=d.get("ca", False),
            children=children,
        )

    def to_dict(self) -> dict:
        d: dict = {
            "name": self.name,
            "path": self.absolute_path,
            "size": self.size,
            "is_directory": self.is_directory,
        }
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d


@dataclass
class SchemaInfo:
    schema: str = ""
    display_schema: str | None = None
    desc: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> SchemaInfo:
        return cls(
            schema=d.get("db", ""),
            display_schema=d.get("ds"),
            desc=d.get("dc"),
        )

    def to_dict(self) -> dict:
        d: dict = {"schema": self.schema}
        if self.desc:
            d["desc"] = self.desc
        return d


@dataclass
class WApplication:
    package_name: str = ""
    activity: WActivity = field(default_factory=WActivity)
    file: WFile | None = None
    schemas: list[SchemaInfo] = field(default_factory=list)
    is_debug: bool = False
    density: float = 0.0
    screen_width: int = 0
    screen_height: int = 0
    android_version: int = 0
    device_info: str | None = None
    sdk_version: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> WApplication:
        activity_raw = d.get("b7", {})
        file_raw = d.get("b8")
        schema_raw = d.get("bc", [])
        return cls(
            package_name=d.get("bd", ""),
            activity=WActivity.from_dict(activity_raw) if activity_raw else WActivity(),
            file=WFile.from_dict(file_raw) if file_raw else None,
            schemas=[SchemaInfo.from_dict(s) for s in schema_raw],
            is_debug=d.get("bf", False),
            density=d.get("bj", 0.0),
            screen_width=d.get("bq", 0),
            screen_height=d.get("br", 0),
            android_version=d.get("by", 0),
            device_info=d.get("bz"),
            sdk_version=d.get("bo"),
        )

    def to_dict(self) -> dict:
        d: dict = {
            "package_name": self.package_name,
            "activity": self.activity.to_dict(),
            "screen": {
                "width": self.screen_width,
                "height": self.screen_height,
                "density": self.density,
            },
        }
        if self.schemas:
            d["schemas"] = [s.to_dict() for s in self.schemas]
        if self.device_info:
            d["device_info"] = self.device_info
        return d


def parse_application(response: dict) -> WApplication:
    """Parse a full ApplicationResponse (BaseResponse<WApplication>) into WApplication."""
    data = response.get("data", {})
    return WApplication.from_dict(data)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/Desktop/CodeLocator_CLI && python -m pytest tests/test_models.py -v`

Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/CodeLocator_CLI
git add src/aidb_locator/models.py tests/test_models.py
git commit -m "feat: data models with upstream JSON field mapping and tests"
```

---

### Task 5: Commands Layer

**Files:**
- Create: `src/aidb_locator/commands.py`
- Create: `tests/test_commands.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_commands.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/Desktop/CodeLocator_CLI && python -m pytest tests/test_commands.py -v 2>&1 | head -20`

Expected: FAILED — ModuleNotFoundError: No module named 'aidb_locator.commands'

- [ ] **Step 3: Implement commands.py**

```python
# src/aidb_locator/commands.py
"""High-level API for CodeLocator capabilities."""

from __future__ import annotations

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
        """Edit a View property by memory address."""
        change_data = f"{view_mem_addr},{edit_type},{value}"
        response = self._send(ACTION_CHANGE_VIEW, {KEY_CHANGE_VIEW: change_data})
        return response.get("code", -1) == 0

    def get_touch_view(self, x: int, y: int) -> WView:
        """Get the View at the given touch coordinates."""
        response = self._send(
            ACTION_GET_TOUCH_VIEW,
            {KEY_MOCK_CLICK_X: str(x), KEY_MOCK_CLICK_Y: str(y)},
        )
        return WView.from_dict(response.get("data", {}))

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

    def capture_view(self, view_mem_addr: str, output: str | Path | None = None) -> Path:
        """Capture a View's rendered bitmap."""
        change_data = f"{view_mem_addr},{EDIT_VIEW_BITMAP},"
        self._send(ACTION_CHANGE_VIEW, {KEY_CHANGE_VIEW: change_data})

        if output is None:
            output = Path(tempfile.mktemp(suffix=".png"))
        output = Path(output)
        return self._adb.pull(RESULT_IMAGE_PATH, output)

    def get_view_data(self, view_mem_addr: str) -> dict:
        """Get data bound to a View."""
        change_data = f"{view_mem_addr},{EDIT_GET_DATA},"
        response = self._send(ACTION_CHANGE_VIEW, {KEY_CHANGE_VIEW: change_data})
        data = response.get("data", "")
        if isinstance(data, str):
            try:
                import json
                return json.loads(data)
            except (json.JSONDecodeError, TypeError):
                return {"raw": data}
        return data if isinstance(data, dict) else {"raw": str(data)}

    def set_view_data(self, view_mem_addr: str, data: str) -> bool:
        """Set data on a View."""
        change_data = f"{view_mem_addr},{EDIT_SET_DATA},{data}"
        response = self._send(ACTION_CHANGE_VIEW, {KEY_CHANGE_VIEW: change_data})
        return response.get("code", -1) == 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/Desktop/CodeLocator_CLI && python -m pytest tests/test_commands.py -v`

Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/CodeLocator_CLI
git add src/aidb_locator/commands.py tests/test_commands.py
git commit -m "feat: commands layer with 10 capabilities and tests"
```

---

### Task 6: CLI Layer

**Files:**
- Create: `src/aidb_locator/cli.py`

- [ ] **Step 1: Implement cli.py**

```python
# src/aidb_locator/cli.py
"""CLI entry point — Click-based command interface."""

from __future__ import annotations

import json
import sys

import click

from aidb_locator.adb import AdbClient, AdbError


def _get_adb(device: str | None) -> AdbClient:
    return AdbClient(device_serial=device)


def _get_locator(device: str | None):
    from aidb_locator.commands import CodeLocator
    return CodeLocator(_get_adb(device))


def _output(data, as_json: bool):
    if as_json:
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        click.echo(_format_readable(data))


def _format_readable(data, indent: int = 0) -> str:
    """Format a dict/list as a human-readable tree."""
    if isinstance(data, dict):
        lines = []
        for k, v in data.items():
            prefix = "  " * indent
            if isinstance(v, (dict, list)):
                lines.append(f"{prefix}{k}:")
                lines.append(_format_readable(v, indent + 1))
            else:
                lines.append(f"{prefix}{k}: {v}")
        return "\n".join(lines)
    elif isinstance(data, list):
        lines = []
        for item in data:
            lines.append(_format_readable(item, indent))
        return "\n".join(lines)
    return "  " * indent + str(data)


def _print_view_tree(view_dict: dict, indent: int = 0):
    """Print a view tree with tree-drawing characters."""
    prefix = "  " * indent
    cls = view_dict.get("class_name", "?")
    # Shorten class name to simple name
    short_cls = cls.rsplit(".", 1)[-1] if "." in cls else cls
    parts = [short_cls]

    bounds = view_dict.get("bounds", {})
    if bounds:
        parts.append(f"({bounds['left']},{bounds['top']},{bounds['right']},{bounds['bottom']})")

    vid = view_dict.get("id")
    if vid:
        parts.append(f"id={vid}")

    text = view_dict.get("text")
    if text:
        display = text[:30] + "..." if len(text) > 30 else text
        parts.append(f'"{display}"')

    connector = "├── " if indent > 0 else ""
    click.echo(f"{prefix}{connector}{' '.join(parts)}")

    for child in view_dict.get("children", []):
        _print_view_tree(child, indent + 1)


@click.group()
@click.option("--device", "-d", default=None, help="Device serial (for multi-device)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def main(ctx, device, as_json):
    """aidb — AI-powered Android Debug Bridge."""
    ctx.ensure_object(dict)
    ctx.obj["device"] = device
    ctx.obj["json"] = as_json


@main.command()
@click.pass_context
def devices(ctx):
    """List connected ADB devices."""
    adb = _get_adb(ctx.obj["device"])
    try:
        devs = adb.list_devices()
    except AdbError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    if ctx.obj["json"]:
        click.echo(json.dumps([{"serial": d.serial, "state": d.state} for d in devs], indent=2))
    else:
        if not devs:
            click.echo("No devices connected.")
        else:
            for d in devs:
                click.echo(f"{d.serial}\t{d.state}")


@main.command()
@click.pass_context
def layout(ctx):
    """Grab View hierarchy + Activity/Fragment info."""
    locator = _get_locator(ctx.obj["device"])
    try:
        app = locator.grab_layout()
    except AdbError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    data = app.to_dict()
    if ctx.obj["json"]:
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        click.echo(f"Activity: {app.activity.class_name}")
        frags = [f.class_name for f in app.activity.fragments]
        if frags:
            click.echo(f"Fragments: {frags}")
        click.echo("\nView Tree:")
        for vt in data.get("activity", {}).get("view_tree", []):
            _print_view_tree(vt)


@main.command()
@click.pass_context
def activity(ctx):
    """Show current Activity + Fragment info."""
    locator = _get_locator(ctx.obj["device"])
    try:
        app = locator.grab_layout()
    except AdbError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    if ctx.obj["json"]:
        click.echo(json.dumps(app.activity.to_dict(), indent=2, ensure_ascii=False))
    else:
        click.echo(f"Activity: {app.activity.class_name}")
        for frag in app.activity.fragments:
            vis = "visible" if frag.is_visible else "hidden"
            click.echo(f"  Fragment: {frag.class_name} ({vis})")


@main.command()
@click.argument("x", type=int)
@click.argument("y", type=int)
@click.pass_context
def touch(ctx, x, y):
    """Find the View at touch coordinates (x, y)."""
    locator = _get_locator(ctx.obj["device"])
    try:
        view = locator.get_touch_view(x, y)
    except AdbError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    _output(view.to_dict(), ctx.obj["json"])


@main.command("click")
@click.argument("x", type=int)
@click.argument("y", type=int)
@click.pass_context
def click_cmd(ctx, x, y):
    """Simulate a tap at coordinates (x, y)."""
    locator = _get_locator(ctx.obj["device"])
    try:
        ok = locator.mock_touch(x, y)
    except AdbError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    if ctx.obj["json"]:
        click.echo(json.dumps({"success": ok}))
    else:
        click.echo("OK" if ok else "FAILED")


@main.command()
@click.argument("view_id")
@click.argument("edit_type")
@click.argument("value")
@click.pass_context
def edit(ctx, view_id, edit_type, value):
    """Edit a View property. EDIT_TYPE: P(adding), M(argin), T(ext), A(lpha), etc."""
    locator = _get_locator(ctx.obj["device"])
    try:
        ok = locator.edit_view(view_id, edit_type, value)
    except AdbError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    if ctx.obj["json"]:
        click.echo(json.dumps({"success": ok}))
    else:
        click.echo(f"{'OK' if ok else 'FAILED'}: {edit_type} → {value}")


@main.command()
@click.argument("url")
@click.pass_context
def schema(ctx, url):
    """Send a deep link (schema URL) to the app."""
    locator = _get_locator(ctx.obj["device"])
    try:
        result = locator.send_schema(url)
    except AdbError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    if ctx.obj["json"]:
        click.echo(json.dumps({"result": result}))
    else:
        click.echo(result or "Schema sent.")


@main.command()
@click.pass_context
def files(ctx):
    """Browse the app's file system."""
    locator = _get_locator(ctx.obj["device"])
    try:
        tree = locator.list_files()
    except AdbError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    _output(tree.to_dict(), ctx.obj["json"])


@main.command("file-op")
@click.argument("source")
@click.argument("target")
@click.argument("op")
@click.pass_context
def file_op(ctx, source, target, op):
    """Operate on a file (copy, move, delete)."""
    locator = _get_locator(ctx.obj["device"])
    try:
        ok = locator.operate_file(source, target, op)
    except AdbError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    if ctx.obj["json"]:
        click.echo(json.dumps({"success": ok}))
    else:
        click.echo(f"{'OK' if ok else 'FAILED'}: {op} {source} → {target}")


@main.command()
@click.argument("view_id")
@click.option("-o", "--output", "output_path", default=None, help="Output file path")
@click.pass_context
def capture(ctx, view_id, output_path):
    """Capture a View's rendered bitmap as PNG."""
    locator = _get_locator(ctx.obj["device"])
    try:
        path = locator.capture_view(view_id, output_path)
    except AdbError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    if ctx.obj["json"]:
        click.echo(json.dumps({"path": str(path)}))
    else:
        click.echo(f"Saved: {path}")


@main.command("view-data")
@click.argument("view_id")
@click.option("--set", "set_data", default=None, help="Set data on the View")
@click.pass_context
def view_data(ctx, view_id, set_data):
    """Get or set data bound to a View."""
    locator = _get_locator(ctx.obj["device"])
    try:
        if set_data is not None:
            ok = locator.set_view_data(view_id, set_data)
            if ctx.obj["json"]:
                click.echo(json.dumps({"success": ok}))
            else:
                click.echo("OK" if ok else "FAILED")
        else:
            data = locator.get_view_data(view_id)
            _output(data, ctx.obj["json"])
    except AdbError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.pass_context
def serve(ctx):
    """Start the MCP Server (stdio transport)."""
    from aidb_locator.mcp_server import run_server
    run_server(device_serial=ctx.obj["device"])
```

- [ ] **Step 2: Verify CLI loads without error**

Run: `cd ~/Desktop/CodeLocator_CLI && python -m aidb_locator.cli --help`

Expected: Shows help text with all commands listed

- [ ] **Step 3: Verify subcommand help**

Run: `cd ~/Desktop/CodeLocator_CLI && python -c "from aidb_locator.cli import main; main(['layout', '--help'])"`

Expected: Shows layout command help (no import errors)

- [ ] **Step 4: Commit**

```bash
cd ~/Desktop/CodeLocator_CLI
git add src/aidb_locator/cli.py
git commit -m "feat: CLI layer with all 12 commands"
```

---

### Task 7: MCP Server Layer

**Files:**
- Create: `src/aidb_locator/mcp_server.py`

- [ ] **Step 1: Implement mcp_server.py**

```python
# src/aidb_locator/mcp_server.py
"""MCP Server — exposes CodeLocator capabilities as MCP tools."""

from __future__ import annotations

import base64
import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, ImageContent, Tool

from aidb_locator.adb import AdbClient, AdbError
from aidb_locator.commands import CodeLocator


def _build_tools() -> list[Tool]:
    return [
        Tool(
            name="aidb_grab_layout",
            description="Grab the full View hierarchy tree including Activity, Fragment info, and schemas from the connected Android device.",
            inputSchema={
                "type": "object",
                "properties": {
                    "device": {"type": "string", "description": "Device serial (optional)"},
                },
            },
        ),
        Tool(
            name="aidb_edit_view",
            description="Edit a View property in real-time. Edit types: P(adding), M(argin), T(ext), TC(text color), TS(text size), A(lpha), B(ackground color), VF(view flags), LP(layout params), TXY(translation), SCXY(scale), etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "view_mem_addr": {"type": "string", "description": "View memory address (from grab_layout)"},
                    "edit_type": {"type": "string", "description": "Edit type code (e.g., T for text, P for padding)"},
                    "value": {"type": "string", "description": "New value"},
                    "device": {"type": "string", "description": "Device serial (optional)"},
                },
                "required": ["view_mem_addr", "edit_type", "value"],
            },
        ),
        Tool(
            name="aidb_get_touch_view",
            description="Find which View is at the given screen coordinates.",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate"},
                    "y": {"type": "integer", "description": "Y coordinate"},
                    "device": {"type": "string", "description": "Device serial (optional)"},
                },
                "required": ["x", "y"],
            },
        ),
        Tool(
            name="aidb_mock_touch",
            description="Simulate a tap at the given screen coordinates.",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate"},
                    "y": {"type": "integer", "description": "Y coordinate"},
                    "device": {"type": "string", "description": "Device serial (optional)"},
                },
                "required": ["x", "y"],
            },
        ),
        Tool(
            name="aidb_send_schema",
            description="Send a deep link (schema URL) to navigate the app.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Deep link URL (e.g., myapp://home)"},
                    "device": {"type": "string", "description": "Device serial (optional)"},
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="aidb_list_files",
            description="Browse the app's file system directory tree.",
            inputSchema={
                "type": "object",
                "properties": {
                    "device": {"type": "string", "description": "Device serial (optional)"},
                },
            },
        ),
        Tool(
            name="aidb_operate_file",
            description="Operate on a file in the app's filesystem (copy, move, delete).",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source file path"},
                    "target": {"type": "string", "description": "Target file path"},
                    "op": {"type": "string", "description": "Operation (copy, move, delete)"},
                    "device": {"type": "string", "description": "Device serial (optional)"},
                },
                "required": ["source", "target", "op"],
            },
        ),
        Tool(
            name="aidb_capture_view",
            description="Capture a View's rendered bitmap as a PNG image.",
            inputSchema={
                "type": "object",
                "properties": {
                    "view_mem_addr": {"type": "string", "description": "View memory address (from grab_layout)"},
                    "device": {"type": "string", "description": "Device serial (optional)"},
                },
                "required": ["view_mem_addr"],
            },
        ),
        Tool(
            name="aidb_get_view_data",
            description="Get data bound to a View.",
            inputSchema={
                "type": "object",
                "properties": {
                    "view_mem_addr": {"type": "string", "description": "View memory address"},
                    "device": {"type": "string", "description": "Device serial (optional)"},
                },
                "required": ["view_mem_addr"],
            },
        ),
        Tool(
            name="aidb_set_view_data",
            description="Set data on a View.",
            inputSchema={
                "type": "object",
                "properties": {
                    "view_mem_addr": {"type": "string", "description": "View memory address"},
                    "data": {"type": "string", "description": "Data to set"},
                    "device": {"type": "string", "description": "Device serial (optional)"},
                },
                "required": ["view_mem_addr", "data"],
            },
        ),
    ]


def _make_locator(args: dict, default_serial: str | None = None) -> CodeLocator:
    serial = args.get("device") or default_serial
    return CodeLocator(AdbClient(device_serial=serial))


def run_server(device_serial: str | None = None):
    """Run the MCP server with stdio transport."""
    import asyncio

    server = Server("aidb-locator")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return _build_tools()

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent]:
        try:
            locator = _make_locator(arguments, device_serial)

            if name == "aidb_grab_layout":
                app = locator.grab_layout()
                return [TextContent(type="text", text=json.dumps(app.to_dict(), indent=2, ensure_ascii=False))]

            elif name == "aidb_edit_view":
                ok = locator.edit_view(arguments["view_mem_addr"], arguments["edit_type"], arguments["value"])
                return [TextContent(type="text", text=json.dumps({"success": ok}))]

            elif name == "aidb_get_touch_view":
                view = locator.get_touch_view(arguments["x"], arguments["y"])
                return [TextContent(type="text", text=json.dumps(view.to_dict(), indent=2, ensure_ascii=False))]

            elif name == "aidb_mock_touch":
                ok = locator.mock_touch(arguments["x"], arguments["y"])
                return [TextContent(type="text", text=json.dumps({"success": ok}))]

            elif name == "aidb_send_schema":
                result = locator.send_schema(arguments["url"])
                return [TextContent(type="text", text=json.dumps({"result": result}))]

            elif name == "aidb_list_files":
                tree = locator.list_files()
                return [TextContent(type="text", text=json.dumps(tree.to_dict(), indent=2, ensure_ascii=False))]

            elif name == "aidb_operate_file":
                ok = locator.operate_file(arguments["source"], arguments["target"], arguments["op"])
                return [TextContent(type="text", text=json.dumps({"success": ok}))]

            elif name == "aidb_capture_view":
                path = locator.capture_view(arguments["view_mem_addr"])
                with open(path, "rb") as f:
                    img_data = base64.b64encode(f.read()).decode("ascii")
                return [ImageContent(type="image", data=img_data, mimeType="image/png")]

            elif name == "aidb_get_view_data":
                data = locator.get_view_data(arguments["view_mem_addr"])
                return [TextContent(type="text", text=json.dumps(data, indent=2, ensure_ascii=False))]

            elif name == "aidb_set_view_data":
                ok = locator.set_view_data(arguments["view_mem_addr"], arguments["data"])
                return [TextContent(type="text", text=json.dumps({"success": ok}))]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except AdbError as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def _run():
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    asyncio.run(_run())
```

- [ ] **Step 2: Verify import works**

Run: `cd ~/Desktop/CodeLocator_CLI && python -c "from aidb_locator.mcp_server import _build_tools; print(len(_build_tools()), 'tools')"`

Expected: `10 tools`

- [ ] **Step 3: Commit**

```bash
cd ~/Desktop/CodeLocator_CLI
git add src/aidb_locator/mcp_server.py
git commit -m "feat: MCP server with 10 tools for AI agent integration"
```

---

### Task 8: Integration Verification & Final Polish

**Files:**
- Modify: `pyproject.toml` (if needed)
- Modify: `README.md` (if needed)

- [ ] **Step 1: Run full test suite**

Run: `cd ~/Desktop/CodeLocator_CLI && python -m pytest tests/ -v`

Expected: All tests pass (protocol: 8, adb: 5, models: 9, commands: 5 = 27 total)

- [ ] **Step 2: Verify CLI entry point**

Run: `cd ~/Desktop/CodeLocator_CLI && pip install -e . && aidb --help`

Expected: Shows help with all commands: devices, layout, activity, touch, click, edit, schema, files, file-op, capture, view-data, serve

- [ ] **Step 3: Verify package imports**

Run:
```bash
cd ~/Desktop/CodeLocator_CLI && python -c "
from aidb_locator import __version__
from aidb_locator.adb import AdbClient, Device, AdbError
from aidb_locator.protocol import ACTION_LAYOUT_INFO, encode_args, decode_inline_result
from aidb_locator.models import WView, WApplication, WFile, WFragment
from aidb_locator.commands import CodeLocator
from aidb_locator.cli import main
print(f'aidb-locator v{__version__} — all imports OK')
"
```

Expected: `aidb-locator v0.1.0 — all imports OK`

- [ ] **Step 4: Commit any fixes**

```bash
cd ~/Desktop/CodeLocator_CLI
git add -A
git commit -m "chore: integration verification and polish"
```

(Skip this commit if no changes were needed.)

- [ ] **Step 5: Final git log check**

Run: `cd ~/Desktop/CodeLocator_CLI && git log --oneline`

Expected:
```
chore: integration verification and polish
feat: MCP server with 10 tools for AI agent integration
feat: CLI layer with all 12 commands
feat: commands layer with 10 capabilities and tests
feat: data models with upstream JSON field mapping and tests
feat: ADB client layer with subprocess wrapper and tests
feat: protocol layer with constants, encode/decode, and tests
chore: project scaffolding with pyproject.toml, README, LICENSE
docs: add aidb-locator design spec
```
