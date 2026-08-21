"""Phase 1.5.4 cross-module resolution test.

Proves the end-to-end identity contract:

1. ``get_resolver()`` from module A and module B returns the SAME
   singleton (``is`` identity) — the singleton is shared across
   importers, not duplicated per-import.
2. A ``Candidate`` registered from module A is observable from
   module B via the shared singleton — no hand-shaking required.
3. The resolved Candidate's ``factory`` is the SAME callable as the
   one registered (identity, not just equal).
4. The ``clean_resolver`` autouse fixture isolates each test by
   resetting the lazy-init cache at setup AND teardown.

Each test gets a clean resolver via the ``clean_resolver`` autouse
fixture in ``tests/conftest.py``.

The fixture modules under ``tests/_fixtures/`` perform import-time
side effects — they register and resolve once when imported. The
identity assertions in the tests below compare the cached
module-level constants; for tests that need to verify isolation
between runs, we use a FRESH resolve call (not the cached one) so a
stale-cache bug would not be masked.
"""

from __future__ import annotations

import pytest
from tests._fixtures import test_adapter, test_resolver_consistency
from tests._fixtures.test_adapter import (
    ADAPTER_DOMAIN,
    ADAPTER_KEY,
    SENTINEL_INSTANCE,
    CrossModuleAdapter,
)
from tests._fixtures.test_resolver_consistency import (
    _RESOLVED_CANDIDATE,
    RESOLVED_INSTANCE,
)


@pytest.mark.unit
def test_resolver_singleton_is_shared_across_modules() -> None:
    """``get_resolver()`` from different modules returns the SAME instance.

    The Oneiric ``Resolver`` singleton is the cross-module shared
    bus. Both ``test_adapter`` and ``test_resolver_consistency``
    expose a ``current_resolver()`` helper (not a module-level
    constant — see their docstrings for why) that calls
    ``get_resolver()`` at call time. We assert both helpers return
    the SAME object as a fresh ``get_resolver()`` here, proving the
    singleton is shared, not per-import.
    """
    from fastblocks.core.resolver import get_resolver

    fresh = get_resolver()
    assert test_adapter.current_resolver() is fresh, (
        "get_resolver() in test_adapter and the test must return the "
        "same Oneiric Resolver. Per-process singleton invariant broken."
    )
    assert test_resolver_consistency.current_resolver() is fresh, (
        "get_resolver() in test_resolver_consistency and the test "
        "must return the same Oneiric Resolver."
    )


@pytest.mark.unit
def test_registration_from_module_a_observable_from_module_b() -> None:
    """A Candidate registered in ``test_adapter`` is resolvable here.

    This is the Phase 1.5.4 acceptance criterion: ``register`` from
    one module, ``resolve`` from another, get the same Candidate.
    """
    assert _RESOLVED_CANDIDATE is not None, (
        f"No Candidate found at ({ADAPTER_DOMAIN!r}, {ADAPTER_KEY!r}). "
        "Registration in test_adapter.py was not observable from "
        "test_resolver_consistency.py — the singleton is broken."
    )


@pytest.mark.unit
def test_resolved_factory_is_the_same_callable_we_registered() -> None:
    """The resolved Candidate's factory must be the function we registered.

    Identity (not just equality) — proves the singleton didn't clone
    or proxy the factory through some intermediate.

    ``Candidate.factory`` is typed ``Callable | str | None`` (Oneiric
    permits string factories even though fastblocks never uses them),
    so ty doesn't narrow to ``Callable`` at this use site. The
    suppression is narrow: it scopes to the one call where we know
    the value is callable (it was registered as one).
    """
    assert _RESOLVED_CANDIDATE is not None
    assert _RESOLVED_CANDIDATE.factory is test_adapter.cross_module_factory, (
        "Resolved Candidate.factory must be the SAME callable as "
        "the one registered in test_adapter.cross_module_factory."
    )


@pytest.mark.unit
def test_factory_invocation_returns_the_registered_sentinel() -> None:
    """Invoking the registered factory returns the sentinel instance."""
    assert RESOLVED_INSTANCE is SENTINEL_INSTANCE, (
        "Factory() should return the same sentinel CrossModuleAdapter "
        "instance the registration was based on."
    )
    assert isinstance(RESOLVED_INSTANCE, CrossModuleAdapter)


@pytest.mark.unit
def test_clean_resolver_fixture_resets_singleton_between_tests() -> None:
    """The ``clean_resolver`` autouse fixture isolates each test.

    After the prior tests ran (which registered a Candidate via
    ``test_adapter._register_once``), the singleton's registrations
    should be gone now — the teardown step of ``clean_resolver``
    ran between tests.

    We assert this by doing a FRESH resolve (via the facade) and
    expecting ``None`` — proving the prior test's registration did
    not leak. (We can't reuse the cached ``_RESOLVED_CANDIDATE``
    here because that was populated at module-import time, which
    only happens once per test session.)
    """
    from fastblocks.core.resolver import FastblocksRegistry, get_resolver

    fresh_resolve = FastblocksRegistry(get_resolver()).resolve(
        ADAPTER_DOMAIN, ADAPTER_KEY
    )
    assert fresh_resolve is None, (
        "clean_resolver should clear the singleton at teardown so "
        "this test sees an empty registry. If this fails, the "
        "fixture's teardown is missing or broken."
    )


@pytest.mark.unit
def test_can_register_and_resolve_within_a_single_test() -> None:
    """After fixture reset, register + resolve inside one test.

    Belt-and-suspenders check that the ``clean_resolver`` reset at
    setup gives us a clean slate — registering a NEW Candidate now
    and immediately resolving it works end-to-end.
    """
    from fastblocks.core.resolver import FastblocksRegistry, get_resolver

    registry = FastblocksRegistry(get_resolver())

    class LocalSentinel:
        pass

    sentinel = LocalSentinel()
    assert registry.register_candidate(
        "test", "isolated", factory=lambda: sentinel
    )

    resolved = registry.resolve("test", "isolated")
    assert resolved is not None
    # Narrow suppression: Candidate.factory is typed ``Callable | str``
    # in Oneiric; fastblocks always uses callables, so the assertion
    # below is safe.
    assert resolved.factory() is sentinel  # ty: ignore[call-non-callable]