"""Unit tests for tutr.models."""

import pytest
from pydantic import ValidationError

from tutr.models import CommandResponse


class TestCommandResponse:
    """Tests for CommandResponse model."""

    def test_valid_instantiation(self):
        """Test that CommandResponse can be instantiated with a valid command string."""
        response = CommandResponse(command="git status")
        assert response.command == "git status"

    def test_valid_instantiation_complex_command(self):
        """Test instantiation with a complex multi-part command."""
        cmd = "find . -name '*.py' -type f -exec grep -l 'test' {} \\;"
        response = CommandResponse(command=cmd)
        assert response.command == cmd

    def test_missing_command_field_raises_validation_error(self):
        """Test that missing command field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CommandResponse()
        errors = exc_info.value.errors()
        assert len(errors) > 0
        assert errors[0]["type"] == "missing"
        assert errors[0]["loc"] == ("command",)

    def test_wrong_type_for_command_raises_validation_error(self):
        """Test that non-string types for command field raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CommandResponse(command=123)
        errors = exc_info.value.errors()
        assert len(errors) > 0
        assert errors[0]["loc"] == ("command",)

    def test_wrong_type_list_raises_validation_error(self):
        """Test that list type for command raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CommandResponse(command=["git", "status"])
        errors = exc_info.value.errors()
        assert len(errors) > 0
        assert errors[0]["loc"] == ("command",)

    def test_wrong_type_dict_raises_validation_error(self):
        """Test that dict type for command raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CommandResponse(command={"cmd": "git status"})
        errors = exc_info.value.errors()
        assert len(errors) > 0
        assert errors[0]["loc"] == ("command",)

    def test_wrong_type_none_raises_validation_error(self):
        """Test that None value for command raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CommandResponse(command=None)
        errors = exc_info.value.errors()
        assert len(errors) > 0
        assert errors[0]["loc"] == ("command",)

    def test_empty_string_is_valid(self):
        """Test that empty string is a valid command value."""
        response = CommandResponse(command="")
        assert response.command == ""

    def test_command_with_whitespace_only(self):
        """Test that whitespace-only string is valid."""
        response = CommandResponse(command="   ")
        assert response.command == "   "

    def test_command_with_special_characters(self):
        """Test that command with special characters is valid."""
        response = CommandResponse(command="echo 'hello | world & test'")
        assert response.command == "echo 'hello | world & test'"

    def test_command_with_newlines(self):
        """Test that command with newlines is valid."""
        response = CommandResponse(command="echo test\necho test2")
        assert response.command == "echo test\necho test2"

    def test_model_serialization(self):
        """Test that CommandResponse can be serialized."""
        response = CommandResponse(command="ls -la")
        data = response.model_dump()
        assert data == {"command": "ls -la", "explanation": "", "source": None}

    def test_model_json_serialization(self):
        """Test that CommandResponse can be serialized to JSON."""
        response = CommandResponse(command="pwd")
        json_str = response.model_dump_json()
        assert "pwd" in json_str
        assert "command" in json_str

    def test_model_from_dict(self):
        """Test that CommandResponse can be instantiated from a dict."""
        data = {"command": "echo hello"}
        response = CommandResponse(**data)
        assert response.command == "echo hello"
