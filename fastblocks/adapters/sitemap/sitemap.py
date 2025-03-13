from acb.adapters import import_adapter
from acb.depends import depends
from asgi_sitemaps import Sitemap as AsgiSitemap
from asgi_sitemaps import SitemapApp as AsgiSitemapApp

from ._base import SitemapBase, SitemapBaseSettings

Routes = import_adapter()


class SitemapSettings(SitemapBaseSettings): ...


class Sitemap(AsgiSitemap, SitemapBase):  # type: ignore
    sitemap: AsgiSitemapApp | None = None

    @depends.inject
    def items(self, routes: Routes = depends()) -> list[str]:
        return [r.path for r in routes.routes]

    def location(self, item: str) -> str:
        return item

    def changefreq(self, item: str) -> str:
        return self.config.change_freq

    async def init(self) -> None:
        self.sitemap = AsgiSitemapApp(self, domain=self.config.domain)


depends.set(Sitemap)
