"""Tests for sanitized WebSocket error responses.

Phase 1.1.d: the server must not echo the raw ``str(e)`` of an
internal exception back to the client. Instead, the client gets a
stable error code (``"internal_error"``) and the actual exception is
logged server-side. The original exception detail never crosses the
trust boundary.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from fastblocks.websocket import FastblocksWebSocketServer
from mcp_common.websocket.protocol import (
    MessageType,
    WebSocketMessage,
    WebSocketProtocol,
)

# This module imports directly from mcp_common.websocket.protocol
# (the stub provided by tests/conftest.py) and also constructs a
# FastblocksWebSocketServer (which transitively requires the stub).
pytestmark = [pytest.mark.unit, pytest.mark.websocket]


def _decode_last_send(mock_websocket: MagicMock) -> object:
    """Decode the last message the mock server sent."""
    sent = mock_websocket.send.call_args[0][0]
    return WebSocketProtocol.decode(sent)


@pytest.mark.unit
class TestSanitizedErrorResponses:
    @pytest.fixture
    def server(self) -> FastblocksWebSocketServer:
        return FastblocksWebSocketServer(host="127.0.0.1", port=0)

    @pytest.fixture
    def mock_websocket(self) -> MagicMock:
        ws = MagicMock()
        ws.send = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_subscribe_error_does_not_echo_internal_exception(
        self, server: FastblocksWebSocketServer, mock_websocket: MagicMock
    ) -> None:
        """A server-side exception must surface as a stable code, not str(e)."""
        # Patch join_room to raise on call so the handler's except branch
        # fires and the current behaviour is to echo str(e).
        server.join_room = AsyncMock(  # type: ignore[method-assign]
            side_effect=RuntimeError("database password=hunter2 exploded")
        )
        message = WebSocketMessage(
            type=MessageType.REQUEST,
            event="subscribe",
            data={"channel": "component:navbar"},
        )
        # Bypass the auth check.
        mock_websocket.user = {"id": "user-1", "role": "user"}
        server._can_subscribe_to_channel = MagicMock(return_value=True)  # type: ignore[method-assign]

        await server._handle_request(mock_websocket, message, "conn-1")

        decoded = _decode_last_send(mock_websocket)
        body_str = str(decoded.data)
        assert "hunter2" not in body_str, (
            "Server leaked internal exception text in the error response"
        )
        assert "database password" not in body_str
        # Stable, non-revealing code
        assert decoded.error_code == "INTERNAL_ERROR"

    @pytest.mark.asyncio
    async def test_request_error_does_not_echo_internal_exception(
        self, server: FastblocksWebSocketServer, mock_websocket: MagicMock
    ) -> None:
        """Same guarantee for the request handler."""
        # Patch the response helper to raise mid-dispatch. The handler
        # unconditionally calls WebSocketProtocol.create_response on
        # the success path, so this patch is guaranteed to fire.
        from mcp_common.websocket import protocol

        original_create_response = protocol.WebSocketProtocol.create_response
        protocol.WebSocketProtocol.create_response = MagicMock(  # type: ignore[method-assign]
            side_effect=RuntimeError("vault token=abc leaked")
        )
        message = WebSocketMessage(
            type=MessageType.REQUEST,
            event="get_component_status",
            data={"component_id": "navbar"},
        )

        try:
            await server._handle_request(mock_websocket, message, "conn-1")
        finally:
            protocol.WebSocketProtocol.create_response = original_create_response

        decoded = _decode_last_send(mock_websocket)
        body_str = str(decoded.data)
        assert "vault token" not in body_str
        assert "abc" not in body_str
        assert decoded.error_code == "INTERNAL_ERROR"


def _raises_in_subscribe(
    server: FastblocksWebSocketServer, message: WebSocketMessage
) -> bool:
    """Quickly check whether a message would actually raise."""
    import asyncio

    async def probe() -> None:
        ws = MagicMock()
        ws.send = AsyncMock()
        try:
            await server._handle_subscribe(ws, message, "probe")
        except Exception:
            return

    try:
        asyncio.run(probe())
    except Exception:
        return True
    return False
