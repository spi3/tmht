"""Unit tests for tmht.context."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from tmht.context import (
    _get_distro,
    gather_context,
    get_help_output,
    get_man_page,
    get_system_info,
)


def make_result(stdout="", stderr="", returncode=0):
    """Return a mock CompletedProcess-like object."""
    result = MagicMock()
    result.stdout = stdout
    result.stderr = stderr
    result.returncode = returncode
    return result


class TestGetHelpOutput:
    """Tests for get_help_output()."""

    @patch("tmht.context.subprocess.run")
    def test_returns_stdout(self, mock_run):
        mock_run.return_value = make_result(stdout="usage: git [options]")
        assert get_help_output("git") == "usage: git [options]"
        mock_run.assert_called_once_with(
            ["git", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )

    @patch("tmht.context.subprocess.run")
    def test_falls_back_to_stderr_when_stdout_empty(self, mock_run):
        mock_run.return_value = make_result(stdout="", stderr="usage: curl [options]")
        assert get_help_output("curl") == "usage: curl [options]"

    @patch("tmht.context.subprocess.run")
    def test_returns_none_when_both_outputs_empty(self, mock_run):
        mock_run.return_value = make_result(stdout="", stderr="")
        assert get_help_output("noop") is None

    @patch("tmht.context.subprocess.run")
    def test_returns_none_when_output_is_only_whitespace(self, mock_run):
        mock_run.return_value = make_result(stdout="   \n\t  ", stderr="")
        assert get_help_output("noop") is None

    @patch("tmht.context.subprocess.run")
    def test_strips_surrounding_whitespace(self, mock_run):
        mock_run.return_value = make_result(stdout="  help text  ")
        assert get_help_output("cmd") == "help text"

    @patch("tmht.context.subprocess.run")
    def test_returns_none_on_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="slow --help", timeout=5)
        assert get_help_output("slow") is None

    @patch("tmht.context.subprocess.run")
    def test_returns_none_on_file_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError("no such file")
        assert get_help_output("nonexistent") is None

    @patch("tmht.context.subprocess.run")
    def test_returns_none_on_permission_error(self, mock_run):
        mock_run.side_effect = PermissionError("permission denied")
        assert get_help_output("restricted") is None


class TestGetManPage:
    """Tests for get_man_page()."""

    @patch("tmht.context.subprocess.run")
    def test_returns_man_output(self, mock_run):
        mock_run.return_value = make_result(stdout="GIT(1)\n\nNAME\n    git\n", returncode=0)
        result = get_man_page("git")
        assert result is not None
        assert "GIT(1)" in result
        assert "NAME" in result

    @patch("tmht.context.subprocess.run")
    def test_truncates_output_when_exceeding_max_lines(self, mock_run):
        long_output = "\n".join(f"line {i}" for i in range(300))
        mock_run.return_value = make_result(stdout=long_output, returncode=0)
        result = get_man_page("git", max_lines=200)
        assert result is not None
        # The truncation notice is embedded in the result text
        assert "truncated" in result
        assert "200 of 300 lines shown" in result
        # Only the first max_lines content lines are present; line 200 onward must be absent
        assert "line 199" in result
        assert "line 200" not in result.splitlines()[:201]

    @patch("tmht.context.subprocess.run")
    def test_does_not_truncate_when_within_max_lines(self, mock_run):
        output = "\n".join(f"line {i}" for i in range(10))
        mock_run.return_value = make_result(stdout=output, returncode=0)
        result = get_man_page("git", max_lines=200)
        assert result is not None
        assert "truncated" not in result
        assert len(result.splitlines()) == 10

    @patch("tmht.context.subprocess.run")
    def test_returns_none_on_nonzero_returncode(self, mock_run):
        mock_run.return_value = make_result(stdout="No manual entry for fakecmd", returncode=16)
        assert get_man_page("fakecmd") is None

    @patch("tmht.context.subprocess.run")
    def test_returns_none_when_stdout_empty_with_zero_returncode(self, mock_run):
        mock_run.return_value = make_result(stdout="", returncode=0)
        assert get_man_page("emptycmd") is None

    @patch("tmht.context.subprocess.run")
    def test_returns_none_when_stdout_is_only_whitespace(self, mock_run):
        mock_run.return_value = make_result(stdout="   \n  ", returncode=0)
        assert get_man_page("whitespace") is None

    @patch("tmht.context.subprocess.run")
    def test_returns_none_on_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="man slow", timeout=10)
        assert get_man_page("slow") is None

    @patch("tmht.context.subprocess.run")
    def test_returns_none_on_file_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError("man not found")
        assert get_man_page("anything") is None

    @patch("tmht.context.subprocess.run")
    def test_sets_manpager_and_manwidth_env(self, mock_run):
        mock_run.return_value = make_result(stdout="some output", returncode=0)
        get_man_page("git")
        _, kwargs = mock_run.call_args
        env = kwargs.get("env") or mock_run.call_args[1].get("env")
        assert env["MANPAGER"] == "cat"
        assert env["MANWIDTH"] == "120"

    @patch("tmht.context.subprocess.run")
    def test_truncation_uses_custom_max_lines(self, mock_run):
        long_output = "\n".join(f"line {i}" for i in range(50))
        mock_run.return_value = make_result(stdout=long_output, returncode=0)
        result = get_man_page("git", max_lines=10)
        assert result is not None
        assert "10 of 50 lines shown" in result


class TestGatherContext:
    """Tests for gather_context()."""

    @patch("tmht.context.get_man_page")
    @patch("tmht.context.get_help_output")
    def test_combines_help_and_man(self, mock_help, mock_man):
        mock_help.return_value = "help text"
        mock_man.return_value = "man text"
        result = gather_context("git")
        assert "=== git --help ===" in result
        assert "help text" in result
        assert "=== man git ===" in result
        assert "man text" in result

    @patch("tmht.context.get_man_page")
    @patch("tmht.context.get_help_output")
    def test_only_help_when_man_unavailable(self, mock_help, mock_man):
        mock_help.return_value = "help text"
        mock_man.return_value = None
        result = gather_context("git")
        assert "=== git --help ===" in result
        assert "help text" in result
        assert "man git" not in result

    @patch("tmht.context.get_man_page")
    @patch("tmht.context.get_help_output")
    def test_only_man_when_help_unavailable(self, mock_help, mock_man):
        mock_help.return_value = None
        mock_man.return_value = "man text"
        result = gather_context("git")
        assert "git --help" not in result
        assert "=== man git ===" in result
        assert "man text" in result

    @patch("tmht.context.get_man_page")
    @patch("tmht.context.get_help_output")
    def test_fallback_message_when_no_docs_found(self, mock_help, mock_man):
        mock_help.return_value = None
        mock_man.return_value = None
        result = gather_context("unknowncmd")
        assert "No documentation found for 'unknowncmd'" in result
        assert "Rely on general knowledge" in result

    @patch("tmht.context.get_man_page")
    @patch("tmht.context.get_help_output")
    def test_sections_separated_by_double_newline(self, mock_help, mock_man):
        mock_help.return_value = "help text"
        mock_man.return_value = "man text"
        result = gather_context("git")
        assert "\n\n" in result

    @patch("tmht.context.get_man_page")
    @patch("tmht.context.get_help_output")
    def test_returns_string(self, mock_help, mock_man):
        mock_help.return_value = None
        mock_man.return_value = None
        result = gather_context("git")
        assert isinstance(result, str)

    def test_returns_empty_string_when_cmd_is_none(self):
        result = gather_context(None)
        assert result == ""


class TestGetDistro:
    """Tests for _get_distro()."""

    @patch("tmht.context.platform.system", return_value="Darwin")
    @patch("tmht.context.platform.mac_ver", return_value=("14.2.1", ("", "", ""), ""))
    def test_macos_with_version(self, mock_mac_ver, mock_system):
        assert _get_distro() == "macOS 14.2.1"

    @patch("tmht.context.platform.system", return_value="Darwin")
    @patch("tmht.context.platform.mac_ver", return_value=("", ("", "", ""), ""))
    def test_macos_without_version(self, mock_mac_ver, mock_system):
        assert _get_distro() == "macOS"

    @patch("tmht.context.platform.system", return_value="Linux")
    @patch(
        "tmht.context.platform.freedesktop_os_release",
        return_value={"PRETTY_NAME": "Debian GNU/Linux 12 (bookworm)", "NAME": "Debian GNU/Linux"},
    )
    def test_linux_pretty_name(self, mock_os_release, mock_system):
        assert _get_distro() == "Debian GNU/Linux 12 (bookworm)"

    @patch("tmht.context.platform.system", return_value="Linux")
    @patch(
        "tmht.context.platform.freedesktop_os_release",
        return_value={"NAME": "Fedora Linux"},
    )
    def test_linux_falls_back_to_name(self, mock_os_release, mock_system):
        assert _get_distro() == "Fedora Linux"

    @patch("tmht.context.platform.system", return_value="Linux")
    @patch(
        "tmht.context.platform.freedesktop_os_release",
        side_effect=OSError("not found"),
    )
    def test_linux_falls_back_to_system_on_oserror(self, mock_os_release, mock_system):
        assert _get_distro() == "Linux"


class TestGetSystemInfo:
    """Tests for get_system_info()."""

    @patch("tmht.context._get_distro", return_value="Debian GNU/Linux 12 (bookworm)")
    @patch("tmht.context.platform.release", return_value="6.1.0")
    @patch.dict("os.environ", {"SHELL": "/bin/bash"})
    def test_returns_distro_kernel_and_shell(self, mock_release, mock_distro):
        result = get_system_info()
        assert "OS: Debian GNU/Linux 12 (bookworm) (6.1.0)" in result
        assert "Shell: /bin/bash" in result

    @patch("tmht.context._get_distro", return_value="macOS 14.2.1")
    @patch("tmht.context.platform.release", return_value="23.2.0")
    @patch.dict("os.environ", {"SHELL": "/bin/zsh"})
    def test_macos_with_zsh(self, mock_release, mock_distro):
        result = get_system_info()
        assert "OS: macOS 14.2.1 (23.2.0)" in result
        assert "Shell: /bin/zsh" in result

    @patch("tmht.context._get_distro", return_value="Linux")
    @patch("tmht.context.platform.release", return_value="5.15.0")
    @patch.dict("os.environ", {}, clear=True)
    def test_unknown_shell_when_env_missing(self, mock_release, mock_distro):
        result = get_system_info()
        assert "Shell: unknown" in result

    def test_returns_string(self):
        result = get_system_info()
        assert isinstance(result, str)

    def test_contains_os_and_shell_labels(self):
        result = get_system_info()
        assert "OS:" in result
        assert "Shell:" in result
