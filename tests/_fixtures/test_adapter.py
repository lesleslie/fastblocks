"""Phase 1.5.4 cross-module test fixture: registers a Candidate.

Per the Phase 1.5.4 spec, this module performs import-time
registration via the FastblocksRegistry facade. A *different* test
module (``tests/_fixtures/test_resolver_consistency.py``) then
resolves the registered Candidate and asserts it sees the same
singleton instance and the same registered factory output.

The point of the two-module split is to prove that:
- The underlying Oneiric ``Resolver`` (returned by ``get_resolver()``)
  is shared across modules — one singleton per process, accessible
  from any importer.
- Registering from module A is observable from module B without any
  hand-shaking — the singleton is the implicit shared bus.
- ``Factory()`` invocation produces a stable instance when the
  factory itself is a single Callable (registered once).

If the singleton invariant breaks (e.g., a future refactor accidentally
introduces a per-module ``Resolver()``), the cross-module test fails:
the registration here would be invisible to ``test_resolver_consistency``.

Note on naming: this module's class is called ``CrossModuleAdapter``
(not ``Test*``) so pytest does not try to collect it as a test class.
"""

from __future__ import annotations

from fastblocks.core.resolver import FastblocksRegistry, get_resolver

# Module-level constants — referenced by the test_resolver_consistency
# module to assert that the resolved factory is THE factory we
# registered (same identity, not just same value).
ADAPTER_DOMAIN = "fastblocks"
ADAPTER_KEY = "phase1_5_4_cross_module"


def current_resolver():
    """Return ``get_resolver()`` evaluated AT CALL TIME.

    This is a function (not a module-level constant) because the
    ``clean_resolver`` autouse fixture resets the singleton's
    lazy-init cache between tests. Module-level state captured at
    import time would be stale by the time the test asserts it.

    Used by the cross-module test to prove the singleton is shared,
    not per-import.
    """
    return get_resolver()


class CrossModuleAdapter:
    """Sentinel class whose identity we assert across modules.

    The factory below returns a SINGLETON instance of this class
    so the test can compare resolved-instance identity with the
    module-level ``SENTINEL_INSTANCE``.
    """

    def __init__(self) -> None:
        self.born_at = id(self)


# Module-level singleton — every factory invocation returns the
# SAME instance, so identity assertions are deterministic.
SENTINEL_INSTANCE = CrossModuleAdapter()


def cross_module_factory() -> CrossModuleAdapter:
    """The factory registered below. Returns the module-level singleton."""
    return SENTINEL_INSTANCE


def _register_once() -> None:
    """Perform the registration. Idempotent: only registers if missing.

    The ``clean_resolver`` autouse fixture (in ``tests/conftest.py``)
    clears the singleton between tests, so a re-import of this module
    could re-trigger registration. Wrapping in ``_register_once`` and
    gating on the ``REGISTERED`` flag prevents double-registration
    within a single test session (which would itself be a
    registration test failure — but the gate is defensive).
    """
    global _REGISTERED
    if _REGISTERED:
        return
    registry = FastblocksRegistry(get_resolver())
    registry.register_candidate(
        ADAPTER_DOMAIN,
        ADAPTER_KEY,
        factory=cross_module_factory,
        metadata={"source": "tests/_fixtures/test_adapter.py"},
    )
    _REGISTERED = True


_REGISTERED = False

# Import-time side effect: register immediately when this module
# is imported by the test.
_register_once()
