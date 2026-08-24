"""Production-grade wrapper for ``FastMCP.add_tool`` / ``server.tool``.

Per Δ32: lifts the monkeypatch from
``tests/mcp/test_consumer_pattern_wiring.py:61-74`` into a real
production helper. The monkeypatch short-circuits when ``fn`` is a
``Tool`` instance (mcp_common 0.19.0 passes a Tool object to
``server.add_tool(...)``, which would otherwise fail in pydantic 2 / Py
3.14 because ``Tool.from_function(tool_obj)`` calls ``tool_obj.__name__``
and pydantic ``BaseModel.__getattr__`` raises instead of falling
through).

Per Δ47: ``add_tool_safe`` is idempotent — calling it twice with the
same ``name`` does NOT re-register the tool on the FastMCP server. The
second call short-circuits and returns the existing registration.

Exposes ``add_tool_safe(server, name, fn, **kwargs) -> None`` — same
contract as ``server.add_tool(...)`` minus the pydantic-compat bug.
"""
from __future__ import annotations

from typing import Any

__all__ = [
    "add_tool_safe",
]

# Per Δ32: both Tool classes from the active install may appear in
# ``fn``. We duck-type on the ``name`` attribute (every Tool object has
# it) rather than importing either class directly — keeps the helper
# independent of which mcp_common / fastmcp version is installed.
_TOOL_LIKE_TYPES: tuple[type, ...] = ()


def _is_tool_like(fn: Any) -> bool:
    """Return True if ``fn`` is a Tool instance (any flavor).

    Duck-type check: Tool objects expose ``.name`` and ``.fn`` (the
    backing function). Plain callables don't have ``.fn``. We use
    ``hasattr`` rather than ``isinstance`` against a specific Tool
    class because the active install may be ``fastmcp`` v2 (Tool from
    ``fastmcp.tools.base``) or the legacy ``mcp.server.fastmcp.tools``
    package — same shape, different import path.
    """
    return callable(fn) and hasattr(fn, "fn") and hasattr(fn, "name")


def add_tool_safe(server: Any, name: str, fn: Any, **kwargs: Any) -> Any:
    """Idempotently register ``fn`` as tool ``name`` on ``server``.

    Behavior:
      * If ``fn`` is a Tool instance (pydantic BaseModel) and a tool
        with the same name is already registered, return that
        registration without touching the server (idempotent).
      * If ``fn`` is a Tool instance and no tool with that name is
        registered, inject it directly into ``server._tool_manager._tools``.
      * If ``fn`` is a plain callable, delegate to ``server.add_tool(fn, name=name, **kwargs)``.
      * If ``fn`` is already registered under ``name``, return the
        existing registration without re-registering.

    Returns the registered Tool object (whatever ``server.add_tool``
    returns or whatever was already in ``_tool_manager._tools[name]``).
    """
    # Idempotency: short-circuit if the tool is already registered.
    existing = None
    tool_manager = getattr(server, "_tool_manager", None)
    if tool_manager is not None:
        existing = tool_manager._tools.get(name)  # type: ignore[attr-defined]

    if existing is not None:
        return existing

    # Per Δ32: Tool instance branch — bypass ``server.add_tool```` (which
    # would call ``Tool.from_function(fn)`` → ``fn.__name__`` and fail on
    # a pydantic BaseModel in Py 3.14). Inject directly into the manager.
    if _is_tool_like(fn):
        if tool_manager is None:
            msg = (
                f"Server {type(server).__name__!r} has no _tool_manager; "
                "cannot register Tool instance directly"
            )
            raise AttributeError(msg)
        tool_manager._tools[name] = fn  # type: ignore[attr-defined]
        return fn

    # Plain function / callable path — delegate to the server's add_tool.
    # ``server.add_tool(fn)`` is the v2 fastmcp signature (single
    # positional arg; Tool name comes from ``fn.__name__`` or the Tool
    # object's ``.name``). The legacy mcp_common / ``mcp.server.fastmcp``
    # signature ``server.add_tool(fn, name=name)`` would fail here; we
    # drop the ``name`` kwarg unconditionally and rely on the Tool object's
    # own ``.name`` attribute for the canonical identity.
    try:
        return server.add_tool(fn, name=name, **kwargs)
    except TypeError:
        # v2 fastmcp signature — single positional arg.
        return server.add_tool(fn)
