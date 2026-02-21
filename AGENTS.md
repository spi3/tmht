# AGENTS.md

AI Agents **MUST** follow these instructions.

## Commands

```bash
uv sync              # Install/update project and dependencies
uv run tutr          # Run the CLI
uv run tutr -V       # Print version
uv run python -m tutr  # Run as module
uv add <pkg>         # Add a dependency
uv build             # Build wheel + sdist into dist/
```

## Architecture

Python CLI tool using `uv` (with `uv_build` backend) and `src/` layout.

- **Entry point**: `src/tutr/cli.py` — `entrypoint()` is registered as `[project.scripts] tutr` in `pyproject.toml`. `main(argv)` contains the argparse logic and returns an exit code.
- **Interactive shell wrapper**: `src/tutr/shell.py` (`[project.scripts] shell`) auto-detects and launches Bash, Zsh, or PowerShell. `TUTR_SHELL` can override detection.
- **`__main__.py`**: enables `python -m tutr` invocation.
- **Version**: single source of truth in `src/tutr/__init__.py` (`__version__`).

## Self-Refinement

When an agent discovers new information, conventions, or workflow guidance that is important and relevant to all agents working on this project, the agent **MUST** add it to `AGENTS.md` as part of the same change.
