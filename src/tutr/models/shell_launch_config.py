"""Shell launch model for PTY wrapper."""

from dataclasses import dataclass


@dataclass
class ShellLaunchConfig:
    """How to launch a supported interactive shell in the PTY child process."""

    kind: str
    executable: str
    argv: list[str]
    env: dict[str, str]
    cleanup_paths: list[str]
