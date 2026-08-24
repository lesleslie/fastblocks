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


def _construction_site_info() -> str:
    r"""Return the file:line of the immediate caller of FastblocksRegistry().

    Used by the Card 8 identity-check warning so operators see where
    the leak was constructed, not just that one happened. Limited to
    the immediate caller (one frame above the constructor) — deeper
    tracking would intrude on async scheduling stacks and is not
    worth the cost. Returns \"<unknown>\" if no caller frame is found
    (e.g. when invoked from an interactive interpreter).
    """
    import inspect

    frame = inspect.currentframe()
    if frame is None or frame.f_back is None or frame.f_back.f_back is None:
        return "<unknown>"
    caller = frame.f_back.f_back
    return f"{caller.f_code.co_filename}:{caller.f_lineno}"


class CandidateValidationError(ValueError):
    """Raised by ``register_candidate_strict`` when Candidate construction fails.

    Phase 2 fix for F-L5-01. Subclasses ``ValueError`` so existing
    ``except ValueError`` handlers continue to match, while callers that
    want to specifically catch validation-rejection can do so.

    Attributes:
        domain: The candidate domain that was being registered.
        key: The candidate key that was being registered.
        original: The underlying ``ValidationError``, ``ValueError``,
            or ``TypeError`` that triggered the rejection.
    """

    def __init__(
        self,
        *,
        domain: str,
        key: str,
        original: BaseException,
    ) -> None:
        self.domain = domain
        self.key = key
        self.original = original
        super().__init__(
            f"register_candidate_strict rejected invalid registration: "
            f"domain={domain!r} key={key!r} error={original}"
        )


def _build_candidate(
    domain: str,
    key: str,
    factory: Callable[..., Any],
    metadata: dict[str, Any] | None,
) -> Candidate:
    """Construct a Candidate for the fastblocks facade's strict + lenient paths.

    Shared between :meth:`FastblocksRegistry.register_candidate` (which
    swallows the documented exception set) and
    :meth:`FastblocksRegistry.register_candidate_strict` (which raises
    :class:`CandidateValidationError`). Keeps the construction shape in
    one place so the two paths cannot drift on ``source`` /
    ``metadata`` defaults.
    """
    return Candidate(
        domain=domain,
        key=key,
        factory=factory,
        source=CandidateSource.LOCAL_PKG,
        metadata=metadata or {},
    )


def get_resolver() -> Resolver:
    """Return the **fastblocks-owned** Resolver singleton.

    Ownership boundary (Phase 1.5.2): this singleton is owned by the
    ``fastblocks`` package — not by Oneiric, not by the process. Cross-
    component consumers (mahavishnu, akosha, dhara, session-buddy,
    crackerjack, oneiric, mcp-common) MUST call
    ``oneiric.core.resolver.get_resolver()`` if they need their own
    resolver. Importing ``from fastblocks.core.resolver import
    get_resolver`` across component boundaries is forbidden — enforced
    by ``tests/test_ci_guard.py`` (Phase 1.5.3) and the
    ``git grep`` audit on every release.

    Lifetime: process-wide. Each Python process has exactly one
    ``_resolver`` instance; multi-pool workers (each subprocess) get
    their own singleton, but no state crosses pool boundaries.

    Lazy-initialised so import-time side effects (the integration
    modules import this module at top of file) don't pay the
    construction cost until first ``resolve()`` call.
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
    as the public capability registration primitives in
    ``fastblocks.mcp.capabilities`` (Phase 4 v2.1) — the framework
    exports registration functions for consumers (e.g. SplashStand)
    to wire into their own ``mcp_common.tools.apply_tool_profile`` calls.

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
        # Card 8 (F-L3-3 identity check): the constructor accepts any
        # Resolver-shaped object, but a non-canonical one (i.e. not
        # the singleton returned by ``get_resolver()``) silently
        # creates a parallel registry that bypasses the consolidation
        # invariant (ADR 0008 Rule 2). We log a warning so operators
        # see the leak; we don't raise because some legitimate test
        # isolation patterns construct ephemeral Resolvers to run
        # against private state.
        self._resolver = resolver
        canonical = get_resolver()
        if resolver is not canonical:
            import logging

            stack = _construction_site_info()
            logging.getLogger(__name__).warning(
                "FastblocksRegistry constructed with a non-canonical "
                "Resolver at %s; ADR 0008 Rule 2 expects all consumers "
                "to share the singleton from fastblocks.core.resolver."
                "get_resolver(). Pass `get_resolver()` or import path: "
                "%s",
                stack,
                type(resolver).__module__ + "." + type(resolver).__name__,
            )
        # Phase 1.5 observability: bump the registry-size counter
        # on every facade construction. Post-Phase-1.5 the expected
        # value is 1 — the consolidation invariant (see ADR 0008
        # Rule 2 selection mechanism ownership + the singleton
        # ownership boundary in ``fastblocks/core/resolver.py``).
        # Phase 6 replaces this with a Prometheus exporter over
        # the same counter.
        from fastblocks.core import resolver_metrics

        resolver_metrics.increment_registry_size()

    def unwrap(self) -> Resolver:
        """Return the underlying Oneiric ``Resolver``.

        Use this ONLY for upstream APIs that strictly type their
        ``Resolver`` parameter and reject the facade — e.g.
        ``oneiric.adapters.bootstrap.register_builtin_adapters`` and
        ``oneiric.adapters.metadata.register_adapter_metadata``.
        New code should prefer the facade methods (``register_candidate``,
        ``resolve_instance``, ``register``, ``resolve``, ``explain``).
        """
        return self._resolver

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

        For Phase 2 callers that need validation failures to surface as
        exceptions, see :meth:`register_candidate_strict`.
        """
        try:
            candidate = _build_candidate(domain, key, factory, metadata)
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
        # Phase 1.5 observability: bump per-registration counter.
        # ``register_candidate`` is the hot path; the metrics
        # increment is in-process under a lock (cheap), and the
        # counter is exported by Phase 6's Prometheus integration.
        from fastblocks.core import resolver_metrics

        resolver_metrics.increment_registration_count()
        return True

    def register_candidate_strict(
        self,
        domain: str,
        key: str,
        factory: Callable[..., Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Wrap ``factory`` in a Candidate and register it; raise on failure.

        Phase 2 fix for F-L5-01 (Phase 1.5 adversarial review). The
        default :meth:`register_candidate` swallows
        ``(ValidationError, ValueError, TypeError)`` and returns
        ``False`` — a Phase 2 typed candidate that fails validation
        would silently disappear from the registry, defeating the
        fail-loud startup validation contract.

        This method raises :class:`CandidateValidationError` (a
        ``ValueError`` subclass, so existing ``except ValueError``
        handlers still match) on the documented validation failure set.
        Resolver implementation errors other than the documented set
        still propagate as before — they are not graceful-degradation
        cases and must be visible.

        ``metadata`` validation is identical to ``register_candidate``;
        no additional checks are added here. Phase 2 callers should
        validate their own candidate metadata before calling this.
        """
        try:
            candidate = _build_candidate(domain, key, factory, metadata)
        except (ValidationError, ValueError, TypeError) as exc:
            raise CandidateValidationError(
                domain=domain,
                key=key,
                original=exc,
            ) from exc
        self._resolver.register(candidate)
        from fastblocks.core import resolver_metrics

        resolver_metrics.increment_registration_count()

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
