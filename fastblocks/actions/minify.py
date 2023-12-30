import sass
from htmlmin import minify as min_html
from jsmin import jsmin as min_js


class Minify:
    @staticmethod
    def js(js: str) -> str:
        return min_js(js)

    @staticmethod
    def html(html: str) -> str:
        return min_html(html)

    @staticmethod
    def scss(css: str) -> str:
        return sass.compile(string=css, output_style="compressed")  # type: ignore


minify = Minify()
