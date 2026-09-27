# `style` adapter

The style adapter resolves the active UI framework and registers its
helpers/filters into the Jinja environment. The supported styles are
`vanilla` (no helpers, raw HTML) and `fastblocks_ui` (the
`fastblocks-ui` package — the first style adapter wired end-to-end).
Legacy styles `kelp`, `webawesome`, `bulma`, and `custom` were
removed in 0.30.0; the registry now fails loudly for unknown styles
so misconfigurations surface at startup rather than silently
producing unstyled output.

## Configuration

Configuration keys read from the Oneiric config tree under the
`fastblocks.style` (or `fastblocks.app.style` — alias) namespace:

- `framework` (default: `"vanilla"`) — one of `vanilla`,
  `fastblocks_ui`. Unknown values raise at startup.
- `fastblocks_ui_options` (default: `{}`) — kwargs forwarded to the
  `fastblocks_ui` helper registration call (e.g. component bundle
  version pin).

## Usage

Public API surface:

- `style_registry.register_style_functions(env, framework, depends)`
  — entry point called by `Templates.init_envs` after the
  AsyncEnvironment is built.
- `fastblocks_ui.py` — the only first-party style adapter that
  actually wires helpers into the live environment; see its module
  docstring for the rationale.
- `vanilla.py` — no-op registration; documents the contract that
  other styles must satisfy.

## See also

- Parent index: [README.md](README.md)
- Module README: `fastblocks/adapters/style/README.md`
- Style registry contract: `fastblocks/core/style_registry.py`
