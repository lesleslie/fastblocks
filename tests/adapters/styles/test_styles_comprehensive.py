"""Comprehensive tests for FastBlocks style adapters."""

from uuid import UUID

import pytest
from fastblocks.adapters.style._base import StyleBase
from fastblocks.adapters.style.vanilla import VanillaStyle, VanillaStyleSettings
from fastblocks.adapters.style.webawesome import (
    WebAwesomeStyle,
    WebAwesomeStyleSettings,
)


@pytest.mark.unit
class TestStyleBase:
    """Test StyleBase adapter functionality."""

    def test_styles_base_inheritance(self):
        """Test StyleBase inherits from correct base classes."""
        adapter = StyleBase()
        assert hasattr(adapter, "MODULE_ID")
        assert hasattr(adapter, "MODULE_STATUS")
        assert adapter.MODULE_STATUS == "stable"
        assert isinstance(adapter.MODULE_ID, UUID)

    def test_styles_base_protocol_compliance(self):
        """Test StyleBase implements StylesProtocol."""
        # Check that required methods exist
        required_methods = ["get_component_class", "get_stylesheet_links"]
        for method in required_methods:
            assert hasattr(StyleBase, method)

    def test_styles_base_abstract_methods(self):
        """Test abstract methods raise NotImplementedError."""
        adapter = StyleBase()

        with pytest.raises(NotImplementedError):
            adapter.get_component_class("button")

        with pytest.raises(NotImplementedError):
            adapter.get_stylesheet_links()


@pytest.mark.unit
class TestVanillaStyle:
    """Test Vanilla CSS adapter functionality."""

    def test_vanilla_adapter_initialization(self):
        """Test Vanilla CSS adapter initializes correctly."""
        adapter = VanillaStyle()
        assert isinstance(adapter.settings, VanillaStyleSettings)
        assert adapter.MODULE_STATUS == "stable"
        assert isinstance(adapter.MODULE_ID, UUID)

    def test_vanilla_settings_defaults(self):
        """Test Vanilla CSS settings have correct defaults."""
        settings = VanillaStyleSettings()
        assert settings.css_paths == ["/static/css/base.css"]
        assert settings.custom_properties == {}
        assert settings.css_variables == {}

    def test_vanilla_get_component_class_basic(self):
        """Test basic component class retrieval."""
        adapter = VanillaStyle()

        button_class = adapter.get_component_class("button")
        assert button_class == "btn"  # Semantic mapping

        card_class = adapter.get_component_class("card")
        assert card_class == "card"

    def test_vanilla_get_component_class_with_css_variables(self):
        """Test component class with CSS variables."""
        adapter = VanillaStyle()
        adapter.settings.css_variables = {"primary-color": "#007bff"}

        css_vars = adapter.get_css_variables()
        assert "--primary-color: #007bff;" in css_vars

    def test_vanilla_get_component_class_unknown(self):
        """Test unknown component class handling."""
        adapter = VanillaStyle()

        unknown_class = adapter.get_component_class("unknown-component")
        assert unknown_class == "unknown-component"

    def test_vanilla_get_stylesheet_links_empty(self):
        """Test stylesheet links for vanilla CSS (should use default paths)."""
        adapter = VanillaStyle()

        links = adapter.get_stylesheet_links()

        assert isinstance(links, list)
        assert any("/static/css/base.css" in link for link in links)

    def test_vanilla_get_stylesheet_links_with_custom(self):
        """Test stylesheet links with custom stylesheets."""
        adapter = VanillaStyle()
        adapter.settings.css_paths = [
            "/static/css/custom.css",
            "/static/css/components.css",
        ]

        links = adapter.get_stylesheet_links()

        assert isinstance(links, list)
        assert any("/static/css/custom.css" in link for link in links)
        assert any("/static/css/components.css" in link for link in links)

    def test_vanilla_get_utility_classes(self):
        """Test utility classes retrieval."""
        adapter = VanillaStyle()

        utilities = adapter.get_utility_classes()

        assert isinstance(utilities, dict)
        assert "text_center" in utilities
        assert "background_primary" in utilities
        assert "margin_large" in utilities

    def test_vanilla_build_component_html(self):
        """Test component HTML building."""
        adapter = VanillaStyle()

        html = adapter.build_component_html(
            "button", "Click Me", **{"class": "btn--primary"}
        )

        assert "<button" in html
        assert 'class="btn btn--primary"' in html
        assert "Click Me" in html

    def test_vanilla_semantic_mappings(self):
        """Test semantic class mappings."""
        adapter = VanillaStyle()

        # Test common semantic mappings
        assert adapter.get_component_class("button") == "btn"
        assert adapter.get_component_class("input") == "form__input"
        assert adapter.get_component_class("navbar") == "navbar"

    def test_vanilla_modifier_application(self):
        """Test modifier application in HTML building."""
        adapter = VanillaStyle()

        html = adapter.build_component_html(
            "button", "Submit", **{"class": "btn--primary btn--large custom-btn"}
        )

        assert 'class="btn btn--primary btn--large custom-btn"' in html


@pytest.mark.unit
class TestStyleIntegration:
    """Test style adapter integration patterns."""

    def test_multiple_adapters_coexistence(self):
        """Test multiple style adapters can coexist."""
        webawesome = WebAwesomeStyle()
        vanilla = VanillaStyle()

        # Both should have different MODULE_IDs
        assert webawesome.MODULE_ID != vanilla.MODULE_ID

        # Both should implement the same protocol
        for adapter in [webawesome, vanilla]:
            assert hasattr(adapter, "get_component_class")
            assert hasattr(adapter, "get_stylesheet_links")

    def test_adapter_consistency(self):
        """Test adapter method consistency."""
        adapters = [WebAwesomeStyle(), VanillaStyle()]

        for adapter in adapters:
            # Test required methods return correct types
            component_class = adapter.get_component_class("button")
            assert isinstance(component_class, str)

            stylesheet_links = adapter.get_stylesheet_links()
            assert isinstance(stylesheet_links, list)

            if hasattr(adapter, "get_utility_classes"):
                utility_classes = adapter.get_utility_classes()
                assert isinstance(utility_classes, dict)

    def test_framework_switching(self):
        """Test framework switching capabilities."""
        # Test that adapters can be swapped easily
        webawesome = WebAwesomeStyle()
        vanilla = VanillaStyle()

        # Same method calls should work with different frameworks
        webawesome_button = webawesome.get_component_class("button")
        vanilla_button = vanilla.get_component_class("button")

        assert isinstance(webawesome_button, str)
        assert isinstance(vanilla_button, str)
        # Results may differ but should be valid CSS classes
        assert "wa-btn" in webawesome_button
        assert vanilla_button == "btn"

    def test_protocol_compliance(self):
        """Test all adapters comply with StylesProtocol."""
        adapters = [WebAwesomeStyle(), VanillaStyle()]

        for adapter in adapters:
            # Test required methods exist and work
            component_class = adapter.get_component_class("test")
            assert isinstance(component_class, str)

            stylesheet_links = adapter.get_stylesheet_links()
            assert isinstance(stylesheet_links, list)

    def test_settings_customization(self):
        """Test settings customization."""
        # Test WebAwesome customization
        webawesome = WebAwesomeStyle()
        webawesome.settings = WebAwesomeStyleSettings()
        webawesome.settings.version = "6.0.0"
        webawesome.settings.include_brands = False

        assert webawesome.settings.version == "6.0.0"
        assert webawesome.settings.include_brands is False

        # Test Vanilla CSS customization
        vanilla = VanillaStyle()
        vanilla.settings.css_paths = ["/my/styles.css"]
        vanilla.settings.css_variables = {"brand-color": "#FF0000"}

        assert "/my/styles.css" in vanilla.settings.css_paths
        assert vanilla.settings.css_variables["brand-color"] == "#FF0000"

    def test_html_building_patterns(self):
        """Test HTML building patterns across adapters."""
        adapters = [VanillaStyle()]

        for adapter in adapters:
            if hasattr(adapter, "build_component_html"):
                html = adapter.build_component_html(
                    "button", "Test", **{"class": "btn--primary"}
                )

                # All should produce valid HTML
                assert "<button" in html
                assert "class=" in html
                assert "Test" in html
                assert ">" in html

    def test_error_handling(self):
        """Test error handling in adapters."""
        adapters = [WebAwesomeStyle(), VanillaStyle()]

        for adapter in adapters:
            # Test with invalid/empty inputs
            result = adapter.get_component_class("")
            assert isinstance(result, str)  # Should handle gracefully

            # Test with None (should handle gracefully)
            try:
                result = adapter.get_component_class(None)
                assert isinstance(result, str)
            except (TypeError, AttributeError):
                # Some adapters might not handle None gracefully, which is acceptable
                pass
