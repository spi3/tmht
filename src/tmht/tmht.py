"""Core logic for tmht."""

import logging
import shutil

from tmht.context import gather_context, get_system_info
from tmht.llm import query_llm
from tmht.models import CommandResponse
from tmht.prompt import build_messages

log = logging.getLogger("tmht")


def parse_input(words: list[str]) -> tuple[str | None, str]:
    """Split raw input words into an optional command and a query string."""
    first, rest = words[0], words[1:]
    if shutil.which(first):
        cmd = first
        query = " ".join(rest) if rest else ""
    else:
        cmd = None
        query = " ".join(words)
    log.debug("cmd=%s query=%r", cmd, query)
    return cmd, query


def run(words: list[str], config: dict) -> CommandResponse:
    """Run the core tmht pipeline: parse input, gather context, query LLM."""
    cmd, query = parse_input(words)
    context = gather_context(cmd)
    system_info = get_system_info()
    messages = build_messages(cmd, query, context, system_info)
    return query_llm(messages, config)
