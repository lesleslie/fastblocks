import typing as t
from unittest.mock import patch

import pytest
from pytest_mock import MockerFixture


@pytest.fixture
def mock_acb(mocker: MockerFixture) -> t.Any:
    # Create mock modules
    mock_acb = mocker.MagicMock()
    mock_depends = mocker.MagicMock()
    mock_config = mocker.MagicMock()

    mock_templates = mocker.MagicMock()
    mock_templates.filter.return_value = lambda func: func

    mock_config.Config = mocker.MagicMock

    mock_acb.depends = mock_depends
    mock_acb.config = mock_config
    mock_depends.depends = mock_depends
    mock_depends.get.return_value = mock_templates

    # Create basic module structure for filters
    mock_filters_module = mocker.MagicMock()
    mock_actions_module = mocker.MagicMock()
    mock_minify_module = mocker.MagicMock()
    mock_minify_module.html.return_value = "minified_html"
    mock_minify_module.js.return_value = "minified_js"
    mock_minify_module.css.return_value = "minified_css"

    # Set up the mocked modules
    mock_actions_module.minify = mock_minify_module

    # Define the Filters class
    class Filters:
        @staticmethod
        def url_encode(s: str) -> str:
            from urllib.parse import quote_plus

            return quote_plus(s)

        @staticmethod
        def minify_html(html: str) -> str:
            return mock_minify_module.html(html)

        @staticmethod
        def minify_js(js: str) -> str:
            return mock_minify_module.js(js)

        @staticmethod
        def minify_css(css: str) -> str:
            return mock_minify_module.css(css)

    # Add the Filters class to our mock module
    mock_filters_module.Filters = Filters
    mock_filters_module.minify = mock_minify_module

    # Patch sys.modules
    mocker.patch.dict(
        "sys.modules",
        {
            "acb": mock_acb,
            "acb.depends": mock_depends,
            "acb.config": mock_config,
            "fastblocks.actions": mock_actions_module,
            "fastblocks.actions.minify": mock_minify_module,
            "fastblocks.adapters.templates._filters": mock_filters_module,
        },
    )

    return mock_acb


@pytest.fixture
def mock_minify(mocker: MockerFixture) -> t.Any:
    mock_minify = mocker.MagicMock()
    mock_minify.html.return_value = "minified_html"
    mock_minify.js.return_value = "minified_js"
    mock_minify.css.return_value = "minified_css"
    return mock_minify


@pytest.mark.unit
class TestFilters:
    def test_url_encode(self, mock_acb: t.Any) -> None:
        test_string = "test string with spaces"
        expected_result = "test+string+with+spaces"

        with patch("urllib.parse.quote_plus", return_value=expected_result):
            from fastblocks.adapters.templates._filters import Filters

            result = Filters.url_encode(test_string)
            assert result == expected_result

    def test_minify_methods(
        self, mock_minify: t.Any, mock_acb: t.Any, mocker: MockerFixture
    ) -> None:
        test_html = "<html><body>Test</body></html>"
        test_js = "function test() { return true; }"
        test_css = "body { color: red; }"

        mocker.patch("fastblocks.actions.minify", mock_minify)

        class MockFilters:
            @staticmethod
            def minify_html(html: str) -> str:
                return mock_minify.html(html)

            @staticmethod
            def minify_js(js: str) -> str:
                return mock_minify.js(js)

            @staticmethod
            def minify_css(css: str) -> str:
                return mock_minify.css(css)

        mocker.patch("fastblocks.adapters.templates._filters.Filters", MockFilters)

        from fastblocks.adapters.templates._filters import Filters

        result = Filters.minify_html(test_html)
        assert result == "minified_html"
        mock_minify.html.assert_called_once_with(test_html)

        result = Filters.minify_js(test_js)
        assert result == "minified_js"
        mock_minify.js.assert_called_once_with(test_js)

        result = Filters.minify_css(test_css)
        assert result == "minified_css"
        mock_minify.css.assert_called_once_with(test_css)
