import typing as t

from acb.adapters import import_adapter
from acb.depends import depends
from starlette.routing import Route
from fastblocks.adapters.sitemap._base import SitemapProtocol

# Explicitly cast the import_adapter result to SitemapProtocol
sitemap_adapter: SitemapProtocol = t.cast(SitemapProtocol, import_adapter("sitemap"))
routes = [Route("/sitemap.xml", depends.get(sitemap_adapter.sitemap))]
