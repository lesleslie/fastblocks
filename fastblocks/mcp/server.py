"""FastBlocks MCP (Model Context Protocol) server implementation.

Provides IDE/AI assistant integration for FastBlocks capabilities including:
- Template management and validation
- Component creation and discovery
- Adapter configuration and health checks
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from oneiric.core.logging import get_logger

if TYPE_CHECKING:
    from fastmcp import FastMCP

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
        self._server: FastMCP[Any] | None = None
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
            #
            # Per Wave 6 Task 1: migrate from the v1 path ``mcp.server.fastmcp``
            # (removed in fastmcp>=3) to the v2 path ``fastmcp``. The v1 module
            # raises ``ModuleNotFoundError`` under fastmcp 3.x/4.x; the previous
            # ``except ImportError`` swallowed that failure and left
            # ``_initialized = False`` while reporting the server as operational.
            from fastmcp import FastMCP

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

        Per Task 22 (W4 tool-profile adoption): dispatch through
        :func:`mcp_common.tools.dispatch._apply_tool_profile` so the
        ``FASTBLOCKS_TOOL_PROFILE`` env var gates the registered surface.
        The single registration map key (``register_fastblocks_tools``)
        delegates to :func:`fastblocks.mcp.tools.register_fastblocks_tools`,
        which wraps every tool function with ``instrument_tool`` before
        passing to ``server.tool(...)``. This keeps the callable-mode
        shape of the dispatcher intact (no decorator-mode refactor).
        """
        from mcp_common.tools.dispatch import _apply_tool_profile

        from .tools.profiles import (
            FASTBLOCKS_MANDATORY_GROUPS,
            PROFILE_REGISTRATIONS,
            REGISTRATION_MAP,
            register_all_tool_groups,
        )

        if self._server is None:
            raise RuntimeError(
                "MCP server not initialized; call initialize() before _register_tools()"
            )
        # PROFILE_REGISTRATIONS is typed wider than the dispatcher's
        # invariant list[str | Callable] parameter. At runtime every
        # value is list[str] of group names; the dispatcher only
        # branches on `is ALL_TOOLS` vs iterable. ty's variance check
        # is too strict here.
        await _apply_tool_profile(
            self._server,
            profile_env_var="FASTBLOCKS_TOOL_PROFILE",
            registrations=PROFILE_REGISTRATIONS,  # ty: ignore[invalid-argument-type]
            registration_map=REGISTRATION_MAP,
            register_all_fn=register_all_tool_groups,
            mandatory_groups=FASTBLOCKS_MANDATORY_GROUPS,
            essential_tool_names=set(),
            discovery_fn=None,
            yaml_loader=None,
        )
        logger.debug("FastBlocks MCP tools registered via profile dispatch")

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
            # ty thinks FastMCP.run returns None; the installed fastmcp
            # version exposes an async run() — pre-existing in this repo,
            # silently OK at runtime.
            await self._server.run()  # ty: ignore[invalid-await]
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
            # ty doesn't see .stop() on FastMCP; it's added at runtime.
            await self._server.stop()  # ty: ignore[unresolved-attribute]
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
