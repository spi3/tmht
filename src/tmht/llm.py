"""LLM interaction for tmht."""

import json

import litellm
from pydantic import ValidationError

from tmht.config import get_model
from tmht.models import CommandResponse

# Suppress litellm's noisy logging
litellm.suppress_debug_info = True


def query_llm(messages: list[dict]) -> CommandResponse:
    """Send messages to the LLM and return a parsed CommandResponse."""
    response = litellm.completion(
        model=get_model(),
        messages=messages,
        temperature=0,
        max_tokens=256,
    )
    content = response.choices[0].message.content.strip()

    try:
        data = json.loads(content)
        return CommandResponse(**data)
    except (json.JSONDecodeError, ValidationError):
        # Fallback: treat entire response as the command
        return CommandResponse(command=content)
