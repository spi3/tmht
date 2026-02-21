"""Unit tests for tutr.setup."""

from unittest.mock import call, patch

import pytest

from tutr.config import TutrConfig
from tutr.setup import _prompt_choice, run_setup


# ---------------------------------------------------------------------------
# _prompt_choice
# ---------------------------------------------------------------------------


class TestPromptChoice:
    def test_valid_input_returns_value(self):
        with patch("builtins.input", return_value="2"), patch("builtins.print"):
            assert _prompt_choice(3) == 2

    def test_returns_lower_bound(self):
        with patch("builtins.input", return_value="1"), patch("builtins.print"):
            assert _prompt_choice(3) == 1

    def test_returns_upper_bound(self):
        with patch("builtins.input", return_value="3"), patch("builtins.print"):
            assert _prompt_choice(3) == 3

    def test_invalid_then_valid_retries(self):
        with patch("builtins.input", side_effect=["abc", "2"]), patch("builtins.print") as mock_print:
            result = _prompt_choice(3)
        assert result == 2
        # Error message printed at least once
        assert any("Please enter a number" in str(c) for c in mock_print.call_args_list)

    def test_out_of_range_low_retries(self):
        with patch("builtins.input", side_effect=["0", "1"]), patch("builtins.print") as mock_print:
            result = _prompt_choice(3)
        assert result == 1
        assert any("Please enter a number" in str(c) for c in mock_print.call_args_list)

    def test_out_of_range_high_retries(self):
        with patch("builtins.input", side_effect=["99", "2"]), patch("builtins.print") as mock_print:
            result = _prompt_choice(3)
        assert result == 2
        assert any("Please enter a number" in str(c) for c in mock_print.call_args_list)

    def test_eoferror_retries_then_succeeds(self):
        with patch("builtins.input", side_effect=[EOFError, "1"]), patch("builtins.print"):
            assert _prompt_choice(2) == 1

    def test_multiple_bad_inputs_then_valid(self):
        with patch("builtins.input", side_effect=["x", "0", EOFError, "3"]), patch("builtins.print"):
            assert _prompt_choice(3) == 3

    def test_max_val_one_accepts_only_1(self):
        with patch("builtins.input", side_effect=["2", "1"]), patch("builtins.print"):
            assert _prompt_choice(1) == 1

    def test_empty_string_retries(self):
        with patch("builtins.input", side_effect=["", "2"]), patch("builtins.print"):
            assert _prompt_choice(3) == 2


# ---------------------------------------------------------------------------
# run_setup
# ---------------------------------------------------------------------------


class TestRunSetupGeminiWithApiKey:
    """Selecting gemini (choice 1) with a valid API key saves correct config."""

    def test_saves_provider_model_and_api_key(self):
        # providers order: gemini=1, anthropic=2, openai=3, ollama=4
        # gemini models order: gemini-3-flash=1, gemini-2.0-flash=2, gemini-2.5-pro=3
        inputs = ["1", "1"]  # provider=gemini, model=gemini-3-flash-preview

        with (
            patch("builtins.input", side_effect=inputs),
            patch("builtins.print"),
            patch("getpass.getpass", return_value="my-api-key"),
            patch("tutr.setup.save_config") as mock_save,
        ):
            result = run_setup()

        mock_save.assert_called_once_with(
            TutrConfig(provider="gemini", model="gemini/gemini-3-flash-preview", api_key="my-api-key")
        )
        assert result == TutrConfig(provider="gemini", model="gemini/gemini-3-flash-preview", api_key="my-api-key")

    def test_selects_non_default_model(self):
        inputs = ["1", "2"]  # provider=gemini, model=gemini-2.0-flash

        with (
            patch("builtins.input", side_effect=inputs),
            patch("builtins.print"),
            patch("getpass.getpass", return_value="key-abc"),
            patch("tutr.setup.save_config") as mock_save,
        ):
            result = run_setup()

        mock_save.assert_called_once_with(TutrConfig(provider="gemini", model="gemini/gemini-2.0-flash", api_key="key-abc"))
        assert result.model == "gemini/gemini-2.0-flash"


class TestRunSetupOllamaSkipsApiKey:
    """Selecting ollama (choice 4) must not prompt for an API key."""

    def test_getpass_not_called_for_ollama(self):
        inputs = ["4", "1"]  # provider=ollama, model=llama3

        with (
            patch("builtins.input", side_effect=inputs),
            patch("builtins.print"),
            patch("getpass.getpass") as mock_getpass,
            patch("tutr.setup.save_config"),
        ):
            run_setup()

        mock_getpass.assert_not_called()

    def test_saved_config_has_no_api_key(self):
        inputs = ["4", "1"]

        with (
            patch("builtins.input", side_effect=inputs),
            patch("builtins.print"),
            patch("getpass.getpass"),
            patch("tutr.setup.save_config") as mock_save,
        ):
            result = run_setup()

        saved = mock_save.call_args[0][0]
        assert saved.api_key is None
        assert result.api_key is None

    def test_correct_provider_and_model_saved(self):
        inputs = ["4", "2"]  # provider=ollama, model=mistral

        with (
            patch("builtins.input", side_effect=inputs),
            patch("builtins.print"),
            patch("getpass.getpass"),
            patch("tutr.setup.save_config") as mock_save,
        ):
            run_setup()

        mock_save.assert_called_once_with(TutrConfig(provider="ollama", model="ollama/mistral"))


class TestRunSetupEmptyApiKey:
    """An empty API key must not be included in the saved config."""

    def test_empty_api_key_excluded_from_config(self):
        inputs = ["2", "1"]  # provider=anthropic, model=claude-haiku

        with (
            patch("builtins.input", side_effect=inputs),
            patch("builtins.print"),
            patch("getpass.getpass", return_value=""),
            patch("tutr.setup.save_config") as mock_save,
        ):
            result = run_setup()

        saved = mock_save.call_args[0][0]
        assert saved.api_key is None
        assert result.api_key is None

    def test_whitespace_only_api_key_excluded(self):
        """getpass returns whitespace; after strip() it is empty, so excluded."""
        inputs = ["2", "1"]

        with (
            patch("builtins.input", side_effect=inputs),
            patch("builtins.print"),
            patch("getpass.getpass", return_value="   "),
            patch("tutr.setup.save_config") as mock_save,
        ):
            result = run_setup()

        saved = mock_save.call_args[0][0]
        assert saved.api_key is None
        assert result.api_key is None

    def test_no_api_key_message_printed(self):
        """When API key is empty, a hint about setting the env var is printed."""
        inputs = ["3", "1"]  # provider=openai, model=gpt-4o-mini

        with (
            patch("builtins.input", side_effect=inputs),
            patch("builtins.print") as mock_print,
            patch("getpass.getpass", return_value=""),
            patch("tutr.setup.save_config"),
        ):
            run_setup()

        all_output = " ".join(str(c) for c in mock_print.call_args_list)
        assert "OPENAI_API_KEY" in all_output


class TestRunSetupSaveConfigAlwaysCalled:
    def test_save_config_called_exactly_once(self):
        inputs = ["1", "1"]

        with (
            patch("builtins.input", side_effect=inputs),
            patch("builtins.print"),
            patch("getpass.getpass", return_value="key"),
            patch("tutr.setup.save_config") as mock_save,
        ):
            run_setup()

        assert mock_save.call_count == 1

    def test_returned_config_matches_saved_config(self):
        inputs = ["3", "2"]  # provider=openai, model=gpt-4o

        with (
            patch("builtins.input", side_effect=inputs),
            patch("builtins.print"),
            patch("getpass.getpass", return_value="sk-test"),
            patch("tutr.setup.save_config") as mock_save,
        ):
            result = run_setup()

        assert result == mock_save.call_args[0][0]
