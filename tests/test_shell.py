"""Unit tests for tutr.shell."""

import os
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tutr.config import TutrConfig
from tutr.models import ShellLaunchConfig
from tutr.shell.detection import (
    _build_shell_launch_config,
    _classify_shell,
    _detect_shell,
    _resolve_executable,
    _shell_candidates,
)
from tutr.shell.hooks import write_bash_rcfile, write_powershell_profile, write_zsh_rcdir
from tutr.shell.loop import _ask_tutor_with_cancel, shell_loop
from tutr.shell.shell import (
    _ask_tutor,
    _is_auto_run_accepted,
    _prompt_auto_run,
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


class TestPromptAutoRun:
    def test_accepts_lowercase_y_and_writes_to_pty(self):
        writes: list[tuple[int, bytes]] = []

        def _fake_write(fd: int, data: bytes) -> int:
            writes.append((fd, data))
            return len(data)

        with patch("tutr.shell.shell.os.read", return_value=b"y"):
            with patch("tutr.shell.shell.os.write", side_effect=_fake_write):
                _prompt_auto_run(10, 11, 12, "echo hi")

        assert writes == [
            (11, b"Run suggested command? [y/N] (Esc rejects): "),
            (11, b"y\r\n"),
            (12, b"echo hi\n"),
        ]

    def test_accepts_uppercase_y_and_writes_to_pty(self):
        writes: list[tuple[int, bytes]] = []

        def _fake_write(fd: int, data: bytes) -> int:
            writes.append((fd, data))
            return len(data)

        with patch("tutr.shell.shell.os.read", return_value=b"Y"):
            with patch("tutr.shell.shell.os.write", side_effect=_fake_write):
                _prompt_auto_run(10, 11, 12, "echo hi")

        assert writes == [
            (11, b"Run suggested command? [y/N] (Esc rejects): "),
            (11, b"y\r\n"),
            (12, b"echo hi\n"),
        ]

    @pytest.mark.parametrize("choice", [b"n", b"N", b"\x1b", b"\x03", b"\r", b"\n"])
    def test_reject_choices_write_no_and_do_not_run_command(self, choice: bytes):
        writes: list[tuple[int, bytes]] = []

        def _fake_write(fd: int, data: bytes) -> int:
            writes.append((fd, data))
            return len(data)

        with patch("tutr.shell.shell.os.read", return_value=choice):
            with patch("tutr.shell.shell.os.write", side_effect=_fake_write):
                _prompt_auto_run(10, 11, 12, "echo hi")

        assert writes == [
            (11, b"Run suggested command? [y/N] (Esc rejects): "),
            (11, b"n\r\n"),
        ]

    def test_empty_read_writes_newline_and_returns(self):
        writes: list[tuple[int, bytes]] = []

        def _fake_write(fd: int, data: bytes) -> int:
            writes.append((fd, data))
            return len(data)

        with patch("tutr.shell.shell.os.read", return_value=b""):
            with patch("tutr.shell.shell.os.write", side_effect=_fake_write):
                _prompt_auto_run(10, 11, 12, "echo hi")

        assert writes == [
            (11, b"Run suggested command? [y/N] (Esc rejects): "),
            (11, b"\r\n"),
        ]

    def test_oserror_from_read_writes_newline_and_returns(self):
        writes: list[tuple[int, bytes]] = []

        def _fake_write(fd: int, data: bytes) -> int:
            writes.append((fd, data))
            return len(data)

        with patch("tutr.shell.shell.os.read", side_effect=OSError("read failed")):
            with patch("tutr.shell.shell.os.write", side_effect=_fake_write):
                _prompt_auto_run(10, 11, 12, "echo hi")

        assert writes == [
            (11, b"Run suggested command? [y/N] (Esc rejects): "),
            (11, b"\r\n"),
        ]


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


class TestResolveExecutable:
    def test_pathlike_candidate_returns_when_executable(self, tmp_path: Path):
        executable = tmp_path / "tool"
        executable.write_text("#!/bin/sh\n", encoding="utf-8")
        executable.chmod(0o755)

        assert _resolve_executable(str(executable)) == str(executable)

    def test_relative_pathlike_candidate_returns_when_executable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        executable = tmp_path / "tool"
        executable.write_text("#!/bin/sh\n", encoding="utf-8")
        executable.chmod(0o755)
        monkeypatch.chdir(tmp_path)

        assert _resolve_executable(f".{os.path.sep}tool") == f".{os.path.sep}tool"

    def test_pathlike_candidate_returns_none_when_not_executable(self, tmp_path: Path):
        not_executable = tmp_path / "tool"
        not_executable.write_text("echo hi\n", encoding="utf-8")
        not_executable.chmod(0o644)

        assert _resolve_executable(str(not_executable)) is None

    def test_bare_command_uses_shutil_which(self):
        with patch("tutr.shell.detection.shutil.which", return_value="/usr/bin/bash") as mock_which:
            assert _resolve_executable("bash") == "/usr/bin/bash"

        mock_which.assert_called_once_with("bash")

    def test_bare_command_returns_none_when_which_fails(self):
        with patch("tutr.shell.detection.shutil.which", return_value=None):
            assert _resolve_executable("does-not-exist") is None


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
        assert "if ($tutrPrefix) {" in content
        assert '"$tutrPrefix $(& $global:tutr_old_prompt)"' in content


class TestShellLaunchEnv:
    @patch("tutr.shell.detection._detect_shell", return_value=("bash", "/bin/bash"))
    @patch("tutr.shell.detection.write_bash_rcfile", return_value="/tmp/tutr_test.bashrc")
    def test_launch_env_sets_tutr_active(self, _write, _detect):
        launch = _build_shell_launch_config()
        assert launch.env.get("TUTR_ACTIVE") == "1"
        assert launch.env.get("TUTR_AUTOSTARTED") == "1"

    @patch("tutr.shell.detection._detect_shell", return_value=("zsh", "/bin/zsh"))
    @patch("tutr.shell.detection.write_zsh_rcdir", return_value="/tmp/tutr_test_zdotdir")
    def test_zsh_launch_sets_zdotdir_and_uses_interactive_argv(self, _write, _detect):
        launch = _build_shell_launch_config()
        assert launch.argv == ["/bin/zsh", "-i"]
        assert launch.env.get("ZDOTDIR") == "/tmp/tutr_test_zdotdir"
        assert launch.cleanup_paths == ["/tmp/tutr_test_zdotdir"]

    @patch("tutr.shell.detection._detect_shell", return_value=("powershell", "C:/pwsh.exe"))
    @patch("tutr.shell.detection.write_powershell_profile", return_value="/tmp/tutr_profile.ps1")
    def test_powershell_launch_uses_expected_args_and_profile_cleanup(self, _write, _detect):
        launch = _build_shell_launch_config()
        assert launch.argv == [
            "C:/pwsh.exe",
            "-NoLogo",
            "-NoExit",
            "-File",
            "/tmp/tutr_profile.ps1",
        ]
        assert launch.cleanup_paths == ["/tmp/tutr_profile.ps1"]


class TestShellLoop:
    def test_shell_loop_strips_markers_resets_context_and_cleans_up(self):
        marker_one = b"\033]7770;1;first bad\007"
        marker_two = b"\033]7770;2;second bad\007"
        pty_reads: Iterator[bytes] = iter(
            [
                b"before-one\n",
                marker_one + b"middle\n",
                marker_two + b"tail\n",
            ]
        )
        writes: list[tuple[int, bytes]] = []
        tutor_calls: list[tuple[str, str]] = []
        removed_files: list[str] = []
        removed_dirs: list[str] = []

        launch = ShellLaunchConfig(
            kind="bash",
            executable="/bin/bash",
            argv=["/bin/bash", "-i"],
            env={"PATH": "/usr/bin"},
            cleanup_paths=["/tmp/tutr-test-file", "/tmp/tutr-test-dir"],
        )
        fake_stdin = MagicMock()
        fake_stdin.isatty.return_value = True
        fake_stdin.fileno.return_value = 10
        fake_stdout = MagicMock()
        fake_stdout.fileno.return_value = 11
        fake_select = [
            ([20], [], []),
            ([20], [], []),
            ([20], [], []),
            ValueError("done"),
        ]

        def _fake_read(fd: int, _size: int) -> bytes:
            if fd == 20:
                return next(pty_reads)
            raise AssertionError(f"unexpected os.read fd={fd}")

        def _fake_write(fd: int, data: bytes) -> int:
            writes.append((fd, data))
            return len(data)

        def _fake_ask(command: str, output: str, *_: object) -> tuple[bytes, str | None]:
            tutor_calls.append((command, output))
            return b"hint\r\n", None

        with ExitStack() as stack:
            stack.enter_context(
                patch("tutr.shell.loop.load_shell_config", return_value=TutrConfig())
            )
            stack.enter_context(
                patch("tutr.shell.loop._build_shell_launch_config", return_value=launch)
            )
            stack.enter_context(patch("tutr.shell.loop.sys.stdin", fake_stdin))
            stack.enter_context(patch("tutr.shell.loop.sys.stdout", fake_stdout))
            stack.enter_context(patch("tutr.shell.loop._winsize", return_value=(24, 80, 0, 0)))
            stack.enter_context(patch("tutr.shell.loop._set_winsize"))
            stack.enter_context(patch("tutr.shell.loop.os.openpty", return_value=(20, 21)))
            stack.enter_context(patch("tutr.shell.loop.os.fork", return_value=123))
            stack.enter_context(patch("tutr.shell.loop.os.close"))
            stack.enter_context(patch("tutr.shell.loop.signal.signal"))
            stack.enter_context(
                patch(
                    "tutr.shell.loop.termios.tcgetattr",
                    return_value=[0, 0, 0, 0, 0, 0],
                )
            )
            stack.enter_context(patch("tutr.shell.loop.tty.setraw"))
            stack.enter_context(patch("tutr.shell.loop.select.select", side_effect=fake_select))
            stack.enter_context(patch("tutr.shell.loop.os.read", side_effect=_fake_read))
            stack.enter_context(patch("tutr.shell.loop.os.write", side_effect=_fake_write))
            stack.enter_context(
                patch("tutr.shell.loop._shell_status_line", return_value=b"status\r\n")
            )
            stack.enter_context(patch("tutr.shell.loop._should_ask_tutor", return_value=True))
            stack.enter_context(
                patch("tutr.shell.loop._ask_tutor_with_cancel", side_effect=_fake_ask)
            )
            stack.enter_context(
                patch(
                    "tutr.shell.loop.os.path.isdir",
                    side_effect=lambda path: path.endswith("-dir"),
                )
            )
            stack.enter_context(
                patch("tutr.shell.loop.os.unlink", side_effect=removed_files.append)
            )
            stack.enter_context(
                patch("tutr.shell.loop.shutil.rmtree", side_effect=removed_dirs.append)
            )
            stack.enter_context(patch("tutr.shell.loop.termios.tcsetattr"))
            stack.enter_context(patch("tutr.shell.loop.os.waitpid", return_value=(123, 0)))
            stack.enter_context(patch("tutr.shell.loop.os.waitstatus_to_exitcode", return_value=0))
            exit_code = shell_loop()

        assert exit_code == 0
        assert tutor_calls == [("first bad", "before-one\n"), ("second bad", "middle\n")]

        visible_output = b"".join(data for fd, data in writes if fd == 11)
        assert marker_one not in visible_output
        assert marker_two not in visible_output
        assert b"before-one\n" in visible_output
        assert b"middle\n" in visible_output
        assert b"tail\n" in visible_output

        assert removed_files == ["/tmp/tutr-test-file"]
        assert removed_dirs == ["/tmp/tutr-test-dir"]
