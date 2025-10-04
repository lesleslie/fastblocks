"""FastBlocks MCP server entry point.

Run the FastBlocks MCP protocol server:
    python -m fastblocks.mcp

This enables IDE/AI assistant integration for FastBlocks development.
"""

import asyncio
import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        return 1


def run() -> None:
    """Synchronous wrapper for async main function."""
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    run()
