# FastBlocks HTMY ↔ Jinja2 hybrid demo — Phase 2 dogfood B3

This is the **B3 deliverable** for the Phase 2 dogfood-readiness build
wave. It exercises the FastBlocks template stack with **three render
modes** for the same greeting-card markup:

| Mode      | Engine                                  | What it proves                                                       |
| --------- | --------------------------------------- | -------------------------------------------------------------------- |
| `jinja`   | Pure Jinja2 template + macro            | The Jinja2-only baseline keeps working.                              |
| `htmy`    | Pure HTMY `GreetingCard` component      | HTMY renders the same DOM structure.                                 |
| `hybrid`  | HTMY component embedded in Jinja2 layout | The two engines compose without semantic drift.                       |

Visit `/?render=<mode>` to see each. The **snapshot test** in
`tests/test_render_hybrid.py::test_all_three_modes_semantically_equivalent`
asserts that all three modes produce byte-identical greeting-card divs
(stripped of the per-mode HTML comment marker).

## Run

```bash
cd examples/htmy-hybrid
uv venv && source .venv/bin/activate
uv pip install -e "../../[dev]"
uv pip install -e .
ONEIRIC__APP__NAME=fastblocks-htmy-hybrid-example ONEIRIC__APP__STYLE=fastblocks_ui \
  python -m uvicorn main:app --host 127.0.0.1 --port 8002
```

Then visit:

- <http://127.0.0.1:8002/?render=jinja>
- <http://127.0.0.1:8002/?render=htmy>
- <http://127.0.0.1:8002/?render=hybrid>

## Tests

```bash
cd examples/htmy-hybrid
../.venv/bin/pytest tests/ -v
```

Expected: 8 tests, all green.

## Layout

```
examples/htmy-hybrid/
├── main.py                       # FastBlocks app factory, port 8002
├── pyproject.toml
├── adapters/
│   └── templates.py              # Registers HybridTemplatesManager via Oneiric
├── components/
│   └── greeting_card.py          # HTMY Component + GreetingCardProps dataclass
├── routes/
│   ├── __init__.py
│   └── greeting.py               # ?render=<jinja|htmy|hybrid> dispatch
├── settings/
│   ├── app.yaml
│   └── adapters/
│       └── templates.yaml        # declares hybrid as default
├── templates/
│   ├── __init__.py               # Jinja2 wrapper
│   ├── base.html
│   └── greeting/
│       ├── _macros.html          # Jinja2 macro for the jinja mode
│       ├── jinja.html            # jinja mode (extends base.html + macro)
│       └── hybrid.html           # hybrid mode (extends base.html + embeds HTMY)
```