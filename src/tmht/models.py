"""Response models for tmht."""

from pydantic import BaseModel, Field


class CommandResponse(BaseModel):
    command: str = Field(description="The terminal command to execute")
