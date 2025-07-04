import typing as t

from ...dependencies import get_acb_subset

import_adapter, depends = get_acb_subset("import_adapter", "depends")
from starlette.routing import Route
from fastblocks.adapters.sitemap._base import SitemapProtocol

sitemap_adapter: SitemapProtocol = t.cast(SitemapProtocol, import_adapter("sitemap"))
routes = [Route("/sitemap.xml", depends.get(sitemap_adapter.sitemap))]
sitemap_routes: dict[str, t.Any] = {"sitemap_endpoint": sitemap_adapter.sitemap}
