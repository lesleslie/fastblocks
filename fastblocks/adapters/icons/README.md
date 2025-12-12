# Icon Adapters

> **FastBlocks Documentation**: [Main](../../../README.md) | [Adapters](../README.md) | [Templates](../templates/README.md)
>
> _Last reviewed: 2025-11-19_

Icon adapters encapsulate SVG/font libraries so FastBlocks can render consistent icon markup regardless of which vendor you choose. Implementations follow the `IconsBase`/`IconsProtocol` contract and register themselves under the `"icons"` or library-specific dependency keys (`"phosphor"`, `"heroicons"`, `"remix_icons"`, etc.) for template filters to consume.

## Available Implementations

| Adapter | Module | Highlights |
|---------|--------|------------|
| Font Awesome (Web Awesome) | `fontawesome.py` | Provides class generation and helper markup for Font Awesome 7 / Web Awesome icons. |
| Phosphor | `phosphor.py` | Exposes all Phosphor styles (regular, bold, duotone) with weight-aware helpers. |
| Heroicons | `heroicons.py` | Handles outline/solid variants with inline SVG output for Tailwind-friendly workflows. |
| Lucide | `lucide.py` | Modernized Feather icon set with configurable stroke widths. |
| Remix Icon | `remixicon.py` | Class-based icon rendering for Remix's extensive library. |
| Material Symbols | `materialicons.py` | Supports filled/outlined/rounded variants with font-based delivery. |

Every adapter inherits `IconsBaseSettings`, giving you standard configuration fields like `cdn_url`, `version`, and per-icon overrides.

## Configuration

Example `settings/adapters/icons.yml` targeting Web Awesome + Phosphor:

```yaml
icons:
  adapter: fontawesome
  settings:
    kit_token: "${FA_KIT_TOKEN}"
    cdn_url: "https://pro.fontawesome.com"
    default_prefix: "wa"

phosphor:
  adapter: phosphor
  settings:
    variant: "duotone"
```

Adapters that expose additional dependency keys (e.g., `heroicons`, `remix_icons`) can be configured in their own YAML blocks so you can mix and match libraries inside the same project.

## Template Helpers

Enhanced filters (see `_enhanced_filters.py`) surface each adapter in Jinja2:

- `[[ wa_icon('save', class='btn__icon') | safe ]]` or `[[ wa_icon_with_text('check', 'Save') | safe ]]`
- `[[ phosphor_icon('rocket', weight='duotone', size='32') | safe ]]`
- `[[ heroicon('home', 'solid', size='24') | safe ]]`
- `[[ remix_icon('home-line', class='nav__icon') | safe ]]`
- `[[ material_icon('settings', 'outlined') | safe ]]`

Pair these with the adapter-specific stylesheet helpers (e.g., `[[ webawesome_stylesheet_links() | safe ]]`) inside your `<head>` block to ensure the necessary CSS/JS assets load.

## Extending

To add a new icon pack:

1. Subclass `IconsBaseSettings` for configuration (CDN URLs, kit IDs, variant flags).
1. Implement `IconsBase` with `get_icon_class()` and `get_icon_tag()` (returning HTML markup or SVG).
1. Register globals/filters if the pack needs template shortcuts (see `register_webawesome_functions` for reference).

Keeping adapters isolated this way makes it trivial to offer multiple icon options within a single FastBlocks application while keeping template syntax predictable.
