from minify_html import minify as min_html  # type: ignore
from rcssmin import cssmin as min_css
from rjsmin import jsmin as min_js


class Minify:
    @staticmethod
    def js(js: str) -> bytearray | bytes | str:
        return min_js(js)

    @staticmethod
    def html(html: str) -> str:
        return min_html(html, minify_css=True, minify_js=True)

    @staticmethod
    def css(css: str) -> bytearray | bytes | str:
        return min_css(css)


minify = Minify()
