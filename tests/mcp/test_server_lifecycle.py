"""Wave D coverage backfill for fastblocks/mcp/server.py.

Targets the previously-uncovered statements in ``FastBlocksMCPServer.start``
(lines 149-170) and ``FastBlocksMCPServer.stop`` (lines 174-187). Both
methods are pure orchestration over an injected ``_server`` attribute
so the tests construct a ``FastBlocksMCPServer`` directly and swap in
a MagicMock transport.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastblocks.mcp.server import FastBlocksMCPServer


def _make_server_with_transport() -> tuple[FastBlocksMCPServer, MagicMock]:
    """Construct a server whose ``_server`` is an async-transport mock."""
    server = FastBlocksMCPServer(name="test", version="0.0.0")
    transport = MagicMock()
    transport.run = AsyncMock()
    transport.stop = AsyncMock()
    server._server = transport
    server._initialized = True
    return server, transport


@pytest.mark.unit
class TestStartMethod:
    """Cover FastBlocksMCPServer.start (lines 147-170)."""

    async def test_start_calls_server_run_when_initialized(self) -> None:
        server, transport = _make_server_with_transport()
        await server.start()
        transport.run.assert_awaited_once()

    async def test_start_returns_when_server_is_none(self) -> None:
        # _initialized=True but _server=None triggers the early-return path
        server = FastBlocksMCPServer()
        server._initialized = True
        server._server = None
        # Should not raise; ``logger.warning`` is silently tolerated.
        await server.start()

    async def test_start_initializes_if_not_yet_initialized(self) -> None:
        server = FastBlocksMCPServer()
        server._initialized = False
        server._server = None

        # Stub initialize() to flip _initialized and set _server.
        async def _fake_initialize() -> None:
            server._initialized = True
            transport = MagicMock()
            transport.run = AsyncMock()
            server._server = transport

        server.initialize = _fake_initialize  # type: ignore[method-assign]
        await server.start()
        assert server._server is not None
        server._server.run.assert_awaited_once()

    async def test_start_propagates_server_run_errors(self) -> None:
        server, transport = _make_server_with_transport()
        transport.run = AsyncMock(side_effect=RuntimeError("transport down"))
        with pytest.raises(RuntimeError, match="transport down"):
            await server.start()


@pytest.mark.unit
class TestStopMethod:
    """Cover FastBlocksMCPServer.stop (lines 172-187)."""

    async def test_stop_calls_server_stop_when_initialized(self) -> None:
        server, transport = _make_server_with_transport()
        await server.stop()
        transport.stop.assert_awaited_once()

    async def test_stop_returns_when_server_is_none(self) -> None:
        server = FastBlocksMCPServer()
        server._server = None
        # No-op path; the early-return on line 175.
        await server.stop()

    async def test_stop_swallows_transport_errors(self) -> None:
        server, transport = _make_server_with_transport()
        transport.stop = AsyncMock(side_effect=RuntimeError("transport down"))
        # The except block logs and does NOT re-raise.
        await server.stop()


@pytest.mark.unit
class TestRegisterToolsPrecondition:
    """Cover the RuntimeError branch in _register_tools (line 105).

    The branch fires if someone calls _register_tools before
    ``_server`` has been created. We invoke the method directly on a
    fresh instance.
    """

    async def test_register_tools_raises_when_server_is_none(self) -> None:
        server = FastBlocksMCPServer()
        server._server = None
        with pytest.raises(RuntimeError, match="not initialized"):
            await server._register_tools()
