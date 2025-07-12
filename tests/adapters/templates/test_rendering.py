"""Tests for template rendering functionality."""

from pathlib import Path
from typing import Any, Protocol

import pytest
from jinja2 import TemplateNotFound
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response
from fastblocks.adapters.templates._base import TemplatesBase

TemplateContext = dict[str, Any]


class TemplatesWithFilters(Protocol):
    filters: dict[str, Any]


class TestTemplateRendering:
    @pytest.fixture
    def template_context(self) -> TemplateContext:
        return {
            "title": "Test Page",
            "content": "This is a test page content",
            "items": ["item1", "item2", "item3"],
        }

    @pytest.fixture
    def mock_templates(self, templates: TemplatesBase) -> TemplatesBase:
        custom_response = HTMLResponse(
            "<html><body>Custom template response</body></html>",
        )
        templates.app.set_response("custom.html", custom_response)
        return templates

    @pytest.mark.parametrize(
        ("template_name", "expected_content"),
        [
            ("page.html", "<html><body>page.html: title, content, items</body></html>"),
            ("custom.html", "<html><body>Custom template response</body></html>"),
            ("cached.html", "<html><body>Cached content</body></html>"),
        ],
    )
    @pytest.mark.asyncio
    async def test_template_render_pages(
        self,
        mock_templates: TemplatesBase,
        http_request: Request,
        template_name: str,
        expected_content: str,
    ) -> None:
        context: TemplateContext = {
            "title": "Test",
            "content": "Content",
            "items": [1, 2, 3],
        }
        response = await mock_templates.app.render_template(
            http_request,
            template_name,
            context,
        )
        assert response.body.decode() == expected_content

    @pytest.mark.asyncio
    async def test_template_render_with_context(
        self,
        mock_templates: TemplatesBase,
        http_request: Request,
        template_context: TemplateContext,
    ) -> None:
        response = await mock_templates.app.render_template(
            http_request,
            "test.html",
            template_context,
        )
        content = response.body.decode()
        assert "test.html" in content
        assert "title, content, items" in content


class TestTemplateErrors:
    @pytest.fixture
    def mock_templates(self, templates: TemplatesBase) -> TemplatesBase:
        original_render = templates.app.render_template

        async def mock_render(
            request: Request,
            template: str,
            context: TemplateContext | None = None,
            headers: dict[str, str] | None = None,
        ) -> Response:
            if template == "missing.html":
                raise TemplateNotFound(template)
            return await original_render(request, template, context, headers)

        templates.app.render_template = mock_render
        return templates

    @pytest.mark.parametrize(
        "template_name",
        [
            "missing.html",
        ],
    )
    @pytest.mark.asyncio
    async def test_template_not_found(
        self,
        mock_templates: TemplatesBase,
        http_request: Request,
        template_name: str,
    ) -> None:
        with pytest.raises(TemplateNotFound):
            await mock_templates.app.render_template(http_request, template_name)


class TestTemplateCaching:
    @pytest.fixture
    def cached_template(self, tmp_path: Path) -> Path:
        template_path = tmp_path / "cached.html"
        template_path.write_text("<html><body>Cached content</body></html>")
        return template_path

    @pytest.mark.asyncio
    async def test_template_caching(
        self,
        templates: TemplatesBase,
        http_request: Request,
        cached_template: Path,
        cache: Any,
    ) -> None:
        response1 = await templates.app.render_template(http_request, "cached.html")
        assert response1.body.decode() == "<html><body>Cached content</body></html>"

        cached_template.write_text("<html><body>Updated content</body></html>")

        response2 = await templates.app.render_template(http_request, "cached.html")
        assert response2.body.decode() == "<html><body>Cached content</body></html>"


class TestTemplateHelpers:
    @pytest.mark.parametrize(
        ("input_text", "expected_length"),
        [
            ("Short text", 20),
            (
                "This is a very long text that should be truncated at some point",
                15,
            ),
        ],
    )
    def test_truncate_filter(
        self,
        templates: TemplatesWithFilters,
        input_text: str,
        expected_length: int,
    ) -> None:
        result = templates.filters["truncate"](input_text, expected_length)
        if len(input_text) > expected_length:
            assert len(result) == expected_length
            assert result.endswith("...")
        else:
            assert result == input_text

    @pytest.mark.parametrize(
        ("file_size", "expected_output"),
        [
            (512, "0.5 KB"),
            (1024 * 1024, "1.0 MB"),
            (1024 * 1024 * 1024, "1.0 GB"),
            (1024 * 1024 * 1024 * 2, "2.0 GB"),
        ],
    )
    def test_filesize_filter(
        self,
        templates: TemplatesWithFilters,
        file_size: int,
        expected_output: str,
    ) -> None:
        result = templates.filters["filesize"](file_size)
        assert result == expected_output
