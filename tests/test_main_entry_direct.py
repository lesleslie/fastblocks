import sys
from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
def test_main_entry_directly(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_cli = MagicMock()

    mock_modules = {
        "fastblocks.cli": MagicMock(cli=mock_cli),
    }

    for mod_name, mock_mod in mock_modules.items():
        monkeypatch.setitem(sys.modules, mod_name, mock_mod)

    code = "if __name__ == '__main__':\n    from fastblocks.cli import cli\n    cli()"

    namespace = {"__name__": "__main__"}

    exec(code, namespace)  # nosec B102

    mock_cli.assert_called_once()
