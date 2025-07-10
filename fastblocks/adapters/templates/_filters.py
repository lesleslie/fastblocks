import hashlib
import typing as t
from urllib.parse import quote_plus

from acb.config import Config
from acb.depends import depends
from fastblocks.actions.minify import minify

_minification_cache = {}
_cache_max_size = 1000


def _cached_minify(
    content: str,
    minify_func: t.Callable[[str], str | bytes | bytearray],
    cache_prefix: str,
) -> str | bytes | bytearray:
    content_hash = hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()
    cache_key = f"{cache_prefix}:{content_hash}"

    if cache_key in _minification_cache:
        return _minification_cache[cache_key]

    result = minify_func(content)

    if len(_minification_cache) >= _cache_max_size:
        oldest_key = next(iter(_minification_cache))
        del _minification_cache[oldest_key]

    _minification_cache[cache_key] = result
    return result


class Filters:
    config: Config = depends()

    @classmethod
    def get_templates(cls) -> t.Any:
        if not hasattr(cls, "_templates"):
            cls._templates = depends.get("templates")
        return cls._templates

    @staticmethod
    def map_src(address: str) -> str:
        return quote_plus(address)

    @staticmethod
    def url_encode(text: str) -> str:
        return quote_plus(text)

    @staticmethod
    def minify_html(html: str) -> str | bytes | bytearray:
        return _cached_minify(html, minify.html, "html")

    @staticmethod
    def minify_js(js: str) -> bytearray | bytes | str:
        return _cached_minify(js, minify.js, "js")

    @staticmethod
    def minify_css(css: str) -> bytearray | bytes | str:
        return _cached_minify(css, minify.css, "css")

    @classmethod
    def register_filters(cls) -> None:
        templates = cls.get_templates()
        templates.filter()(cls.map_src)
        templates.filter()(cls.url_encode)
        templates.filter()(cls.minify_html)
        templates.filter()(cls.minify_js)
        templates.filter()(cls.minify_css)
