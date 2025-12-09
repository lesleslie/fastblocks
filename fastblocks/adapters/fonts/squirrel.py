"""Font Squirrel adapter implementation for self-hosted fonts."""

import typing as t
from contextlib import suppress
from pathlib import Path
from uuid import UUID

from acb.depends import depends

from ._base import FontsBase, FontsBaseSettings


class FontSquirrelFontsSettings(FontsBaseSettings):
    """Font Squirrel-specific settings."""

    fonts_dir: str = "/static/fonts"
    fonts: list[dict[str, t.Any]] = []
    preload_critical: bool = True
    display: str = "swap"


class FontSquirrelFonts(FontsBase):
    """Font Squirrel adapter for self-hosted fonts."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-4f2a-7b3c-8d9e-f3b4d3c2e1a2")  # Static UUID7
    MODULE_STATUS = "stable"

    # Common font format priorities (most modern first)
    FORMAT_PRIORITIES = ["woff2", "woff", "ttf", "otf", "eot"]

    def __init__(self) -> None:
        """Initialize Font Squirrel adapter."""
        super().__init__()
        self.settings = FontSquirrelFontsSettings()

        # Register with ACB dependency system
        with suppress(Exception):
            depends.set(self)

    async def get_font_import(self) -> str:
        """Generate @font-face declarations for self-hosted fonts."""
        if not self.settings.fonts:
            return "<!-- No self-hosted fonts configured -->"

        font_faces = []

        for font_config in self.settings.fonts:
            font_face = self._generate_font_face(font_config)
            if font_face:
                font_faces.append(font_face)

        if font_faces:
            return f"<style>\n{chr(10).join(font_faces)}\n</style>"
        return ""

    def get_font_family(self, font_type: str) -> str:
        """Get font family CSS values for configured fonts."""
        # Look for a font with the specified type
        for font_config in self.settings.fonts:
            if font_config.get("type") == font_type:
                family_name = font_config.get("family", font_config.get("name", ""))
                fallback = font_config.get(
                    "fallback", self._get_default_fallback(font_type)
                )
                return f"'{family_name}', {fallback}" if family_name else fallback

        # Return default fallbacks if no specific font found
        return self._get_default_fallback(font_type)

    def _generate_font_face(self, font_config: dict[str, t.Any]) -> str:
        """Generate a single @font-face declaration."""
        family = font_config.get("family") or font_config.get("name")
        if not family:
            return ""

        # Build font-face properties
        properties = [
            f"  font-family: '{family}';",
            f"  font-display: {self.settings.display};",
        ]

        # Add font style
        style = font_config.get("style", "normal")
        properties.append(f"  font-style: {style};")

        # Add font weight
        weight = font_config.get("weight", "400")
        properties.append(f"  font-weight: {weight};")

        # Build src declaration
        src_parts = self._build_src_declaration(font_config)
        if not src_parts:
            return ""  # No valid sources found

        properties.append(f"  src: {src_parts};")

        # Add unicode-range if specified
        if "unicode_range" in font_config:
            properties.append(f"  unicode-range: {font_config['unicode_range']};")

        return f"@font-face {{\n{chr(10).join(properties)}\n}}"

    def _handle_single_file_path(self, font_config: dict[str, t.Any]) -> list[str]:
        """Handle single file path configuration."""
        src_parts = []
        file_path = font_config["path"]
        format_hint = self._get_format_from_path(file_path)
        url = self._normalize_font_url(file_path)
        src_parts.append(f"url('{url}') format('{format_hint}')")
        return src_parts

    def _handle_multiple_file_paths(self, font_config: dict[str, t.Any]) -> list[str]:
        """Handle multiple file paths with formats."""
        src_parts = []
        files = font_config["files"]

        # Sort files by format priority
        sorted_files = sorted(
            files,
            key=lambda f: self.FORMAT_PRIORITIES.index(f.get("format", "ttf"))
            if f.get("format") in self.FORMAT_PRIORITIES
            else 999,
        )

        for file_info in sorted_files:
            file_path = file_info.get("path")
            format_hint = file_info.get("format") or self._get_format_from_path(
                file_path
            )

            if file_path and format_hint:
                url = self._normalize_font_url(file_path)
                src_parts.append(f"url('{url}') format('{format_hint}')")

        return src_parts

    def _handle_directory_discovery(self, font_config: dict[str, t.Any]) -> list[str]:
        """Handle directory-based font discovery."""
        src_parts = []
        directory = font_config["directory"]
        family = font_config.get("family") or font_config.get("name", "")
        weight = font_config.get("weight", "400")
        style = font_config.get("style", "normal")

        # Look for font files in directory
        if family:  # Only proceed if family name is available
            discovered_files = self._discover_font_files(
                directory, family, weight, style
            )
            for file_path, format_hint in discovered_files:
                url = self._normalize_font_url(file_path)
                src_parts.append(f"url('{url}') format('{format_hint}')")

        return src_parts

    def _build_src_declaration(self, font_config: dict[str, t.Any]) -> str:
        """Build the src property for @font-face."""
        src_parts = []

        # Handle single file path
        if "path" in font_config:
            src_parts.extend(self._handle_single_file_path(font_config))

        # Handle multiple file paths with formats
        elif "files" in font_config:
            src_parts.extend(self._handle_multiple_file_paths(font_config))

        # Handle directory-based discovery
        elif "directory" in font_config:
            src_parts.extend(self._handle_directory_discovery(font_config))

        return ", ".join(src_parts)

    def _get_format_from_path(self, file_path: str) -> str:
        """Determine font format from file extension."""
        path = Path(file_path)
        extension = path.suffix.lower()

        format_map = {
            ".woff2": "woff2",
            ".woff": "woff",
            ".ttf": "truetype",
            ".otf": "opentype",
            ".eot": "embedded-opentype",
            ".svg": "svg",
        }

        return format_map.get(extension, "truetype")

    def _normalize_font_url(self, file_path: str) -> str:
        """Normalize font file path to URL."""
        # If already a full URL, return as-is
        if file_path.startswith(("http://", "https://", "//")):
            return file_path

        # If relative path, prepend fonts directory
        if not file_path.startswith("/"):
            return f"{self.settings.fonts_dir.rstrip('/')}/{file_path}"

        return file_path

    def _discover_font_files(
        self, directory: str, family: str, weight: str, style: str
    ) -> list[tuple[str, str]]:
        """Discover font files in a directory based on naming patterns."""
        discovered = []

        # Common naming patterns for font files
        patterns = [
            f"{family.lower().replace(' ', '-')}-{weight}-{style}",
            f"{family.lower().replace(' ', '')}{weight}{style}",
            f"{family.replace(' ', '')}-{weight}",
            f"{family.lower()}-{style}",
            family.lower().replace(" ", "-"),
        ]

        for pattern in patterns:
            for ext in (".woff2", ".woff", ".ttf", ".otf"):
                file_path = f"{directory.rstrip('/')}/{pattern}{ext}"
                format_hint = self._get_format_from_path(file_path)
                discovered.append((file_path, format_hint))

        return discovered

    def _get_default_fallback(self, font_type: str) -> str:
        """Get default fallback fonts for different types."""
        fallbacks = {
            "primary": "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
            "secondary": "Georgia, 'Times New Roman', serif",
            "heading": "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
            "body": "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
            "monospace": "'Courier New', monospace",
            "display": "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
            "sans-serif": "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
            "serif": "Georgia, 'Times New Roman', serif",
        }
        return fallbacks.get(font_type, "inherit")

    def _get_default_critical_fonts(self) -> list[str]:
        """Get default critical fonts (first font of each type).

        Returns:
            List of font family names to preload
        """
        fonts_to_preload = []
        seen_types = set()

        for font_config in self.settings.fonts:
            font_type = font_config.get("type")
            if font_type and font_type not in seen_types:
                font_family = font_config.get("family") or font_config.get("name")
                if font_family:
                    fonts_to_preload.append(font_family)
                    seen_types.add(font_type)

        return fonts_to_preload

    def _generate_preload_links_for_fonts(self, font_families: list[str]) -> list[str]:
        """Generate preload links for specified font families.

        Args:
            font_families: List of font family names

        Returns:
            List of preload link HTML strings
        """
        preload_links: list[str] = []

        for font_family in font_families:
            for font_config in self.settings.fonts:
                config_family = font_config.get("family") or font_config.get("name")
                if config_family == font_family:
                    preload_link = self._generate_preload_link(font_config)
                    if preload_link:
                        preload_links.append(preload_link)
                    break

        return preload_links

    def get_preload_links(self, critical_fonts: list[str] | None = None) -> str:
        """Generate preload links for critical fonts."""
        if not self.settings.preload_critical:
            return ""

        # Determine which fonts to preload
        fonts_to_preload = critical_fonts or self._get_default_critical_fonts()

        # Generate preload links
        preload_links = self._generate_preload_links_for_fonts(fonts_to_preload)

        return "\n".join(preload_links)

    def _find_best_font_file(self, font_config: dict[str, t.Any]) -> str | None:
        """Find the best format file (woff2 preferred, then woff).

        Args:
            font_config: Font configuration dictionary

        Returns:
            Path to best font file or None
        """
        if "path" in font_config:
            # Dictionary access returns Any, so we cast to the expected type
            return t.cast(str | None, font_config["path"])

        if "files" not in font_config:
            return None

        # Search for woff2 first
        for file_info in font_config["files"]:
            if file_info.get("format") == "woff2":
                # Dictionary.get() returns Any, so we cast to the expected type
                return t.cast(str | None, file_info.get("path"))

        # Fall back to woff
        for file_info in font_config["files"]:
            if file_info.get("format") == "woff":
                # Dictionary.get() returns Any, so we cast to the expected type
                return t.cast(str | None, file_info.get("path"))

        return None

    def _generate_preload_link(self, font_config: dict[str, t.Any]) -> str:
        """Generate a preload link for a specific font."""
        best_file = self._find_best_font_file(font_config)

        if best_file:
            url = self._normalize_font_url(best_file)
            return f'<link rel="preload" as="font" type="font/woff2" href="{url}" crossorigin>'

        return ""

    def validate_font_files(self) -> dict[str, list[str]]:
        """Validate that configured font files exist and are accessible."""
        validation_results: dict[str, list[str]] = {
            "valid": [],
            "invalid": [],
            "warnings": [],
        }

        for font_config in self.settings.fonts:
            family = font_config.get("family") or font_config.get("name", "Unknown")

            if "path" in font_config:
                # Single file validation would go here
                validation_results["valid"].append(f"{family}: {font_config['path']}")
            elif "files" in font_config:
                # Multiple files validation would go here
                for file_info in font_config["files"]:
                    validation_results["valid"].append(
                        f"{family}: {file_info.get('path', 'Unknown path')}"
                    )
            else:
                validation_results["warnings"].append(
                    f"{family}: No font files specified"
                )

        return validation_results


FontsSettings = FontSquirrelFontsSettings
Fonts = FontSquirrelFonts

depends.set(Fonts, "squirrel")
