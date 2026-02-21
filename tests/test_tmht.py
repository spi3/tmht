"""Unit tests for tmht.tmht (core logic)."""

from unittest.mock import MagicMock, patch

from tmht.tmht import parse_input, run


def _make_llm_result(command="git checkout -b testing"):
    result = MagicMock()
    result.command = command
    return result


def _core_patches(**overrides):
    """Return a patch.multiple context for tmht.tmht internals."""
    defaults = dict(
        gather_context=MagicMock(return_value="ctx"),
        get_system_info=MagicMock(return_value="OS: Linux 6.1.0\nShell: /bin/bash"),
        build_messages=MagicMock(return_value=[]),
        query_llm=MagicMock(return_value=_make_llm_result()),
    )
    defaults.update(overrides)
    return patch.multiple("tmht.tmht", **defaults)


# ---------------------------------------------------------------------------
# parse_input()
# ---------------------------------------------------------------------------


class TestParseInput:
    def test_known_command_splits_cmd_and_query(self):
        with patch("shutil.which", return_value="/usr/bin/git"):
            cmd, query = parse_input(["git", "create", "a", "branch"])
        assert cmd == "git"
        assert query == "create a branch"

    def test_unknown_command_folds_all_into_query(self):
        with patch("shutil.which", return_value=None):
            cmd, query = parse_input(["how", "do", "I", "list", "files"])
        assert cmd is None
        assert query == "how do I list files"

    def test_known_command_with_no_rest(self):
        with patch("shutil.which", return_value="/usr/bin/ls"):
            cmd, query = parse_input(["ls"])
        assert cmd == "ls"
        assert query == ""

    def test_multi_word_query_joined_with_spaces(self):
        with patch("shutil.which", return_value="/usr/bin/git"):
            cmd, query = parse_input(["git", "create", "and", "switch", "to", "new", "branch"])
        assert query == "create and switch to new branch"


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------


class TestRun:
    def test_returns_llm_result(self):
        expected = _make_llm_result("ls -la")
        with _core_patches(query_llm=MagicMock(return_value=expected)):
            with patch("shutil.which", return_value="/usr/bin/ls"):
                result = run(["ls", "list files"], {})
        assert result.command == "ls -la"

    def test_gathers_context_for_known_command(self):
        mock_gather = MagicMock(return_value="man page")
        with _core_patches(gather_context=mock_gather):
            with patch("shutil.which", return_value="/usr/bin/git"):
                run(["git", "status"], {})
        mock_gather.assert_called_once_with("git")

    def test_gathers_context_with_none_for_unknown_command(self):
        mock_gather = MagicMock(return_value="")
        with _core_patches(gather_context=mock_gather):
            with patch("shutil.which", return_value=None):
                run(["how", "do", "I", "list", "files"], {})
        mock_gather.assert_called_once_with(None)

    def test_passes_query_to_build_messages(self):
        mock_build = MagicMock(return_value=[])
        with _core_patches(build_messages=mock_build):
            with patch("shutil.which", return_value="/usr/bin/git"):
                run(["git", "create", "a", "branch"], {})
        query_arg = mock_build.call_args[0][1]
        assert query_arg == "create a branch"

    def test_passes_config_to_query_llm(self):
        mock_llm = MagicMock(return_value=_make_llm_result())
        config = {"model": "test/model", "api_key": "key123"}
        with _core_patches(query_llm=mock_llm):
            with patch("shutil.which", return_value="/usr/bin/git"):
                run(["git", "status"], config)
        config_arg = mock_llm.call_args[0][1]
        assert config_arg == config
