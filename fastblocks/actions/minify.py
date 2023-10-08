import sass
from htmlmin import minify as min_html
from jsmin import jsmin as min_js


class Minify:
    @staticmethod
    def js(js: str):
        return min_js(js)

    @staticmethod
    def html(html: str):
        return min_html(html)

    @staticmethod
    def scss(css: str):
        return sass.compile(string=css, output_style="compressed")


minify = Minify()
