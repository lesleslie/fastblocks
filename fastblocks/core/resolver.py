"""Shared Oneiric resolver singleton.

Phase 3.1 of the ACB→Oneiric migration: collapse the 4 per-module
Resolver() instances into one process-wide singleton so dependencies
resolved in `_events_integration` are visible to `_workflows_integration`.

Helpers:
- `resolve_component()` invokes a registered `Candidate.factory` and returns
  the concrete value, hiding the raw `Candidate` wrapper from callers.
- `resolve_component_async()` is the async-aware variant and supports both
  sync and async factories; callers must `await` its return value.

Use the sync helper from synchronous callers and the async helper from async
callers. Do not wrap the sync helper in `asyncio.run`; the candidate factory
is invoked synchronously by design.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import cast

from oneiric.core.resolution import Resolver

Factory = Callable[[], object | Awaitable[object]]

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


def _candidate_value(
    resolver: Resolver, domain: str, key: str
) -> object | Awaitable[object] | None:
    candidate = resolver.resolve(domain, key)
    if candidate is None:
        return None
    if candidate.factory is None:
        raise TypeError(f"Missing factory for {domain}:{key}")
    if isinstance(candidate.factory, str):
        raise TypeError(f"String factories are not supported for {domain}:{key}")
    return cast(Factory, candidate.factory)()


def resolve_component(resolver: Resolver, domain: str, key: str) -> object | None:
    """Resolve and invoke a synchronous component factory.

    Raises `TypeError` if the registered factory returns an awaitable; such
    factories must be resolved via `resolve_component_async()` instead.
    """
    value = _candidate_value(resolver, domain, key)
    if inspect.isawaitable(value):
        # Close the coroutine so it isn't garbage-collected unawaited (which
        # emits a RuntimeWarning under "auto" asyncio mode).
        value.close()  # ty: ignore[unresolved-attribute]
        raise TypeError(
            f"Async factory requires resolve_component_async: {domain}:{key}"
        )
    return value


async def resolve_component_async(
    resolver: Resolver, domain: str, key: str
) -> object | None:
    """Resolve and invoke a synchronous or asynchronous component factory.

    Returns the concrete component (or `None` when no candidate is registered)
    after awaiting any coroutine produced by the factory.
    """
    value = _candidate_value(resolver, domain, key)
    if inspect.isawaitable(value):
        return await cast(Awaitable[object], value)
    return value
