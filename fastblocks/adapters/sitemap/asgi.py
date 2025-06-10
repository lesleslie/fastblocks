from acb.depends import depends
from asgi_sitemaps import Sitemap as AsgiSitemap
from asgi_sitemaps import SitemapApp as AsgiSitemapApp

from ._base import SitemapBase, SitemapBaseSettings


class SitemapSettings(SitemapBaseSettings): ...


class Sitemap(AsgiSitemap[str], SitemapBase):
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


depends.set(Sitemap)
