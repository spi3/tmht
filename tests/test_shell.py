"""Unit tests for tutr.shell."""

import os
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from tutr.config import TutrConfig
from tutr.shell.detection import (
    _build_shell_launch_config,
    _classify_shell,
    _detect_shell,
    _shell_candidates,
)
from tutr.shell.hooks import write_bash_rcfile, write_powershell_profile, write_zsh_rcdir
from tutr.shell.loop import _ask_tutor_with_cancel
from tutr.shell.shell import (
    _ask_tutor,
    _is_auto_run_accepted,
    _shell_status_line,
    _should_ask_tutor,
)


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
    @patch("tutr.shell.detection.os.name", "posix")
    def test_candidates_prefer_override_then_env(self):
        assert _shell_candidates()[:4] == ["zsh", "/bin/bash", "bash", "pwsh"]

    @patch.dict("os.environ", {"SHELL": "/bin/zsh"}, clear=False)
    @patch("tutr.shell.detection.os.name", "posix")
    @patch("tutr.shell.detection._resolve_executable", side_effect=lambda value: value)
    def test_detect_shell_uses_shell_env_when_supported(self, _resolve):
        assert _detect_shell() == ("zsh", "/bin/zsh")

    @patch.dict("os.environ", {"SHELL": "/usr/bin/fish"}, clear=False)
    @patch("tutr.shell.detection.os.name", "posix")
    @patch(
        "tutr.shell.detection._resolve_executable",
        side_effect=lambda value: {"bash": "/bin/bash"}.get(value),
    )
    def test_detect_shell_falls_back_to_bash(self, _resolve):
        assert _detect_shell() == ("bash", "/bin/bash")

    @patch.dict("os.environ", {}, clear=True)
    @patch("tutr.shell.detection.os.name", "nt")
    @patch(
        "tutr.shell.detection._resolve_executable",
        side_effect=lambda value: {"pwsh": "C:/Program Files/PowerShell/7/pwsh.exe"}.get(value),
    )
    def test_detect_shell_prefers_pwsh_on_windows(self, _resolve):
        kind, executable = _detect_shell()
        assert kind == "powershell"
        assert executable.endswith("pwsh.exe")


class TestCancelableTutorInvocation:
    def test_escape_cancels_inflight_tutor_request(self):
        stdin_r, stdin_w = os.pipe()
        config = TutrConfig()

        def _write_escape():
            time.sleep(0.05)
            os.write(stdin_w, b"\x1b")

        def _slow_tutor(*_):
            time.sleep(5)
            return b"never", "echo no"

        writer = threading.Thread(target=_write_escape)
        writer.start()
        with patch("tutr.shell.loop._ask_tutor", side_effect=_slow_tutor):
            suggestion, command = _ask_tutor_with_cancel("bad", "output", config, stdin_r)
        writer.join(timeout=1)
        os.close(stdin_r)
        os.close(stdin_w)

        assert b"tutr canceled." in suggestion
        assert command is None

    def test_ctrl_c_cancels_inflight_tutor_request(self):
        stdin_r, stdin_w = os.pipe()
        config = TutrConfig()

        def _write_ctrl_c():
            time.sleep(0.05)
            os.write(stdin_w, b"\x03")

        def _slow_tutor(*_):
            time.sleep(5)
            return b"never", "echo no"

        writer = threading.Thread(target=_write_ctrl_c)
        writer.start()
        with patch("tutr.shell.loop._ask_tutor", side_effect=_slow_tutor):
            suggestion, command = _ask_tutor_with_cancel("bad", "output", config, stdin_r)
        writer.join(timeout=1)
        os.close(stdin_r)
        os.close(stdin_w)

        assert b"tutr canceled." in suggestion
        assert command is None

    def test_returns_tutor_response_when_not_canceled(self):
        stdin_r, stdin_w = os.pipe()
        config = TutrConfig()

        with patch("tutr.shell.loop._ask_tutor", return_value=(b"hello", "echo hi")):
            suggestion, command = _ask_tutor_with_cancel("bad", "output", config, stdin_r)

        os.close(stdin_r)
        os.close(stdin_w)

        assert suggestion == b"hello"
        assert command == "echo hi"


class TestAskTutorMessageFormatting:
    def test_includes_explanation_when_enabled(self):
        config = TutrConfig(show_explanation=True)
        result = MagicMock(command="ls -la", explanation="Lists all files.", source="man ls")
        with patch("tutr.shell.shell.run_query", return_value=result):
            msg, command = _ask_tutor("bad cmd", "error output", config)

        text = msg.decode()
        assert "ls -la" in text
        assert "Lists all files." in text
        assert "source: man ls" in text
        assert command == "ls -la"

    def test_omits_explanation_when_disabled(self):
        config = TutrConfig(show_explanation=False)
        result = MagicMock(command="ls -la", explanation="Lists all files.", source="man ls")
        with patch("tutr.shell.shell.run_query", return_value=result):
            msg, _ = _ask_tutor("bad cmd", "error output", config)

        text = msg.decode()
        assert "ls -la" in text
        assert "Lists all files." not in text
        assert "source: man ls" not in text

    def test_uses_unsplit_query_and_detects_command_name(self):
        config = TutrConfig(show_explanation=False)
        result = MagicMock(command="git checkout -- .", explanation="", source=None)
        command_text = "git commit --amend -m 'fix tests'"
        output_text = "error: nothing to amend"
        expected_query = (
            "fix this command: git commit --amend -m 'fix tests'\n\n"
            "Terminal output:\nerror: nothing to amend"
        )

        with patch("tutr.shell.shell.run_query", return_value=result) as mock_run_query:
            _ask_tutor(command_text, output_text, config)

        mock_run_query.assert_called_once_with(expected_query, config, cmd="git")

    def test_blocks_unsafe_suggestion_by_default(self):
        config = TutrConfig(show_explanation=False)
        result = MagicMock(command="rm -rf /tmp/test", explanation="", source=None)
        with patch("tutr.shell.shell.run_query", return_value=result):
            msg, command = _ask_tutor("bad cmd", "error output", config)

        text = msg.decode()
        assert "blocked a potentially dangerous suggestion" in text
        assert "rm -rf style" in text
        assert command is None

    @patch.dict("os.environ", {"TUTR_ALLOW_UNSAFE": "1"}, clear=False)
    def test_unsafe_override_allows_suggestion(self):
        config = TutrConfig(show_explanation=False)
        result = MagicMock(command="rm -rf /tmp/test", explanation="", source=None)
        with patch("tutr.shell.shell.run_query", return_value=result):
            msg, command = _ask_tutor("bad cmd", "error output", config)

        text = msg.decode()
        assert "unsafe override enabled" in text
        assert "rm -rf /tmp/test" in text
        assert command == "rm -rf /tmp/test"


class TestShellStatusLine:
    @patch.dict("os.environ", {"TERM": "xterm-256color"}, clear=True)
    def test_uses_color_by_default(self):
        text = _shell_status_line().decode()
        assert "\x1b[" in text
        assert "tutr active" in text
        assert "Ctrl-D to exit" in text

    @patch.dict("os.environ", {"NO_COLOR": "1", "TERM": "xterm-256color"}, clear=True)
    def test_honors_no_color(self):
        text = _shell_status_line().decode()
        assert "\x1b[" not in text
        assert "tutr active" in text
        assert "Ctrl-D to exit" in text


class TestShellEntrypoint:
    def test_entrypoint_checks_for_updates_before_shell_loop(self):
        with patch("tutr.shell.notify_if_update_available_async") as mock_update:
            with patch("tutr.shell.shell_loop", return_value=0):
                with patch.object(sys, "argv", ["tutr"]):
                    try:
                        from tutr.shell import entrypoint

                        entrypoint()
                    except SystemExit as exc:
                        assert exc.code == 0

        mock_update.assert_called_once()

    def test_entrypoint_passes_no_execute_override_to_shell_loop(self):
        with patch("tutr.shell.notify_if_update_available_async"):
            with patch("tutr.shell.shell_loop", return_value=0) as mock_shell_loop:
                with patch.object(sys, "argv", ["tutr", "--no-execute"]):
                    try:
                        from tutr.shell import entrypoint

                        entrypoint()
                    except SystemExit as exc:
                        assert exc.code == 0

        mock_shell_loop.assert_called_once_with(no_execute_override=True)


class TestShellHooks:
    def test_bash_hook_adds_prompt_marker(self):
        path = write_bash_rcfile()
        try:
            content = Path(path).read_text(encoding="utf-8")
        finally:
            os.unlink(path)
        assert '__tutr_prefix="${TUTR_PROMPT_PREFIX:-[tutr]}"' in content
        assert 'PS1="$__tutr_prefix ' in content

    def test_zsh_hook_adds_prompt_marker(self):
        rcdir = write_zsh_rcdir()
        rcfile = Path(rcdir) / ".zshrc"
        try:
            content = rcfile.read_text(encoding="utf-8")
        finally:
            os.unlink(rcfile)
            os.rmdir(rcdir)
        assert 'typeset -g __tutr_prefix="${TUTR_PROMPT_PREFIX:-[tutr]}"' in content
        assert 'PROMPT="$__tutr_prefix $PROMPT"' in content

    def test_powershell_hook_adds_prompt_marker(self):
        path = write_powershell_profile()
        try:
            content = Path(path).read_text(encoding="utf-8")
        finally:
            os.unlink(path)
        assert "$tutrPrefix = if ($env:TUTR_PROMPT_PREFIX)" in content
        assert 'if ($tutrPrefix) { "$tutrPrefix $(& $global:tutr_old_prompt)" }' in content


class TestShellLaunchEnv:
    @patch("tutr.shell.detection._detect_shell", return_value=("bash", "/bin/bash"))
    @patch("tutr.shell.detection.write_bash_rcfile", return_value="/tmp/tutr_test.bashrc")
    def test_launch_env_sets_tutr_active(self, _write, _detect):
        launch = _build_shell_launch_config()
        assert launch.env.get("TUTR_ACTIVE") == "1"
        assert launch.env.get("TUTR_AUTOSTARTED") == "1"
