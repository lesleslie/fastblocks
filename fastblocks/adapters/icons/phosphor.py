"""Phosphor icons adapter for FastBlocks with multiple variants."""

from contextlib import suppress
from typing import Any
from uuid import UUID

from acb.depends import depends

from ._base import IconsBase, IconsBaseSettings


class PhosphorIconsSettings(IconsBaseSettings):
    """Settings for Phosphor icons adapter."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-9c7e-b18f-da0b-f9a0b1c2d3e4")  # Static UUID7
    MODULE_STATUS: str = "stable"

    # Phosphor configuration
    version: str = "2.0.8"
    cdn_url: str = "https://unpkg.com/@phosphor-icons/web"
    default_variant: str = "regular"  # regular, thin, light, bold, fill, duotone
    default_size: str = "1em"

    # Variant settings
    enabled_variants: list[str] = [
        "regular",
        "thin",
        "light",
        "bold",
        "fill",
        "duotone",
    ]

    # Icon mapping for common names
    icon_aliases: dict[str, str] = {
        "home": "house",
        "user": "user-circle",
        "settings": "gear",
        "search": "magnifying-glass",
        "menu": "list",
        "close": "x",
        "check": "check",
        "error": "warning-circle",
        "info": "info",
        "success": "check-circle",
        "warning": "warning",
        "edit": "pencil",
        "delete": "trash",
        "save": "floppy-disk",
        "download": "download",
        "upload": "upload",
        "email": "envelope",
        "phone": "phone",
        "location": "map-pin",
        "calendar": "calendar",
        "clock": "clock",
        "heart": "heart",
        "star": "star",
        "share": "share",
        "link": "link",
        "copy": "copy",
        "cut": "scissors",
        "paste": "clipboard",
        "undo": "arrow-counter-clockwise",
        "redo": "arrow-clockwise",
        "refresh": "arrow-clockwise",
        "logout": "sign-out",
        "login": "sign-in",
    }


class PhosphorIcons(IconsBase):
    """Phosphor icons adapter with multiple variants support."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-9c7e-b18f-da0b-f9a0b1c2d3e4")  # Static UUID7
    MODULE_STATUS: str = "stable"

    def __init__(self) -> None:
        """Initialize Phosphor adapter."""
        super().__init__()
        self.settings: PhosphorIconsSettings | None = None

        # Register with ACB dependency system
        with suppress(Exception):
            depends.set(self)

    def get_stylesheet_links(self) -> list[str]:
        """Get Phosphor icons stylesheet links."""
        if not self.settings:
            self.settings = PhosphorIconsSettings()

        links = []

        # Add CSS for each enabled variant
        for variant in self.settings.enabled_variants:
            css_url = (
                f"{self.settings.cdn_url}@{self.settings.version}/{variant}/style.css"
            )
            links.append(f'<link rel="stylesheet" href="{css_url}">')

        # Add base Phosphor CSS if needed
        base_css = self._generate_phosphor_css()
        links.append(f"<style>{base_css}</style>")

        return links

    def _generate_phosphor_css(self) -> str:
        """Generate Phosphor-specific CSS."""
        if not self.settings:
            self.settings = PhosphorIconsSettings()

        return f"""
/* Phosphor Icons Base Styles */
.ph {{
    display: inline-block;
    font-style: normal;
    font-variant: normal;
    text-rendering: auto;
    line-height: 1;
    vertical-align: -0.125em;
    font-size: {self.settings.default_size};
}}

/* Size variants */
.ph-xs {{ font-size: 0.75em; }}
.ph-sm {{ font-size: 0.875em; }}
.ph-lg {{ font-size: 1.125em; }}
.ph-xl {{ font-size: 1.25em; }}
.ph-2x {{ font-size: 2em; }}
.ph-3x {{ font-size: 3em; }}
.ph-4x {{ font-size: 4em; }}
.ph-5x {{ font-size: 5em; }}

/* Rotation and transformation */
.ph-rotate-90 {{ transform: rotate(90deg); }}
.ph-rotate-180 {{ transform: rotate(180deg); }}
.ph-rotate-270 {{ transform: rotate(270deg); }}
.ph-flip-horizontal {{ transform: scaleX(-1); }}
.ph-flip-vertical {{ transform: scaleY(-1); }}

/* Animation support */
.ph-spin {{
    animation: ph-spin 2s linear infinite;
}}

.ph-pulse {{
    animation: ph-pulse 2s ease-in-out infinite alternate;
}}

@keyframes ph-spin {{
    0% {{ transform: rotate(0deg); }}
    100% {{ transform: rotate(360deg); }}
}}

@keyframes ph-pulse {{
    from {{ opacity: 1; }}
    to {{ opacity: 0.25; }}
}}

/* Color utilities */
.ph-primary {{ color: var(--primary-color, #007bff); }}
.ph-secondary {{ color: var(--secondary-color, #6c757d); }}
.ph-success {{ color: var(--success-color, #28a745); }}
.ph-warning {{ color: var(--warning-color, #ffc107); }}
.ph-danger {{ color: var(--danger-color, #dc3545); }}
.ph-info {{ color: var(--info-color, #17a2b8); }}
.ph-light {{ color: var(--light-color, #f8f9fa); }}
.ph-dark {{ color: var(--dark-color, #343a40); }}
.ph-muted {{ color: var(--muted-color, #6c757d); }}

/* Interactive states */
.ph-interactive {{
    cursor: pointer;
    transition: all 0.2s ease;
}}

.ph-interactive:hover {{
    transform: scale(1.1);
    opacity: 0.8;
}}

/* Alignment utilities */
.ph-align-top {{ vertical-align: top; }}
.ph-align-middle {{ vertical-align: middle; }}
.ph-align-bottom {{ vertical-align: bottom; }}
.ph-align-baseline {{ vertical-align: baseline; }}
"""

    def get_icon_class(self, icon_name: str, variant: str | None = None) -> str:
        """Get Phosphor icon class with variant support."""
        if not self.settings:
            self.settings = PhosphorIconsSettings()

        # Resolve icon aliases
        if icon_name in self.settings.icon_aliases:
            icon_name = self.settings.icon_aliases[icon_name]

        # Use default variant if not specified
        if not variant:
            variant = self.settings.default_variant

        # Validate variant
        if variant not in self.settings.enabled_variants:
            variant = self.settings.default_variant

        # Build class name based on variant
        if variant == "regular":
            return f"ph ph-{icon_name}"

        return f"ph-{variant} ph-{icon_name}"

    def _apply_size_class(
        self, size: str | None, icon_class: str, attributes: dict[str, Any]
    ) -> str:
        """Apply size styling to icon class."""
        if not size:
            return icon_class

        if size in ("xs", "sm", "lg", "xl", "2x", "3x", "4x", "5x"):
            return f"{icon_class} ph-{size}"

        # Custom size via style
        attributes["style"] = f"font-size: {size}; {attributes.get('style', '')}"
        return icon_class

    def _apply_transformations(
        self, icon_class: str, attributes: dict[str, Any]
    ) -> str:
        """Apply rotation and flip transformations."""
        if "rotate" in attributes:
            rotation = attributes.pop("rotate")
            icon_class += f" ph-rotate-{rotation}"

        if "flip" in attributes:
            flip = attributes.pop("flip")
            if flip in ("horizontal", "vertical"):
                icon_class += f" ph-flip-{flip}"

        return icon_class

    def _apply_animations(self, icon_class: str, attributes: dict[str, Any]) -> str:
        """Apply animation classes."""
        if "spin" in attributes and attributes.pop("spin"):
            icon_class += " ph-spin"

        if "pulse" in attributes and attributes.pop("pulse"):
            icon_class += " ph-pulse"

        return icon_class

    def _apply_color_styling(self, icon_class: str, attributes: dict[str, Any]) -> str:
        """Apply color styling (semantic or custom)."""
        if "color" not in attributes:
            return icon_class

        color = attributes.pop("color")
        semantic_colors = (
            "primary",
            "secondary",
            "success",
            "warning",
            "danger",
            "info",
            "light",
            "dark",
            "muted",
        )

        if color in semantic_colors:
            return f"{icon_class} ph-{color}"

        # Custom color via style
        attributes["style"] = f"color: {color}; {attributes.get('style', '')}"
        return icon_class

    def _apply_interactive_and_alignment(
        self, icon_class: str, attributes: dict[str, Any]
    ) -> str:
        """Apply interactive and alignment classes."""
        if "interactive" in attributes and attributes.pop("interactive"):
            icon_class += " ph-interactive"

        if "align" in attributes:
            align = attributes.pop("align")
            if align in ("top", "middle", "bottom", "baseline"):
                icon_class += f" ph-align-{align}"

        return icon_class

    def get_icon_tag(
        self,
        icon_name: str,
        variant: str | None = None,
        size: str | None = None,
        **attributes: Any,
    ) -> str:
        """Generate Phosphor icon tag with full customization."""
        icon_class = self.get_icon_class(icon_name, variant)

        # Add custom classes first
        if "class" in attributes:
            icon_class += f" {attributes.pop('class')}"

        # Apply all styling and features
        icon_class = self._apply_size_class(size, icon_class, attributes)
        icon_class = self._apply_transformations(icon_class, attributes)
        icon_class = self._apply_animations(icon_class, attributes)
        icon_class = self._apply_color_styling(icon_class, attributes)
        icon_class = self._apply_interactive_and_alignment(icon_class, attributes)

        # Build final attributes
        attrs = {"class": icon_class} | attributes

        # Add accessibility attributes
        if "aria-label" not in attrs and "title" not in attrs:
            attrs["aria-hidden"] = "true"

        # Generate tag
        attr_string = " ".join(f'{k}="{v}"' for k, v in attrs.items())
        return f"<i {attr_string}></i>"

    def get_duotone_icon_tag(
        self,
        icon_name: str,
        primary_color: str | None = None,
        secondary_color: str | None = None,
        **attributes: Any,
    ) -> str:
        """Generate duotone Phosphor icon with custom colors."""
        # Force duotone variant
        attributes["variant"] = "duotone"

        # Handle duotone colors via CSS custom properties
        style = attributes.get("style", "")
        if primary_color:
            style += f" --ph-duotone-primary: {primary_color};"
        if secondary_color:
            style += f" --ph-duotone-secondary: {secondary_color};"

        if style:
            attributes["style"] = style

        return self.get_icon_tag(icon_name, **attributes)

    def get_icon_sprite_tag(
        self, icon_name: str, variant: str | None = None, **attributes: Any
    ) -> str:
        """Generate SVG sprite-based icon tag (alternative approach)."""
        if not self.settings:
            self.settings = PhosphorIconsSettings()

        if not variant:
            variant = self.settings.default_variant

        # Resolve icon aliases
        if icon_name in self.settings.icon_aliases:
            icon_name = self.settings.icon_aliases[icon_name]

        # Build SVG tag
        svg_class = f"ph ph-{icon_name}"
        if "class" in attributes:
            svg_class += f" {attributes.pop('class')}"

        # Default attributes for SVG
        svg_attrs = {
            "class": svg_class,
            "width": attributes.pop("width", self.settings.default_size),
            "height": attributes.pop("height", self.settings.default_size),
            "fill": "currentColor",
        } | attributes

        # Add accessibility
        if "aria-label" not in svg_attrs and "title" not in svg_attrs:
            svg_attrs["aria-hidden"] = "true"

        attr_string = " ".join(
            f'{k}="{v}"' for k, v in svg_attrs.items() if v is not None
        )

        # Use symbol reference (assumes sprite is loaded)
        symbol_id = f"ph-{variant}-{icon_name}"
        return f'<svg {attr_string}><use href="#{symbol_id}"></use></svg>'

    def get_available_icons(self) -> dict[str, list[str]]:
        """Get list of available icons by category."""
        # This would typically come from the Phosphor icon registry
        # For now, return a sample of common categories
        return {
            "general": [
                "house",
                "user-circle",
                "gear",
                "magnifying-glass",
                "list",
                "x",
                "check",
                "warning-circle",
                "info",
                "check-circle",
            ],
            "communication": [
                "envelope",
                "phone",
                "chat-circle",
                "paper-plane-right",
                "bell",
                "speaker-high",
                "microphone",
                "video-camera",
            ],
            "media": [
                "play",
                "pause",
                "stop",
                "skip-back",
                "skip-forward",
                "volume-high",
                "volume-low",
                "volume-x",
                "music-note",
            ],
            "navigation": [
                "arrow-left",
                "arrow-right",
                "arrow-up",
                "arrow-down",
                "caret-left",
                "caret-right",
                "caret-up",
                "caret-down",
            ],
            "file": [
                "file",
                "folder",
                "download",
                "upload",
                "floppy-disk",
                "file-text",
                "file-image",
                "file-video",
                "file-audio",
            ],
            "business": [
                "briefcase",
                "calendar",
                "clock",
                "chart-line",
                "currency-dollar",
                "credit-card",
                "receipt",
                "invoice",
            ],
            "social": [
                "heart",
                "star",
                "share",
                "thumbs-up",
                "thumbs-down",
                "bookmark",
                "flag",
                "gift",
                "trophy",
            ],
        }


# Template filter registration for FastBlocks
def _register_ph_basic_filters(env: Any) -> None:
    """Register basic Phosphor filters."""

    @env.filter("ph_icon")  # type: ignore[misc]
    def ph_icon_filter(
        icon_name: str,
        variant: str = "regular",
        size: str | None = None,
        **attributes: Any,
    ) -> str:
        """Template filter for Phosphor icons."""
        icons = depends.get_sync("icons")
        if isinstance(icons, PhosphorIcons):
            return icons.get_icon_tag(icon_name, variant, size, **attributes)
        return f"<!-- {icon_name} -->"

    @env.filter("ph_class")  # type: ignore[misc]
    def ph_class_filter(icon_name: str, variant: str = "regular") -> str:
        """Template filter for Phosphor icon classes."""
        icons = depends.get_sync("icons")
        if isinstance(icons, PhosphorIcons):
            return icons.get_icon_class(icon_name, variant)
        return f"ph-{icon_name}"

    @env.global_("phosphor_stylesheet_links")  # type: ignore[misc]
    def phosphor_stylesheet_links() -> str:
        """Global function for Phosphor stylesheet links."""
        icons = depends.get_sync("icons")
        if isinstance(icons, PhosphorIcons):
            return "\n".join(icons.get_stylesheet_links())
        return ""


def _register_ph_duotone_functions(env: Any) -> None:
    """Register Phosphor duotone functions."""

    @env.global_("ph_duotone")  # type: ignore[misc]
    def ph_duotone(
        icon_name: str,
        primary_color: str | None = None,
        secondary_color: str | None = None,
        **attributes: Any,
    ) -> str:
        """Generate duotone Phosphor icon."""
        icons = depends.get_sync("icons")
        if isinstance(icons, PhosphorIcons):
            return icons.get_duotone_icon_tag(
                icon_name, primary_color, secondary_color, **attributes
            )
        return f"<!-- {icon_name} duotone -->"


def _register_ph_interactive_functions(env: Any) -> None:
    """Register Phosphor interactive functions."""

    @env.global_("ph_interactive")  # type: ignore[misc]
    def ph_interactive(
        icon_name: str,
        variant: str = "regular",
        action: str | None = None,
        **attributes: Any,
    ) -> str:
        """Generate interactive Phosphor icon with action."""
        icons = depends.get_sync("icons")
        if not isinstance(icons, PhosphorIcons):
            return f"<!-- {icon_name} -->"

        attributes["interactive"] = True
        if action:
            attributes["onclick"] = action
        attributes["style"] = f"cursor: pointer; {attributes.get('style', '')}"

        return icons.get_icon_tag(icon_name, variant, **attributes)

    @env.global_("ph_button_icon")  # type: ignore[misc]
    def ph_button_icon(
        icon_name: str,
        text: str | None = None,
        variant: str = "regular",
        position: str = "left",
        **attributes: Any,
    ) -> str:
        """Generate button with Phosphor icon."""
        icons = depends.get_sync("icons")
        if not isinstance(icons, PhosphorIcons):
            return f"<button>{text or icon_name}</button>"

        icon_tag = icons.get_icon_tag(icon_name, variant, class_="ph-sm")

        if text:
            content = (
                f"{icon_tag} {text}" if position == "left" else f"{text} {icon_tag}"
            )
        else:
            content = icon_tag

        btn_class = attributes.pop("class", "btn")
        attr_string = " ".join(
            f'{k}="{v}"' for k, v in ({"class": btn_class} | attributes).items()
        )
        return f"<button {attr_string}>{content}</button>"


def register_phosphor_filters(env: Any) -> None:
    """Register Phosphor filters for Jinja2 templates."""
    _register_ph_basic_filters(env)
    _register_ph_duotone_functions(env)
    _register_ph_interactive_functions(env)


IconsSettings = PhosphorIconsSettings
Icons = PhosphorIcons

depends.set(Icons, "phosphor")

# ACB 0.19.0+ compatibility
__all__ = [
    "PhosphorIcons",
    "PhosphorIconsSettings",
    "register_phosphor_filters",
    "Icons",
    "IconsSettings",
]
