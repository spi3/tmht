"""Command-line interface for tmht."""

import argparse
import sys

from tmht import __version__
from tmht.context import gather_context
from tmht.llm import query_llm
from tmht.prompt import build_messages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tmht",
        description="Tell Me How To — AI-powered terminal command assistant",
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "command",
        help="The terminal command to get help with (e.g., git, sed, curl)",
    )
    parser.add_argument(
        "query",
        nargs="+",
        help="What you want to do, in natural language",
    )

    args = parser.parse_args(argv)

    cmd = args.command
    query = " ".join(args.query)

    context = gather_context(cmd)
    messages = build_messages(cmd, query, context)

    try:
        result = query_llm(messages)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"\n  {result.command}\n")

    return 0


def entrypoint() -> None:
    raise SystemExit(main())
