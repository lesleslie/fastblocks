# `icons` adapter

The icons adapter resolves the active icon library and exposes
icon-name → SVG-string helpers for templates. Five libraries are
bundled: `fontawesome`, `heroicons`, `lucide`, `materialicons`,
`phosphor`, and `remixicon`. Selection is config-driven; the
adapter returns the right helper for the configured library at
template-render time.

## Configuration

Configuration keys read from the Oneiric config tree under the
`fastblocks.icons` namespace:

- `library` (default: `"heroicons"`) — one of the bundled library
  keys (see list above). Unknown values raise at startup.
- `version` (default: library-specific) — pins the icon set version
  when the library is CDN-loaded (e.g. fontawesome).

## Usage

Public API surface:

- `Icons(library)` — adapter constructor; picks the right
  library module under `fastblocks/adapters/icons/<library>.py`.
- `Icons.render(name, **attrs)` — returns the SVG string for
  `name`, with `**attrs` merged into the SVG root element.
- Each library module exposes a `ICON_NAMES` set and a `render`
  function; templates that need direct access can import the
  module constant.

## See also

- Parent index: [README.md](README.md)
- Module README: `fastblocks/adapters/icons/README.md`
