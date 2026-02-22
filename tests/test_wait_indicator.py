"""Unit tests for tutr.wait_indicator."""

import os
import time
from typing import TextIO, cast

from tutr.wait_indicator import WaitIndicator


class _RecordingStream:
    def __init__(self, tty: bool = True) -> None:
        self._tty = tty
        self.writes: list[str] = []
        self.flush_calls = 0

    def isatty(self) -> bool:
        return self._tty

    def write(self, text: str) -> int:
        self.writes.append(text)
        return len(text)

    def flush(self) -> None:
        self.flush_calls += 1


class _RaisingStream(_RecordingStream):
    def write(self, text: str) -> int:
        raise OSError("stream write failed")


def test_start_stop_lifecycle_stops_and_cleans_up_thread() -> None:
    stream = _RecordingStream(tty=True)
    indicator = WaitIndicator(["ls", "pwd"], stream=cast(TextIO, stream), interval=0.01)

    indicator.start()
    time.sleep(0.03)
    indicator.stop()

    assert indicator._thread is not None
    assert indicator._stop_event.is_set()
    assert not indicator._thread.is_alive()


def test_non_tty_start_stop_are_noops_without_writing() -> None:
    stream = _RecordingStream(tty=False)
    indicator = WaitIndicator(["ls"], stream=cast(TextIO, stream), interval=0.01)

    indicator.start()
    indicator.stop()

    assert indicator._enabled is False
    assert indicator._thread is None
    assert stream.writes == []
    assert stream.flush_calls == 0


def test_write_line_disables_indicator_on_oserror() -> None:
    stream = _RaisingStream(tty=True)
    indicator = WaitIndicator(["ls"], stream=cast(TextIO, stream))

    indicator._write_line("waiting")

    assert indicator._enabled is False


def test_clear_line_writes_expected_terminal_clear(monkeypatch) -> None:
    stream = _RecordingStream(tty=True)
    indicator = WaitIndicator(["ls"], stream=cast(TextIO, stream))
    monkeypatch.setattr(
        "tutr.wait_indicator.shutil.get_terminal_size", lambda fallback: os.terminal_size((20, 24))
    )

    indicator._clear_line()

    assert stream.writes == ["\r" + (" " * 19) + "\r"]
    assert stream.flush_calls == 1
