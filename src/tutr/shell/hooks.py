"""Temporary shell startup hooks that emit command markers."""

import os
import tempfile


def write_bash_rcfile() -> str:
    """Write a temporary bashrc that sets up the PROMPT_COMMAND hook."""
    rc = tempfile.NamedTemporaryFile(
        mode="w", prefix="tutr_", suffix=".bashrc", delete=False
    )
    rc.write(
        # Source the user's normal bashrc so the shell feels familiar.
        '[ -f ~/.bashrc ] && source ~/.bashrc\n'
        # PROMPT_COMMAND runs after every command. It emits an OSC marker
        # containing the exit code and the command that was just run.
        "PROMPT_COMMAND='__e=$?; "
        'printf "\\033]7770;%d;%s\\007" "$__e" '
        '"$(history 1 | sed \"s/^[ ]*[0-9]*[ ]*//\")"\'\n'
    )
    rc.close()
    return rc.name


def write_zsh_rcdir() -> str:
    """Write a temporary ZDOTDIR containing a zshrc that emits markers."""
    rcdir = tempfile.mkdtemp(prefix="tutr_zsh_")
    rcfile = os.path.join(rcdir, ".zshrc")
    with open(rcfile, "w", encoding="utf-8") as f:
        f.write(
            '[ -f ~/.zshrc ] && source ~/.zshrc\n'
            "autoload -Uz add-zsh-hook 2>/dev/null || true\n"
            "_tutr_emit_marker() {\n"
            "  local __e=$?\n"
            "  local __cmd\n"
            "  __cmd=$(fc -ln -1 2>/dev/null)\n"
            "  printf '\\033]7770;%d;%s\\007' \"$__e\" \"$__cmd\"\n"
            "}\n"
            "if typeset -f add-zsh-hook >/dev/null 2>&1; then\n"
            "  add-zsh-hook precmd _tutr_emit_marker\n"
            "else\n"
            "  precmd_functions+=(_tutr_emit_marker)\n"
            "fi\n"
        )
    return rcdir


def write_powershell_profile() -> str:
    """Write a temporary PowerShell profile script that emits markers."""
    profile = tempfile.NamedTemporaryFile(
        mode="w", prefix="tutr_", suffix=".ps1", delete=False, encoding="utf-8"
    )
    profile.write(
        "$global:tutr_old_prompt = $function:prompt\n"
        "function global:prompt {\n"
        "  $exitCode = if ($?) { 0 } elseif ($LASTEXITCODE -ne $null) "
        "{ [int]$LASTEXITCODE } else { 1 }\n"
        "  $last = Get-History -Count 1 -ErrorAction SilentlyContinue\n"
        "  $cmd = if ($last) { $last.CommandLine } else { '' }\n"
        "  [Console]::Out.Write((\"`e]7770;{0};{1}`a\" -f $exitCode, $cmd))\n"
        "  if ($global:tutr_old_prompt) {\n"
        "    & $global:tutr_old_prompt\n"
        "  } else {\n"
        "    \"PS $($executionContext.SessionState.Path.CurrentLocation)> \"\n"
        "  }\n"
        "}\n"
    )
    profile.close()
    return profile.name
