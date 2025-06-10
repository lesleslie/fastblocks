import typing as t

from acb.adapters import import_adapter
from acb.depends import depends
from starlette.routing import Route
from fastblocks.adapters.sitemap._base import SitemapProtocol

sitemap_adapter: SitemapProtocol = t.cast(SitemapProtocol, import_adapter("sitemap"))
routes = [Route("/sitemap.xml", depends.get(sitemap_adapter.sitemap))]
sitemap_routes: dict[str, t.Any] = {"sitemap_endpoint": sitemap_adapter.sitemap}
