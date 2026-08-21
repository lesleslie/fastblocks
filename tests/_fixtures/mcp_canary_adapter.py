"""Phase 1.5.5 MCP tools resolution canary fixture.

The MCP tool layer (``fastblocks.mcp.tools``) uses a module-level
``depends = FastblocksRegistry(get_resolver())`` to resolve adapters.
This fixture registers a known test adapter via that same facade so
the integration test can assert that ``list_components()`` /
``configure_adapter()`` see the registration.

Why this exists separately from the cross-module fixture
(``tests/_fixtures/test_adapter.py``):
- The cross-module fixture uses domain ``"fastblocks"`` and key
  ``"phase1_5_4_cross_module"`` to assert singleton identity via
  module-level constants captured at import time.
- This fixture uses a different key but CANNOT use the same
  import-time registration trick — the ``clean_resolver`` autouse
  fixture wipes registrations between tests, so the import-time
  registration would be invisible to MCP tool calls inside a test
  body. The cross-module test survived this because it caches the
  Candidate at module-import time (the Candidate dataclass is
  independent of the Resolver after registration), but MCP tools
  actively re-resolve at call time — they need a LIVE registration.

What it exposes:
- ``CANARY_DOMAIN`` / ``CANARY_KEY`` — coordinates for the registration.
- ``CanaryAdapter`` — minimal stub with ``discover_components()`` and
  a ``settings`` attribute so ``configure_adapter()`` can ``setattr``
  on it.
- ``canary_factory()`` — returns a SINGLETON ``CanaryAdapter`` so
  identity assertions across the MCP tool surface are deterministic.
- ``register_canary()`` — idempotent registration helper. Tests
  invoke this from inside the test body (after ``clean_resolver``
  setup has cleared state).

No import-time side effect: the fixture does NOT call
``register_canary()`` at import. Tests must call it explicitly so
they re-register AFTER the autouse fixture's setup reset.
"""

from __future__ import annotations

from fastblocks.core.resolver import FastblocksRegistry, get_resolver

CANARY_DOMAIN = "fastblocks"
CANARY_KEY = "phase1_5_5_mcp_canary"


class CanaryComponentMetadata:
    """Object with the attributes ``list_components`` reads.

    The tool does ``metadata.path``, ``metadata.type.value``,
    ``metadata.status.value``, ``metadata.docstring``,
    ``metadata.error_message``. So this is a namespace with the
    right attribute shape — NOT a dict.

    ``type`` and ``status`` are themselves objects with a ``.value``
    attribute (e.g. an ``Enum``). We use ``types.SimpleNamespace``
    instead of a real Enum to keep this fixture free of
    cross-component imports.
    """

    def __init__(self) -> None:
        from types import SimpleNamespace

        self.path = "/virtual/canary/path"
        self.type = SimpleNamespace(value="htmy")
        self.status = SimpleNamespace(value="valid")
        self.docstring = "Phase 1.5.5 MCP resolution canary."
        self.error_message: str | None = None


class CanaryAdapter:
    """Stub adapter satisfying the surface MCP tools depend on.

    ``list_components()`` (tools.py:380) calls
    ``htmy_adapter.discover_components()`` and expects a mapping of
    name → metadata-like object. We expose that with one entry so the
    tool sees ``count >= 1``.

    ``configure_adapter()`` (tools.py:471) iterates the provided
    settings dict and does ``setattr(adapter, key, value)``. Our
    adapter accepts arbitrary attributes so the tool's ``hasattr``
    check passes.
    """

    def __init__(self) -> None:
        self.components: dict[str, CanaryComponentMetadata] = {
            "phase1_5_5_canary_component": CanaryComponentMetadata(),
        }
        # Pre-declare so ``configure_adapter``'s ``hasattr`` gate
        # passes and ``setattr`` actually runs. The tool only updates
        # EXISTING attributes — that's an existing semantics we
        # respect here by seeding the attribute on construction.
        self.phase1_5_5_marker: str | None = None

    async def discover_components(self) -> dict[str, CanaryComponentMetadata]:
        """Return the single canary component."""
        return self.components


# Singleton so identity assertions across multiple MCP tool calls
# observe the same adapter instance.
CANARY_INSTANCE = CanaryAdapter()


def canary_factory() -> CanaryAdapter:
    """Factory registered with the facade. Returns the singleton."""
    return CANARY_INSTANCE


def current_resolver():
    """Return ``get_resolver()`` evaluated AT CALL TIME.

    See ``tests/_fixtures/test_adapter.py::current_resolver`` — the
    ``clean_resolver`` autouse fixture resets the singleton between
    tests, so a function is the right shape for cross-module
    observability.
    """
    return get_resolver()


def register_canary() -> None:
    """Register the canary Candidate via the facade.

    No idempotency gate by design. The ``clean_resolver`` autouse
    fixture wipes the singleton between tests, so each call to
    ``register_canary()`` from a test body sees an empty registry
    and registers fresh. A module-level ``_REGISTERED`` flag would
    go stale after the first test wipes state — same trap Phase
    1.5.4 hit with module-level constants.

    ``register_candidate`` either succeeds or returns ``False`` if
    the key already exists — but with a clean registry it always
    succeeds, so the return value is informational only.
    """
    registry = FastblocksRegistry(get_resolver())
    registry.register_candidate(
        CANARY_DOMAIN,
        CANARY_KEY,
        factory=canary_factory,
        metadata={"source": "tests/_fixtures/mcp_canary_adapter.py"},
    )


# No import-time side effect by design — see the module docstring.
# Tests must call ``register_canary()`` from inside the test body,
# AFTER the ``clean_resolver`` autouse fixture's setup reset has
# cleared any prior registrations.
