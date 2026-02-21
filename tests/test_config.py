"""Unit tests for tutr.config."""

import json
import stat

import pytest

import tutr.config as config_module
from tutr.config import DEFAULT_MODEL, TutrConfig, load_config, needs_setup, save_config


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Redirect CONFIG_DIR and CONFIG_FILE to a temp directory for every test."""
    config_dir = tmp_path / ".tutr"
    config_file = config_dir / "config.json"
    monkeypatch.setattr(config_module, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)
    return config_dir, config_file


@pytest.fixture()
def config_dir(isolated_config):
    return isolated_config[0]


@pytest.fixture()
def config_file(isolated_config):
    return isolated_config[1]


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_no_file_returns_empty_dict(self, config_file):
        assert not config_file.exists()
        result = load_config()
        assert result == TutrConfig()

    def test_loads_values_from_file(self, config_dir, config_file):
        config_dir.mkdir(parents=True)
        config_file.write_text(json.dumps({"model": "openai/gpt-4o", "provider": "openai"}))

        result = load_config()

        assert result.model == "openai/gpt-4o"
        assert result.provider == "openai"

    def test_loads_show_explanation_from_file(self, config_dir, config_file):
        config_dir.mkdir(parents=True)
        config_file.write_text(json.dumps({"show_explanation": True}))

        result = load_config()

        assert result.show_explanation is True

    def test_tutr_model_env_overrides_file(self, config_dir, config_file, monkeypatch):
        config_dir.mkdir(parents=True)
        config_file.write_text(json.dumps({"model": "openai/gpt-4o"}))
        monkeypatch.setenv("TUTR_MODEL", "anthropic/claude-3-opus")

        result = load_config()

        assert result.model == "anthropic/claude-3-opus"

    def test_tutr_model_env_sets_model_when_no_file(self, monkeypatch):
        monkeypatch.setenv("TUTR_MODEL", "ollama/llama3")

        result = load_config()

        assert result.model == "ollama/llama3"

    def test_provider_api_key_env_override(self, config_dir, config_file, monkeypatch):
        config_dir.mkdir(parents=True)
        config_file.write_text(json.dumps({"provider": "anthropic"}))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

        result = load_config()

        assert result.api_key == "sk-test-key"

    def test_provider_api_key_not_injected_when_env_unset(
        self, config_dir, config_file, monkeypatch
    ):
        config_dir.mkdir(parents=True)
        config_file.write_text(json.dumps({"provider": "anthropic"}))
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        result = load_config()

        assert result.api_key is None

    def test_unknown_provider_does_not_inject_api_key(self, config_dir, config_file, monkeypatch):
        config_dir.mkdir(parents=True)
        config_file.write_text(json.dumps({"provider": "unknown_provider"}))
        monkeypatch.setenv("UNKNOWN_PROVIDER_API_KEY", "should-not-appear")

        result = load_config()

        assert result.api_key is None

    def test_ollama_provider_no_api_key_injected(self, config_dir, config_file):
        """Ollama has env_key=None, so no key injection should occur."""
        config_dir.mkdir(parents=True)
        config_file.write_text(json.dumps({"provider": "ollama"}))

        result = load_config()

        assert result.api_key is None

    def test_gemini_provider_api_key_override(self, config_dir, config_file, monkeypatch):
        config_dir.mkdir(parents=True)
        config_file.write_text(json.dumps({"provider": "gemini"}))
        monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")

        result = load_config()

        assert result.api_key == "gemini-test-key"

    def test_openai_provider_api_key_override(self, config_dir, config_file, monkeypatch):
        config_dir.mkdir(parents=True)
        config_file.write_text(json.dumps({"provider": "openai"}))
        monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")

        result = load_config()

        assert result.api_key == "openai-test-key"

    def test_no_provider_in_config_no_api_key_injected(self, config_dir, config_file, monkeypatch):
        config_dir.mkdir(parents=True)
        config_file.write_text(json.dumps({"model": "some-model"}))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-irrelevant")

        result = load_config()

        assert result.api_key is None

    def test_file_values_preserved_alongside_overrides(self, config_dir, config_file, monkeypatch):
        config_dir.mkdir(parents=True)
        config_file.write_text(json.dumps({"provider": "openai", "extra_key": "preserved"}))
        monkeypatch.setenv("TUTR_MODEL", "openai/gpt-4o")
        monkeypatch.setenv("OPENAI_API_KEY", "openai-key")

        result = load_config()

        assert result.model_dump(exclude_none=True) == {
            "provider": "openai",
            "model": "openai/gpt-4o",
            "api_key": "openai-key",
        }


# ---------------------------------------------------------------------------
# save_config
# ---------------------------------------------------------------------------


class TestSaveConfig:
    def test_creates_config_dir_if_missing(self, config_dir, config_file):
        assert not config_dir.exists()

        save_config(TutrConfig(model="test/model"))

        assert config_dir.is_dir()

    def test_writes_json_to_config_file(self, config_file):
        payload = TutrConfig(
            model="test/model",
            provider="openai",
            api_key="my-key",
            show_explanation=True,
        )

        save_config(payload)

        written = json.loads(config_file.read_text())
        assert written == payload.model_dump(exclude_none=True)

    def test_sets_file_permissions_to_0o600(self, config_file):
        save_config(TutrConfig(model="test/model"))

        file_mode = stat.S_IMODE(config_file.stat().st_mode)
        assert file_mode == 0o600

    def test_overwrites_existing_config(self, config_dir, config_file):
        config_dir.mkdir(parents=True)
        config_file.write_text(json.dumps({"model": "old/model"}))

        save_config(TutrConfig(model="new/model"))

        written = json.loads(config_file.read_text())
        assert written["model"] == "new/model"

    def test_saves_empty_dict(self, config_file):
        save_config(TutrConfig())

        written = json.loads(config_file.read_text())
        assert written == {"model": DEFAULT_MODEL}

    def test_json_is_pretty_printed(self, config_file):
        """Verify indent=2 formatting is applied."""
        save_config(TutrConfig(provider="openai"))

        raw = config_file.read_text()
        assert "\n" in raw


# ---------------------------------------------------------------------------
# needs_setup
# ---------------------------------------------------------------------------


class TestNeedsSetup:
    def _clear_provider_env_keys(self, monkeypatch):
        """Remove all known provider API key env vars."""
        for info in config_module.PROVIDERS.values():
            if info["env_key"]:
                monkeypatch.delenv(info["env_key"], raising=False)

    def test_true_when_no_file_and_no_env_vars(self, config_file, monkeypatch):
        self._clear_provider_env_keys(monkeypatch)
        assert not config_file.exists()

        assert needs_setup() is True

    def test_false_when_config_file_exists(self, config_dir, config_file, monkeypatch):
        self._clear_provider_env_keys(monkeypatch)
        config_dir.mkdir(parents=True)
        config_file.write_text(json.dumps({}))

        assert needs_setup() is False

    def test_false_when_gemini_api_key_set(self, config_file, monkeypatch):
        self._clear_provider_env_keys(monkeypatch)
        monkeypatch.setenv("GEMINI_API_KEY", "some-key")

        assert needs_setup() is False

    def test_false_when_anthropic_api_key_set(self, config_file, monkeypatch):
        self._clear_provider_env_keys(monkeypatch)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "some-key")

        assert needs_setup() is False

    def test_false_when_openai_api_key_set(self, config_file, monkeypatch):
        self._clear_provider_env_keys(monkeypatch)
        monkeypatch.setenv("OPENAI_API_KEY", "some-key")

        assert needs_setup() is False

    def test_ollama_env_key_is_none_does_not_satisfy_setup(self, config_file, monkeypatch):
        """Ollama has no env key, so setting arbitrary env vars should not suppress setup."""
        self._clear_provider_env_keys(monkeypatch)
        # Ollama's env_key is None; setting an arbitrary var should not matter
        monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")

        assert needs_setup() is True

    def test_file_takes_precedence_over_missing_env_keys(
        self, config_dir, config_file, monkeypatch
    ):
        self._clear_provider_env_keys(monkeypatch)
        config_dir.mkdir(parents=True)
        config_file.write_text(json.dumps({"provider": "openai"}))

        assert needs_setup() is False
