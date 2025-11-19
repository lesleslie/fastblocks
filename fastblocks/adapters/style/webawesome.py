"""WebAwesome styles adapter for FastBlocks with integrated icon system."""

from contextlib import suppress
from typing import Any
from uuid import UUID

from acb.depends import depends

from ._base import StyleBase, StyleBaseSettings


class WebAwesomeStyleSettings(StyleBaseSettings):
    """Settings for WebAwesome styles adapter."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-7a5c-9f6d-b8e9-d7e8f9a0b1c2")  # Static UUID7
    MODULE_STATUS: str = "stable"

    # WebAwesome configuration
    version: str = "latest"
    cdn_url: str = "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free"
    include_brands: bool = True
    include_regular: bool = True
    include_solid: bool = True

    # Custom configuration
    custom_css_url: str | None = None
    primary_color: str = "#007bff"
    secondary_color: str = "#6c757d"
    success_color: str = "#28a745"
    warning_color: str = "#ffc107"
    danger_color: str = "#dc3545"
    info_color: str = "#17a2b8"

    # Layout settings
    container_max_width: str = "1200px"
    grid_columns: int = 12
    gutter_width: str = "1rem"

    # Typography
    font_family: str = (
        "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    )
    base_font_size: str = "16px"
    line_height: str = "1.6"


class WebAwesomeStyle(StyleBase):
    """WebAwesome styles adapter with integrated icons and components."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-7a5c-9f6d-b8e9-d7e8f9a0b1c2")  # Static UUID7
    MODULE_STATUS: str = "stable"

    def __init__(self) -> None:
        """Initialize WebAwesome adapter."""
        super().__init__()
        self.settings: WebAwesomeStyleSettings | None = None

        # Register with ACB dependency system
        with suppress(Exception):
            depends.set(self)

    def get_stylesheet_links(self) -> list[str]:
        """Get WebAwesome stylesheet links."""
        if not self.settings:
            self.settings = WebAwesomeStyleSettings()

        links = []

        # FontAwesome CSS (for icon integration)
        if self.settings.include_solid:
            links.extend(
                (
                    f'<link rel="stylesheet" href="{self.settings.cdn_url}@{self.settings.version}/css/fontawesome.min.css">',
                    f'<link rel="stylesheet" href="{self.settings.cdn_url}@{self.settings.version}/css/solid.min.css">',
                )
            )

        if self.settings.include_regular:
            links.append(
                f'<link rel="stylesheet" href="{self.settings.cdn_url}@{self.settings.version}/css/regular.min.css">'
            )

        if self.settings.include_brands:
            links.append(
                f'<link rel="stylesheet" href="{self.settings.cdn_url}@{self.settings.version}/css/brands.min.css">'
            )

        # Custom WebAwesome CSS
        if self.settings.custom_css_url:
            links.append(
                f'<link rel="stylesheet" href="{self.settings.custom_css_url}">'
            )

        # Generate inline CSS for WebAwesome system
        inline_css = self._generate_webawesome_css()
        links.append(f"<style>{inline_css}</style>")

        return links

    def _generate_webawesome_css(self) -> str:
        """Generate WebAwesome CSS framework."""
        if not self.settings:
            self.settings = WebAwesomeStyleSettings()

        css = f"""
/* WebAwesome CSS Framework for FastBlocks */
:root {{
    --wa-primary: {self.settings.primary_color};
    --wa-secondary: {self.settings.secondary_color};
    --wa-success: {self.settings.success_color};
    --wa-warning: {self.settings.warning_color};
    --wa-danger: {self.settings.danger_color};
    --wa-info: {self.settings.info_color};
    --wa-font-family: {self.settings.font_family};
    --wa-font-size: {self.settings.base_font_size};
    --wa-line-height: {self.settings.line_height};
    --wa-container-max-width: {self.settings.container_max_width};
    --wa-gutter: {self.settings.gutter_width};
}}

/* Reset and Base */
*, *::before, *::after {{
    box-sizing: border-box;
}}

body {{
    font-family: var(--wa-font-family);
    font-size: var(--wa-font-size);
    line-height: var(--wa-line-height);
    margin: 0;
    padding: 0;
}}

/* Container System */
.wa-container {{
    max-width: var(--wa-container-max-width);
    margin: 0 auto;
    padding: 0 var(--wa-gutter);
}}

.wa-container-fluid {{
    width: 100%;
    padding: 0 var(--wa-gutter);
}}

/* Grid System */
.wa-row {{
    display: flex;
    flex-wrap: wrap;
    margin: 0 calc(var(--wa-gutter) / -2);
}}

.wa-col {{
    flex: 1;
    padding: 0 calc(var(--wa-gutter) / 2);
}}

/* Responsive columns */
{self._generate_grid_css()}

/* Component System */
.wa-card {{
    background: white;
    border: 1px solid #e9ecef;
    border-radius: 0.5rem;
    box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
    overflow: hidden;
}}

.wa-card-header {{
    padding: 1rem;
    background: #f8f9fa;
    border-bottom: 1px solid #e9ecef;
    font-weight: 600;
}}

.wa-card-body {{
    padding: 1rem;
}}

.wa-card-footer {{
    padding: 1rem;
    background: #f8f9fa;
    border-top: 1px solid #e9ecef;
}}

/* Button System */
.wa-btn {{
    display: inline-block;
    padding: 0.5rem 1rem;
    border: 1px solid transparent;
    border-radius: 0.375rem;
    font-weight: 500;
    text-align: center;
    text-decoration: none;
    cursor: pointer;
    transition: all 0.2s ease-in-out;
    font-family: inherit;
    font-size: 1rem;
    line-height: 1.5;
}}

.wa-btn:hover {{
    transform: translateY(-1px);
    box-shadow: 0 0.125rem 0.5rem rgba(0, 0, 0, 0.15);
}}

.wa-btn-primary {{
    background: var(--wa-primary);
    border-color: var(--wa-primary);
    color: white;
}}

.wa-btn-secondary {{
    background: var(--wa-secondary);
    border-color: var(--wa-secondary);
    color: white;
}}

.wa-btn-success {{
    background: var(--wa-success);
    border-color: var(--wa-success);
    color: white;
}}

.wa-btn-warning {{
    background: var(--wa-warning);
    border-color: var(--wa-warning);
    color: #212529;
}}

.wa-btn-danger {{
    background: var(--wa-danger);
    border-color: var(--wa-danger);
    color: white;
}}

.wa-btn-info {{
    background: var(--wa-info);
    border-color: var(--wa-info);
    color: white;
}}

/* Form Controls */
.wa-form-group {{
    margin-bottom: 1rem;
}}

.wa-form-label {{
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: #495057;
}}

.wa-form-control {{
    display: block;
    width: 100%;
    padding: 0.5rem 0.75rem;
    font-size: 1rem;
    line-height: 1.5;
    color: #495057;
    background: white;
    border: 1px solid #ced4da;
    border-radius: 0.375rem;
    transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
}}

.wa-form-control:focus {{
    border-color: var(--wa-primary);
    outline: 0;
    box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}}

/* Alert System */
.wa-alert {{
    padding: 1rem;
    margin-bottom: 1rem;
    border: 1px solid transparent;
    border-radius: 0.375rem;
}}

.wa-alert-primary {{
    color: #084298;
    background: #cfe2ff;
    border-color: #b6d4fe;
}}

.wa-alert-success {{
    color: #0f5132;
    background: #d1e7dd;
    border-color: #badbcc;
}}

.wa-alert-warning {{
    color: #664d03;
    background: #fff3cd;
    border-color: #ffecb5;
}}

.wa-alert-danger {{
    color: #842029;
    background: #f8d7da;
    border-color: #f5c2c7;
}}

/* Navigation */
.wa-navbar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem var(--wa-gutter);
    background: white;
    border-bottom: 1px solid #e9ecef;
}}

.wa-navbar-brand {{
    font-size: 1.25rem;
    font-weight: 600;
    text-decoration: none;
    color: var(--wa-primary);
}}

.wa-navbar-nav {{
    display: flex;
    list-style: none;
    margin: 0;
    padding: 0;
    gap: 1rem;
}}

.wa-navbar-link {{
    text-decoration: none;
    color: #495057;
    transition: color 0.2s;
}}

.wa-navbar-link:hover {{
    color: var(--wa-primary);
}}

/* Icon Integration */
.wa-icon {{
    display: inline-block;
    width: 1em;
    height: 1em;
    vertical-align: -0.125em;
}}

.wa-icon-sm {{
    font-size: 0.875rem;
}}

.wa-icon-lg {{
    font-size: 1.125rem;
}}

.wa-icon-xl {{
    font-size: 1.5rem;
}}

.wa-icon-2x {{
    font-size: 2rem;
}}

/* Utility Classes */
.wa-text-center {{ text-align: center; }}
.wa-text-left {{ text-align: left; }}
.wa-text-right {{ text-align: right; }}

.wa-d-block {{ display: block; }}
.wa-d-inline {{ display: inline; }}
.wa-d-inline-block {{ display: inline-block; }}
.wa-d-flex {{ display: flex; }}
.wa-d-none {{ display: none; }}

.wa-mt-0 {{ margin-top: 0; }}
.wa-mt-1 {{ margin-top: 0.25rem; }}
.wa-mt-2 {{ margin-top: 0.5rem; }}
.wa-mt-3 {{ margin-top: 1rem; }}
.wa-mt-4 {{ margin-top: 1.5rem; }}
.wa-mt-5 {{ margin-top: 3rem; }}

.wa-mb-0 {{ margin-bottom: 0; }}
.wa-mb-1 {{ margin-bottom: 0.25rem; }}
.wa-mb-2 {{ margin-bottom: 0.5rem; }}
.wa-mb-3 {{ margin-bottom: 1rem; }}
.wa-mb-4 {{ margin-bottom: 1.5rem; }}
.wa-mb-5 {{ margin-bottom: 3rem; }}

.wa-p-0 {{ padding: 0; }}
.wa-p-1 {{ padding: 0.25rem; }}
.wa-p-2 {{ padding: 0.5rem; }}
.wa-p-3 {{ padding: 1rem; }}
.wa-p-4 {{ padding: 1.5rem; }}
.wa-p-5 {{ padding: 3rem; }}

/* Responsive Design */
@media (max-width: 768px) {{
    .wa-container {{
        padding: 0 0.5rem;
    }}

    .wa-btn {{
        width: 100%;
        margin-bottom: 0.5rem;
    }}

    .wa-navbar {{
        flex-direction: column;
        gap: 1rem;
    }}
}}
"""
        return css

    def _generate_grid_css(self) -> str:
        """Generate responsive grid CSS."""
        if not self.settings:
            self.settings = WebAwesomeStyleSettings()

        css = ""
        breakpoints = {
            "sm": "576px",
            "md": "768px",
            "lg": "992px",
            "xl": "1200px",
        }

        for _breakpoint, width in breakpoints.items():
            css += f"\n@media (min-width: {width}) {{\n"

            for i in range(1, self.settings.grid_columns + 1):
                percentage = (i / self.settings.grid_columns) * 100
                css += (
                    f"  .wa-col-{_breakpoint}-{i} {{ flex: 0 0 {percentage:.4f}%; "
                    f"max-width: {percentage:.4f}%; }}\n"
                )

            css += "}\n"

        # Default columns
        for i in range(1, self.settings.grid_columns + 1):
            percentage = (i / self.settings.grid_columns) * 100
            css += f".wa-col-{i} {{ flex: 0 0 {percentage:.4f}%; max-width: {percentage:.4f}%; }}\n"

        return css

    def get_component_class(self, component: str) -> str:
        """Get WebAwesome-specific classes."""
        class_map = {
            # Layout
            "container": "wa-container",
            "container-fluid": "wa-container-fluid",
            "row": "wa-row",
            "col": "wa-col",
            # Components
            "card": "wa-card",
            "card-header": "wa-card-header",
            "card-body": "wa-card-body",
            "card-footer": "wa-card-footer",
            # Buttons
            "button": "wa-btn wa-btn-primary",
            "btn": "wa-btn",
            "btn-primary": "wa-btn wa-btn-primary",
            "btn-secondary": "wa-btn wa-btn-secondary",
            "btn-success": "wa-btn wa-btn-success",
            "btn-warning": "wa-btn wa-btn-warning",
            "btn-danger": "wa-btn wa-btn-danger",
            "btn-info": "wa-btn wa-btn-info",
            # Forms
            "form-group": "wa-form-group",
            "form-label": "wa-form-label",
            "form-control": "wa-form-control",
            "input": "wa-form-control",
            "textarea": "wa-form-control",
            "select": "wa-form-control",
            # Alerts
            "alert": "wa-alert",
            "alert-primary": "wa-alert wa-alert-primary",
            "alert-success": "wa-alert wa-alert-success",
            "alert-warning": "wa-alert wa-alert-warning",
            "alert-danger": "wa-alert wa-alert-danger",
            # Navigation
            "navbar": "wa-navbar",
            "navbar-brand": "wa-navbar-brand",
            "navbar-nav": "wa-navbar-nav",
            "navbar-link": "wa-navbar-link",
            # Icons
            "icon": "wa-icon fas",
            "icon-sm": "wa-icon wa-icon-sm fas",
            "icon-lg": "wa-icon wa-icon-lg fas",
            "icon-xl": "wa-icon wa-icon-xl fas",
            "icon-2x": "wa-icon wa-icon-2x fas",
        }

        return class_map.get(component, f"wa-{component}")

    @staticmethod
    def get_icon_class(icon_name: str, style: str = "solid") -> str:
        """Get FontAwesome icon class integrated with WebAwesome."""
        prefix_map = {
            "solid": "fas",
            "regular": "far",
            "brands": "fab",
        }

        prefix = prefix_map.get(style, "fas")

        # Ensure icon name has fa- prefix
        if not icon_name.startswith("fa-"):
            icon_name = f"fa-{icon_name}"

        return f"wa-icon {prefix} {icon_name}"


# Template function registration for FastBlocks
def _register_wa_basic_filters(env: Any) -> None:
    """Register basic WebAwesome filters."""

    @env.global_("wa_stylesheet_links")  # type: ignore[misc]
    def wa_stylesheet_links() -> str:
        """Global function for WebAwesome stylesheet links."""
        styles = depends.get_sync("styles")
        if isinstance(styles, WebAwesomeStyle):
            return "\n".join(styles.get_stylesheet_links())
        return ""

    @env.filter("wa_class")  # type: ignore[misc]
    def wa_class_filter(component: str) -> str:
        """Filter for getting WebAwesome component classes."""
        styles = depends.get_sync("styles")
        if isinstance(styles, WebAwesomeStyle):
            return styles.get_component_class(component)
        return component

    @env.filter("wa_icon")  # type: ignore[misc]
    def wa_icon_filter(icon_name: str, style: str = "solid") -> str:
        """Filter for WebAwesome icon classes."""
        styles = depends.get_sync("styles")
        if isinstance(styles, WebAwesomeStyle):
            return styles.get_icon_class(icon_name, style)
        return f"fa-{icon_name}"


def _register_wa_button_functions(env: Any) -> None:
    """Register WebAwesome button component functions."""

    @env.global_("wa_button")  # type: ignore[misc]
    def wa_button(
        text: str, variant: str = "primary", icon: str | None = None, **attributes: Any
    ) -> str:
        """Generate WebAwesome button with optional icon."""
        styles = depends.get_sync("styles")
        if not isinstance(styles, WebAwesomeStyle):
            return f'<button class="btn">{text}</button>'

        btn_class = styles.get_component_class(f"btn-{variant}")
        if "class" in attributes:
            btn_class += f" {attributes.pop('class')}"

        content = ""
        if icon:
            content += f'<i class="{styles.get_icon_class(icon)}"></i> '
        content += text

        attr_string = " ".join(f'{k}="{v}"' for k, v in attributes.items())
        return f'<button class="{btn_class}" {attr_string}>{content}</button>'


def _register_wa_card_functions(env: Any) -> None:
    """Register WebAwesome card component functions."""

    @env.global_("wa_card")  # type: ignore[misc]
    def wa_card(
        title: str | None = None,
        content: str = "",
        footer: str | None = None,
        **attributes: Any,
    ) -> str:
        """Generate WebAwesome card component."""
        styles = depends.get_sync("styles")
        if not isinstance(styles, WebAwesomeStyle):
            return f'<div class="card">{content}</div>'

        card_class = styles.get_component_class("card")
        if "class" in attributes:
            card_class += f" {attributes.pop('class')}"

        card_content = ""
        if title:
            card_content += f'<div class="{styles.get_component_class("card-header")}">{title}</div>'
        card_content += (
            f'<div class="{styles.get_component_class("card-body")}">{content}</div>'
        )
        if footer:
            card_content += f'<div class="{styles.get_component_class("card-footer")}">{footer}</div>'

        attr_string = " ".join(f'{k}="{v}"' for k, v in attributes.items())
        return f'<div class="{card_class}" {attr_string}>{card_content}</div>'


def register_webawesome_functions(env: Any) -> None:
    """Register WebAwesome functions for Jinja2 templates."""
    _register_wa_basic_filters(env)
    _register_wa_button_functions(env)
    _register_wa_card_functions(env)


StyleSettings = WebAwesomeStyleSettings
Style = WebAwesomeStyle

depends.set(Style, "webawesome")

# ACB 0.19.0+ compatibility
__all__ = [
    "WebAwesomeStyle",
    "WebAwesomeStyleSettings",
    "register_webawesome_functions",
    "Style",
    "StyleSettings",
]
