"""Check whether a newer tutr version is available on PyPI."""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
import sys
from typing import TextIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PYPI_JSON_URL = "https://pypi.org/pypi/tutr/json"
NETWORK_TIMEOUT_SECONDS = 1.5


def _fetch_latest_version() -> str | None:
    """Return the latest version published on PyPI, if available."""
    request = Request(
        PYPI_JSON_URL,
        headers={"Accept": "application/json", "User-Agent": "tutr update-check"},
    )
    try:
        with urlopen(request, timeout=NETWORK_TIMEOUT_SECONDS) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None
    info = payload.get("info")
    if not isinstance(info, dict):
        return None

    latest = info.get("version")
    if isinstance(latest, str) and latest.strip():
        return latest.strip()
    return None


def _infer_installer() -> str | None:
    """Infer how tutr was installed from runtime paths."""
    runtime = f"{sys.executable} {sys.prefix}".lower()
    if "pipx" in runtime:
        return "pipx"
    if "uv/tools" in runtime or ".local/share/uv" in runtime:
        return "uv"
    return None


def _update_command() -> list[str]:
    """Return the best update command for the current environment."""
    installer = _infer_installer()
    if installer == "pipx" and shutil.which("pipx"):
        return ["pipx", "upgrade", "tutr"]
    if installer == "uv" and shutil.which("uv"):
        return ["uv", "tool", "upgrade", "tutr"]
    if shutil.which("uv"):
        return ["uv", "tool", "upgrade", "tutr"]
    if shutil.which("pipx"):
        return ["pipx", "upgrade", "tutr"]
    return [sys.executable, "-m", "pip", "install", "--upgrade", "tutr"]


def _is_interactive(stream: TextIO, input_stream: TextIO) -> bool:
    return stream.isatty() and input_stream.isatty()


def notify_if_update_available(current_version: str, stream: TextIO = sys.stderr) -> None:
    """Offer an update when the installed version is behind PyPI."""
    latest_version = _fetch_latest_version()
    if latest_version is None or latest_version == current_version:
        return

    command = _update_command()
    command_text = shlex.join(command)
    print(
        (
            f"tutr update available: {current_version} -> {latest_version}. "
            f"Suggested command: {command_text}"
        ),
        file=stream,
    )

    if not _is_interactive(stream, sys.stdin):
        return

    print("Run update now? [y/N]: ", end="", file=stream, flush=True)
    choice = sys.stdin.readline().strip().lower()
    if choice not in {"y", "yes"}:
        return

    try:
        result = subprocess.run(command, check=False)
    except OSError as exc:
        print(f"Unable to start updater: {exc}", file=stream)
        return

    if result.returncode == 0:
        print("tutr updated successfully.", file=stream)
        return

    print(
        f"Update command failed with exit code {result.returncode}. Run manually: {command_text}",
        file=stream,
    )
