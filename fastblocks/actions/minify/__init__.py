import typing as t

from minify_html import minify as min_html
from rcssmin import cssmin as min_css
from rjsmin import jsmin as min_js

__all__: list[str] = ["minify"]


class Minify:
    @staticmethod
    def js(js: str) -> bytearray | bytes | str:
        if not js or js.isspace():
            return ""
        js = js.replace("}", "}\n")
        return t.cast(bytearray | bytes | str, min_js(js))

    @staticmethod
    def html(html: str) -> str:
        if not html or html.isspace():
            return ""
        return min_html(html, minify_css=True, minify_js=True)

    @staticmethod
    def css(css: str) -> bytearray | bytes | str:
        if not css or css.isspace():
            return ""
        css = css.replace("@media (", "@media(")
        return t.cast(bytearray | bytes | str, min_css(css))


minify = Minify()
