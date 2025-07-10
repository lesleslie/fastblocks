"""FastBlocks - Asynchronous web application framework for rapid HTMX/Jinja template delivery."""

from __future__ import annotations

import sys
from typing import Any

from . import exceptions

# Register FastBlocks as a package with ACB so its adapters can be discovered
try:
    from acb import register_pkg
    register_pkg()
except ImportError:
    # ACB not available, skip registration
    pass

# Import actions - required for FastBlocks with ACB
from . import actions

# Import applications - required for FastBlocks with ACB
from . import applications

# Import caching - required for FastBlocks with ACB
from . import caching

# Import middleware - required for FastBlocks with ACB
from . import middleware

__all__ = ["actions", "applications", "caching", "exceptions", "middleware"]
