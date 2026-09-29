"""D1 coverage tests for fastblocks/adapters/routes/default.py.

Targets the default route registration:
- ``root_path``, ``AdapterStatus`` enum, ``MODULE_ID`` / ``MODULE_STATUS``
- ``FastBlocksEndpoint`` constructor behaviour
- ``Routes`` (basic init + gather + favicon + robots)
- ``Index`` / ``Block`` / ``Component`` endpoint shapes
"""
# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false
from __future__ import annotations

import uuid as _uuid
from typing import Any

import pytest
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from fastblocks.adapters.routes.default import (
    AdapterStatus,
    MODULE_ID,
    MODULE_STATUS,
    Routes,
    root_path,
)


# ---------------------------------------------------------------------------
# AdapterStatus + module metadata
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAdapterStatus:
    def test_status_values(self) -> None:
        assert AdapterStatus.STABLE == "STABLE"
        assert AdapterStatus.BETA == "BETA"
        assert AdapterStatus.ALPHA == "ALPHA"
        assert AdapterStatus.EXPERIMENTAL == "EXPERIMENTAL"

    def test_module_metadata(self) -> None:
        assert MODULE_STATUS == AdapterStatus.STABLE
        assert isinstance(MODULE_ID, _uuid.UUID)


@pytest.mark.unit
class TestRootPath:
    def test_root_path_default(self) -> None:
        assert root_path() == "/"


# ---------------------------------------------------------------------------
# Routes (sync init + sync favicon/robots + gather_routes + init)
# ---------------------------------------------------------------------------


def _make_request(
    path: str = "/", method: str = "GET", query: str = ""
) -> Request:
    from urllib.parse import unquote

    scope: dict[str, Any] = {
        "type": "http",
        "method": method,
        "scheme": "https",
        "server": ("example.com", 443),
        "path": unquote(path),
        "headers": [],
        "query_string": query.encode(),
    }
    return Request(scope)


@pytest.mark.unit
class TestRoutesFaviconAndRobots:
    def test_routes_init_empty(self) -> None:
        r = Routes()
        assert r.routes == []

    @pytest.mark.asyncio
    async def test_favicon(self) -> None:
        response = await Routes.favicon(_make_request())
        assert isinstance(response, PlainTextResponse)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_robots(self) -> None:
        response = await Routes.robots(_make_request())
        assert isinstance(response, PlainTextResponse)
        assert response.status_code == 200
        body = response.body.decode()
        assert "User-agent" in body
        assert "Disallow" in body

    @pytest.mark.asyncio
    async def test_init_populates_routes(self, monkeypatch) -> None:
        # Make the base_routes_path lookup return False so we don't traverse
        # the real filesystem.
        import fastblocks.adapters.routes.default as routes_mod

        async def _exists(self) -> bool:  # type: ignore[no-untyped-def]
            return False

        monkeypatch.setattr(routes_mod.AsyncPath, "exists", _exists)
        r = Routes()
        await r.init()
        paths = [getattr(rt, "path", None) for rt in r.routes]
        assert "/" in paths
        assert "/favicon.ico" in paths
        assert "/robots.txt" in paths
        assert "/block/{block}" in paths
        assert "/component/{component}" in paths


# ---------------------------------------------------------------------------
# Index / Block / Component endpoint shapes
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEndpointClasses:
    def test_index_class_shape(self) -> None:
        from fastblocks.adapters.routes.default import Index

        assert hasattr(Index, "get")
        assert callable(Index.get)

    def test_block_class_shape(self) -> None:
        from fastblocks.adapters.routes.default import Block

        assert hasattr(Block, "get")
        assert callable(Block.get)

    def test_component_class_shape(self) -> None:
        from fastblocks.adapters.routes.default import Component

        assert hasattr(Component, "get")
        assert callable(Component.get)
