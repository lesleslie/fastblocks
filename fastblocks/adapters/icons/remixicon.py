"""Remix Icon adapter for FastBlocks with extensive icon library."""

from contextlib import suppress
from typing import Any
from uuid import UUID

from acb.depends import depends

from ._base import IconsBase, IconsBaseSettings
from ._utils import (
    add_accessibility_attributes,
    build_attr_string,
    process_animations,
    process_semantic_colors,
    process_state_attributes,
    process_transformations,
)


class RemixIconSettings(IconsBaseSettings):
    """Settings for Remix Icon adapter."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-be9a-d3ab-fc2d-1b2c3d4e5f60")  # Static UUID7
    MODULE_STATUS: str = "stable"

    # Remix Icon configuration
    version: str = "4.2.0"
    cdn_url: str = "https://cdn.jsdelivr.net/npm/remixicon"
    default_variant: str = "line"  # line, fill
    default_size: str = "1em"

    # Icon variants
    enabled_variants: list[str] = ["line", "fill"]

    # Icon mapping for common names
    icon_aliases: dict[str, str] = {
        "home": "home-line",
        "user": "user-line",
        "settings": "settings-line",
        "search": "search-line",
        "menu": "menu-line",
        "close": "close-line",
        "check": "check-line",
        "error": "error-warning-line",
        "info": "information-line",
        "success": "checkbox-circle-line",
        "warning": "alert-line",
        "edit": "edit-line",
        "delete": "delete-bin-line",
        "save": "save-line",
        "download": "download-line",
        "upload": "upload-line",
        "email": "mail-line",
        "phone": "phone-line",
        "location": "map-pin-line",
        "calendar": "calendar-line",
        "clock": "time-line",
        "heart": "heart-line",
        "star": "star-line",
        "share": "share-line",
        "link": "external-link-line",
        "copy": "file-copy-line",
        "cut": "scissors-cut-line",
        "paste": "clipboard-line",
        "undo": "arrow-go-back-line",
        "redo": "arrow-go-forward-line",
        "refresh": "refresh-line",
        "logout": "logout-box-r-line",
        "login": "login-box-line",
        "plus": "add-line",
        "minus": "subtract-line",
        "eye": "eye-line",
        "eye-off": "eye-off-line",
        "lock": "lock-line",
        "unlock": "lock-unlock-line",
    }

    # Size presets
    size_presets: dict[str, str] = {
        "xs": "0.75em",
        "sm": "0.875em",
        "md": "1em",
        "lg": "1.125em",
        "xl": "1.25em",
        "2xl": "1.5em",
        "3xl": "1.875em",
        "4xl": "2.25em",
        "5xl": "3em",
    }


class RemixIcon(IconsBase):
    """Remix Icon adapter with extensive icon library."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-be9a-d3ab-fc2d-1b2c3d4e5f60")  # Static UUID7
    MODULE_STATUS: str = "stable"

    def __init__(self) -> None:
        """Initialize Remix Icon adapter."""
        super().__init__()
        self.settings: RemixIconSettings | None = None

        # Register with ACB dependency system
        with suppress(Exception):
            depends.set(self)

    def get_stylesheet_links(self) -> list[str]:
        """Get Remix Icon stylesheet links."""
        if not self.settings:
            self.settings = RemixIconSettings()

        links = []

        # Remix Icon CSS from CDN
        css_url = f"{self.settings.cdn_url}@{self.settings.version}/fonts/remixicon.css"
        links.append(f'<link rel="stylesheet" href="{css_url}">')

        # Custom Remix Icon CSS
        remix_css = self._generate_remixicon_css()
        links.append(f"<style>{remix_css}</style>")

        return links

    def _generate_remixicon_css(self) -> str:
        """Generate Remix Icon-specific CSS."""
        if not self.settings:
            self.settings = RemixIconSettings()

        return f"""
/* Remix Icon Base Styles */
.ri {{
    display: inline-block;
    font-style: normal;
    font-variant: normal;
    text-rendering: auto;
    line-height: 1;
    vertical-align: -0.125em;
    font-size: {self.settings.default_size};
}}

/* Size variants */
.ri-xs {{ font-size: 0.75em; }}
.ri-sm {{ font-size: 0.875em; }}
.ri-md {{ font-size: 1em; }}
.ri-lg {{ font-size: 1.125em; }}
.ri-xl {{ font-size: 1.25em; }}
.ri-2xl {{ font-size: 1.5em; }}
.ri-3xl {{ font-size: 1.875em; }}
.ri-4xl {{ font-size: 2.25em; }}
.ri-5xl {{ font-size: 3em; }}

/* Weight variants (for consistency with other icon sets) */
.ri-thin {{ font-weight: 100; }}
.ri-light {{ font-weight: 300; }}
.ri-regular {{ font-weight: 400; }}
.ri-medium {{ font-weight: 500; }}
.ri-bold {{ font-weight: 700; }}

/* Rotation and transformation */
.ri-rotate-90 {{ transform: rotate(90deg); }}
.ri-rotate-180 {{ transform: rotate(180deg); }}
.ri-rotate-270 {{ transform: rotate(270deg); }}
.ri-flip-horizontal {{ transform: scaleX(-1); }}
.ri-flip-vertical {{ transform: scaleY(-1); }}

/* Animation support */
.ri-spin {{
    animation: ri-spin 2s linear infinite;
}}

.ri-pulse {{
    animation: ri-pulse 2s ease-in-out infinite alternate;
}}

.ri-bounce {{
    animation: ri-bounce 1s ease-in-out infinite;
}}

.ri-shake {{
    animation: ri-shake 0.82s cubic-bezier(.36,.07,.19,.97) both;
}}

@keyframes ri-spin {{
    0% {{ transform: rotate(0deg); }}
    100% {{ transform: rotate(360deg); }}
}}

@keyframes ri-pulse {{
    from {{ opacity: 1; }}
    to {{ opacity: 0.25; }}
}}

@keyframes ri-bounce {{
    0%, 100% {{ transform: translateY(0); }}
    50% {{ transform: translateY(-25%); }}
}}

@keyframes ri-shake {{
    10%, 90% {{ transform: translate3d(-1px, 0, 0); }}
    20%, 80% {{ transform: translate3d(2px, 0, 0); }}
    30%, 50%, 70% {{ transform: translate3d(-4px, 0, 0); }}
    40%, 60% {{ transform: translate3d(4px, 0, 0); }}
}}

/* Color utilities */
.ri-primary {{ color: var(--primary-color, #007bff); }}
.ri-secondary {{ color: var(--secondary-color, #6c757d); }}
.ri-success {{ color: var(--success-color, #28a745); }}
.ri-warning {{ color: var(--warning-color, #ffc107); }}
.ri-danger {{ color: var(--danger-color, #dc3545); }}
.ri-info {{ color: var(--info-color, #17a2b8); }}
.ri-light {{ color: var(--light-color, #f8f9fa); }}
.ri-dark {{ color: var(--dark-color, #343a40); }}
.ri-muted {{ color: var(--muted-color, #6c757d); }}
.ri-white {{ color: white; }}
.ri-black {{ color: black; }}

/* Gradient colors */
.ri-gradient-primary {{
    background: linear-gradient(45deg, #007bff, #0056b3);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}

.ri-gradient-success {{
    background: linear-gradient(45deg, #28a745, #155724);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}

.ri-gradient-warning {{
    background: linear-gradient(45deg, #ffc107, #856404);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}

.ri-gradient-danger {{
    background: linear-gradient(45deg, #dc3545, #721c24);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}

/* Interactive states */
.ri-interactive {{
    cursor: pointer;
    transition: all 0.2s ease;
}}

.ri-interactive:hover {{
    transform: scale(1.1);
    opacity: 0.8;
}}

.ri-interactive:active {{
    transform: scale(0.95);
}}

/* States */
.ri-disabled {{
    opacity: 0.5;
    cursor: not-allowed;
}}

.ri-loading {{
    opacity: 0.6;
}}

/* Button integration */
.btn .ri {{
    margin-right: 0.5rem;
    vertical-align: -0.125em;
}}

.btn .ri:last-child {{
    margin-right: 0;
    margin-left: 0.5rem;
}}

.btn .ri:only-child {{
    margin: 0;
}}

.btn-sm .ri {{
    font-size: 0.875em;
}}

.btn-lg .ri {{
    font-size: 1.125em;
}}

/* Badge integration */
.badge .ri {{
    font-size: 0.875em;
    margin-right: 0.25rem;
    vertical-align: baseline;
}}

/* Navigation integration */
.nav-link .ri {{
    margin-right: 0.5rem;
    font-size: 1.125em;
}}

/* Input group integration */
.input-group-text .ri {{
    color: inherit;
}}

/* Alert integration */
.alert .ri {{
    margin-right: 0.5rem;
    font-size: 1.125em;
}}

/* Card integration */
.card-title .ri {{
    margin-right: 0.5rem;
}}

/* List group integration */
.list-group-item .ri {{
    margin-right: 0.75rem;
    color: var(--bs-text-muted, #6c757d);
}}

/* Dropdown integration */
.dropdown-item .ri {{
    margin-right: 0.5rem;
    width: 1em;
    text-align: center;
}}

/* Breadcrumb integration */
.breadcrumb-item .ri {{
    margin-right: 0.25rem;
}}

/* Responsive utilities */
@media (max-width: 576px) {{
    .ri-responsive {{
        font-size: 0.875em;
    }}
}}

@media (max-width: 768px) {{
    .ri-md-hide {{
        display: none;
    }}
}}
"""

    def get_icon_class(self, icon_name: str, variant: str | None = None) -> str:
        """Get Remix Icon class with variant support."""
        if not self.settings:
            self.settings = RemixIconSettings()

        # Resolve icon aliases
        resolved_name = icon_name
        if icon_name in self.settings.icon_aliases:
            resolved_name = self.settings.icon_aliases[icon_name]
        elif not icon_name.endswith(("-line", "-fill")):
            # Auto-append variant if not present
            if not variant:
                variant = self.settings.default_variant
            resolved_name = f"{icon_name}-{variant}"

        # Ensure proper ri- prefix
        if not resolved_name.startswith("ri-"):
            resolved_name = f"ri-{resolved_name}"

        return f"ri {resolved_name}"

    def get_icon_tag(
        self,
        icon_name: str,
        variant: str | None = None,
        size: str | None = None,
        **attributes: Any,
    ) -> str:
        """Generate Remix Icon tag with full customization."""
        icon_class = self.get_icon_class(icon_name, variant)

        # Add size class or custom size
        if size:
            if self.settings and size in self.settings.size_presets:
                icon_class += f" ri-{size}"
            else:
                attributes["style"] = (
                    f"font-size: {size}; {attributes.get('style', '')}"
                )

        # Add custom classes
        if "class" in attributes:
            icon_class += f" {attributes.pop('class')}"

        # Process attributes using shared utilities
        transform_classes, attributes = process_transformations(attributes, "ri")
        animation_classes, attributes = process_animations(
            attributes, ["spin", "pulse", "bounce", "shake"], "ri"
        )

        # Extended semantic colors including gradients
        semantic_colors = [
            "primary",
            "secondary",
            "success",
            "warning",
            "danger",
            "info",
            "light",
            "dark",
            "muted",
            "white",
            "black",
            "gradient-primary",
            "gradient-success",
            "gradient-warning",
            "gradient-danger",
        ]
        color_class, attributes = process_semantic_colors(
            attributes, semantic_colors, "ri"
        )
        state_classes, attributes = process_state_attributes(attributes, "ri")

        # Handle weight (Remix-specific feature)
        if "weight" in attributes:
            weight = attributes.pop("weight")
            if weight in ("thin", "light", "regular", "medium", "bold"):
                icon_class += f" ri-{weight}"

        # Combine all classes
        icon_class += (
            transform_classes + animation_classes + color_class + state_classes
        )

        # Build attributes and add accessibility
        attrs = {"class": icon_class} | attributes
        attrs = add_accessibility_attributes(attrs)

        # Generate tag
        attr_string = build_attr_string(attrs)
        return f"<i {attr_string}></i>"

    def get_stacked_icons(
        self,
        background_icon: str,
        foreground_icon: str,
        background_variant: str = "fill",
        foreground_variant: str = "line",
        **attributes: Any,
    ) -> str:
        """Generate stacked Remix Icons for layered effects."""
        # Background icon (larger, usually filled)
        bg_icon = self.get_icon_tag(
            background_icon, background_variant, size="lg", class_="ri-stack-background"
        )

        # Foreground icon (smaller, usually line)
        fg_icon = self.get_icon_tag(
            foreground_icon, foreground_variant, size="sm", class_="ri-stack-foreground"
        )

        # Container attributes
        container_class = "ri-stack " + attributes.pop("class", "")
        container_attrs = {"class": container_class.strip()} | attributes

        attr_string = " ".join(f'{k}="{v}"' for k, v in container_attrs.items())

        # Additional CSS for stacking (inline)
        stack_css = """
        .ri-stack {
            position: relative;
            display: inline-block;
        }
        .ri-stack .ri-stack-foreground {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
        }
        """

        return f"""
        <style>{stack_css}</style>
        <span {attr_string}>
            {bg_icon}
            {fg_icon}
        </span>
        """

    @staticmethod
    def get_available_icons() -> dict[str, list[str]]:
        """Get list of available icons by category."""
        return {
            "general": [
                "home-line",
                "user-line",
                "settings-line",
                "search-line",
                "menu-line",
                "close-line",
                "check-line",
                "add-line",
                "subtract-line",
                "more-line",
            ],
            "communication": [
                "mail-line",
                "phone-line",
                "chat-1-line",
                "message-2-line",
                "notification-line",
                "speak-line",
                "mic-line",
                "vidicon-line",
            ],
            "media": [
                "play-line",
                "pause-line",
                "stop-line",
                "skip-back-line",
                "skip-forward-line",
                "volume-up-line",
                "volume-down-line",
                "volume-mute-line",
                "music-2-line",
            ],
            "navigation": [
                "arrow-left-line",
                "arrow-right-line",
                "arrow-up-line",
                "arrow-down-line",
                "arrow-left-s-line",
                "arrow-right-s-line",
                "arrow-up-s-line",
                "arrow-down-s-line",
            ],
            "file": [
                "file-line",
                "folder-line",
                "download-line",
                "upload-line",
                "save-line",
                "file-text-line",
                "image-line",
                "video-line",
            ],
            "editing": [
                "edit-line",
                "delete-bin-line",
                "file-copy-line",
                "scissors-cut-line",
                "clipboard-line",
                "eye-line",
                "eye-off-line",
                "lock-line",
            ],
            "business": [
                "briefcase-line",
                "calendar-line",
                "time-line",
                "bar-chart-line",
                "money-dollar-circle-line",
                "bank-card-line",
                "receipt-line",
                "invoice-line",
            ],
            "social": [
                "heart-line",
                "star-line",
                "share-line",
                "thumb-up-line",
                "thumb-down-line",
                "bookmark-line",
                "flag-line",
                "gift-line",
                "trophy-line",
            ],
            "weather": [
                "sun-line",
                "moon-line",
                "cloudy-line",
                "rainy-line",
                "snowy-line",
                "thunderstorms-line",
                "mist-line",
                "temp-hot-line",
            ],
            "technology": [
                "smartphone-line",
                "computer-line",
                "tv-line",
                "camera-line",
                "headphone-line",
                "keyboard-line",
                "mouse-line",
                "router-line",
            ],
            "transportation": [
                "car-line",
                "bus-line",
                "subway-line",
                "taxi-line",
                "bike-line",
                "walk-line",
                "flight-takeoff-line",
                "ship-line",
            ],
            "health": [
                "heart-pulse-line",
                "medicine-bottle-line",
                "hospital-line",
                "first-aid-kit-line",
                "capsule-line",
                "stethoscope-line",
                "thermometer-line",
                "mental-health-line",
            ],
        }


# Template filter registration for FastBlocks
def _register_ri_basic_filters(env: Any) -> None:
    """Register basic Remix Icon filters."""

    @env.filter("ri")  # type: ignore[misc]
    def ri_filter(
        icon_name: str,
        variant: str | None = None,
        size: str | None = None,
        **attributes: Any,
    ) -> str:
        """Template filter for Remix Icons."""
        icons = depends.get_sync("icons")
        if isinstance(icons, RemixIcon):
            return icons.get_icon_tag(icon_name, variant, size, **attributes)
        return f"<!-- {icon_name} -->"

    @env.filter("ri_class")  # type: ignore[misc]
    def ri_class_filter(icon_name: str, variant: str | None = None) -> str:
        """Template filter for Remix Icon classes."""
        icons = depends.get_sync("icons")
        if isinstance(icons, RemixIcon):
            return icons.get_icon_class(icon_name, variant)
        return f"ri-{icon_name}"

    @env.global_("remixicon_stylesheet_links")  # type: ignore[misc]
    def remixicon_stylesheet_links() -> str:
        """Global function for Remix Icon stylesheet links."""
        icons = depends.get_sync("icons")
        if isinstance(icons, RemixIcon):
            return "\n".join(icons.get_stylesheet_links())
        return ""


def _register_ri_advanced_functions(env: Any) -> None:
    """Register advanced Remix Icon functions."""

    @env.global_("ri_stacked")  # type: ignore[misc]
    def ri_stacked(
        background_icon: str,
        foreground_icon: str,
        background_variant: str = "fill",
        foreground_variant: str = "line",
        **attributes: Any,
    ) -> str:
        """Generate stacked Remix Icons."""
        icons = depends.get_sync("icons")
        if isinstance(icons, RemixIcon):
            return icons.get_stacked_icons(
                background_icon,
                foreground_icon,
                background_variant,
                foreground_variant,
                **attributes,
            )
        return f"<!-- {background_icon} + {foreground_icon} -->"

    @env.global_("ri_gradient")  # type: ignore[misc]
    def ri_gradient(
        icon_name: str,
        gradient_type: str = "primary",
        variant: str = "fill",
        **attributes: Any,
    ) -> str:
        """Generate gradient Remix Icon."""
        icons = depends.get_sync("icons")
        if isinstance(icons, RemixIcon):
            attributes["color"] = f"gradient-{gradient_type}"
            return icons.get_icon_tag(icon_name, variant, **attributes)
        return f"<!-- {icon_name} gradient -->"


def _register_ri_button_functions(env: Any) -> None:
    """Register Remix Icon button functions."""

    @env.global_("ri_button")  # type: ignore[misc]  # Jinja2 decorator preserves signature
    def ri_button(
        text: str,
        icon: str | None = None,
        variant: str = "line",
        icon_position: str = "left",
        **attributes: Any,
    ) -> str:
        """Generate button with Remix Icon."""
        icons = depends.get_sync("icons")
        if not isinstance(icons, RemixIcon):
            return f"<button>{text}</button>"

        btn_class = attributes.pop("class", "btn btn-primary")

        if icon:
            icon_tag = icons.get_icon_tag(icon, variant, size="sm")
            position_map = {
                "left": f"{icon_tag} {text}",
                "right": f"{text} {icon_tag}",
                "only": icon_tag,
            }
            content = position_map.get(icon_position, text)
        else:
            content = text

        attr_string = " ".join(
            f'{k}="{v}"' for k, v in ({"class": btn_class} | attributes).items()
        )
        return f"<button {attr_string}>{content}</button>"


def register_remixicon_filters(env: Any) -> None:
    """Register Remix Icon filters for Jinja2 templates."""
    _register_ri_basic_filters(env)
    _register_ri_advanced_functions(env)
    _register_ri_button_functions(env)


IconsSettings = RemixIconSettings
Icons = RemixIcon

depends.set(Icons, "remixicon")


# ACB 0.19.0+ compatibility
__all__ = [
    "RemixIcon",
    "RemixIconSettings",
    "register_remixicon_filters",
    "Icons",
    "IconsSettings",
]
