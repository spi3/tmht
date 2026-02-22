"""Configuration for tutr."""

import json
import logging
import os
import secrets
import stat
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
    "xai": {"env_key": "XAI_API_KEY", "label": "xAI"},
    "ollama": {"env_key": None, "label": "Ollama (local, no API key needed)"},
}


def load_config() -> TutrConfig:
    """Load config from file, with env var overrides."""
    raw_config: dict[str, Any] = {}

    _ensure_config_dir_permissions(create=False)

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                loaded = json.load(f)
        except json.JSONDecodeError as exc:
            log.warning(
                "invalid config JSON in %s (%s); falling back to defaults",
                CONFIG_FILE,
                exc,
            )
        else:
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
    _ensure_config_dir_permissions(create=True)
    # Write to a temp file opened as 0o600, then atomically replace.
    temp_file = CONFIG_DIR / f".{CONFIG_FILE.name}.{os.getpid()}.{secrets.token_hex(8)}.tmp"
    fd = os.open(temp_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(config.model_dump(exclude_none=True), f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, CONFIG_FILE)
    except Exception:
        temp_file.unlink(missing_ok=True)
        raise
    log.debug("saved config to %s", CONFIG_FILE)


def _ensure_config_dir_permissions(*, create: bool) -> None:
    """Ensure the config directory exists and is owner-only."""
    if create:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)

    if not CONFIG_DIR.exists():
        return

    current_mode = stat.S_IMODE(CONFIG_DIR.stat().st_mode)
    if current_mode != 0o700:
        CONFIG_DIR.chmod(0o700)
        log.warning(
            "updated config directory permissions for %s from %o to 700",
            CONFIG_DIR,
            current_mode,
        )


def needs_setup() -> bool:
    """Check if initial setup is needed."""
    if CONFIG_FILE.exists():
        return False
    # Any provider API key env var set means the user configured externally
    for info in PROVIDERS.values():
        if info["env_key"] and os.environ.get(info["env_key"]):
            return False
    return True
