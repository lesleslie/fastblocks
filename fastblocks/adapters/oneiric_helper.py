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

_log = get_logger("fastblocks.oneiric_helper")


def register_candidate(
    resolver: Resolver,
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

    resolver.register(candidate)
    return True


def resolve_instance(resolver: Resolver, domain: str, key: str) -> Any:
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
