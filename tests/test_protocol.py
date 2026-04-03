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
