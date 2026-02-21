"""Shell detection and launch configuration."""

import os
import shutil

from tutr.models import ShellLaunchConfig
from tutr.shell.hooks import write_bash_rcfile, write_powershell_profile, write_zsh_rcdir


def _classify_shell(candidate: str) -> str | None:
    """Return the supported shell kind for a candidate executable/path."""
    name = os.path.basename(candidate).lower()
    if name in {"bash", "bash.exe"}:
        return "bash"
    if name in {"zsh", "zsh.exe"}:
        return "zsh"
    if name in {"pwsh", "pwsh.exe", "powershell", "powershell.exe"}:
        return "powershell"
    return None


def _resolve_executable(candidate: str) -> str | None:
    """Resolve an executable name or path to a runnable command path."""
    has_sep = os.path.sep in candidate or (
        os.path.altsep is not None and os.path.altsep in candidate
    )
    if has_sep:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
        return None
    return shutil.which(candidate)


def _shell_candidates() -> list[str]:
    """Return shell candidates in preference order."""
    candidates: list[str] = []
    override = os.environ.get("TUTR_SHELL", "").strip()
    if override:
        candidates.append(override)

    env_shell = os.environ.get("SHELL", "").strip()
    if env_shell:
        candidates.append(env_shell)

    if os.name == "nt":
        candidates.extend(["pwsh", "powershell", "bash", "zsh"])
    else:
        candidates.extend(["bash", "zsh", "pwsh", "powershell"])

    deduped: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _detect_shell() -> tuple[str, str]:
    """Detect a supported shell and return (kind, executable path)."""
    for candidate in _shell_candidates():
        kind = _classify_shell(candidate)
        if not kind:
            continue
        executable = _resolve_executable(candidate)
        if executable:
            return kind, executable
    raise RuntimeError(
        "No supported shell found. Install bash, zsh, or PowerShell, "
        "or set TUTR_SHELL to one of them."
    )


def _build_shell_launch_config() -> ShellLaunchConfig:
    """Build shell launch configuration for the detected environment."""
    kind, executable = _detect_shell()
    env = dict(os.environ)
    env["TUTR_ACTIVE"] = "1"
    # Prevent rc-file auto-start snippets from recursively launching tutr.
    env["TUTR_AUTOSTARTED"] = "1"

    if kind == "bash":
        rcfile = write_bash_rcfile()
        return ShellLaunchConfig(
            kind=kind,
            executable=executable,
            argv=[executable, "--rcfile", rcfile, "-i"],
            env=env,
            cleanup_paths=[rcfile],
        )
    if kind == "zsh":
        rcdir = write_zsh_rcdir()
        env["ZDOTDIR"] = rcdir
        return ShellLaunchConfig(
            kind=kind,
            executable=executable,
            argv=[executable, "-i"],
            env=env,
            cleanup_paths=[rcdir],
        )

    profile = write_powershell_profile()
    return ShellLaunchConfig(
        kind=kind,
        executable=executable,
        argv=[executable, "-NoLogo", "-NoExit", "-File", profile],
        env=env,
        cleanup_paths=[profile],
    )
