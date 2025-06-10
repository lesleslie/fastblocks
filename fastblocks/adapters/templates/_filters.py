from urllib.parse import quote_plus

from acb.config import Config
from acb.depends import depends
from fastblocks.actions.minify import minify


class Filters:
    templates = depends.get()
    config: Config = depends()

    @staticmethod
    @templates.filter()
    def map_src(address: str) -> str:
        return quote_plus(address)

    @staticmethod
    @templates.filter()
    def url_encode(text: str) -> str:
        return quote_plus(text)

    @staticmethod
    @templates.filter()
    def minify_html(html: str) -> str:
        return minify.html(html)

    @staticmethod
    @templates.filter()
    def minify_js(js: str) -> bytearray | bytes | str:
        return minify.js(js)

    @staticmethod
    @templates.filter()
    def minify_css(css: str) -> bytearray | bytes | str:
        return minify.css(css)
