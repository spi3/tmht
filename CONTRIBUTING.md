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

Release CI enforces `vX.Y.Z` tags and checks that the tag version matches `pyproject.toml`.
The historical `0.1.0` tag is legacy and should not be reused for new releases.
