"""Live integration tests that hit a real LLM backend."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from tutr.config import TutrConfig
from tutr.tutr import run


def _load_live_config() -> TutrConfig:
    if os.environ.get("TUTR_RUN_INTEGRATION") != "1":
        pytest.skip("Set TUTR_RUN_INTEGRATION=1 to run live integration tests")

    model = os.environ.get("TUTR_INTEGRATION_MODEL") or os.environ.get("TUTR_MODEL")
    if not model:
        pytest.skip("Set TUTR_INTEGRATION_MODEL (or TUTR_MODEL) for live integration tests")

    provider = model.split("/", 1)[0] if "/" in model else None
    provider_key = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }.get(provider or "")

    api_key = os.environ.get("TUTR_INTEGRATION_API_KEY")
    if not api_key and provider_key:
        api_key = os.environ.get(provider_key)

    if provider != "ollama" and not api_key:
        pytest.skip(
            "No API key found. Set TUTR_INTEGRATION_API_KEY or the provider env key "
            f"({provider_key})."
        )

    return TutrConfig(provider=provider, model=model, api_key=api_key)


def _assert_safe_single_command(command: str) -> None:
    dangerous_pattern = re.compile(
        r"(`|\$\(|\brm\b|\bmkfs\b|\bdd\b|\bshutdown\b|\breboot\b|\bkillall\b|\b:\s*\(\))",
        re.IGNORECASE,
    )
    assert "\n" not in command, f"expected a single-line command, got: {command!r}"
    assert not dangerous_pattern.search(command), f"unsafe command generated: {command!r}"


def _run_shell_command(command: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-lc", command],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )


class TestSuccessfulExecution:
    @pytest.mark.integration
    def test_generated_command_executes_successfully(self, tmp_path: Path) -> None:
        config = _load_live_config()
        result = run(
            [
                "please",
                "generate",
                "a",
                "portable",
                "shell",
                "command",
                "that",
                "prints",
                "INTEGRATION_OK",
                "exactly",
                "once",
            ],
            config,
        )

        command = result.command.strip()
        assert command, "expected non-empty command from LLM"
        _assert_safe_single_command(command)

        completed = _run_shell_command(command, tmp_path)
        output = f"{completed.stdout}\n{completed.stderr}".strip()
        assert completed.returncode == 0, f"command failed: {command!r}\noutput:\n{output}"
        assert "INTEGRATION_OK" in output, f"missing expected token in output:\n{output}"


@dataclass
class EvaluationCase:
    prompt_words: list[str]
    accuracy_pattern: re.Pattern[str]
    quality_hint: str


class TestResultEvaluation:
    @pytest.mark.integration
    @pytest.mark.parametrize(
        "case",
        [
            EvaluationCase(
                prompt_words=[
                    "please",
                    "print",
                    "the",
                    "current",
                    "working",
                    "directory",
                    "as",
                    "a",
                    "single",
                    "command",
                ],
                accuracy_pattern=re.compile(r"\bpwd\b|\bos\.getcwd\b", re.IGNORECASE),
                quality_hint="should use pwd (or a direct equivalent)",
            ),
            EvaluationCase(
                prompt_words=[
                    "please",
                    "list",
                    "all",
                    "files",
                    "including",
                    "hidden",
                    "ones",
                    "in",
                    "long",
                    "format",
                    "as",
                    "a",
                    "single",
                    "command",
                ],
                accuracy_pattern=re.compile(r"\bls\b.*-a|-\w*a\w*", re.IGNORECASE),
                quality_hint="should include ls with hidden-file flag (-a)",
            ),
        ],
    )
    def test_command_accuracy_and_quality(self, case: EvaluationCase) -> None:
        config = _load_live_config()
        result = run(case.prompt_words, config)
        command = result.command.strip()

        assert command, "expected non-empty command"
        _assert_safe_single_command(command)

        # Accuracy: command should semantically match the requested task.
        assert case.accuracy_pattern.search(command), (
            f"low-accuracy command: {command!r}; expected pattern hint: {case.quality_hint}"
        )

        # Quality: concise, direct command without shell chaining.
        assert len(command) <= 120, f"command is too verbose: {command!r}"
        assert "&&" not in command and ";" not in command, (
            f"expected one direct command, got: {command!r}"
        )
