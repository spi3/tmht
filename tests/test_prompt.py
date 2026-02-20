"""Unit tests for prompt module."""

import pytest

from tmht.prompt import SYSTEM_PROMPT, build_messages


class TestBuildMessages:
    """Tests for build_messages function."""

    def test_returns_list_of_dicts(self):
        """Test that build_messages returns a list of dictionaries."""
        result = build_messages("git", "create a branch", "context here")
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, dict) for item in result)

    def test_returns_correct_structure(self):
        """Test that build_messages returns the expected message structure."""
        result = build_messages("git", "create a branch", "context here")

        # Check system message
        assert result[0]["role"] == "system"
        assert "content" in result[0]

        # Check user message
        assert result[1]["role"] == "user"
        assert "content" in result[1]

    def test_system_message_contains_system_prompt(self):
        """Test that system message contains SYSTEM_PROMPT."""
        result = build_messages("git", "create a branch", "context here")
        assert result[0]["content"] == SYSTEM_PROMPT

    def test_user_message_contains_command(self):
        """Test that user message contains the command."""
        cmd = "git"
        result = build_messages(cmd, "create a branch", "context here")
        assert f"Command: {cmd}" in result[1]["content"]

    def test_user_message_contains_query(self):
        """Test that user message contains the query."""
        query = "create a new branch called main"
        result = build_messages("git", query, "context here")
        assert f"What I want to do: {query}" in result[1]["content"]

    def test_user_message_contains_context(self):
        """Test that user message contains the context."""
        context = "some documentation about git"
        result = build_messages("git", "create a branch", context)
        assert f"Context:\n{context}" in result[1]["content"]

    def test_empty_command_string(self):
        """Test handling of empty command string."""
        result = build_messages("", "create a branch", "context")
        assert len(result) == 2
        assert "Command: " in result[1]["content"]

    def test_empty_query_string(self):
        """Test handling of empty query string."""
        result = build_messages("git", "", "context")
        assert len(result) == 2
        assert "What I want to do: " in result[1]["content"]

    def test_empty_context_string(self):
        """Test handling of empty context string."""
        result = build_messages("git", "create a branch", "")
        assert len(result) == 2
        assert "Context:\n" in result[1]["content"]

    def test_all_empty_strings(self):
        """Test handling of all empty strings."""
        result = build_messages("", "", "")
        assert len(result) == 2
        assert result[0]["content"] == SYSTEM_PROMPT
        assert "Command: " in result[1]["content"]
        assert "Context:\n" in result[1]["content"]
        assert "What I want to do: " in result[1]["content"]

    def test_multiline_context(self):
        """Test handling of multiline context."""
        context = "line 1\nline 2\nline 3"
        result = build_messages("git", "query", context)
        assert context in result[1]["content"]

    def test_special_characters_in_inputs(self):
        """Test handling of special characters in inputs."""
        cmd = "git && echo 'test'"
        query = "run command with special chars: $VAR && |"
        context = "context with 'quotes' and \"double quotes\" and ${variables}"
        result = build_messages(cmd, query, context)

        assert cmd in result[1]["content"]
        assert query in result[1]["content"]
        assert context in result[1]["content"]

    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        cmd = "grep"
        query = "find emoji 😀 and accents café"
        context = "context with unicode: 中文 العربية"
        result = build_messages(cmd, query, context)

        assert cmd in result[1]["content"]
        assert query in result[1]["content"]
        assert context in result[1]["content"]

    def test_very_long_inputs(self):
        """Test handling of very long input strings."""
        long_cmd = "x" * 1000
        long_query = "y" * 2000
        long_context = "z" * 5000
        result = build_messages(long_cmd, long_query, long_context)

        assert len(result) == 2
        assert long_cmd in result[1]["content"]
        assert long_query in result[1]["content"]
        assert long_context in result[1]["content"]

    def test_message_order(self):
        """Test that messages are in correct order (system first, user second)."""
        result = build_messages("git", "query", "context")
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"

    def test_user_message_format(self):
        """Test that user message has correct formatting with proper newlines."""
        cmd = "git"
        query = "create branch"
        context = "git docs"
        result = build_messages(cmd, query, context)
        user_content = result[1]["content"]

        # Verify the structure matches the expected format
        expected_format = f"Command: {cmd}\n\nContext:\n{context}\n\nWhat I want to do: {query}"
        assert user_content == expected_format

    def test_none_command_omits_command_and_context(self):
        """When cmd is None, user message contains only the query."""
        result = build_messages(None, "how do I list files", "")
        user_content = result[1]["content"]
        assert user_content == "What I want to do: how do I list files"
        assert "Command:" not in user_content
        assert "Context:" not in user_content

    def test_none_command_returns_valid_structure(self):
        """When cmd is None, the message list is still well-formed."""
        result = build_messages(None, "show disk usage", "")
        assert len(result) == 2
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"


class TestSystemPrompt:
    """Tests for SYSTEM_PROMPT constant."""

    def test_system_prompt_is_string(self):
        """Test that SYSTEM_PROMPT is a string."""
        assert isinstance(SYSTEM_PROMPT, str)

    def test_system_prompt_is_not_empty(self):
        """Test that SYSTEM_PROMPT is not empty."""
        assert len(SYSTEM_PROMPT) > 0

    def test_system_prompt_contains_instructions(self):
        """Test that SYSTEM_PROMPT contains key instructions."""
        assert "terminal command assistant" in SYSTEM_PROMPT
        assert "JSON" in SYSTEM_PROMPT
        assert "command" in SYSTEM_PROMPT
