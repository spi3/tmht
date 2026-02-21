"""Command-line interface for tutr."""

import argparse
import logging
import sys

from tutr import __version__
from tutr.config import load_config, needs_setup
from tutr.setup import run_setup
from tutr.tutr import run


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

    print(f"\n  {result.command}\n")
    if config.show_explanation:
        if result.explanation.strip():
            print(f"  {result.explanation}\n")
        if result.source and result.source.strip():
            print(f"  source: {result.source}\n")

    return 0


def entrypoint() -> None:
    raise SystemExit(main())
