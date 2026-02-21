"""Provider metadata model for tutr."""

from typing import TypedDict


class ProviderInfo(TypedDict):
    env_key: str | None
    label: str
