"""TLS configuration for Fastblocks WebSocket server.

This module provides TLS configuration loading from environment variables
and helper functions for secure WebSocket connections.
"""

from __future__ import annotations

from mcp_common.websocket.tls import (
    create_ssl_context,
    get_tls_config_from_env,
)
from oneiric.core.logging import get_logger

logger = get_logger(__name__)


def get_websocket_tls_config() -> dict[str, str | bool | None]:
    """Get TLS configuration from environment variables.

    Environment Variables:
        FASTBLOCKS_WS_TLS_ENABLED: Enable TLS ("true" or "false")
        FASTBLOCKS_WS_CERT_FILE: Path to certificate file (PEM format)
        FASTBLOCKS_WS_KEY_FILE: Path to private key file (PEM format)
        FASTBLOCKS_WS_CA_FILE: Path to CA file (for client verification)
        FASTBLOCKS_WS_VERIFY_CLIENT: Verify client certificates ("true" or "false")

    Returns:
        Dictionary with TLS configuration
    """
    return get_tls_config_from_env("FASTBLOCKS_WS")


def load_ssl_context(
    cert_file: str | None = None,
    key_file: str | None = None,
    ca_file: str | None = None,
    verify_client: bool = False,
) -> dict:  # type: ignore
    """Load SSL context for WebSocket server.

    Args:
        cert_file: Path to certificate file
        key_file: Path to private key file
        ca_file: Path to CA file for client verification
        verify_client: Whether to verify client certificates

    Returns:
        Dictionary with ssl_context and paths for cleanup
    """
    # If no files provided, check environment
    if not cert_file and not key_file:
        config = get_websocket_tls_config()
        if config["tls_enabled"]:
            cert_file = config["cert_file"]  # type: ignore[assignment]
            key_file = config["key_file"]  # type: ignore[assignment]
            ca_file = config["ca_file"]  # type: ignore[assignment]
            verify_client = config.get("verify_client", False)  # type: ignore[assignment]

    # Create SSL context if files provided
    ssl_context = None
    if cert_file and key_file:
        try:
            ssl_context = create_ssl_context(
                cert_file=cert_file,
                key_file=key_file,
                ca_file=ca_file,
                verify_client=verify_client,
            )
            logger.info(f"Loaded TLS certificate: {cert_file}")
        except Exception:
            logger.exception("Failed to load SSL context")
            raise

    return {
        "ssl_context": ssl_context,
        "cert_file": cert_file,
        "key_file": key_file,
        "ca_file": ca_file,
        "verify_client": verify_client,
    }
