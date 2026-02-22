"""`tutr configure` command implementation."""

import argparse
import logging
import sys

from tutr import __version__
from tutr.cli.wizard import run_configure
from tutr.config import CONFIG_FILE, PROVIDERS, TutrConfig, load_config, needs_setup
from tutr.update_check import notify_if_update_available_async


def build_parser() -> argparse.ArgumentParser:
    """Build parser for the configure command."""
    parser = argparse.ArgumentParser(
        prog="tutr configure",
        description="Configure tutr provider, model, and runtime flags",
    )
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run the interactive wizard (default when no explicit options are given)",
    )
    parser.add_argument(
        "--provider",
        choices=sorted(PROVIDERS.keys()),
        help="LLM provider to use",
    )
    parser.add_argument("--model", help="Model ID in LiteLLM format (example: openai/gpt-4o)")
    parser.add_argument("--api-key", help="Provider API key to store in config")
    parser.add_argument(
        "--clear-api-key",
        action="store_true",
        help="Remove stored API key from config",
    )
    parser.add_argument(
        "--ollama-host",
        help="Ollama host URL (example: http://localhost:11434)",
    )
    parser.add_argument(
        "--clear-ollama-host",
        action="store_true",
        help="Remove stored Ollama host from config",
    )
    explain_group = parser.add_mutually_exclusive_group()
    explain_group.add_argument(
        "--show-explanation",
        action="store_true",
        help="Enable explanation output by default",
    )
    explain_group.add_argument(
        "--hide-explanation",
        action="store_true",
        help="Disable explanation output by default",
    )
    return parser


def run(argv: list[str]) -> int:
    """Execute the configure command."""
    parser = build_parser()
    args = parser.parse_args(argv)

    notify_if_update_available_async(__version__)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(name)s %(levelname)s: %(message)s",
    )

    if args.clear_api_key and args.api_key is not None:
        print("Error: --api-key and --clear-api-key cannot be used together", file=sys.stderr)
        return 2
    if args.clear_ollama_host and args.ollama_host is not None:
        print(
            "Error: --ollama-host and --clear-ollama-host cannot be used together",
            file=sys.stderr,
        )
        return 2

    show_explanation: bool | None = None
    if args.show_explanation:
        show_explanation = True
    if args.hide_explanation:
        show_explanation = False

    has_explicit_options = any(
        [
            args.provider is not None,
            args.model is not None,
            args.api_key is not None,
            args.clear_api_key,
            args.ollama_host is not None,
            args.clear_ollama_host,
            show_explanation is not None,
        ]
    )
    interactive = args.interactive or not has_explicit_options

    if CONFIG_FILE.exists() or not needs_setup():
        existing = load_config()
    else:
        existing = TutrConfig()

    try:
        updated = run_configure(
            existing,
            provider=args.provider,
            model=args.model,
            api_key=args.api_key,
            clear_api_key=args.clear_api_key,
            ollama_host=args.ollama_host,
            clear_ollama_host=args.clear_ollama_host,
            show_explanation=show_explanation,
            interactive=interactive,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print("\nConfiguration saved to ~/.tutr/config.json")
    print(f"  provider: {updated.provider or '(not set)'}")
    print(f"  model: {updated.model}")
    print(f"  api_key: {'set' if updated.api_key else 'not set'}")
    print(f"  ollama_host: {updated.ollama_host or 'not set'}")
    print("  show_explanation: " + ("true" if bool(updated.show_explanation) else "false"))
    print("")
    return 0
