"""FastBlocks adapters package."""

import types
from contextlib import suppress

try:
    from . import templates
except (ImportError, TypeError):
    templates = types.ModuleType("templates")

__all__ = ["templates"]

for module_name in ("admin", "app", "auth", "routes", "sitemap"):
    with suppress(ImportError, TypeError):
        globals()[module_name] = __import__(
            f"fastblocks.adapters.{module_name}",
            fromlist=[module_name],
        )
        __all__.append(module_name)  # type: ignore[attr-defined]
