"""Unit tests for FastBlocks MCP package entry point."""

import asyncio
import sys
import types

import pytest


def _make_stub_mcp_server() -> types.ModuleType:
    """Create a stub module for fastblocks.mcp.server with async factory/start."""
    stub = types.ModuleType("fastblocks.mcp.server")

    class _Server:
        async def start(self) -> None:
            return None

    async def _factory() -> _Server:
        return _Server()

    setattr(stub, "create_fastblocks_mcp_server", _factory)
    return stub


@pytest.mark.unit
def test_mcp_dunder_main_invokes_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Executing `python -m fastblocks.mcp` should exit with code 0 on success."""
    # Provide server stub
    monkeypatch.setitem(sys.modules, "fastblocks.mcp.server", _make_stub_mcp_server())

    # Capture sys.exit without exiting the test runner
    exit_calls = []

    def _fake_exit(code: int) -> None:
        exit_calls.append(code)

    monkeypatch.setattr(sys, "exit", _fake_exit)

    # Execute the module as if it were run as a script
    import runpy

    runpy.run_module("fastblocks.mcp.__main__", run_name="__main__")

    assert exit_calls and exit_calls[-1] == 0


@pytest.mark.unit
def test_mcp_main_handles_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """`main()` returns 1 when server creation fails with an error."""
    # Create stub that raises a generic exception
    exc_stub = types.ModuleType("fastblocks.mcp.server")

    async def _raise() -> None:  # type: ignore[return-type]
        raise RuntimeError("boom")

    setattr(exc_stub, "create_fastblocks_mcp_server", _raise)
    monkeypatch.setitem(sys.modules, "fastblocks.mcp.server", exc_stub)

    # Import the module and run main()
    from fastblocks.mcp.__main__ import main

    rc = asyncio.run(main())
    assert rc == 1


@pytest.mark.unit
def test_mcp_main_handles_keyboard_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    """`main()` returns 0 when KeyboardInterrupt is raised."""
    ki_stub = types.ModuleType("fastblocks.mcp.server")

    async def _raise_ki() -> None:  # type: ignore[return-type]
        raise KeyboardInterrupt()

    setattr(ki_stub, "create_fastblocks_mcp_server", _raise_ki)
    monkeypatch.setitem(sys.modules, "fastblocks.mcp.server", ki_stub)

    from fastblocks.mcp.__main__ import main

    rc = asyncio.run(main())
    assert rc == 0
