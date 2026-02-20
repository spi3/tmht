"""Command-line interface for tmht."""

import argparse
import sys

from tmht import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tmht",
        description="tmht CLI tool",
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.parse_args(argv)

    print("Hello from tmht!")
    return 0


def entrypoint() -> None:
    raise SystemExit(main())
