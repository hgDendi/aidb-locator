# aidb-locator

AI-powered Android Debug Bridge — CLI & MCP Server for Android UI inspection and manipulation.

[中文](README.md)

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
pip install git+https://github.com/hgDendi/aidb-locator.git
```

### Prerequisites

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

## Development

```bash
git clone https://github.com/hgDendi/aidb-locator.git
cd aidb-locator
pip install -e .
pytest tests/ -v
```

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.

This project is a CLI/MCP client for the [CodeLocator](https://github.com/bytedance/CodeLocator) protocol, originally developed by ByteDance.
