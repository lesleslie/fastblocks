"""FastBlocks MCP server entry point.

Run the FastBlocks MCP protocol server:
    python -m fastblocks.mcp

This enables IDE/AI assistant integration for FastBlocks development.
"""

from __future__ import annotations

import asyncio
import sys

from oneiric.core.logging import get_logger

logger = get_logger(__name__)


async def main() -> int:
    """Main entry point for FastBlocks MCP server.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        from .server import create_fastblocks_mcp_server

        logger.info("Initializing FastBlocks MCP server...")
        server = await create_fastblocks_mcp_server()

        logger.info("Starting FastBlocks MCP server...")
        await server.start()

        return 0

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        return 0
    except Exception:
        logger.exception("Server error")
        return 1


def run() -> None:
    """Synchronous wrapper for async main function."""
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    run()
