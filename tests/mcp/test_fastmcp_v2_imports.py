"""Phase 6 follow-up Wave 6 / Task 1 — FastMCP v2 import regression test.

Production code MUST use ``from fastmcp import FastMCP`` (v2 split), NOT
``from mcp.server.fastmcp import FastMCP`` (v1 path that breaks under
``fastmcp>=3``). The v1 path raises ``ModuleNotFoundError`` at import time
because fastmcp 3.x removed the ``mcp.server.fastmcp`` shim.

Per the Phase 6 followup ledger, this regression blocks end-to-end runtime
verification: prod code imports ``FastMCP`` lazily inside
``FastBlocksMCPServer.initialize()``, but ``fastblocks.mcp.capabilities``
imports it at module top-level (any consumer that imports the public
capability surface triggers the v1 ImportError immediately).
"""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.unit
def test_capabilities_module_uses_v2_fastmcp_import() -> None:
    """``fastblocks.mcp.capabilities`` must import successfully under fastmcp>=3.

    Before the fix: ``from mcp.server.fastmcp import FastMCP`` at module
    top-level raises ``ModuleNotFoundError`` because fastmcp 3.x removed
    the ``mcp.server.fastmcp`` shim package.

    After the fix: the module imports cleanly and re-exports a ``FastMCP``
    symbol sourced from the v2 ``fastmcp`` package.
    """
    module = importlib.import_module("fastblocks.mcp.capabilities")
    # The module exposes ``FastMCP`` as a module-level binding for type
    # annotations (see ``_TOOL_CAPABILITY: dict[str, dict[str, tuple]]``).
    # Whatever the binding name is, it must resolve through fastmcp>=3.
    assert hasattr(module, "FastMCP"), (
        "fastblocks.mcp.capabilities is expected to re-export FastMCP for "
        "type-annotation use; missing after v2 migration?"
    )


@pytest.mark.unit
def test_capabilities_fastmcp_resolves_via_fastmcp_package() -> None:
    """The ``FastMCP`` symbol re-exported by capabilities must come from ``fastmcp``.

    Guards against a regression where someone migrates to
    ``from fastmcp import FastMCP`` but accidentally re-exports the
    legacy v1 alias from a different package. The check confirms the
    symbol's ``__module__`` is rooted at ``fastmcp``.
    """
    module = importlib.import_module("fastblocks.mcp.capabilities")
    fastmcp_obj = module.FastMCP
    assert fastmcp_obj.__module__.startswith("fastmcp"), (
        f"Expected FastMCP from the v2 fastmcp package; "
        f"got module={fastmcp_obj.__module__!r}"
    )


@pytest.mark.unit
async def test_server_module_can_construct_fastmcp_instance_v2() -> None:
    """``FastBlocksMCPServer.initialize()`` must produce a v2 ``FastMCP`` server.

    Before the fix: the lazy import
    ``from mcp.server.fastmcp import FastMCP`` inside ``initialize()``
    raises ``ImportError``, which the surrounding ``except ImportError``
    catches and silently degrades. ``_initialized`` stays ``False`` and the
    server reports as operational even though it is unusable.

    After the fix: the lazy import resolves via ``fastmcp`` v2 and
    ``_server`` is bound to a real ``fastmcp.FastMCP`` instance.
    """
    from fastmcp import FastMCP

    from fastblocks.mcp.server import FastBlocksMCPServer

    server_obj = FastBlocksMCPServer(name="test-v2-runtime")
    await server_obj.initialize()

    assert server_obj._initialized is True, (
        "FastBlocksMCPServer.initialize() should succeed under fastmcp>=3; "
        "the ImportError fallback path was triggered."
    )
    assert isinstance(server_obj._server, FastMCP), (
        f"Expected _server to be a fastmcp.FastMCP instance; "
        f"got {type(server_obj._server).__name__}"
    )
