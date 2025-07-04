from contextlib import suppress

from ...dependencies import get_acb_subset

depends = get_acb_subset("depends")[0]
from asgi_sitemaps import Sitemap as AsgiSitemap  # type: ignore[import-untyped]
from asgi_sitemaps import SitemapApp as AsgiSitemapApp  # type: ignore[import-untyped]

from ._base import SitemapBase, SitemapBaseSettings


class SitemapSettings(SitemapBaseSettings): ...


class Sitemap(AsgiSitemap[str], SitemapBase):  # type: ignore[misc]
    sitemap: AsgiSitemapApp | None = None

    @depends.inject
    def items(self) -> list[str]:
        return [r.path for r in depends.get("routes").routes]

    def location(self, item: str) -> str:
        return item

    def changefreq(self, item: str) -> str:
        return self.config.change_freq

    async def init(self) -> None:
        if not self.config.app.domain:
            raise ValueError("`domain` must be set in AppSettings")
        self.sitemap = AsgiSitemapApp(self, domain=self.config.app.domain)


with suppress(Exception):
    depends.set(Sitemap)
