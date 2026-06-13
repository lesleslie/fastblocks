"""FastBlocks admin shell with session tracking.

Provides an interactive IPython shell for FastBlocks application development
with session tracking integration via Session-Buddy.
"""

from __future__ import annotations

import asyncio
import importlib.metadata
from typing import Any

from oneiric.core.logging import get_logger
from oneiric.shell import AdminShell

logger = get_logger(__name__)


class FastBlocksShell(AdminShell):
    """FastBlocks admin shell for application building.

    Features:
    - build() - Build application
    - render() - Render templates
    - routes() - Show routing table
    - auth - Authentication info

    Session tracking via Session-Buddy:
    - Tracks shell session lifecycle (start/end)
    - Records component metadata (version, adapters)
    - Fire-and-forget emission for non-blocking startup

    Example:
        ```python
        from fastblocks.shell import FastBlocksShell
        from fastblocks.applications import FastBlocks

        app = FastBlocks()
        shell = FastBlocksShell(app)
        shell.start()
        ```
    """

    def __init__(self, app: Any, config: Any = None) -> None:
        """Initialize FastBlocks admin shell.

        Args:
            app: FastBlocks application instance
            config: Optional shell configuration
        """
        super().__init__(app, config)
        self._add_fastblocks_namespace()

    def _get_component_name(self) -> str:
        """Get component name for session tracking."""
        return "fastblocks"

    def _get_component_version(self) -> str:
        """Get FastBlocks version."""
        try:
            return importlib.metadata.version("fastblocks")
        except Exception:
            return "unknown"

    def _get_adapters_info(self) -> list[str]:
        """Get enabled adapters info for session metadata."""
        adapters = ["web_framework", "ui_components"]

        # Try to get additional adapters from app config
        try:
            if hasattr(self.app, "config"):
                config = self.app.config
                if hasattr(config, "adapters"):
                    for adapter_name, enabled in config.adapters.items():
                        if enabled and adapter_name not in adapters:
                            adapters.append(adapter_name)
        except Exception:
            pass

        return adapters

    async def _build_app(self) -> dict[str, Any]:
        """Build application and return build info."""
        try:
            build_info = {
                "status": "success",
                "app_name": getattr(self.app, "title", "FastBlocks App"),
                "middleware_count": len(getattr(self.app, "user_middleware", [])),
            }

            # Try to build middleware stack
            if hasattr(self.app, "build_middleware_stack"):
                self.app.build_middleware_stack()

            logger.info("Application built successfully")
            return build_info
        except Exception as e:
            logger.error(f"Build failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _get_render_info(self) -> dict[str, Any]:
        """Get template rendering info."""
        try:
            templates_info = {}

            if hasattr(self.app, "templates"):
                templates = self.app.templates
                if hasattr(templates, "env"):
                    jinja_env = templates.env
                    templates_info = {
                        "loader": str(type(jinja_env.loader).__name__),
                        "auto_reload": jinja_env.auto_reload,
                        "cache_size": jinja_env.cache.capacity,
                    }

            return {
                "status": "success",
                "templates": templates_info,
            }
        except Exception as e:
            logger.error(f"Failed to get render info: {e}")
            return {"status": "error", "error": str(e)}

    async def _get_routes(self) -> list[dict[str, Any]]:
        """Show routing table."""
        try:
            routes = []

            if hasattr(self.app, "routes"):
                for route in self.app.routes:
                    route_info = {
                        "path": getattr(route, "path", None),
                        "name": getattr(route, "name", None),
                        "methods": getattr(route, "methods", None),
                    }
                    routes.append(route_info)

            return routes
        except Exception as e:
            logger.error(f"Failed to get routes: {e}")
            return [{"error": str(e)}]

    def _get_auth_info(self) -> dict[str, Any]:
        """Get authentication info."""
        auth_info = {"enabled": False, "type": None}

        try:
            # Check for CSRF middleware
            if hasattr(self.app, "user_middleware"):
                for mw in self.app.user_middleware:
                    if "csrf" in str(mw.cls).lower():
                        auth_info["csrf_enabled"] = True

            # Check for auth adapter
            if hasattr(self.app, "config") and hasattr(self.app.config, "adapters"):
                auth_adapter = self.app.config.adapters.get("auth", "basic")
                auth_info["type"] = auth_adapter
                auth_info["enabled"] = True

        except Exception as e:
            logger.error(f"Failed to get auth info: {e}")

        return auth_info

    def _add_fastblocks_namespace(self) -> None:
        """Add FastBlocks-specific helpers to shell namespace."""
        # Add helpers to namespace (async functions wrapped)
        self.namespace.update(
            {
                "build": lambda: asyncio.run(self._build_app()),
                "render": lambda: asyncio.run(self._get_render_info()),
                "routes": lambda: asyncio.run(self._get_routes()),
                "auth": self._get_auth_info(),
            }
        )

        logger.debug("Added FastBlocks helpers to shell namespace")

    def _get_banner(self) -> str:
        """Get shell banner."""
        version = self._get_component_version()
        adapters = self._get_adapters_info()
        adapters_str = ", ".join(adapters)

        return f"""
FastBlocks Admin Shell
{"=" * 60}
Application Builder & Web Framework
Version: {version}

Adapters: {adapters_str}
Session Tracking: ✓ Enabled

Builder Commands:
  build()        - Build application
  render()       - Render templates
  routes()       - Show routing table
  auth           - Authentication info

Type 'help()' for Python help or %help_shell for shell commands
{"=" * 60}
"""


__all__ = ["FastBlocksShell"]
