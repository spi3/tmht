import runpy
from unittest.mock import patch

import pytest


def test_module_main_raises_system_exit_with_cli_exit_code() -> None:
    with patch("tutr.cli.main", return_value=3) as mock_main:
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module("tutr.__main__", run_name="__main__")

    assert exc_info.value.code == 3
    mock_main.assert_called_once_with()
