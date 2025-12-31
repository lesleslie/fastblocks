"""Oneiric compatibility helpers for FastBlocks adapters.

Provides utility functions for registering components with Oneiric's Resolver system.
Oneiric requires wrapping objects in Candidate instances with domain, key, and factory.

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-12-31
"""

import typing as t

from oneiric.core.resolution import Candidate, CandidateSource, Resolver


def register_candidate(
    resolver: Resolver,
    domain: str,
    key: str,
    factory: t.Callable[..., t.Any],
    metadata: dict[str, t.Any] | None = None,
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
        True if registration succeeded, False if it failed gracefully

    Example:
        >>> from oneiric.core.resolution import Resolver
        >>> depends = Resolver()
        >>> templates_instance = Templates()
        >>> register_candidate(
        ...     depends,
        ...     domain="fastblocks",
        ...     key="templates",
        ...     factory=lambda: templates_instance,
        ...     metadata={"class": "Templates"}
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
        resolver.register(candidate)
        return True
    except Exception:
        # Graceful degradation if registration fails
        return False
