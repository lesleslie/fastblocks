"""Tests for the ``fastblocks run`` subcommand.

Verifies the ``run`` CLI subcommand advertises the expected options
(REQ-P2-B1-T8). The subcommand itself launches uvicorn/granian and is
not exercised here — only the CLI surface (help text + defaults) is
contract-tested via ``typer.testing.CliRunner``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

if TYPE_CHECKING:
    from fastblocks.cli import FastblocksCLI


@pytest.fixture
def cli_app(tmp_path, monkeypatch: pytest.MonkeyPatch) -> "FastblocksCLI":
    """Import ``fastblocks.cli`` from a non-repo CWD.

    ``fastblocks/cli.py`` raises ``SystemExit`` at module load if
    ``Path.cwd() == the fastblocks repo directory``. chdir to
    ``tmp_path`` before importing so the module loads cleanly.
    """
    monkeypatch.chdir(tmp_path)
    from fastblocks.cli import cli

    return cli


@pytest.fixture
def runner() -> CliRunner:
    """CliRunner for invoking the typer app."""
    return CliRunner()


def test_run_help(cli_app: "FastblocksCLI", runner: CliRunner) -> None:
    """``fastblocks run --help`` exits 0 and surfaces the run docstring."""
    result = runner.invoke(cli_app, ["run", "--help"])
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "Run the FastBlocks app" in result.output


def test_run_default_args(cli_app: "FastblocksCLI", runner: CliRunner) -> None:
    """``fastblocks run --help`` advertises the documented defaults.

    Pinned defaults: host ``127.0.0.1``, port ``8000``,
    app_module ``main:app``. The starter README points users at
    ``uv run fastblocks run`` and depends on these defaults.
    """
    result = runner.invoke(cli_app, ["run", "--help"])
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "127.0.0.1" in result.output
    assert "8000" in result.output
    assert "main:app" in result.output