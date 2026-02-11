"""WebSocket abstraction layer for Fastblocks.

This module provides real-time bidirectional communication for UI updates,
enabling live streaming of component render events, state changes, and
application lifecycle events.

Follows the WebSocket Analysis implementation plan from the ecosystem
architecture.
"""

from .server import FastblocksWebSocketServer

__all__ = [
    "FastblocksWebSocketServer",
]
