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
    # SDK may omit base64 padding — fix length to be multiple of 4
    b64_data += "=" * (-len(b64_data) % 4)
    compressed = base64.b64decode(b64_data)
    json_bytes = zlib.decompress(compressed)
    return json.loads(json_bytes)


def decode_file_result(file_content: bytes) -> dict:
    """Decode a file-based result: Base64 decode, decompress, JSON parse."""
    if isinstance(file_content, bytes):
        file_content = file_content.decode("ascii", errors="ignore")
    file_content += "=" * (-len(file_content) % 4)
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
