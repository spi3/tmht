# Security Tasks: TMHT (tutr)

Derived from `docs/analysis/security.md` (2026-02-20).

## P0 - Critical

- [x] Add a production command safety filter for LLM output.
  - Scope: `src/tutr/cli/query.py`, `src/tutr/shell/shell.py`, new safety module in `src/tutr/`.
  - Action: Validate suggested commands before display/auto-run; block or require explicit override for dangerous patterns (for example `rm -rf`, `mkfs`, `dd`, fork bombs, `curl|bash`).
  - Note: Reuse and harden logic from `tests/test_integration_live.py` (`_assert_safe_single_command()`).

- [x] Restrict config directory permissions to owner-only.
  - Scope: `src/tutr/config.py`.
  - Action: Create `~/.tutr` with `mode=0o700` and ensure existing directory permissions are corrected if too permissive.

- [x] Eliminate config file permission race when writing secrets.
  - Scope: `src/tutr/config.py`.
  - Action: Create config file atomically with `0o600` at open time (`os.open` + `os.fdopen`) instead of write-then-`chmod`.

## P1 - High

- [x] Deprecate or hard-warn on `--api-key` CLI argument.
  - Scope: `src/tutr/cli/configure.py`, docs.
  - Action: Print explicit warning about shell history/process-list leakage; prefer interactive prompt or env vars.
  - Optional: Add `--api-key-stdin` for non-interactive safe usage.

- [x] Document transmitted data and privacy implications.
  - Scope: user docs (`README` and/or `docs/`).
  - Action: Clearly document that queries, command docs (`man`/`--help`), system info, and up to 2048 chars of shell output may be sent to provider APIs.

- [x] Commit and maintain `uv.lock`.
  - Scope: repo root (`.gitignore`, lockfile policy).
  - Action: Ensure `uv.lock` is tracked for reproducible installs/builds.

## P2 - Medium

- [x] Add query input length limits.
  - Scope: `src/tutr/tutr.py`, `src/tutr/cli/query.py`.
  - Action: Enforce max query length (for example 1000 chars) and fail with actionable error message.

- [x] Add dependency vulnerability scanning to checks/CI.
  - Scope: `pyproject.toml` (`poe` tasks), CI workflow(s).
  - Action: Integrate `pip-audit` (or equivalent) and make results visible in CI.

- [x] Cache update checks and add opt-out.
  - Scope: `src/tutr/update_check.py`, config/docs.
  - Action: Check at most once per 24h; provide a flag/config to disable update checks.

- [x] Strengthen prompt-injection defenses.
  - Scope: prompt construction in `src/tutr/`.
  - Action: Keep documentation context clearly separated from instructions; explicitly instruct model to ignore instructions embedded in context; rely on safety filter as enforcement layer.

## P3 - Low

- [ ] Add a shell-mode no-execute option.
  - Scope: shell CLI/config and `src/tutr/shell/`.
  - Action: Add `--no-execute`/dry-run behavior to only show suggestions and never auto-run.

- [ ] Add redaction for sensitive terminal output before LLM calls.
  - Scope: `src/tutr/shell/loop.py` and shared helpers.
  - Action: Redact common secret patterns (for example `sk-...`, `token=`, `password=`) before sending context.

- [x] Verify config permissions on load.
  - Scope: `src/tutr/config.py`.
  - Action: Warn (or auto-fix) when config file or directory permissions are more permissive than expected.

- [x] Tighten dependency constraints for `litellm`.
  - Scope: `pyproject.toml`.
  - Action: Use bounded range (for example `<2.0`) and review upgrade policy.

## Tracking Notes

- [ ] Add tests for each security control above (unit + integration where relevant).
- [ ] Run full validation before merge: `uv run poe check`.
