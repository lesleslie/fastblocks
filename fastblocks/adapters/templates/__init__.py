"""FastBlocks templates adapters."""

import types

try:
    from . import jinja2  # noqa: F401
except (ImportError, TypeError):
    jinja2 = types.ModuleType("jinja2")

__all__ = ["jinja2"]
