"""Core logic for tutr."""

import logging
import shutil

from tutr.config import TutrConfig
from tutr.context import gather_context, get_system_info
from tutr.llm import query_llm
from tutr.models import CommandResponse
from tutr.prompt import build_messages

log = logging.getLogger("tutr")


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


def run_query(query: str, config: TutrConfig, cmd: str | None = None) -> CommandResponse:
    """Run the core tutr pipeline for a pre-parsed query string."""
    context = gather_context(cmd)
    system_info = get_system_info()
    messages = build_messages(cmd, query, context, system_info)
    return query_llm(messages, config)


def run(words: list[str], config: TutrConfig) -> CommandResponse:
    """Run the core tutr pipeline: parse input, gather context, query LLM."""
    cmd, query = parse_input(words)
    return run_query(query, config, cmd=cmd)
