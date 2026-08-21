"""Phase 1.5.5 — MCP tools resolution integration test.

Proves that the FastblocksRegistry facade (which
``fastblocks.mcp.tools.depends`` is bound to at module-load) is
actually the surface the MCP tool layer reads from. Without this
test, a future refactor could swap ``depends`` to use a per-module
``Resolver()`` and break the singleton contract silently — the
per-test isolated MCP tool call would still "work" because each
call would construct its own local registry.

Acceptance criteria (from the master plan, Phase 1.5.5):

>  Register a known test adapter via ``mcp_canary_server``
>  session-scoped fixture, assert ``check_adapter_health`` and
>  ``list_components`` return non-empty results via the MCP server
>  surface.

Concretely we assert:

1. ``depends.resolve("fastblocks", CANARY_KEY)`` returns the
   factory-registered Candidate (proves ``depends`` is the facade).
2. Calling the MCP ``configure_adapter`` tool with the canary
   key returns ``success: True`` with the settings applied (proves
   the tool reads through ``depends`` end-to-end).
3. Calling the MCP ``list_components`` tool with an htmy Candidate
   registered returns ``success: True`` and ``count >= 1`` (proves
   ``list_components`` reads through ``depends``).
4. A fresh ``FastblocksRegistry(get_resolver())`` instance also
   resolves the canary (proves the facade ↔ singleton contract,
   not facade-per-construction).
5. ``check_adapter_health`` returns ``success: True`` with a
   non-zero ``count`` (proves the AdapterRegistry layer still works
   under the same MCP tool entry point).

Note on registration timing: the ``clean_resolver`` autouse fixture
in ``tests/conftest.py`` resets the Resolver singleton at setup AND
teardown. So every test in this file calls ``register_canary()``
explicitly from inside the test body, AFTER the setup reset, so the
MCP tools see a fresh registration on every invocation.
"""

from __future__ import annotations

import pytest
from tests._fixtures.mcp_canary_adapter import (
    CANARY_DOMAIN,
    CANARY_INSTANCE,
    CANARY_KEY,
    canary_factory,
    current_resolver,
    register_canary,
)


@pytest.mark.unit
def test_depends_resolves_canary_via_facade() -> None:
    """``fastblocks.mcp.tools.depends`` resolves the canary.

    ``tools.depends`` is a module-level
    ``FastblocksRegistry(get_resolver())``. The canary was registered
    via the same facade in the test body. If ``tools.depends``
    resolved through some other path (e.g. a fresh ``Resolver()``),
    this would return ``None`` and the test would fail — proving
    the facade contract is the live wire.
    """
    from fastblocks.mcp import tools

    register_canary()
    resolved = tools.depends.resolve(CANARY_DOMAIN, CANARY_KEY)
    assert resolved is not None, (
        "MCP tools.depends is not seeing the canary registration. "
        "Expected a fresh FastblocksRegistry(get_resolver()) instance "
        "bound to the singleton; got something that resolves to None."
    )


@pytest.mark.unit
async def test_mcp_configure_adapter_returns_canary_via_depends_path() -> None:
    """Calling the MCP ``configure_adapter`` tool routes through the facade.

    The tool calls ``depends.resolve("fastblocks", adapter_name)``
    then invokes the factory and does ``setattr(adapter, key, value)``
    for each setting. We register a canary whose factory returns a
    stub adapter, then assert the tool's response shows the setting
    was applied.
    """
    from fastblocks.mcp import tools

    register_canary()
    result = await tools.configure_adapter(
        CANARY_KEY, {"phase1_5_5_marker": "set-via-facade"}
    )
    assert result["success"] is True, (
        f"configure_adapter returned failure: {result.get('error')!r}. "
        "This means the MCP tool could not resolve the canary via "
        "depends / FastblocksRegistry."
    )
    assert result["adapter"] == CANARY_KEY
    assert result["settings"] == {"phase1_5_5_marker": "set-via-facade"}
    # Belt-and-suspenders: the singleton instance should now carry
    # the attribute the tool wrote.
    assert CANARY_INSTANCE.phase1_5_5_marker == "set-via-facade"


@pytest.mark.unit
async def test_mcp_list_components_returns_nonempty_via_depends_path() -> None:
    """Calling the MCP ``list_components`` tool returns the canary component.

    The tool resolves ``("fastblocks", "htmy")`` via ``depends``,
    invokes the factory, and awaits ``discover_components()``. We
    register a Candidate under the ``htmy`` key (with the canary
    factory) within the test and then call the tool — proves
    ``list_components`` reads through the facade.
    """
    from fastblocks.core.resolver import FastblocksRegistry
    from fastblocks.mcp import tools

    # Register the canary factory under the ("fastblocks", "htmy") key
    # that ``list_components`` looks up. Uses the same facade the MCP
    # tool layer reads through.
    registry = FastblocksRegistry(current_resolver())
    assert registry.register_candidate(
        "fastblocks",
        "htmy",
        factory=canary_factory,
        metadata={"source": "test_mcp_resolution_integration.py"},
    )

    result = await tools.list_components()
    assert result["success"] is True, (
        f"list_components returned failure: {result.get('error')!r}. "
        "The MCP tool could not resolve ('fastblocks', 'htmy') via the "
        "FastblocksRegistry facade."
    )
    assert result["count"] >= 1, (
        f"Expected at least one component, got count={result.get('count')!r}."
    )
    component_names = [c["name"] for c in result["components"]]
    assert "phase1_5_5_canary_component" in component_names, (
        f"Expected the canary component in {component_names!r}."
    )


@pytest.mark.unit
def test_fresh_facade_instance_sees_canary_registration() -> None:
    """A new facade instance still resolves the canary.

    Constructs ``FastblocksRegistry(get_resolver())`` from scratch and
    asserts it sees the registration made by ``register_canary()``
    inside the test body. If ``FastblocksRegistry`` ever drifted to
    per-construction state, this test would fail (the new facade
    wouldn't see the registration).

    This is the Phase 1.5.4 singleton contract reaffirmed at the MCP
    layer — the facade and the singleton are the SAME thing, not
    two parallel state holders.
    """
    from fastblocks.core.resolver import FastblocksRegistry

    register_canary()
    fresh_facade = FastblocksRegistry(current_resolver())
    resolved = fresh_facade.resolve(CANARY_DOMAIN, CANARY_KEY)
    assert resolved is not None, (
        "Fresh FastblocksRegistry(get_resolver()) could not see the "
        "canary registration made via register_canary(). Facade and "
        "singleton have diverged — the facade is per-construction "
        "state, not a singleton wrapper."
    )


@pytest.mark.unit
async def test_mcp_check_adapter_health_returns_nonempty() -> None:
    """``check_adapter_health`` returns ``success: True`` with count >= 1.

    This tool uses an internal ``AdapterRegistry`` (not the facade),
    but it's still part of the MCP server surface. We assert it
    succeeds in the test environment — proves the tool surface as a
    whole is reachable.
    """
    from fastblocks.mcp import tools

    result = await tools.check_adapter_health()
    assert result["success"] is True, (
        f"check_adapter_health returned failure: {result.get('error')!r}. "
        "The MCP tool layer's AdapterRegistry path is broken."
    )
    assert result["count"] >= 1, (
        f"Expected at least one health check entry, got count={result.get('count')!r}."
    )
