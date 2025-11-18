"""FastBlocks Native Sitemap Adapter.

Automatic route-based sitemap generation using FastBlocks routing system
with enhanced caching, filtering, and debugging capabilities.
"""

import re
import typing as t
from contextlib import suppress
from uuid import UUID

from acb.adapters import AdapterStatus
from acb.debug import debug
from acb.depends import depends

from ._base import SitemapBase, SitemapBaseSettings
from .core import BaseSitemap, SitemapApp


class NativeSitemapSettings(SitemapBaseSettings):
    pass


class NativeSitemap(BaseSitemap[str], SitemapBase):
    sitemap: SitemapApp | None = None

    def items(self) -> t.Any:
        try:
            routes_adapter = depends.get_sync("routes")
            if not routes_adapter or not hasattr(routes_adapter, "routes"):
                debug("NativeSitemap: No routes adapter found")
                return []
            route_paths = [r.path for r in routes_adapter.routes]
            debug(f"NativeSitemap: Found {len(route_paths)} routes")
            filtered_paths = self._filter_routes(route_paths)
            debug(f"NativeSitemap: Filtered to {len(filtered_paths)} routes")

            return filtered_paths
        except Exception as e:
            debug(f"NativeSitemap: Error getting routes: {e}")
            return []

    def _filter_routes(self, routes: list[str]) -> list[str]:
        strategy_options = self.config.strategy_options
        include_patterns = strategy_options.get("include_patterns", [])
        exclude_patterns = strategy_options.get("exclude_patterns", [])
        filtered = routes.copy()
        for pattern in exclude_patterns:
            try:
                regex = re.compile(
                    pattern
                )  # REGEX OK: Dynamic user patterns for route filtering
                filtered = [
                    r for r in filtered if not regex.match(r)
                ]  # REGEX OK: Pattern matching for route filtering
            except re.error as e:
                debug(f"NativeSitemap: Invalid exclude pattern '{pattern}': {e}")
        if include_patterns:
            included = []
            for pattern in include_patterns:
                try:
                    regex = re.compile(
                        pattern
                    )  # REGEX OK: Dynamic user patterns for route filtering
                    included.extend(
                        [r for r in filtered if regex.match(r)]
                    )  # REGEX OK: Pattern matching for route filtering
                except re.error as e:
                    debug(f"NativeSitemap: Invalid include pattern '{pattern}': {e}")
            filtered = list(set(included))

        return filtered

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
        debug(f"NativeSitemap: Initialized with domain={self.config.domain}")


Sitemap = NativeSitemap

MODULE_ID = UUID("01937d86-9f7f-7081-d342-6789012345f0")
MODULE_STATUS = AdapterStatus.STABLE

with suppress(Exception):
    depends.set(Sitemap)
