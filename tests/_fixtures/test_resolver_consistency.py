"""Phase 1.5.4 cross-module test fixture: resolves + asserts identity.

This module is imported by ``tests/core/test_resolver_cross_module.py``
to prove that registrations from ``tests/_fixtures/test_adapter.py``
are observable here, via the shared ``get_resolver()`` singleton.

What this module does at import time:
- Resolves the adapter registered by ``test_adapter.py`` (via the
  shared singleton) and stashes the resolved Candidate + factory
  output for identity assertions in the pytest test.

If the singleton invariant breaks, the resolve below returns
``None`` (the registration in ``test_adapter`` would be invisible)
and the pytest test fails.
"""

from __future__ import annotations

from fastblocks.core.resolver import FastblocksRegistry, get_resolver
from oneiric.core.resolution import Candidate

from tests._fixtures.test_adapter import (
    ADAPTER_DOMAIN,
    ADAPTER_KEY,
    SENTINEL_INSTANCE,
    cross_module_factory,
)


def current_resolver():
    """Return ``get_resolver()`` evaluated AT CALL TIME.

    See ``tests/_fixtures/test_adapter.py::current_resolver`` for the
    rationale (the ``clean_resolver`` fixture resets state between
    tests, so a function — not a module-level constant — is the
    right shape).
    """
    return get_resolver()


# Resolve at import time. This is the only module-level state we
# keep, and it's safe because it captures the FACTORY IDENTITY of
# the Candidate registered by ``test_adapter``. The Candidate object
# itself is a plain dataclass — it doesn't depend on the underlying
# Resolver after registration. So even if the Resolver is reset
# between tests, this captured Candidate still points to the same
# factory function.
_RESOLVED_CANDIDATE: Candidate | None = FastblocksRegistry(
    current_resolver()
).resolve(ADAPTER_DOMAIN, ADAPTER_KEY)

# Invoke the factory to capture the resolved sentinel instance for
# identity comparison in the pytest test. ``Candidate.factory`` is
# typed ``Callable | str | None`` in Oneiric — fastblocks never uses
# the string form, so the narrow suppression is safe here.
RESOLVED_INSTANCE = (
    _RESOLVED_CANDIDATE.factory()  # ty: ignore[call-non-callable]
    if _RESOLVED_CANDIDATE is not None
    else None
)
