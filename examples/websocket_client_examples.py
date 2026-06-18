"""WebSocket client examples for Fastblocks UI update streams.

This module demonstrates how to connect to the Fastblocks WebSocket server
and receive real-time UI updates, state changes, and component events.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import websockets

    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    logger.warning(
        "websockets package not installed. Install with: pip install websockets"
    )


class FastblocksWebSocketClient:
    """Client for Fastblocks WebSocket server.

    Handles connection, subscription, and event reception for UI updates.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8684,
    ):
        """Initialize WebSocket client.

        Args:
            host: WebSocket server host
            port: WebSocket server port (default: 8684)
        """
        self.host = host
        self.port = port
        self.uri = f"ws://{host}:{port}"
        self.websocket: Any = None
        self.connected = False

    async def connect(self) -> bool:
        """Connect to WebSocket server.

        Returns:
            True if connection successful
        """
        if not WEBSOCKETS_AVAILABLE:
            logger.error("websockets package not installed")
            return False

        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            logger.info(f"Connected to Fastblocks WebSocket at {self.uri}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info("Disconnected from WebSocket server")

    async def subscribe(self, channel: str) -> bool:
        """Subscribe to a channel.

        Args:
            channel: Channel name (e.g., "ui:header", "state")

        Returns:
            True if subscription successful
        """
        if not self.connected:
            logger.error("Not connected to server")
            return False

        try:
            request = {
                "type": "request",
                "event": "subscribe",
                "data": {"channel": channel},
                "correlation_id": "sub_" + channel,
            }
            await self.websocket.send(json.dumps(request))
            logger.info(f"Subscribed to channel: {channel}")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe: {e}")
            return False

    async def unsubscribe(self, channel: str) -> bool:
        """Unsubscribe from a channel.

        Args:
            channel: Channel name

        Returns:
            True if unsubscription successful
        """
        if not self.connected:
            logger.error("Not connected to server")
            return False

        try:
            request = {
                "type": "request",
                "event": "unsubscribe",
                "data": {"channel": channel},
                "correlation_id": "unsub_" + channel,
            }
            await self.websocket.send(json.dumps(request))
            logger.info(f"Unsubscribed from channel: {channel}")
            return True
        except Exception as e:
            logger.error(f"Failed to unsubscribe: {e}")
            return False

    async def listen(self, callback: Any = None) -> None:
        """Listen for messages from the server.

        Args:
            callback: Optional callback function for received messages
        """
        if not self.connected:
            logger.error("Not connected to server")
            return

        try:
            async for message in self.websocket:
                data = json.loads(message)
                logger.info(f"Received: {data.get('type')} - {data.get('event')}")

                if callback:
                    await callback(data)

        except websockets.exceptions.ConnectionClosed:
            logger.info("Server closed connection")
            self.connected = False
        except Exception as e:
            logger.error(f"Error listening: {e}")
            self.connected = False


async def example_ui_updates():
    """Example: Subscribe to UI component updates."""
    if not WEBSOCKETS_AVAILABLE:
        return

    client = FastblocksWebSocketClient()

    if await client.connect():
        # Subscribe to header component updates
        await client.subscribe("ui:header")

        # Subscribe to state changes
        await client.subscribe("state")

        # Listen for updates
        async def handle_message(data: dict[str, Any]) -> None:
            event = data.get("event", "")
            payload = data.get("data", {})

            if event == "ui.updated":
                logger.info(
                    f"UI Update: {payload.get('component_id')} - {payload.get('timestamp')}"
                )
            elif event == "state.changed":
                logger.info(
                    f"State Change: {payload.get('state_path')} = {payload.get('new_value')}"
                )
            elif event == "session.created":
                logger.info(f"Session: {payload.get('message')}")

        await client.listen(handle_message)


async def example_component_rendering():
    """Example: Subscribe to component rendering events."""
    if not WEBSOCKETS_AVAILABLE:
        return

    client = FastblocksWebSocketClient()

    if await client.connect():
        # Subscribe to specific component
        await client.subscribe("component:navbar")

        async def handle_render(data: dict[str, Any]) -> None:
            if data.get("event") == "component.rendered":
                payload = data.get("data", {})
                logger.info(
                    f"Component Rendered: {payload.get('component_id')} "
                    f"in {payload.get('render_time', 'N/A')}ms"
                )

        await client.listen(handle_render)


async def example_multi_channel():
    """Example: Subscribe to multiple channels simultaneously."""
    if not WEBSOCKETS_AVAILABLE:
        return

    client = FastblocksWebSocketClient()

    if await client.connect():
        channels = ["ui:header", "ui:sidebar", "state", "component:footer"]

        for channel in channels:
            await client.subscribe(channel)

        # Listen with timeout
        try:

            async def handle_all(data: dict[str, Any]) -> None:
                logger.info(
                    f"[{data.get('event')}] {json.dumps(data.get('data', {}), indent=2)}"
                )

            await asyncio.wait_for(client.listen(handle_all), timeout=30.0)
        except TimeoutError:
            logger.info("Listening complete (timeout)")
        finally:
            await client.disconnect()


async def example_request_response():
    """Example: Send requests and receive responses."""
    if not WEBSOCKETS_AVAILABLE:
        return

    client = FastblocksWebSocketClient()

    if await client.connect():
        # Request component status
        request = {
            "type": "request",
            "event": "get_component_status",
            "data": {"component_id": "header"},
            "correlation_id": "req_001",
        }

        await client.websocket.send(json.dumps(request))

        # Listen for response
        async for message in client.websocket:
            data = json.loads(message)

            if data.get("type") == "response":
                if data.get("correlation_id") == "req_001":
                    logger.info(f"Component Status: {data.get('data')}")
                    break

        await client.disconnect()


async def main():
    """Run all examples."""
    examples = [
        ("UI Updates", example_ui_updates),
        ("Component Rendering", example_component_rendering),
        ("Multi-Channel", example_multi_channel),
        ("Request/Response", example_request_response),
    ]

    print("Fastblocks WebSocket Client Examples")
    print("=" * 50)
    print()

    for i, (name, example_func) in enumerate(examples, 1):
        print(f"{i}. {name}")
        print(
            f"   python -c 'import asyncio; from examples.websocket_client_examples import {name_example.replace(' ', '_')}; asyncio.run({name_example.replace(' ', '_')}())'"
        )
        print()

    print("To run a specific example, use the function name directly.")
    print("Example: asyncio.run(example_ui_updates())")


if __name__ == "__main__":
    if WEBSOCKETS_AVAILABLE:
        # Run UI updates example by default
        asyncio.run(example_ui_updates())
    else:
        logger.error("Please install websockets: pip install websockets")
