"""Comprehensive tests for FastBlocks template filters."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastblocks.adapters.templates._async_filters import (
    FASTBLOCKS_ASYNC_FILTERS,
    async_font_import,
    async_image_url,
    async_image_with_transformations,
    async_optimized_font_stack,
    async_responsive_image,
)
from fastblocks.adapters.templates._filters import (
    FASTBLOCKS_FILTERS,
    font_family,
    font_import,
    htmx_attrs,
    htmx_component,
    htmx_form,
    htmx_lazy_load,
    icon_tag,
    icon_with_text,
    image_url,
    img_tag,
    style_class,
)
from fastblocks.adapters.templates._registration import (
    get_global_template_context,
    register_async_fastblocks_filters,
    register_fastblocks_filters,
    setup_fastblocks_template_environment,
)


@pytest.mark.unit
class TestSyncFilters:
    """Test synchronous template filters."""

    @patch("fastblocks.adapters.templates._filters.depends")
    def test_img_tag_with_adapter(self, mock_depends):
        """Test img_tag with image adapter."""
        mock_adapter = MagicMock()
        mock_adapter.get_img_tag.return_value = (
            '<img src="test.jpg" alt="Test" width="300">'
        )
        mock_depends.get_sync.return_value = mock_adapter

        result = img_tag("test.jpg", "Test", width=300)

        assert '<img src="test.jpg" alt="Test" width="300">' in result
        mock_adapter.get_img_tag.assert_called_once_with("test.jpg", "Test", width=300)

    @patch("fastblocks.adapters.templates._filters.depends")
    def test_img_tag_fallback(self, mock_depends):
        """Test img_tag fallback behavior."""
        mock_depends.get_sync.return_value = None

        result = img_tag("test.jpg", "Test", width=300, **{"class": "responsive"})

        assert "<img" in result
        assert 'src="test.jpg"' in result
        assert 'alt="Test"' in result
        assert 'width="300"' in result
        assert 'class="responsive"' in result

    @patch("fastblocks.adapters.templates._filters.depends")
    def test_image_url_with_adapter(self, mock_depends):
        """Test image_url with image adapter."""
        mock_adapter = MagicMock()
        mock_adapter.get_sync_image_url.return_value = (
            "https://example.com/test.jpg?w=300"
        )
        mock_depends.get_sync.return_value = mock_adapter

        result = image_url("test.jpg", width=300)

        assert result == "https://example.com/test.jpg?w=300"
        mock_adapter.get_sync_image_url.assert_called_once_with("test.jpg", width=300)

    @patch("fastblocks.adapters.templates._filters.depends")
    def test_image_url_fallback_with_params(self, mock_depends):
        """Test image_url fallback with parameters."""
        mock_adapter = MagicMock(spec=[])  # Adapter without get_sync_image_url method
        mock_depends.get_sync.return_value = mock_adapter

        result = image_url("test.jpg", width=300, height=200)

        assert "test.jpg" in result
        assert "width=300" in result
        assert "height=200" in result

    @patch("fastblocks.adapters.templates._filters.depends")
    def test_style_class_with_adapter(self, mock_depends):
        """Test style_class with style adapter."""
        mock_adapter = MagicMock()
        mock_adapter.get_component_class.return_value = "btn"
        mock_adapter.get_utility_classes.return_value = {
            "variant_primary": "btn-primary",
            "size_large": "btn-large",
        }
        mock_depends.get_sync.return_value = mock_adapter

        result = style_class("button", variant="primary", size="large")

        assert "btn" in result
        assert "btn-primary" in result
        assert "btn-large" in result

    @patch("fastblocks.adapters.templates._filters.depends")
    def test_style_class_fallback(self, mock_depends):
        """Test style_class fallback behavior."""
        mock_depends.get_sync.return_value = None

        result = style_class("form_input")

        assert result == "form-input"  # Underscore replaced with dash

    @patch("fastblocks.adapters.templates._filters.depends")
    def test_icon_tag_with_adapter(self, mock_depends):
        """Test icon_tag with icon adapter."""
        mock_adapter = MagicMock()
        mock_adapter.get_icon_tag.return_value = '<i class="fas fa-home"></i>'
        mock_depends.get_sync.return_value = mock_adapter

        result = icon_tag("home")

        assert '<i class="fas fa-home"></i>' in result
        mock_adapter.get_icon_tag.assert_called_once_with("home")

    @patch("fastblocks.adapters.templates._filters.depends")
    def test_icon_tag_fallback(self, mock_depends):
        """Test icon_tag fallback behavior."""
        mock_depends.get_sync.return_value = None

        result = icon_tag("home")

        assert result == "[home]"

    @patch("fastblocks.adapters.templates._filters.depends")
    def test_icon_with_text_with_adapter(self, mock_depends):
        """Test icon_with_text with icon adapter."""
        mock_adapter = MagicMock()
        mock_adapter.get_icon_with_text.return_value = (
            '<span><i class="fas fa-save"></i> Save</span>'
        )
        mock_depends.get_sync.return_value = mock_adapter

        result = icon_with_text("save", "Save", position="left")

        assert '<span><i class="fas fa-save"></i> Save</span>' in result
        mock_adapter.get_icon_with_text.assert_called_once_with("save", "Save", "left")

    @patch("fastblocks.adapters.templates._filters.depends")
    def test_font_import_with_adapter(self, mock_depends):
        """Test font_import with font adapter."""
        mock_adapter = MagicMock()
        mock_adapter.get_sync_font_import.return_value = (
            '<link rel="stylesheet" href="fonts.css">'
        )
        mock_depends.get_sync.return_value = mock_adapter

        result = font_import()

        assert '<link rel="stylesheet" href="fonts.css">' in result
        mock_adapter.get_sync_font_import.assert_called_once()

    @patch("fastblocks.adapters.templates._filters.depends")
    def test_font_family_with_adapter(self, mock_depends):
        """Test font_family with font adapter."""
        mock_adapter = MagicMock()
        mock_adapter.get_font_family.return_value = "'Inter', sans-serif"
        mock_depends.get_sync.return_value = mock_adapter

        result = font_family("primary")

        assert result == "'Inter', sans-serif"
        mock_adapter.get_font_family.assert_called_once_with("primary")

    @patch("fastblocks.adapters.templates._filters.depends")
    def test_font_family_fallback(self, mock_depends):
        """Test font_family fallback behavior."""
        mock_depends.get_sync.return_value = None

        result = font_family("primary")

        assert "-apple-system" in result
        assert "BlinkMacSystemFont" in result
        assert "sans-serif" in result

    def test_htmx_attrs_basic(self):
        """Test basic HTMX attributes generation."""
        result = htmx_attrs(get="/api/data", target="#content", swap="innerHTML")

        assert 'hx-get="/api/data"' in result
        assert 'hx-target="#content"' in result
        assert 'hx-swap="innerHTML"' in result

    def test_htmx_attrs_complex(self):
        """Test complex HTMX attributes."""
        result = htmx_attrs(
            post="/api/submit",
            trigger="click",
            confirm="Are you sure?",
            push_url="true",
            headers='{"X-Custom": "value"}',
        )

        assert 'hx-post="/api/submit"' in result
        assert 'hx-trigger="click"' in result
        assert 'hx-confirm="Are you sure?"' in result
        assert 'hx-push-url="true"' in result
        assert 'hx-headers="{' in result and '"X-Custom": "value"' in result

    def test_htmx_component(self):
        """Test HTMX component generation."""
        with patch("fastblocks.adapters.templates._filters.style_class") as mock_style:
            mock_style.return_value = "card htmx-card"

            result = htmx_component("card", get="/api/card", target="this")

            assert 'class="card htmx-card"' in result
            assert 'hx-get="/api/card"' in result
            assert 'hx-target="this"' in result

    def test_htmx_form(self):
        """Test HTMX form generation."""
        result = htmx_form("/submit", target="#form-container")

        assert 'hx-post="/submit"' in result
        assert 'hx-target="#form-container"' in result
        assert 'hx-swap="outerHTML"' in result
        assert 'hx-indicator="#form-loading"' in result

    def test_htmx_lazy_load(self):
        """Test HTMX lazy load generation."""
        result = htmx_lazy_load("/api/content", "Loading...", trigger="revealed once")

        assert 'hx-get="/api/content"' in result
        assert 'hx-trigger="revealed once"' in result
        assert 'data-placeholder="Loading..."' in result

    def test_filters_registry_completeness(self):
        """Test that all filters are registered in FASTBLOCKS_FILTERS."""
        expected_filters = [
            "img_tag",
            "image_url",
            "style_class",
            "icon_tag",
            "icon_with_text",
            "font_import",
            "font_family",
            "stylesheet_links",
            "component_html",
            "htmx_attrs",
            "htmx_component",
            "htmx_form",
            "htmx_lazy_load",
        ]

        for filter_name in expected_filters:
            assert filter_name in FASTBLOCKS_FILTERS
            assert callable(FASTBLOCKS_FILTERS[filter_name])


@pytest.mark.unit
class TestAsyncFilters:
    """Test asynchronous template filters."""

    @pytest.mark.asyncio
    @patch("fastblocks.adapters.templates.async_filters.depends")
    async def test_async_image_url_with_adapter(self, mock_depends):
        """Test async_image_url with image adapter."""
        mock_adapter = MagicMock()
        mock_adapter.get_image_url = AsyncMock(
            return_value="https://example.com/test.jpg?w=300"
        )
        mock_depends.get_sync.return_value = mock_adapter

        result = await async_image_url("test.jpg", width=300)

        assert result == "https://example.com/test.jpg?w=300"
        mock_adapter.get_image_url.assert_called_once_with("test.jpg", width=300)

    @pytest.mark.asyncio
    @patch("fastblocks.adapters.templates.async_filters.depends")
    async def test_async_image_url_fallback(self, mock_depends):
        """Test async_image_url fallback behavior."""
        mock_depends.get_sync.return_value = None

        result = await async_image_url("test.jpg", width=300)

        assert result == "test.jpg"

    @pytest.mark.asyncio
    @patch("fastblocks.adapters.templates.async_filters.depends")
    async def test_async_font_import_with_adapter(self, mock_depends):
        """Test async_font_import with font adapter."""
        mock_adapter = MagicMock()
        mock_adapter.get_font_import = AsyncMock(
            return_value='<link rel="stylesheet" href="fonts.css">'
        )
        mock_depends.get_sync.return_value = mock_adapter

        result = await async_font_import()

        assert result == '<link rel="stylesheet" href="fonts.css">'
        mock_adapter.get_font_import.assert_called_once()

    @pytest.mark.asyncio
    @patch("fastblocks.adapters.templates.async_filters.depends")
    async def test_async_font_import_fallback(self, mock_depends):
        """Test async_font_import fallback behavior."""
        mock_depends.get_sync.return_value = None

        result = await async_font_import()

        assert result == ""

    @pytest.mark.asyncio
    @patch("fastblocks.adapters.templates.async_filters.depends")
    async def test_async_image_with_transformations(self, mock_depends):
        """Test async_image_with_transformations."""
        mock_adapter = MagicMock()
        mock_adapter.get_image_url = AsyncMock(
            return_value="https://example.com/hero.jpg?w=1200&q=85"
        )
        mock_depends.get_sync.return_value = mock_adapter

        result = await async_image_with_transformations(
            "hero.jpg", "Hero Image", {"width": 1200, "quality": 85}, class_="hero-img"
        )

        assert "<img" in result
        assert 'src="https://example.com/hero.jpg?w=1200&q=85"' in result
        assert 'alt="Hero Image"' in result
        assert 'class="hero-img"' in result

    @pytest.mark.asyncio
    @patch("fastblocks.adapters.templates.async_filters.depends")
    async def test_async_responsive_image(self, mock_depends):
        """Test async_responsive_image generation."""
        mock_adapter = MagicMock()

        # Mock different URLs for different sizes
        def mock_get_image_url(image_id, **kwargs):
            width = kwargs.get("width", 400)
            return f"https://example.com/{image_id}?w={width}"

        mock_adapter.get_image_url = AsyncMock(side_effect=mock_get_image_url)
        mock_depends.get_sync.return_value = mock_adapter

        sizes = {
            "mobile": {"width": 400, "quality": 75},
            "tablet": {"width": 800, "quality": 80},
            "desktop": {"width": 1200, "quality": 85},
        }

        result = await async_responsive_image("article.jpg", "Article Image", sizes)

        assert "<img" in result
        assert "srcset=" in result
        assert "w=400" in result
        assert "w=800" in result
        assert "w=1200" in result
        assert "sizes=" in result

    @pytest.mark.asyncio
    @patch("fastblocks.adapters.templates.async_filters.depends")
    async def test_async_optimized_font_stack(self, mock_depends):
        """Test async_optimized_font_stack generation."""
        mock_adapter = MagicMock()
        mock_adapter.get_font_import = AsyncMock(
            return_value='<link rel="stylesheet" href="fonts.css">'
        )
        mock_adapter.get_preload_links.return_value = (
            '<link rel="preload" href="font.woff2">'
        )
        mock_adapter.get_css_variables.return_value = ":root { --font-primary: Inter; }"
        mock_depends.get_sync.return_value = mock_adapter

        result = await async_optimized_font_stack()

        assert '<link rel="stylesheet" href="fonts.css">' in result
        assert '<link rel="preload" href="font.woff2">' in result
        assert ":root { --font-primary: Inter; }" in result

    def test_async_filters_registry_completeness(self):
        """Test that all async filters are registered in FASTBLOCKS_ASYNC_FILTERS."""
        expected_async_filters = [
            "async_image_url",
            "async_font_import",
            "async_image_with_transformations",
            "async_responsive_image",
            "async_optimized_font_stack",
        ]

        for filter_name in expected_async_filters:
            assert filter_name in FASTBLOCKS_ASYNC_FILTERS
            assert callable(FASTBLOCKS_ASYNC_FILTERS[filter_name])


@pytest.mark.unit
class TestFilterRegistration:
    """Test filter registration system."""

    def test_register_fastblocks_filters(self):
        """Test sync filter registration."""
        mock_env = MagicMock()
        mock_env.filters = {}

        register_fastblocks_filters(mock_env)

        # Check that filters were registered
        assert len(mock_env.filters) > 0
        assert "img_tag" in mock_env.filters
        assert "style_class" in mock_env.filters
        assert "htmx_attrs" in mock_env.filters

    def test_register_async_fastblocks_filters(self):
        """Test async filter registration."""
        mock_env = MagicMock()
        mock_env.filters = {}

        register_async_fastblocks_filters(mock_env)

        # Check that both sync and async filters were registered
        assert len(mock_env.filters) > 0
        assert "img_tag" in mock_env.filters  # Sync filter
        assert "async_image_url" in mock_env.filters  # Async filter

    @patch("fastblocks.adapters.templates.registration.depends")
    def test_get_global_template_context(self, mock_depends):
        """Test global template context generation."""
        mock_images = MagicMock()
        mock_styles = MagicMock()
        mock_icons = MagicMock()
        mock_fonts = MagicMock()

        def mock_get(name):
            return {
                "images": mock_images,
                "styles": mock_styles,
                "icons": mock_icons,
                "fonts": mock_fonts,
            }.get(name)

        mock_depends.get.side_effect = mock_get

        context = get_global_template_context()

        assert "images_adapter" in context
        assert "styles_adapter" in context
        assert "icons_adapter" in context
        assert "fonts_adapter" in context
        assert context["images_adapter"] is mock_images
        assert context["styles_adapter"] is mock_styles

    def test_setup_fastblocks_template_environment_sync(self):
        """Test complete sync template environment setup."""
        mock_env = MagicMock()
        mock_env.filters = {}
        mock_env.globals = {}

        setup_fastblocks_template_environment(mock_env, async_mode=False)

        # Check filters were registered
        assert len(mock_env.filters) > 0
        assert "img_tag" in mock_env.filters

        # Check globals were updated
        mock_env.globals.update.assert_called_once()

        # Check delimiters were set
        assert mock_env.variable_start_string == "[["
        assert mock_env.variable_end_string == "]]"
        assert mock_env.block_start_string == "[%"
        assert mock_env.block_end_string == "%]"

        # Check other settings
        assert mock_env.trim_blocks is True
        assert mock_env.lstrip_blocks is True

    def test_setup_fastblocks_template_environment_async(self):
        """Test complete async template environment setup."""
        mock_env = MagicMock()
        mock_env.filters = {}
        mock_env.globals = {}

        setup_fastblocks_template_environment(mock_env, async_mode=True)

        # Check that async filters were registered (includes sync ones too)
        assert len(mock_env.filters) > 0
        # Should have both sync and async filters
        assert "img_tag" in mock_env.filters  # Sync
        assert "async_image_url" in mock_env.filters  # Async

    def test_setup_fastblocks_template_environment_delimiter_preservation(self):
        """Test that delimiters are only set once."""
        mock_env = MagicMock()
        mock_env.filters = {}
        mock_env.globals = {}
        mock_env._fastblocks_delimiters_set = True

        setup_fastblocks_template_environment(mock_env)

        # Delimiters should not be changed if already set
        assert (
            not hasattr(mock_env, "variable_start_string")
            or mock_env.variable_start_string != "[["
        )


@pytest.mark.unit
class TestFilterIntegration:
    """Test filter integration patterns."""

    def test_filter_chaining_compatibility(self):
        """Test that filters can be chained in templates."""
        # This tests the return types are compatible for chaining
        with patch("fastblocks.adapters.templates.filters.depends") as mock_depends:
            mock_depends.get_sync.return_value = None

            # Test that string outputs can be chained
            img_result = img_tag("test.jpg", "Test")
            assert isinstance(img_result, str)

            style_result = style_class("button")
            assert isinstance(style_result, str)

            icon_result = icon_tag("home")
            assert isinstance(icon_result, str)

    def test_filter_error_handling(self):
        """Test filter error handling."""
        with patch("fastblocks.adapters.templates.filters.depends") as mock_depends:
            # Test when depends.get returns None
            mock_depends.get_sync.return_value = None

            # All filters should handle None gracefully
            assert isinstance(img_tag("test.jpg", "Test"), str)
            assert isinstance(image_url("test.jpg"), str)
            assert isinstance(style_class("button"), str)
            assert isinstance(icon_tag("home"), str)
            assert isinstance(font_family("primary"), str)

    def test_filter_attribute_handling(self):
        """Test attribute handling across filters."""
        # Test that all filters handle various attribute types
        with patch("fastblocks.adapters.templates.filters.depends") as mock_depends:
            mock_depends.get_sync.return_value = None

            # Test with different attribute types
            img_result = img_tag(
                "test.jpg", "Test", width=300, height="200", class_="img"
            )
            assert 'width="300"' in img_result
            assert 'height="200"' in img_result
            assert 'class="img"' in img_result

    @pytest.mark.asyncio
    async def test_async_filter_error_handling(self):
        """Test async filter error handling."""
        with patch(
            "fastblocks.adapters.templates.async_filters.depends"
        ) as mock_depends:
            mock_depends.get_sync.return_value = None

            # All async filters should handle None gracefully
            result1 = await async_image_url("test.jpg")
            assert isinstance(result1, str)

            result2 = await async_font_import()
            assert isinstance(result2, str)

    def test_htmx_filter_integration(self):
        """Test HTMX filter integration patterns."""
        # Test that HTMX filters produce valid HTML attributes
        result1 = htmx_attrs(get="/api", target="#content")
        assert result1.startswith("hx-")
        assert "=" in result1
        assert '"' in result1

        result2 = htmx_form("/submit")
        assert 'hx-post="/submit"' in result2

        result3 = htmx_lazy_load("/content")
        assert 'hx-get="/content"' in result3

    def test_filter_performance_considerations(self):
        """Test performance-related aspects of filters."""
        # Test that filters don't have expensive operations in their core logic
        with patch("fastblocks.adapters.templates.filters.depends") as mock_depends:
            mock_depends.get_sync.return_value = None

            # These should be fast even with fallback behavior
            for _ in range(100):
                img_tag("test.jpg", "Test")
                style_class("button")
                icon_tag("home")
