"""Response models for tutr."""

from pydantic import BaseModel, Field


class CommandResponse(BaseModel):
    command: str = Field(
        description=(
            "The terminal command to execute. "
            "The command must be a single, copy-pasteable terminal command. "
            "Use pipes, &&, or ; to chain commands if needed. "
            "Do not wrap the command in backticks or code blocks. "
        )
    )
    explanation: str = Field(
        default="",
        description=(
            "Brief explanation of what the command does. "
            "Keep the explanation to one sentence. "
            "If the request is ambiguous, make reasonable assumptions and note them in the explanation"
        ),
    )
    source: str | None = Field(
        default=None,
        description="Optional source of the command, e.g. 'man <cmd>' or '<cmd> --help'",
    )
