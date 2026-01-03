"""FastBlocks - Asynchronous web application framework for rapid HTMX/Jinja template delivery."""

from __future__ import annotations

from contextlib import suppress

from oneiric.core.resolution import register_pkg

from . import exceptions

# Register package with Oneiric
with suppress(Exception):
    register_pkg()

from . import actions, applications, caching, cli, middleware

__all__ = ["actions", "applications", "caching", "cli", "exceptions", "middleware"]
