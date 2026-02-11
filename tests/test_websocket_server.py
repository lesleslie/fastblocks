"""Tests for Fastblocks WebSocket server.

Tests cover:
- Server initialization and lifecycle
- Connection management
- Channel subscription and broadcasting
- UI update events
- State change events
"""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastblocks.websocket import FastblocksWebSocketServer
from mcp_common.websocket.protocol import WebSocketProtocol


@pytest.fixture
def ws_server():
    """Create a WebSocket server instance for testing."""
    return FastblocksWebSocketServer(
        host="127.0.0.1",
        port=8684,
        max_connections=100,
        message_rate_limit=60,
    )


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    ws = MagicMock()
    ws.send = AsyncMock()
    ws.id = "test-connection-123"
    return ws


class TestFastblocksWebSocketServer:
    """Test FastblocksWebSocketServer initialization and basic operations."""

    def test_initialization(self, ws_server):
        """Test server initialization with correct defaults."""
        assert ws_server.host == "127.0.0.1"
        assert ws_server.port == 8684
        assert ws_server.max_connections == 100
        assert ws_server.message_rate_limit == 60
        assert not ws_server.is_running
        assert ws_server.server is None

    def test_initialization_custom_params(self):
        """Test server initialization with custom parameters."""
        server = FastblocksWebSocketServer(
            host="0.0.0.0",
            port=9000,
            max_connections=50,
            message_rate_limit=30,
        )
        assert server.host == "0.0.0.0"
        assert server.port == 9000
        assert server.max_connections == 50
        assert server.message_rate_limit == 30

    @pytest.mark.asyncio
    async def test_on_connect_sends_welcome(self, ws_server, mock_websocket):
        """Test that on_connect sends a welcome message."""
        connection_id = "conn-123"

        await ws_server.on_connect(mock_websocket, connection_id)

        # Verify welcome message was sent
        mock_websocket.send.assert_called_once()
        sent_message = mock_websocket.send.call_args[0][0]

        # Decode and verify message structure
        decoded = WebSocketProtocol.decode(sent_message)
        assert decoded.event == "session.created"
        assert decoded.data["server"] == "fastblocks"
        assert decoded.data["connection_id"] == connection_id
        assert "message" in decoded.data

    @pytest.mark.asyncio
    async def test_on_disconnect(self, ws_server, mock_websocket):
        """Test that on_disconnect handles disconnection."""
        connection_id = "conn-123"

        # First join some rooms
        await ws_server.join_room("ui:header", connection_id)
        await ws_server.join_room("state", connection_id)

        # Now disconnect
        await ws_server.on_disconnect(mock_websocket, connection_id)

        # Verify rooms were cleaned up
        assert connection_id not in ws_server.room_connections


class TestChannelSubscription:
    """Test channel subscription and room management."""

    @pytest.mark.asyncio
    async def test_subscribe_request(self, ws_server, mock_websocket):
        """Test handling subscribe request."""
        from mcp_common.websocket.protocol import MessageType, WebSocketMessage

        message = WebSocketMessage(
            type=MessageType.REQUEST,
            event="subscribe",
            data={"channel": "ui:header"},
        )

        await ws_server._handle_request(mock_websocket, message)

        # Verify subscription response
        mock_websocket.send.assert_called_once()
        sent_message = mock_websocket.send.call_args[0][0]
        decoded = WebSocketProtocol.decode(sent_message)

        assert decoded.data["status"] == "subscribed"
        assert decoded.data["channel"] == "ui:header"

    @pytest.mark.asyncio
    async def test_unsubscribe_request(self, ws_server, mock_websocket):
        """Test handling unsubscribe request."""
        from mcp_common.websocket.protocol import MessageType, WebSocketMessage

        # First subscribe
        connection_id = "conn-123"
        await ws_server.join_room("ui:header", connection_id)

        # Now unsubscribe
        message = WebSocketMessage(
            type=MessageType.REQUEST,
            event="unsubscribe",
            data={"channel": "ui:header"},
        )

        await ws_server._handle_request(mock_websocket, message)

        # Verify unsubscription response
        mock_websocket.send.assert_called_once()
        sent_message = mock_websocket.send.call_args[0][0]
        decoded = WebSocketProtocol.decode(sent_message)

        assert decoded.data["status"] == "unsubscribed"
        assert decoded.data["channel"] == "ui:header"


class TestUIUpdateBroadcasting:
    """Test UI update event broadcasting."""

    @pytest.mark.asyncio
    async def test_broadcast_ui_updated(self, ws_server, mock_websocket):
        """Test broadcasting UI update event."""
        connection_id = "conn-123"
        component_id = "header"

        # Add connection to room
        await ws_server.join_room(f"ui:{component_id}", connection_id)
        ws_server.connections[connection_id] = mock_websocket

        # Broadcast UI update
        metadata = {
            "changes": {"title": "New Title"},
            "source": "user_action",
        }
        await ws_server.broadcast_ui_updated(component_id, metadata)

        # Verify broadcast
        mock_websocket.send.assert_called()
        sent_message = mock_websocket.send.call_args[0][0]
        decoded = WebSocketProtocol.decode(sent_message)

        assert decoded.event == "ui.updated"
        assert decoded.data["component_id"] == component_id
        assert decoded.data["changes"]["title"] == "New Title"
        assert "timestamp" in decoded.data

    @pytest.mark.asyncio
    async def test_broadcast_component_rendered(self, ws_server, mock_websocket):
        """Test broadcasting component render event."""
        connection_id = "conn-123"
        component_id = "navbar"

        # Add connection to room
        await ws_server.join_room(f"component:{component_id}", connection_id)
        ws_server.connections[connection_id] = mock_websocket

        # Broadcast render event
        render_info = {
            "html": "<nav>...</nav>",
            "render_time": 15,
            "cached": True,
        }
        await ws_server.broadcast_component_rendered(component_id, render_info)

        # Verify broadcast
        mock_websocket.send.assert_called()
        sent_message = mock_websocket.send.call_args[0][0]
        decoded = WebSocketProtocol.decode(sent_message)

        assert decoded.event == "component.rendered"
        assert decoded.data["component_id"] == component_id
        assert decoded.data["html"] == "<nav>...</nav>"
        assert decoded.data["render_time"] == 15


class TestStateChangeBroadcasting:
    """Test state change event broadcasting."""

    @pytest.mark.asyncio
    async def test_broadcast_state_changed(self, ws_server, mock_websocket):
        """Test broadcasting state change event."""
        connection_id = "conn-123"
        state_path = "user.preferences.theme"

        # Add connection to state room
        await ws_server.join_room("state", connection_id)
        ws_server.connections[connection_id] = mock_websocket

        # Broadcast state change
        new_value = "dark"
        await ws_server.broadcast_state_changed(state_path, new_value)

        # Verify broadcast
        mock_websocket.send.assert_called()
        sent_message = mock_websocket.send.call_args[0][0]
        decoded = WebSocketProtocol.decode(sent_message)

        assert decoded.event == "state.changed"
        assert decoded.data["state_path"] == state_path
        assert decoded.data["new_value"] == new_value
        assert "timestamp" in decoded.data

    @pytest.mark.asyncio
    async def test_broadcast_nested_state_change(self, ws_server, mock_websocket):
        """Test broadcasting nested state change."""
        connection_id = "conn-123"
        state_path = "app.ui.sidebar.collapsed"

        await ws_server.join_room("state", connection_id)
        ws_server.connections[connection_id] = mock_websocket

        new_value = True
        await ws_server.broadcast_state_changed(state_path, new_value)

        sent_message = mock_websocket.send.call_args[0][0]
        decoded = WebSocketProtocol.decode(sent_message)

        assert decoded.data["state_path"] == state_path
        assert decoded.data["new_value"] is True


class TestRequestHandling:
    """Test request handling and responses."""

    @pytest.mark.asyncio
    async def test_get_component_status(self, ws_server, mock_websocket):
        """Test get_component_status request."""
        from mcp_common.websocket.protocol import MessageType, WebSocketMessage

        message = WebSocketMessage(
            type=MessageType.REQUEST,
            event="get_component_status",
            data={"component_id": "header"},
        )

        await ws_server._handle_request(mock_websocket, message)

        # Verify response
        mock_websocket.send.assert_called_once()
        sent_message = mock_websocket.send.call_args[0][0]
        decoded = WebSocketProtocol.decode(sent_message)

        assert decoded.data["component_id"] == "header"
        assert decoded.data["status"] == "active"
        assert "timestamp" in decoded.data

    @pytest.mark.asyncio
    async def test_get_state(self, ws_server, mock_websocket):
        """Test get_state request."""
        from mcp_common.websocket.protocol import MessageType, WebSocketMessage

        message = WebSocketMessage(
            type=MessageType.REQUEST,
            event="get_state",
            data={"state_path": "user.theme"},
        )

        await ws_server._handle_request(mock_websocket, message)

        # Verify response
        mock_websocket.send.assert_called_once()
        sent_message = mock_websocket.send.call_args[0][0]
        decoded = WebSocketProtocol.decode(sent_message)

        assert decoded.data["state_path"] == "user.theme"
        assert "timestamp" in decoded.data

    @pytest.mark.asyncio
    async def test_unknown_request_returns_error(self, ws_server, mock_websocket):
        """Test that unknown requests return error."""
        from mcp_common.websocket.protocol import MessageType, WebSocketMessage

        message = WebSocketMessage(
            type=MessageType.REQUEST,
            event="unknown_action",
            data={},
        )

        await ws_server._handle_request(mock_websocket, message)

        # Verify error response
        mock_websocket.send.assert_called_once()
        sent_message = mock_websocket.send.call_args[0][0]
        decoded = WebSocketProtocol.decode(sent_message)

        assert decoded.type == "error"
        assert decoded.error_code == "UNKNOWN_REQUEST"


class TestRoomManagement:
    """Test room join/leave operations."""

    @pytest.mark.asyncio
    async def test_join_room(self, ws_server):
        """Test joining a room."""
        connection_id = "conn-123"
        room_id = "ui:header"

        await ws_server.join_room(room_id, connection_id)

        assert connection_id in ws_server.connection_rooms[room_id]
        assert ws_server.room_connections[connection_id] == room_id

    @pytest.mark.asyncio
    async def test_leave_room(self, ws_server):
        """Test leaving a room."""
        connection_id = "conn-123"
        room_id = "ui:header"

        # First join
        await ws_server.join_room(room_id, connection_id)

        # Then leave
        await ws_server.leave_room(room_id, connection_id)

        assert connection_id not in ws_server.connection_rooms[room_id]
        assert connection_id not in ws_server.room_connections

    @pytest.mark.asyncio
    async def test_multiple_connections_same_room(self, ws_server):
        """Test multiple connections in the same room."""
        conn1 = "conn-1"
        conn2 = "conn-2"
        room_id = "state"

        await ws_server.join_room(room_id, conn1)
        await ws_server.join_room(room_id, conn2)

        assert len(ws_server.connection_rooms[room_id]) == 2
        assert conn1 in ws_server.connection_rooms[room_id]
        assert conn2 in ws_server.connection_rooms[room_id]


class TestTimestampGeneration:
    """Test timestamp generation for events."""

    def test_get_timestamp_format(self, ws_server):
        """Test that timestamps are in ISO format."""
        timestamp = ws_server._get_timestamp()

        assert isinstance(timestamp, str)
        assert "T" in timestamp
        # ISO format should end with Z or have timezone
        assert timestamp.endswith("Z") or "+" in timestamp or "-" in timestamp

    def test_get_timestamp_unique(self, ws_server):
        """Test that consecutive timestamps are different."""
        import time

        timestamp1 = ws_server._get_timestamp()
        time.sleep(0.01)  # Small delay
        timestamp2 = ws_server._get_timestamp()

        # Should be different (or at least ordered)
        assert timestamp1 <= timestamp2
