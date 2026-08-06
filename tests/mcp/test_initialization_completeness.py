"""Tests for MCP server initialization honesty.

Step 1 of Task 5: confirm that ``FastBlocksMCPServer.initialize()``
surfaces failures from ``_register_tools`` instead of swallowing them
with ``contextlib.suppress(Exception)``. A registration that raises
must propagate; the ``_initialized`` flag must stay ``False`` so
callers know the server is not safe to use.

The pytest environment stubs out ``mcp_common`` (see
``tests/_websocket_stub.py``), so ``mcp_common.cli`` is not present
unless we install it ourselves. We do so for these tests because
``FastBlocksMCPServer.initialize`` short-circuits on an ``ImportError``
from that path and never reaches the registration code we want to
exercise.
"""

from __future__ import annotations

import sys
import types
from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock

import pytest

pytestmark = [pytest.mark.unit]


@pytest.fixture
def stub_mcp_common_cli(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Install a stub ``mcp_common.cli`` with a working factory.

    The factory's ``create_server`` returns a ``MagicMock`` so
    ``FastBlocksMCPServer.initialize`` can proceed past the
    ``from mcp_common.cli import MCPServerCLIFactory`` import and reach
    the ``_register_tools`` / ``_register_resources`` calls under test.
    """
    if "mcp_common.cli" not in sys.modules:
        cli_module = types.ModuleType("mcp_common.cli")

        class _StubFactory:
            @staticmethod
            def create_server() -> Any:
                return MagicMock()

        cli_module.MCPServerCLIFactory = _StubFactory  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "mcp_common.cli", cli_module)
    yield


@pytest.mark.unit
class TestInitializationCompleteness:
    @pytest.mark.asyncio
    async def test_initialize_does_not_hide_registration_failure(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_mcp_common_cli: None,
    ) -> None:
        """A broken ``_register_tools`` must surface as a RuntimeError.

        Before the inner ``with suppress(Exception)`` was removed in
        ``FastBlocksMCPServer._register_tools``, the outer
        ``initialize`` caught it, logged ``logger.exception("Failed to
        initialize MCP server")``, and silently left ``_initialized``
        set to ``False``. That made every MCP initialization appear to
        succeed while actually registering zero tools. This test pins
        the fix.
        """
        from fastblocks.mcp.server import FastBlocksMCPServer

        server = FastBlocksMCPServer()

        async def broken_registration() -> None:
            raise RuntimeError("registration failed")

        monkeypatch.setattr(server, "_register_tools", broken_registration)

        with pytest.raises(RuntimeError, match="registration failed"):
            await server.initialize()

        assert server._initialized is False

    @pytest.mark.asyncio
    async def test_initialize_marks_initialized_false_on_registration_failure(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_mcp_common_cli: None,
    ) -> None:
        """Even when ``_register_resources`` is the failure point, the
        ``_initialized`` flag must stay ``False`` so callers do not
        assume the server is safe to start serving requests.
        """
        from fastblocks.mcp.server import FastBlocksMCPServer

        server = FastBlocksMCPServer()

        async def broken_resources() -> None:
            raise RuntimeError("resource registration failed")

        monkeypatch.setattr(server, "_register_resources", broken_resources)

        with pytest.raises(RuntimeError, match="resource registration failed"):
            await server.initialize()

        assert server._initialized is False
