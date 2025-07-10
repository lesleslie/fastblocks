"""FastBlocks - Asynchronous web application framework for rapid HTMX/Jinja template delivery."""

from __future__ import annotations

from contextlib import suppress

from . import exceptions

with suppress(ImportError):
    from acb import register_pkg

    register_pkg()

from . import actions, applications, caching, middleware

__all__ = ["actions", "applications", "caching", "exceptions", "middleware"]
