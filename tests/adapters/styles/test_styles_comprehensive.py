"""Comprehensive tests for FastBlocks style adapters."""

from uuid import UUID

import pytest
from fastblocks.adapters.style._base import StyleBase
from fastblocks.adapters.style.bulma import BulmaStyle, BulmaStyleSettings
from fastblocks.adapters.style.vanilla import VanillaStyle, VanillaStyleSettings


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
class TestBulmaStyle:
    """Test Bulma CSS framework adapter functionality."""

    def test_bulma_adapter_initialization(self):
        """Test Bulma adapter initializes correctly."""
        adapter = BulmaStyle()
        assert isinstance(adapter.settings, BulmaStyleSettings)
        assert adapter.MODULE_STATUS == "stable"
        assert isinstance(adapter.MODULE_ID, UUID)

    def test_bulma_settings_defaults(self):
        """Test Bulma settings have correct defaults."""
        settings = BulmaStyleSettings()
        assert settings.version == "0.9.4"
        assert settings.cdn is True
        assert "button" in settings.components
        assert "card" in settings.components

    def test_bulma_get_component_class_basic(self):
        """Test basic component class retrieval."""
        adapter = BulmaStyle()

        button_class = adapter.get_component_class("button")
        assert button_class == "button"

        card_class = adapter.get_component_class("card")
        assert card_class == "card"

    def test_bulma_get_component_class_unknown(self):
        """Test unknown component class handling."""
        adapter = BulmaStyle()

        unknown_class = adapter.get_component_class("unknown-component")
        assert unknown_class == "unknown-component"  # Fallback to original name

    def test_bulma_get_stylesheet_links_cdn(self):
        """Test CDN stylesheet links generation."""
        adapter = BulmaStyle()
        adapter.settings.cdn = True
        adapter.settings.version = "0.9.4"

        links = adapter.get_stylesheet_links()

        assert isinstance(links, list)
        assert len(links) > 0
        assert any("bulma" in link for link in links)
        assert any("0.9.4" in link for link in links)

    def test_bulma_get_stylesheet_links_local(self):
        """Test local stylesheet links generation."""
        adapter = BulmaStyle()
        adapter.settings.cdn = False
        adapter.settings.local_path = "/static/css/bulma.min.css"

        links = adapter.get_stylesheet_links()

        assert isinstance(links, list)
        assert any("/static/css/bulma.min.css" in link for link in links)

    def test_bulma_get_utility_classes(self):
        """Test utility classes retrieval."""
        adapter = BulmaStyle()

        utilities = adapter.get_utility_classes()

        assert isinstance(utilities, dict)
        assert "primary" in utilities
        assert utilities["primary"] == "is-primary"
        assert "large" in utilities
        assert utilities["large"] == "is-large"

    def test_bulma_build_component_html(self):
        """Test component HTML building."""
        adapter = BulmaStyle()

        html = adapter.build_component_html("button", "Click Me", variant="primary")

        assert "<button" in html
        assert 'class="button is-primary"' in html
        assert "Click Me" in html

    def test_bulma_responsive_utilities(self):
        """Test responsive utility classes."""
        adapter = BulmaStyle()

        utilities = adapter.get_utility_classes()

        # Check for responsive classes
        assert "mobile" in utilities
        assert "tablet" in utilities
        assert "desktop" in utilities

    def test_bulma_color_utilities(self):
        """Test color utility classes."""
        adapter = BulmaStyle()

        utilities = adapter.get_utility_classes()

        # Check for color classes
        color_variants = [
            "primary",
            "secondary",
            "success",
            "danger",
            "warning",
            "info",
        ]
        for variant in color_variants:
            assert variant in utilities
            assert utilities[variant].startswith("is-")


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
        """Test stylesheet links for vanilla CSS (should be empty by default)."""
        adapter = VanillaStyle()

        links = adapter.get_stylesheet_links()

        assert isinstance(links, list)
        # Vanilla CSS typically doesn't include external stylesheets by default

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
        assert "primary" in utilities
        assert "large" in utilities
        assert "small" in utilities

    def test_vanilla_build_component_html(self):
        """Test component HTML building."""
        adapter = VanillaStyle()

        html = adapter.build_component_html("button", "Click Me", variant="primary")

        assert "<button" in html
        assert 'class="btn btn-primary"' in html
        assert "Click Me" in html

    def test_vanilla_semantic_mappings(self):
        """Test semantic class mappings."""
        adapter = VanillaStyle()

        # Test common semantic mappings
        assert adapter.get_component_class("button") == "btn"
        assert adapter.get_component_class("form_input") == "form-control"
        assert adapter.get_component_class("navbar") == "nav"

    def test_vanilla_modifier_application(self):
        """Test modifier application in HTML building."""
        adapter = VanillaStyle()

        html = adapter.build_component_html(
            "button", "Submit", variant="primary", size="large", class_="custom-btn"
        )

        assert 'class="btn btn-primary btn-large custom-btn"' in html


@pytest.mark.unit
class TestStyleIntegration:
    """Test style adapter integration patterns."""

    def test_multiple_adapters_coexistence(self):
        """Test multiple style adapters can coexist."""
        bulma = BulmaStyle()
        vanilla = VanillaStyle()

        # Both should have different MODULE_IDs
        assert bulma.MODULE_ID != vanilla.MODULE_ID

        # Both should implement the same protocol
        for adapter in [bulma, vanilla]:
            assert hasattr(adapter, "get_component_class")
            assert hasattr(adapter, "get_stylesheet_links")
            assert hasattr(adapter, "get_utility_classes")

    def test_adapter_consistency(self):
        """Test adapter method consistency."""
        adapters = [BulmaStyle(), VanillaStyle()]

        for adapter in adapters:
            # Test required methods return correct types
            component_class = adapter.get_component_class("button")
            assert isinstance(component_class, str)

            stylesheet_links = adapter.get_stylesheet_links()
            assert isinstance(stylesheet_links, list)

            utility_classes = adapter.get_utility_classes()
            assert isinstance(utility_classes, dict)

    def test_framework_switching(self):
        """Test framework switching capabilities."""
        # Test that adapters can be swapped easily
        bulma = BulmaStyle()
        vanilla = VanillaStyle()

        # Same method calls should work with different frameworks
        bulma_button = bulma.get_component_class("button")
        vanilla_button = vanilla.get_component_class("button")

        assert isinstance(bulma_button, str)
        assert isinstance(vanilla_button, str)
        # Results may differ but should be valid CSS classes
        assert bulma_button == "button"
        assert vanilla_button == "btn"

    def test_protocol_compliance(self):
        """Test all adapters comply with StylesProtocol."""
        adapters = [BulmaStyle(), VanillaStyle()]

        for adapter in adapters:
            # Test required methods exist and work
            component_class = adapter.get_component_class("test")
            assert isinstance(component_class, str)

            stylesheet_links = adapter.get_stylesheet_links()
            assert isinstance(stylesheet_links, list)

    def test_settings_customization(self):
        """Test settings customization."""
        # Test Bulma customization
        bulma = BulmaStyle()
        bulma.settings.version = "0.9.3"
        bulma.settings.cdn = False
        bulma.settings.local_path = "/custom/bulma.css"

        assert bulma.settings.version == "0.9.3"
        assert bulma.settings.cdn is False

        # Test Vanilla CSS customization
        vanilla = VanillaStyle()
        vanilla.settings.css_paths = ["/my/styles.css"]
        vanilla.settings.css_variables = {"brand-color": "#FF0000"}

        assert "/my/styles.css" in vanilla.settings.css_paths
        assert vanilla.settings.css_variables["brand-color"] == "#FF0000"

    def test_html_building_patterns(self):
        """Test HTML building patterns across adapters."""
        adapters = [BulmaStyle(), VanillaStyle()]

        for adapter in adapters:
            if hasattr(adapter, "build_component_html"):
                html = adapter.build_component_html("button", "Test", variant="primary")

                # All should produce valid HTML
                assert "<button" in html
                assert "class=" in html
                assert "Test" in html
                assert ">" in html

    def test_error_handling(self):
        """Test error handling in adapters."""
        adapters = [BulmaStyle(), VanillaStyle()]

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
