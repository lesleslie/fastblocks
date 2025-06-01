import sys
from unittest.mock import MagicMock, patch

import pytest
from pytest_mock import MockerFixture


@pytest.mark.unit
class TestTemplateFilters:
    @pytest.fixture(autouse=True)
    def setup_module_patches(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        self.mock_templates = mocker.MagicMock()
        self.mock_templates.filter.return_value = lambda func: func

        self.mock_depends = mocker.MagicMock()
        self.mock_get = mocker.MagicMock(
            side_effect=lambda name=None: self.mock_templates
        )
        self.mock_depends.get = self.mock_get

        self.mock_config = mocker.MagicMock()

        sys.modules["acb"] = mocker.MagicMock()
        sys.modules["acb.depends"] = mocker.MagicMock()
        sys.modules["acb.depends"].depends = self.mock_depends
        sys.modules["acb.config"] = mocker.MagicMock()
        sys.modules["acb.config"].Config = self.mock_config

    def test_map_src(self) -> None:
        from fastblocks.adapters.templates._filters import Filters

        with patch(
            "urllib.parse.quote_plus",
            side_effect=lambda s: s.replace(" ", "+")
            .replace("@", "%40")
            .replace("/", "%2F"),
        ):
            assert Filters.map_src("hello world") == "hello+world"

            assert Filters.map_src("test@example.com") == "test%40example.com"

            assert Filters.map_src("path/to/resource") == "path%2Fto%2Fresource"

            assert Filters.map_src("") == ""

    def test_minify_html(self) -> None:
        mock_minify = MagicMock()
        mock_minify.html = MagicMock(return_value="<html><body>minified</body></html>")

        with patch("fastblocks.adapters.templates._filters.minify", mock_minify):
            from fastblocks.adapters.templates._filters import Filters

            html_content = "<html>\n  <body>\n    content\n  </body>\n</html>"

            result = Filters.minify_html(html_content)

            mock_minify.html.assert_called_once_with(html_content)

            assert result == "<html><body>minified</body></html>"

    def test_minify_js(self) -> None:
        mock_minify = MagicMock()
        mock_minify.js = MagicMock(return_value="function test(){return true;}")

        with patch("fastblocks.adapters.templates._filters.minify", mock_minify):
            from fastblocks.adapters.templates._filters import Filters

            js_content = "function test() {\n  return true;\n}"

            result = Filters.minify_js(js_content)

            mock_minify.js.assert_called_once_with(js_content)

            assert result == "function test(){return true;}"

    def test_minify_css(self) -> None:
        mock_minify = MagicMock()
        mock_minify.css = MagicMock(return_value="body{color:red}")

        with patch("fastblocks.adapters.templates._filters.minify", mock_minify):
            from fastblocks.adapters.templates._filters import Filters

            css_content = "body {\n  color: red;\n}"

            result = Filters.minify_css(css_content)

            mock_minify.css.assert_called_once_with(css_content)

            assert result == "body{color:red}"
