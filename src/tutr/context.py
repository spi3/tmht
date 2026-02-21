"""Gather documentation context for a terminal command."""

import logging
import os
import platform
import subprocess
from collections.abc import Iterable

log = logging.getLogger(__name__)


def get_help_output(cmd: str) -> str | None:
    """Run `cmd --help` and return the output."""
    try:
        result = subprocess.run(
            [cmd, "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stdout or result.stderr
        text = output.strip() if output and output.strip() else None
        log.debug("%s --help returned %d chars", cmd, len(text) if text else 0)
        return text
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError) as e:
        log.debug("%s --help failed: %s", cmd, e)
        return None


def get_man_page(cmd: str, max_lines: int = 200) -> str | None:
    """Run `man cmd` and return the output, truncated to max_lines."""
    try:
        env = {**os.environ, "MANPAGER": "cat", "MANWIDTH": "120"}
        result = subprocess.run(
            ["man", cmd],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().splitlines()
            total = len(lines)
            if total > max_lines:
                lines = lines[:max_lines]
                lines.append(f"\n... (truncated, {max_lines} of {total} lines shown)")
            log.debug("man %s returned %d lines", cmd, total)
            return "\n".join(lines)
        log.debug("man %s returned nothing (rc=%d)", cmd, result.returncode)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        log.debug("man %s failed: %s", cmd, e)
    return None


def _get_distro() -> str:
    """Return the OS distribution name (e.g. 'Debian GNU/Linux 12', 'macOS 14.0')."""
    system = platform.system()
    if system == "Darwin":
        mac_ver = platform.mac_ver()[0]
        return f"macOS {mac_ver}" if mac_ver else "macOS"
    try:
        info = platform.freedesktop_os_release()
        return info.get("PRETTY_NAME", info.get("NAME", system))
    except OSError:
        return system


def _iter_path_dirs(path_env: str) -> Iterable[str]:
    """Yield unique PATH directories in order."""
    seen: set[str] = set()
    for raw_dir in path_env.split(os.pathsep):
        path_dir = raw_dir.strip()
        if not path_dir:
            continue
        normalized = os.path.normpath(path_dir)
        if normalized in seen:
            continue
        seen.add(normalized)
        yield normalized


def get_available_commands(max_commands: int = 400) -> tuple[list[str], int]:
    """Return a sorted list of executable command names discoverable via PATH."""
    path_env = os.environ.get("PATH", "")
    if not path_env:
        return [], 0

    names: set[str] = set()
    for path_dir in _iter_path_dirs(path_env):
        try:
            with os.scandir(path_dir) as entries:
                for entry in entries:
                    # Keep only executable files/symlinks that can be launched by name.
                    if entry.name.startswith("."):
                        continue
                    if os.access(entry.path, os.X_OK):
                        names.add(entry.name)
        except OSError:
            continue

    sorted_names = sorted(names)
    total = len(sorted_names)
    if total > max_commands:
        return sorted_names[:max_commands], total
    return sorted_names, total


def get_available_commands_summary(max_commands: int = 400) -> str:
    """Return a compact, prompt-safe summary of installed commands."""
    commands, total = get_available_commands(max_commands=max_commands)
    if not commands:
        return "Available commands in PATH: unavailable"
    visible = len(commands)
    if total > visible:
        return f"Available commands in PATH (showing {visible} of {total}): " + ", ".join(commands)
    return f"Available commands in PATH ({total}): " + ", ".join(commands)


def get_system_info() -> str:
    """Return a summary of the operating system and shell."""
    distro = _get_distro()
    kernel = platform.release()
    shell = os.environ.get("SHELL", "unknown")
    return f"OS: {distro} ({kernel})\nShell: {shell}"


def gather_context(cmd: str | None) -> str:
    """Gather all available documentation for a command."""
    if cmd is None:
        log.debug("no command specified, skipping context gathering")
        return ""

    parts = []

    help_output = get_help_output(cmd)
    if help_output:
        parts.append(f"=== {cmd} --help ===\n{help_output}")

    man_page = get_man_page(cmd)
    if man_page:
        parts.append(f"=== man {cmd} ===\n{man_page}")

    if not parts:
        log.debug("no docs found for %s", cmd)
        parts.append(f"No documentation found for '{cmd}'. Rely on general knowledge.")
        parts.append(get_available_commands_summary())

    context = "\n\n".join(parts)
    log.debug("total context: %d chars", len(context))
    return context
