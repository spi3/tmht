"""Unit tests for tmht.cli."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tmht.cli import entrypoint, main


def _make_llm_result(command="git checkout -b testing"):
    result = MagicMock()
    result.command = command
    return result


def _cli_patches(**overrides):
    """Return a patch.multiple context with standard defaults plus overrides."""
    defaults = dict(
        needs_setup=MagicMock(return_value=False),
        load_config=MagicMock(return_value={}),
        run_setup=MagicMock(return_value={}),
        run=MagicMock(return_value=_make_llm_result()),
    )
    defaults.update(overrides)
    return patch.multiple("tmht.cli", **defaults)


# ---------------------------------------------------------------------------
# main() — successful run
# ---------------------------------------------------------------------------


class TestMainSuccess:
    def test_returns_zero_on_success(self):
        with _cli_patches(run=MagicMock(return_value=_make_llm_result("ls -la"))):
            assert main(["ls", "list files"]) == 0

    def test_prints_command_to_stdout(self, capsys):
        with _cli_patches(run=MagicMock(return_value=_make_llm_result("ls -la"))):
            main(["ls", "list files"])

        out = capsys.readouterr().out
        assert "ls -la" in out

    def test_passes_words_to_run(self):
        mock_run = MagicMock(return_value=_make_llm_result())
        with _cli_patches(run=mock_run):
            main(["git", "create", "and", "switch", "to", "new", "branch"])

        words_arg = mock_run.call_args[0][0]
        assert words_arg == ["git", "create", "and", "switch", "to", "new", "branch"]

    def test_calls_load_config_when_needs_setup_false(self):
        mock_load = MagicMock(return_value={})
        mock_run_setup = MagicMock(return_value={})
        with _cli_patches(load_config=mock_load, run_setup=mock_run_setup):
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
            main(["git", "status"])

        mock_run_setup.assert_called_once()
        mock_load.assert_not_called()


# ---------------------------------------------------------------------------
# main() — run() raises an exception
# ---------------------------------------------------------------------------


class TestMainLlmError:
    def test_returns_one_on_exception(self):
        with _cli_patches(run=MagicMock(side_effect=RuntimeError("API failure"))):
            assert main(["curl", "fetch a page"]) == 1

    def test_prints_error_to_stderr_on_exception(self, capsys):
        with _cli_patches(run=MagicMock(side_effect=ValueError("bad response"))):
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
            with pytest.raises(SystemExit) as exc_info:
                with patch.object(sys, "argv", ["tmht", "git", "status"]):
                    entrypoint()

        assert exc_info.value.code == 0

    def test_entrypoint_exits_with_one_on_error(self):
        with _cli_patches(run=MagicMock(side_effect=Exception("boom"))):
            with pytest.raises(SystemExit) as exc_info:
                with patch.object(sys, "argv", ["tmht", "git", "status"]):
                    entrypoint()

        assert exc_info.value.code == 1
