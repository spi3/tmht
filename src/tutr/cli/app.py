"""Top-level CLI router."""

import sys

from . import configure as configure_cmd
from . import query as query_cmd


def main(argv: list[str] | None = None) -> int:
    """Route to one-shot query mode or configure mode."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "configure":
        return configure_cmd.run(args[1:])
    return query_cmd.run(args)


def entrypoint() -> None:
    """Console script entrypoint."""
    raise SystemExit(main())
