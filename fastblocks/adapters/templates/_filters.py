from urllib.parse import quote_plus

from acb.config import Config
from acb.depends import depends
from fastblocks.actions import minify


class Filters:
    templates = depends.get("templates")  # type: ignore
    config: Config = depends()  # type: ignore

    @staticmethod
    @templates.filter()
    def map_src(address: str) -> str:
        return quote_plus(address)

    @staticmethod
    @templates.filter()
    def minify_html(html: str) -> str:
        return minify.html(html)  # type: ignore

    @staticmethod
    @templates.filter()
    def minify_js(js: str) -> str:
        return minify.js(js)  # type: ignore

    @staticmethod
    @templates.filter()
    def minify_scss(css: str) -> str:
        return minify.scss(css)  # type: ignore
