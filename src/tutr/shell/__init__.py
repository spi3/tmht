"""PTY-based shell wrapper that intercepts errors and asks tutr for help."""

from tutr.shell.detection import (
    _classify_shell,
    _detect_shell,
    _resolve_executable,
    _shell_candidates,
)
from tutr.shell.loop import shell_loop
from tutr.shell.shell import _is_auto_run_accepted, _should_ask_tutor
from tutr.update_check import notify_if_update_available
from tutr import __version__


__all__ = [
    "entrypoint",
    "shell_loop",
    "_is_auto_run_accepted",
    "_should_ask_tutor",
    "_classify_shell",
    "_detect_shell",
    "_resolve_executable",
    "_shell_candidates",
]


def entrypoint() -> None:
    notify_if_update_available(__version__)
    raise SystemExit(shell_loop())
