"""PTY-based shell wrapper that intercepts errors and asks tutr for help."""

import argparse

from tutr import __version__
from tutr.shell.loop import shell_loop
from tutr.update_check import notify_if_update_available_async

__all__ = [
    "entrypoint",
    "shell_loop",
]


def entrypoint() -> None:
    parser = argparse.ArgumentParser(
        prog="tutr",
        description="Run interactive tutr shell mode",
    )
    execute_group = parser.add_mutually_exclusive_group()
    execute_group.add_argument(
        "--no-execute",
        action="store_true",
        help="Never prompt to auto-run suggested commands in this shell session",
    )
    execute_group.add_argument(
        "--allow-execute",
        action="store_true",
        help="Allow prompting to auto-run suggested commands in this shell session",
    )
    args = parser.parse_args()
    no_execute_override: bool | None = None
    if args.no_execute:
        no_execute_override = True
    if args.allow_execute:
        no_execute_override = False

    notify_if_update_available_async(__version__)
    raise SystemExit(shell_loop(no_execute_override=no_execute_override))
