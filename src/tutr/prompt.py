"""Prompt construction for tutr."""

import json

from tutr.models import CommandResponse


SYSTEM_PROMPT = f"""\
You are a terminal command assistant. Your job is to generate the exact terminal \
command that accomplishes what the user describes.

<critical>
Return **ONLY** valid JSON matching this schema: 

{json.dumps(CommandResponse.model_json_schema())}

</critical>
"""


def build_messages(cmd: str | None, query: str, context: str, system_info: str = "") -> list[dict]:
    """Build the message list for the LLM call."""
    parts: list[str] = []

    if system_info:
        parts.append(f"System:\n{system_info}")

    if cmd is not None:
        parts.append(f"Command: {cmd}")
        parts.append(f"Context:\n{context}")

    parts.append(f"What I want to do: {query}")

    user_content = "\n\n".join(parts)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
