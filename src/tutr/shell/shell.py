"""Tutor suggestion helpers for shell command failures."""

import os

from tutr.config import load_config, needs_setup
from tutr.setup import run_setup
from tutr.tutr import run
from tutr.shell.constants import BOLD, RED, RESET


def load_shell_config() -> dict:
    """Load or bootstrap config for shell mode."""
    if needs_setup():
        return run_setup()
    return load_config()


def _should_ask_tutor(exit_code: int, command: str) -> bool:
    """Return whether a prompt marker should trigger an LLM suggestion."""
    # Ctrl-C usually maps to exit code 130 in POSIX shells. Treat that as an
    # intentional interruption rather than a command failure needing help.
    if exit_code == 130:
        return False
    return exit_code != 0 and bool(command.strip())


def _ask_tutor(cmd: str, output: str, config: dict) -> tuple[bytes, str | None]:
    """Query tutr with a failed command and return display text and command."""
    query = f"fix this command: {cmd}"
    if output:
        query += f"\n\nTerminal output:\n{output}"
    try:
        result = run(query.split(), config)
        msg = f"\r\n{BOLD}tutr suggests:{RESET}\r\n  {result.command}\r\n".encode()
        return msg, result.command
    except Exception as e:
        return f"\r\n{RED}tutr error: {e}{RESET}\r\n".encode(), None


def _is_auto_run_accepted(choice: bytes) -> bool:
    """Return whether a one-byte prompt response means 'yes'."""
    return choice in {b"y", b"Y"}


def _prompt_auto_run(stdin_fd: int, stdout_fd: int, master_fd: int, command: str) -> None:
    """Prompt for yes/no and optionally execute the suggested command."""
    prompt = "Run suggested command? [y/N] (Esc rejects): "
    os.write(stdout_fd, prompt.encode())
    while True:
        try:
            choice = os.read(stdin_fd, 1)
        except OSError:
            os.write(stdout_fd, b"\r\n")
            return
        if not choice:
            os.write(stdout_fd, b"\r\n")
            return
        if _is_auto_run_accepted(choice):
            os.write(stdout_fd, b"y\r\n")
            os.write(master_fd, command.encode() + b"\n")
            return
        if choice in {b"n", b"N", b"\x03", b"\x1b", b"\r", b"\n"}:
            os.write(stdout_fd, b"n\r\n")
            return
