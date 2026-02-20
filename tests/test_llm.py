"""Unit tests for tmht.llm."""

import json
from unittest.mock import MagicMock, patch

import pytest

from tmht.config import DEFAULT_MODEL
from tmht.llm import query_llm
from tmht.models import CommandResponse


def make_mock_response(content: str) -> MagicMock:
    """Build a mock object that mimics litellm's completion return structure."""
    message = MagicMock()
    message.content = content

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]

    return response


MESSAGES = [{"role": "user", "content": "how do I list files?"}]


class TestQueryLlmValidResponse:
    """Tests for valid JSON responses from the LLM."""

    def test_valid_json_parsed_into_command_response(self):
        """Valid JSON with 'command' field is parsed into CommandResponse."""
        payload = json.dumps({"command": "ls -la"})
        with patch("tmht.llm.litellm.completion", return_value=make_mock_response(payload)):
            result = query_llm(MESSAGES)
        assert isinstance(result, CommandResponse)
        assert result.command == "ls -la"

    def test_valid_json_with_extra_whitespace(self):
        """Valid JSON padded with whitespace is stripped and parsed correctly."""
        payload = "  " + json.dumps({"command": "pwd"}) + "\n"
        with patch("tmht.llm.litellm.completion", return_value=make_mock_response(payload)):
            result = query_llm(MESSAGES)
        assert result.command == "pwd"


class TestQueryLlmFallback:
    """Tests for non-JSON and invalid JSON responses falling back to raw content."""

    def test_non_json_response_uses_raw_content(self):
        """A plain-text (non-JSON) response is used as the command directly."""
        raw = "ls -la"
        with patch("tmht.llm.litellm.completion", return_value=make_mock_response(raw)):
            result = query_llm(MESSAGES)
        assert isinstance(result, CommandResponse)
        assert result.command == raw

    def test_invalid_json_uses_raw_content(self):
        """Malformed JSON falls back to raw content as command."""
        raw = "{not valid json"
        with patch("tmht.llm.litellm.completion", return_value=make_mock_response(raw)):
            result = query_llm(MESSAGES)
        assert result.command == raw

    def test_valid_json_wrong_fields_uses_raw_content(self):
        """Valid JSON that fails CommandResponse validation falls back to raw content."""
        # 'cmd' is not a recognised field; 'command' is required so validation fails
        payload = json.dumps({"cmd": "ls -la"})
        with patch("tmht.llm.litellm.completion", return_value=make_mock_response(payload)):
            result = query_llm(MESSAGES)
        assert result.command == payload

    def test_json_null_command_uses_raw_content(self):
        """JSON with command=null fails pydantic validation and falls back to raw."""
        payload = json.dumps({"command": None})
        with patch("tmht.llm.litellm.completion", return_value=make_mock_response(payload)):
            result = query_llm(MESSAGES)
        assert result.command == payload


class TestQueryLlmConfig:
    """Tests for config handling: model, api_key, and defaults."""

    def test_none_config_uses_default_model(self):
        """Passing config=None uses DEFAULT_MODEL."""
        payload = json.dumps({"command": "echo hi"})
        with patch("tmht.llm.litellm.completion", return_value=make_mock_response(payload)) as mock_completion:
            query_llm(MESSAGES, config=None)
        call_kwargs = mock_completion.call_args.kwargs
        assert call_kwargs["model"] == DEFAULT_MODEL

    def test_empty_config_uses_default_model(self):
        """Passing an empty dict uses DEFAULT_MODEL."""
        payload = json.dumps({"command": "echo hi"})
        with patch("tmht.llm.litellm.completion", return_value=make_mock_response(payload)) as mock_completion:
            query_llm(MESSAGES, config={})
        call_kwargs = mock_completion.call_args.kwargs
        assert call_kwargs["model"] == DEFAULT_MODEL

    def test_config_model_overrides_default(self):
        """A model specified in config overrides DEFAULT_MODEL."""
        payload = json.dumps({"command": "echo hi"})
        custom_model = "anthropic/claude-3-haiku"
        with patch("tmht.llm.litellm.completion", return_value=make_mock_response(payload)) as mock_completion:
            query_llm(MESSAGES, config={"model": custom_model})
        call_kwargs = mock_completion.call_args.kwargs
        assert call_kwargs["model"] == custom_model

    def test_config_api_key_passed_through(self):
        """An api_key in config is forwarded to litellm.completion."""
        payload = json.dumps({"command": "echo hi"})
        with patch("tmht.llm.litellm.completion", return_value=make_mock_response(payload)) as mock_completion:
            query_llm(MESSAGES, config={"api_key": "sk-test-123"})
        call_kwargs = mock_completion.call_args.kwargs
        assert call_kwargs["api_key"] == "sk-test-123"

    def test_no_api_key_in_config_omits_kwarg(self):
        """When api_key is absent from config, it is not forwarded to litellm."""
        payload = json.dumps({"command": "echo hi"})
        with patch("tmht.llm.litellm.completion", return_value=make_mock_response(payload)) as mock_completion:
            query_llm(MESSAGES, config={})
        call_kwargs = mock_completion.call_args.kwargs
        assert "api_key" not in call_kwargs

    def test_fixed_temperature_and_max_tokens(self):
        """temperature=0 and max_tokens=256 are always sent regardless of config."""
        payload = json.dumps({"command": "echo hi"})
        with patch("tmht.llm.litellm.completion", return_value=make_mock_response(payload)) as mock_completion:
            query_llm(MESSAGES, config={})
        call_kwargs = mock_completion.call_args.kwargs
        assert call_kwargs["temperature"] == 0
        assert call_kwargs["max_tokens"] == 256


class TestQueryLlmExceptions:
    """Tests for exception propagation from litellm."""

    def test_litellm_exception_propagates(self):
        """An exception raised by litellm.completion is not swallowed."""
        with patch("tmht.llm.litellm.completion", side_effect=RuntimeError("API error")):
            with pytest.raises(RuntimeError, match="API error"):
                query_llm(MESSAGES)

    def test_litellm_connection_error_propagates(self):
        """A network-level exception propagates unchanged."""
        with patch("tmht.llm.litellm.completion", side_effect=ConnectionError("timeout")):
            with pytest.raises(ConnectionError):
                query_llm(MESSAGES)
