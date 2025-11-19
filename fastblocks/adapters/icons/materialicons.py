"""Material Icons adapter for FastBlocks with multiple themes."""

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


class MaterialIconsSettings(IconsBaseSettings):
    """Settings for Material Icons adapter."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-cf0b-e4bc-0d3e-2c3d4e5f6071")  # Static UUID7
    MODULE_STATUS: str = "stable"

    # Material Icons configuration
    version: str = "latest"
    base_url: str = "https://fonts.googleapis.com"
    default_theme: str = "filled"  # filled, outlined, round, sharp, two-tone
    default_size: str = "24px"

    # Available themes
    enabled_themes: list[str] = ["filled", "outlined", "round", "sharp", "two-tone"]

    # Icon mapping for common names
    icon_aliases: dict[str, str] = {
        "home": "home",
        "user": "person",
        "settings": "settings",
        "search": "search",
        "menu": "menu",
        "close": "close",
        "check": "check",
        "error": "error",
        "info": "info",
        "success": "check_circle",
        "warning": "warning",
        "edit": "edit",
        "delete": "delete",
        "save": "save",
        "download": "download",
        "upload": "upload",
        "email": "email",
        "phone": "phone",
        "location": "location_on",
        "calendar": "event",
        "clock": "schedule",
        "heart": "favorite",
        "star": "star",
        "share": "share",
        "link": "link",
        "copy": "content_copy",
        "cut": "content_cut",
        "paste": "content_paste",
        "undo": "undo",
        "redo": "redo",
        "refresh": "refresh",
        "logout": "logout",
        "login": "login",
        "plus": "add",
        "minus": "remove",
        "eye": "visibility",
        "eye-off": "visibility_off",
        "lock": "lock",
        "unlock": "lock_open",
        "arrow-up": "keyboard_arrow_up",
        "arrow-down": "keyboard_arrow_down",
        "arrow-left": "keyboard_arrow_left",
        "arrow-right": "keyboard_arrow_right",
    }

    # Size presets
    size_presets: dict[str, str] = {
        "xs": "16px",
        "sm": "20px",
        "md": "24px",
        "lg": "28px",
        "xl": "32px",
        "2xl": "40px",
        "3xl": "48px",
        "4xl": "56px",
        "5xl": "64px",
    }

    # Color palette
    material_colors: dict[str, str] = {
        "red": "#f44336",
        "pink": "#e91e63",
        "purple": "#9c27b0",
        "deep-purple": "#673ab7",
        "indigo": "#3f51b5",
        "blue": "#2196f3",
        "light-blue": "#03a9f4",
        "cyan": "#00bcd4",
        "teal": "#009688",
        "green": "#4caf50",
        "light-green": "#8bc34a",
        "lime": "#cddc39",
        "yellow": "#ffeb3b",
        "amber": "#ffc107",
        "orange": "#ff9800",
        "deep-orange": "#ff5722",
        "brown": "#795548",
        "grey": "#9e9e9e",
        "blue-grey": "#607d8b",
    }


class MaterialIcons(IconsBase):
    """Material Icons adapter with multiple themes and comprehensive icon set."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-cf0b-e4bc-0d3e-2c3d4e5f6071")  # Static UUID7
    MODULE_STATUS: str = "stable"

    def __init__(self) -> None:
        """Initialize Material Icons adapter."""
        super().__init__()
        self.settings: MaterialIconsSettings | None = None

        # Register with ACB dependency system
        with suppress(Exception):
            depends.set(self)

    def get_stylesheet_links(self) -> list[str]:
        """Get Material Icons stylesheet links."""
        if not self.settings:
            self.settings = MaterialIconsSettings()

        links = []

        # Material Icons CSS from Google Fonts
        for theme in self.settings.enabled_themes:
            if theme == "filled":
                # Base Material Icons (filled is default)
                css_url = f"{self.settings.base_url}/icon?family=Material+Icons"
            else:
                # Themed variants
                theme_name = theme.replace("-", "+").title()
                css_url = (
                    f"{self.settings.base_url}/icon?family=Material+Icons+{theme_name}"
                )

            links.append(f'<link rel="stylesheet" href="{css_url}">')

        # Custom Material Icons CSS
        material_css = self._generate_material_css()
        links.append(f"<style>{material_css}</style>")

        return links

    def _generate_material_css(self) -> str:
        """Generate Material Icons-specific CSS."""
        if not self.settings:
            self.settings = MaterialIconsSettings()

        return f"""
/* Material Icons Base Styles */
.material-icons {{
    font-family: 'Material Icons';
    font-weight: normal;
    font-style: normal;
    font-size: {self.settings.default_size};
    line-height: 1;
    letter-spacing: normal;
    text-transform: none;
    display: inline-block;
    white-space: nowrap;
    word-wrap: normal;
    direction: ltr;
    -webkit-font-feature-settings: 'liga';
    -webkit-font-smoothing: antialiased;
    vertical-align: -0.125em;
}}

/* Theme-specific font families */
.material-icons-outlined {{
    font-family: 'Material Icons Outlined';
}}

.material-icons-round {{
    font-family: 'Material Icons Round';
}}

.material-icons-sharp {{
    font-family: 'Material Icons Sharp';
}}

.material-icons-two-tone {{
    font-family: 'Material Icons Two Tone';
}}

/* Size variants */
.material-icons-xs {{ font-size: 16px; }}
.material-icons-sm {{ font-size: 20px; }}
.material-icons-md {{ font-size: 24px; }}
.material-icons-lg {{ font-size: 28px; }}
.material-icons-xl {{ font-size: 32px; }}
.material-icons-2xl {{ font-size: 40px; }}
.material-icons-3xl {{ font-size: 48px; }}
.material-icons-4xl {{ font-size: 56px; }}
.material-icons-5xl {{ font-size: 64px; }}

/* Density variants */
.material-icons-dense {{
    font-size: 20px;
}}

.material-icons-comfortable {{
    font-size: 24px;
}}

.material-icons-compact {{
    font-size: 18px;
}}

/* Rotation and transformation */
.material-icons-rotate-90 {{ transform: rotate(90deg); }}
.material-icons-rotate-180 {{ transform: rotate(180deg); }}
.material-icons-rotate-270 {{ transform: rotate(270deg); }}
.material-icons-flip-horizontal {{ transform: scaleX(-1); }}
.material-icons-flip-vertical {{ transform: scaleY(-1); }}

/* Animation support */
.material-icons-spin {{
    animation: material-spin 2s linear infinite;
}}

.material-icons-pulse {{
    animation: material-pulse 2s ease-in-out infinite alternate;
}}

.material-icons-bounce {{
    animation: material-bounce 1s ease-in-out infinite;
}}

.material-icons-shake {{
    animation: material-shake 0.82s cubic-bezier(.36,.07,.19,.97) both;
}}

.material-icons-flip {{
    animation: material-flip 2s linear infinite;
}}

@keyframes material-spin {{
    0% {{ transform: rotate(0deg); }}
    100% {{ transform: rotate(360deg); }}
}}

@keyframes material-pulse {{
    from {{ opacity: 1; }}
    to {{ opacity: 0.25; }}
}}

@keyframes material-bounce {{
    0%, 100% {{ transform: translateY(0); }}
    50% {{ transform: translateY(-25%); }}
}}

@keyframes material-shake {{
    10%, 90% {{ transform: translate3d(-1px, 0, 0); }}
    20%, 80% {{ transform: translate3d(2px, 0, 0); }}
    30%, 50%, 70% {{ transform: translate3d(-4px, 0, 0); }}
    40%, 60% {{ transform: translate3d(4px, 0, 0); }}
}}

@keyframes material-flip {{
    0% {{ transform: rotateY(0); }}
    50% {{ transform: rotateY(180deg); }}
    100% {{ transform: rotateY(360deg); }}
}}

/* Material Design color utilities */
{self._generate_material_color_classes()}

/* Interactive states */
.material-icons-interactive {{
    cursor: pointer;
    transition: all 0.2s ease;
    border-radius: 50%;
    padding: 4px;
}}

.material-icons-interactive:hover {{
    background-color: rgba(0, 0, 0, 0.04);
    transform: scale(1.1);
}}

.material-icons-interactive:active {{
    background-color: rgba(0, 0, 0, 0.08);
    transform: scale(0.95);
}}

/* States */
.material-icons-disabled {{
    opacity: 0.38;
    cursor: not-allowed;
}}

.material-icons-inactive {{
    opacity: 0.54;
}}

.material-icons-loading {{
    opacity: 0.6;
}}

/* Button integration */
.btn .material-icons {{
    margin-right: 8px;
    vertical-align: -0.125em;
}}

.btn .material-icons:last-child {{
    margin-right: 0;
    margin-left: 8px;
}}

.btn .material-icons:only-child {{
    margin: 0;
}}

.btn-sm .material-icons {{
    font-size: 20px;
}}

.btn-lg .material-icons {{
    font-size: 28px;
}}

/* Floating Action Button */
.fab {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 56px;
    height: 56px;
    border-radius: 50%;
    border: none;
    box-shadow: 0 3px 5px -1px rgba(0,0,0,.2), 0 6px 10px 0 rgba(0,0,0,.14), 0 1px 18px 0 rgba(0,0,0,.12);
    cursor: pointer;
    transition: all 0.3s ease;
}}

.fab:hover {{
    box-shadow: 0 5px 5px -3px rgba(0,0,0,.2), 0 8px 10px 1px rgba(0,0,0,.14), 0 3px 14px 2px rgba(0,0,0,.12);
    transform: translateY(-2px);
}}

.fab-mini {{
    width: 40px;
    height: 40px;
}}

.fab-extended {{
    width: auto;
    height: 48px;
    border-radius: 24px;
    padding: 0 16px;
}}

/* Badge integration */
.badge .material-icons {{
    font-size: 16px;
    margin-right: 4px;
    vertical-align: baseline;
}}

/* Navigation integration */
.nav-link .material-icons {{
    margin-right: 8px;
    font-size: 20px;
}}

/* List integration */
.list-group-item .material-icons {{
    margin-right: 16px;
    color: rgba(0, 0, 0, 0.54);
}}

/* Input group integration */
.input-group-text .material-icons {{
    color: rgba(0, 0, 0, 0.54);
}}

/* Alert integration */
.alert .material-icons {{
    margin-right: 8px;
    font-size: 20px;
}}

/* Card integration */
.card-title .material-icons {{
    margin-right: 8px;
}}

/* Toolbar integration */
.toolbar .material-icons {{
    color: rgba(255, 255, 255, 0.87);
}}

/* Dark theme support */
@media (prefers-color-scheme: dark) {{
    .material-icons-interactive:hover {{
        background-color: rgba(255, 255, 255, 0.08);
    }}

    .material-icons-interactive:active {{
        background-color: rgba(255, 255, 255, 0.12);
    }}

    .list-group-item .material-icons {{
        color: rgba(255, 255, 255, 0.7);
    }}

    .input-group-text .material-icons {{
        color: rgba(255, 255, 255, 0.7);
    }}
}}

/* Accessibility */
.material-icons[aria-hidden="false"] {{
    position: relative;
}}

.material-icons[aria-hidden="false"]:focus {{
    outline: 2px solid #1976d2;
    outline-offset: 2px;
}}
"""

    def _generate_material_color_classes(self) -> str:
        """Generate Material Design color classes."""
        if not self.settings:
            self.settings = MaterialIconsSettings()

        css = "/* Material Design Colors */\n"
        for name, color in self.settings.material_colors.items():
            css += f".material-icons-{name} {{ color: {color}; }}\n"

        # Add semantic colors
        css += """
.material-icons-primary { color: var(--primary-color, #1976d2); }
.material-icons-secondary { color: var(--secondary-color, #424242); }
.material-icons-success { color: var(--success-color, #4caf50); }
.material-icons-warning { color: var(--warning-color, #ff9800); }
.material-icons-danger { color: var(--danger-color, #f44336); }
.material-icons-info { color: var(--info-color, #2196f3); }
.material-icons-light { color: var(--light-color, #fafafa); }
.material-icons-dark { color: var(--dark-color, #212121); }
.material-icons-muted { color: var(--muted-color, #757575); }
"""

        return css

    def get_icon_class(self, icon_name: str, theme: str | None = None) -> str:
        """Get Material Icons class with theme support."""
        if not self.settings:
            self.settings = MaterialIconsSettings()

        # Use default theme if not specified
        if not theme:
            theme = self.settings.default_theme

        # Validate theme
        if theme not in self.settings.enabled_themes:
            theme = self.settings.default_theme

        # Build class name based on theme
        if theme == "filled":
            return "material-icons"

        return f"material-icons-{theme.replace('_', '-')}"

    def get_icon_tag(
        self,
        icon_name: str,
        **attributes: Any,
    ) -> str:
        """Generate Material Icons tag with full customization."""
        # Extract theme and size from attributes
        theme = attributes.pop("theme", None)
        size = attributes.pop("size", None)

        if not self.settings:
            self.settings = MaterialIconsSettings()

        # Resolve icon aliases
        resolved_name = icon_name
        if icon_name in self.settings.icon_aliases:
            resolved_name = self.settings.icon_aliases[icon_name]

        # Get base icon class
        icon_class = self.get_icon_class(icon_name, theme)

        # Add size class or custom size
        if size:
            if size in self.settings.size_presets:
                icon_class += f" material-icons-{size}"
            else:
                attributes["style"] = (
                    f"font-size: {size}; {attributes.get('style', '')}"
                )

        # Add custom classes
        if "class" in attributes:
            icon_class += f" {attributes.pop('class')}"

        # Process attributes using shared utilities
        transform_classes, attributes = process_transformations(
            attributes, "material-icons"
        )
        animation_classes, attributes = process_animations(
            attributes, ["spin", "pulse", "bounce", "shake", "flip"], "material-icons"
        )

        # Extended semantic colors including material design colors
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
            *list(self.settings.material_colors.keys()),
        ]
        color_class, attributes = process_semantic_colors(
            attributes, semantic_colors, "material-icons"
        )
        state_classes, attributes = process_state_attributes(
            attributes, "material-icons"
        )

        # Handle density (Material Design specific feature)
        if "density" in attributes:
            density = attributes.pop("density")
            if density in ("dense", "comfortable", "compact"):
                icon_class += f" material-icons-{density}"

        # Combine all classes
        icon_class += (
            transform_classes + animation_classes + color_class + state_classes
        )

        # Build attributes and add accessibility
        attrs = {"class": icon_class} | attributes
        attrs = add_accessibility_attributes(attrs)

        # Generate tag
        attr_string = build_attr_string(attrs)
        return f"<span {attr_string}>{resolved_name}</span>"

    def get_fab_tag(
        self,
        icon_name: str,
        variant: str = "regular",
        theme: str | None = None,
        **attributes: Any,
    ) -> str:
        """Generate Material Design Floating Action Button."""
        if not self.settings:
            self.settings = MaterialIconsSettings()

        # Resolve icon name
        resolved_name = icon_name
        if icon_name in self.settings.icon_aliases:
            resolved_name = self.settings.icon_aliases[icon_name]

        # Get icon tag
        icon_tag = self.get_icon_tag(resolved_name, theme=theme, size="md")

        # Build FAB classes
        fab_class = "fab"
        if variant == "mini":
            fab_class += " fab-mini"
        elif variant == "extended":
            fab_class += " fab-extended"

        # Add custom classes
        if "class" in attributes:
            fab_class += f" {attributes.pop('class')}"

        # Handle extended FAB with text
        text = attributes.pop("text", "")
        if variant == "extended" and text:
            content = f"{icon_tag} {text}"
        else:
            content = icon_tag

        # Build attributes
        attrs = {"class": fab_class} | attributes
        attr_string = " ".join(f'{k}="{v}"' for k, v in attrs.items())

        return f"<button {attr_string}>{content}</button>"

    @staticmethod
    def get_available_icons() -> dict[str, list[str]]:
        """Get list of available Material Icons by category."""
        return {
            "action": [
                "home",
                "search",
                "settings",
                "favorite",
                "star",
                "bookmark",
                "help",
                "info",
                "check_circle",
                "done",
                "thumb_up",
                "thumb_down",
            ],
            "communication": [
                "email",
                "phone",
                "chat",
                "message",
                "comment",
                "forum",
                "contact_mail",
                "contact_phone",
                "textsms",
                "call",
            ],
            "content": [
                "add",
                "remove",
                "clear",
                "create",
                "edit",
                "delete_forever",
                "content_copy",
                "content_cut",
                "content_paste",
                "save",
                "undo",
                "redo",
            ],
            "editor": [
                "format_bold",
                "format_italic",
                "format_underlined",
                "format_color_text",
                "format_align_left",
                "format_align_center",
                "format_align_right",
                "format_list_bulleted",
            ],
            "file": [
                "folder",
                "folder_open",
                "insert_drive_file",
                "cloud",
                "cloud_download",
                "cloud_upload",
                "attachment",
                "file_download",
                "file_upload",
            ],
            "hardware": [
                "computer",
                "phone_android",
                "phone_iphone",
                "tablet",
                "laptop",
                "desktop_windows",
                "keyboard",
                "mouse",
                "headset",
                "speaker",
            ],
            "image": [
                "image",
                "photo",
                "photo_camera",
                "video_camera",
                "movie",
                "music_note",
                "palette",
                "brush",
                "color_lens",
                "gradient",
            ],
            "maps": [
                "location_on",
                "location_off",
                "my_location",
                "navigation",
                "map",
                "place",
                "directions",
                "directions_car",
                "directions_walk",
                "local_taxi",
            ],
            "navigation": [
                "menu",
                "close",
                "arrow_back",
                "arrow_forward",
                "arrow_upward",
                "arrow_downward",
                "chevron_left",
                "chevron_right",
                "expand_less",
                "expand_more",
                "fullscreen",
            ],
            "notification": [
                "notifications",
                "notifications_off",
                "notification_important",
                "alarm",
                "alarm_on",
                "alarm_off",
                "event",
                "event_available",
                "schedule",
            ],
            "social": [
                "person",
                "people",
                "group",
                "public",
                "school",
                "domain",
                "cake",
                "mood",
                "mood_bad",
                "sentiment_satisfied",
                "party_mode",
            ],
            "toggle": [
                "check_box",
                "check_box_outline_blank",
                "radio_button_checked",
                "radio_button_unchecked",
                "star",
                "star_border",
                "favorite",
                "favorite_border",
                "visibility",
                "visibility_off",
            ],
            "av": [
                "play_arrow",
                "pause",
                "stop",
                "fast_forward",
                "fast_rewind",
                "skip_next",
                "skip_previous",
                "volume_up",
                "volume_down",
                "volume_off",
            ],
        }


# Template filter registration for FastBlocks
def _register_material_basic_filters(env: Any) -> None:
    """Register basic Material Icons filters."""

    @env.filter("material_icon")  # type: ignore[misc]
    def material_icon_filter(
        icon_name: str,
        theme: str | None = None,
        size: str | None = None,
        **attributes: Any,
    ) -> str:
        """Template filter for Material Icons."""
        icons = depends.get_sync("icons")
        if isinstance(icons, MaterialIcons):
            return icons.get_icon_tag(icon_name, theme=theme, size=size, **attributes)
        return f"<!-- {icon_name} -->"

    @env.filter("material_class")  # type: ignore[misc]
    def material_class_filter(icon_name: str, theme: str | None = None) -> str:
        """Template filter for Material Icons classes."""
        icons = depends.get_sync("icons")
        if isinstance(icons, MaterialIcons):
            return icons.get_icon_class(icon_name, theme)
        return "material-icons"

    @env.global_("materialicons_stylesheet_links")  # type: ignore[misc]
    def materialicons_stylesheet_links() -> str:
        """Global function for Material Icons stylesheet links."""
        icons = depends.get_sync("icons")
        if isinstance(icons, MaterialIcons):
            return "\n".join(icons.get_stylesheet_links())
        return ""


def _register_material_fab_functions(env: Any) -> None:
    """Register Material Design FAB functions."""

    @env.global_("material_fab")  # type: ignore[misc]
    def material_fab(
        icon_name: str,
        variant: str = "regular",
        theme: str | None = None,
        **attributes: Any,
    ) -> str:
        """Generate Material Design Floating Action Button."""
        icons = depends.get_sync("icons")
        if isinstance(icons, MaterialIcons):
            return icons.get_fab_tag(icon_name, variant, theme, **attributes)
        return f"<button class='fab'>{icon_name}</button>"


def _register_material_button_functions(env: Any) -> None:
    """Register Material Design button functions."""

    @env.global_("material_button")  # type: ignore[misc]
    def material_button(
        text: str,
        icon: str | None = None,
        theme: str | None = None,
        icon_position: str = "left",
        **attributes: Any,
    ) -> str:
        """Generate button with Material Icon."""
        icons = depends.get_sync("icons")
        if not isinstance(icons, MaterialIcons):
            return f"<button>{text}</button>"

        btn_class = attributes.pop("class", "btn btn-primary")

        # Build button content
        content = ""
        if icon:
            icon_tag = icons.get_icon_tag(icon, theme=theme, size="sm")

            if icon_position == "left":
                content = f"{icon_tag} {text}"
            elif icon_position == "right":
                content = f"{text} {icon_tag}"
            elif icon_position == "only":
                content = icon_tag
            else:
                content = text
        else:
            content = text

        # Build button attributes
        btn_attrs = {"class": btn_class} | attributes
        attr_string = " ".join(f'{k}="{v}"' for k, v in btn_attrs.items())

        return f"<button {attr_string}>{content}</button>"


def _register_material_chip_functions(env: Any) -> None:
    """Register Material Design chip functions."""

    @env.global_("material_chip")  # type: ignore[misc]
    def material_chip(
        text: str,
        icon: str | None = None,
        theme: str | None = None,
        deletable: bool = False,
        **attributes: Any,
    ) -> str:
        """Generate Material Design chip with icon."""
        icons = depends.get_sync("icons")
        if not isinstance(icons, MaterialIcons):
            return f"<div class='chip'>{text}</div>"

        chip_class = attributes.pop("class", "chip")

        # Build chip content
        content = ""
        if icon:
            icon_tag = icons.get_icon_tag(
                icon, theme=theme, size="sm", class_="chip-icon"
            )
            content += icon_tag

        content += f"<span class='chip-text'>{text}</span>"

        if deletable:
            delete_icon = icons.get_icon_tag(
                "close", theme=theme, size="sm", class_="chip-delete"
            )
            content += delete_icon

        # Build chip attributes
        chip_attrs = {"class": chip_class} | attributes
        attr_string = " ".join(f'{k}="{v}"' for k, v in chip_attrs.items())

        return f"<div {attr_string}>{content}</div>"


def register_materialicons_filters(env: Any) -> None:
    """Register Material Icons filters for Jinja2 templates."""
    _register_material_basic_filters(env)
    _register_material_fab_functions(env)
    _register_material_button_functions(env)
    _register_material_chip_functions(env)


IconsSettings = MaterialIconsSettings
Icons = MaterialIcons

depends.set(Icons, "materialicons")

# ACB 0.19.0+ compatibility
__all__ = [
    "MaterialIcons",
    "MaterialIconsSettings",
    "register_materialicons_filters",
    "Icons",
    "IconsSettings",
]
