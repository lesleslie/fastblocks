# FastBlocks landing page — live dogfood demo

The landing page is the Phase 2 dogfood-readiness surface for FastBlocks.
It exercises every B2 deliverable in the spec and serves as the live
audit surface for the framework itself.

## Run

```bash
cd examples/landing
uv venv && source .venv/bin/activate
uv pip install -e "../../[dev]"
uv pip install -e .
uv run fastblocks run
# OR (without Oneiric env wiring):
ONEIRIC__APP__NAME=fastblocks-landing-example ONEIRIC__APP__STYLE=fastblocks_ui \
  python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

Then visit http://127.0.0.1:8001/.

## Routes

| Route | What it proves |
| ------------------ | ----------------------------------------------------------------- |
| `/` | Headline claims only |
| `/features` | Per-feature section with `ui-section` + `ui-card` |
| `/adapter-matrix` | **D3 live proof** — auto-generated from the Oneiric resolver |
| `/demo` | **D4 + D5 live proof** — search-as-you-type HTMX |
| `/performance` | **D7 live proof** — latest benchmarks from `.benchmarks/` |
| `/security` | **D6** — threat model + CVE status |
| `/docs` | Link to full docs |
| `/install` | One-command install + hello-world |

## Tests

```bash
cd examples/landing
../.venv/bin/pytest tests/ -v
```

Expected: green.

## Theme discipline

Only `--ui-*` tokens are permitted in `templates/` and `static/`. The
CI grep gate (see `tests/test_no_claim_without_evidence.py` plus the
manual `grep -rn -- "--fb-\|--fast-\|--brand-\|#[0-9a-fA-F]\{6\}" templates/ static/` check in the brief) rejects `--fb-*`, `--fast-*`,
`--brand-*`, and hex literals.

Dark variant ships via `[data-theme="dark"]` — the documented closed
decision in `fastblocks-ui/docs/theming-recipes.md`. Not `light-dark()`.
