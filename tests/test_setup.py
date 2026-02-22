"""Unit tests for tutr.cli.wizard."""

from unittest.mock import patch

from tutr.cli.wizard import _normalize_ollama_host, _prompt_choice, run_configure, run_setup
from tutr.config import TutrConfig

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
        with (
            patch("builtins.input", side_effect=["abc", "2"]),
            patch("builtins.print") as mock_print,
        ):
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
        with (
            patch("builtins.input", side_effect=["99", "2"]),
            patch("builtins.print") as mock_print,
        ):
            result = _prompt_choice(3)
        assert result == 2
        assert any("Please enter a number" in str(c) for c in mock_print.call_args_list)

    def test_eoferror_retries_then_succeeds(self):
        with patch("builtins.input", side_effect=[EOFError, "1"]), patch("builtins.print"):
            assert _prompt_choice(2) == 1

    def test_multiple_bad_inputs_then_valid(self):
        with (
            patch("builtins.input", side_effect=["x", "0", EOFError, "3"]),
            patch("builtins.print"),
        ):
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
        # providers order: gemini=1, anthropic=2, openai=3, xai=4, ollama=5
        # gemini models order: gemini-3-flash=1, gemini-2.0-flash=2, gemini-2.5-pro=3
        inputs = ["1", "1", "n"]  # provider=gemini, model=gemini-3-flash-preview

        with (
            patch("builtins.input", side_effect=inputs),
            patch("builtins.print"),
            patch("getpass.getpass", return_value="my-api-key"),
            patch("tutr.cli.wizard.save_config") as mock_save,
        ):
            result = run_setup()

        mock_save.assert_called_once_with(
            TutrConfig(
                provider="gemini",
                model="gemini/gemini-3-flash-preview",
                api_key="my-api-key",
                show_explanation=False,
            )
        )
        assert result == TutrConfig(
            provider="gemini",
            model="gemini/gemini-3-flash-preview",
            api_key="my-api-key",
            show_explanation=False,
        )

    def test_selects_non_default_model(self):
        inputs = ["1", "2", "n"]  # provider=gemini, model=gemini-2.0-flash

        with (
            patch("builtins.input", side_effect=inputs),
            patch("builtins.print"),
            patch("getpass.getpass", return_value="key-abc"),
            patch("tutr.cli.wizard.save_config") as mock_save,
        ):
            result = run_setup()

        mock_save.assert_called_once_with(
            TutrConfig(
                provider="gemini",
                model="gemini/gemini-2.0-flash",
                api_key="key-abc",
                show_explanation=False,
            )
        )
        assert result.model == "gemini/gemini-2.0-flash"


class TestRunSetupOllamaSkipsApiKey:
    """Selecting ollama (choice 5) must not prompt for an API key."""

    def test_getpass_not_called_for_ollama(self):
        inputs = ["5", "", "1", "n"]  # provider=ollama, default host, model=llama3

        with (
            patch("builtins.input", side_effect=inputs),
            patch("builtins.print"),
            patch("getpass.getpass") as mock_getpass,
            patch("tutr.cli.wizard.save_config"),
        ):
            run_setup()

        mock_getpass.assert_not_called()

    def test_saved_config_has_no_api_key(self):
        inputs = ["5", "", "1", "n"]

        with (
            patch("builtins.input", side_effect=inputs),
            patch("builtins.print"),
            patch("getpass.getpass"),
            patch("tutr.cli.wizard.save_config") as mock_save,
        ):
            result = run_setup()

        saved = mock_save.call_args[0][0]
        assert saved.api_key is None
        assert result.api_key is None

    def test_correct_provider_and_model_saved(self):
        inputs = ["5", "", "2", "n"]  # provider=ollama, default host, model=mistral

        with (
            patch("builtins.input", side_effect=inputs),
            patch("builtins.print"),
            patch("getpass.getpass"),
            patch("tutr.cli.wizard.save_config") as mock_save,
        ):
            run_setup()

        mock_save.assert_called_once_with(
            TutrConfig(
                provider="ollama",
                model="ollama/mistral",
                ollama_host="http://localhost:11434",
                show_explanation=False,
            )
        )


class TestRunSetupEmptyApiKey:
    """An empty API key must not be included in the saved config."""

    def test_empty_api_key_excluded_from_config(self):
        inputs = ["2", "1", "n"]  # provider=anthropic, model=claude-haiku

        with (
            patch("builtins.input", side_effect=inputs),
            patch("builtins.print"),
            patch("getpass.getpass", return_value=""),
            patch("tutr.cli.wizard.save_config") as mock_save,
        ):
            result = run_setup()

        saved = mock_save.call_args[0][0]
        assert saved.api_key is None
        assert result.api_key is None

    def test_whitespace_only_api_key_excluded(self):
        """getpass returns whitespace; after strip() it is empty, so excluded."""
        inputs = ["2", "1", "n"]

        with (
            patch("builtins.input", side_effect=inputs),
            patch("builtins.print"),
            patch("getpass.getpass", return_value="   "),
            patch("tutr.cli.wizard.save_config") as mock_save,
        ):
            result = run_setup()

        saved = mock_save.call_args[0][0]
        assert saved.api_key is None
        assert result.api_key is None

    def test_no_api_key_message_printed(self):
        """When API key is empty, a hint about setting the env var is printed."""
        inputs = ["3", "1", "n"]  # provider=openai, model=gpt-4o-mini

        with (
            patch("builtins.input", side_effect=inputs),
            patch("builtins.print") as mock_print,
            patch("getpass.getpass", return_value=""),
            patch("tutr.cli.wizard.save_config"),
        ):
            run_setup()

        all_output = " ".join(str(c) for c in mock_print.call_args_list)
        assert "OPENAI_API_KEY" in all_output


class TestRunSetupXaiWithApiKey:
    def test_saves_provider_model_and_api_key(self):
        inputs = ["4", "1", "n"]  # provider=xai, model=grok-3-mini

        with (
            patch("builtins.input", side_effect=inputs),
            patch("builtins.print"),
            patch("getpass.getpass", return_value="xai-key"),
            patch("tutr.cli.wizard.save_config") as mock_save,
        ):
            result = run_setup()

        expected = TutrConfig(
            provider="xai",
            model="xai/grok-3-mini",
            api_key="xai-key",
            show_explanation=False,
        )
        mock_save.assert_called_once_with(expected)
        assert result == expected


class TestRunSetupSaveConfigAlwaysCalled:
    def test_save_config_called_exactly_once(self):
        inputs = ["1", "1", "n"]

        with (
            patch("builtins.input", side_effect=inputs),
            patch("builtins.print"),
            patch("getpass.getpass", return_value="key"),
            patch("tutr.cli.wizard.save_config") as mock_save,
        ):
            run_setup()

        assert mock_save.call_count == 1

    def test_returned_config_matches_saved_config(self):
        inputs = ["3", "2", "n"]  # provider=openai, model=gpt-4o

        with (
            patch("builtins.input", side_effect=inputs),
            patch("builtins.print"),
            patch("getpass.getpass", return_value="sk-test"),
            patch("tutr.cli.wizard.save_config") as mock_save,
        ):
            result = run_setup()

        assert result == mock_save.call_args[0][0]


class TestRunConfigureNonInteractive:
    def test_switch_provider_sets_recommended_model(self):
        config = TutrConfig(provider="gemini", model="gemini/gemini-3-flash-preview")

        with patch("tutr.cli.wizard.save_config"):
            updated = run_configure(config, provider="openai")

        assert updated.provider == "openai"
        assert updated.model == "openai/gpt-4o-mini"

    def test_model_infers_provider(self):
        config = TutrConfig(provider="gemini", model="gemini/gemini-3-flash-preview")

        with patch("tutr.cli.wizard.save_config"):
            updated = run_configure(config, model="anthropic/claude-sonnet-4-6")

        assert updated.provider == "anthropic"
        assert updated.model == "anthropic/claude-sonnet-4-6"

    def test_clear_api_key(self):
        config = TutrConfig(provider="openai", model="openai/gpt-4o", api_key="secret")

        with patch("tutr.cli.wizard.save_config"):
            updated = run_configure(config, clear_api_key=True)

        assert updated.api_key is None

    def test_ollama_provider_defaults_host(self):
        config = TutrConfig(provider="gemini", model="gemini/gemini-3-flash-preview")

        with patch("tutr.cli.wizard.save_config"):
            updated = run_configure(config, provider="ollama")

        assert updated.ollama_host == "http://localhost:11434"

    def test_ollama_host_normalized_when_set(self):
        config = TutrConfig(provider="ollama", model="ollama/llama3")

        with patch("tutr.cli.wizard.save_config"):
            updated = run_configure(config, ollama_host="localhost:11434/")

        assert updated.ollama_host == "http://localhost:11434"

    def test_no_execute_toggle_is_applied(self):
        config = TutrConfig(provider="openai", model="openai/gpt-4o", no_execute=None)

        with patch("tutr.cli.wizard.save_config"):
            updated = run_configure(config, no_execute=True)

        assert updated.no_execute is True


class TestNormalizeOllamaHost:
    def test_empty_string_uses_default_host(self):
        assert _normalize_ollama_host("") == "http://localhost:11434"

    def test_existing_scheme_is_preserved(self):
        assert (
            _normalize_ollama_host("https://ollama.internal:8443") == "https://ollama.internal:8443"
        )

    def test_trailing_slash_is_removed(self):
        assert _normalize_ollama_host("localhost:11434/") == "http://localhost:11434"
