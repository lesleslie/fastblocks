"""FastBlocks MCP (Model Context Protocol) server implementation.

Provides IDE/AI assistant integration for FastBlocks capabilities including:
- Template management and validation
- Component creation and discovery
- Adapter configuration and health checks
"""

import logging
from contextlib import suppress
from typing import Any

logger = logging.getLogger(__name__)


class FastBlocksMCPServer:
    """FastBlocks MCP protocol server using ACB infrastructure."""

    def __init__(self, name: str = "fastblocks", version: str = "0.16.0"):
        """Initialize FastBlocks MCP server.

        Args:
            name: Server name for MCP protocol
            version: FastBlocks version
        """
        self.name = name
        self.version = version
        self._server: Any | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize MCP server with ACB integration."""
        if self._initialized:
            return

        try:
            # Import ACB MCP utilities
            from acb import HAS_MCP

            if not HAS_MCP:
                logger.warning("ACB MCP support not available - server disabled")
                return

            from acb import create_mcp_server

            # Create server using ACB infrastructure
            # ACB provides the FastMCP instance with rate limiting already configured
            self._server = create_mcp_server()

            # Register FastBlocks tools and resources
            await self._register_tools()
            await self._register_resources()

            self._initialized = True
            logger.info(
                f"FastBlocks MCP server initialized: {self.name} v{self.version} "
                f"(using ACB infrastructure with rate limiting: 15 req/sec, burst 40)"
            )

        except ImportError:
            logger.debug("ACB MCP dependencies not available - graceful degradation")
        except Exception as e:
            logger.error(f"Failed to initialize MCP server: {e}")

    async def _register_tools(self) -> None:
        """Register FastBlocks MCP tools.

        Tools will be implemented in tools.py and registered here.
        """
        with suppress(Exception):
            from .tools import register_fastblocks_tools

            await register_fastblocks_tools(self._server)
            logger.debug("FastBlocks MCP tools registered")

    async def _register_resources(self) -> None:
        """Register FastBlocks MCP resources.

        Resources will be implemented in resources.py and registered here.
        """
        with suppress(Exception):
            from .resources import register_fastblocks_resources

            await register_fastblocks_resources(self._server)
            logger.debug("FastBlocks MCP resources registered")

    async def start(self) -> None:
        """Start the MCP server."""
        if not self._initialized:
            await self.initialize()

        if self._server is None:
            logger.warning("MCP server not available - skipping start")
            return

        try:
            logger.info("Starting FastBlocks MCP server...")
            await self._server.run()
        except Exception as e:
            logger.error(f"MCP server error: {e}")
            raise

    async def stop(self) -> None:
        """Stop the MCP server gracefully."""
        if self._server is None:
            return

        try:
            logger.info("Stopping FastBlocks MCP server...")
            # Server shutdown will be handled by ACB
            await self._server.stop()
        except Exception as e:
            logger.error(f"Error stopping MCP server: {e}")


async def create_fastblocks_mcp_server() -> FastBlocksMCPServer:
    """Create and initialize FastBlocks MCP server.

    Returns:
        Initialized FastBlocksMCPServer instance

    Example:
        >>> server = await create_fastblocks_mcp_server()
        >>> await server.start()
    """
    server = FastBlocksMCPServer()
    await server.initialize()
    return server
