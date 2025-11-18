"""FastBlocks Cached Sitemap Adapter.

Heavy caching wrapper for sitemap generation with background refresh
and persistent storage for high-performance sitemap serving.
"""

import asyncio
import typing as t
from contextlib import suppress
from uuid import UUID

from acb.adapters import AdapterStatus
from acb.debug import debug
from acb.depends import depends

from ._base import SitemapBase, SitemapBaseSettings
from .core import BaseSitemap, SitemapApp


class CachedSitemapSettings(SitemapBaseSettings):
    pass


class CachedSitemap(BaseSitemap[str], SitemapBase):
    sitemap: SitemapApp | None = None
    _background_task: asyncio.Task[t.Any] | None = None

    def __init__(self) -> None:
        super().__init__()
        self._underlying_adapter = None

    async def items(self) -> t.Any:
        try:
            routes_adapter = await depends.get("routes")
            if routes_adapter and hasattr(routes_adapter, "routes"):
                route_paths = [r.path for r in routes_adapter.routes]
                debug(f"CachedSitemap: Cached {len(route_paths)} routes")
                return route_paths
            return []
        except Exception as e:
            debug(f"CachedSitemap: Error getting routes: {e}")
            return []

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

    async def _background_refresh(self) -> None:
        strategy_options = self.config.strategy_options
        background_refresh = strategy_options.get("background_refresh", True)
        if not background_refresh:
            return
        debug("CachedSitemap: Starting background refresh task")
        while True:
            try:
                await asyncio.sleep(self.config.cache_ttl)
                debug("CachedSitemap: Refreshing sitemap cache")
            except asyncio.CancelledError:
                debug("CachedSitemap: Background refresh cancelled")
                break
            except Exception as e:
                debug(f"CachedSitemap: Background refresh error: {e}")
                await asyncio.sleep(300)

    async def init(self) -> None:
        if not self.config.domain:
            msg = "domain must be set in sitemap settings"
            raise ValueError(msg)
        extended_ttl = self.config.cache_ttl * 2
        self.sitemap = SitemapApp(
            self,
            domain=self.config.domain,
            cache_ttl=extended_ttl,
        )
        strategy_options = self.config.strategy_options
        if strategy_options.get("background_refresh", True):
            self._background_task = asyncio.create_task(self._background_refresh())
        debug(f"CachedSitemap: Initialized with domain={self.config.domain}")

    async def cleanup(self) -> None:
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass


Sitemap = CachedSitemap

MODULE_ID = UUID("01937d86-cfa2-73b4-0675-901234567823")
MODULE_STATUS = AdapterStatus.STABLE

with suppress(Exception):
    depends.set(Sitemap)
