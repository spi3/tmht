"""Gather documentation context for a terminal command."""

import os
import subprocess


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
        return output.strip() if output and output.strip() else None
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
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
            return "\n".join(lines)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def gather_context(cmd: str) -> str:
    """Gather all available documentation for a command."""
    parts = []

    help_output = get_help_output(cmd)
    if help_output:
        parts.append(f"=== {cmd} --help ===\n{help_output}")

    man_page = get_man_page(cmd)
    if man_page:
        parts.append(f"=== man {cmd} ===\n{man_page}")

    if not parts:
        parts.append(f"No documentation found for '{cmd}'. Rely on general knowledge.")

    return "\n\n".join(parts)
