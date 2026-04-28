"""FastAPI server + uvicorn entry."""

from __future__ import annotations

import socket
import threading
import time
import webbrowser
from pathlib import Path

import click
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from aidb_locator.ui import errors
from aidb_locator.ui.api import api_router

STATIC_DIR = Path(__file__).parent / "static"


def build_app() -> FastAPI:
    app = FastAPI(title="aidb-locator UI", version="0.1.0")
    errors.install(app)
    app.include_router(api_router)
    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
    return app


def _pick_port(host: str, start: int) -> int:
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No free port found in {start}..{start + 100}")


def _open_browser_when_ready(url: str) -> None:
    def _open() -> None:
        time.sleep(0.6)
        webbrowser.open(url)
    threading.Thread(target=_open, daemon=True).start()


@click.command()
@click.option("--host", default="127.0.0.1", help="Bind host.")
@click.option("--port", default=0, type=int, help="Bind port (0 = auto-pick from 8765+).")
@click.option("--no-browser", is_flag=True, help="Do not auto-open browser.")
def main(host: str, port: int, no_browser: bool) -> None:
    """Start the aidb-locator local web UI."""
    chosen = _pick_port(host, port if port else 8765)
    url = f"http://{host}:{chosen}"
    click.echo(f"aidb-ui listening on {url}")
    if host not in ("127.0.0.1", "localhost"):
        click.secho(
            f"WARNING: bound to {host}; anyone on your network can drive the device. "
            "Use --host 127.0.0.1 to restrict to localhost.",
            fg="yellow",
            err=True,
        )
    if not no_browser:
        _open_browser_when_ready(url)
    uvicorn.run(build_app(), host=host, port=chosen, log_level="info")
