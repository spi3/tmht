# AGENTS.md

AI Agents **MUST** follow these instructions.

## Commands

```bash
uv sync              # Install/update project and dependencies
uv run tutr          # Run the CLI
uv run tutr -V       # Print version
uv run python -m tutr  # Run as module
uv run poe check     # Run lint, format check, type-check, and tests
uv run ruff check .  # Lint
uv run ruff format . # Format
uv run mypy          # Type-check
uv add <pkg>         # Add a dependency
uv build             # Build wheel + sdist into dist/
```

## Architecture

Python CLI tool using `uv` (with `uv_build` backend) and `src/` layout.

- **Entry point**: `src/tutr/cli.py` — `entrypoint()` is registered as `[project.scripts] tutr` in `pyproject.toml`. `main(argv)` contains the argparse logic and returns an exit code.
- **Interactive shell wrapper**: `src/tutr/shell/` package (`[project.scripts] shell` via `tutr.shell:entrypoint`) contains the PTY loop (`loop.py`), shell detection/launch config (`detection.py`), startup hook writers (`hooks.py`), and tutor prompt logic (`tutor.py`). `TUTR_SHELL` can override detection.
- **`__main__.py`**: enables `python -m tutr` invocation.
- **Version**: single source of truth in `src/tutr/__init__.py` (`__version__`).

## Self-Refinement

When an agent discovers new information, conventions, or workflow guidance that is important and relevant to all agents working on this project, the agent **MUST** add it to `AGENTS.md` as part of the same change.

## Conventions

- Prefer structured models (for example, Pydantic models) over untyped `dict` values for config and other cross-module data contracts whenever it makes sense.
- Use `uv run poe check` as the default pre-merge validation command; it runs ruff lint, ruff format check, mypy, and pytest.
