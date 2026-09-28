"""Wave D coverage backfill for fastblocks/mcp/_add_tool_safe.py.

The 7 statements missing from the prior coverage report (lines 68, 71,
77-84) all live inside the ``add_tool_safe`` body. Each test below
targets one branch so the gate runs cleanly at 67.81%.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastblocks.mcp._add_tool_safe import _is_tool_like, add_tool_safe


class _FakeTool:
    """Stand-in for a fastmcp ``Tool`` instance (duck-types on ``.name`` + ``.fn``)."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.fn = lambda: None  # arbitrary backing callable

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        # _is_tool_like requires the fn to be ``callable()``; Tool
        # instances satisfy that via their own ``__call__``.
        return None


@pytest.mark.unit
class TestIsToolLike:
    """Cover ``_is_tool_like`` directly (a sanity check on the duck-typing predicate)."""

    def test_plain_function_is_not_tool_like(self) -> None:
        def plain() -> None:
            return None

        assert _is_tool_like(plain) is False

    def test_tool_object_is_tool_like(self) -> None:
        assert _is_tool_like(_FakeTool("any")) is True


@pytest.mark.unit
class TestAddToolSafeIdempotency:
    """Cover the early-return branch (lines 66-71)."""

    def test_returns_existing_registration_without_re_registering(self) -> None:
        existing = _FakeTool("echo")
        tool_manager = SimpleNamespace(_tools={"echo": existing})
        # Server object only needs _tool_manager; add_tool should never
        # be called on the early-return path.
        server = SimpleNamespace(_tool_manager=tool_manager, add_tool=pytest.fail)

        result = add_tool_safe(server, "echo", _FakeTool("new"))

        assert result is existing
        # The original registration was not overwritten
        assert tool_manager._tools["echo"] is existing


@pytest.mark.unit
class TestAddToolSafeToolInstance:
    """Cover the Tool-instance branch (lines 76-84)."""

    def test_injects_tool_into_manager_when_no_existing_registration(self) -> None:
        tool_manager = SimpleNamespace(_tools={})
        server = SimpleNamespace(
            _tool_manager=tool_manager,
            add_tool=pytest.fail,  # Tool path bypasses server.add_tool
        )
        new_tool = _FakeTool("ping")

        result = add_tool_safe(server, "ping", new_tool)

        assert result is new_tool
        assert tool_manager._tools["ping"] is new_tool

    def test_raises_when_server_has_no_tool_manager(self) -> None:
        # Server lacks _tool_manager; fn is a Tool instance so the Tool
        # branch fires and raises AttributeError before mutating anything.
        server = SimpleNamespace(_tool_manager=None, add_tool=lambda *a, **k: None)

        with pytest.raises(AttributeError, match="_tool_manager"):
            add_tool_safe(server, "ping", _FakeTool("ping"))


@pytest.mark.unit
class TestAddToolSafePlainCallable:
    """Cover the plain-callable fallback path (line 93)."""

    def test_delegates_to_server_add_tool(self) -> None:
        captured: dict[str, Any] = {}

        def echo() -> str:
            return "hi"

        def fake_add_tool(fn: Any) -> Any:
            captured["fn"] = fn
            return _FakeTool("echo")

        server = SimpleNamespace(
            _tool_manager=SimpleNamespace(_tools={}),
            add_tool=fake_add_tool,
        )

        result = add_tool_safe(server, "echo", echo)

        assert captured["fn"] is echo
        assert isinstance(result, _FakeTool)
        assert result.name == "echo"
