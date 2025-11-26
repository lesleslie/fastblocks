"""Unit test for the FastBlocks package entry point.

This test ensures that running `python -m fastblocks` (i.e. executing
`fastblocks.__main__`) properly invokes the CLI entry function.
"""

import runpy
import sys
import types
from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
def test_package_dunder_main_invokes_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    # Provide a lightweight stub for fastblocks.cli before loading __main__
    stub_cli_mod = types.ModuleType("fastblocks.cli")
    called = {"count": 0}

    def _cli() -> None:  # simple callable to track invocation
        called["count"] += 1

    # Attach the stub function under expected name
    setattr(stub_cli_mod, "cli", MagicMock(side_effect=_cli))

    # Ensure the real fastblocks.cli is replaced with our stub for this test
    monkeypatch.setitem(sys.modules, "fastblocks.cli", stub_cli_mod)

    # Execute the package's __main__ module as if via `python -m fastblocks`
    runpy.run_module("fastblocks.__main__", run_name="__main__")

    # Verify the CLI entry was invoked exactly once
    assert called["count"] == 1
