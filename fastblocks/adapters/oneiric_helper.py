"""Oneiric compatibility helpers for FastBlocks adapters.

Provides utility functions for registering components with Oneiric's Resolver system.
Oneiric requires wrapping objects in Candidate instances with domain, key, and factory.

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-12-31
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from oneiric.core.logging import get_logger
from oneiric.core.resolution import Candidate, CandidateSource, Resolver
from pydantic import ValidationError
from fastblocks.core.resolver import FastblocksRegistry

_log = get_logger("fastblocks.oneiric_helper")


def _build_candidate(
    domain: str,
    key: str,
    factory: Callable[..., Any],
    metadata: dict[str, Any] | None,
) -> Candidate:
    """Construct a Candidate for the strict + lenient registration paths.

    Mirrors the helper in ``fastblocks.core.resolver._build_candidate`` so
    both paths use the same construction shape. Kept module-local so
    this file remains importable without going through the facade.
    """
    return Candidate(
        domain=domain,
        key=key,
        factory=factory,
        source=CandidateSource.LOCAL_PKG,
        metadata=metadata or {},
    )


def register_candidate(
    resolver: Resolver | FastblocksRegistry,
    domain: str,
    key: str,
    factory: Callable[..., Any],
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Register a Oneiric Candidate with the resolver.

    Oneiric's Resolver.register() requires Candidate objects, not plain objects.
    This helper wraps objects in proper Candidate instances with:
    - domain: The domain namespace (e.g., "fastblocks")
    - key: The lookup key (e.g., "templates")
    - factory: A callable that returns the actual object
    - metadata: Optional metadata dictionary

    Args:
        resolver: Oneiric Resolver instance
        domain: Candidate domain (e.g., "fastblocks")
        key: Candidate key (e.g., "templates")
        factory: Factory function that creates/returns the object
        metadata: Optional metadata dictionary

    Returns:
        True if registration succeeded, False if registration data was invalid
        (Pydantic validation or value-shape failure). Resolver implementation
        errors propagate to the caller -- a candidate the registry rejects for
        reasons unrelated to the inputs we constructed is not a "graceful
        degradation" case and must be visible to the caller.

    For Phase 2 callers that need validation failures to surface as
    exceptions, see :func:`register_candidate_strict`.

    Example:
        >>> from oneiric.core.resolution import Resolver
        >>> depends = Resolver()
        >>> templates_instance = Templates()
        >>> register_candidate(
        ...     depends,
        ...     domain="fastblocks",
        ...     key="templates",
        ...     factory=lambda: templates_instance,
        ...     metadata={"class": "Templates"},
        ... )
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

    resolver.register(candidate)
    return True


def register_candidate_strict(
    resolver: Resolver | FastblocksRegistry,
    domain: str,
    key: str,
    factory: Callable[..., Any],
    metadata: dict[str, Any] | None = None,
) -> None:
    """Register a Candidate with the resolver; raise on validation failure.

    Phase 2 fix for F-L5-01 (Phase 1.5 adversarial review). Mirrors
    :func:`register_candidate` but raises
    :class:`fastblocks.core.resolver.CandidateValidationError` instead
    of returning ``False`` on the documented validation failure set.
    Resolver implementation errors other than the documented set still
    propagate as before.

    Subclass ``ValueError`` so existing ``except ValueError`` handlers
    continue to match — callers that want specifically validation-rejection
    can catch ``CandidateValidationError`` directly.
    """
    try:
        candidate = _build_candidate(domain, key, factory, metadata)
    except (ValidationError, ValueError, TypeError) as exc:
        # Local import to keep oneiric_helper.py decoupled from
        # fastblocks.core.resolver at module-import time (some legacy
        # callers import this module before fastblocks.core.resolver
        # is initialised).
        from fastblocks.core.resolver import CandidateValidationError

        raise CandidateValidationError(
            domain=domain,
            key=key,
            original=exc,
        ) from exc

    resolver.register(candidate)


def resolve_instance(
    resolver: Resolver | FastblocksRegistry, domain: str, key: str
) -> Any:
    """Resolve a registered Candidate and return its factory output.

    Oneiric's Resolver.resolve() returns either a Candidate (whose
    ``factory()`` yields the resolved instance) or ``None`` when no
    candidate is registered for the given domain/key. This helper
    unwraps that contract so callers receive the underlying object.

    Args:
        resolver: Oneiric Resolver instance.
        domain: Candidate domain (e.g. "fastblocks").
        key: Candidate key (e.g. "templates").

    Returns:
        The result of calling ``Candidate.factory()`` for the resolved
        candidate, or ``None`` when no candidate is registered.
        Resolver implementation errors outside the documented swallow
        set propagate to the caller -- a hard failure of the resolver
        is not a graceful-degradation case.

    Example:
        >>> from oneiric.core.resolution import Resolver
        >>> depends = Resolver()
        >>> register_candidate(
        ...     depends,
        ...     domain="fastblocks",
        ...     key="templates",
        ...     factory=lambda: Templates(),
        ... )
        >>> resolve_instance(
        ...     depends, "fastblocks", "templates"
        ... )  # Returns the Templates instance.
    """
    try:
        candidate = resolver.resolve(domain, key)
    except (KeyError, AttributeError, RuntimeError, TypeError):
        return None
    if candidate is None:
        return None
    factory = candidate.factory
    try:
        return cast("Any", factory)()
    except (KeyError, AttributeError, RuntimeError, TypeError):
        return None
