# aidb-locator Design Spec

> Date: 2026-04-03
> Status: Approved
> License: Apache 2.0

## Overview

aidb-locator 是一个 Python CLI + MCP Server 工具，基于 CodeLocator 协议通过 ADB 与 Android 设备通信，提供 View 检查、编辑、交互、文件浏览等能力。目标是让 AI agent 具备 Android UI 调试的基础能力，无需依赖 Android Studio。

## Architecture

单层架构，所有代码在 `aidb_locator` 包内：

```
src/aidb_locator/
├── adb.py          # ADB 通信层（subprocess 封装）
├── protocol.py     # CodeLocator 协议（编码/解码/常量）
├── models.py       # 数据模型（dataclass）
├── commands.py     # 10 项能力的高层 API
├── cli.py          # Click CLI 入口
└── mcp_server.py   # MCP Server
```

层级依赖方向：`cli.py / mcp_server.py → commands.py → protocol.py → adb.py`

## Layer 1: ADB 通信层 (adb.py)

### AdbClient

```python
class AdbClient:
    def __init__(self, device_serial: str | None = None)
    def broadcast(self, action: str, args: dict) -> str
    def pull(self, remote_path: str, local_path: str) -> Path
    def shell(self, command: str) -> str
    def list_devices(self) -> list[Device]
```

- 通过 `subprocess` 调用系统 `adb` 命令
- `device_serial` 支持多设备场景（`-s` 参数）
- 超时控制，默认 10s
- 统一异常类型 `AdbError`

## Layer 2: 协议层 (protocol.py)

### 常量

CodeLocator 协议使用 broadcast action 通信，常量定义：

```python
_PREFIX = "com.bytedance.tools.codelocator"

ACTION_LAYOUT_INFO      = f"{_PREFIX}.action_debug_layout_info"
ACTION_CHANGE_VIEW      = f"{_PREFIX}.action_change_view_info"
ACTION_GET_TOUCH_VIEW   = f"{_PREFIX}.action_get_touch_view"
ACTION_MOCK_TOUCH_VIEW  = f"{_PREFIX}.action_mock_touch_view"
ACTION_PROCESS_SCHEMA   = f"{_PREFIX}.action_process_schema"
ACTION_DEBUG_FILE_INFO  = f"{_PREFIX}.action_debug_file_info"
ACTION_DEBUG_FILE_OP    = f"{_PREFIX}.action_debug_file_operate"
ACTION_OPERATE_CUSTOM   = f"{_PREFIX}.action_operate_custom_file"
ACTION_USE_TOOLS_INFO   = f"{_PREFIX}.action_use_tools_info"
ACTION_PROCESS_CONFIG   = f"{_PREFIX}.action_process_config_list"
ACTION_CONFIG_SDK       = f"{_PREFIX}.action_config_sdk"
```

### 参数键

```python
KEY_SHELL_ARGS     = "codeLocator_shell_args"
KEY_ASYNC          = "codeLocator_save_async"
KEY_CHANGE_VIEW    = "codeLocator_change_view"
KEY_MOCK_CLICK_X   = "codeLocator_mock_click_x"
KEY_MOCK_CLICK_Y   = "codeLocator_mock_click_y"
KEY_DATA           = "codeLocator_data"
KEY_SAVE_TO_FILE   = "codeLocator_save_to_file"
KEY_ACTION         = "codeLocator_action"
KEY_SOURCE_PATH    = "codeLocator_process_source_file_path"
KEY_TARGET_PATH    = "codeLocator_process_target_file_path"
KEY_FILE_OPERATE   = "codeLocator_process_file_operate"
```

### EditType 常量

```python
EDIT_PADDING       = "P"
EDIT_MARGIN        = "M"
EDIT_BACKGROUND    = "B"
EDIT_VIEW_FLAG     = "VF"
EDIT_LAYOUT_PARAMS = "LP"
EDIT_TRANSLATION   = "TXY"
EDIT_SCROLL        = "SXY"
EDIT_SCALE         = "SCXY"
EDIT_PIVOT         = "PXY"
EDIT_TEXT          = "T"
EDIT_TEXT_COLOR    = "TC"
EDIT_TEXT_SIZE     = "TS"
EDIT_LINE_SPACE   = "LS"
EDIT_SHADOW_XY    = "SA"
EDIT_SHADOW_RADIUS = "SR"
EDIT_SHADOW_COLOR  = "SC"
EDIT_MIN_HEIGHT   = "MH"
EDIT_MIN_WIDTH    = "MW"
EDIT_ALPHA        = "A"
EDIT_VIEW_BITMAP  = "VB"
EDIT_LAYER_BITMAP = "DLB"
EDIT_FOREGROUND   = "OF"
EDIT_BACKGROUND_ONLY = "OB"
EDIT_GET_DATA     = "GVD"
EDIT_SET_DATA     = "SVD"
EDIT_GET_CLASS    = "GVCI"
EDIT_GET_INTENT   = "GI"
EDIT_CLOSE_ACTIVITY = "CA"
EDIT_INVOKE       = "IK"
EDIT_IGNORE       = "X"
```

### 编码/解码

```python
def encode_args(args: dict) -> str
    # dict → JSON → Base64

def decode_result(raw: str) -> dict
    # 原始 broadcast 输出 → 提取 data="..." 或 FP:path → Base64 → 解压 → JSON

def parse_result(raw_output: str, adb: AdbClient) -> dict
    # 自动判断 inline vs file path，统一返回 dict
```

### 结果文件路径

```python
RESULT_DATA_PATH  = "/sdcard/Download/codeLocator_data.txt"
RESULT_IMAGE_PATH = "/sdcard/Download/codeLocator_image.png"
BASE_DIR          = "/sdcard/codeLocator"
BASE_TMP_DIR      = "/data/local/tmp/codeLocator"
```

### 结果解码流程

1. 检查输出中是否包含 `FP:` → 有则 adb pull 文件
2. 否则提取 `data="..."` 中的内容
3. Base64 decode → zlib decompress → JSON parse

## Layer 3: 数据模型 (models.py)

```python
@dataclass
class ViewInfo:
    id: str
    class_name: str
    bounds: tuple[int, int, int, int]
    visibility: str
    text: str | None
    children: list[ViewInfo]

@dataclass
class ApplicationInfo:
    activity: str
    fragments: list[str]
    view_tree: ViewInfo
    schema_list: list[str]

@dataclass
class FileTree:
    path: str
    size: int
    children: list[FileTree]
```

## Layer 4: Commands 层 (commands.py)

```python
class CodeLocator:
    def __init__(self, adb: AdbClient)

    def grab_layout(self) -> ApplicationInfo          # 能力 1+2
    def edit_view(self, view_id, edit_type, value)    # 能力 3
    def get_touch_view(self, x, y) -> ViewInfo        # 能力 4
    def mock_touch(self, x, y) -> bool                # 能力 5
    def send_schema(self, url) -> str                 # 能力 6
    def list_files(self) -> FileTree                  # 能力 7
    def operate_file(self, source, target, op)        # 能力 8
    def capture_view(self, view_id) -> Path           # 能力 9
    def get_view_data(self, view_id) -> dict          # 能力 10
    def set_view_data(self, view_id, data) -> bool    # 能力 10
```

## Layer 5: CLI (cli.py)

基于 Click，入口命令 `aidb`：

```
aidb devices                              # 列出已连接设备
aidb layout [--device SERIAL] [--json]    # View 层级树 + Activity/Fragment
aidb activity [--device SERIAL]           # 当前 Activity + Fragment（layout 子集）
aidb touch <x> <y>                        # 坐标定位 View
aidb click <x> <y>                        # 模拟点击
aidb edit <view_id> <type> <value>        # 编辑 View 属性
aidb schema <url>                         # 发送深度链接
aidb files                                # 文件目录树
aidb file-op <source> <target> <op>       # 文件操作
aidb capture <view_id> [-o output.png]    # View 截图
aidb view-data <view_id> [--set <data>]   # 获取/设置 View 数据
aidb serve [--port PORT]                  # 启动 MCP Server
```

全局 flag：
- `--device SERIAL` 指定设备
- `--json` 输出 JSON 格式

默认输出人类友好格式（树状缩进），`--json` 输出结构化 JSON。

## Layer 6: MCP Server (mcp_server.py)

10 个 MCP tools，通过 `aidb serve` 启动，stdio 传输：

| Tool Name           | 对应能力 |
|---------------------|----------|
| aidb_grab_layout    | 1+2      |
| aidb_edit_view      | 3        |
| aidb_get_touch_view | 4        |
| aidb_mock_touch     | 5        |
| aidb_send_schema    | 6        |
| aidb_list_files     | 7        |
| aidb_operate_file   | 8        |
| aidb_capture_view   | 9        |
| aidb_get_view_data  | 10       |
| aidb_set_view_data  | 10       |

配置方式：

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

`aidb_capture_view` 返回 base64 PNG，利用 MCP image content type。

## Dependencies

```toml
[project]
name = "aidb-locator"
requires-python = ">=3.10"
dependencies = [
    "click>=8.0",
    "mcp>=1.0",
]

[project.scripts]
aidb = "aidb_locator.cli:main"
```

- 无 adb Python 包依赖，通过 subprocess 调用系统 adb
- 仅两个外部依赖

## Testing

```
tests/
├── test_protocol.py    # 编码解码单测（不需要设备）
├── test_models.py      # 模型解析单测
└── test_commands.py    # 集成测试（需要设备）
```

test_protocol 和 test_models 可离线运行，覆盖核心编码逻辑。

## Acknowledgement

This project is a CLI/MCP client for the [CodeLocator](https://github.com/bytedance/CodeLocator) protocol, originally developed by ByteDance. Licensed under Apache 2.0.
