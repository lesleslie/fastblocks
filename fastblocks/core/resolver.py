"""Shared Oneiric resolver singleton.

Phase 3.1 of the ACB→Oneiric migration: collapse the 4 per-module
Resolver() instances into one process-wide singleton so dependencies
resolved in `_events_integration` are visible to `_workflows_integration`.
"""

from __future__ import annotations

from oneiric.core.resolution import Resolver

_resolver: Resolver | None = None


def get_resolver() -> Resolver:
    """Return the process-wide Oneiric Resolver singleton.

    Lazy-initialised so import-time side effects (the 4 integration
    modules import this module at top of file) don't pay the
    construction cost until first `resolve()` call.
    """
    global _resolver
    if _resolver is None:
        _resolver = Resolver()
    return _resolver
