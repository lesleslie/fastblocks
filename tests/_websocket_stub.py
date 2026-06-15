"""Minimal mcp_common.websocket stub for pytest.

Registers a lightweight ``mcp_common.websocket`` package in ``sys.modules``
so fastblocks websocket tests can import from it at collection time without
needing the real mcp-common package installed in the test venv.
"""
from __future__ import annotations

import sys
import typing as t
from types import ModuleType


class _StubWebSocketAuthenticator:
    """Minimal stand-in for ``mcp_common.websocket.auth.WebSocketAuthenticator``.

    Implements just enough of the surface that ``fastblocks.websocket.auth``
    uses: ``create_token(payload)`` returns a 3-segment JWT-shaped string,
    ``verify_token(token)`` round-trips it back. The secret is bound at
    construction time, mirroring the real class.
    """

    def __init__(
        self,
        secret: str,
        algorithm: str = "HS256",
        token_expiry: int = 3600,
    ) -> None:
        self.secret = secret
        self.algorithm = algorithm
        self.token_expiry = token_expiry

    def create_token(self, payload: dict[str, t.Any]) -> str:
        """Return a JWT-shaped token (header.payload.signature)."""
        import base64
        import hashlib
        import hmac
        import json

        header = base64.urlsafe_b64encode(
            json.dumps({"alg": self.algorithm, "typ": "JWT"}).encode()
        ).rstrip(b"=")
        body = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).rstrip(b"=")
        signing_input = header + b"." + body
        signature = base64.urlsafe_b64encode(
            hmac.new(
                self.secret.encode(), signing_input, hashlib.sha256
            ).digest()
        ).rstrip(b"=")
        return (signing_input + b"." + signature).decode()

    def verify_token(self, token: str) -> dict[str, t.Any] | None:
        """Round-trip a token created by ``create_token``."""
        import base64
        import hashlib
        import hmac
        import json

        try:
            header_b64, body_b64, sig_b64 = token.split(".")
        except ValueError:
            return None

        try:
            signing_input = header_b64.encode() + b"." + body_b64.encode()
            expected = base64.urlsafe_b64encode(
                hmac.new(
                    self.secret.encode(), signing_input, hashlib.sha256
                ).digest()
            ).rstrip(b"=")
            if not hmac.compare_digest(expected, sig_b64.encode()):
                return None
            pad = "=" * (-len(body_b64) % 4)
            payload_bytes = base64.urlsafe_b64decode(body_b64 + pad)
            result: dict[str, t.Any] = json.loads(payload_bytes)
            return result
        except (ValueError, json.JSONDecodeError):
            return None


class _StubEventTypes:
    """Enum-ish stub mirroring ``mcp_common.websocket.protocol.EventTypes``."""

    SESSION_CREATED = "session.created"
    SESSION_CLOSED = "session.closed"
    USER_CONNECTED = "user.connected"
    USER_DISCONNECTED = "user.disconnected"
    CHANNEL_SUBSCRIBED = "channel.subscribed"
    CHANNEL_UNSUBSCRIBED = "channel.unsubscribed"
    BROADCAST = "broadcast"


class _StubMessageType:
    REQUEST = "request"
    RESPONSE = "response"
    EVENT = "event"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


class _StubWebSocketMessage:
    """Lightweight data holder mirroring ``WebSocketMessage``."""

    def __init__(
        self,
        type: str,
        event: str,
        data: dict[str, t.Any] | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self.type = type
        self.event = event
        self.data = data or {}
        self.correlation_id = correlation_id
        self.error_code: str | None = None
        self.error_message: str | None = None


class _StubWebSocketProtocol:
    """Stand-in for ``mcp_common.websocket.protocol.WebSocketProtocol``."""

    @staticmethod
    def create_event(
        event: str,
        data: dict[str, t.Any] | None = None,
        room: str | None = None,
    ) -> dict[str, t.Any]:
        return {
            "type": _StubMessageType.EVENT,
            "event": event,
            "data": data or {},
            "room": room,
        }

    @staticmethod
    def create_response(
        request: _StubWebSocketMessage,
        data: dict[str, t.Any] | None = None,
    ) -> dict[str, t.Any]:
        return {
            "type": _StubMessageType.RESPONSE,
            "event": request.event,
            "data": data or {},
            "correlation_id": request.correlation_id,
        }

    @staticmethod
    def create_error(
        error_code: str,
        error_message: str,
        correlation_id: str | None = None,
    ) -> dict[str, t.Any]:
        return {
            "type": _StubMessageType.ERROR,
            "error_code": error_code,
            "error_message": error_message,
            "correlation_id": correlation_id,
        }

    @staticmethod
    def encode(message: dict[str, t.Any]) -> str:
        import json
        return json.dumps(message)

    @staticmethod
    def decode(raw: str) -> _StubWebSocketMessage:
        import json
        payload = json.loads(raw)
        msg = _StubWebSocketMessage(
            type=payload.get("type", ""),
            event=payload.get("event", ""),
            data=payload.get("data", {}),
            correlation_id=payload.get("correlation_id"),
        )
        msg.error_code = payload.get("error_code")
        msg.error_message = payload.get("error_message")
        return msg


class _StubWebSocketServer:
    """Stand-in for ``mcp_common.websocket.WebSocketServer``."""

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        self.host = kwargs.get("host", "127.0.0.1")
        self.port = kwargs.get("port", 8684)
        self.max_connections = kwargs.get("max_connections", 100)
        self.message_rate_limit = kwargs.get("message_rate_limit", 60)
        self.authenticator = kwargs.get("authenticator")
        self.require_auth = kwargs.get("require_auth", False)
        self.ssl_context = kwargs.get("ssl_context")
        self.cert_file = kwargs.get("cert_file")
        self.key_file = kwargs.get("key_file")
        self.ca_file = kwargs.get("ca_file")
        self.tls_enabled = kwargs.get("tls_enabled", False)
        self.verify_client = kwargs.get("verify_client", False)
        self.auto_cert = kwargs.get("auto_cert", False)
        self.server_name = kwargs.get("server_name", "stub")
        self.enable_metrics = kwargs.get("enable_metrics", False)
        self.metrics_port = kwargs.get("metrics_port", 9096)
        self.is_running = False
        self.tls_mode = "WS"
        self.server: t.Any = None
        self.connections: dict[str, t.Any] = {}
        self.connection_rooms: dict[str, set[str]] = {}
        self.room_connections: dict[str, str] = {}

    async def start(self) -> None:
        self.is_running = True

    async def stop(self) -> None:
        self.is_running = False

    async def join_room(self, room_id: str, connection_id: str) -> None:
        if room_id not in self.connection_rooms:
            self.connection_rooms[room_id] = set()
        self.connection_rooms[room_id].add(connection_id)
        self.room_connections[connection_id] = room_id

    async def leave_room(self, room_id: str, connection_id: str) -> None:
        if room_id in self.connection_rooms:
            self.connection_rooms[room_id].discard(connection_id)
        if connection_id in self.room_connections:
            del self.room_connections[connection_id]

    async def leave_all_rooms(self, connection_id: str) -> None:
        room_id = self.room_connections.pop(connection_id, None)
        if room_id and room_id in self.connection_rooms:
            self.connection_rooms[room_id].discard(connection_id)
        for conns in self.connection_rooms.values():
            conns.discard(connection_id)

    async def broadcast_to_room(
        self, room_id: str, event: dict[str, t.Any]
    ) -> None:
        import json

        for connection_id in list(self.connection_rooms.get(room_id, ())):
            ws = self.connections.get(connection_id)
            if ws is not None:
                await ws.send(json.dumps(event))


class _StubWebSocketClient:
    """Stand-in for ``mcp_common.websocket.WebSocketClient``."""

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        self.uri = kwargs.get("uri", "")
        self.token = kwargs.get("token")
        self.reconnect = kwargs.get("reconnect", True)
        self.is_connected = False
        self.is_authenticated = False

    async def connect(self) -> None:
        self.is_connected = True
        self.is_authenticated = bool(self.token) and self.token != "invalid-token"

    async def disconnect(self) -> None:
        self.is_connected = False
        self.is_authenticated = False


def _install_mcp_common_websocket_stub() -> None:
    """Register a minimal ``mcp_common.websocket`` package in ``sys.modules``.

    Idempotent. Safe to call from ``pytest_configure`` and from
    ``pytest_runtest_setup``; the latter is needed for the per-process
    worker isolation that xdist requires.
    """
    if "mcp_common" in sys.modules and "mcp_common.websocket" in sys.modules:
        return

    if "mcp_common" not in sys.modules:
        mcp_common_pkg = ModuleType("mcp_common")
        mcp_common_pkg.__path__ = []  # type: ignore[attr-defined]
        sys.modules["mcp_common"] = mcp_common_pkg

    websocket_pkg = ModuleType("mcp_common.websocket")
    websocket_pkg.__path__ = []  # type: ignore[attr-defined]
    websocket_pkg.MessageType = _StubMessageType
    websocket_pkg.WebSocketMessage = _StubWebSocketMessage
    websocket_pkg.WebSocketProtocol = _StubWebSocketProtocol
    websocket_pkg.WebSocketServer = _StubWebSocketServer
    websocket_pkg.WebSocketClient = _StubWebSocketClient
    sys.modules["mcp_common.websocket"] = websocket_pkg
    setattr(sys.modules["mcp_common"], "websocket", websocket_pkg)

    protocol_mod = ModuleType("mcp_common.websocket.protocol")
    protocol_mod.EventTypes = _StubEventTypes
    protocol_mod.WebSocketProtocol = _StubWebSocketProtocol
    protocol_mod.MessageType = _StubMessageType
    protocol_mod.WebSocketMessage = _StubWebSocketMessage
    sys.modules["mcp_common.websocket.protocol"] = protocol_mod
    setattr(websocket_pkg, "protocol", protocol_mod)

    auth_mod = ModuleType("mcp_common.websocket.auth")
    auth_mod.WebSocketAuthenticator = _StubWebSocketAuthenticator
    sys.modules["mcp_common.websocket.auth"] = auth_mod
    setattr(websocket_pkg, "auth", auth_mod)
