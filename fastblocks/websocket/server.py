"""WebSocket server for Fastblocks UI update streams.

Broadcasts real-time events for:
- UI component updates and rendering
- State management changes
- Application lifecycle events
- Component interaction events
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, UTC
from typing import Any, Optional

from mcp_common.websocket import (
    MessageType,
    WebSocketMessage,
    WebSocketProtocol,
    WebSocketServer,
)

# Import EventTypes from protocol module
from mcp_common.websocket.protocol import EventTypes

# Import authentication
from fastblocks.websocket.auth import get_authenticator

logger = logging.getLogger(__name__)


class FastblocksWebSocketServer(WebSocketServer):
    """WebSocket server for Fastblocks UI update streams.

    Broadcasts real-time events for:
    - UI component render events
    - State management changes
    - Application lifecycle events
    - Component interaction events

    Channels:
    - ui:{component_id} - Component-specific UI events
    - component:{id} - Component lifecycle events
    - state - State management events
    - global - System-wide events

    Attributes:
        host: Server host address
        port: Server port number (default: 8684)

    Example:
        >>> from fastblocks.websocket import FastblocksWebSocketServer
        >>>
        >>> server = FastblocksWebSocketServer()
        >>> await server.start()

    With TLS:
        >>> server = FastblocksWebSocketServer(
        ...     cert_file="/path/to/cert.pem",
        ...     key_file="/path/to/key.pem"
        ... )
        >>> await server.start()
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8684,
        max_connections: int = 100,
        message_rate_limit: int = 60,
        require_auth: bool = False,
        # TLS parameters
        ssl_context: Any = None,
        cert_file: str | None = None,
        key_file: str | None = None,
        ca_file: str | None = None,
        tls_enabled: bool = False,
        verify_client: bool = False,
        auto_cert: bool = False,
        # Metrics parameters
        enable_metrics: bool = False,
        metrics_port: int = 9096,
    ):
        """Initialize Fastblocks WebSocket server.

        Args:
            host: Server host address (default: "127.0.0.1")
            port: Server port number (default: 8684)
            max_connections: Maximum concurrent connections (default: 100)
            message_rate_limit: Messages per second per connection (default: 60)
            require_auth: Require JWT authentication for connections
            ssl_context: Pre-configured SSL context
            cert_file: Path to TLS certificate file (PEM format)
            key_file: Path to TLS private key file (PEM format)
            ca_file: Path to CA file for client verification
            tls_enabled: Enable TLS (generates self-signed cert if no cert provided)
            verify_client: Verify client certificates
            auto_cert: Auto-generate self-signed certificate for development
            enable_metrics: Enable Prometheus metrics collection
            metrics_port: Port for Prometheus metrics server (default: 9096)
        """
        authenticator = get_authenticator()

        super().__init__(
            host=host,
            port=port,
            max_connections=max_connections,
            message_rate_limit=message_rate_limit,
            authenticator=authenticator,
            require_auth=require_auth,
            ssl_context=ssl_context,
            cert_file=cert_file,
            key_file=key_file,
            ca_file=ca_file,
            tls_enabled=tls_enabled,
            verify_client=verify_client,
            auto_cert=auto_cert,
            server_name="fastblocks",
            enable_metrics=enable_metrics,
            metrics_port=metrics_port,
        )

        tls_mode = "WSS" if tls_enabled or ssl_context else "WS"
        logger.info(
            f"FastblocksWebSocketServer initialized: {host}:{port} ({tls_mode})"
        )

    async def leave_all_rooms(self, connection_id: str) -> None:
        """Remove connection from all rooms.

        Args:
            connection_id: Connection identifier
        """
        # Remove from room_connections tracking
        if connection_id in self.room_connections:
            room_id = self.room_connections[connection_id]
            await self.leave_room(room_id, connection_id)

        # Also check connection_rooms for any lingering references
        for room_id, connections in list(self.connection_rooms.items()):
            if connection_id in connections:
                connections.discard(connection_id)

    async def on_connect(self, websocket: Any, connection_id: str) -> None:
        """Handle new WebSocket connection.

        Args:
            websocket: WebSocket connection object
            connection_id: Unique connection identifier
        """
        user = getattr(websocket, "user", None)
        user_id = user.get("user_id") if user else "anonymous"

        tls_mode = "WSS" if self.ssl_context else "WS"
        logger.info(
            f"Client connected: {connection_id} (user: {user_id}, mode: {tls_mode})"
        )

        # Send welcome message
        welcome = WebSocketProtocol.create_event(
            EventTypes.SESSION_CREATED,
            {
                "connection_id": connection_id,
                "server": "fastblocks",
                "message": "Connected to Fastblocks UI update stream",
                "authenticated": user is not None,
                "tls_mode": tls_mode,
            },
        )
        await websocket.send(WebSocketProtocol.encode(welcome))

    async def on_disconnect(self, websocket: Any, connection_id: str) -> None:
        """Handle WebSocket disconnection.

        Args:
            websocket: WebSocket connection object
            connection_id: Unique connection identifier
        """
        logger.info(f"Client disconnected: {connection_id}")
        await self.leave_all_rooms(connection_id)

    async def on_message(self, websocket: Any, message: WebSocketMessage) -> None:
        """Handle incoming WebSocket message.

        Args:
            websocket: WebSocket connection object
            message: Decoded message
        """
        if message.type == MessageType.REQUEST:
            await self._handle_request(websocket, message)
        elif message.type == MessageType.EVENT:
            await self._handle_event(websocket, message)
        else:
            logger.warning(f"Unhandled message type: {message.type}")

    async def _handle_request(
        self, websocket: Any, message: WebSocketMessage
    ) -> None:
        """Handle request message (expects response).

        Args:
            websocket: WebSocket connection object
            message: Request message
        """
        # Get authenticated user from connection
        user = getattr(websocket, "user", None)

        if message.event == "subscribe":
            channel = message.data.get("channel")

            # Check authorization for this channel
            if user and not self._can_subscribe_to_channel(user, channel):
                error = WebSocketProtocol.create_error(
                    error_code="FORBIDDEN",
                    error_message=f"Not authorized to subscribe to {channel}",
                    correlation_id=message.correlation_id,
                )
                await websocket.send(WebSocketProtocol.encode(error))
                return

            if channel:
                connection_id = getattr(websocket, "id", str(uuid.uuid4()))
                await self.join_room(channel, connection_id)

                response = WebSocketProtocol.create_response(
                    message,
                    {"status": "subscribed", "channel": channel}
                )
                await websocket.send(WebSocketProtocol.encode(response))

        elif message.event == "unsubscribe":
            channel = message.data.get("channel")
            if channel:
                connection_id = getattr(websocket, "id", str(uuid.uuid4()))
                await self.leave_room(channel, connection_id)

                response = WebSocketProtocol.create_response(
                    message,
                    {"status": "unsubscribed", "channel": channel}
                )
                await websocket.send(WebSocketProtocol.encode(response))

        elif message.event == "get_component_status":
            component_id = message.data.get("component_id")
            if component_id:
                status = await self._get_component_status(component_id)
                response = WebSocketProtocol.create_response(message, status)
                await websocket.send(WebSocketProtocol.encode(response))

        elif message.event == "get_state":
            state_path = message.data.get("state_path")
            if state_path:
                state_value = await self._get_state(state_path)
                response = WebSocketProtocol.create_response(message, state_value)
                await websocket.send(WebSocketProtocol.encode(response))

        else:
            error = WebSocketProtocol.create_error(
                error_code="UNKNOWN_REQUEST",
                error_message=f"Unknown request event: {message.event}",
                correlation_id=message.correlation_id,
            )
            await websocket.send(WebSocketProtocol.encode(error))

    async def _handle_event(self, websocket: Any, message: WebSocketMessage) -> None:
        """Handle event message (no response expected).

        Args:
            websocket: WebSocket connection object
            message: Event message
        """
        logger.debug(f"Received client event: {message.event}")

    def _can_subscribe_to_channel(self, user: dict[str, Any], channel: str) -> bool:
        """Check if user can subscribe to channel.

        Args:
            user: User payload from JWT
            channel: Channel name

        Returns:
            True if authorized, False otherwise
        """
        permissions = user.get("permissions", [])

        # Admin can subscribe to any channel
        if "fastblocks:admin" in permissions:
            return True

        # Check channel-specific permissions
        if channel.startswith("ui:"):
            return "fastblocks:read" in permissions

        if channel.startswith("component:"):
            return "fastblocks:read" in permissions

        if channel.startswith("state"):
            return "fastblocks:read" in permissions

        # Default: deny
        return False

    async def _get_component_status(self, component_id: str) -> dict[str, Any]:
        """Get component status.

        Args:
            component_id: Component identifier

        Returns:
            Component status dictionary
        """
        # In a real implementation, this would query the application state
        return {
            "component_id": component_id,
            "status": "active",
            "timestamp": self._get_timestamp(),
        }

    async def _get_state(self, state_path: str) -> dict[str, Any]:
        """Get state value.

        Args:
            state_path: State path (e.g., "user.preferences.theme")

        Returns:
            State value dictionary
        """
        # In a real implementation, this would query the state manager
        return {
            "state_path": state_path,
            "value": None,
            "timestamp": self._get_timestamp(),
        }

    # Broadcast methods for UI events

    async def broadcast_ui_updated(
        self, component_id: str, metadata: dict[str, Any]
    ) -> None:
        """Broadcast UI component update event.

        Args:
            component_id: Component identifier
            metadata: Update metadata (changes, timestamp, etc.)
        """
        event = WebSocketProtocol.create_event(
            "ui.updated",
            {
                "component_id": component_id,
                "timestamp": self._get_timestamp(),
                **metadata
            },
            room=f"ui:{component_id}"
        )
        await self.broadcast_to_room(f"ui:{component_id}", event)

    async def broadcast_component_rendered(
        self, component_id: str, render_info: dict[str, Any]
    ) -> None:
        """Broadcast component render event.

        Args:
            component_id: Component identifier
            render_info: Render information (HTML, timing, etc.)
        """
        event = WebSocketProtocol.create_event(
            "component.rendered",
            {
                "component_id": component_id,
                "timestamp": self._get_timestamp(),
                **render_info
            },
            room=f"component:{component_id}"
        )
        await self.broadcast_to_room(f"component:{component_id}", event)

    async def broadcast_state_changed(
        self, state_path: str, new_value: Any
    ) -> None:
        """Broadcast state change event.

        Args:
            state_path: State path (e.g., "user.preferences.theme")
            new_value: New state value
        """
        event = WebSocketProtocol.create_event(
            "state.changed",
            {
                "state_path": state_path,
                "new_value": new_value,
                "timestamp": self._get_timestamp(),
            },
            room="state"
        )
        await self.broadcast_to_room("state", event)

    def _get_timestamp(self) -> str:
        """Get current ISO timestamp.

        Returns:
            ISO 8601 formatted timestamp
        """
        return datetime.now(UTC).isoformat()
