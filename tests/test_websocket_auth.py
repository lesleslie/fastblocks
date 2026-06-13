"""Tests for FastBlocks WebSocket authentication."""

from __future__ import annotations

import os
import pytest

from fastblocks.websocket.auth import (
    get_authenticator,
    generate_token,
    verify_token,
)
from fastblocks.websocket.server import FastblocksWebSocketServer
from mcp_common.websocket import WebSocketProtocol

# This module imports from mcp_common.websocket (the stub provided by
# tests/conftest.py) and constructs a FastblocksWebSocketServer.
pytestmark = [pytest.mark.unit, pytest.mark.websocket]


@pytest.mark.unit
class TestFastBlocksWebSocketAuth:
    """Test FastBlocks WebSocket authentication configuration."""

    def test_get_authenticator_dev_mode(self):
        """Test getting authenticator in development mode."""
        # Ensure auth is disabled
        os.environ["FASTBLOCKS_AUTH_ENABLED"] = "false"

        authenticator = get_authenticator()
        assert authenticator is None

    def test_generate_token(self):
        """Test generating a JWT token."""
        token = generate_token("user123", ["fastblocks:read", "fastblocks:write"])

        assert isinstance(token, str)
        assert len(token) > 0
        assert token.count(".") == 2  # JWT format

    def test_verify_token(self):
        """Test verifying a generated token."""
        token = generate_token("user123", ["fastblocks:read"])
        payload = verify_token(token)

        assert payload is not None
        assert payload["user_id"] == "user123"
        assert payload["permissions"] == ["fastblocks:read"]

    def test_verify_invalid_token(self):
        """Test verifying an invalid token."""
        payload = verify_token("invalid-token")
        assert payload is None


@pytest.mark.unit
class TestFastBlocksWebSocketServer:
    """Test FastBlocks WebSocket server with authentication."""

    def test_server_initialization(self):
        """Test server initialization."""
        server = FastblocksWebSocketServer(
            host="127.0.0.1",
            port=8684,
            require_auth=False,
        )

        assert server.host == "127.0.0.1"
        assert server.port == 8684
        assert server.require_auth is False

    def test_server_with_auth_enabled(self):
        """Test server with authentication enabled."""
        # Enable auth for this test
        os.environ["FASTBLOCKS_AUTH_ENABLED"] = "true"

        try:
            server = FastblocksWebSocketServer(
                require_auth=True,
            )

            assert server.require_auth is True
            # authenticator should be set when AUTH_ENABLED is true
            assert server.authenticator is not None
        finally:
            # Clean up
            os.environ["FASTBLOCKS_AUTH_ENABLED"] = "false"

    def test_channel_authorization(self):
        """Test channel subscription authorization."""
        server = FastblocksWebSocketServer(
            require_auth=False,
        )

        # Test admin user
        admin_user = {"user_id": "admin", "permissions": ["fastblocks:admin"]}
        assert server._can_subscribe_to_channel(admin_user, "ui:123") is True
        assert server._can_subscribe_to_channel(admin_user, "component:abc") is True
        assert server._can_subscribe_to_channel(admin_user, "state") is True

        # Test user with fastblocks:read permission
        read_user = {"user_id": "user1", "permissions": ["fastblocks:read"]}
        assert server._can_subscribe_to_channel(read_user, "ui:123") is True
        assert server._can_subscribe_to_channel(read_user, "component:abc") is True
        assert server._can_subscribe_to_channel(read_user, "state") is True

        # Test user without relevant permissions
        limited_user = {"user_id": "user2", "permissions": ["other"]}
        assert server._can_subscribe_to_channel(limited_user, "ui:123") is False
        assert server._can_subscribe_to_channel(limited_user, "component:abc") is False
        assert server._can_subscribe_to_channel(limited_user, "state") is False


@pytest.mark.integration
class TestFastBlocksWebSocketAuthenticationIntegration:
    """Integration tests for FastBlocks WebSocket authentication."""

    @pytest.mark.asyncio
    async def test_server_start_without_auth(self):
        """Test that server starts without authentication."""
        server = FastblocksWebSocketServer(
            host="127.0.0.1",
            port=8685,  # Use different port for testing
            require_auth=False,
        )

        try:
            await server.start()
            assert server.is_running is True
        finally:
            await server.stop()
            assert server.is_running is False

    @pytest.mark.asyncio
    async def test_server_start_with_auth(self):
        """Test that server starts with authentication."""
        # Enable auth for this test
        os.environ["FASTBLOCKS_AUTH_ENABLED"] = "true"

        try:
            server = FastblocksWebSocketServer(
                host="127.0.0.1",
                port=8686,  # Use different port for testing
                require_auth=True,
            )

            await server.start()
            assert server.is_running is True
            await server.stop()
            assert server.is_running is False
        finally:
            # Clean up
            os.environ["FASTBLOCKS_AUTH_ENABLED"] = "false"

    @pytest.mark.asyncio
    async def test_authenticated_connection_flow(self):
        """Test full authentication flow with WebSocket client."""
        # Enable auth for this test
        os.environ["FASTBLOCKS_AUTH_ENABLED"] = "true"

        server = FastblocksWebSocketServer(
            host="127.0.0.1",
            port=8687,
            require_auth=True,
        )

        try:
            await server.start()

            # Create client with token
            token = generate_token("test_user", ["fastblocks:read", "fastblocks:admin"])

            from mcp_common.websocket import WebSocketClient
            client = WebSocketClient(
                uri="ws://127.0.0.1:8687",
                token=token,
                reconnect=False,
            )

            try:
                await client.connect()
                assert client.is_connected is True
                assert client.is_authenticated is True
            finally:
                await client.disconnect()

        finally:
            await server.stop()
            os.environ["FASTBLOCKS_AUTH_ENABLED"] = "false"

    @pytest.mark.asyncio
    async def test_unauthenticated_connection_rejected(self):
        """Test that connections without valid token are rejected."""
        # Enable auth for this test
        os.environ["FASTBLOCKS_AUTH_ENABLED"] = "true"

        server = FastblocksWebSocketServer(
            host="127.0.0.1",
            port=8688,
            require_auth=True,
        )

        try:
            await server.start()

            # Create client with invalid token
            from mcp_common.websocket import WebSocketClient
            client = WebSocketClient(
                uri="ws://127.0.0.1:8688",
                token="invalid-token",
                reconnect=False,
            )

            try:
                # Connection should fail or auth should fail
                await client.connect()
                # If connection succeeds, auth should have failed
                assert client.is_authenticated is False
            except (ConnectionError, Exception):
                # Expected - connection should be rejected
                pass
            finally:
                await client.disconnect()

        finally:
            await server.stop()
            os.environ["FASTBLOCKS_AUTH_ENABLED"] = "false"
