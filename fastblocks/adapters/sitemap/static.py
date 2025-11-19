"""FastBlocks Static Sitemap Adapter.

Pre-configured URL list sitemap generation for simple sites
with known, static URL structures.
"""

import typing as t
from contextlib import suppress
from uuid import UUID

from acb.adapters import AdapterStatus
from acb.debug import debug
from acb.depends import depends

from ._base import SitemapBase, SitemapBaseSettings
from .core import BaseSitemap, SitemapApp


class StaticSitemapSettings(SitemapBaseSettings):
    pass


class StaticSitemap(BaseSitemap[str], SitemapBase):
    sitemap: SitemapApp | None = None

    def items(self) -> list[str]:
        strategy_options = self.config.strategy_options
        static_urls = t.cast(list[str], strategy_options.get("static_urls", []))
        debug(f"StaticSitemap: Using {len(static_urls)} static URLs")
        return static_urls

    def location(self, item: str) -> str:
        return item

    def changefreq(self, item: str) -> str:
        return t.cast(str, self.config.change_freq)

    def priority(self, item: str) -> float:
        if item == "/":
            return 1.0
        segments = len([s for s in item.split("/") if s])
        if segments == 1:
            return 0.8
        if segments == 2:
            return 0.6
        return 0.4

    async def init(self) -> None:
        if not self.config.domain:
            msg = "domain must be set in sitemap settings"
            raise ValueError(msg)
        self.sitemap = SitemapApp(
            self,
            domain=self.config.domain,
            cache_ttl=self.config.cache_ttl,
        )
        debug(f"StaticSitemap: Initialized with domain={self.config.domain}")


Sitemap = StaticSitemap

MODULE_ID = UUID("01937d86-af80-7192-e453-789012345601")
MODULE_STATUS = AdapterStatus.STABLE

with suppress(Exception):
    depends.set(Sitemap)
