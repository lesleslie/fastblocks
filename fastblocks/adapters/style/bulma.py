"""Bulma CSS framework adapter implementation."""

from contextlib import suppress
from typing import Any
from uuid import UUID

from acb.depends import depends

from ._base import StyleBase, StyleBaseSettings


class BulmaStyleSettings(StyleBaseSettings):
    """Bulma-specific settings."""

    version: str = "0.9.4"
    cdn_url: str = "https://cdn.jsdelivr.net/npm/bulma@{version}/css/bulma.min.css"
    custom_variables: dict[str, str] = {}
    local_path: str | None = None  # For local CSS files

    def __init__(self, **data):
        """Initialize settings with support for cdn property."""
        super().__init__(**data)
        # Store cdn override if passed in, otherwise default to True
        self._cdn = data.get("cdn", True)  # Default to True as per test

    @property
    def cdn(self) -> bool:
        """Check if using CDN (True if local_path is None)."""
        return self._cdn

    @cdn.setter
    def cdn(self, value: bool) -> None:
        """Set CDN status."""
        self._cdn = value

    @property
    def components(self):
        """Return component mappings for Bulma framework."""
        # Return the same mappings as defined in BulmaStyle.COMPONENT_CLASSES
        return {
            "button": "button",
            "button_primary": "button is-primary",
            "button_secondary": "button is-light",
            "button_success": "button is-success",
            "button_danger": "button is-danger",
            "button_warning": "button is-warning",
            "button_info": "button is-info",
            "button_small": "button is-small",
            "button_medium": "button is-medium",
            "button_large": "button is-large",
            "input": "input",
            "textarea": "textarea",
            "select": "select",
            "checkbox": "checkbox",
            "radio": "radio",
            "field": "field",
            "label": "label",
            "control": "control",
            "card": "card",
            "card_header": "card-header",
            "card_content": "card-content",
            "card_footer": "card-footer",
            "hero": "hero",
            "hero_body": "hero-body",
            "section": "section",
            "container": "container",
            "columns": "columns",
            "column": "column",
            "navbar": "navbar",
            "navbar_brand": "navbar-brand",
            "navbar_menu": "navbar-menu",
            "navbar_item": "navbar-item",
            "footer": "footer",
            "modal": "modal",
            "modal_background": "modal-background",
            "modal_content": "modal-content",
            "modal_close": "modal-close",
            "notification": "notification",
            "tag": "tag",
            "title": "title",
            "subtitle": "subtitle",
        }


class BulmaStyle(StyleBase):
    """Bulma CSS framework adapter implementation."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-4f2a-7b3c-8d9e-f3b4d3c2c1a1")  # Static UUID7
    MODULE_STATUS = "stable"

    # Component class mappings for Bulma
    COMPONENT_CLASSES = {
        "button": "button",
        "button_primary": "button is-primary",
        "button_secondary": "button is-light",
        "button_success": "button is-success",
        "button_danger": "button is-danger",
        "button_warning": "button is-warning",
        "button_info": "button is-info",
        "button_small": "button is-small",
        "button_medium": "button is-medium",
        "button_large": "button is-large",
        "input": "input",
        "textarea": "textarea",
        "select": "select",
        "checkbox": "checkbox",
        "radio": "radio",
        "field": "field",
        "label": "label",
        "control": "control",
        "card": "card",
        "card_header": "card-header",
        "card_content": "card-content",
        "card_footer": "card-footer",
        "hero": "hero",
        "hero_body": "hero-body",
        "section": "section",
        "container": "container",
        "columns": "columns",
        "column": "column",
        "navbar": "navbar",
        "navbar_brand": "navbar-brand",
        "navbar_menu": "navbar-menu",
        "navbar_item": "navbar-item",
        "footer": "footer",
        "modal": "modal",
        "modal_background": "modal-background",
        "modal_content": "modal-content",
        "modal_close": "modal-close",
        "notification": "notification",
        "tag": "tag",
        "title": "title",
        "subtitle": "subtitle",
    }

    def __init__(self) -> None:
        """Initialize Bulma adapter."""
        super().__init__()
        self.settings = BulmaStyleSettings()

        # Register with ACB dependency system
        with suppress(Exception):
            depends.set(self)

    def get_stylesheet_links(self) -> list[str]:
        """Generate Bulma stylesheet link tags."""
        if self.settings.cdn and self.settings.local_path is None:
            # Use CDN
            cdn_url = self.settings.cdn_url.format(version=self.settings.version)
            return [f'<link rel="stylesheet" href="{cdn_url}">']
        elif not self.settings.cdn and self.settings.local_path:
            # Use local path
            return [f'<link rel="stylesheet" href="{self.settings.local_path}">']
        else:
            # Fallback to CDN
            cdn_url = self.settings.cdn_url.format(version=self.settings.version)
            return [f'<link rel="stylesheet" href="{cdn_url}">']

    def get_component_class(self, component: str) -> str:
        """Get Bulma-specific class names for components."""
        return self.COMPONENT_CLASSES.get(component, component)

    def get_utility_classes(self) -> dict[str, str]:
        """Get common Bulma utility classes."""
        return {
            "primary": "is-primary",
            "secondary": "is-secondary",  # This might not be standard Bulma, but we'll include it
            "success": "is-success",
            "danger": "is-danger",
            "warning": "is-warning",
            "info": "is-info",
            "light": "is-light",
            "dark": "is-dark",
            "small": "is-small",
            "medium": "is-medium",
            "large": "is-large",
            # Responsive utilities
            "mobile": "is-hidden-tablet-only",
            "tablet": "is-hidden-mobile",
            "desktop": "is-hidden-widescreen-only",
            "widescreen": "is-hidden-fullhd-only",
            "fullhd": "is-hidden-touch",
            "text_center": "has-text-centered",
            "text_left": "has-text-left",
            "text_right": "has-text-right",
            "text_weight_bold": "has-text-weight-bold",
            "text_weight_light": "has-text-weight-light",
            "background_primary": "has-background-primary",
            "background_secondary": "has-background-light",
            "text_primary": "has-text-primary",
            "text_secondary": "has-text-dark",
            "margin_small": "m-2",
            "margin_medium": "m-4",
            "margin_large": "m-6",
            "padding_small": "p-2",
            "padding_medium": "p-4",
            "padding_large": "p-6",
            "is_hidden": "is-hidden",
            "is_visible": "is-visible",
            "is_responsive": "is-responsive",
        }

    def build_component_html(
        self, component: str, content: str = "", **attributes: Any
    ) -> str:
        """Build complete HTML component with Bulma classes."""
        css_class = self.get_component_class(component)

        # Handle variant attribute by converting it to appropriate Bulma class
        if "variant" in attributes:
            variant = attributes.pop("variant")
            # Add variant class to the css_class
            utility_classes = self.get_utility_classes()
            variant_class = utility_classes.get(variant, f"is-{variant}")
            css_class = f"{css_class} {variant_class}"

        # Add any additional classes
        if "class" in attributes:
            additional_class = attributes.pop("class")
            css_class = f"{css_class} {additional_class}"

        # Build attributes string
        attr_parts = [f'class="{css_class}"']
        for key, value in attributes.items():
            if key not in ("transformations"):  # Skip internal attributes
                attr_parts.append(f'{key}="{value}"')

        attrs_str = " ".join(attr_parts)

        # Determine the appropriate HTML tag based on component type
        if component.startswith("button"):
            return f"<button {attrs_str}>{content}</button>"
        elif component in ("input", "textarea", "select"):
            return f"<{component} {attrs_str}>"
        elif component == "field":
            return f"<div {attrs_str}>{content}</div>"

        return f"<div {attrs_str}>{content}</div>"


StyleSettings = BulmaStyleSettings
Style = BulmaStyle

depends.set(Style, "bulma")

__all__ = ["BulmaStyle", "Style", "StyleSettings", "BulmaStyleSettings"]
