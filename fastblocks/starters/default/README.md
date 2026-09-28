# {app_name}

A FastBlocks app scaffolded by `fastblocks create-app`. Built on Starlette + HTMX
with the `fastblocks-ui` design system.

## Quick start

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
uv run fastblocks run                # starts uvicorn on 127.0.0.1:8000
```

Open <http://127.0.0.1:8000/> for the landing page and
<http://127.0.0.1:8000/demo> for the search-as-you-type HTMX demo.

## Layout

```
.
├── main.py                  # FastBlocks ASGI entry — `from main:app`
├── routes/                  # Route handlers (home, demo)
├── templates/               # Jinja2 templates (base, home, demo, partials/)
├── adapters/                # Oneiric adapter registrations
├── settings/                # Oneiric layered config (app.yaml, adapters/*.yaml)
├── static/                  # css/img served at /static
├── mcp/                     # Read-only MCP introspection surface
├── tests/                   # pytest suite (routes, templates, htmx, adapter boot)
└── docs/ADAPTERS.md         # Adapter reference
```

## Default style

This scaffold uses `fastblocks_ui` (the FastBlocks design system). To change
styles, edit `settings/app.yaml` (`app.style`) and `settings/adapters/style.yaml`.
The only legal values today are `vanilla` and `fastblocks_ui` — any other value
fails loudly with `unknown style`.

## See also

- [docs/ADAPTERS.md](docs/ADAPTERS.md) — adapter reference
- FastBlocks framework docs — https://github.com/lesleslie/fastblocks
- fastblocks-ui docs — https://github.com/lesleslie/fastblocks-ui
