# Font Adapters

> **FastBlocks Documentation**: [Main](../../../README.md) | [Adapters](../README.md) | [Templates](../templates/README.md)
>
> _Last reviewed: 2025-11-19_

Font adapters centralize how web fonts are loaded and referenced across layouts. They implement `FontsBase`/`FontsProtocol`, expose async helpers for imports, and register themselves under the `"fonts"` dependency key so both sync and async template filters can reuse the same configuration.

## Available Implementations

| Adapter | Module | Highlights |
|---------|--------|------------|
| Google Fonts | `google.py` | Builds optimized `<link>` tags, optional preconnect hints, and CSS variables for popular families. |
| Font Squirrel | `squirrel.py` | Targets self-hosted kits exported from Font Squirrel, generating `@font-face` blocks for bundled assets. |

## Configuration

Example `settings/adapters/fonts.yml` for Google Fonts:

```yaml
fonts:
  adapter: google
  settings:
    families: ["Inter", "Source Serif Pro"]
    weights: ["400", "600", "700"]
    subsets: ["latin", "latin-ext"]
    display: "swap"
```

Switch `adapter` to `squirrel` when you want to serve local assets and provide the kit metadata the adapter expects (family name, file paths, weights).

## Template Helpers

The template layer exposes both sync and async helpers:

- `[[ font_import() ]]` or `[[ await async_font_import() ]]` inject the `<link>` tags returned by the active adapter.
- `[[ await async_optimized_font_loading(['Inter', 'Roboto Mono']) ]]` preloads critical fonts (delegates to adapter implementation when available).
- `[[ font_face_declaration('MyFont', {'woff2': '/fonts/myfont.woff2'}) | safe ]]` outputs `@font-face` rules; adapters that provide `generate_font_face()` will override the fallback implementation.

In Python, you can always access the adapter directly:

```python
from acb.depends import depends

Fonts = depends.get_sync("fonts")
font_css = await Fonts.get_font_import()
```

## Extending

New font adapters should:

1. Subclass `FontsBaseSettings` for configuration (hostnames, kit IDs, etc.).
1. Implement `get_font_import()` (async) and optionally helper methods like `get_font_family()` or `get_optimized_loading()`.
1. Register any sync wrappers (`get_sync_font_import`) if your adapter needs to be reachable from sync template contexts.

Use the Google Fonts adapter as a reference for how to generate preconnect tags, CSS variables, and preloads while staying compliant with the base protocol.
