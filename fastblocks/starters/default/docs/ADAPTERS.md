# Adapter Reference

This app uses the following FastBlocks adapters:

- **Templates**: Jinja2 (via `fastblocks.adapters.templates.jinja2`) — default
  renderer; the scaffold's `templates/__init__.py` is a thin wrapper so the
  starter is runnable without going through the full Oneiric resolver at
  scaffold time.
- **Style**: `fastblocks_ui` (default; provides the design system tokens,
  helpers, and CSS/JS asset paths consumed by `fastblocks-ui`). See
  [fastblocks-ui docs](https://github.com/lesleslie/fastblocks-ui).
- **Icons**: Lucide (default; replaceable via `adapters/icons.py`).
- **Fonts**: Squirrel (default; via `fastblocks.adapters.fonts.squirrel`).
- **Auth**: Skeleton — no routes bound by default; consumers wire their own
  provider on top of `adapters/auth.py`. See `settings/adapters/auth.yaml`
  for the `bind_routes: false` flag.
- **Admin**: Skeleton — no routes bound by default; consumers wire their own
  admin surface on top of `adapters/admin.py`.
- **Routes**: Default dispatcher — resolves the routes registered in
  `routes/__init__.py`.

## Style contract

The framework recognises exactly two legal style values today: `vanilla` and
`fastblocks_ui`. Any other value (including the previously-removed `kelp` and
`webawesome`) fails loudly via the `ResolverMismatchError` contract in
`fastblocks.core.validators`. Do not add other styles to
`settings/adapters/style.yaml` — they will fail at startup.

## Replacing adapters

Each `adapters/*.py` file exposes a `build()` function returning the adapter
instance. To swap, edit the relevant file (and the corresponding YAML under
`settings/adapters/`) to point at your custom adapter module.

For full framework adapter docs, see `docs/adapters/` in the FastBlocks
framework repo.
