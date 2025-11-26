"""Kelp styles adapter for FastBlocks with component system."""

from contextlib import suppress
from typing import Any
from uuid import UUID

from acb.depends import depends

from ._base import StyleBase, StyleBaseSettings


class KelpStyleSettings(StyleBaseSettings):
    """Settings for Kelp styles adapter."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-8b6d-a07e-c9fa-e8f9a0b1c2d3")  # Static UUID7
    MODULE_STATUS: str = "stable"

    # Kelp configuration
    version: str = "latest"
    cdn_url: str = "https://cdn.jsdelivr.net/npm/kelp"
    theme: str = "default"  # default, dark, ocean, forest, sunset

    # Color system
    primary_hue: int = 210  # Blue
    secondary_hue: int = 160  # Green
    accent_hue: int = 45  # Orange
    neutral_hue: int = 220  # Cool gray

    # Spacing system (rem units)
    spacing_scale: list[str] = [
        "0",
        "0.25",
        "0.5",
        "0.75",
        "1",
        "1.25",
        "1.5",
        "2",
        "2.5",
        "3",
        "4",
        "5",
        "6",
        "8",
        "10",
        "12",
        "16",
        "20",
        "24",
    ]

    # Typography
    font_family_sans: str = "Inter, system-ui, -apple-system, sans-serif"
    font_family_mono: str = "JetBrains Mono, 'Fira Code', Consolas, monospace"
    font_scale: dict[str, str] = {
        "xs": "0.75rem",
        "sm": "0.875rem",
        "base": "1rem",
        "lg": "1.125rem",
        "xl": "1.25rem",
        "2xl": "1.5rem",
        "3xl": "1.875rem",
        "4xl": "2.25rem",
        "5xl": "3rem",
        "6xl": "3.75rem",
    }

    # Border radius
    radius_scale: dict[str, str] = {
        "none": "0",
        "sm": "0.125rem",
        "base": "0.25rem",
        "md": "0.375rem",
        "lg": "0.5rem",
        "xl": "0.75rem",
        "2xl": "1rem",
        "3xl": "1.5rem",
        "full": "9999px",
    }

    # Shadow system
    enable_shadows: bool = True
    enable_animations: bool = True


class KelpStyle(StyleBase):
    """Kelp styles adapter with modern component system."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-8b6d-a07e-c9fa-e8f9a0b1c2d3")  # Static UUID7
    MODULE_STATUS: str = "stable"

    def __init__(self) -> None:
        """Initialize Kelp adapter."""
        super().__init__()
        self.settings: KelpStyleSettings | None = None

        # Register with ACB dependency system
        with suppress(Exception):
            depends.set(self)

    def get_stylesheet_links(self) -> list[str]:
        """Get Kelp stylesheet links."""
        if not self.settings:
            self.settings = KelpStyleSettings()

        links = []

        # Kelp base CSS (if available from CDN)
        # Note: Kelp might be a custom framework, so we generate it inline
        kelp_css = self._generate_kelp_css()
        links.append(f"<style>{kelp_css}</style>")

        # Inter font for better typography
        links.extend(
            (
                '<link rel="preconnect" href="https://fonts.googleapis.com">',
                '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
                '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@100;200;300;400;500;600;700;800;900&display=swap" rel="stylesheet">',
                '<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;1,100;1,200;1,300;1,400;1,500;1,600;1,700;1,800&display=swap" rel="stylesheet">',
            )
        )

        return links

    def _generate_kelp_css(self) -> str:
        """Generate Kelp CSS framework."""
        if not self.settings:
            self.settings = KelpStyleSettings()

        # Generate color variables based on HSL
        color_vars = self._generate_color_variables()
        spacing_vars = self._generate_spacing_variables()
        typography_vars = self._generate_typography_variables()
        radius_vars = self._generate_radius_variables()

        css = f"""
/* Kelp CSS Framework for FastBlocks */
{color_vars}
{spacing_vars}
{typography_vars}
{radius_vars}

/* Base Reset */
*, *::before, *::after {{
    box-sizing: border-box;
}}

* {{
    margin: 0;
    padding: 0;
}}

html {{
    scroll-behavior: smooth;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}}

body {{
    font-family: var(--kelp-font-sans);
    font-size: var(--kelp-text-base);
    line-height: 1.6;
    color: var(--kelp-gray-900);
    background-color: var(--kelp-gray-50);
    min-height: 100vh;
}}

/* Layout System */
.kelp-container {{
    width: 100%;
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 var(--kelp-space-4);
}}

.kelp-container-sm {{ max-width: 640px; }}
.kelp-container-md {{ max-width: 768px; }}
.kelp-container-lg {{ max-width: 1024px; }}
.kelp-container-xl {{ max-width: 1280px; }}
.kelp-container-2xl {{ max-width: 1536px; }}

/* Flexbox Grid */
.kelp-flex {{
    display: flex;
}}

.kelp-flex-col {{
    flex-direction: column;
}}

.kelp-flex-wrap {{
    flex-wrap: wrap;
}}

.kelp-items-center {{
    align-items: center;
}}

.kelp-items-start {{
    align-items: flex-start;
}}

.kelp-items-end {{
    align-items: flex-end;
}}

.kelp-justify-center {{
    justify-content: center;
}}

.kelp-justify-between {{
    justify-content: space-between;
}}

.kelp-justify-around {{
    justify-content: space-around;
}}

.kelp-gap-1 {{ gap: var(--kelp-space-1); }}
.kelp-gap-2 {{ gap: var(--kelp-space-2); }}
.kelp-gap-3 {{ gap: var(--kelp-space-3); }}
.kelp-gap-4 {{ gap: var(--kelp-space-4); }}
.kelp-gap-6 {{ gap: var(--kelp-space-6); }}
.kelp-gap-8 {{ gap: var(--kelp-space-8); }}

/* Grid System */
.kelp-grid {{
    display: grid;
}}

.kelp-grid-cols-1 {{ grid-template-columns: repeat(1, minmax(0, 1fr)); }}
.kelp-grid-cols-2 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
.kelp-grid-cols-3 {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
.kelp-grid-cols-4 {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
.kelp-grid-cols-6 {{ grid-template-columns: repeat(6, minmax(0, 1fr)); }}
.kelp-grid-cols-12 {{ grid-template-columns: repeat(12, minmax(0, 1fr)); }}

/* Component: Card */
.kelp-card {{
    background: white;
    border: 1px solid var(--kelp-gray-200);
    border-radius: var(--kelp-radius-lg);
    overflow: hidden;
    transition: all 0.2s ease;
}}

.kelp-card:hover {{
    box-shadow: var(--kelp-shadow-lg);
    transform: translateY(-2px);
}}

.kelp-card-header {{
    padding: var(--kelp-space-4) var(--kelp-space-6);
    border-bottom: 1px solid var(--kelp-gray-200);
    background: var(--kelp-gray-50);
}}

.kelp-card-body {{
    padding: var(--kelp-space-6);
}}

.kelp-card-footer {{
    padding: var(--kelp-space-4) var(--kelp-space-6);
    border-top: 1px solid var(--kelp-gray-200);
    background: var(--kelp-gray-50);
}}

/* Component: Button */
.kelp-btn {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--kelp-space-2);
    padding: var(--kelp-space-3) var(--kelp-space-6);
    font-family: inherit;
    font-size: var(--kelp-text-sm);
    font-weight: 500;
    line-height: 1;
    border: 1px solid transparent;
    border-radius: var(--kelp-radius-md);
    cursor: pointer;
    transition: all 0.2s ease;
    text-decoration: none;
    white-space: nowrap;
}}

.kelp-btn:focus {{
    outline: 2px solid var(--kelp-primary-500);
    outline-offset: 2px;
}}

.kelp-btn:disabled {{
    opacity: 0.6;
    cursor: not-allowed;
}}

.kelp-btn-primary {{
    background: var(--kelp-primary-600);
    border-color: var(--kelp-primary-600);
    color: white;
}}

.kelp-btn-primary:hover:not(:disabled) {{
    background: var(--kelp-primary-700);
    border-color: var(--kelp-primary-700);
    transform: translateY(-1px);
    box-shadow: var(--kelp-shadow-md);
}}

.kelp-btn-secondary {{
    background: var(--kelp-secondary-600);
    border-color: var(--kelp-secondary-600);
    color: white;
}}

.kelp-btn-secondary:hover:not(:disabled) {{
    background: var(--kelp-secondary-700);
    border-color: var(--kelp-secondary-700);
    transform: translateY(-1px);
    box-shadow: var(--kelp-shadow-md);
}}

.kelp-btn-outline {{
    background: transparent;
    border-color: var(--kelp-gray-300);
    color: var(--kelp-gray-700);
}}

.kelp-btn-outline:hover:not(:disabled) {{
    background: var(--kelp-gray-50);
    border-color: var(--kelp-gray-400);
}}

.kelp-btn-ghost {{
    background: transparent;
    border-color: transparent;
    color: var(--kelp-gray-700);
}}

.kelp-btn-ghost:hover:not(:disabled) {{
    background: var(--kelp-gray-100);
}}

/* Button Sizes */
.kelp-btn-sm {{
    padding: var(--kelp-space-2) var(--kelp-space-4);
    font-size: var(--kelp-text-xs);
}}

.kelp-btn-lg {{
    padding: var(--kelp-space-4) var(--kelp-space-8);
    font-size: var(--kelp-text-base);
}}

/* Component: Form Controls */
.kelp-form-group {{
    margin-bottom: var(--kelp-space-4);
}}

.kelp-label {{
    display: block;
    margin-bottom: var(--kelp-space-2);
    font-size: var(--kelp-text-sm);
    font-weight: 500;
    color: var(--kelp-gray-700);
}}

.kelp-input {{
    width: 100%;
    padding: var(--kelp-space-3);
    font-family: inherit;
    font-size: var(--kelp-text-sm);
    border: 1px solid var(--kelp-gray-300);
    border-radius: var(--kelp-radius-md);
    background: white;
    color: var(--kelp-gray-900);
    transition: all 0.2s ease;
}}

.kelp-input:focus {{
    outline: none;
    border-color: var(--kelp-primary-500);
    box-shadow: 0 0 0 3px var(--kelp-primary-100);
}}

.kelp-input:disabled {{
    background: var(--kelp-gray-100);
    color: var(--kelp-gray-500);
    cursor: not-allowed;
}}

.kelp-textarea {{
    resize: vertical;
    min-height: 80px;
}}

.kelp-select {{
    background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='m6 8 4 4 4-4'/%3e%3c/svg%3e");
    background-position: right 0.5rem center;
    background-repeat: no-repeat;
    background-size: 1.5em 1.5em;
    padding-right: 2.5rem;
}}

/* Component: Alert */
.kelp-alert {{
    padding: var(--kelp-space-4);
    border-radius: var(--kelp-radius-md);
    border: 1px solid;
    margin-bottom: var(--kelp-space-4);
}}

.kelp-alert-info {{
    background: var(--kelp-primary-50);
    border-color: var(--kelp-primary-200);
    color: var(--kelp-primary-800);
}}

.kelp-alert-success {{
    background: var(--kelp-secondary-50);
    border-color: var(--kelp-secondary-200);
    color: var(--kelp-secondary-800);
}}

.kelp-alert-warning {{
    background: var(--kelp-accent-50);
    border-color: var(--kelp-accent-200);
    color: var(--kelp-accent-800);
}}

.kelp-alert-error {{
    background: #fef2f2;
    border-color: #fecaca;
    color: #991b1b;
}}

/* Component: Badge */
.kelp-badge {{
    display: inline-flex;
    align-items: center;
    padding: var(--kelp-space-1) var(--kelp-space-2);
    font-size: var(--kelp-text-xs);
    font-weight: 500;
    border-radius: var(--kelp-radius-full);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}

.kelp-badge-primary {{
    background: var(--kelp-primary-100);
    color: var(--kelp-primary-800);
}}

.kelp-badge-secondary {{
    background: var(--kelp-secondary-100);
    color: var(--kelp-secondary-800);
}}

.kelp-badge-gray {{
    background: var(--kelp-gray-100);
    color: var(--kelp-gray-800);
}}

/* Utility Classes */
{self._generate_utility_classes()}

/* Responsive Design */
{self._generate_responsive_classes()}

/* Animation System */
{self._generate_animations()}
"""
        return css

    def _generate_color_variables(self) -> str:
        """Generate CSS color variables based on HSL."""
        if not self.settings:
            self.settings = KelpStyleSettings()

        def hsl_colors(hue: int, prefix: str) -> str:
            """Generate HSL color scale."""
            return f"""
    --kelp-{prefix}-50: hsl({hue}, 100%, 97%);
    --kelp-{prefix}-100: hsl({hue}, 100%, 94%);
    --kelp-{prefix}-200: hsl({hue}, 100%, 87%);
    --kelp-{prefix}-300: hsl({hue}, 100%, 80%);
    --kelp-{prefix}-400: hsl({hue}, 100%, 66%);
    --kelp-{prefix}-500: hsl({hue}, 100%, 50%);
    --kelp-{prefix}-600: hsl({hue}, 100%, 45%);
    --kelp-{prefix}-700: hsl({hue}, 100%, 35%);
    --kelp-{prefix}-800: hsl({hue}, 100%, 25%);
    --kelp-{prefix}-900: hsl({hue}, 100%, 15%);"""

        return f"""
:root {{
    /* Color System */
    {hsl_colors(self.settings.primary_hue, "primary")}
    {hsl_colors(self.settings.secondary_hue, "secondary")}
    {hsl_colors(self.settings.accent_hue, "accent")}

    /* Neutral Colors */
    --kelp-gray-50: hsl({self.settings.neutral_hue}, 20%, 98%);
    --kelp-gray-100: hsl({self.settings.neutral_hue}, 20%, 95%);
    --kelp-gray-200: hsl({self.settings.neutral_hue}, 15%, 89%);
    --kelp-gray-300: hsl({self.settings.neutral_hue}, 10%, 78%);
    --kelp-gray-400: hsl({self.settings.neutral_hue}, 8%, 56%);
    --kelp-gray-500: hsl({self.settings.neutral_hue}, 6%, 45%);
    --kelp-gray-600: hsl({self.settings.neutral_hue}, 5%, 35%);
    --kelp-gray-700: hsl({self.settings.neutral_hue}, 5%, 25%);
    --kelp-gray-800: hsl({self.settings.neutral_hue}, 5%, 15%);
    --kelp-gray-900: hsl({self.settings.neutral_hue}, 5%, 9%);

    /* Shadow System */
    --kelp-shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
    --kelp-shadow-base: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
    --kelp-shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
    --kelp-shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
    --kelp-shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
}}"""

    def _generate_spacing_variables(self) -> str:
        """Generate spacing variables."""
        if not self.settings:
            self.settings = KelpStyleSettings()

        vars_css = ""
        for i, value in enumerate(self.settings.spacing_scale):
            vars_css += f"    --kelp-space-{i}: {value}rem;\n"

        return f"""
    /* Spacing System */
{vars_css}"""

    def _generate_typography_variables(self) -> str:
        """Generate typography variables."""
        if not self.settings:
            self.settings = KelpStyleSettings()

        font_vars = f"""
    /* Typography System */
    --kelp-font-sans: {self.settings.font_family_sans};
    --kelp-font-mono: {self.settings.font_family_mono};
"""

        for name, size in self.settings.font_scale.items():
            font_vars += f"    --kelp-text-{name}: {size};\n"

        return font_vars

    def _generate_radius_variables(self) -> str:
        """Generate border radius variables."""
        if not self.settings:
            self.settings = KelpStyleSettings()

        radius_vars = "    /* Border Radius System */\n"
        for name, value in self.settings.radius_scale.items():
            radius_vars += f"    --kelp-radius-{name}: {value};\n"

        return radius_vars

    @staticmethod
    def _generate_utility_classes() -> str:
        """Generate utility classes."""
        return """
/* Text Utilities */
.kelp-text-left { text-align: left; }
.kelp-text-center { text-align: center; }
.kelp-text-right { text-align: right; }
.kelp-text-justify { text-align: justify; }

.kelp-font-sans { font-family: var(--kelp-font-sans); }
.kelp-font-mono { font-family: var(--kelp-font-mono); }

.kelp-text-xs { font-size: var(--kelp-text-xs); }
.kelp-text-sm { font-size: var(--kelp-text-sm); }
.kelp-text-base { font-size: var(--kelp-text-base); }
.kelp-text-lg { font-size: var(--kelp-text-lg); }
.kelp-text-xl { font-size: var(--kelp-text-xl); }
.kelp-text-2xl { font-size: var(--kelp-text-2xl); }
.kelp-text-3xl { font-size: var(--kelp-text-3xl); }

.kelp-font-light { font-weight: 300; }
.kelp-font-normal { font-weight: 400; }
.kelp-font-medium { font-weight: 500; }
.kelp-font-semibold { font-weight: 600; }
.kelp-font-bold { font-weight: 700; }

/* Display Utilities */
.kelp-block { display: block; }
.kelp-inline { display: inline; }
.kelp-inline-block { display: inline-block; }
.kelp-hidden { display: none; }

/* Spacing Utilities */
.kelp-m-0 { margin: var(--kelp-space-0); }
.kelp-m-1 { margin: var(--kelp-space-1); }
.kelp-m-2 { margin: var(--kelp-space-2); }
.kelp-m-3 { margin: var(--kelp-space-3); }
.kelp-m-4 { margin: var(--kelp-space-4); }
.kelp-m-6 { margin: var(--kelp-space-6); }
.kelp-m-8 { margin: var(--kelp-space-8); }

.kelp-p-0 { padding: var(--kelp-space-0); }
.kelp-p-1 { padding: var(--kelp-space-1); }
.kelp-p-2 { padding: var(--kelp-space-2); }
.kelp-p-3 { padding: var(--kelp-space-3); }
.kelp-p-4 { padding: var(--kelp-space-4); }
.kelp-p-6 { padding: var(--kelp-space-6); }
.kelp-p-8 { padding: var(--kelp-space-8); }

/* Color Utilities */
.kelp-text-primary { color: var(--kelp-primary-600); }
.kelp-text-secondary { color: var(--kelp-secondary-600); }
.kelp-text-gray { color: var(--kelp-gray-600); }
.kelp-text-white { color: white; }

.kelp-bg-primary { background-color: var(--kelp-primary-600); }
.kelp-bg-secondary { background-color: var(--kelp-secondary-600); }
.kelp-bg-gray { background-color: var(--kelp-gray-100); }
.kelp-bg-white { background-color: white; }

/* Border Utilities */
.kelp-border { border: 1px solid var(--kelp-gray-200); }
.kelp-border-0 { border: none; }
.kelp-rounded { border-radius: var(--kelp-radius-base); }
.kelp-rounded-md { border-radius: var(--kelp-radius-md); }
.kelp-rounded-lg { border-radius: var(--kelp-radius-lg); }
.kelp-rounded-full { border-radius: var(--kelp-radius-full); }

/* Shadow Utilities */
.kelp-shadow { box-shadow: var(--kelp-shadow-base); }
.kelp-shadow-md { box-shadow: var(--kelp-shadow-md); }
.kelp-shadow-lg { box-shadow: var(--kelp-shadow-lg); }
.kelp-shadow-none { box-shadow: none; }"""

    @staticmethod
    def _generate_responsive_classes() -> str:
        """Generate responsive design classes."""
        return """
/* Responsive Design */
@media (max-width: 640px) {
    .kelp-container {
        padding: 0 var(--kelp-space-2);
    }

    .kelp-grid-cols-2 {
        grid-template-columns: repeat(1, minmax(0, 1fr));
    }

    .kelp-grid-cols-3 {
        grid-template-columns: repeat(1, minmax(0, 1fr));
    }

    .kelp-grid-cols-4 {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

@media (max-width: 768px) {
    .kelp-md\\:hidden {
        display: none;
    }

    .kelp-md\\:flex {
        display: flex;
    }

    .kelp-md\\:grid-cols-1 {
        grid-template-columns: repeat(1, minmax(0, 1fr));
    }
}"""

    def _generate_animations(self) -> str:
        """Generate animation system."""
        if not self.settings or not self.settings.enable_animations:
            return ""

        return """
/* Animation System */
@keyframes kelp-fade-in {
    from {
        opacity: 0;
        transform: translateY(0.5rem);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes kelp-slide-up {
    from {
        transform: translateY(1rem);
        opacity: 0;
    }
    to {
        transform: translateY(0);
        opacity: 1;
    }
}

@keyframes kelp-scale-in {
    from {
        transform: scale(0.95);
        opacity: 0;
    }
    to {
        transform: scale(1);
        opacity: 1;
    }
}

.kelp-animate-fade-in {
    animation: kelp-fade-in 0.3s ease-out;
}

.kelp-animate-slide-up {
    animation: kelp-slide-up 0.4s ease-out;
}

.kelp-animate-scale-in {
    animation: kelp-scale-in 0.2s ease-out;
}

.kelp-transition {
    transition: all 0.2s ease;
}

.kelp-transition-colors {
    transition: color 0.2s ease, background-color 0.2s ease, border-color 0.2s ease;
}"""

    def get_component_class(self, component: str) -> str:
        """Get Kelp-specific classes."""
        class_map = {
            # Layout
            "container": "kelp-container",
            "container-sm": "kelp-container-sm",
            "container-md": "kelp-container-md",
            "container-lg": "kelp-container-lg",
            "container-xl": "kelp-container-xl",
            "flex": "kelp-flex",
            "flex-col": "kelp-flex-col",
            "grid": "kelp-grid",
            # Components
            "card": "kelp-card",
            "card-header": "kelp-card-header",
            "card-body": "kelp-card-body",
            "card-footer": "kelp-card-footer",
            # Buttons
            "btn": "kelp-btn",
            "btn-primary": "kelp-btn kelp-btn-primary",
            "btn-secondary": "kelp-btn kelp-btn-secondary",
            "btn-outline": "kelp-btn kelp-btn-outline",
            "btn-ghost": "kelp-btn kelp-btn-ghost",
            "btn-sm": "kelp-btn kelp-btn-sm",
            "btn-lg": "kelp-btn kelp-btn-lg",
            # Forms
            "form-group": "kelp-form-group",
            "label": "kelp-label",
            "input": "kelp-input",
            "textarea": "kelp-input kelp-textarea",
            "select": "kelp-input kelp-select",
            # Alerts
            "alert": "kelp-alert",
            "alert-info": "kelp-alert kelp-alert-info",
            "alert-success": "kelp-alert kelp-alert-success",
            "alert-warning": "kelp-alert kelp-alert-warning",
            "alert-error": "kelp-alert kelp-alert-error",
            # Badges
            "badge": "kelp-badge",
            "badge-primary": "kelp-badge kelp-badge-primary",
            "badge-secondary": "kelp-badge kelp-badge-secondary",
            "badge-gray": "kelp-badge kelp-badge-gray",
        }

        return class_map.get(component, f"kelp-{component}")


# Template function registration for FastBlocks
def _determine_component_tag(component_type: str, attributes: dict[str, Any]) -> str:
    """Determine HTML tag for Kelp component type."""
    if component_type in (
        "btn",
        "btn-primary",
        "btn-secondary",
        "btn-outline",
        "btn-ghost",
    ):
        return "button"

    if component_type in ("input", "textarea", "select"):
        if component_type == "input":
            attributes.setdefault("type", "text")
            return "input"
        return "textarea" if component_type == "textarea" else component_type

    return "div"


def _build_kelp_component_html(
    tag: str,
    component_class: str,
    content: str,
    attributes: dict[str, Any],
) -> str:
    """Build Kelp component HTML."""
    attr_string = " ".join(f'{k}="{v}"' for k, v in attributes.items())

    if tag == "input":
        return f'<{tag} class="{component_class}" {attr_string}>'

    return f'<{tag} class="{component_class}" {attr_string}>{content}</{tag}>'


def register_kelp_functions(env: Any) -> None:
    """Register Kelp functions for Jinja2 templates."""

    @env.global_("kelp_stylesheet_links")  # type: ignore[misc]
    def kelp_stylesheet_links() -> str:
        """Global function for Kelp stylesheet links."""
        styles = depends.get_sync("styles")
        if isinstance(styles, KelpStyle):
            return "\n".join(styles.get_stylesheet_links())
        return ""

    @env.filter("kelp_class")  # type: ignore[misc]
    def kelp_class_filter(component: str) -> str:
        """Filter for getting Kelp component classes."""
        styles = depends.get_sync("styles")
        if isinstance(styles, KelpStyle):
            return styles.get_component_class(component)
        return component

    @env.global_("kelp_component")  # type: ignore[misc]
    def kelp_component(
        component_type: str, content: str = "", **attributes: Any
    ) -> str:
        """Generate Kelp component."""
        styles = depends.get_sync("styles")
        if not isinstance(styles, KelpStyle):
            return f"<div>{content}</div>"

        component_class = styles.get_component_class(component_type)

        # Add custom classes
        if "class" in attributes:
            component_class += f" {attributes.pop('class')}"

        # Determine tag and build HTML
        tag = _determine_component_tag(component_type, attributes)
        return _build_kelp_component_html(tag, component_class, content, attributes)


StyleSettings = KelpStyleSettings
Style = KelpStyle

depends.set(Style, "kelp")


# ACB 0.19.0+ compatibility
__all__ = [
    "KelpStyle",
    "KelpStyleSettings",
    "register_kelp_functions",
    "Style",
    "StyleSettings",
]
