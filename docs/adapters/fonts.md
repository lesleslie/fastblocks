# `fonts` adapter

The fonts adapter resolves the active web-font provider and emits
the `<link>` / `@import` markup needed to load self-hosted or
CDN-hosted fonts. Two providers ship in-tree: `google` (Google
Fonts via CSS API) and `squirrel` (Font Squirrel self-hosted).
Unknown providers raise at startup.

## Configuration

Configuration keys read from the Oneiric config tree under the
`fastblocks.fonts` namespace:

- `provider` (default: `"google"`) — `google` or `squirrel`.
- `families` (default: `[]`) — list of font family names to load.
  For `google`, these map to Google Fonts API queries; for
  `squirrel`, these map to filenames under the configured
  self-host directory.
- `self_host_dir` (default: `null`) — required when
  `provider=squirrel`; absolute path to the self-hosted font
  directory.

## Usage

Public API surface:

- `Fonts(provider)` — adapter constructor; picks the right
  provider module under `fastblocks/adapters/fonts/<provider>.py`.
- `Fonts.get_font_import()` — returns the `<style>` or `<link>`
  markup to inject into the page head. Returns the documented
  empty-fonts branch (`<!-- No self-hosted fonts configured -->`)
  when no families are configured.
- `Fonts.family_url(family)` — returns the URL/path for a single
  family (used for preconnect hints).

## See also

- Parent index: [README.md](README.md)
- Module README: `fastblocks/adapters/fonts/README.md`
