"""Configuration for tmht."""

import json
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".tmht"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_MODEL = "gemini/gemini-3-flash-preview"

PROVIDERS = {
    "gemini": {"env_key": "GEMINI_API_KEY", "label": "Gemini"},
    "anthropic": {"env_key": "ANTHROPIC_API_KEY", "label": "Anthropic"},
    "openai": {"env_key": "OPENAI_API_KEY", "label": "OpenAI"},
    "ollama": {"env_key": None, "label": "Ollama (local, no API key needed)"},
}


def load_config() -> dict:
    """Load config from file, with env var overrides."""
    config = {}

    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            config = json.load(f)
        log.debug("loaded config from %s", CONFIG_FILE)

    # Env var overrides
    if model := os.environ.get("TMHT_MODEL"):
        config["model"] = model

    provider = config.get("provider")
    if provider and provider in PROVIDERS:
        env_key = PROVIDERS[provider]["env_key"]
        if env_key and (api_key := os.environ.get(env_key)):
            config["api_key"] = api_key

    return config


def save_config(config: dict) -> None:
    """Save config to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
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
