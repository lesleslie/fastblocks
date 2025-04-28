"""Tests for template rendering with mocks."""

from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, Mock

import pytest
from starlette.requests import Request
from starlette.responses import Response
from fastblocks.adapters.templates._base import TemplateContext, TemplateResponse


class TestTemplateRendering:
    @pytest.fixture
    async def template_context(self) -> AsyncGenerator[TemplateContext, None]:
        yield {
            "title": "Test Page",
            "content": "Hello, World!",
            "items": ["one", "two", "three"],
        }

    @pytest.fixture
    def mock_templates(self) -> Any:
        mock = Mock()
        mock.app = Mock()
        mock.app.render_template = AsyncMock()
        return mock

    @pytest.mark.parametrize(
        "template_name,expected_content",
        [
            ("index.html", "Welcome page"),
            ("about.html", "About page"),
            ("contact.html", "Contact page"),
        ],
    )
    async def test_template_render_pages(
        self,
        mock_templates: Any,
        http_request: Request,
        template_name: str,
        expected_content: str,
    ) -> None:
        mock_templates.app.render_template.return_value = Response(expected_content)
        response: TemplateResponse = await mock_templates.app.render_template(
            http_request, template_name
        )
        assert response.body == expected_content.encode()

    async def test_template_render_with_context(
        self,
        mock_templates: Any,
        http_request: Request,
        template_context: TemplateContext,
    ) -> None:
        mock_templates.app.render_template.return_value = Response(
            "Test Page - Hello, World!"
        )
        response: TemplateResponse = await mock_templates.app.render_template(
            http_request, "test.html", context=template_context
        )
        assert response.body == b"Test Page - Hello, World!"
        mock_templates.app.render_template.assert_called_once_with(
            http_request, "test.html", context=template_context
        )


class TestTemplateErrors:
    @pytest.fixture
    def mock_templates(self) -> Any:
        mock = Mock()
        mock.app = Mock()
        mock.app.render_template = AsyncMock()
        return mock

    @pytest.mark.parametrize(
        "template_name",
        [
            "nonexistent.html",
            "missing/template.html",
            "../invalid.html",
        ],
    )
    async def test_template_not_found(
        self, mock_templates: Any, http_request: Request, template_name: str
    ) -> None:
        mock_templates.app.render_template.side_effect = FileNotFoundError(
            f"Template not found: {template_name}"
        )
        with pytest.raises(FileNotFoundError):
            await mock_templates.app.render_template(http_request, template_name)
