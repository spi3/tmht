"""Configuration for tutr."""

import json
import logging
import os
from pathlib import Path
from typing import Any

from tutr.models import DEFAULT_MODEL as MODEL_DEFAULT_MODEL
from tutr.models import DEFAULT_OLLAMA_HOST as MODEL_DEFAULT_OLLAMA_HOST
from tutr.models import ProviderInfo, TutrConfig

log = logging.getLogger(__name__)

__all__ = [
    "CONFIG_DIR",
    "CONFIG_FILE",
    "DEFAULT_MODEL",
    "DEFAULT_OLLAMA_HOST",
    "PROVIDERS",
    "TutrConfig",
    "load_config",
    "save_config",
    "needs_setup",
]

CONFIG_DIR = Path.home() / ".tutr"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_MODEL = MODEL_DEFAULT_MODEL
DEFAULT_OLLAMA_HOST = MODEL_DEFAULT_OLLAMA_HOST

PROVIDERS: dict[str, ProviderInfo] = {
    "gemini": {"env_key": "GEMINI_API_KEY", "label": "Gemini"},
    "anthropic": {"env_key": "ANTHROPIC_API_KEY", "label": "Anthropic"},
    "openai": {"env_key": "OPENAI_API_KEY", "label": "OpenAI"},
    "ollama": {"env_key": None, "label": "Ollama (local, no API key needed)"},
}


def load_config() -> TutrConfig:
    """Load config from file, with env var overrides."""
    raw_config: dict[str, Any] = {}

    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            raw_config = loaded
        log.debug("loaded config from %s", CONFIG_FILE)

    config = TutrConfig.model_validate(raw_config)

    # Env var overrides
    if model := os.environ.get("TUTR_MODEL"):
        config.model = model

    provider = config.provider
    if provider and provider in PROVIDERS:
        env_key = PROVIDERS[provider]["env_key"]
        if env_key and (api_key := os.environ.get(env_key)):
            config.api_key = api_key
        if provider == "ollama":
            if ollama_host := os.environ.get("OLLAMA_HOST"):
                config.ollama_host = ollama_host
            elif not config.ollama_host:
                config.ollama_host = DEFAULT_OLLAMA_HOST

    return config


def save_config(config: TutrConfig) -> None:
    """Save config to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config.model_dump(exclude_none=True), f, indent=2)
    # Restrict permissions — file contains API key
    CONFIG_FILE.chmod(0o600)
    log.debug("saved config to %s", CONFIG_FILE)


def needs_setup() -> bool:
    """Check if initial setup is needed."""
    if CONFIG_FILE.exists():
        return False
    # Any provider API key env var set means the user configured externally
    for info in PROVIDERS.values():
        if info["env_key"] and os.environ.get(info["env_key"]):
            return False
    return True
