"""FastBlocks Static Sitemap Adapter.

Pre-configured URL list sitemap generation for simple sites
with known, static URL structures.
"""

from __future__ import annotations

import typing as t
from contextlib import suppress
from uuid import UUID


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


from oneiric.core.resolution import Resolver

# Oneiric resolver for dependency injection
depends = Resolver()


def import_adapter(adapter_name: str) -> None:
    """Custom implementation for Oneiric compatibility."""
    return None


from ._base import SitemapBase, SitemapBaseSettings
from .core import BaseSitemap, SitemapApp


class StaticSitemapSettings(SitemapBaseSettings):
    pass


class StaticSitemap(BaseSitemap[str], SitemapBase):
    sitemap: SitemapApp | None = None

    def items(self) -> list[str]:
        strategy_options = self.config.strategy_options  # type: ignore[attr-defined]
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
            domain=self.config.domain,  # type: ignore[attr-defined]
            cache_ttl=self.config.cache_ttl,
        )


Sitemap = StaticSitemap

MODULE_ID = UUID("01937d86-af80-7192-e453-789012345601")
MODULE_STATUS = AdapterStatus.STABLE

with suppress(Exception):
    depends.set(Sitemap)
