# Style Adapters

> **FastBlocks Documentation**: [Main](../../../README.md) | [Adapters](../README.md) | [Templates](../templates/README.md)
>
> _Last reviewed: 2025-11-19_

The style adapters provide pluggable CSS frameworks for FastBlocks. Each adapter exposes the same protocol (`StyleBase`/`StyleProtocol`) so templates can ask for component class names and stylesheet links without caring which framework backs the UI.

## Available Implementations

| Adapter | Module | Highlights |
|---------|--------|------------|
| Bulma | `bulma.py` | Wraps Bulma's CDN build, exposes helper classes for buttons, cards, notifications, etc. |
| Web Awesome | `webawesome.py` | Ships Font Awesome 7's Web Awesome components plus preset utility classes. |
| Kelp | `kelp.py` | First-party lightweight system with generated CSS variables, utility classes, and component builders. |
| Vanilla | `vanilla.py` | Minimal, semantic styling intended as a starting point for bespoke themes. |

Every adapter registers itself with the dependency container (`depends.set(self)`) using the `"styles"` key, so template helpers and CLI tooling can resolve whichever implementation you configure.

## Configuration

Configure styles in `settings/adapters/styles.yml`. Example using the Kelp adapter:

```yaml
styles:
  adapter: kelp
  settings:
    theme: "default"
    enable_shadows: true
    additional_stylesheets:
      - "/static/css/app.css"
```

Switching adapters is as simple as changing the `adapter` field to `bulma`, `webawesome`, or `vanilla`. Adapter-specific options live inside `settings`.

## Template Helpers

Each adapter registers globals and filters inside `fastblocks/adapters/style/<name>.py`. Common helpers include:

- `[[ kelp_stylesheet_links() | safe ]]` – injects the adapter's `<link>`/`<style>` tags into your layout block.
- `[[ kelp_class('btn-primary') ]]` – returns the framework-specific class string for a named component.
- `[[ kelp_component('card', '<p>Hello</p>', variant='elevated') | safe ]]` – renders canonical markup for complex components.

Replace `kelp_` with the adapter prefix you have enabled (e.g., `webawesome_stylesheet_links`). These helpers are also exposed to editor auto-complete via `_syntax_support.py`.

## Extending

To add a new style adapter:

1. Create `MyStyleSettings(StyleBaseSettings)` and declare adapter metadata (`MODULE_ID`, `MODULE_STATUS`).
1. Implement `MyStyle(StyleBase)` with `get_stylesheet_links()` and `get_component_class()`.
1. Register any globals/filters in `register_mystyle_functions(env)` so templates can discover your adapter.

Use the existing adapters as references—the dependency injection hooks and exported names are intentionally consistent across implementations.
