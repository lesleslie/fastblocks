"""Shared Oneiric resolver singleton + FastblocksRegistry facade.

Phase 3.1 of the ACB→Oneiric migration: collapse the 4 per-module
Resolver() instances into one process-wide singleton so dependencies
resolved in `_events_integration` are visible to `_workflows_integration`.

Phase 1.5: add :class:`FastblocksRegistry` so every call site that
currently does ``depends = Resolver()`` can route through a single
chokepoint. Future Oneiric API changes absorb here instead of at
~90 call sites.

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
from typing import Any, cast

from oneiric.core.logging import get_logger
from oneiric.core.resolution import (
    Candidate,
    CandidateSource,
    Resolver,
)
from pydantic import ValidationError

Factory = Callable[[], object | Awaitable[object]]

_log = get_logger("fastblocks.resolver")

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


class FastblocksRegistry:
    """Single-chokepoint facade over Oneiric's Resolver.

    Wraps every method the codebase calls on Resolver so future
    Oneiric API changes (0.13→0.17 already changed the registration
    shape once) absorb here instead of at ~90 call sites. Same posture
    as :func:`fastblocks.mcp.profiles.apply_fastblocks_tool_profile`
    wrapping ``mcp_common.tools.apply_tool_profile``.

    Construct against the fastblocks singleton via :func:`get_resolver` —
    never against a fresh ``Resolver()`` — that defeats the "single
    shared registry" invariant Phase 1.5 enforces.

    Example:
        >>> from fastblocks.core.resolver import get_resolver, FastblocksRegistry
        >>> depends = FastblocksRegistry(get_resolver())
        >>> depends.register_candidate("fastblocks", "templates", factory=...)
        >>> instance = depends.resolve_instance("fastblocks", "templates")
    """

    def __init__(self, resolver: Resolver) -> None:
        self._resolver = resolver

    # --- Raw Resolver passthroughs (Phase 1.5 deliverable 0 list) ---

    def register(self, candidate: Candidate) -> None:
        """Register a pre-built Candidate."""
        self._resolver.register(candidate)

    def resolve(self, domain: str, key: str) -> Candidate | None:
        """Resolve a Candidate by domain/key; returns the wrapper or None."""
        return self._resolver.resolve(domain, key)

    def explain(self, domain: str, key: str) -> Any:
        """Diagnostic — show why a candidate is or isn't selected."""
        return self._resolver.explain(domain, key)

    def list_shadowed(self, domain: str) -> list[Candidate]:
        """List shadowed candidates in ``domain`` (registered but not selected)."""
        return self._resolver.list_shadowed(domain)

    def list_active(self, domain: str) -> list[Candidate]:
        """List active candidates in ``domain``."""
        return self._resolver.list_active(domain)

    # --- Consolidated helpers (moved from oneiric_helper.py) ---

    def register_candidate(
        self,
        domain: str,
        key: str,
        factory: Callable[..., Any],
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Wrap ``factory`` in a Candidate and register it.

        Returns ``True`` on success, ``False`` if the candidate was
        rejected for documented validation failures (``ValidationError``,
        value-shape mismatch). Resolver implementation errors propagate
        to the caller — a candidate the registry rejects for reasons
        unrelated to the inputs we constructed is not a graceful
        degradation case and must be visible.
        """
        try:
            candidate = Candidate(
                domain=domain,
                key=key,
                factory=factory,
                source=CandidateSource.LOCAL_PKG,
                metadata=metadata or {},
            )
        except (ValidationError, ValueError, TypeError) as exc:
            _log.exception(
                "register_candidate rejected invalid registration: "
                "domain=%r key=%r error=%s",
                domain,
                key,
                exc,
            )
            return False
        self._resolver.register(candidate)
        return True

    def resolve_instance(self, domain: str, key: str) -> Any:
        """Resolve and invoke the factory; return ``None`` on miss or failure.

        Returns the result of calling ``Candidate.factory()`` for the
        resolved candidate, or ``None`` when no candidate is registered.
        Resolver implementation errors outside the documented swallow
        set propagate to the caller — a hard failure of the resolver
        is not a graceful-degradation case.
        """
        try:
            candidate = self._resolver.resolve(domain, key)
        except (KeyError, AttributeError, RuntimeError, TypeError):
            return None
        if candidate is None:
            return None
        factory = candidate.factory
        try:
            return cast("Any", factory)()
        except (KeyError, AttributeError, RuntimeError, TypeError):
            return None

    # Note: a ``clear()`` method is intentionally NOT exposed. Oneiric
    # 0.17.x does not provide a public reset, and reaching into the
    # underlying resolver to call ``__init__`` is brittle. Phase 1.5.4
    # test isolation resets via the ``clean_resolver`` fixture calling
    # ``get_resolver().__init__()`` directly — the underlying resolver
    # is reachable via :func:`get_resolver` for test-only purposes.


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
        return await value
    return value
