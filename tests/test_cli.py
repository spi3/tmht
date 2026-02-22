"""Unit tests for tutr.cli."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tutr import __version__
from tutr.cli import entrypoint, main
from tutr.config import TutrConfig
from tutr.models import CommandResponse
from tutr.tutr import MAX_QUERY_LENGTH


def _make_llm_result(command="git checkout -b testing", explanation="", source=None):
    return CommandResponse(command=command, explanation=explanation, source=source)


def _query_patches(**overrides):
    defaults = dict(
        needs_setup=MagicMock(return_value=False),
        load_config=MagicMock(return_value=TutrConfig()),
        run_setup=MagicMock(return_value=TutrConfig()),
        query_llm=MagicMock(return_value=_make_llm_result()),
        notify_if_update_available_async=MagicMock(),
    )
    defaults.update(overrides)
    return patch.multiple("tutr.cli.query", **defaults)


def _configure_patches(**overrides):
    config_file = MagicMock()
    config_file.exists.return_value = True
    defaults = dict(
        CONFIG_FILE=config_file,
        needs_setup=MagicMock(return_value=False),
        load_config=MagicMock(return_value=TutrConfig()),
        run_configure=MagicMock(return_value=TutrConfig()),
        notify_if_update_available_async=MagicMock(),
    )
    defaults.update(overrides)
    return patch.multiple("tutr.cli.configure", **defaults)


class TestMainSuccess:
    def test_returns_zero_on_success(self):
        with _query_patches(query_llm=MagicMock(return_value=_make_llm_result("ls -la"))):
            assert main(["ls", "list files"]) == 0

    def test_prints_command_to_stdout(self, capsys):
        with _query_patches(query_llm=MagicMock(return_value=_make_llm_result("ls -la"))):
            main(["ls", "list files"])

        out = capsys.readouterr().out
        assert "ls -la" in out

    def test_passes_words_to_run(self):
        mock_run = MagicMock(return_value=_make_llm_result())
        with _query_patches(query_llm=mock_run):
            main(["git", "create", "and", "switch", "to", "new", "branch"])

        assert mock_run.call_args[0][0] == ["git", "create", "and", "switch", "to", "new", "branch"]

    def test_calls_load_config_when_needs_setup_false(self):
        mock_load = MagicMock(return_value=TutrConfig())
        mock_run_setup = MagicMock(return_value=TutrConfig())
        with _query_patches(load_config=mock_load, run_setup=mock_run_setup):
            main(["git", "status"])

        mock_load.assert_called_once()
        mock_run_setup.assert_not_called()

    def test_calls_run_setup_when_needs_setup_true(self):
        mock_load = MagicMock(return_value=TutrConfig())
        mock_run_setup = MagicMock(return_value=TutrConfig())
        with _query_patches(
            needs_setup=MagicMock(return_value=True),
            load_config=mock_load,
            run_setup=mock_run_setup,
        ):
            main(["git", "status"])

        mock_run_setup.assert_called_once()
        mock_load.assert_not_called()


class TestMainLlmError:
    def test_returns_one_on_exception(self):
        with _query_patches(query_llm=MagicMock(side_effect=RuntimeError("API failure"))):
            assert main(["curl", "fetch a page"]) == 1

    def test_prints_error_to_stderr_on_exception(self, capsys):
        with _query_patches(query_llm=MagicMock(side_effect=ValueError("bad response"))):
            main(["curl", "fetch a page"])

        assert "bad response" in capsys.readouterr().err

    def test_returns_one_when_query_exceeds_max_length(self, capsys):
        long_query = "x" * (MAX_QUERY_LENGTH + 1)
        with (
            patch("tutr.cli.query.needs_setup", return_value=False),
            patch("tutr.cli.query.load_config", return_value=TutrConfig()),
            patch("tutr.cli.query.notify_if_update_available_async"),
            patch("tutr.tutr.gather_context"),
            patch("tutr.tutr.get_system_info"),
            patch("tutr.tutr.build_messages"),
            patch("tutr.tutr.query_llm"),
            patch("shutil.which", return_value=None),
        ):
            assert main([long_query]) == 1

        err = capsys.readouterr().err
        assert "Query is too long" in err

    def test_blocks_unsafe_suggestion_by_default(self, capsys):
        result = _make_llm_result("rm -rf ~/tmp")
        with _query_patches(query_llm=MagicMock(return_value=result)):
            assert main(["delete temp files"]) == 1

        err = capsys.readouterr().err
        assert "potentially dangerous" in err
        assert "rm -rf style" in err

    def test_allow_unsafe_flag_displays_unsafe_suggestion(self, capsys):
        result = _make_llm_result("rm -rf ~/tmp")
        with _query_patches(query_llm=MagicMock(return_value=result)):
            assert main(["--allow-unsafe", "delete temp files"]) == 0

        out_err = capsys.readouterr()
        assert "matched dangerous-pattern checks" in out_err.err
        assert "rm -rf ~/tmp" in out_err.out


class TestMainExplanationOutput:
    def test_prints_explanation_when_enabled_in_config(self, capsys):
        config = TutrConfig(show_explanation=True)
        result = _make_llm_result("ls -la", "Lists all files, including hidden ones.", "man ls")
        with _query_patches(
            load_config=MagicMock(return_value=config),
            query_llm=MagicMock(return_value=result),
        ):
            main(["ls", "list files"])

        out = capsys.readouterr().out
        assert "ls -la" in out
        assert "Lists all files, including hidden ones." in out
        assert "source: man ls" in out

    def test_prints_explanation_when_explain_flag_set(self, capsys):
        config = TutrConfig(show_explanation=False)
        result = _make_llm_result("ls -la", "Lists all files, including hidden ones.", "man ls")
        with _query_patches(
            load_config=MagicMock(return_value=config),
            query_llm=MagicMock(return_value=result),
        ):
            main(["--explain", "ls", "list files"])

        out = capsys.readouterr().out
        assert "ls -la" in out
        assert "Lists all files, including hidden ones." in out
        assert "source: man ls" in out


class TestMainArgparse:
    def test_version_flag_raises_system_exit(self):
        with pytest.raises(SystemExit):
            main(["--version"])

    def test_version_output_contains_version_string(self, capsys):
        with pytest.raises(SystemExit):
            main(["--version"])

        assert __version__ in capsys.readouterr().out

    def test_no_args_raises_system_exit(self):
        with pytest.raises(SystemExit):
            main([])

    def test_no_args_exits_with_nonzero_code(self):
        with pytest.raises(SystemExit) as exc_info:
            main([])

        assert exc_info.value.code != 0


class TestConfigureCommand:
    def test_defaults_to_interactive_when_no_options(self):
        mock_run_configure = MagicMock(
            return_value=TutrConfig(provider="openai", model="openai/gpt-4o")
        )
        with _configure_patches(
            run_configure=mock_run_configure,
            load_config=MagicMock(return_value=TutrConfig()),
        ):
            assert main(["configure"]) == 0

        assert mock_run_configure.call_args.kwargs["interactive"] is True

    def test_passes_explicit_flags_to_run_configure(self):
        mock_run_configure = MagicMock(
            return_value=TutrConfig(provider="openai", model="openai/gpt-4o")
        )
        with _configure_patches(
            run_configure=mock_run_configure,
            load_config=MagicMock(return_value=TutrConfig()),
        ):
            assert (
                main(
                    [
                        "configure",
                        "--provider",
                        "openai",
                        "--model",
                        "openai/gpt-4o",
                        "--show-explanation",
                    ]
                )
                == 0
            )

        kwargs = mock_run_configure.call_args.kwargs
        assert kwargs["provider"] == "openai"
        assert kwargs["model"] == "openai/gpt-4o"
        assert kwargs["show_explanation"] is True
        assert kwargs["interactive"] is False

    def test_passes_ollama_host_flags_to_run_configure(self):
        mock_run_configure = MagicMock(
            return_value=TutrConfig(provider="ollama", model="ollama/llama3")
        )
        with _configure_patches(run_configure=mock_run_configure):
            assert (
                main(["configure", "--provider", "ollama", "--ollama-host", "localhost:11434"]) == 0
            )

        kwargs = mock_run_configure.call_args.kwargs
        assert kwargs["ollama_host"] == "localhost:11434"
        assert kwargs["clear_ollama_host"] is False

    def test_passes_disable_update_check_flag_to_run_configure(self):
        mock_run_configure = MagicMock(
            return_value=TutrConfig(provider="openai", model="openai/gpt-4o")
        )
        with _configure_patches(
            run_configure=mock_run_configure,
            load_config=MagicMock(return_value=TutrConfig()),
        ):
            assert main(["configure", "--disable-update-check"]) == 0

        kwargs = mock_run_configure.call_args.kwargs
        assert kwargs["update_check_enabled"] is False

    def test_passes_no_execute_flag_to_run_configure(self):
        mock_run_configure = MagicMock(
            return_value=TutrConfig(provider="openai", model="openai/gpt-4o", no_execute=True)
        )
        with _configure_patches(
            run_configure=mock_run_configure,
            load_config=MagicMock(return_value=TutrConfig()),
        ):
            assert main(["configure", "--no-execute"]) == 0

        kwargs = mock_run_configure.call_args.kwargs
        assert kwargs["no_execute"] is True

    def test_returns_one_when_run_configure_raises_value_error(self):
        with _configure_patches(
            run_configure=MagicMock(side_effect=ValueError("invalid")),
            load_config=MagicMock(return_value=TutrConfig()),
        ):
            assert main(["configure", "--provider", "openai"]) == 1

    def test_conflicting_api_key_args_return_two(self):
        with _configure_patches(load_config=MagicMock(return_value=TutrConfig())):
            assert main(["configure", "--api-key", "x", "--clear-api-key"]) == 2

    def test_conflicting_ollama_host_args_return_two(self):
        with _configure_patches(load_config=MagicMock(return_value=TutrConfig())):
            assert main(["configure", "--ollama-host", "x", "--clear-ollama-host"]) == 2

    def test_api_key_flag_prints_security_warning(self, capsys):
        with _configure_patches(load_config=MagicMock(return_value=TutrConfig())):
            assert main(["configure", "--provider", "openai", "--api-key", "secret"]) == 0

        err = capsys.readouterr().err
        assert "--api-key may leak secrets via shell history and process lists" in err


class TestEntrypoint:
    def test_entrypoint_raises_system_exit(self):
        with patch("tutr.cli.app.main", return_value=0):
            with pytest.raises(SystemExit) as exc_info:
                with patch.object(sys, "argv", ["tutr", "git", "status"]):
                    entrypoint()

        assert exc_info.value.code == 0

    def test_entrypoint_exits_with_one_on_error(self):
        with patch("tutr.cli.app.main", return_value=1):
            with pytest.raises(SystemExit) as exc_info:
                with patch.object(sys, "argv", ["tutr", "git", "status"]):
                    entrypoint()

        assert exc_info.value.code == 1
