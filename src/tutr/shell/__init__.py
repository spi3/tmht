"""PTY-based shell wrapper that intercepts errors and asks tutr for help."""

from tutr import __version__
from tutr.shell.loop import shell_loop
from tutr.update_check import notify_if_update_available

__all__ = [
    "entrypoint",
    "shell_loop",
]


def entrypoint() -> None:
    notify_if_update_available(__version__)
    raise SystemExit(shell_loop())
