"""Configuration model for tutr."""

from pydantic import BaseModel

DEFAULT_MODEL = "gemini/gemini-3-flash-preview"
DEFAULT_OLLAMA_HOST = "http://localhost:11434"


class TutrConfig(BaseModel):
    """Runtime configuration for tutr."""

    provider: str | None = None
    model: str = DEFAULT_MODEL
    api_key: str | None = None
    ollama_host: str | None = None
    show_explanation: bool | None = None
    update_check_enabled: bool = True
    no_execute: bool | None = None
