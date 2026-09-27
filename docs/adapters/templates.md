# `templates` adapter

The templates adapter wires the async Jinja2 stack
(`jinja2-async-environment` + `starlette-async-jinja`) and the
HTMY Python-component loader into a FastBlocks application. It is
the first adapter you typically register and the one every other
adapter depends on indirectly (style, icons, fonts all register
their helpers as Jinja globals via this adapter's environment).

## Configuration

Configuration keys read from the Oneiric config tree under the
`fastblocks.templates` namespace:

- `directory` (default: `"templates"`) — root directory for template
  file resolution.
- `env_options` (default: `{}`) — extra kwargs forwarded to
  `jinja2_async_environment.AsyncEnvironment`.
- `cache_size` (default: `1024`) — bound on the
  `Template.render_async` LRU cache in `_performance_optimizer.py`.

## Usage

Public API surface:

- `Templates.init_envs(app, depends)` — build the
  `AsyncJinja2Templates` instance and attach it to `app.state`.
- `Templates(app, depends)` — adapter class constructor; registered
  via `oneiric_helper.register_candidate`.
- `template.render_async(**context)` — async render entry point.
- `template.render_block(name, **context)` — block-only render
  (used by HTMX partial swaps).

## See also

- Parent index: [README.md](README.md)
- Module README: `fastblocks/adapters/templates/README.md`
- HTMY components: `fastblocks/adapters/templates/_htmy_components.py`
- Async Jinja troubleshooting:
  `docs/JINJA2_ASYNC_ENVIRONMENT_USAGE.md`
