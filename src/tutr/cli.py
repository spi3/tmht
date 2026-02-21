"""Command-line interface for tutr."""

import argparse
import logging
import os
import sys

from tutr import __version__
from tutr.config import load_config, needs_setup
from tutr.constants import BOLD, CYAN, RESET
from tutr.setup import run_setup
from tutr.tutr import run
from tutr.update_check import notify_if_update_available


def _supports_color() -> bool:
    """Return whether ANSI color output should be used."""
    if os.getenv("NO_COLOR") is not None:
        return False
    if os.getenv("TERM", "").lower() == "dumb":
        return False
    return sys.stdout.isatty()


def _format_suggested_command(command: str) -> str:
    """Return a shell-like prompt line for the suggested command."""
    if _supports_color():
        return f"{BOLD}{CYAN}$ {command}{RESET}"
    return f"$ {command}"


def main(argv: list[str] | None = None) -> int:
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
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
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

    args = parser.parse_args(argv)
    notify_if_update_available(__version__)

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
        result = run(args.words, config)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"\n  {_format_suggested_command(result.command)}\n")
    if config.show_explanation:
        if result.explanation.strip():
            print(f"  {result.explanation}\n")
        if result.source and result.source.strip():
            print(f"  source: {result.source}\n")

    return 0


def entrypoint() -> None:
    raise SystemExit(main())
