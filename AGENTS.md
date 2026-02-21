# AGENTS.md

AI Agents **MUST** follow these instructions.

## Commands

```bash
uv sync              # Install/update project and dependencies
uv run tutr          # Run the CLI
uv run tutr -V       # Print version
uv run python -m tutr  # Run as module
uv run poe check     # Run lint, format check, type-check, and tests
uv run poe dist      # Build sdist/wheel and run twine checks
uv run poe publish_testpypi  # Upload dist/* to TestPyPI
uv run poe publish_pypi      # Upload dist/* to PyPI
uv run ruff check .  # Lint
uv run ruff format . # Format
uv run mypy          # Type-check
uv add <pkg>         # Add a dependency
uv build             # Build wheel + sdist into dist/
git config core.hooksPath .githooks  # Enable repo-managed git hooks
```

## Architecture

Python CLI tool using `uv` (with `uv_build` backend) and `src/` layout.

- **One-shot CLI entry point**: `src/tutr/cli/` package (`[project.scripts] tutr-cli` via `tutr.cli:entrypoint`).
  - `app.py` routes top-level commands.
  - `query.py` handles natural-language command generation mode.
  - `configure.py` handles `tutr-cli configure`.
  - `wizard.py` contains interactive setup/config flows (`run_setup`, `run_configure`).
- **Interactive shell wrapper**: `src/tutr/shell/` package (`[project.scripts] shell` via `tutr.shell:entrypoint`) contains the PTY loop (`loop.py`), shell detection/launch config (`detection.py`), startup hook writers (`hooks.py`), and tutor prompt logic (`tutor.py`). `TUTR_SHELL` can override detection.
- **`__main__.py`**: enables `python -m tutr` invocation.
- **Version**: keep `project.version` in `pyproject.toml` and `__version__` in `src/tutr/__init__.py` in sync.

## Self-Refinement

When an agent discovers new information, conventions, or workflow guidance that is important and relevant to all agents working on this project, the agent **MUST** add it to `AGENTS.md` as part of the same change.

## Conventions

- Prefer structured models (for example, Pydantic models) over untyped `dict` values for config and other cross-module data contracts whenever it makes sense.
- Use `uv run poe check` as the default pre-merge validation command; it runs ruff lint, ruff format check, mypy, and pytest.
- Keep `mypy` in strict mode for `src/`; for `tests/`, use `tool.mypy.overrides` to relax `disallow_untyped_defs`/`disallow_untyped_calls` when needed instead of weakening global strictness.
- The repository pre-commit hook lives at `.githooks/pre-commit` and runs `uv run poe check`; enable it locally with `git config core.hooksPath .githooks`.
- Live integration tests are opt-in and require env vars: run with `TUTR_RUN_INTEGRATION=1 uv run pytest -q -m integration` and set `TUTR_INTEGRATION_MODEL` (or `TUTR_MODEL`) plus either `TUTR_INTEGRATION_API_KEY` or the provider-specific API key env var.
- Ollama configuration uses `ollama_host` in `TutrConfig` and supports `OLLAMA_HOST` env override; default host is `http://localhost:11434`.
- For releases, build and validate artifacts with `uv run poe dist` before any upload, then publish with `uv run poe publish_testpypi` and `uv run poe publish_pypi` using `TWINE_USERNAME=__token__` and an API token in `TWINE_PASSWORD`.
- When documenting shell rc auto-start for `tutr`, always include a recursion guard env var (for example `TUTR_AUTOSTARTED`) because the wrapper shell sources the user's rc file.
- The shell wrapper launch config sets both `TUTR_ACTIVE=1` and `TUTR_AUTOSTARTED=1` for the child shell environment to prevent recursive auto-start.
