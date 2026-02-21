"""Model package for tutr."""

from tutr.models.command_response import CommandResponse
from tutr.models.provider_info import ProviderInfo
from tutr.models.shell_launch_config import ShellLaunchConfig
from tutr.models.tutr_config import DEFAULT_MODEL, DEFAULT_OLLAMA_HOST, TutrConfig

__all__ = [
    "CommandResponse",
    "DEFAULT_MODEL",
    "DEFAULT_OLLAMA_HOST",
    "ProviderInfo",
    "ShellLaunchConfig",
    "TutrConfig",
]
