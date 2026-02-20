"""Configuration for tmht."""

import os

DEFAULT_MODEL = "gemini/gemini-3-flash-preview"


def get_model() -> str:
    """Return the LLM model identifier from env or default."""
    return os.environ.get("TMHT_MODEL", DEFAULT_MODEL)
