"""Unit tests for tutr.shell."""

from unittest.mock import patch

from tutr.shell import _is_auto_run_accepted, _should_ask_tutor
from tutr.shell import _classify_shell, _detect_shell, _shell_candidates


class TestShouldAskTutor:
    def test_nonzero_exit_with_command_triggers(self):
        assert _should_ask_tutor(1, "git checkout main") is True

    def test_zero_exit_never_triggers(self):
        assert _should_ask_tutor(0, "git checkout main") is False

    def test_empty_command_never_triggers(self):
        assert _should_ask_tutor(1, "   ") is False

    def test_sigint_exit_code_130_never_triggers(self):
        assert _should_ask_tutor(130, "git checkout main") is False


class TestAutoRunPrompt:
    def test_yes_is_accepted(self):
        assert _is_auto_run_accepted(b"y") is True
        assert _is_auto_run_accepted(b"Y") is True

    def test_non_yes_is_rejected(self):
        assert _is_auto_run_accepted(b"n") is False
        assert _is_auto_run_accepted(b"\x1b") is False
        assert _is_auto_run_accepted(b"\x03") is False


class TestShellDetection:
    def test_classifies_supported_shell_names(self):
        assert _classify_shell("bash") == "bash"
        assert _classify_shell("/bin/zsh") == "zsh"
        assert _classify_shell("pwsh") == "powershell"
        assert _classify_shell("powershell.exe") == "powershell"

    def test_unknown_shell_name_returns_none(self):
        assert _classify_shell("/usr/bin/fish") is None

    @patch.dict("os.environ", {"TUTR_SHELL": "zsh", "SHELL": "/bin/bash"}, clear=False)
    @patch("tutr.shell.os.name", "posix")
    def test_candidates_prefer_override_then_env(self):
        assert _shell_candidates()[:4] == ["zsh", "/bin/bash", "bash", "pwsh"]

    @patch.dict("os.environ", {"SHELL": "/bin/zsh"}, clear=False)
    @patch("tutr.shell.os.name", "posix")
    @patch("tutr.shell._resolve_executable", side_effect=lambda value: value)
    def test_detect_shell_uses_shell_env_when_supported(self, _resolve):
        assert _detect_shell() == ("zsh", "/bin/zsh")

    @patch.dict("os.environ", {"SHELL": "/usr/bin/fish"}, clear=False)
    @patch("tutr.shell.os.name", "posix")
    @patch(
        "tutr.shell._resolve_executable",
        side_effect=lambda value: {"bash": "/bin/bash"}.get(value),
    )
    def test_detect_shell_falls_back_to_bash(self, _resolve):
        assert _detect_shell() == ("bash", "/bin/bash")

    @patch.dict("os.environ", {}, clear=True)
    @patch("tutr.shell.os.name", "nt")
    @patch(
        "tutr.shell._resolve_executable",
        side_effect=lambda value: {"pwsh": "C:/Program Files/PowerShell/7/pwsh.exe"}.get(value),
    )
    def test_detect_shell_prefers_pwsh_on_windows(self, _resolve):
        kind, executable = _detect_shell()
        assert kind == "powershell"
        assert executable.endswith("pwsh.exe")
