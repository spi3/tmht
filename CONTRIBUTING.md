# Contributing to tutr

This guide covers local setup, validation, pull requests, and releases.

## Setup

1. Clone and enter the repository:

```bash
git clone https://github.com/spi3/tutr.git
cd tutr
```

2. Install dependencies:

```bash
uv sync
```

3. Enable repository git hooks:

```bash
git config core.hooksPath .githooks
```

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  Entry Points                                                    │
│                                                                  │
│  tutr-cli <query>           tutr  /  python -m tutr             │
│  (one-shot CLI)             (interactive shell wrapper)         │
└──────────┬──────────────────────────────┬───────────────────────┘
           │                              │
           ▼                              ▼
┌──────────────────────┐   ┌─────────────────────────────────┐
│  src/tutr/cli/       │   │  src/tutr/shell/                │
│  app.py  – routing   │   │  loop.py  – PTY loop            │
│  query.py – query    │   │  detection.py – shell detect    │
│  configure.py        │   │  hooks.py – rc startup hooks    │
│  wizard.py – setup   │   │  shell.py – tutor prompt logic  │
└──────────┬───────────┘   └──────────────┬──────────────────┘
           └──────────────┬───────────────┘
                          │
                          ▼
           ┌──────────────────────────────┐
           │  src/tutr/                   │
           │  tutr.py    – orchestration  │
           │  llm.py     – LiteLLM calls  │
           │  prompt.py  – LLM prompts    │
           │  config.py  – config file    │
           │  context.py – system info    │
           │  safety.py  – command safety │
           │  models/    – Pydantic types  │
           └──────────────┬───────────────┘
                          │
                          ▼
           ┌──────────────────────────────┐
           │  LiteLLM → AI Provider       │
           │  OpenAI · Anthropic · Gemini │
           │  xAI · Ollama (local)        │
           └──────────────────────────────┘
```

## Development Workflow

Run the app locally:

```bash
uv run tutr
```

Run the one-shot CLI:

```bash
uv run tutr-cli --help
```

Run module entrypoint:

```bash
uv run python -m tutr
```

## Validation

Run the full pre-merge validation suite:

```bash
uv run poe check
```

This runs:
- Ruff lint (`ruff check .`)
- Ruff format check (`ruff format --check .`)
- Mypy strict type-checking
- `pip-audit`
- Pytest (with coverage gate)

Common focused commands:

```bash
uv run ruff check .
uv run ruff format .
uv run mypy
uv run pytest -q
```

Optional live integration tests:

```bash
TUTR_RUN_INTEGRATION=1 uv run pytest -q -m integration
```

## Branch and Commit Conventions

- Branch off `main` for all changes; use short descriptive names (e.g. `fix-ollama-host`, `add-no-color-docs`).
- Write commit messages in the imperative mood with a type prefix:
  - `feat:` — new user-facing functionality
  - `fix:` — bug fix
  - `docs:` — documentation-only changes
  - `refactor:` — code restructuring without behaviour change
  - `test:` — test additions or fixes
  - `chore:` — tooling, dependencies, release plumbing
- Keep commits focused; one logical change per commit.

## Pull Requests

1. Create a branch from `main`.
2. Keep changes focused and include tests for behavior changes.
3. Run `uv run poe check` locally and ensure it passes.
4. Update docs when behavior, config, or commands change.
5. Open a PR with:
- clear problem statement
- concise change summary
- validation steps and results

## Releases

Use the release script:

```bash
scripts/release.sh patch
```

You can also pass `minor`, `major`, or an explicit version like `scripts/release.sh 0.1.6`.
The script updates `pyproject.toml`, runs checks, creates/pushes a `vX.Y.Z` tag, and creates the GitHub release.

Authoritative production publish path: GitHub Actions trusted publishing.
- Triggered by publishing a GitHub Release (created by `scripts/release.sh`).
- Implemented by `.github/workflows/python-publish.yml` using OIDC (`id-token: write`) and `pypa/gh-action-pypi-publish`.

Manual `twine` publish commands are non-canonical maintainer fallbacks:
- `uv run poe publish_testpypi` is for staging to TestPyPI.
- `uv run poe publish_pypi` is only for exceptional/manual recovery scenarios with `TWINE_USERNAME`/`TWINE_PASSWORD`.

Release CI enforces `vX.Y.Z` tags and checks that the tag version matches `pyproject.toml`.
The historical `0.1.0` tag is legacy and should not be reused for new releases.
