from __future__ import annotations

import typing as t

from starlette.responses import Response
from starlette.routing import Route

from fastblocks.adapters.oneiric_helper import resolve_instance
from oneiric.core.resolution import Resolver

from fastblocks.adapters.sitemap._base import SitemapProtocol


# Custom implementations for ACB compatibility
class AdapterStatus:
    """Custom AdapterStatus for Oneiric compatibility."""

    STABLE = "STABLE"
    BETA = "BETA"
    ALPHA = "ALPHA"
    EXPERIMENTAL = "EXPERIMENTAL"


def debug(msg: str) -> None:
    """Custom debug function for Oneiric compatibility."""
    print(f"[DEBUG] {msg}")


# Oneiric resolver for dependency injection
depends = Resolver()


def import_adapter(adapter_name: str) -> None:
    """Custom implementation for Oneiric compatibility."""


def get_sitemap_adapter() -> SitemapProtocol:
    return t.cast("SitemapProtocol", import_adapter("sitemap"))


_EMPTY_SITEMAP_BODY = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
)


def sitemap_endpoint(request: t.Any) -> t.Any:
    adapter = get_sitemap_adapter()
    try:
        instance = resolve_instance(depends, "fastblocks", adapter.sitemap)
        if instance is None:
            return Response(
                _EMPTY_SITEMAP_BODY,
                media_type="application/xml",
                status_code=503,
            )
        return instance(request)
    except Exception:  # noqa: BLE001
        return Response(
            _EMPTY_SITEMAP_BODY,
            media_type="application/xml",
            status_code=503,
        )


routes = [Route("/sitemap.xml", sitemap_endpoint)]
sitemap_routes: dict[str, t.Any] = {"sitemap_endpoint": sitemap_endpoint}
