"""Heroicons adapter for FastBlocks with outline/solid variants."""

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


class HeroiconsIconsSettings(IconsBaseSettings):
    """Settings for Heroicons adapter."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-ad8f-c29a-eb1c-0a1b2c3d4e5f")  # Static UUID7
    MODULE_STATUS: str = "stable"

    # Heroicons configuration
    version: str = "2.0.18"
    cdn_url: str = "https://cdn.jsdelivr.net/npm/heroicons"
    default_variant: str = "outline"  # outline, solid, mini
    default_size: str = "24"  # 20 (mini), 24 (outline/solid)

    # Variant settings
    enabled_variants: list[str] = ["outline", "solid", "mini"]

    # Icon mapping for common names and aliases
    icon_aliases: dict[str, str] = {
        "home": "home",
        "user": "user",
        "settings": "cog-6-tooth",
        "search": "magnifying-glass",
        "menu": "bars-3",
        "close": "x-mark",
        "check": "check",
        "error": "exclamation-triangle",
        "info": "information-circle",
        "success": "check-circle",
        "warning": "exclamation-triangle",
        "edit": "pencil",
        "delete": "trash",
        "save": "document-arrow-down",
        "download": "arrow-down-tray",
        "upload": "arrow-up-tray",
        "email": "envelope",
        "phone": "phone",
        "location": "map-pin",
        "calendar": "calendar-days",
        "clock": "clock",
        "heart": "heart",
        "star": "star",
        "share": "share",
        "link": "link",
        "copy": "document-duplicate",
        "cut": "scissors",
        "paste": "clipboard",
        "undo": "arrow-uturn-left",
        "redo": "arrow-uturn-right",
        "refresh": "arrow-path",
        "logout": "arrow-right-on-rectangle",
        "login": "arrow-left-on-rectangle",
        "plus": "plus",
        "minus": "minus",
        "eye": "eye",
        "eye-off": "eye-slash",
        "lock": "lock-closed",
        "unlock": "lock-open",
    }

    # Size presets
    size_presets: dict[str, str] = {
        "xs": "16",
        "sm": "20",
        "md": "24",
        "lg": "28",
        "xl": "32",
        "2xl": "40",
        "3xl": "48",
    }


class HeroiconsIcons(IconsBase):
    """Heroicons adapter with outline/solid/mini variants."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-ad8f-c29a-eb1c-0a1b2c3d4e5f")  # Static UUID7
    MODULE_STATUS: str = "stable"

    def __init__(self) -> None:
        """Initialize Heroicons adapter."""
        super().__init__()
        self.settings: HeroiconsIconsSettings | None = None

        # Register with ACB dependency system
        with suppress(Exception):
            depends.set(self)

    def get_stylesheet_links(self) -> list[str]:
        """Get Heroicons stylesheet links."""
        if not self.settings:
            self.settings = HeroiconsIconsSettings()

        links = []

        # Heroicons base CSS
        heroicons_css = self._generate_heroicons_css()
        links.append(f"<style>{heroicons_css}</style>")

        return links

    def _generate_heroicons_css(self) -> str:
        """Generate Heroicons-specific CSS."""
        if not self.settings:
            self.settings = HeroiconsIconsSettings()

        return f"""
/* Heroicons Base Styles */
.heroicon {{
    display: inline-block;
    vertical-align: -0.125em;
    width: {self.settings.default_size}px;
    height: {self.settings.default_size}px;
    flex-shrink: 0;
}}

/* Size variants */
.heroicon-xs {{ width: 16px; height: 16px; }}
.heroicon-sm {{ width: 20px; height: 20px; }}
.heroicon-md {{ width: 24px; height: 24px; }}
.heroicon-lg {{ width: 28px; height: 28px; }}
.heroicon-xl {{ width: 32px; height: 32px; }}
.heroicon-2xl {{ width: 40px; height: 40px; }}
.heroicon-3xl {{ width: 48px; height: 48px; }}

/* Variant-specific styles */
.heroicon-outline {{
    stroke: currentColor;
    fill: none;
    stroke-width: 1.5;
}}

.heroicon-solid {{
    fill: currentColor;
}}

.heroicon-mini {{
    fill: currentColor;
    width: 20px;
    height: 20px;
}}

/* Rotation and transformation */
.heroicon-rotate-90 {{ transform: rotate(90deg); }}
.heroicon-rotate-180 {{ transform: rotate(180deg); }}
.heroicon-rotate-270 {{ transform: rotate(270deg); }}
.heroicon-flip-horizontal {{ transform: scaleX(-1); }}
.heroicon-flip-vertical {{ transform: scaleY(-1); }}

/* Animation support */
.heroicon-spin {{
    animation: heroicon-spin 2s linear infinite;
}}

.heroicon-pulse {{
    animation: heroicon-pulse 2s ease-in-out infinite alternate;
}}

.heroicon-bounce {{
    animation: heroicon-bounce 1s ease-in-out infinite;
}}

@keyframes heroicon-spin {{
    0% {{ transform: rotate(0deg); }}
    100% {{ transform: rotate(360deg); }}
}}

@keyframes heroicon-pulse {{
    from {{ opacity: 1; }}
    to {{ opacity: 0.25; }}
}}

@keyframes heroicon-bounce {{
    0%, 100% {{ transform: translateY(0); }}
    50% {{ transform: translateY(-25%); }}
}}

/* Color utilities */
.heroicon-primary {{ color: var(--primary-color, #3b82f6); }}
.heroicon-secondary {{ color: var(--secondary-color, #6b7280); }}
.heroicon-success {{ color: var(--success-color, #10b981); }}
.heroicon-warning {{ color: var(--warning-color, #f59e0b); }}
.heroicon-danger {{ color: var(--danger-color, #ef4444); }}
.heroicon-info {{ color: var(--info-color, #3b82f6); }}
.heroicon-gray {{ color: var(--gray-color, #6b7280); }}
.heroicon-white {{ color: white; }}
.heroicon-black {{ color: black; }}

/* Interactive states */
.heroicon-interactive {{
    cursor: pointer;
    transition: all 0.2s ease;
}}

.heroicon-interactive:hover {{
    transform: scale(1.1);
    opacity: 0.8;
}}

.heroicon-interactive:active {{
    transform: scale(0.95);
}}

/* States */
.heroicon-disabled {{
    opacity: 0.5;
    cursor: not-allowed;
}}

.heroicon-loading {{
    opacity: 0.6;
}}

/* Button integration */
.btn .heroicon {{
    margin-right: 0.5rem;
}}

.btn .heroicon:last-child {{
    margin-right: 0;
    margin-left: 0.5rem;
}}

.btn .heroicon:only-child {{
    margin: 0;
}}

/* Badge integration */
.badge .heroicon {{
    width: 1em;
    height: 1em;
    margin-right: 0.25rem;
}}

/* Navigation integration */
.nav-link .heroicon {{
    width: 1.25rem;
    height: 1.25rem;
    margin-right: 0.5rem;
}}
"""

    def get_icon_class(self, icon_name: str, variant: str | None = None) -> str:
        if not self.settings:
            self.settings = HeroiconsIconsSettings()

        # Resolve icon aliases
        if icon_name in self.settings.icon_aliases:
            icon_name = self.settings.icon_aliases[icon_name]

        # Use default variant if not specified
        if not variant:
            variant = self.settings.default_variant

        # Validate variant
        if variant not in self.settings.enabled_variants:
            variant = self.settings.default_variant

        return f"heroicon heroicon-{variant}"

    def _get_icon_size(self, size: str | None, variant: str) -> str:
        """Determine icon size based on input and variant."""
        if size and size in self.settings.size_presets:
            return self.settings.size_presets[size]
        elif size and size.isdigit():
            return size
        else:
            # Default size based on variant
            return "20" if variant == "mini" else self.settings.default_size

    def _build_icon_class(
        self, icon_name: str, variant: str, size: str | None, attributes: dict[str, Any]
    ) -> str:
        """Build the complete icon class string."""
        # Build base icon class
        icon_class = self.get_icon_class(icon_name, variant)

        # Add size class if using preset
        if size and size in self.settings.size_presets:
            icon_class += f" heroicon-{size}"

        # Add custom classes
        if "class" in attributes:
            icon_class += f" {attributes.pop('class')}"

        # Process attributes using shared utilities
        transform_classes, attributes = process_transformations(attributes, "heroicon")
        animation_classes, attributes = process_animations(
            attributes, ["spin", "pulse", "bounce"], "heroicon"
        )
        semantic_colors = [
            "primary",
            "secondary",
            "success",
            "warning",
            "danger",
            "info",
            "gray",
            "white",
            "black",
        ]
        color_class, attributes = process_semantic_colors(
            attributes, semantic_colors, "heroicon"
        )
        state_classes, attributes = process_state_attributes(attributes, "heroicon")

        # Combine all classes
        return icon_class + (
            transform_classes + animation_classes + color_class + state_classes
        )

    def _build_svg_attributes(
        self, icon_class: str, icon_size: str, variant: str, attributes: dict[str, Any]
    ) -> dict[str, Any]:
        """Build SVG attributes with variant-specific settings."""
        # Build SVG attributes
        svg_attrs = {
            "class": icon_class,
            "width": icon_size,
            "height": icon_size,
            "viewBox": f"0 0 {icon_size} {icon_size}",
        } | attributes

        # Add accessibility and variant-specific attributes
        svg_attrs = add_accessibility_attributes(svg_attrs)
        if variant == "outline":
            svg_attrs.setdefault("stroke-width", "1.5")
            svg_attrs.setdefault("stroke", "currentColor")
            svg_attrs.setdefault("fill", "none")
        else:
            svg_attrs.setdefault("fill", "currentColor")

        return svg_attrs

    def get_icon_tag(
        self,
        icon_name: str,
        variant: str | None = None,
        size: str | None = None,
        **attributes: Any,
    ) -> str:
        if not self.settings:
            self.settings = HeroiconsIconsSettings()

        # Resolve icon aliases
        if icon_name in self.settings.icon_aliases:
            icon_name = self.settings.icon_aliases[icon_name]

        # Use default variant if not specified
        if not variant:
            variant = self.settings.default_variant

        # Validate variant
        if variant not in self.settings.enabled_variants:
            variant = self.settings.default_variant

        # Determine size
        icon_size = self._get_icon_size(size, variant)

        # Build icon class
        icon_class = self._build_icon_class(icon_name, variant, size, attributes)

        # Build SVG attributes
        svg_attrs = self._build_svg_attributes(
            icon_class, icon_size, variant, attributes
        )

        # Generate SVG content and build tag
        svg_content = self._get_icon_svg_content(icon_name, variant)
        attr_string = build_attr_string(svg_attrs)
        return f"<svg {attr_string}>{svg_content}</svg>"

    def _get_icon_svg_content(self, icon_name: str, variant: str) -> str:
        """Get SVG content for specific icon and variant."""
        # This would typically come from the Heroicons icon registry
        # For now, return placeholder content for common icons

        # Common icon paths (simplified examples)
        icon_paths = {
            "home": {
                "outline": '<path stroke-linecap="round" stroke-linejoin="round" d="m2.25 12 8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />',
                "solid": '<path d="M11.47 3.84a.75.75 0 011.06 0l8.69 8.69a.75.75 0 101.06-1.06l-8.689-8.69a2.25 2.25 0 00-3.182 0l-8.69 8.69a.75.75 0 001.061 1.06l8.69-8.69z"/><path d="M12 5.432l8.159 8.159c.03.03.06.058.091.086v6.198c0 1.035-.84 1.875-1.875 1.875H15a.75.75 0 01-.75-.75v-4.5a.75.75 0 00-.75-.75h-3a.75.75 0 00-.75.75V21a.75.75 0 01-.75.75H5.625a1.875 1.875 0 01-1.875-1.875v-6.198a2.29 2.29 0 00.091-.086L12 5.432z"/>',
                "mini": '<path d="M9.293 2.293a1 1 0 011.414 0l7 7A1 1 0 0117 11h-1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-3a1 1 0 00-1-1H9a1 1 0 00-1 1v3a1 1 0 01-1 1H5a1 1 0 01-1-1v-6H3a1 1 0 01-.707-1.707l7-7z"/>',
            },
            "user": {
                "outline": '<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />',
                "solid": '<path fill-rule="evenodd" d="M7.5 6a4.5 4.5 0 119 0 4.5 4.5 0 01-9 0zM3.751 20.105a8.25 8.25 0 0116.498 0 .75.75 0 01-.437.695A18.683 18.683 0 0112 22.5c-2.786 0-5.433-.608-7.812-1.7a.75.75 0 01-.437-.695z" clip-rule="evenodd" />',
                "mini": '<path d="M10 8a3 3 0 100-6 3 3 0 000 6zM3.465 14.493a1.23 1.23 0 00.41 1.412A9.957 9.957 0 0010 18c2.31 0 4.438-.784 6.131-2.1.43-.333.604-.903.408-1.41a7.002 7.002 0 00-13.074.003z"/>',
            },
            "x-mark": {
                "outline": '<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />',
                "solid": '<path fill-rule="evenodd" d="M5.47 5.47a.75.75 0 011.06 0L12 10.94l5.47-5.47a.75.75 0 111.06 1.06L13.06 12l5.47 5.47a.75.75 0 11-1.06 1.06L12 13.06l-5.47 5.47a.75.75 0 01-1.06-1.06L10.94 12 5.47 6.53a.75.75 0 010-1.06z" clip-rule="evenodd" />',
                "mini": '<path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"/>',
            },
            "check": {
                "outline": '<path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />',
                "solid": '<path fill-rule="evenodd" d="M19.916 4.626a.75.75 0 01.208 1.04l-9 13.5a.75.75 0 01-1.154.114l-6-6a.75.75 0 011.06-1.06l5.353 5.353 8.493-12.739a.75.75 0 011.04-.208z" clip-rule="evenodd" />',
                "mini": '<path fill-rule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clip-rule="evenodd" />',
            },
        }

        # Return path for the requested icon and variant
        if icon_name in icon_paths and variant in icon_paths[icon_name]:
            return icon_paths[icon_name][variant]

        # Fallback for unknown icons
        return f"<!-- {icon_name} ({variant}) not found -->"

    def get_icon_sprite_url(self, variant: str = "outline") -> str:
        """Get URL for Heroicons sprite file."""
        if not self.settings:
            self.settings = HeroiconsIconsSettings()

        return f"{self.settings.cdn_url}@{self.settings.version}/{variant}.svg"

    @staticmethod
    def get_available_icons() -> dict[str, list[str]]:
        """Get list of available icons by category."""
        return {
            "general": [
                "home",
                "user",
                "cog-6-tooth",
                "magnifying-glass",
                "bars-3",
                "x-mark",
                "check",
                "plus",
                "minus",
                "ellipsis-horizontal",
            ],
            "navigation": [
                "arrow-left",
                "arrow-right",
                "arrow-up",
                "arrow-down",
                "chevron-left",
                "chevron-right",
                "chevron-up",
                "chevron-down",
                "arrow-path",
                "arrow-uturn-left",
                "arrow-uturn-right",
            ],
            "communication": [
                "envelope",
                "phone",
                "chat-bubble-left",
                "paper-airplane",
                "bell",
                "speaker-wave",
                "microphone",
                "video-camera",
            ],
            "media": [
                "play",
                "pause",
                "stop",
                "backward",
                "forward",
                "speaker-wave",
                "speaker-x-mark",
                "musical-note",
            ],
            "file": [
                "document",
                "folder",
                "arrow-down-tray",
                "arrow-up-tray",
                "document-arrow-down",
                "document-text",
                "photo",
                "film",
            ],
            "editing": [
                "pencil",
                "trash",
                "document-duplicate",
                "scissors",
                "clipboard",
                "eye",
                "eye-slash",
                "lock-closed",
                "lock-open",
            ],
            "status": [
                "check-circle",
                "x-circle",
                "exclamation-triangle",
                "information-circle",
                "question-mark-circle",
                "light-bulb",
            ],
        }


# Template filter registration for FastBlocks
def _create_hero_button(
    text: str,
    icon: str | None,
    variant: str,
    icon_position: str,
    icons: HeroiconsIcons,
    **attributes: Any,
) -> str:
    """Build button HTML with Heroicons icon."""
    btn_class = attributes.pop("class", "btn btn-primary")

    # Build button content
    if icon:
        icon_tag = icons.get_icon_tag(icon, variant, size="sm")
        if icon_position == "left":
            content = f"{icon_tag} {text}"
        elif icon_position == "right":
            content = f"{text} {icon_tag}"
        else:
            content = text
    else:
        content = text

    # Build button attributes
    btn_attrs = {"class": btn_class} | attributes
    attr_string = " ".join(f'{k}="{v}"' for k, v in btn_attrs.items())

    return f"<button {attr_string}>{content}</button>"


def _create_hero_badge(
    text: str,
    icon: str | None,
    variant: str,
    icons: HeroiconsIcons,
    **attributes: Any,
) -> str:
    """Build badge HTML with Heroicons icon."""
    badge_class = attributes.pop("class", "badge badge-primary")

    # Build badge content
    if icon:
        icon_tag = icons.get_icon_tag(icon, variant, size="xs")
        content = f"{icon_tag} {text}"
    else:
        content = text

    # Build badge attributes
    badge_attrs = {"class": badge_class} | attributes
    attr_string = " ".join(f'{k}="{v}"' for k, v in badge_attrs.items())

    return f"<span {attr_string}>{content}</span>"


def register_heroicons_filters(env: Any) -> None:
    """Register Heroicons filters for Jinja2 templates."""

    @env.filter("heroicon")  # type: ignore[misc]  # Jinja2 decorator preserves signature
    def heroicon_filter(
        icon_name: str,
        variant: str = "outline",
        size: str | None = None,
        **attributes: Any,
    ) -> str:
        """Template filter for Heroicons."""
        icons = depends.get_sync("icons")
        if isinstance(icons, HeroiconsIcons):
            return icons.get_icon_tag(icon_name, variant, size, **attributes)
        return f"<!-- {icon_name} -->"

    @env.filter("heroicon_class")  # type: ignore[misc]  # Jinja2 decorator preserves signature
    def heroicon_class_filter(icon_name: str, variant: str = "outline") -> str:
        """Template filter for Heroicons classes."""
        icons = depends.get_sync("icons")
        if isinstance(icons, HeroiconsIcons):
            return icons.get_icon_class(icon_name, variant)
        return f"heroicon-{icon_name}"

    @env.global_("heroicons_stylesheet_links")  # type: ignore[misc]  # Jinja2 decorator preserves signature
    def heroicons_stylesheet_links() -> str:
        """Global function for Heroicons stylesheet links."""
        icons = depends.get_sync("icons")
        if isinstance(icons, HeroiconsIcons):
            return "\n".join(icons.get_stylesheet_links())
        return ""

    @env.global_("hero_button")  # type: ignore[misc]  # Jinja2 decorator preserves signature
    def hero_button(
        text: str,
        icon: str | None = None,
        variant: str = "outline",
        icon_position: str = "left",
        **attributes: Any,
    ) -> str:
        """Generate button with Heroicons icon."""
        icons = depends.get_sync("icons")
        if isinstance(icons, HeroiconsIcons):
            return _create_hero_button(
                text, icon, variant, icon_position, icons, **attributes
            )
        return f"<button>{text}</button>"

    @env.global_("hero_badge")  # type: ignore[misc]  # Jinja2 decorator preserves signature
    def hero_badge(
        text: str, icon: str | None = None, variant: str = "outline", **attributes: Any
    ) -> str:
        """Generate badge with Heroicons icon."""
        icons = depends.get_sync("icons")
        if isinstance(icons, HeroiconsIcons):
            return _create_hero_badge(text, icon, variant, icons, **attributes)
        return f"<span class='badge'>{text}</span>"


IconsSettings = HeroiconsIconsSettings
Icons = HeroiconsIcons

depends.set(Icons, "heroicons")


# ACB 0.19.0+ compatibility
__all__ = [
    "HeroiconsIcons",
    "HeroiconsIconsSettings",
    "register_heroicons_filters",
    "Icons",
    "IconsSettings",
]
