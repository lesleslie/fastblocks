from acb.depends import depends
from asgi_sitemaps import Sitemap as AsgiSitemap


class Sitemap(AsgiSitemap):  # type: ignore
    def items(self) -> list[str]:
        return ["/"]

    def location(self, item: str) -> str:
        return item

    def changefreq(self, item: str) -> str:
        return "monthly"


# Simplest usage: return a list
# def items(self) -> List[str]:
#     return ["/", "/contact"]


# Async operations are also supported
# async def items(self) -> list[dict]:
#     query = text("SELECT permalink, updated_at FROM pages;")
#     with async_session() as sess:
#         return await sess.fetch_all(query)


# Sync and async generators are also supported
# async def items(self) -> AsyncIterator[dict]:
#     query = "SELECT permalink, updated_at FROM pages;"
#     async for row in database.aiter_rows(query):
#         yield row


depends.set(Sitemap)
