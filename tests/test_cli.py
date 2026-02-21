"""Unit tests for tmht.cli."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tmht.cli import entrypoint, main


PATCHES = [
    "tmht.cli.needs_setup",
    "tmht.cli.load_config",
    "tmht.cli.run_setup",
    "tmht.cli.gather_context",
    "tmht.cli.build_messages",
    "tmht.cli.query_llm",
]


def _make_llm_result(command="git checkout -b testing"):
    result = MagicMock()
    result.command = command
    return result


def _apply_defaults(mocks):
    """Apply safe defaults to the six patched objects (order matches PATCHES)."""
    needs_setup, load_config, run_setup, gather_context, build_messages, query_llm = mocks
    needs_setup.return_value = False
    load_config.return_value = {"model": "test/model"}
    run_setup.return_value = {"model": "test/model"}
    gather_context.return_value = "some context"
    build_messages.return_value = [{"role": "user", "content": "help"}]
    query_llm.return_value = _make_llm_result()


def _cli_patches(**overrides):
    """Return a patch.multiple context with standard defaults plus overrides."""
    defaults = dict(
        needs_setup=MagicMock(return_value=False),
        load_config=MagicMock(return_value={}),
        gather_context=MagicMock(return_value="ctx"),
        get_system_info=MagicMock(return_value="OS: Linux 6.1.0\nShell: /bin/bash"),
        build_messages=MagicMock(return_value=[]),
        query_llm=MagicMock(return_value=_make_llm_result()),
    )
    defaults.update(overrides)
    return patch.multiple("tmht.cli", **defaults)


# ---------------------------------------------------------------------------
# main() — successful run
# ---------------------------------------------------------------------------


class TestMainSuccess:
    def test_returns_zero_on_success(self):
        with _cli_patches(query_llm=MagicMock(return_value=_make_llm_result("ls -la"))):
            with patch("shutil.which", return_value="/usr/bin/ls"):
                assert main(["ls", "list files"]) == 0

    def test_prints_command_to_stdout(self, capsys):
        with _cli_patches(query_llm=MagicMock(return_value=_make_llm_result("ls -la"))):
            with patch("shutil.which", return_value="/usr/bin/ls"):
                main(["ls", "list files"])

        out = capsys.readouterr().out
        assert "ls -la" in out

    def test_multi_word_query_joined_with_spaces(self):
        mock_build = MagicMock(return_value=[])
        with _cli_patches(build_messages=mock_build):
            with patch("shutil.which", return_value="/usr/bin/git"):
                main(["git", "create", "and", "switch", "to", "new", "branch"])

        call_args = mock_build.call_args
        # second positional arg is query
        query_arg = call_args[0][1]
        assert query_arg == "create and switch to new branch"

    def test_calls_load_config_when_needs_setup_false(self):
        mock_load = MagicMock(return_value={})
        mock_run_setup = MagicMock(return_value={})
        with _cli_patches(load_config=mock_load, run_setup=mock_run_setup):
            with patch("shutil.which", return_value="/usr/bin/git"):
                main(["git", "status"])

        mock_load.assert_called_once()
        mock_run_setup.assert_not_called()

    def test_calls_run_setup_when_needs_setup_true(self):
        mock_load = MagicMock(return_value={})
        mock_run_setup = MagicMock(return_value={})
        with _cli_patches(
            needs_setup=MagicMock(return_value=True),
            load_config=mock_load,
            run_setup=mock_run_setup,
        ):
            with patch("shutil.which", return_value="/usr/bin/git"):
                main(["git", "status"])

        mock_run_setup.assert_called_once()
        mock_load.assert_not_called()


# ---------------------------------------------------------------------------
# main() — command not found, all words become the query
# ---------------------------------------------------------------------------


class TestMainCommandNotFound:
    def test_unknown_command_folds_into_query(self):
        mock_build = MagicMock(return_value=[])
        with _cli_patches(build_messages=mock_build):
            with patch("shutil.which", return_value=None):
                main(["how", "do", "I", "list", "files"])

        call_args = mock_build.call_args
        cmd_arg = call_args[0][0]
        query_arg = call_args[0][1]
        assert cmd_arg is None
        assert query_arg == "how do I list files"

    def test_unknown_command_gathers_no_context(self):
        mock_gather = MagicMock(return_value="")
        with _cli_patches(gather_context=mock_gather):
            with patch("shutil.which", return_value=None):
                main(["how", "do", "I", "list", "files"])

        mock_gather.assert_called_once_with(None)

    def test_known_command_passes_cmd(self):
        mock_build = MagicMock(return_value=[])
        with _cli_patches(build_messages=mock_build):
            with patch("shutil.which", return_value="/usr/bin/git"):
                main(["git", "create", "a", "branch"])

        call_args = mock_build.call_args
        cmd_arg = call_args[0][0]
        query_arg = call_args[0][1]
        assert cmd_arg == "git"
        assert query_arg == "create a branch"


# ---------------------------------------------------------------------------
# main() — query_llm raises an exception
# ---------------------------------------------------------------------------


class TestMainLlmError:
    def test_returns_one_on_llm_exception(self):
        with _cli_patches(query_llm=MagicMock(side_effect=RuntimeError("API failure"))):
            with patch("shutil.which", return_value="/usr/bin/curl"):
                assert main(["curl", "fetch a page"]) == 1

    def test_prints_error_to_stderr_on_exception(self, capsys):
        with _cli_patches(query_llm=MagicMock(side_effect=ValueError("bad response"))):
            with patch("shutil.which", return_value="/usr/bin/curl"):
                main(["curl", "fetch a page"])

        err = capsys.readouterr().err
        assert "bad response" in err


# ---------------------------------------------------------------------------
# main() — argparse edge cases
# ---------------------------------------------------------------------------


class TestMainArgparse:
    def test_version_flag_raises_system_exit(self):
        with pytest.raises(SystemExit):
            main(["--version"])

    def test_version_output_contains_version_string(self, capsys):
        with pytest.raises(SystemExit):
            main(["--version"])

        out = capsys.readouterr().out
        assert "0.1.0" in out

    def test_no_args_raises_system_exit(self):
        with pytest.raises(SystemExit):
            main([])

    def test_no_args_exits_with_nonzero_code(self):
        with pytest.raises(SystemExit) as exc_info:
            main([])

        assert exc_info.value.code != 0


# ---------------------------------------------------------------------------
# entrypoint()
# ---------------------------------------------------------------------------


class TestEntrypoint:
    def test_entrypoint_raises_system_exit(self):
        with _cli_patches():
            with patch("shutil.which", return_value="/usr/bin/git"):
                with pytest.raises(SystemExit) as exc_info:
                    entrypoint.__wrapped__ = None  # ensure we call the real one
                    # Provide argv via sys.argv override
                    with patch.object(sys, "argv", ["tmht", "git", "status"]):
                        entrypoint()

        assert exc_info.value.code == 0

    def test_entrypoint_exits_with_one_on_llm_error(self):
        with _cli_patches(query_llm=MagicMock(side_effect=Exception("boom"))):
            with patch("shutil.which", return_value="/usr/bin/git"):
                with pytest.raises(SystemExit) as exc_info:
                    with patch.object(sys, "argv", ["tmht", "git", "status"]):
                        entrypoint()

        assert exc_info.value.code == 1
