import sys
import types
import typing as t

import pytest


@pytest.fixture
def mock_sitemap_routes() -> dict[str, dict[str, str]]:
    return {
        "route1": {
            "changefreq": "daily",
            "priority": "0.7",
        },
        "route2": {
            "changefreq": "weekly",
            "priority": "0.5",
        },
    }


@pytest.mark.unit
class TestSitemapRoutes:
    def setup_method(self) -> None:
        for mod in list(sys.modules.keys()):
            if mod.startswith("fastblocks"):
                sys.modules.pop(mod, None)

    def test_sitemap_routes_creation(
        self,
        mock_sitemap_routes: dict[str, dict[str, str]],
    ) -> None:
        sys.modules["fastblocks"] = types.ModuleType("fastblocks")
        sys.modules["fastblocks.adapters"] = types.ModuleType("fastblocks.adapters")
        sys.modules["fastblocks.adapters.sitemap"] = types.ModuleType(
            "fastblocks.adapters.sitemap",
        )

        routes_module = types.ModuleType("fastblocks.adapters.sitemap._routes")
        setattr(routes_module, "routes", mock_sitemap_routes)
        sys.modules["fastblocks.adapters.sitemap._routes"] = routes_module

        from fastblocks.adapters.sitemap._routes import routes

        assert routes == mock_sitemap_routes
        assert len(routes) == 2
        assert "route1" in routes
        assert "route2" in routes

        routes_dict: dict[str, dict[str, str]] = t.cast(
            "dict[str, dict[str, str]]",
            routes,
        )

        if "route1" in routes_dict:
            route1 = routes_dict["route1"]
            assert route1.get("changefreq") == "daily"

        if "route2" in routes_dict:
            route2 = routes_dict["route2"]
            assert route2.get("priority") == "0.5"
