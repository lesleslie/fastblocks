# Style Adapters

> **FastBlocks Documentation**: [Main](../../../README.md) | [Adapters](../README.md) | [Templates](../templates/README.md)
>
> _Last reviewed: 2026-08-21 (Phase 1A style cleanup)_

The style adapters provide pluggable CSS frameworks for FastBlocks. Each adapter exposes the same protocol (`StyleBase`/`StyleProtocol`) so templates can ask for component class names and stylesheet links without caring which framework backs the UI.

## Available Implementations

| Adapter | Module | Highlights |
|---------|--------|------------|
| Vanilla | `vanilla.py` | Minimal, semantic styling intended as a starting point for bespoke themes. |
| FastBlocks UI | `fastblocks_ui.py` | Default. First-party component layer on top of the `fastblocks-ui` CSS framework; provides `ui_button`, `ui_card`, etc., plus asset paths and class lookups. |

Every adapter registers itself with the Oneiric resolver (`register_candidate(depends, domain="fastblocks", key="styles", factory=lambda: self)`) so template helpers and CLI tooling can resolve whichever implementation you configure.

## Configuration

Configure styles in `settings/adapters/styles.yml`. Example using the `fastblocks_ui` adapter:

```yaml
styles:
  adapter: fastblocks_ui
  settings:
    theme: "default"
    enable_shadows: true
    additional_stylesheets:
      - "/static/css/app.css"
```

Switching adapters is as simple as changing the `adapter` field to `vanilla`. Adapter-specific options live inside `settings`.

## Template Helpers

Each adapter registers globals and filters inside `fastblocks/adapters/style/<name>.py`. Common helpers include:

- `[[ fastblocks_ui_stylesheet_links() | safe ]]` – injects the adapter's `<link>`/`<style>` tags into your layout block.
- `[[ fastblocks_ui_class('btn-primary') ]]` – returns the framework-specific class string for a named component.
- `[[ fastblocks_ui_button('<p>Hello</p>', variant='elevated') | safe ]]` – renders canonical markup for complex components.

These helpers are also exposed to editor auto-complete via `_syntax_support.py`.

## Extending

To add a new style adapter:

1. Create `MyStyleSettings(StyleBaseSettings)` and declare adapter metadata (`MODULE_ID`, `MODULE_STATUS`).
1. Implement `MyStyle(StyleBase)` with `get_stylesheet_links()` and `get_component_class()`.
1. Register any globals/filters in `register_mystyle_functions(env)` so templates can discover your adapter.

Use the existing adapters as references — the dependency injection hooks and exported names are intentionally consistent across implementations.

Note: when writing `register_<name>_functions`, use plain `env.globals[name] = func` / `env.filters[name] = func` assignment. `@env.global_(...)` / `@env.filter(...)` decorator calls do not exist on a real Jinja2 environment.

## Removed styles (since 0.30.0)

The `kelp`, `webawesome`, `bulma`, and `custom` style adapters were removed in fastblocks 0.30.0. Each carried multiple silent-failure traps (decorator-API misuse, wrong-Resolver-API, masked XSS surface) swallowed by `with suppress(Exception)`; users who selected them registered nothing and rendered as unstyled without warning. After upgrade, `config.app.style = "kelp"` (etc.) fails loudly at startup with `unknown style: 'kelp'` from `style_registry.py`. Migrate to `fastblocks_ui` (recommended) or `vanilla`.
