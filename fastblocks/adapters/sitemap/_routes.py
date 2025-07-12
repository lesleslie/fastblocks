import typing as t

from acb.adapters import import_adapter
from acb.depends import depends
from starlette.routing import Route
from fastblocks.adapters.sitemap._base import SitemapProtocol


def get_sitemap_adapter() -> SitemapProtocol:
    return t.cast("SitemapProtocol", import_adapter("sitemap"))


def sitemap_endpoint(request: t.Any) -> t.Any:
    adapter = get_sitemap_adapter()
    return depends.get(adapter.sitemap)(request)


routes = [Route("/sitemap.xml", sitemap_endpoint)]
sitemap_routes: dict[str, t.Any] = {"sitemap_endpoint": sitemap_endpoint}
