"""Comprehensive tests for FastBlocks font adapters."""

from uuid import UUID

import pytest
from fastblocks.adapters.fonts._base import FontsBase
from fastblocks.adapters.fonts.google import GoogleFonts, GoogleFontsSettings
from fastblocks.adapters.fonts.squirrel import (
    FontSquirrelFonts,
    FontSquirrelFontsSettings,
)


@pytest.mark.unit
class TestFontsBase:
    """Test FontsBase adapter functionality."""

    def test_fonts_base_inheritance(self):
        """Test FontsBase inherits from correct base classes."""
        adapter = FontsBase()
        assert hasattr(adapter, "MODULE_ID")
        assert hasattr(adapter, "MODULE_STATUS")
        assert adapter.MODULE_STATUS == "stable"
        assert isinstance(adapter.MODULE_ID, UUID)

    def test_fonts_base_protocol_compliance(self):
        """Test FontsBase implements FontsProtocol."""
        # Check that required methods exist
        required_methods = ["get_font_import", "get_font_family"]
        for method in required_methods:
            assert hasattr(FontsBase, method)

    def test_fonts_base_abstract_methods(self):
        """Test abstract methods raise NotImplementedError."""
        adapter = FontsBase()

        with pytest.raises(NotImplementedError):
            adapter.get_font_family("primary")


@pytest.mark.unit
class TestGoogleFonts:
    """Test Google Fonts adapter functionality."""

    def test_google_fonts_initialization(self):
        """Test Google Fonts adapter initializes correctly."""
        adapter = GoogleFonts()
        assert isinstance(adapter.settings, GoogleFontsSettings)
        assert adapter.MODULE_STATUS == "stable"
        assert isinstance(adapter.MODULE_ID, UUID)

    def test_google_fonts_settings_defaults(self):
        """Test Google Fonts settings have correct defaults."""
        settings = GoogleFontsSettings()
        assert settings.families == ["Roboto", "Open Sans"]
        assert settings.weights == ["400", "700"]
        assert settings.subsets == ["latin"]
        assert settings.display == "swap"
        assert settings.preconnect is True

    @pytest.mark.asyncio
    async def test_google_fonts_get_font_import_basic(self):
        """Test basic font import generation."""
        adapter = GoogleFonts()
        adapter.settings.families = ["Roboto"]
        adapter.settings.weights = ["400", "700"]

        import_html = await adapter.get_font_import()

        assert '<link rel="preconnect"' in import_html
        assert "fonts.googleapis.com" in import_html
        assert "fonts.gstatic.com" in import_html
        assert "Roboto" in import_html
        assert "display=swap" in import_html

    @pytest.mark.asyncio
    async def test_google_fonts_get_font_import_multiple_families(self):
        """Test font import with multiple families."""
        adapter = GoogleFonts()
        adapter.settings.families = ["Roboto", "Open Sans", "Lato"]
        adapter.settings.weights = ["300", "400", "700"]

        import_html = await adapter.get_font_import()

        assert "Roboto" in import_html
        assert "Open+Sans" in import_html  # URL encoded
        assert "Lato" in import_html

    @pytest.mark.asyncio
    async def test_google_fonts_get_font_import_with_subsets(self):
        """Test font import with subsets."""
        adapter = GoogleFonts()
        adapter.settings.families = ["Roboto"]
        adapter.settings.subsets = ["latin", "latin-ext", "cyrillic"]

        import_html = await adapter.get_font_import()

        assert "subset=latin" in import_html or "latin" in import_html

    def test_google_fonts_get_font_family_primary(self):
        """Test primary font family retrieval."""
        adapter = GoogleFonts()
        adapter.settings.families = ["Inter", "Roboto"]

        family = adapter.get_font_family("primary")

        assert "Inter" in family
        assert "BlinkMacSystemFont" in family  # Fallback
        assert "sans-serif" in family

    def test_google_fonts_get_font_family_secondary(self):
        """Test secondary font family retrieval."""
        adapter = GoogleFonts()
        adapter.settings.families = ["Inter", "Playfair Display"]

        family = adapter.get_font_family("secondary")

        assert "Playfair Display" in family
        assert "serif" in family

    def test_google_fonts_get_font_family_fallback(self):
        """Test font family fallback handling."""
        adapter = GoogleFonts()
        adapter.settings.families = []

        family = adapter.get_font_family("primary")

        assert "BlinkMacSystemFont" in family
        assert "sans-serif" in family

    def test_google_fonts_build_families_param(self):
        """Test families parameter building."""
        adapter = GoogleFonts()
        adapter.settings.families = ["Roboto", "Open Sans"]
        adapter.settings.weights = ["400", "700"]

        families_param = adapter._build_families_param()

        assert "Roboto" in families_param
        assert "Open+Sans" in families_param
        assert "wght@400" in families_param
        assert "wght@700" in families_param

    def test_google_fonts_get_css_variables(self):
        """Test CSS variables generation."""
        adapter = GoogleFonts()
        adapter.settings.families = ["Inter", "Playfair Display"]
        adapter.settings.weights = ["400", "600", "700"]

        css_vars = adapter.get_css_variables()

        assert ":root {" in css_vars
        assert "--font-primary:" in css_vars
        assert "--font-secondary:" in css_vars
        assert "--font-weight-normal:" in css_vars
        assert "--font-weight-bold:" in css_vars

    def test_google_fonts_get_font_preload(self):
        """Test font preload link generation."""
        adapter = GoogleFonts()

        preload_link = adapter.get_font_preload("Roboto", "400")

        assert '<link rel="preload"' in preload_link
        assert 'as="font"' in preload_link
        assert "crossorigin" in preload_link
        assert "roboto" in preload_link.lower()

    def test_google_fonts_validate_font_availability(self):
        """Test font availability validation."""
        adapter = GoogleFonts()

        # Test common fonts
        assert adapter.validate_font_availability("Roboto") is True
        assert adapter.validate_font_availability("Open Sans") is True
        assert adapter.validate_font_availability("Inter") is True

        # Test uncommon font (might return False in basic implementation)
        result = adapter.validate_font_availability("Very-Rare-Font-12345")
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_google_fonts_get_optimized_import(self):
        """Test optimized import with critical fonts."""
        adapter = GoogleFonts()
        adapter.settings.families = ["Roboto", "Open Sans", "Lato"]

        critical_fonts = ["Roboto"]
        optimized_import = await adapter.get_optimized_import(critical_fonts)

        assert isinstance(optimized_import, str)
        assert "Roboto" in optimized_import


@pytest.mark.unit
class TestFontSquirrelAdapter:
    """Test Font Squirrel adapter functionality."""

    def test_font_squirrel_adapter_initialization(self):
        """Test Font Squirrel adapter initializes correctly."""
        adapter = FontSquirrelFonts()
        assert isinstance(adapter.settings, FontSquirrelFontsSettings)
        assert adapter.MODULE_STATUS == "stable"
        assert isinstance(adapter.MODULE_ID, UUID)

    def test_font_squirrel_settings_defaults(self):
        """Test Font Squirrel settings have correct defaults."""
        settings = FontSquirrelFontsSettings()
        assert settings.fonts_dir == "/static/fonts"
        assert settings.fonts == []
        assert settings.preload_critical is True
        assert settings.display == "swap"

    @pytest.mark.asyncio
    async def test_font_squirrel_get_font_import_empty(self):
        """Test font import with no fonts configured."""
        adapter = FontSquirrelFonts()
        adapter.settings.fonts = []

        import_html = await adapter.get_font_import()

        assert "No self-hosted fonts configured" in import_html

    @pytest.mark.asyncio
    async def test_font_squirrel_get_font_import_single_font(self):
        """Test font import with single font."""
        adapter = FontSquirrelFonts()
        adapter.settings.fonts = [
            {
                "family": "Custom Font",
                "path": "/fonts/custom-font.woff2",
                "weight": "400",
                "style": "normal",
            }
        ]

        import_html = await adapter.get_font_import()

        assert "<style>" in import_html
        assert "@font-face" in import_html
        assert "Custom Font" in import_html
        assert "custom-font.woff2" in import_html
        assert "font-weight: 400" in import_html
        assert "font-display: swap" in import_html

    @pytest.mark.asyncio
    async def test_font_squirrel_get_font_import_multiple_formats(self):
        """Test font import with multiple formats."""
        adapter = FontSquirrelFonts()
        adapter.settings.fonts = [
            {
                "family": "Multi Format Font",
                "files": [
                    {"path": "/fonts/font.woff2", "format": "woff2"},
                    {"path": "/fonts/font.woff", "format": "woff"},
                    {"path": "/fonts/font.ttf", "format": "ttf"},
                ],
                "weight": "400",
                "style": "normal",
            }
        ]

        import_html = await adapter.get_font_import()

        assert "font.woff2" in import_html
        assert "font.woff" in import_html
        assert "font.ttf" in import_html
        assert "format('woff2')" in import_html
        assert "format('woff')" in import_html
        assert "format('truetype')" in import_html

    def test_font_squirrel_get_font_family_configured(self):
        """Test font family retrieval for configured fonts."""
        adapter = FontSquirrelFonts()
        adapter.settings.fonts = [
            {
                "type": "primary",
                "family": "Custom Primary",
                "fallback": "Arial, sans-serif",
            }
        ]

        family = adapter.get_font_family("primary")

        assert "Custom Primary" in family
        assert "Arial, sans-serif" in family

    def test_font_squirrel_get_font_family_fallback(self):
        """Test font family fallback for unconfigured types."""
        adapter = FontSquirrelFonts()
        adapter.settings.fonts = []

        family = adapter.get_font_family("primary")

        assert "BlinkMacSystemFont" in family
        assert "sans-serif" in family

    def test_font_squirrel_generate_font_face(self):
        """Test font-face declaration generation."""
        adapter = FontSquirrelFonts()

        font_config = {
            "family": "Test Font",
            "path": "/fonts/test.woff2",
            "weight": "600",
            "style": "italic",
            "unicode_range": "U+0000-00FF",
        }

        font_face = adapter._generate_font_face(font_config)

        assert "@font-face {" in font_face
        assert "font-family: 'Test Font'" in font_face
        assert "font-weight: 600" in font_face
        assert "font-style: italic" in font_face
        assert "unicode-range: U+0000-00FF" in font_face
        assert "src:" in font_face

    def test_font_squirrel_build_src_declaration_single_file(self):
        """Test src declaration for single file."""
        adapter = FontSquirrelFonts()

        font_config = {"path": "/fonts/test.woff2"}
        src = adapter._build_src_declaration(font_config)

        assert "url('/static/fonts/test.woff2')" in src
        assert "format('woff2')" in src

    def test_font_squirrel_build_src_declaration_multiple_files(self):
        """Test src declaration for multiple files."""
        adapter = FontSquirrelFonts()

        font_config = {
            "files": [
                {"path": "/fonts/test.woff2", "format": "woff2"},
                {"path": "/fonts/test.woff", "format": "woff"},
            ]
        }

        src = adapter._build_src_declaration(font_config)

        assert "test.woff2" in src
        assert "test.woff" in src
        assert "format('woff2')" in src
        assert "format('woff')" in src

    def test_font_squirrel_get_format_from_path(self):
        """Test format detection from file path."""
        adapter = FontSquirrelFonts()

        assert adapter._get_format_from_path("/fonts/test.woff2") == "woff2"
        assert adapter._get_format_from_path("/fonts/test.woff") == "woff"
        assert adapter._get_format_from_path("/fonts/test.ttf") == "truetype"
        assert adapter._get_format_from_path("/fonts/test.otf") == "opentype"
        assert adapter._get_format_from_path("/fonts/test.eot") == "embedded-opentype"

    def test_font_squirrel_normalize_font_url(self):
        """Test font URL normalization."""
        adapter = FontSquirrelFonts()

        # Test relative path
        assert adapter._normalize_font_url("test.woff2") == "/static/fonts/test.woff2"

        # Test absolute path
        assert (
            adapter._normalize_font_url("/custom/path/test.woff2")
            == "/custom/path/test.woff2"
        )

        # Test full URL
        assert (
            adapter._normalize_font_url("https://cdn.example.com/font.woff2")
            == "https://cdn.example.com/font.woff2"
        )

    def test_font_squirrel_get_preload_links(self):
        """Test preload links generation."""
        adapter = FontSquirrelFonts()
        adapter.settings.fonts = [
            {
                "family": "Primary Font",
                "type": "primary",
                "path": "/fonts/primary.woff2",
            }
        ]

        preload_links = adapter.get_preload_links()

        assert '<link rel="preload"' in preload_links
        assert 'as="font"' in preload_links
        assert "crossorigin" in preload_links
        assert "primary.woff2" in preload_links

    def test_font_squirrel_get_preload_links_disabled(self):
        """Test preload links when disabled."""
        adapter = FontSquirrelFonts()
        adapter.settings.preload_critical = False

        preload_links = adapter.get_preload_links()

        assert preload_links == ""

    def test_font_squirrel_validate_font_files(self):
        """Test font file validation."""
        adapter = FontSquirrelFonts()
        adapter.settings.fonts = [
            {"family": "Valid Font", "path": "/fonts/valid.woff2"},
            {
                "family": "Multi File Font",
                "files": [
                    {"path": "/fonts/multi1.woff2"},
                    {"path": "/fonts/multi2.woff"},
                ],
            },
            {
                "family": "No Files Font"
                # No path or files specified
            },
        ]

        validation = adapter.validate_font_files()

        assert "valid" in validation
        assert "invalid" in validation
        assert "warnings" in validation
        assert len(validation["valid"]) >= 3  # At least 3 valid entries
        assert len(validation["warnings"]) >= 1  # At least 1 warning

    def test_font_squirrel_discover_font_files(self):
        """Test font file discovery."""
        adapter = FontSquirrelFonts()

        discovered = adapter._discover_font_files(
            "/fonts", "Custom Font", "400", "normal"
        )

        # Should return list of tuples (path, format)
        assert isinstance(discovered, list)
        for item in discovered:
            assert isinstance(item, tuple)
            assert len(item) == 2
            path, format_hint = item
            assert "/fonts" in path
            assert "custom" in path.lower()


@pytest.mark.unit
class TestFontAdapterIntegration:
    """Test font adapter integration patterns."""

    def test_multiple_adapters_coexistence(self):
        """Test multiple font adapters can coexist."""
        google = GoogleFonts()
        squirrel = FontSquirrelFonts()

        # Both should have different MODULE_IDs
        assert google.MODULE_ID != squirrel.MODULE_ID

        # Both should implement the same protocol
        for adapter in [google, squirrel]:
            assert hasattr(adapter, "get_font_family")

    @pytest.mark.asyncio
    async def test_adapter_consistency(self):
        """Test adapter method consistency."""
        adapters = [GoogleFonts(), FontSquirrelFonts()]

        for adapter in adapters:
            # Test required methods return correct types
            family = adapter.get_font_family("primary")
            assert isinstance(family, str)

            if hasattr(adapter, "get_font_import"):
                import_html = await adapter.get_font_import()
                assert isinstance(import_html, str)

    def test_font_provider_switching(self):
        """Test font provider switching capabilities."""
        google = GoogleFonts()
        squirrel = FontSquirrelFonts()

        # Same method calls should work with different providers
        google_primary = google.get_font_family("primary")
        squirrel_primary = squirrel.get_font_family("primary")

        assert isinstance(google_primary, str)
        assert isinstance(squirrel_primary, str)

    @pytest.mark.asyncio
    async def test_protocol_compliance(self):
        """Test all adapters comply with FontsProtocol."""
        adapters = [GoogleFonts(), FontSquirrelFonts()]

        for adapter in adapters:
            # Test required methods exist and work
            family = adapter.get_font_family("primary")
            assert isinstance(family, str)

    def test_settings_customization(self):
        """Test settings customization."""
        # Test Google Fonts customization
        google = GoogleFonts()
        google.settings.families = ["Inter", "Roboto Slab"]
        google.settings.weights = ["300", "400", "600"]
        google.settings.display = "block"

        assert google.settings.families == ["Inter", "Roboto Slab"]
        assert google.settings.weights == ["300", "400", "600"]
        assert google.settings.display == "block"

        # Test Font Squirrel customization
        squirrel = FontSquirrelFonts()
        squirrel.settings.fonts_dir = "/custom/fonts"
        squirrel.settings.display = "fallback"

        assert squirrel.settings.fonts_dir == "/custom/fonts"
        assert squirrel.settings.display == "fallback"

    @pytest.mark.asyncio
    async def test_performance_optimization(self):
        """Test performance optimization features."""
        google = GoogleFonts()
        google.settings.families = ["Inter", "Roboto"]

        # Test optimized import
        optimized = await google.get_optimized_import(["Inter"])
        assert isinstance(optimized, str)

        # Test CSS variables for performance
        css_vars = google.get_css_variables()
        assert "--font-" in css_vars

        # Test preload for Font Squirrel
        squirrel = FontSquirrelFonts()
        squirrel.settings.fonts = [
            {"family": "Custom", "type": "primary", "path": "/fonts/custom.woff2"}
        ]

        preload = squirrel.get_preload_links()
        assert isinstance(preload, str)

    def test_error_handling(self):
        """Test error handling in adapters."""
        adapters = [GoogleFonts(), FontSquirrelFonts()]

        for adapter in adapters:
            # Test with invalid/empty inputs
            result = adapter.get_font_family("")
            assert isinstance(result, str)  # Should handle gracefully

            # Test with unknown font types
            result = adapter.get_font_family("unknown-font-type-12345")
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_font_loading_strategies(self):
        """Test different font loading strategies."""
        google = GoogleFonts()
        google.settings.display = "swap"
        google.settings.preconnect = True

        import_html = await google.get_font_import()

        # Should include preconnect for performance
        assert "preconnect" in import_html
        assert "display=swap" in import_html

        squirrel = FontSquirrelFonts()
        squirrel.settings.display = "block"
        squirrel.settings.preload_critical = True

        # Test that display setting is applied
        assert squirrel.settings.display == "block"
