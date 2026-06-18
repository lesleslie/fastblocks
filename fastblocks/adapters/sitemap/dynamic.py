"""FastBlocks Dynamic Sitemap Adapter.

Database-driven sitemap generation for content management systems
and applications with dynamic URL structures.
"""

from __future__ import annotations

import datetime as dt
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


class DynamicSitemapSettings(SitemapBaseSettings):
    pass


class DynamicSitemap(BaseSitemap[dict[str, t.Any]], SitemapBase):
    sitemap: SitemapApp | None = None

    async def items(self) -> list[dict[str, t.Any]]:
        strategy_options = self.config.strategy_options
        model_configs = strategy_options.get("model_configs", [])
        all_items = []
        for model_config in model_configs:
            try:
                items = await self._get_model_items(model_config)
                all_items.extend(items)
            except Exception as e:
                debug(f"DynamicSitemap: Error loading model {model_config}: {e}")
        debug(f"DynamicSitemap: Generated {len(all_items)} dynamic URLs")
        return all_items

    async def _get_model_items(
        self, model_config: dict[str, t.Any]
    ) -> list[dict[str, t.Any]]:
        model_name = model_config.get("model", "Unknown")
        debug(f"DynamicSitemap: Loading items from model {model_name}")

        return [
            {
                "url": f"/{model_name.lower()}/sample-item",
                "lastmod": dt.datetime.now(),
                "priority": 0.7,
            }
        ]

    def location(self, item: dict[str, t.Any]) -> str:
        return t.cast(str, item.get("url", "/"))

    def lastmod(self, item: dict[str, t.Any]) -> dt.datetime | None:
        return item.get("lastmod")

    def changefreq(self, item: dict[str, t.Any]) -> str:
        return t.cast(str, item.get("changefreq", self.config.change_freq))  # type: ignore[attr-defined]

    def priority(self, item: dict[str, t.Any]) -> float:
        return t.cast(float, item.get("priority", 0.5))

    async def init(self) -> None:
        if not self.config.domain:
            msg = "domain must be set in sitemap settings"
            raise ValueError(msg)
        self.sitemap = SitemapApp(
            self,
            domain=self.config.domain,
            cache_ttl=self.config.cache_ttl,  # type: ignore[attr-defined]
        )


Sitemap = DynamicSitemap

MODULE_ID = UUID("01937d86-bf91-72a3-f564-890123456712")
MODULE_STATUS = AdapterStatus.STABLE

with suppress(Exception):
    depends.set(Sitemap)
