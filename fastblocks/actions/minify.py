from subprocess import run

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
        return str(
            run(  # noqa
                ["sass", "--no-source-map", "--style=compressed", "--stdin", css],
                capture_output=True,
            ).stdout
        )


minify = Minify()
