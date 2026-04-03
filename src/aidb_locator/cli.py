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


# --- Native ADB fallback commands (no SDK needed) ---


def _get_native(device: str | None):
    from aidb_locator.commands import NativeAdb
    return NativeAdb(_get_adb(device))


@main.command()
@click.option("-o", "--output", "output_path", default=None, help="Output file path")
@click.pass_context
def screenshot(ctx, output_path):
    """Take a full-screen screenshot (no SDK needed)."""
    native = _get_native(ctx.obj["device"])
    try:
        path = native.screenshot(output_path)
    except AdbError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    if ctx.obj["json"]:
        click.echo(json.dumps({"path": str(path)}))
    else:
        click.echo(f"Saved: {path}")


@main.command()
@click.argument("x", type=int)
@click.argument("y", type=int)
@click.pass_context
def tap(ctx, x, y):
    """Tap at screen coordinates (no SDK needed)."""
    native = _get_native(ctx.obj["device"])
    try:
        native.tap(x, y)
    except AdbError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    if ctx.obj["json"]:
        click.echo(json.dumps({"success": True, "x": x, "y": y}))
    else:
        click.echo(f"Tapped ({x}, {y})")


@main.command()
@click.argument("x1", type=int)
@click.argument("y1", type=int)
@click.argument("x2", type=int)
@click.argument("y2", type=int)
@click.option("--duration", "-t", default=300, help="Duration in ms")
@click.pass_context
def swipe(ctx, x1, y1, x2, y2, duration):
    """Swipe from (x1,y1) to (x2,y2) (no SDK needed)."""
    native = _get_native(ctx.obj["device"])
    try:
        native.swipe(x1, y1, x2, y2, duration)
    except AdbError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    if ctx.obj["json"]:
        click.echo(json.dumps({"success": True}))
    else:
        click.echo(f"Swiped ({x1},{y1}) → ({x2},{y2})")


@main.command("dump")
@click.pass_context
def dump_ui(ctx):
    """Dump UI hierarchy via uiautomator (no SDK needed)."""
    native = _get_native(ctx.obj["device"])
    try:
        xml = native.dump_ui()
    except AdbError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    click.echo(xml)


@main.command("top-activity")
@click.pass_context
def top_activity(ctx):
    """Show the current top Activity (no SDK needed)."""
    native = _get_native(ctx.obj["device"])
    try:
        info = native.top_activity()
    except AdbError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    if ctx.obj["json"]:
        click.echo(json.dumps(info, indent=2))
    else:
        pkg = info.get("package", "?")
        act = info.get("activity", "?")
        click.echo(f"{pkg}/{act}")


@main.command()
@click.argument("text")
@click.pass_context
def input_text(ctx, text):
    """Input text to focused field (ASCII only, no SDK needed)."""
    native = _get_native(ctx.obj["device"])
    try:
        native.input_text(text)
    except AdbError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    if ctx.obj["json"]:
        click.echo(json.dumps({"success": True}))
    else:
        click.echo(f"Typed: {text}")


@main.command()
@click.argument("keycode")
@click.pass_context
def key(ctx, keycode):
    """Send a key event (e.g., BACK, HOME, 4, 3) (no SDK needed)."""
    native = _get_native(ctx.obj["device"])
    key_map = {"BACK": 4, "HOME": 3, "ENTER": 66, "TAB": 61, "MENU": 82, "POWER": 26}
    resolved = key_map.get(keycode.upper(), keycode)
    try:
        native.input_keyevent(resolved)
    except AdbError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    if ctx.obj["json"]:
        click.echo(json.dumps({"success": True, "keycode": resolved}))
    else:
        click.echo(f"Key: {keycode}")


@main.command("screen-size")
@click.pass_context
def screen_size(ctx):
    """Get screen resolution (no SDK needed)."""
    native = _get_native(ctx.obj["device"])
    try:
        size = native.screen_size()
    except AdbError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    if ctx.obj["json"]:
        click.echo(json.dumps(size))
    else:
        click.echo(f"{size['width']}x{size['height']}")
