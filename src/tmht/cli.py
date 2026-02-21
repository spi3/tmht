"""Command-line interface for tmht."""

import argparse
import logging
import shutil
import sys

from tmht import __version__
from tmht.config import load_config, needs_setup
from tmht.context import gather_context, get_system_info
from tmht.llm import query_llm
from tmht.prompt import build_messages
from tmht.setup import run_setup

log = logging.getLogger("tmht")


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
        "-d", "--debug",
        action="store_true",
        help="Enable debug logging",
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

    first, rest = args.words[0], args.words[1:]
    if shutil.which(first):
        cmd = first
        query = " ".join(rest) if rest else ""
    else:
        cmd = None
        query = " ".join(args.words)
    log.debug("cmd=%s query=%r", cmd, query)

    context = gather_context(cmd)
    system_info = get_system_info()
    messages = build_messages(cmd, query, context, system_info)

    try:
        result = query_llm(messages, config)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"\n  {result.command}\n")

    return 0


def entrypoint() -> None:
    raise SystemExit(main())
