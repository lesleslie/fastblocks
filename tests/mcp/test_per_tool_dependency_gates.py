"""Phase 4 v2.1 Commit 1 — per-tool dependency gate tests.

Verifies that the three ``_is_X_available()`` gates probe resolved state
(not lazy construction) and never raise.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_is_template_available_returns_bool() -> None:
    from fastblocks.mcp.capabilities import _is_template_available

    result = _is_template_available()
    assert isinstance(result, bool), (
        f"_is_template_available() must return bool; got {type(result).__name__}"
    )


@pytest.mark.unit
def test_is_template_available_false_when_jinja2_and_htmy_missing() -> None:
    """Template gate returns False when both Jinja2 and HTMY are absent.

    Pins the gate's try/except ImportError branch. Both ``jinja2`` and
    ``htmy`` are top-level packages in this project, so blocking them
    by exact name is correct (no submodule-vs-package distinction).
    """
    import builtins
    import sys

    real_import = builtins.__import__

    def blocking_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "jinja2" or name == "htmy":
            raise ImportError(f"blocked {name} for test")
        return real_import(name, globals, locals, fromlist, level)

    builtins.__import__ = blocking_import
    sys.modules.pop("jinja2", None)
    sys.modules.pop("htmy", None)
    try:
        from fastblocks.mcp.capabilities import _is_template_available
        result = _is_template_available()
    finally:
        builtins.__import__ = real_import
    assert result is False, (
        f"_is_template_available() should return False when both jinja2 and "
        f"htmy imports fail; got {result!r}"
    )


@pytest.mark.unit
def test_is_component_available_returns_bool() -> None:
    from fastblocks.mcp.capabilities import _is_component_available

    result = _is_component_available()
    assert isinstance(result, bool), (
        f"_is_component_available() must return bool; got {type(result).__name__}"
    )


@pytest.mark.unit
def test_is_component_available_false_when_htmy_components_missing() -> None:
    """Component gate returns False when htmy_components is not importable.

    Pins the gate's try/except ImportError branch. Two patches are
    required:
    1. Pop ``htmy_components`` from ``sys.modules`` so the cached lookup
       doesn't bypass our ``__import__`` monkey-patch.
    2. Block at the TOP-LEVEL package (``fastblocks.adapters.templates``),
       not the submodule, because Python's ``from X import Y`` first
       calls ``__import__("X")`` with the top-level package name — the
       submodule name is only passed on a SECOND call if the attribute
       isn't already cached on the package object.

    Using ``sys.modules[name] = None`` as an alternative — Python treats
    a None entry as "import failed" and raises ImportError on attribute
    lookup.
    """
    import builtins
    import sys

    real_import = builtins.__import__

    def blocking_import(name, globals=None, locals=None, fromlist=(), level=0):
        # Block the top-level package so the second-level getattr fails.
        if name == "fastblocks.adapters.templates":
            raise ImportError(f"blocked {name} for test")
        return real_import(name, globals, locals, fromlist, level)

    builtins.__import__ = blocking_import
    sys.modules.pop("fastblocks.adapters.templates.htmy_components", None)
    sys.modules.pop("fastblocks.adapters.templates", None)
    try:
        from fastblocks.mcp.capabilities import _is_component_available
        result = _is_component_available()
    finally:
        builtins.__import__ = real_import
    assert result is False, (
        f"_is_component_available() must return False when htmy_components "
        f"is not importable; got {result!r}"
    )


@pytest.mark.unit
def test_is_adapter_available_probes_resolved_state_not_construction() -> None:
    """Adapter gate must check resolved state, not lazy-construct Resolver.

    The function imports FastblocksRegistry and get_resolver lazily
    inside its body. Patches must target the SOURCE module
    (``fastblocks.core.resolver``), not the ``capabilities`` module —
    because ``from X import Y`` in the function body looks up ``Y`` on
    module ``X`` at call time, not on the importer's namespace.

    The patch makes ``FastblocksRegistry(get_resolver()).list_active(
    'fastblocks')`` return ``[]`` → gate returns ``False``. A gate
    that lazy-constructs would return ``True`` here.
    """
    with patch(
        "fastblocks.core.resolver.FastblocksRegistry"
    ) as mock_registry_cls:
        mock_registry = MagicMock()
        mock_registry.list_active.return_value = []  # no active candidates
        mock_registry_cls.return_value = mock_registry
        with patch(
            "fastblocks.core.resolver.get_resolver",
            return_value=MagicMock(),
        ):
            from fastblocks.mcp.capabilities import _is_adapter_available
            result = _is_adapter_available()
    assert result is False, (
        f"_is_adapter_available() should return False when list_active('fastblocks') "
        f"returns []; got {result!r}. The gate may be lazy-constructing instead "
        f"of probing resolved state (P1 #7 fix)."
    )


@pytest.mark.unit
def test_gates_never_raise() -> None:
    """All three gates must catch any exception and return False.

    The gates are called from capability registration functions; an
    unhandled exception would crash MCP server startup. Patch targets
    the SOURCE module (``fastblocks.core.resolver``) because the
    function body imports ``FastblocksRegistry`` lazily from there.
    """
    from fastblocks.mcp.capabilities import _is_adapter_available
    with patch(
        "fastblocks.core.resolver.FastblocksRegistry",
        side_effect=RuntimeError("simulated bootstrap failure"),
    ):
        result = _is_adapter_available()
    assert result is False, (
        f"_is_adapter_available() must catch exceptions and return False; "
        f"got {result!r}"
    )
