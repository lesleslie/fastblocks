"""Phase 2 mechanical-four Commit4 — Scenario 5 regression.

Typer's auto-validation rejects --style with a value not in the
Literal. Phase 2 pins this behavior so future regressions in Typer
or our annotation are caught here.
"""
from __future__ import annotations

import pytest
from typer.testing import CliRunner
from fastblocks.cli import cli


@pytest.mark.unit
def test_typer_rejects_invalid_style_literal() -> None:
    """--style kelp is rejected with non-zero exit and the value named."""
    runner = CliRunner()
    result = runner.invoke(cli, ["create", "app", "myapp", "--style", "kelp"])
    assert result.exit_code != 0, (
        f"Expected non-zero exit for --style kelp; got {result.exit_code}. "
        f"Output: {result.output!r}"
    )
    combined = (result.output or "") + (result.stderr or "")
    assert "kelp" in combined, (
        f"Expected 'kelp' in error output; got: {combined!r}"
    )
