"""Comprehensive tests for FastBlocks icon adapters."""

from uuid import UUID

import pytest
from fastblocks.adapters.icons._base import IconsBase
from fastblocks.adapters.icons.fontawesome import (
    FontAwesomeIcons,
    FontAwesomeIconsSettings,
)
from fastblocks.adapters.icons.lucide import LucideIcons, LucideIconsSettings


@pytest.mark.unit
class TestIconsBase:
    """Test IconsBase adapter functionality."""

    def test_icons_base_inheritance(self):
        """Test IconsBase inherits from correct base classes."""
        adapter = IconsBase()
        assert hasattr(adapter, "MODULE_ID")
        assert hasattr(adapter, "MODULE_STATUS")
        assert adapter.MODULE_STATUS == "stable"
        assert isinstance(adapter.MODULE_ID, UUID)

    def test_icons_base_protocol_compliance(self):
        """Test IconsBase implements IconsProtocol."""
        # Check that required methods exist
        required_methods = ["get_icon_tag", "get_stylesheet_links"]
        for method in required_methods:
            assert hasattr(IconsBase, method)

    def test_icons_base_abstract_methods(self):
        """Test abstract methods raise NotImplementedError."""
        adapter = IconsBase()

        with pytest.raises(NotImplementedError):
            adapter.get_icon_tag("home")

        with pytest.raises(NotImplementedError):
            adapter.get_stylesheet_links()


@pytest.mark.unit
class TestFontAwesomeAdapter:
    """Test FontAwesome icon adapter functionality."""

    def test_fontawesome_adapter_initialization(self):
        """Test FontAwesome adapter initializes correctly."""
        adapter = FontAwesomeIcons()
        assert isinstance(adapter.settings, FontAwesomeIconsSettings)
        assert adapter.MODULE_STATUS == "stable"
        assert isinstance(adapter.MODULE_ID, UUID)

    def test_fontawesome_settings_defaults(self):
        """Test FontAwesome settings have correct defaults."""
        settings = FontAwesomeIconsSettings()
        assert settings.version == "6.4.0"
        assert settings.style == "solid"
        assert settings.prefix == "fas"
        assert settings.cdn is True

    def test_fontawesome_get_icon_tag_basic(self):
        """Test basic icon tag generation."""
        adapter = FontAwesomeIcons()

        icon_tag = adapter.get_icon_tag("home")

        assert "<i" in icon_tag
        assert 'class="fas fa-home"' in icon_tag
        assert "</i>" in icon_tag

    def test_fontawesome_get_icon_tag_with_attributes(self):
        """Test icon tag with additional attributes."""
        adapter = FontAwesomeIcons()

        icon_tag = adapter.get_icon_tag(
            "user", class_="nav-icon", id="user-icon", size="2x"
        )

        assert 'class="fas fa-user nav-icon"' in icon_tag
        assert 'id="user-icon"' in icon_tag
        # Size should be handled by FontAwesome's sizing classes

    def test_fontawesome_get_icon_tag_different_styles(self):
        """Test icon tag with different FontAwesome styles."""
        adapter = FontAwesomeIcons()

        # Test solid style (default)
        solid_icon = adapter.get_icon_tag("heart")
        assert "fas fa-heart" in solid_icon

        # Test regular style
        adapter.settings.style = "regular"
        adapter.settings.prefix = "far"
        regular_icon = adapter.get_icon_tag("heart")
        assert "far fa-heart" in regular_icon

        # Test brands style
        adapter.settings.style = "brands"
        adapter.settings.prefix = "fab"
        brand_icon = adapter.get_icon_tag("github")
        assert "fab fa-github" in brand_icon

    def test_fontawesome_get_stylesheet_links_cdn(self):
        """Test CDN stylesheet links generation."""
        adapter = FontAwesomeIcons()
        adapter.settings.cdn = True
        adapter.settings.version = "6.4.0"

        links = adapter.get_stylesheet_links()

        assert isinstance(links, list)
        assert len(links) > 0
        assert any("fontawesome" in link.lower() for link in links)
        assert any("6.4.0" in link for link in links)

    def test_fontawesome_get_stylesheet_links_local(self):
        """Test local stylesheet links generation."""
        adapter = FontAwesomeIcons()
        adapter.settings.cdn = False
        adapter.settings.local_path = "/static/css/fontawesome.min.css"

        links = adapter.get_stylesheet_links()

        assert isinstance(links, list)
        assert any("/static/css/fontawesome.min.css" in link for link in links)

    def test_fontawesome_icon_mapping(self):
        """Test icon name mapping."""
        adapter = FontAwesomeIcons()

        # Test common icon mappings
        common_icons = ["home", "user", "search", "menu", "close", "check"]
        for icon_name in common_icons:
            icon_tag = adapter.get_icon_tag(icon_name)
            assert f"fa-{icon_name}" in icon_tag

    def test_fontawesome_get_icon_with_text(self):
        """Test icon with text generation."""
        adapter = FontAwesomeIcons()

        icon_with_text = adapter.get_icon_with_text(
            "save", "Save Document", position="left"
        )

        assert '<i class="fas fa-save"' in icon_with_text
        assert "Save Document" in icon_with_text
        # Icon should come before text for left position

    def test_fontawesome_normalize_icon_name(self):
        """Test icon name normalization."""
        adapter = FontAwesomeIcons()

        # Test various icon name formats
        assert adapter._normalize_icon_name("home") == "home"
        assert adapter._normalize_icon_name("user-circle") == "user-circle"
        assert adapter._normalize_icon_name("fa-home") == "home"  # Remove fa- prefix
        assert adapter._normalize_icon_name("fas-home") == "home"  # Remove style prefix


@pytest.mark.unit
class TestLucideAdapter:
    """Test Lucide icon adapter functionality."""

    def test_lucide_adapter_initialization(self):
        """Test Lucide adapter initializes correctly."""
        adapter = LucideIcons()
        assert isinstance(adapter.settings, LucideIconsSettings)
        assert adapter.MODULE_STATUS == "stable"
        assert isinstance(adapter.MODULE_ID, UUID)

    def test_lucide_settings_defaults(self):
        """Test Lucide settings have correct defaults."""
        settings = LucideIconsSettings()
        assert settings.version == "latest"
        assert settings.mode == "svg"
        assert settings.size == 24
        assert settings.stroke_width == 2

    def test_lucide_get_icon_tag_svg_mode(self):
        """Test SVG icon tag generation."""
        adapter = LucideIcons()
        adapter.settings.mode = "svg"

        icon_tag = adapter.get_icon_tag("home")

        assert "<svg" in icon_tag
        assert 'width="24"' in icon_tag
        assert 'height="24"' in icon_tag
        assert 'stroke-width="2"' in icon_tag
        assert "</svg>" in icon_tag

    def test_lucide_get_icon_tag_font_mode(self):
        """Test font icon tag generation."""
        adapter = LucideIcons()
        adapter.settings.mode = "font"

        icon_tag = adapter.get_icon_tag("home")

        assert "<i" in icon_tag
        assert 'class="lucide lucide-home"' in icon_tag
        assert "</i>" in icon_tag

    def test_lucide_get_icon_tag_with_custom_size(self):
        """Test icon tag with custom size."""
        adapter = LucideIcons()
        adapter.settings.mode = "svg"

        icon_tag = adapter.get_icon_tag("user", size=32)

        assert 'width="32"' in icon_tag
        assert 'height="32"' in icon_tag

    def test_lucide_get_icon_tag_with_attributes(self):
        """Test icon tag with additional attributes."""
        adapter = LucideIcons()
        adapter.settings.mode = "svg"

        icon_tag = adapter.get_icon_tag(
            "search", class_="search-icon", id="main-search", stroke_width=1.5
        )

        assert 'class="search-icon"' in icon_tag
        assert 'id="main-search"' in icon_tag
        assert 'stroke-width="1.5"' in icon_tag

    def test_lucide_get_stylesheet_links_font_mode(self):
        """Test stylesheet links for font mode."""
        adapter = LucideIcons()
        adapter.settings.mode = "font"
        adapter.settings.cdn = True

        links = adapter.get_stylesheet_links()

        assert isinstance(links, list)
        assert len(links) > 0
        assert any("lucide" in link.lower() for link in links)

    def test_lucide_get_stylesheet_links_svg_mode(self):
        """Test stylesheet links for SVG mode (should be empty)."""
        adapter = LucideIcons()
        adapter.settings.mode = "svg"

        links = adapter.get_stylesheet_links()

        assert isinstance(links, list)
        # SVG mode typically doesn't need external stylesheets

    def test_lucide_get_icon_svg(self):
        """Test direct SVG icon generation."""
        adapter = LucideIcons()

        svg = adapter.get_icon_svg("heart", size=20, stroke_width=1.5)

        assert "<svg" in svg
        assert 'width="20"' in svg
        assert 'height="20"' in svg
        assert 'stroke-width="1.5"' in svg

    def test_lucide_icon_mapping(self):
        """Test icon name mapping and validation."""
        adapter = LucideIcons()

        # Test common Lucide icons
        common_icons = ["home", "user", "search", "menu", "x", "check"]
        for icon_name in common_icons:
            icon_tag = adapter.get_icon_tag(icon_name)
            assert icon_name in icon_tag

    def test_lucide_normalize_icon_name(self):
        """Test icon name normalization."""
        adapter = LucideIcons()

        # Test various icon name formats
        assert adapter._normalize_icon_name("home") == "home"
        assert adapter._normalize_icon_name("user-circle") == "user-circle"
        assert adapter._normalize_icon_name("Menu") == "menu"  # Lowercase conversion

    def test_lucide_get_icon_with_text(self):
        """Test icon with text generation."""
        adapter = LucideIcons()

        icon_with_text = adapter.get_icon_with_text(
            "download", "Download File", position="left"
        )

        if adapter.settings.mode == "svg":
            assert "<svg" in icon_with_text
        else:
            assert '<i class="lucide lucide-download"' in icon_with_text
        assert "Download File" in icon_with_text


@pytest.mark.unit
class TestIconAdapterIntegration:
    """Test icon adapter integration patterns."""

    def test_multiple_adapters_coexistence(self):
        """Test multiple icon adapters can coexist."""
        fontawesome = FontAwesomeIcons()
        lucide = LucideIcons()

        # Both should have different MODULE_IDs
        assert fontawesome.MODULE_ID != lucide.MODULE_ID

        # Both should implement the same protocol
        for adapter in [fontawesome, lucide]:
            assert hasattr(adapter, "get_icon_tag")
            assert hasattr(adapter, "get_stylesheet_links")

    def test_adapter_consistency(self):
        """Test adapter method consistency."""
        adapters = [FontAwesomeIcons(), LucideIcons()]

        for adapter in adapters:
            # Test required methods return correct types
            icon_tag = adapter.get_icon_tag("home")
            assert isinstance(icon_tag, str)
            assert len(icon_tag) > 0

            stylesheet_links = adapter.get_stylesheet_links()
            assert isinstance(stylesheet_links, list)

    def test_icon_library_switching(self):
        """Test icon library switching capabilities."""
        fontawesome = FontAwesomeIcons()
        lucide = LucideIcons()

        # Same method calls should work with different libraries
        fa_home = fontawesome.get_icon_tag("home")
        lucide_home = lucide.get_icon_tag("home")

        assert isinstance(fa_home, str)
        assert isinstance(lucide_home, str)
        # Results will differ but should be valid HTML
        assert "home" in fa_home.lower()
        assert "home" in lucide_home.lower()

    def test_protocol_compliance(self):
        """Test all adapters comply with IconsProtocol."""
        adapters = [FontAwesomeIcons(), LucideIcons()]

        for adapter in adapters:
            # Test required methods exist and work
            icon_tag = adapter.get_icon_tag("test")
            assert isinstance(icon_tag, str)

            stylesheet_links = adapter.get_stylesheet_links()
            assert isinstance(stylesheet_links, list)

    def test_settings_customization(self):
        """Test settings customization."""
        # Test FontAwesome customization
        fa = FontAwesomeIcons()
        fa.settings.version = "6.0.0"
        fa.settings.style = "regular"
        fa.settings.prefix = "far"

        assert fa.settings.version == "6.0.0"
        assert fa.settings.style == "regular"
        assert fa.settings.prefix == "far"

        # Test Lucide customization
        lucide = LucideIcons()
        lucide.settings.mode = "font"
        lucide.settings.size = 32
        lucide.settings.stroke_width = 1.5

        assert lucide.settings.mode == "font"
        assert lucide.settings.size == 32
        assert lucide.settings.stroke_width == 1.5

    def test_icon_with_text_patterns(self):
        """Test icon with text patterns across adapters."""
        adapters = [FontAwesomeIcons(), LucideIcons()]

        for adapter in adapters:
            if hasattr(adapter, "get_icon_with_text"):
                # Test left position
                left_result = adapter.get_icon_with_text(
                    "save", "Save", position="left"
                )
                assert isinstance(left_result, str)
                assert "save" in left_result.lower()
                assert "Save" in left_result

                # Test right position
                right_result = adapter.get_icon_with_text(
                    "save", "Save", position="right"
                )
                assert isinstance(right_result, str)
                assert "save" in right_result.lower()
                assert "Save" in right_result

    def test_error_handling(self):
        """Test error handling in adapters."""
        adapters = [FontAwesomeIcons(), LucideIcons()]

        for adapter in adapters:
            # Test with invalid/empty inputs
            result = adapter.get_icon_tag("")
            assert isinstance(result, str)  # Should handle gracefully

            # Test with unknown icon names
            result = adapter.get_icon_tag("unknown-icon-name-12345")
            assert isinstance(result, str)  # Should handle gracefully

    def test_performance_considerations(self):
        """Test performance-related aspects."""
        adapters = [FontAwesomeIcons(), LucideIcons()]

        for adapter in adapters:
            # Test that repeated calls work consistently
            for _ in range(10):
                icon_tag = adapter.get_icon_tag("home")
                assert isinstance(icon_tag, str)
                assert len(icon_tag) > 0

    def test_accessibility_features(self):
        """Test accessibility features in icon generation."""
        adapters = [FontAwesomeIcons(), LucideIcons()]

        for adapter in adapters:
            # Test with aria-label
            icon_tag = adapter.get_icon_tag("home", aria_label="Home page")
            assert 'aria-label="Home page"' in icon_tag

            # Test with title attribute
            icon_tag = adapter.get_icon_tag("user", title="User profile")
            assert 'title="User profile"' in icon_tag
