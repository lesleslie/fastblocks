"""MCP tools for Fastblocks WebSocket server management.

Provides tools for:
- Starting/stopping WebSocket server
- Managing UI update subscriptions
- Broadcasting UI events
- Monitoring connection state
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Global WebSocket server instance
_ws_server: Any = None


async def start_websocket_server(
    host: str = "127.0.0.1",
    port: int = 8684,
    max_connections: int = 100,
    message_rate_limit: int = 60,
) -> dict[str, Any]:
    """Start the Fastblocks WebSocket server for UI update streams.

    The WebSocket server provides real-time updates for:
    - UI component rendering events
    - State management changes
    - Application lifecycle events

    Args:
        host: Server host address (default: "127.0.0.1")
        port: WebSocket port (default: 8684)
        max_connections: Maximum concurrent connections (default: 100)
        message_rate_limit: Messages per second per connection (default: 60)

    Returns:
        Dict with server status and connection details
    """
    global _ws_server

    try:
        # Import here to avoid circular dependency
        from fastblocks.websocket import FastblocksWebSocketServer

        if _ws_server is not None and _ws_server.is_running:
            return {
                "success": False,
                "error": "WebSocket server already running",
                "host": _ws_server.host,
                "port": _ws_server.port,
            }

        # Create and start server
        _ws_server = FastblocksWebSocketServer(
            host=host,
            port=port,
            max_connections=max_connections,
            message_rate_limit=message_rate_limit,
        )

        await _ws_server.start()

        return {
            "success": True,
            "host": host,
            "port": port,
            "max_connections": max_connections,
            "message_rate_limit": message_rate_limit,
            "status": "running",
        }

    except ImportError as e:
        logger.error(f"Failed to import WebSocket server: {e}")
        return {
            "success": False,
            "error": f"WebSocket dependencies not installed: {e}",
        }
    except Exception as e:
        logger.error(f"Failed to start WebSocket server: {e}")
        return {
            "success": False,
            "error": str(e),
        }


async def stop_websocket_server() -> dict[str, Any]:
    """Stop the Fastblocks WebSocket server.

    Returns:
        Dict with stop status
    """
    global _ws_server

    try:
        if _ws_server is None:
            return {
                "success": False,
                "error": "WebSocket server not initialized",
            }

        if not _ws_server.is_running:
            return {
                "success": False,
                "error": "WebSocket server not running",
            }

        await _ws_server.stop()

        result = {
            "success": True,
            "status": "stopped",
            "port": _ws_server.port,
        }

        _ws_server = None
        return result

    except Exception as e:
        logger.error(f"Failed to stop WebSocket server: {e}")
        return {
            "success": False,
            "error": str(e),
        }


async def get_websocket_status() -> dict[str, Any]:
    """Get current WebSocket server status and connection info.

    Returns:
        Dict with server status, connection count, and server details
    """
    global _ws_server

    if _ws_server is None:
        return {
            "status": "not_initialized",
            "connections": 0,
        }

    return {
        "status": "running" if _ws_server.is_running else "stopped",
        "host": _ws_server.host,
        "port": _ws_server.port,
        "connections": len(_ws_server.connections),
        "max_connections": _ws_server.max_connections,
        "message_rate_limit": _ws_server.message_rate_limit,
        "rooms": len(_ws_server.connection_rooms),
    }


async def broadcast_ui_update(
    component_id: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Broadcast a UI component update event to all subscribers.

    This sends a real-time update to all clients subscribed to the
    ui:{component_id} channel.

    Args:
        component_id: Component identifier (e.g., "header", "sidebar")
        metadata: Update metadata (changes, timestamp, source, etc.)

    Returns:
        Dict with broadcast status and recipient count
    """
    global _ws_server

    try:
        if _ws_server is None or not _ws_server.is_running:
            return {
                "success": False,
                "error": "WebSocket server not running",
            }

        await _ws_server.broadcast_ui_updated(component_id, metadata)

        # Count recipients
        room_id = f"ui:{component_id}"
        recipient_count = len(_ws_server.connection_rooms.get(room_id, set()))

        return {
            "success": True,
            "component_id": component_id,
            "channel": room_id,
            "recipients": recipient_count,
        }

    except Exception as e:
        logger.error(f"Failed to broadcast UI update: {e}")
        return {
            "success": False,
            "error": str(e),
            "component_id": component_id,
        }


async def broadcast_state_change(
    state_path: str,
    new_value: Any,
) -> dict[str, Any]:
    """Broadcast a state change event to all subscribers.

    This sends a real-time state update to all clients subscribed to the
    'state' channel.

    Args:
        state_path: State path (e.g., "user.preferences.theme")
        new_value: New state value (any JSON-serializable type)

    Returns:
        Dict with broadcast status and recipient count
    """
    global _ws_server

    try:
        if _ws_server is None or not _ws_server.is_running:
            return {
                "success": False,
                "error": "WebSocket server not running",
            }

        await _ws_server.broadcast_state_changed(state_path, new_value)

        # Count recipients
        recipient_count = len(_ws_server.connection_rooms.get("state", set()))

        return {
            "success": True,
            "state_path": state_path,
            "channel": "state",
            "recipients": recipient_count,
        }

    except Exception as e:
        logger.error(f"Failed to broadcast state change: {e}")
        return {
            "success": False,
            "error": str(e),
            "state_path": state_path,
        }


async def subscribe_to_channel(
    channel: str,
) -> dict[str, Any]:
    """Subscribe to a WebSocket update channel (server-side subscription).

    This creates a server-side room that clients can join to receive
    specific types of updates.

    Args:
        channel: Channel name (e.g., "ui:header", "state", "component:navbar")

    Returns:
        Dict with subscription status
    """
    global _ws_server

    try:
        if _ws_server is None or not _ws_server.is_running:
            return {
                "success": False,
                "error": "WebSocket server not running",
            }

        # Ensure room exists
        if channel not in _ws_server.connection_rooms:
            _ws_server.connection_rooms[channel] = set()

        return {
            "success": True,
            "channel": channel,
            "status": "ready",
        }

    except Exception as e:
        logger.error(f"Failed to subscribe to channel: {e}")
        return {
            "success": False,
            "error": str(e),
            "channel": channel,
        }
