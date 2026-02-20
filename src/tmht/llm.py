"""LLM interaction for tmht."""

import json
import logging

import litellm

log = logging.getLogger(__name__)
from pydantic import ValidationError

from tmht.config import get_model
from tmht.models import CommandResponse

# Suppress litellm's noisy logging
litellm.suppress_debug_info = True


def query_llm(messages: list[dict]) -> CommandResponse:
    """Send messages to the LLM and return a parsed CommandResponse."""
    model = get_model()
    log.debug("model=%s", model)
    log.debug("messages=%s", json.dumps(messages, indent=2))
    response = litellm.completion(
        model=model,
        messages=messages,
        temperature=0,
        max_tokens=256,
    )
    content = response.choices[0].message.content.strip()
    log.debug("raw response: %s", content)

    try:
        data = json.loads(content)
        return CommandResponse(**data)
    except (json.JSONDecodeError, ValidationError) as e:
        log.debug("JSON parse failed (%s), using raw content as command", e)
        return CommandResponse(command=content)
