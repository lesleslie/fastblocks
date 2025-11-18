"""Vanilla CSS adapter implementation for custom stylesheets."""

from contextlib import suppress
from typing import Any
from uuid import UUID

from acb.depends import depends

from ._base import StyleBase, StyleBaseSettings


class VanillaStyleSettings(StyleBaseSettings):
    """Vanilla CSS-specific settings."""

    css_paths: list[str] = ["/static/css/base.css"]
    custom_properties: dict[str, str] = {}
    css_variables: dict[str, str] = {}


class VanillaStyle(StyleBase):
    """Vanilla CSS adapter for custom stylesheets."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-4f2a-7b3c-8d9e-f3b4d3c2c1a2")  # Static UUID7
    MODULE_STATUS = "stable"

    # Default component class mappings for semantic naming
    COMPONENT_CLASSES = {
        "button": "btn",
        "button_primary": "btn btn--primary",
        "button_secondary": "btn btn--secondary",
        "button_success": "btn btn--success",
        "button_danger": "btn btn--danger",
        "button_warning": "btn btn--warning",
        "button_info": "btn btn--info",
        "button_small": "btn btn--small",
        "button_medium": "btn btn--medium",
        "button_large": "btn btn--large",
        "input": "form__input",
        "textarea": "form__textarea",
        "select": "form__select",
        "checkbox": "form__checkbox",
        "radio": "form__radio",
        "field": "form__field",
        "label": "form__label",
        "control": "form__control",
        "card": "card",
        "card_header": "card__header",
        "card_content": "card__content",
        "card_footer": "card__footer",
        "hero": "hero",
        "hero_body": "hero__body",
        "section": "section",
        "container": "container",
        "columns": "grid",
        "column": "grid__item",
        "navbar": "navbar",
        "navbar_brand": "navbar__brand",
        "navbar_menu": "navbar__menu",
        "navbar_item": "navbar__item",
        "footer": "footer",
        "modal": "modal",
        "modal_background": "modal__background",
        "modal_content": "modal__content",
        "modal_close": "modal__close",
        "notification": "notification",
        "tag": "tag",
        "title": "title",
        "subtitle": "subtitle",
    }

    def __init__(self) -> None:
        """Initialize Vanilla CSS adapter."""
        super().__init__()
        self.settings = VanillaStyleSettings()

        # Register with ACB dependency system
        with suppress(Exception):
            depends.set(self)

    def get_stylesheet_links(self) -> list[str]:
        """Generate link tags for custom CSS files."""
        return [
            f'<link rel="stylesheet" href="{css_path}">'
            for css_path in self.settings.css_paths
        ]

    def get_component_class(self, component: str) -> str:
        """Get semantic class names for components."""
        return self.COMPONENT_CLASSES.get(component, component)

    def get_css_variables(self) -> str:
        """Generate CSS custom properties (variables) style block."""
        if not self.settings.css_variables:
            return ""

        variables = [
            f"  --{prop}: {value};"
            for prop, value in self.settings.css_variables.items()
        ]

        return ":root {\n" + "\n".join(variables) + "\n}"

    @staticmethod
    def get_utility_classes() -> dict[str, str]:
        """Get semantic utility classes for common patterns."""
        return {
            "text_center": "text--center",
            "text_left": "text--left",
            "text_right": "text--right",
            "text_weight_bold": "text--bold",
            "text_weight_light": "text--light",
            "background_primary": "bg--primary",
            "background_secondary": "bg--secondary",
            "text_primary": "text--primary",
            "text_secondary": "text--secondary",
            "margin_small": "m--sm",
            "margin_medium": "m--md",
            "margin_large": "m--lg",
            "padding_small": "p--sm",
            "padding_medium": "p--md",
            "padding_large": "p--lg",
            "is_hidden": "hidden",
            "is_visible": "visible",
            "is_responsive": "responsive",
        }

    def build_component_html(
        self, component: str, content: str = "", **attributes: Any
    ) -> str:
        """Build complete HTML component with semantic classes."""
        css_class = self.get_component_class(component)

        # Add any additional classes
        if "class" in attributes:
            css_class = f"{css_class} {attributes.pop('class')}"

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

    @staticmethod
    def generate_base_css() -> str:
        """Generate a basic CSS foundation for vanilla styling."""
        return """
/* FastBlocks Vanilla CSS Base */
:root {
  --primary-color: #007bff;
  --secondary-color: #6c757d;
  --success-color: #28a745;
  --danger-color: #dc3545;
  --warning-color: #ffc107;
  --info-color: #17a2b8;
  --light-color: #f8f9fa;
  --dark-color: #343a40;
}

.btn {
  display: inline-block;
  padding: 0.375rem 0.75rem;
  margin-bottom: 0;
  font-size: 1rem;
  line-height: 1.5;
  text-align: center;
  text-decoration: none;
  vertical-align: middle;
  cursor: pointer;
  border: 1px solid transparent;
  border-radius: 0.25rem;
  transition: all 0.15s ease-in-out;
}

.btn--primary { background-color: var(--primary-color); color: white; }
.btn--secondary { background-color: var(--secondary-color); color: white; }
.btn--success { background-color: var(--success-color); color: white; }
.btn--danger { background-color: var(--danger-color); color: white; }

.form__field { margin-bottom: 1rem; }
.form__input, .form__textarea, .form__select {
  display: block;
  width: 100%;
  padding: 0.375rem 0.75rem;
  font-size: 1rem;
  line-height: 1.5;
  border: 1px solid #ced4da;
  border-radius: 0.25rem;
}

.container { max-width: 1200px; margin: 0 auto; padding: 0 15px; }
.grid { display: grid; gap: 1rem; }
.card { border: 1px solid #dee2e6; border-radius: 0.25rem; }
"""


StyleSettings = VanillaStyleSettings
Style = VanillaStyle

depends.set(Style, "vanilla")

__all__ = ["VanillaStyle", "VanillaStyleSettings", "Style", "StyleSettings"]
