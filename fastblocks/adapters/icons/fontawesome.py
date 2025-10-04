"""FontAwesome icons adapter implementation."""

from contextlib import suppress
from typing import Any
from uuid import UUID

from acb.config import Settings
from acb.depends import depends

from ._base import IconsBase


class FontAwesomeSettings(Settings):  # type: ignore[misc]
    """FontAwesome-specific settings."""

    version: str = "6.4.0"
    style: str = "solid"  # solid, regular, light, thin, brands
    cdn_url: str = (
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/{version}/css/all.min.css"
    )
    kit_url: str | None = None  # For FontAwesome kit users


class FontAwesomeAdapter(IconsBase):
    """FontAwesome icons adapter implementation."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-4f2a-7b3c-8d9e-f3b4d3c2d1a1")  # Static UUID7
    MODULE_STATUS = "stable"

    # Icon mapping for common icons across different styles
    ICON_MAPPINGS = {
        "home": "fa-house",
        "user": "fa-user",
        "users": "fa-users",
        "settings": "fa-gear",
        "edit": "fa-pen-to-square",
        "delete": "fa-trash",
        "save": "fa-floppy-disk",
        "search": "fa-magnifying-glass",
        "add": "fa-plus",
        "remove": "fa-minus",
        "check": "fa-check",
        "close": "fa-xmark",
        "arrow_up": "fa-arrow-up",
        "arrow_down": "fa-arrow-down",
        "arrow_left": "fa-arrow-left",
        "arrow_right": "fa-arrow-right",
        "chevron_up": "fa-chevron-up",
        "chevron_down": "fa-chevron-down",
        "chevron_left": "fa-chevron-left",
        "chevron_right": "fa-chevron-right",
        "heart": "fa-heart",
        "star": "fa-star",
        "bookmark": "fa-bookmark",
        "share": "fa-share",
        "download": "fa-download",
        "upload": "fa-upload",
        "file": "fa-file",
        "folder": "fa-folder",
        "image": "fa-image",
        "video": "fa-video",
        "music": "fa-music",
        "calendar": "fa-calendar",
        "clock": "fa-clock",
        "bell": "fa-bell",
        "email": "fa-envelope",
        "phone": "fa-phone",
        "location": "fa-location-dot",
        "link": "fa-link",
        "external_link": "fa-external-link",
        "info": "fa-circle-info",
        "warning": "fa-triangle-exclamation",
        "error": "fa-circle-exclamation",
        "success": "fa-circle-check",
        "menu": "fa-bars",
        "grid": "fa-grid",
        "list": "fa-list",
        "lock": "fa-lock",
        "unlock": "fa-unlock",
        "eye": "fa-eye",
        "eye_slash": "fa-eye-slash",
        "shopping_cart": "fa-cart-shopping",
        "credit_card": "fa-credit-card",
        "print": "fa-print",
        "question": "fa-circle-question",
        "help": "fa-circle-question",
    }

    # Brand icons (always use fab prefix)
    BRAND_ICONS = {
        "github": "fa-github",
        "twitter": "fa-twitter",
        "facebook": "fa-facebook",
        "instagram": "fa-instagram",
        "linkedin": "fa-linkedin",
        "youtube": "fa-youtube",
        "google": "fa-google",
        "apple": "fa-apple",
        "microsoft": "fa-microsoft",
        "amazon": "fa-amazon",
        "discord": "fa-discord",
        "slack": "fa-slack",
        "telegram": "fa-telegram",
        "whatsapp": "fa-whatsapp",
    }

    def __init__(self) -> None:
        """Initialize FontAwesome adapter."""
        super().__init__()
        self.settings = FontAwesomeSettings()

        # Register with ACB dependency system
        with suppress(Exception):
            depends.set(self)

    def get_stylesheet_links(self) -> list[str]:
        """Generate FontAwesome stylesheet link tags."""
        links = []

        # Use kit URL if provided (overrides CDN)
        if self.settings.kit_url:
            links.append(
                f'<script src="{self.settings.kit_url}" crossorigin="anonymous"></script>'
            )
        else:
            cdn_url = self.settings.cdn_url.format(version=self.settings.version)
            links.append(f'<link rel="stylesheet" href="{cdn_url}">')

        return links

    def get_icon_class(self, icon_name: str) -> str:
        """Get FontAwesome-specific class names for icons."""
        # Check if it's a brand icon
        if icon_name in self.BRAND_ICONS:
            fa_icon = self.BRAND_ICONS[icon_name]
            return f"fab {fa_icon}"

        # Check if it's a mapped icon
        if icon_name in self.ICON_MAPPINGS:
            fa_icon = self.ICON_MAPPINGS[icon_name]
        else:
            # Use icon name as-is, adding fa- prefix if not present
            fa_icon = icon_name if icon_name.startswith("fa-") else f"fa-{icon_name}"

        # Determine style prefix
        style_prefix = self._get_style_prefix(self.settings.style)
        return f"{style_prefix} {fa_icon}"

    def get_icon_tag(self, icon_name: str, **attributes: Any) -> str:
        """Generate complete icon tags with FontAwesome classes."""
        icon_class = self.get_icon_class(icon_name)

        # Add any additional classes
        if "class" in attributes:
            icon_class = f"{icon_class} {attributes.pop('class')}"

        # Build attributes string
        attr_parts = [f'class="{icon_class}"']

        # Handle common attributes
        for key, value in attributes.items():
            if key in ("id", "style", "title", "data-*"):
                attr_parts.append(f'{key}="{value}"')
            elif key.startswith("aria-"):
                attr_parts.append(f'{key}="{value}"')

        # Add accessibility attributes
        if "title" not in attributes and "aria-label" not in attributes:
            attr_parts.append(f'aria-label="{icon_name} icon"')

        attrs_str = " ".join(attr_parts)
        return f"<i {attrs_str}></i>"

    def _get_style_prefix(self, style: str) -> str:
        """Get FontAwesome style prefix."""
        style_map = {
            "solid": "fas",
            "regular": "far",
            "light": "fal",
            "thin": "fat",
            "duotone": "fad",
            "brands": "fab",
        }
        return style_map.get(style, "fas")

    def get_icon_with_text(
        self, icon_name: str, text: str, position: str = "left", **attributes: Any
    ) -> str:
        """Generate icon with text combination."""
        icon_tag = self.get_icon_tag(icon_name, **attributes)

        if position == "right":
            return f"{text} {icon_tag}"

        return f"{icon_tag} {text}"

    def get_icon_button(self, icon_name: str, **attributes: Any) -> str:
        """Generate button with icon."""
        icon_tag = self.get_icon_tag(icon_name)

        # Extract button-specific attributes
        button_class = attributes.pop("button_class", "btn")
        button_attrs = {
            k: v
            for k, v in attributes.items()
            if k in ("id", "style", "onclick", "type", "disabled")
        }

        # Build button attributes
        attr_parts = [f'class="{button_class}"']
        for key, value in button_attrs.items():
            attr_parts.append(f'{key}="{value}"')

        attrs_str = " ".join(attr_parts)
        return f"<button {attrs_str}>{icon_tag}</button>"
