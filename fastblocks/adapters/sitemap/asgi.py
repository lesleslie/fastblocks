from contextlib import suppress

from acb.depends import depends
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
            msg = "`domain` must be set in AppSettings"
            raise ValueError(msg)
        self.sitemap = AsgiSitemapApp(self, domain=self.config.app.domain)


with suppress(Exception):
    depends.set(Sitemap)
