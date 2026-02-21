"""LLM interaction for tutr."""

import json
import logging

import litellm

log = logging.getLogger(__name__)
from pydantic import ValidationError

from tutr.config import DEFAULT_MODEL
from tutr.models import CommandResponse
from tutr.wait_indicator import build_llm_wait_indicator

# Suppress litellm's noisy logging
litellm.suppress_debug_info = True


def query_llm(messages: list[dict], config: dict | None = None) -> CommandResponse:
    """Send messages to the LLM and return a parsed CommandResponse."""
    config = config or {}
    model = config.get("model", DEFAULT_MODEL)
    api_key = config.get("api_key")
    log.debug("model=%s", model)
    log.debug("messages=%s", json.dumps(messages, indent=2))

    kwargs: dict = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": 256,
    }
    if api_key:
        kwargs["api_key"] = api_key

    indicator = build_llm_wait_indicator()
    indicator.start()
    try:
        response = litellm.completion(**kwargs)
    finally:
        indicator.stop()

    content = response.choices[0].message.content.strip()
    log.debug("raw response: %s", content)

    try:
        data = json.loads(content)
        return CommandResponse(**data)
    except (json.JSONDecodeError, ValidationError) as e:
        log.debug("JSON parse failed (%s), using raw content as command", e)
        return CommandResponse(command=content)
