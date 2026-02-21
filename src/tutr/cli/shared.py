"""Shared CLI presentation helpers."""

import os
import sys

from tutr.constants import BOLD, CYAN, RESET


def supports_color() -> bool:
    """Return whether ANSI color output should be used."""
    if os.getenv("NO_COLOR") is not None:
        return False
    if os.getenv("TERM", "").lower() == "dumb":
        return False
    return sys.stdout.isatty()


def format_suggested_command(command: str) -> str:
    """Return a shell-like prompt line for the suggested command."""
    if supports_color():
        return f"{BOLD}{CYAN}$ {command}{RESET}"
    return f"$ {command}"
