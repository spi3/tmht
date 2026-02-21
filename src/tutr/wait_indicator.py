"""Terminal wait indicators used while asynchronous work is in progress."""

import itertools
import shutil
import sys
import threading
import time
from typing import TextIO

from tutr.context import get_available_commands

SPINNER_FRAMES = ("|", "/", "-", "\\")
SPINNER_INTERVAL_SECONDS = 0.1
COMMAND_ROTATION_SECONDS = 0.5


class WaitIndicator:
    """Render a lightweight TTY spinner while waiting for a task to finish."""

    def __init__(
        self,
        commands: list[str],
        stream: TextIO | None = None,
        interval: float = SPINNER_INTERVAL_SECONDS,
        message_prefix: str = "Asking tutr... : ",
    ) -> None:
        self._commands = commands or ["unavailable"]
        self._stream = stream if stream is not None else sys.stderr
        self._interval = interval
        self._message_prefix = message_prefix
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._enabled = hasattr(self._stream, "isatty") and self._stream.isatty()

    def start(self) -> None:
        if not self._enabled:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self._enabled:
            return
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
        self._clear_line()

    def _run(self) -> None:
        spinner = itertools.cycle(SPINNER_FRAMES)
        commands = itertools.cycle(self._commands)
        current_command = next(commands)
        last_command_switch = time.monotonic()
        while not self._stop_event.is_set():
            frame = next(spinner)
            now = time.monotonic()
            if now - last_command_switch >= COMMAND_ROTATION_SECONDS:
                current_command = next(commands)
                last_command_switch = now
            self._write_line(f"{frame} {self._message_prefix}{current_command}")
            time.sleep(self._interval)

    def _write_line(self, text: str) -> None:
        cols = shutil.get_terminal_size(fallback=(80, 24)).columns
        max_width = max(cols - 1, 10)
        clipped = text[:max_width]
        try:
            self._stream.write("\r" + clipped.ljust(max_width))
            self._stream.flush()
        except OSError:
            self._enabled = False

    def _clear_line(self) -> None:
        cols = shutil.get_terminal_size(fallback=(80, 24)).columns
        max_width = max(cols - 1, 10)
        try:
            self._stream.write("\r" + (" " * max_width) + "\r")
            self._stream.flush()
        except OSError:
            pass


def build_llm_wait_indicator() -> WaitIndicator:
    """Build a wait indicator configured with commands discoverable in PATH."""
    commands, _ = get_available_commands(max_commands=200)
    return WaitIndicator(commands)
