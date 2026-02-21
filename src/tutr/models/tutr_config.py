"""Configuration model for tutr."""

from pydantic import BaseModel


DEFAULT_MODEL = "gemini/gemini-3-flash-preview"


class TutrConfig(BaseModel):
    """Runtime configuration for tutr."""

    provider: str | None = None
    model: str = DEFAULT_MODEL
    api_key: str | None = None
    show_explanation: bool | None = None
