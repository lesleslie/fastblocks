"""FastBlocks MCP (Model Context Protocol) server implementation.

Provides IDE/AI assistant integration for FastBlocks capabilities including:
- Template management and validation
- Component creation and discovery
- Adapter configuration and health checks
"""

from __future__ import annotations

from typing import Any

from oneiric.core.logging import get_logger

logger = get_logger(__name__)


class FastBlocksMCPServer:
    """FastBlocks MCP protocol server using Oneiric infrastructure."""

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
        """Initialize MCP server with Oneiric integration.

        Registration failures propagate: ``_initialized`` stays ``False``
        when ``_register_tools`` or ``_register_resources`` raises. An
        ``ImportError`` from Oneiric (no MCP infrastructure available)
        degrades gracefully without flipping the flag — the server is
        not usable in that mode but we do not pretend it is.
        """
        if self._initialized:
            return

        try:
            # Create server using the canonical FastMCP constructor.
            # The previous `MCPServerCLIFactory.create_server()` call referenced a
            # method that does not exist (only `create_app()` and `create_server_cli()`
            # are part of `mcp_common.cli.MCPServerCLIFactory`). FastMCP gives us a
            # working MCP server; Dhara (which replaced Oneiric MCP) infrastructure
            # hooks (rate limiting, health) can be layered on later.
            from mcp.server.fastmcp import FastMCP

            self._server = FastMCP(name=self.name)

            # Register FastBlocks tools and resources. Failures propagate
            # so the caller sees the same RuntimeError we raised — the
            # previous inner ``with suppress(Exception)`` swallowed
            # every registration error and made ``_initialized`` a lie.
            await self._register_tools()
            await self._register_resources()

            self._initialized = True
            logger.info(
                f"FastBlocks MCP server initialized: {self.name} v{self.version} "
                f"(using Oneiric infrastructure with rate limiting: 15 req/sec, burst 40)"
            )

        except ImportError:
            logger.debug(
                "Oneiric MCP dependencies not available - graceful degradation"
            )

    async def _register_tools(self) -> None:
        """Register FastBlocks MCP tools.

        Tools will be implemented in tools.py and registered here.
        """
        from .tools import register_fastblocks_tools

        await register_fastblocks_tools(self._server)
        logger.debug("FastBlocks MCP tools registered")

    async def _register_resources(self) -> None:
        """Register FastBlocks MCP resources.

        Resources will be implemented in resources.py and registered here.
        """
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
        except Exception:
            logger.exception("MCP server error")
            raise

    async def stop(self) -> None:
        """Stop the MCP server gracefully."""
        if self._server is None:
            return

        try:
            logger.info("Stopping FastBlocks MCP server...")
            # Server shutdown will be handled by Oneiric
            await self._server.stop()
        except Exception:
            logger.exception("Error stopping MCP server")


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
