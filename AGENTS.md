# AGENTS.md

AI Agents **MUST** follow these instructions.

## Commands

```bash
uv sync              # Install/update project and dependencies
uv run tutr          # Run the CLI
uv run tutr -V       # Print version
uv run python -m tutr  # Run as module
uv run poe check     # Run lint, format check, type-check, vulnerability scan, and tests
uv run poe dist      # Build sdist/wheel and run twine checks
uv run poe publish_testpypi  # Upload dist/* to TestPyPI
uv run poe publish_pypi      # Upload dist/* to PyPI
scripts/release.sh [patch|minor|major|X.Y.Z]  # Canonical release flow: bump, validate, tag, and create GitHub release
uv run ruff check .  # Lint
uv run ruff format . # Format
uv run mypy          # Type-check
scripts/run_integration_tests.sh [--model <provider/model>] [--provider-key-env <ENV_KEY>]  # Run live integration tests (defaults to saved config)
cd docs && python -m http.server 8000  # Preview docs site locally
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
- **Version**: `project.version` in `pyproject.toml` is the single source of truth; `src/tutr/__init__.py` derives `__version__` from installed package metadata.

## Self-Refinement

When an agent discovers new information, conventions, or workflow guidance that is important and relevant to all agents working on this project, the agent **MUST** add it to `AGENTS.md` as part of the same change.

## Conventions

- Prefer structured models (for example, Pydantic models) over untyped `dict` values for config and other cross-module data contracts whenever it makes sense.
- Use `uv run poe check` as the default pre-merge validation command; it runs ruff lint, ruff format check, mypy, pip-audit, and pytest.
- Keep unit-test coverage gating enabled via pytest-cov (`--cov=tutr --cov-report=term-missing --cov-fail-under=85`) so `uv run poe check` fails on coverage regressions.
- Keep `mypy` in strict mode for `src/`; for `tests/`, use `tool.mypy.overrides` to relax `disallow_untyped_defs`/`disallow_untyped_calls` when needed instead of weakening global strictness.
- The repository pre-commit hook lives at `.githooks/pre-commit` and runs `uv run poe check`; enable it locally with `git config core.hooksPath .githooks`.
- Live integration tests are opt-in: run with `TUTR_RUN_INTEGRATION=1 uv run pytest -q -m integration`; if no integration override env vars are set, tests use saved `tutr` config, otherwise `TUTR_INTEGRATION_MODEL`/`TUTR_MODEL` and `TUTR_INTEGRATION_API_KEY` (or provider env key) override.
- Live integration test pacing is configurable with `TUTR_INTEGRATION_WAIT_SECONDS` (default `0`) to insert a delay between live test calls and reduce provider throttling/rate-limit risk.
- Live integration CLI retries are configurable with `TUTR_INTEGRATION_RETRIES` (default `2`) and `TUTR_INTEGRATION_RETRY_BACKOFF_SECONDS` (default `2`) to reduce transient provider/CLI flakiness.
- Keep live integration prompt/expectation cases in `tests/integration_live_cases.json`; each case uses a single `input` string and structured `expected_any_of` matcher variants (command/flags/tokens/substrings) instead of regex-only checks.
- Ollama configuration uses `ollama_host` in `TutrConfig` and supports `OLLAMA_HOST` env override; default host is `http://localhost:11434`.
- Releases are performed with `scripts/release.sh` (for example `scripts/release.sh patch`), which bumps `pyproject.toml`, runs `uv run poe check`, creates/pushes a `vX.Y.Z` tag, and creates a GitHub release.
- Release tags are standardized to `vX.Y.Z` and CI validates that the tag version matches `project.version` in `pyproject.toml`; `0.1.0` is a legacy one-off tag only.
- When documenting shell rc auto-start for `tutr`, always include a recursion guard env var (for example `TUTR_AUTOSTARTED`) because the wrapper shell sources the user's rc file.
- The shell wrapper launch config sets both `TUTR_ACTIVE=1` and `TUTR_AUTOSTARTED=1` for the child shell environment to prevent recursive auto-start.
- Documentation site is static HTML/CSS in `docs/`; preview with `cd docs && python -m http.server 8000` and deploy `docs/` directly via `.github/workflows/docs.yml`.
- Keep `litellm` constrained to a bounded major range in `pyproject.toml` (currently `>=1.81.13,<2.0`); review changelogs and tests before raising the major upper bound.
