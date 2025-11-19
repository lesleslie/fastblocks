"""Lucide icons adapter implementation."""

from contextlib import suppress
from typing import Any
from uuid import UUID

from acb.depends import depends

from ._base import IconsBase, IconsBaseSettings


class LucideIconsSettings(IconsBaseSettings):
    """Lucide-specific settings."""

    version: str = "0.263.1"
    cdn_url: str = "https://unpkg.com/lucide@{version}/dist/umd/lucide.js"
    css_url: str = "https://unpkg.com/lucide-static@{version}/font/lucide.css"
    use_svg: bool = True  # Use SVG icons vs icon font


class LucideIcons(IconsBase):
    """Lucide icons adapter implementation."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-4f2a-7b3c-8d9e-f3b4d3c2d1a2")  # Static UUID7
    MODULE_STATUS = "stable"

    # Icon mapping for common icons (Lucide naming)
    ICON_MAPPINGS = {
        "home": "home",
        "user": "user",
        "users": "users",
        "settings": "settings",
        "edit": "edit",
        "delete": "trash-2",
        "save": "save",
        "search": "search",
        "add": "plus",
        "remove": "minus",
        "check": "check",
        "close": "x",
        "arrow_up": "arrow-up",
        "arrow_down": "arrow-down",
        "arrow_left": "arrow-left",
        "arrow_right": "arrow-right",
        "chevron_up": "chevron-up",
        "chevron_down": "chevron-down",
        "chevron_left": "chevron-left",
        "chevron_right": "chevron-right",
        "heart": "heart",
        "star": "star",
        "bookmark": "bookmark",
        "share": "share",
        "download": "download",
        "upload": "upload",
        "file": "file",
        "folder": "folder",
        "image": "image",
        "video": "video",
        "music": "music",
        "calendar": "calendar",
        "clock": "clock",
        "bell": "bell",
        "email": "mail",
        "phone": "phone",
        "location": "map-pin",
        "link": "link",
        "external_link": "external-link",
        "info": "info",
        "warning": "alert-triangle",
        "error": "alert-circle",
        "success": "check-circle",
        "menu": "menu",
        "grid": "grid-3x3",
        "list": "list",
        "lock": "lock",
        "unlock": "unlock",
        "eye": "eye",
        "eye_slash": "eye-off",
        "shopping_cart": "shopping-cart",
        "credit_card": "credit-card",
        "print": "printer",
        "question": "help-circle",
        "help": "help-circle",
        "refresh": "refresh-cw",
        "copy": "copy",
        "cut": "scissors",
        "paste": "clipboard",
        "undo": "undo",
        "redo": "redo",
        "maximize": "maximize",
        "minimize": "minimize",
        "filter": "filter",
        "sort": "arrow-up-down",
        "play": "play",
        "pause": "pause",
        "stop": "square",
        "volume": "volume-2",
        "volume_off": "volume-x",
        "fullscreen": "maximize",
        "zoom_in": "zoom-in",
        "zoom_out": "zoom-out",
    }

    def __init__(self) -> None:
        """Initialize Lucide adapter."""
        super().__init__()
        self.settings = LucideIconsSettings()

        # Register with ACB dependency system
        with suppress(Exception):
            depends.set(self)

    def get_stylesheet_links(self) -> list[str]:
        """Generate Lucide stylesheet/script link tags."""
        links = []

        if self.settings.use_svg:
            # Use JavaScript library for SVG icons
            js_url = self.settings.cdn_url.format(version=self.settings.version)
            links.append(f'<script src="{js_url}"></script>')
        else:
            # Use icon font CSS
            css_url = self.settings.css_url.format(version=self.settings.version)
            links.append(f'<link rel="stylesheet" href="{css_url}">')

        return links

    def get_icon_class(self, icon_name: str) -> str:
        """Get Lucide-specific class names for icons."""
        # Map common names to Lucide names
        lucide_name = self.ICON_MAPPINGS.get(icon_name, icon_name)

        if self.settings.use_svg:
            # For SVG mode, return data attribute for JavaScript initialization
            return f"lucide-{lucide_name}"
        # For icon font mode
        return f"lucide lucide-{lucide_name}"

    def get_icon_tag(self, icon_name: str, **attributes: Any) -> str:
        """Generate complete icon tags with Lucide classes."""
        # Map common names to Lucide names
        lucide_name = self.ICON_MAPPINGS.get(icon_name, icon_name)

        if self.settings.use_svg:
            return self._get_svg_icon_tag(lucide_name, **attributes)

        return self._get_font_icon_tag(lucide_name, **attributes)

    @staticmethod
    def _get_svg_icon_tag(icon_name: str, **attributes: Any) -> str:
        """Generate SVG icon tag for JavaScript initialization."""
        # Build attributes string
        attr_parts = [f'data-lucide="{icon_name}"']

        # Handle size attributes
        size = attributes.pop("size", None)
        if size:
            attr_parts.extend((f'width="{size}"', f'height="{size}"'))

        # Handle other attributes
        for key, value in attributes.items():
            if key in ("class", "id", "style", "stroke-width", "color"):
                attr_parts.append(f'{key}="{value}"')
            elif key.startswith(("data-", "aria-")):
                attr_parts.append(f'{key}="{value}"')

        # Add accessibility
        if "aria-label" not in attributes:
            attr_parts.append(f'aria-label="{icon_name} icon"')

        attrs_str = " ".join(attr_parts)
        return f"<i {attrs_str}></i>"

    @staticmethod
    def _get_font_icon_tag(icon_name: str, **attributes: Any) -> str:
        """Generate font icon tag."""
        icon_class = f"lucide lucide-{icon_name}"

        # Add any additional classes
        if "class" in attributes:
            icon_class = f"{icon_class} {attributes.pop('class')}"

        # Build attributes string
        attr_parts = [f'class="{icon_class}"']

        # Handle common attributes
        for key, value in attributes.items():
            if key in ("id", "style", "title"):
                attr_parts.append(f'{key}="{value}"')
            elif key.startswith(("data-", "aria-")):
                attr_parts.append(f'{key}="{value}"')

        # Add accessibility
        if "aria-label" not in attributes:
            attr_parts.append(f'aria-label="{icon_name} icon"')

        attrs_str = " ".join(attr_parts)
        return f"<i {attrs_str}></i>"

    def get_initialization_script(self) -> str:
        """Generate JavaScript initialization script for SVG mode."""
        if not self.settings.use_svg:
            return ""

        return """
<script>
  document.addEventListener('DOMContentLoaded', function() {
    if (typeof lucide !== 'undefined') {
      lucide.createIcons();
    }
  });
</script>
"""

    def get_icon_with_text(
        self, icon_name: str, text: str, position: str = "left", **attributes: Any
    ) -> str:
        """Generate icon with text combination."""
        icon_tag = self.get_icon_tag(icon_name, **attributes)

        if position == "right":
            return f"{text} {icon_tag}"

        return f"{icon_tag} {text}"

    def get_icon_button(self, icon_name: str, **attributes: Any) -> str:
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


IconsSettings = LucideIconsSettings
Icons = LucideIcons

depends.set(Icons, "lucide")

__all__ = ["LucideIcons", "LucideIconsSettings", "IconsSettings", "Icons"]
