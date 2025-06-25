"""FastBlocks routes adapters."""

import importlib.util
from contextlib import suppress

with suppress(ImportError):
    if importlib.util.find_spec(".default", package=__package__):
        from . import default  # noqa: F401

__all__ = ["default"]
