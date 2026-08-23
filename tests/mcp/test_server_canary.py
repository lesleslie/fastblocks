"""MCP server integration canary.

3 scenarios per Erratum 11 (was 2 in v3.1, added suppress-mask regression):
1. Tools list tuple: FastMCP.list_tools() returns the 7 tools registered by
   register_fastblocks_tools, matching profiles.FASTBLOCKS_TOOLS
   (substituted: brief's FastBlocksMCPServer.list_tools() does not exist;
    server.py has no list_tools method (verified 2026-08-23) and
    FastMCP.list_tools() is async, so the substitute initializes the server
    and asserts the registered tool names against FASTBLOCKS_TOOLS).
2. ASGI _get_http_app path coverage: spy on register_fastblocks_tools,
   assert called with FastMCP (weakened per Erratum 11: isinstance check,
   not identity).
3. suppress(Exception) regression: patch register_fastblocks_tools with
   side_effect=RuntimeError, assert _get_http_app() still returns non-None
   (catches the with suppress(Exception) orphan path ADR 0011 Decision 6).
"""

from __future__ import annotations

from unittest import mock

from mcp.server.fastmcp import FastMCP

from fastblocks.mcp.profiles import FASTBLOCKS_TOOLS
from fastblocks.mcp.server import FastBlocksMCPServer


async def test_tools_list_matches_7_name_tuple() -> None:
    """Scenario 1: FastBlocksMCPServer registers 7 tools matching FASTBLOCKS_TOOLS.

    Substituted from brief: the brief called `server.list_tools()` synchronously,
    but FastBlocksMCPServer has no list_tools() method (verified 2026-08-23
    against fastblocks/mcp/server.py: only initialize / start / stop /
    _register_tools / _register_resources are defined). FastMCP.list_tools()
    is async. The canary's intent — verifying that the registered tool set
    matches the canonical FASTBLOCKS_TOOLS tuple — is preserved by initializing
    the server and inspecting the FastMCP instance it wraps.
    """
    server = FastBlocksMCPServer()
    await server.initialize()
    assert server._server is not None, (
        "FastBlocksMCPServer._server is None after initialize() — "
        "FastMCP import or registration failed"
    )
    tools = await server._server.list_tools()
    assert len(tools) == 7
    assert tuple(t.name for t in tools) == FASTBLOCKS_TOOLS


def test_get_http_app_calls_register_fastblocks_tools() -> None:
    """Scenario 2: _get_http_app invokes register_fastblocks_tools with FastMCP.

    Per Erratum 11: identity check was impossible (mcp_instance is local
    to _get_http_app). Use isinstance + name check instead.
    """
    from fastblocks.mcp import server as mcp_server

    with mock.patch("fastblocks.mcp.tools.register_fastblocks_tools") as mock_register:
        app = mcp_server._get_http_app()
        assert app is not None
        assert mock_register.called
        assert isinstance(mock_register.call_args.args[0], FastMCP)
        assert mock_register.call_args.args[0].name == "fastblocks"


def test_suppress_exception_orphan_path_returns_app() -> None:
    """Scenario 3: with suppress(Exception) masks registration failure but app is still returned.

    Catches the ADR 0011 Decision 6 orphan path: if register_fastblocks_tools
    raises mid-body, _get_http_app should NOT crash the import. The test
    verifies _get_http_app returns non-None even when registration fails
    (which is the actual current behavior per the with suppress(Exception)
    wrapper at fastblocks/mcp/server.py:157-164).
    """
    from fastblocks.mcp import server as mcp_server

    with mock.patch(
        "fastblocks.mcp.tools.register_fastblocks_tools",
        side_effect=RuntimeError("simulated failure"),
    ):
        app = mcp_server._get_http_app()
        # Even with registration failure, the app should still be returned
        # (because of with suppress(Exception)). This catches the orphan
        # path: if a future refactor removes the suppress wrapper, this
        # test would change behavior, signaling the regression.
        assert app is not None
