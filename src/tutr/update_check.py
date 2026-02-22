"""Check whether a newer tutr version is available on PyPI."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import threading
import time
from typing import TextIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tutr.config import CONFIG_DIR, TutrConfig, load_config

PYPI_JSON_URL = "https://pypi.org/pypi/tutr/json"
NETWORK_TIMEOUT_SECONDS = 1.5
UPDATE_CHECK_CACHE_TTL_SECONDS = 24 * 60 * 60
UPDATE_CHECK_CACHE_FILE = CONFIG_DIR / "update-check.json"


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


def _read_last_update_check_epoch() -> float | None:
    try:
        with open(UPDATE_CHECK_CACHE_FILE) as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    value = payload.get("last_checked_epoch")
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _record_update_check_epoch(now_epoch: float) -> None:
    try:
        os.makedirs(CONFIG_DIR, mode=0o700, exist_ok=True)
        temp_file = UPDATE_CHECK_CACHE_FILE.with_name(
            f".{UPDATE_CHECK_CACHE_FILE.name}.{os.getpid()}.{time.time_ns()}.tmp"
        )
        fd = os.open(temp_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump({"last_checked_epoch": now_epoch}, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, UPDATE_CHECK_CACHE_FILE)
    except OSError:
        return


def _is_update_check_due(now_epoch: float) -> bool:
    last_checked_epoch = _read_last_update_check_epoch()
    if last_checked_epoch is None:
        return True
    return (now_epoch - last_checked_epoch) >= UPDATE_CHECK_CACHE_TTL_SECONDS


def _load_update_check_config(config: TutrConfig | None) -> TutrConfig:
    if config is not None:
        return config
    return load_config()


def notify_if_update_available(
    current_version: str,
    stream: TextIO = sys.stderr,
    *,
    allow_interactive_update: bool = True,
    config: TutrConfig | None = None,
) -> None:
    """Offer an update when the installed version is behind PyPI."""
    resolved_config = _load_update_check_config(config)
    if not resolved_config.update_check_enabled:
        return

    now_epoch = time.time()
    if not _is_update_check_due(now_epoch):
        return
    _record_update_check_epoch(now_epoch)

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

    if not allow_interactive_update or not _is_interactive(stream, sys.stdin):
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


def notify_if_update_available_async(
    current_version: str, stream: TextIO = sys.stderr, config: TutrConfig | None = None
) -> None:
    """Run update notification in a background thread without prompting for input."""
    thread = threading.Thread(
        target=notify_if_update_available,
        args=(current_version, stream),
        kwargs={"allow_interactive_update": False, "config": config},
        daemon=True,
        name="tutr-update-check",
    )
    thread.start()
