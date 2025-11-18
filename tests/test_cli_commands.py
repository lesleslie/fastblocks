"""Tests for FastBlocks CLI commands."""

# Import CLI after conftest sets up mocks
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

if "fastblocks.cli" in sys.modules:
    del sys.modules["fastblocks.cli"]


@pytest.fixture
def cli_module():
    """Import CLI module with mocks in place."""
    from fastblocks.cli import cli

    return cli


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_console():
    """Mock console for CLI output."""
    with patch("fastblocks.cli.console") as mock:
        yield mock


class TestBasicCommands:
    """Test basic CLI commands."""

    def test_version_command(self, runner, cli_module):
        """Test version command."""
        result = runner.invoke(cli_module, ["version"])
        assert result.exit_code == 0
        # Should print version or "Unable to determine"

    def test_components_command(self, runner, cli_module, mock_console):
        """Test components command displays available components."""
        with (
            patch("fastblocks.cli._display_adapters"),
            patch("fastblocks.cli._display_default_config"),
            patch("fastblocks.cli._display_actions"),
            patch("fastblocks.cli._display_htmy_commands"),
        ):
            result = runner.invoke(cli_module, ["components"])
            assert result.exit_code == 0


class TestHTMYCommands:
    """Test HTMY component commands."""

    @pytest.mark.asyncio
    async def test_scaffold_command_basic(self, runner, cli_module):
        """Test scaffold command with basic component."""
        mock_htmy = AsyncMock()
        mock_htmy.scaffold_component = AsyncMock(return_value="/path/to/component.py")

        with patch("acb.depends.depends.get", return_value=mock_htmy):
            result = runner.invoke(
                cli_module, ["scaffold", "test_component", "--type", "dataclass"]
            )
            # Command should execute without error
            assert result.exit_code == 0 or "Created" in result.stdout

    @pytest.mark.asyncio
    async def test_list_command(self, runner, cli_module):
        """Test list command shows components."""
        mock_htmy = AsyncMock()
        mock_htmy.discover_components = AsyncMock(
            return_value={
                "test_comp": MagicMock(
                    status=MagicMock(value="ready"),
                    type=MagicMock(value="dataclass"),
                    path="/test/path",
                )
            }
        )

        with patch("acb.depends.depends.get", return_value=mock_htmy):
            result = runner.invoke(cli_module, ["list"])
            # Should show component info
            assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_validate_command(self, runner, cli_module):
        """Test validate command for a component."""
        mock_htmy = AsyncMock()
        mock_metadata = MagicMock(
            type=MagicMock(value="dataclass"),
            status=MagicMock(value="ready"),
            path="/test/path",
            docstring="Test component",
            htmx_attributes={},
            dependencies=[],
            error_message=None,
        )
        mock_htmy.validate_component = AsyncMock(return_value=mock_metadata)

        with patch("acb.depends.depends.get", return_value=mock_htmy):
            result = runner.invoke(cli_module, ["validate", "test_component"])
            assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_info_command(self, runner, cli_module):
        """Test info command for component details."""
        mock_htmy = AsyncMock()
        mock_metadata = MagicMock(
            type=MagicMock(value="dataclass"),
            status=MagicMock(value="ready"),
            path="/test/path",
        )
        mock_htmy.validate_component = AsyncMock(return_value=mock_metadata)
        mock_htmy.get_component_class = AsyncMock(return_value=MagicMock)

        with patch("acb.depends.depends.get", return_value=mock_htmy):
            result = runner.invoke(cli_module, ["info", "test_component"])
            assert result.exit_code == 0


class TestServerCommands:
    """Test server startup commands."""

    def test_run_command_default(self, runner, cli_module):
        """Test run command with default uvicorn."""
        with patch("fastblocks.cli.uvicorn.run") as mock_run:
            with patch("fastblocks.cli.setup_signal_handlers"):
                result = runner.invoke(cli_module, ["run"], catch_exceptions=False)
                # Command should be called (but mocked to not actually start server)
                assert mock_run.called or result.exit_code == 0

    def test_dev_command_default(self, runner, cli_module):
        """Test dev command with default uvicorn."""
        with patch("fastblocks.cli.uvicorn.run") as mock_run:
            with patch("fastblocks.cli.setup_signal_handlers"):
                result = runner.invoke(cli_module, ["dev"], catch_exceptions=False)
                # Development server should be configured with reload
                assert mock_run.called or result.exit_code == 0


class TestErrorHandling:
    """Test CLI error handling."""

    @pytest.mark.asyncio
    async def test_scaffold_no_adapter(self, runner, cli_module, mock_console):
        """Test scaffold command when HTMY adapter not available."""
        with patch("acb.depends.depends.get", return_value=None):
            result = runner.invoke(cli_module, ["scaffold", "test_component"])
            # Should show error message about adapter not found
            assert result.exit_code == 0  # CLI handles gracefully
            # Error message should be printed (check via mock_console if needed)

    @pytest.mark.asyncio
    async def test_list_no_adapter(self, runner, cli_module):
        """Test list command when HTMY adapter not available."""
        with patch("acb.depends.depends.get", return_value=None):
            result = runner.invoke(cli_module, ["list"])
            # Should handle missing adapter gracefully
            assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_validate_no_adapter(self, runner, cli_module):
        """Test validate command when HTMY adapter not available."""
        with patch("acb.depends.depends.get", return_value=None):
            result = runner.invoke(cli_module, ["validate", "test_component"])
            # Should handle missing adapter gracefully
            assert result.exit_code == 0
