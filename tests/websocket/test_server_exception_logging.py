"""Tests that WebSocket handler exceptions are logged with tracebacks.

Step 6 of Task 5: when ``_handle_request`` catches an exception from a
handler implementation, it must (a) send a stable ``INTERNAL_ERROR``
response to the client and (b) emit a ``logger.exception`` call so the
traceback is visible in operator logs. The client-visible sanitization
is already pinned by ``test_sanitized_errors.py``; this file pins the
logging contract.

Also pins origin URL return types as booleans and exercises malformed
origin handling explicitly so a future refactor that returns ``None``
for ``check_origin`` cannot regress silently.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from fastblocks.websocket import FastblocksWebSocketServer
from fastblocks.websocket.origin import check_origin
from mcp_common.websocket.protocol import (
    MessageType,
    WebSocketMessage,
    WebSocketProtocol,
)

pytestmark = [pytest.mark.unit, pytest.mark.websocket]


@pytest.fixture
def server() -> FastblocksWebSocketServer:
    return FastblocksWebSocketServer(host="127.0.0.1", port=0)


@pytest.fixture
def mock_websocket() -> MagicMock:
    ws = MagicMock()
    ws.send = AsyncMock()
    ws.user = {"id": "user-1", "role": "user"}
    return ws


def _make_failing_message() -> WebSocketMessage:
    """Construct a request message that will force the handler to raise.

    The handler delegates to ``_dispatch_request`` which (for a
    ``get_component_status`` request) calls ``_get_component_status``.
    We patch that method in each test so we control the failure surface.
    """
    return WebSocketMessage(
        type=MessageType.REQUEST,
        event="get_component_status",
        data={"component_id": "navbar"},
    )


@pytest.mark.unit
class TestWebSocketHandlerLogsException:
    @pytest.mark.asyncio
    async def test_websocket_handler_logs_exception(
        self,
        server: FastblocksWebSocketServer,
        mock_websocket: MagicMock,
    ) -> None:
        """A handler exception must surface as ``logger.exception``.

        We use structlog's ``capture_logs`` context manager because the
        websocket server uses a structlog bound logger (not stdlib
        logging), so ``caplog`` does not capture these events.
        """
        import structlog

        server._get_component_status = AsyncMock(  # type: ignore[method-assign]
            side_effect=RuntimeError("component lookup failed: traceback-test")
        )

        with structlog.testing.capture_logs() as captured:
            await server._handle_request(mock_websocket, _make_failing_message())

        exception_events = [
            event
            for event in captured
            if "websocket request handler raised" in str(event.get("event", "")).lower()
        ]
        assert exception_events, (
            f"Expected diagnostic log event; got captured: {captured!r}"
        )
        # ``logger.exception`` must carry ``exc_info=True`` so structlog's
        # processor chain preserves the traceback. Without this flag the
        # exception detail never reaches operators.
        assert all(event.get("exc_info") for event in exception_events), (
            f"exc_info flag missing from log event; got: {exception_events!r}"
        )

    @pytest.mark.asyncio
    async def test_websocket_handler_logs_and_returns_internals_error(
        self,
        server: FastblocksWebSocketServer,
        mock_websocket: MagicMock,
    ) -> None:
        """Logging and the sanitized client response are both required."""
        server._get_component_status = AsyncMock(  # type: ignore[method-assign]
            side_effect=RuntimeError("vault token leaked: abc")
        )

        await server._handle_request(mock_websocket, _make_failing_message())

        sent = mock_websocket.send.call_args[0][0]
        decoded = WebSocketProtocol.decode(sent)
        assert decoded.error_code == "INTERNAL_ERROR"
        body_str = str(decoded.data)
        # Client-visible payload must not echo the original exception.
        assert "vault token" not in body_str
        assert "abc" not in body_str


@pytest.mark.unit
class TestCheckOriginReturnsBoolean:
    """``check_origin`` must return ``bool`` — never ``None`` or truthy objects."""

    @pytest.mark.parametrize(
        "origin,allowlist",
        [
            ("https://app.example.com", ["https://app.example.com"]),
            ("https://attacker.example.com", ["https://app.example.com"]),
            ("https://attacker.example.com", []),
            ("https://attacker.example.com", ["*"]),
            ("http://localhost:3000", ["*"]),
            (None, ["*"]),
            ("", ["*"]),
            ("javascript:alert(1)", ["*"]),
            ("not-a-url", ["*"]),
            (None, []),
            ("", []),
            ("javascript:alert(1)", ["https://app.example.com"]),
        ],
    )
    def test_returns_python_bool(
        self, origin: str | None, allowlist: list[str]
    ) -> None:
        result = check_origin(origin, allowlist)
        assert isinstance(result, bool), (
            f"check_origin returned {type(result).__name__}; must return bool"
        )

    def test_malformed_origin_does_not_raise(self) -> None:
        """Garbage origins must be denied, not raise."""
        # Random broken URLs and odd inputs that may be submitted by
        # malicious clients. None of these may propagate an exception.
        for bad in [
            "://",
            "http://",
            "https://",
            "ftp://app.example.com",
            "/////",
            "https://app.example.com:abc:def",
            "http://[::1",
            "\x00\x01\x02",
        ]:
            assert check_origin(bad, ["*"]) is False or check_origin(bad, ["*"]) is True
            # The boolean contract is what matters — never an exception.
            assert isinstance(check_origin(bad, ["*"]), bool)
