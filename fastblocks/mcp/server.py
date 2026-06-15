"""FastBlocks MCP (Model Context Protocol) server implementation.

Provides IDE/AI assistant integration for FastBlocks capabilities including:
- Template management and validation
- Component creation and discovery
- Adapter configuration and health checks
"""

from __future__ import annotations

from contextlib import suppress
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
        """Initialize MCP server with Oneiric integration."""
        if self._initialized:
            return

        try:
            # Import Oneiric MCP utilities
            from mcp_common.cli import MCPServerCLIFactory

            # Create server using Oneiric infrastructure
            # Oneiric provides the MCP server with rate limiting already configured
            self._server = MCPServerCLIFactory.create_server()

            # Register FastBlocks tools and resources
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
        except Exception:
            logger.exception("Failed to initialize MCP server")

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


# Export ASGI app for uvicorn (standardized startup pattern)
# Note: Since Oneiric's MCP server returns an ASGI app asynchronously,
# we need to provide a synchronous http_app export for uvicorn
def _get_http_app() -> Any:
    """Get the ASGI app for uvicorn.

    This creates a server instance synchronously and extracts the http_app.
    """
    import asyncio
    from contextlib import suppress

    try:
        from mcp_common.cli import MCPServerCLIFactory

        # Create the MCP server (Oneiric returns ASGI app)
        mcp_instance = MCPServerCLIFactory.create_server()

        # Register tools synchronously
        with suppress(Exception):
            from .tools import register_fastblocks_tools

            # Tools registration needs to be sync for uvicorn startup
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(register_fastblocks_tools(mcp_instance))
            loop.close()

        return mcp_instance.http_app

    except Exception:
        logger.exception("Failed to create http_app")
        return None


# Lazy initialization of http_app to avoid import-time side effects
# (Causing pytest collection errors when http_app is created on module import)
_http_app_cache: Any = None


def get_http_app() -> Any:
    """Get the ASGI app for uvicorn (lazy initialization).

    Returns:
        ASGI app instance or None if initialization fails

    This function defers http_app creation until explicitly called,
    preventing import-time side effects that cause test collection errors.
    """
    global _http_app_cache
    if _http_app_cache is None:
        _http_app_cache = _get_http_app()
    return _http_app_cache


# For backward compatibility with code that might import http_app directly
# This is now None at import time and only created when explicitly requested
http_app = None
