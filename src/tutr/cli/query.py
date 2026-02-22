"""One-shot query CLI implementation."""

import argparse
import logging
import sys

from tutr import __version__
from tutr.cli.shared import format_suggested_command
from tutr.cli.wizard import run_setup
from tutr.config import load_config, needs_setup
from tutr.tutr import run as query_llm
from tutr.update_check import notify_if_update_available_async


def build_parser() -> argparse.ArgumentParser:
    """Build parser for one-shot query mode."""
    parser = argparse.ArgumentParser(
        prog="tutr",
        description="Tell Me How To — AI-powered terminal command assistant",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "-e",
        "--explain",
        action="store_true",
        help="Show the LLM explanation for generated commands",
    )
    parser.add_argument(
        "words",
        nargs="+",
        metavar="command/query",
        help="A command followed by a query, or just a natural-language query",
    )
    return parser


def run(argv: list[str]) -> int:
    """Execute one-shot query mode."""
    parser = build_parser()
    args = parser.parse_args(argv)

    notify_if_update_available_async(__version__)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(name)s %(levelname)s: %(message)s",
    )

    if needs_setup():
        config = run_setup()
    else:
        config = load_config()
    if args.explain:
        config.show_explanation = True

    try:
        result = query_llm(args.words, config)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"\n  {format_suggested_command(result.command)}\n")
    if config.show_explanation:
        if result.explanation.strip():
            print(f"  {result.explanation}\n")
        if result.source and result.source.strip():
            print(f"  source: {result.source}\n")

    return 0
