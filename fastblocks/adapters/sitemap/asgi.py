"""FastBlocks ASGI Sitemap Adapter (Legacy).

This adapter now uses FastBlocks native sitemap implementation
instead of the external asgi-sitemaps dependency.

For new projects, consider using the native adapter directly.
"""

import typing as t
from contextlib import suppress
from uuid import UUID

from acb.adapters import AdapterStatus
from acb.depends import depends

from ._base import SitemapBase, SitemapBaseSettings
from .core import BaseSitemap as NativeSitemap
from .core import SitemapApp


class SitemapSettings(SitemapBaseSettings):
    pass


class AsgiSitemap(NativeSitemap[str], SitemapBase):
    sitemap: SitemapApp | None = None

    def items(self) -> t.Any:
        try:
            routes_adapter = depends.get_sync("routes")
            if routes_adapter and hasattr(routes_adapter, "routes"):
                return [r.path for r in routes_adapter.routes]
            return []
        except Exception:
            return []

    def location(self, item: str) -> str:
        return item

    def changefreq(self, item: str) -> str:
        return t.cast(str, self.config.change_freq)

    async def init(self) -> None:
        if not self.config.app.domain:
            msg = "`domain` must be set in AppSettings"
            raise ValueError(msg)
        self.sitemap = SitemapApp(
            self,
            domain=self.config.app.domain,
            cache_ttl=getattr(self.config, "cache_ttl", 3600),
        )


MODULE_ID = UUID("01937d86-eff0-7410-5786-a01234567890")
MODULE_STATUS = AdapterStatus.STABLE

with suppress(Exception):
    depends.set(AsgiSitemap)
