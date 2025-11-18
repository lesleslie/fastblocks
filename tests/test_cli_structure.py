from pathlib import Path

import pytest

# Get project root dynamically
PROJECT_ROOT = Path(__file__).parent.parent


@pytest.mark.unit
class TestCLIStructure:
    def test_cli_module_structure(self) -> None:
        cli_file_path = PROJECT_ROOT / "fastblocks/cli.py"

        source_code = Path(cli_file_path).read_text()

        assert "def run(" in source_code
        assert "def create(" in source_code
        assert "def dev(" in source_code
        assert "def setup_signal_handlers(" in source_code

        assert "cli = typer.Typer(" in source_code

        assert "@cli.command(" in source_code

        assert "signal.signal(" in source_code

        assert "import asyncio" in source_code
        assert "nest_asyncio.apply()" in source_code
