"""Prompt construction for tmht."""

SYSTEM_PROMPT = """\
You are a terminal command assistant. Your job is to generate the exact terminal \
command that accomplishes what the user describes.

Rules:
- Return ONLY valid JSON matching this schema: {"command": "<the command>"}
- The command must be a single, copy-pasteable terminal command
- Use pipes, &&, or ; to chain commands if needed
- Do not wrap the command in backticks or code blocks
- Keep the explanation to one sentence
- If the request is ambiguous, make reasonable assumptions and note them in the explanation
"""


def build_messages(
    cmd: str | None, query: str, context: str, system_info: str = ""
) -> list[dict]:
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
