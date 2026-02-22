"""Unit tests for tutr.update_check."""

import io
from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

import pytest

from tutr.config import TutrConfig
from tutr.update_check import (
    _fetch_latest_version,
    _infer_installer,
    _is_update_check_due,
    _record_update_check_epoch,
    _update_command,
    notify_if_update_available,
    notify_if_update_available_async,
)


@pytest.fixture(autouse=True)
def isolated_update_cache(tmp_path, monkeypatch):
    cache_file = tmp_path / "update-check.json"
    monkeypatch.setattr("tutr.update_check.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("tutr.update_check.UPDATE_CHECK_CACHE_FILE", cache_file)
    return cache_file


class _TtyStringIO(io.StringIO):
    def isatty(self) -> bool:
        return True


class TestFetchLatestVersion:
    def test_reads_version_from_pypi_json(self):
        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        with patch("tutr.update_check.urlopen", return_value=mock_response):
            with patch("tutr.update_check.json.load", return_value={"info": {"version": "0.2.0"}}):
                assert _fetch_latest_version() == "0.2.0"

    def test_returns_none_on_invalid_payload(self):
        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        with patch("tutr.update_check.urlopen", return_value=mock_response):
            with patch("tutr.update_check.json.load", return_value={"unexpected": {}}):
                assert _fetch_latest_version() is None

    def test_returns_none_when_network_fails(self):
        with patch("tutr.update_check.urlopen", side_effect=OSError("offline")):
            assert _fetch_latest_version() is None


class TestInferInstaller:
    def test_detects_pipx(self):
        with patch("tutr.update_check.sys.executable", "/home/u/.local/pipx/venvs/tutr/bin/python"):
            with patch("tutr.update_check.sys.prefix", "/home/u/.local/pipx/venvs/tutr"):
                assert _infer_installer() == "pipx"

    def test_detects_uv(self):
        with patch(
            "tutr.update_check.sys.executable", "/home/u/.local/share/uv/tools/tutr/bin/python"
        ):
            with patch("tutr.update_check.sys.prefix", "/home/u/.local/share/uv/tools/tutr"):
                assert _infer_installer() == "uv"


class TestUpdateCommand:
    def test_prefers_pipx_when_runtime_is_pipx(self):
        with patch("tutr.update_check._infer_installer", return_value="pipx"):
            with patch(
                "tutr.update_check.shutil.which",
                side_effect=lambda tool: "/bin/pipx" if tool == "pipx" else None,
            ):
                assert _update_command() == ["pipx", "upgrade", "tutr"]

    def test_prefers_uv_when_runtime_is_uv(self):
        with patch("tutr.update_check._infer_installer", return_value="uv"):
            with patch(
                "tutr.update_check.shutil.which",
                side_effect=lambda tool: "/bin/uv" if tool == "uv" else None,
            ):
                assert _update_command() == ["uv", "tool", "upgrade", "tutr"]

    def test_falls_back_to_pip_module(self):
        with patch("tutr.update_check._infer_installer", return_value=None):
            with patch("tutr.update_check.shutil.which", return_value=None):
                with patch("tutr.update_check.sys.executable", "/usr/bin/python3"):
                    assert _update_command() == [
                        "/usr/bin/python3",
                        "-m",
                        "pip",
                        "install",
                        "--upgrade",
                        "tutr",
                    ]


class TestNotifyIfUpdateAvailable:
    def test_prints_message_when_outdated_and_non_interactive(self):
        stream = io.StringIO()
        with patch("tutr.update_check._is_update_check_due", return_value=True):
            with patch("tutr.update_check._record_update_check_epoch"):
                with patch("tutr.update_check._fetch_latest_version", return_value="0.2.0"):
                    with patch(
                        "tutr.update_check._update_command",
                        return_value=["uv", "tool", "upgrade", "tutr"],
                    ):
                        notify_if_update_available("0.1.2", stream=stream)

        output = stream.getvalue()
        assert "0.1.2 -> 0.2.0" in output
        assert "uv tool upgrade tutr" in output

    def test_runs_update_when_user_confirms(self):
        stream = _TtyStringIO()
        stdin = _TtyStringIO("y\n")
        with patch("tutr.update_check.sys.stdin", stdin):
            with patch("tutr.update_check._is_update_check_due", return_value=True):
                with patch("tutr.update_check._record_update_check_epoch"):
                    with patch("tutr.update_check._fetch_latest_version", return_value="0.2.0"):
                        with patch(
                            "tutr.update_check._update_command",
                            return_value=["pipx", "upgrade", "tutr"],
                        ):
                            with patch("tutr.update_check.subprocess.run") as mock_run:
                                mock_run.return_value.returncode = 0
                                notify_if_update_available("0.1.2", stream=stream)

        mock_run.assert_called_once_with(["pipx", "upgrade", "tutr"], check=False)
        assert "Run update now?" in stream.getvalue()
        assert "tutr updated successfully." in stream.getvalue()

    def test_does_not_run_update_when_user_declines(self):
        stream = _TtyStringIO()
        stdin = _TtyStringIO("n\n")
        with patch("tutr.update_check.sys.stdin", stdin):
            with patch("tutr.update_check._is_update_check_due", return_value=True):
                with patch("tutr.update_check._record_update_check_epoch"):
                    with patch("tutr.update_check._fetch_latest_version", return_value="0.2.0"):
                        with patch(
                            "tutr.update_check._update_command",
                            return_value=["uv", "tool", "upgrade", "tutr"],
                        ):
                            with patch("tutr.update_check.subprocess.run") as mock_run:
                                notify_if_update_available("0.1.2", stream=stream)

        mock_run.assert_not_called()

    def test_prints_nothing_when_versions_match(self):
        stream = io.StringIO()
        with patch("tutr.update_check._is_update_check_due", return_value=True):
            with patch("tutr.update_check._record_update_check_epoch"):
                with patch("tutr.update_check._fetch_latest_version", return_value="0.1.2"):
                    notify_if_update_available("0.1.2", stream=stream)

        assert stream.getvalue() == ""

    def test_prints_nothing_when_latest_version_unknown(self):
        stream = io.StringIO()
        with patch("tutr.update_check._is_update_check_due", return_value=True):
            with patch("tutr.update_check._record_update_check_epoch"):
                with patch("tutr.update_check._fetch_latest_version", return_value=None):
                    notify_if_update_available("0.1.2", stream=stream)

        assert stream.getvalue() == ""

    def test_skips_interactive_prompt_when_disabled(self):
        stream = _TtyStringIO()
        stdin = _TtyStringIO("y\n")
        with patch("tutr.update_check.sys.stdin", stdin):
            with patch("tutr.update_check._is_update_check_due", return_value=True):
                with patch("tutr.update_check._record_update_check_epoch"):
                    with patch("tutr.update_check._fetch_latest_version", return_value="0.2.0"):
                        with patch(
                            "tutr.update_check._update_command",
                            return_value=["uv", "tool", "upgrade", "tutr"],
                        ):
                            with patch("tutr.update_check.subprocess.run") as mock_run:
                                notify_if_update_available(
                                    "0.1.2",
                                    stream=stream,
                                    allow_interactive_update=False,
                                )

        mock_run.assert_not_called()
        assert "Run update now?" not in stream.getvalue()

    def test_skips_when_cache_not_due(self):
        stream = io.StringIO()
        with patch("tutr.update_check._is_update_check_due", return_value=False):
            with patch("tutr.update_check._fetch_latest_version") as fetch:
                notify_if_update_available("0.1.2", stream=stream)

        fetch.assert_not_called()
        assert stream.getvalue() == ""

    def test_skips_when_update_checks_disabled(self):
        stream = io.StringIO()
        config = TutrConfig(update_check_enabled=False)
        with patch("tutr.update_check._fetch_latest_version") as fetch:
            notify_if_update_available("0.1.2", stream=stream, config=config)

        fetch.assert_not_called()
        assert stream.getvalue() == ""


class TestUpdateCheckCache:
    def test_records_update_check_epoch(self, isolated_update_cache):
        _record_update_check_epoch(123.0)
        assert isolated_update_cache.exists()
        assert '"last_checked_epoch": 123.0' in Path(isolated_update_cache).read_text()

    def test_is_due_after_ttl(self):
        with patch("tutr.update_check._read_last_update_check_epoch", return_value=1_000.0):
            assert _is_update_check_due(1_000.0 + 86_400.0) is True

    def test_is_not_due_before_ttl(self):
        with patch("tutr.update_check._read_last_update_check_epoch", return_value=1_000.0):
            assert _is_update_check_due(1_000.0 + 60.0) is False


class TestNotifyIfUpdateAvailableAsync:
    def test_starts_background_non_interactive_thread(self):
        mock_thread = MagicMock()
        with patch("tutr.update_check.threading.Thread", return_value=mock_thread) as thread_cls:
            notify_if_update_available_async("0.1.2")

        thread_cls.assert_called_once_with(
            target=notify_if_update_available,
            args=("0.1.2", ANY),
            kwargs={"allow_interactive_update": False, "config": None},
            daemon=True,
            name="tutr-update-check",
        )
        mock_thread.start.assert_called_once_with()
