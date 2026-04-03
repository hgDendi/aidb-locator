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
