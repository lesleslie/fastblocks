"""Tests for FastblocksCLI inheriting from OneiricCLIBase."""

from __future__ import annotations

import json as jsonlib
import re

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_app(tmp_path, monkeypatch):
    """Import fastblocks.cli from a non-repo CWD.

    fastblocks/cli.py raises SystemExit at module load if
    Path.cwd() == the fastblocks repo directory. chdir to tmp_path
    before importing so the module loads cleanly.

    Note: typer.testing.CliRunner is required (not click.testing.CliRunner)
    because typer.Typer is *not* a click.Command subclass; only the
    typer runner resolves typer.Typer apps into click Commands via
    ``_get_command(app)`` before invoking them.
    """
    monkeypatch.chdir(tmp_path)
    from fastblocks.cli import cli
    return cli


def test_help_lists_standard_commands(cli_app):
    runner = CliRunner()
    result = runner.invoke(cli_app, ["--help"])
    assert result.exit_code == 0
    assert "version" in result.output
    assert "doctor" in result.output
    assert "health" in result.output


def test_json_flag_is_global(cli_app):
    runner = CliRunner()
    result = runner.invoke(cli_app, ["--help"])
    # Rich renders ANSI escapes; strip them before substring search.
    clean = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--json" in clean


def test_version_command_runs(cli_app):
    # OneiricCLIBase caches ``component_version`` at ``__init__`` time, and
    # the cli module is imported once per pytest session so the fixture's
    # `from fastblocks.cli import cli` returns the cached instance.
    # Patch the cached value directly to assert the version subcommand
    # formats ``component_name`` + ``component_version`` correctly.
    cli_app.component_version = "1.2.3"
    runner = CliRunner()
    result = runner.invoke(cli_app, ["version"])
    assert result.exit_code == 0
    assert "fastblocks: 1.2.3" in result.output


def test_doctor_returns_specific_real_checks(cli_app):
    """OneiricCLIBase contract: _doctor_checks must return real data per check name.

    Spec requires CI to assert real data, not {}. A passing assertion
    of just `:` in output is too weak — pin each registered check.
    """
    runner = CliRunner()
    result = runner.invoke(cli_app, ["doctor"])
    assert result.exit_code == 0
    for check_name in ("python", "typer", "oneiric"):
        assert f"{check_name}:" in result.output, (
            f"expected check {check_name!r} in doctor output, got: {result.output!r}"
        )


def test_doctor_emits_json(cli_app):
    runner = CliRunner()
    result = runner.invoke(cli_app, ["--json", "doctor"])
    assert result.exit_code == 0
    payload = jsonlib.loads(result.output)
    assert "checks" in payload
    assert set(payload["checks"]) >= {"python", "typer", "oneiric"}