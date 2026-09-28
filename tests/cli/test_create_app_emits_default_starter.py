"""Verifies `fastblocks create-app` writes the new B1 starter.

The starter is the source of truth for REQ-P2-B1-001 through REQ-P2-B1-005.
This test invokes the CLI via typer's CliRunner (not via subprocess/uv) so it
runs inside the existing pytest environment and exercises the actual code path
the brief's contract test demands.

# req: REQ-P2-B1-001, REQ-P2-B1-002, REQ-P2-B1-003, REQ-P2-B1-004, REQ-P2-B1-005
"""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

# Tests live at /Users/les/Projects/fastblocks/tests/ (NOT fastblocks/tests/).
# The brief referenced the package-internal path; this is the actual
# repository test directory per `find . -type d -name tests`.


@pytest.fixture
def cli_app(tmp_path, monkeypatch):
    """Import fastblocks.cli from a non-repo CWD.

    fastblocks/cli.py freezes ``apps_path = Path.cwd()`` at module load. With
    pytest-xdist each worker imports the module exactly once at startup (in
    the repo CWD), so a later chdir does NOT update ``apps_path``. We
    monkeypatch the module-level ``apps_path`` directly to point at tmp_path.
    """
    monkeypatch.chdir(tmp_path)
    import fastblocks.cli as _cli_mod

    monkeypatch.setattr(_cli_mod, "apps_path", tmp_path)
    return _cli_mod.cli


@pytest.fixture
def runner() -> CliRunner:
    """CliRunner for invoking the typer app."""
    return CliRunner()


def test_create_app_emits_new_starter(
    cli_app, runner: CliRunner, tmp_path: Path
) -> None:
    """`fastblocks create-app` must scaffold from fastblocks/starters/default/."""
    target = tmp_path / "test-app"
    result = runner.invoke(
        cli_app,
        [
            "create",
            "app",
            "--app-name",
            "test-app",
            "--style",
            "fastblocks_ui",
            "--domain",
            "example.com",
        ],
    )
    assert result.exit_code == 0, result.stdout + result.stderr

    # REQ-P2-B1-005: starter tree emitted.
    assert (target / "pyproject.toml").exists()
    assert (target / "main.py").exists()
    assert (target / "routes" / "home.py").exists()
    assert (target / "routes" / "demo.py").exists()
    assert (target / "adapters" / "style.py").exists()
    assert (target / "settings" / "app.yaml").exists()
    assert (target / "templates" / "base.html").exists()


def test_create_app_substitutes_app_name_placeholder(
    cli_app, runner: CliRunner, tmp_path: Path
) -> None:
    """`{app_name}` placeholder must be substituted in filenames and contents."""
    target = tmp_path / "my-cool-app"
    result = runner.invoke(
        cli_app,
        [
            "create",
            "app",
            "--app-name",
            "my-cool-app",
            "--style",
            "fastblocks_ui",
            "--domain",
            "example.com",
        ],
    )
    assert result.exit_code == 0, result.stdout + result.stderr

    # Placeholder replaced in text files.
    pyproject = (target / "pyproject.toml").read_text()
    assert "{app_name}" not in pyproject
    assert "my-cool-app" in pyproject

    app_yaml = (target / "settings" / "app.yaml").read_text()
    assert "{app_name}" not in app_yaml
    assert "my-cool-app" in app_yaml

    envrc = (target / ".envrc").read_text()
    assert "{app_name}" not in envrc
    assert "my-cool-app" in envrc


def test_create_app_default_style_is_fastblocks_ui(
    cli_app, runner: CliRunner, tmp_path: Path
) -> None:
    """REQ-P2-B1-001: app.yaml must default to fastblocks_ui, NOT vanilla.

    Omit ``--style`` and ``--domain`` so this test exercises the CLI's actual
    defaults — passing either explicitly would defeat the assertion.
    """
    target = tmp_path / "style-app"
    result = runner.invoke(
        cli_app,
        [
            "create",
            "app",
            "--app-name",
            "style-app",
        ],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    app_yaml = (target / "settings" / "app.yaml").read_text()
    assert "fastblocks_ui" in app_yaml


def test_create_app_starter_has_no_acb_imports(
    cli_app, runner: CliRunner, tmp_path: Path
) -> None:
    """REQ-P2-B1-003: no acb imports anywhere in the scaffold."""
    import re

    target = tmp_path / "no-acb-app"
    result = runner.invoke(
        cli_app,
        [
            "create",
            "app",
            "--app-name",
            "no-acb-app",
            "--style",
            "fastblocks_ui",
            "--domain",
            "example.com",
        ],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    # Match Python import statements only (must be at line start, preceded by
    # whitespace) so docstrings/comments mentioning acb are not flagged.
    import_pattern = re.compile(r"(?m)^\s*(?:import acb\b|from acb\b)")
    for py in target.rglob("*.py"):
        text = py.read_text()
        match = import_pattern.search(text)
        assert not match, f"forbidden acb import in {py}: {match.group(0)!r}"


def test_create_app_starter_has_no_kelp_or_webawesome(
    cli_app, runner: CliRunner, tmp_path: Path
) -> None:
    """REQ-P2-B1-002: kelp / webawesome must not appear as legal style values."""
    import yaml

    target = tmp_path / "no-kelp-app"
    result = runner.invoke(
        cli_app,
        [
            "create",
            "app",
            "--app-name",
            "no-kelp-app",
            "--style",
            "fastblocks_ui",
            "--domain",
            "example.com",
        ],
    )
    assert result.exit_code == 0, result.stdout + result.stderr

    style_yaml = target / "settings" / "adapters" / "style.yaml"
    data = yaml.safe_load(style_yaml.read_text()) or {}
    style_block = data.get("adapters", {}).get("style", {}) if isinstance(data, dict) else {}
    available = style_block.get("available", []) if isinstance(style_block, dict) else []
    default_style = style_block.get("default") if isinstance(style_block, dict) else None
    for forbidden in ("kelp", "webawesome"):
        assert forbidden not in (available or []), (
            f"forbidden style {forbidden!r} listed in {style_yaml} available list"
        )
        assert default_style != forbidden, (
            f"forbidden style {forbidden!r} is the default in {style_yaml}"
        )

    # Also check app.yaml style field is not kelp/webawesome.
    app_yaml = target / "settings" / "app.yaml"
    app_data = yaml.safe_load(app_yaml.read_text()) or {}
    app_style = (
        app_data.get("app", {}).get("style") if isinstance(app_data, dict) else None
    )
    assert app_style not in ("kelp", "webawesome"), (
        f"forbidden style in {app_yaml}: {app_style!r}"
    )


def test_create_app_refuses_overwrite(
    cli_app, runner: CliRunner, tmp_path: Path
) -> None:
    """create_app must refuse to overwrite an existing target path."""
    target = tmp_path / "exists-app"
    target.mkdir()
    result = runner.invoke(
        cli_app,
        [
            "create",
            "app",
            "--app-name",
            "exists-app",
            "--style",
            "fastblocks_ui",
            "--domain",
            "example.com",
        ],
    )
    assert result.exit_code != 0
    assert "already exists" in (result.stdout + result.stderr)
