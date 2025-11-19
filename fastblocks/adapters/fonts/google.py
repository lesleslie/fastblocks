"""Google Fonts adapter implementation."""

from contextlib import suppress
from urllib.parse import quote_plus
from uuid import UUID

from acb.depends import depends

from ._base import FontsBase, FontsBaseSettings


class GoogleFontsSettings(FontsBaseSettings):
    """Google Fonts-specific settings."""

    api_key: str | None = None  # Optional API key for advanced features
    families: list[str] = ["Roboto", "Open Sans"]
    weights: list[str] = ["400", "700"]
    subsets: list[str] = ["latin"]
    display: str = "swap"  # font-display CSS property
    preconnect: bool = True  # Add preconnect link for performance


class GoogleFonts(FontsBase):
    """Google Fonts adapter implementation."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-4f2a-7b3c-8d9e-f3b4d3c2e1a1")  # Static UUID7
    MODULE_STATUS = "stable"

    # Common Google Fonts families with fallbacks
    FONT_FALLBACKS = {
        "Roboto": "Roboto, -apple-system, BlinkMacSystemFont, sans-serif",
        "Open Sans": "'Open Sans', -apple-system, BlinkMacSystemFont, sans-serif",
        "Lato": "Lato, -apple-system, BlinkMacSystemFont, sans-serif",
        "Montserrat": "Montserrat, -apple-system, BlinkMacSystemFont, sans-serif",
        "Source Sans Pro": "'Source Sans Pro', -apple-system, BlinkMacSystemFont, sans-serif",
        "Inter": "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
        "Poppins": "Poppins, -apple-system, BlinkMacSystemFont, sans-serif",
        "Nunito": "Nunito, -apple-system, BlinkMacSystemFont, sans-serif",
        "Playfair Display": "'Playfair Display', Georgia, serif",
        "Merriweather": "Merriweather, Georgia, serif",
        "Lora": "Lora, Georgia, serif",
        "Source Serif Pro": "'Source Serif Pro', Georgia, serif",
        "Crimson Text": "'Crimson Text', Georgia, serif",
        "PT Serif": "'PT Serif', Georgia, serif",
        "Fira Code": "'Fira Code', 'Source Code Pro', monospace",
        "Source Code Pro": "'Source Code Pro', 'Courier New', monospace",
        "JetBrains Mono": "'JetBrains Mono', 'Source Code Pro', monospace",
        "Inconsolata": "Inconsolata, 'Courier New', monospace",
    }

    def __init__(self) -> None:
        """Initialize Google Fonts adapter."""
        super().__init__()
        self.settings = GoogleFontsSettings()

        # Register with ACB dependency system
        with suppress(Exception):
            depends.set(self)

    async def get_font_import(self) -> str:
        """Generate Google Fonts import statements."""
        # Build font families parameter
        families_param = self._build_families_param()

        # Build query parameters
        params = [f"family={families_param}"]

        if self.settings.subsets:
            subsets = "&".join(self.settings.subsets)
            params.extend((f"subset={subsets}", f"display={self.settings.display}"))

        query_string = "&".join(params)
        url = f"https://fonts.googleapis.com/css2?{query_string}"

        # Generate link tags
        links = []

        # Add preconnect for performance
        if self.settings.preconnect:
            links.extend(
                (
                    '<link rel="preconnect" href="https://fonts.googleapis.com">',
                    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
                )
            )

        # Add the main stylesheet link
        links.append(f'<link rel="stylesheet" href="{url}">')

        return "\n".join(links)

    def get_font_family(self, font_type: str) -> str:
        """Get font family CSS values with fallbacks."""
        # Map font types to families
        if font_type == "primary" and self.settings.families:
            primary_font = self.settings.families[0]
            return self.FONT_FALLBACKS.get(
                primary_font, f"'{primary_font}', sans-serif"
            )
        elif font_type == "secondary" and len(self.settings.families) > 1:
            secondary_font = self.settings.families[1]
            return self.FONT_FALLBACKS.get(secondary_font, f"'{secondary_font}', serif")
        if font_type in self.FONT_FALLBACKS:
            return self.FONT_FALLBACKS[font_type]
        # Default fallbacks
        return {
            "primary": "-apple-system, BlinkMacSystemFont, sans-serif",
            "secondary": "Georgia, serif",
            "monospace": "'Source Code Pro', monospace",
            "heading": "-apple-system, BlinkMacSystemFont, sans-serif",
            "body": "-apple-system, BlinkMacSystemFont, sans-serif",
        }.get(font_type, "inherit")

    def _build_families_param(self) -> str:
        """Build the families parameter for Google Fonts URL."""
        family_strings = []

        for family in self.settings.families:
            # Encode family name
            encoded_family = quote_plus(family)

            # Add weights if specified
            if self.settings.weights:
                weights_str = ";".join(
                    [f"wght@{weight}" for weight in self.settings.weights]
                )
                family_strings.append(f"{encoded_family}:ital,{weights_str}")
            else:
                family_strings.append(encoded_family)

        return "&family=".join(family_strings)

    def get_css_variables(self) -> str:
        """Generate CSS custom properties for fonts."""
        variables = []

        if self.settings.families:
            primary_font = self.get_font_family("primary")
            variables.append(f"  --font-primary: {primary_font};")

            if len(self.settings.families) > 1:
                secondary_font = self.get_font_family("secondary")
                variables.append(f"  --font-secondary: {secondary_font};")

        # Add weight variables
        if self.settings.weights:
            for weight in self.settings.weights:
                var_name = (
                    "normal"
                    if weight == "400"
                    else ("bold" if weight == "700" else f"weight-{weight}")
                )
                variables.append(f"  --font-weight-{var_name}: {weight};")

        if variables:
            return ":root {\n" + "\n".join(variables) + "\n}"
        return ""

    def get_font_preload(self, font_family: str, weight: str = "400") -> str:
        """Generate font preload link for critical fonts."""
        # This would need actual font file URLs, which require API access
        # For now, return a basic structure
        encoded_family = quote_plus(font_family)
        return f'<link rel="preload" as="font" type="font/woff2" href="https://fonts.gstatic.com/s/{encoded_family.lower()}/..." crossorigin>'

    def get_font_face_declarations(self) -> str:
        """Generate @font-face declarations for local hosting (if API key available)."""
        if not self.settings.api_key:
            return "<!-- API key required for local font hosting -->"

        # This would integrate with Google Fonts API to get actual font file URLs
        # For now, return a placeholder
        declarations = []
        for family in self.settings.families:
            for weight in self.settings.weights:
                declarations.append(f"""
@font-face {{
  font-family: '{family}';
  font-style: normal;
  font-weight: {weight};
  font-display: {self.settings.display};
  src: url('...') format('woff2');
}}""")

        return "\n".join(declarations)

    def validate_font_availability(self, font_family: str) -> bool:
        """Check if a font family is available in Google Fonts."""
        # This would require API integration
        # For now, return True for common fonts
        common_fonts = {
            "Roboto",
            "Open Sans",
            "Lato",
            "Montserrat",
            "Source Sans Pro",
            "Inter",
            "Poppins",
            "Nunito",
            "Playfair Display",
            "Merriweather",
            "Lora",
            "Source Serif Pro",
            "Fira Code",
            "Source Code Pro",
        }
        return font_family in common_fonts

    async def get_optimized_import(
        self, critical_fonts: list[str] | None = None
    ) -> str:
        """Generate optimized font import with critical font prioritization."""
        if critical_fonts:
            # Prioritize critical fonts in the import order
            prioritized_families = []
            remaining_families = self.settings.families.copy()

            for critical in critical_fonts:
                if critical in remaining_families:
                    prioritized_families.append(critical)
                    remaining_families.remove(critical)

            # Add remaining fonts
            prioritized_families.extend(remaining_families)

            # Temporarily override families for this import
            original_families = self.settings.families
            self.settings.families = prioritized_families

            import_html = await self.get_font_import()

            # Restore original families
            self.settings.families = original_families

            return import_html

        return await self.get_font_import()


FontsSettings = GoogleFontsSettings
Fonts = GoogleFonts

depends.set(Fonts, "google")
