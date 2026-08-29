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
        # ``create`` was refactored from ``def create(...)`` to a
        # ``typer.Typer`` sub-app. The current form is
        # ``create = typer.Typer(...)``; the legacy ``def create(`` form
        # would also satisfy the original assertion, so accept either
        # to keep this test stable across the refactor.
        assert (
            "def create(" in source_code
            or "create = typer.Typer(" in source_code
        )
        assert "def dev(" in source_code
        assert "def setup_signal_handlers(" in source_code

        # Hard cutover (task 8): the bare ``cli = typer.Typer(...)``
        # instantiation was replaced with a FastblocksCLI subclass of
        # oneiric.cli.base.OneiricCLIBase. Accept either form.
        assert (
            "cli = typer.Typer(" in source_code
            or "cli = FastblocksCLI(" in source_code
        )

        assert "@cli.command(" in source_code

        assert "signal.signal(" in source_code

        assert "import asyncio" in source_code
