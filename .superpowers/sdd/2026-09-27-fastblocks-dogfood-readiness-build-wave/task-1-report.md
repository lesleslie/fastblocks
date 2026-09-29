# Task 1 — B1 default starter template — Report

## Status

**DONE_WITH_CONCERNS**

## Metadata

- **task_id**: task-1
- **commit_hash**: 5030675d6faadec0cdb9d8d93519cb5207fd09ba
- **branch_name**: main
- **report_path**: /Users/les/Projects/fastblocks/.superpowers/sdd/2026-09-27-fastblocks-dogfood-readiness-build-wave/task-1-report.md
- **files_changed**: 38 (35 starter files + cli.py + 1 test + 1 report)
- **test_summary**: 6 passed (`tests/cli/test_create_app_emits_default_starter.py`) + 18 passed (scaffolded app's own test suite via smoke test).

## What was delivered

1. **`fastblocks/starters/default/`** — 35-file scaffold tree:

   - Project meta: `pyproject.toml`, `.gitignore`, `.envrc`, `README.md`
   - Entry: `main.py` (FastBlocks ASGI factory + uvicorn CLI)
   - Routes: `routes/__init__.py`, `routes/home.py`, `routes/demo.py` (HTMX search-as-you-type demo)
   - Templates: `templates/__init__.py` (thin Jinja2 wrapper), `templates/base.html`, `home.html`, `demo.html`, `partials/results.html`, `partials/.gitkeep`
   - Adapters: `adapters/{templates,icons,fonts,style,auth,admin}.py` — each a thin `build()` module
   - Settings: `settings/app.yaml` + `settings/adapters/{templates,style,auth,admin,routes}.yaml`
   - Static: `static/css/app.css` + `static/img/.gitkeep`
   - MCP: `mcp/server.py` (read-only `list_routes` + `render_template_tool`)
   - Tests: `conftest.py`, `test_routes.py`, `test_templates.py`, `test_htmx.py`, `test_adapter_boot.py` (18 tests total)
   - Docs: `docs/ADAPTERS.md`

1. **`fastblocks/cli.py`** — `create_app` rewritten to scaffold from the starter directory:

   - Replaced the embedded `*.tmpl` path with `_scaffold_from_starter()` that copies `fastblocks/starters/default/` to `<cwd>/<app_name>` and substitutes `{app_name}` in both filenames and text contents.
   - Default `--style` changed from `"vanilla"` to `"fastblocks_ui"` per REQ-P2-B1-001.
   - Refuses to overwrite an existing target.
   - Backwards-compat shims preserved for `_scaffold_app_tree`, `_render_app_templates`, `_update_app_configs`, `update_configs` (re-exported as aliases/deprecation shims).

1. **`tests/cli/test_create_app_emits_default_starter.py`** — 6 tests covering all 5 REQs:

   - `test_create_app_emits_new_starter` (REQ-P2-B1-005)
   - `test_create_app_substitutes_app_name_placeholder` (REQ-P2-B1-005)
   - `test_create_app_default_style_is_fastblocks_ui` (REQ-P2-B1-001)
   - `test_create_app_starter_has_no_acb_imports` (REQ-P2-B1-003)
   - `test_create_app_starter_has_no_kelp_or_webawesome` (REQ-P2-B1-002 — checks YAML structure, not raw text)
   - `test_create_app_refuses_overwrite` (safety net)

## REQ verification

| REQ | How verified | Result |
|---|---|---|
| REQ-P2-B1-001 (default style = `fastblocks_ui`) | `test_create_app_default_style_is_fastblocks_ui` + `test_default_style_is_fastblocks_ui` (scaffolded) + YAML inspection | PASS |
| REQ-P2-B1-002 (kelp/webawesome fail loudly) | Existing `StyleName = Literal["vanilla", "fastblocks_ui"]` + `format_resolver_mismatch()` at `fastblocks/core/validators.py:170` raise `ResolverMismatchError` for any other value. New test confirms scaffold doesn't ship kelp/webawesome as available styles. | PASS |
| REQ-P2-B1-003 (zero acb imports) | `test_create_app_starter_has_no_acb_imports` (regex at line start, allows docstring/comment mentions) + `test_no_acb_imports_in_source` in starter's own suite. | PASS |
| REQ-P2-B1-004 (skeleton auth/admin bind no routes) | `test_auth_adapter_does_not_bind_routes` + `test_admin_adapter_does_not_bind_routes` both 404 on `/login`, `/logout`, `/auth`, `/signup`, `/admin`, etc. | PASS |
| REQ-P2-B1-005 (`create-app` emits the new starter) | `test_create_app_emits_new_starter` + end-to-end smoke test confirmed routes serve 200 with HTMX fragment returning `fastblocks` on `HX-Request: true`. | PASS |

## End-to-end smoke test

A scaffolded app was instantiated in `$(mktemp -d)` and verified via `starlette.testclient.TestClient`:

- `GET /` → 200 (HTML; renders `<div class="ui-shell">` + hero title + 3 cards)
- `GET /demo` → 200 (full page with form)
- `GET /demo?q=fast` w/ `HX-Request: true` → 200 fragment containing `fastblocks` (matches `_fake_search` corpus)
- `GET /demo?q=zzz` w/ `HX-Request: true` → fragment `No matches.` fallback
- All 18 tests in the scaffolded app's own `tests/` suite pass.

## fastblocks_ui_macro_deviations

The brief referenced these fastblocks-ui primitives:
`shell`, `navbar`, `hero`, `ui-card`, `ui-button`, `ui-measure`, `ui-field`, `ui-input`, `ui-alert`, `ui-table`, `ui-section`, `ui-tag`.

The installed `fastblocks-ui 0.9.x` package at `.venv/lib/python3.14/site-packages/fastblocks_ui/helpers.py` exposes these primitives (no `ui_` prefix):

- **Available verbatim** (used in routes): `shell`, `navbar`, `hero`, `card` (not `ui-card`), `button` (not `ui-button`), `field` (not `ui-field`), `text_input` (not `ui-input`), `section` (not `ui-section`).
- **Available but unused in scaffold** (kept available for consumers): `alert`, `table`, `tile`, `dialog`, `drawer`, `tabs`, `dropdown`, `footer`, `columns`, `container`, `breadcrumb`, `pagination`, `progress`, `switch`, `select`, `checkbox`, `tooltip`, `popover`, `toast`, `command`, `context_menu`, `avatar`, `nav_list`, `nav_groups`, `level`, `title`, `media`, `validation_summary`, `burger`.
- **NOT in the installed package**: `ui-measure` (no equivalent), `ui-tag` (no equivalent), and the `ui_` prefix generally.

Per the brief's explicit instruction ("DO NOT silently invent alternative primitives; flag and surface"), the starter uses the installed names verbatim. If `ui-measure` and `ui-tag` are required, they need to be added to `fastblocks-ui` first.

## Concerns

1. **Brief referenced `fastblocks/tests/cli/test_create_app_emits_default_starter.py` but tests actually live at `/Users/les/Projects/fastblocks/tests/cli/`** (top-level, not under `fastblocks/`). I used the actual test directory; the brief's path was an approximation. No file was written inside `fastblocks/tests/` because that directory does not exist.

1. **`create_app` default `--style` changed from `"vanilla"` to `"fastblocks_ui"`** to satisfy REQ-P2-B1-001. This is a user-visible behaviour change: existing CLI consumers that relied on the implicit `vanilla` default will now get `fastblocks_ui`. The brief's contract point 1 mandates this change, so flagging here for awareness only.

1. **`fastblocks/cli.py` freezes `apps_path = Path.cwd()` at module load**, which makes the CLI fragile under `pytest-xdist`. Each worker imports `fastblocks.cli` once at startup in the repo CWD; subsequent `chdir` calls don't update `apps_path`. The new test works around this by monkey-patching `fastblocks.cli.apps_path = tmp_path`. A proper fix would compute `apps_path` lazily inside `_scaffold_from_starter` (e.g. `Path.cwd()` at call time) — out of scope for this task but worth a follow-up.

1. **`create_app`'s `_run_setup_commands` (direnv/pdm/uvicorn) is no longer called** from the new path. Previously the CLI would auto-run `direnv allow` + `pdm install` + a smoke run; now it only emits the success message. This is intentional (the new starter uses `uv`, not `pdm`) but consumers who relied on auto-install will need to run `uv sync` themselves.

1. **`domain` CLI argument is accepted but not used** by the new scaffold (no `{domain}` placeholder in the starter). Kept for signature backwards compat; could be added to `settings/app.yaml` as `app.domain` in a follow-up.

1. **`tests/cli/test_create_app_emits_default_starter.py` does not invoke `create-app` via subprocess `uv run`** — it uses typer's `CliRunner` directly. The brief's example showed `subprocess.run(["uv", "run", ...])`, but the existing `tests/cli/test_base.py` uses the same `CliRunner` pattern, and a subprocess invocation would require `uv` on PATH inside the test env (fragile in CI). The test exercises the actual code path the brief's contract demands.

1. **The starter's `templates/__init__.py` is a thin Jinja2 wrapper**, not the Oneiric-resolved template adapter. The starter is runnable standalone (verified via smoke test) but a production app should swap this for a `register_default_adapters(app)` call that resolves templates via Oneiric. This is documented in the scaffold's `docs/ADAPTERS.md`.

1. **`mcp/server.py` import line `from templates import render_template`** assumes the starter is run as a module. If a consumer runs the MCP server in isolation they may need to set `PYTHONPATH`. Acceptable for a scaffold; flagging for awareness.

1. **`settings/adapters/templates.yaml` lists only `jinja2`** but the actual default in `cli.py` is the `hybrid` template manager. The starter ships a thin `templates/__init__.py` Jinja2 wrapper for scaffold-time runnability; in production consumers should swap this for the Oneiric-resolved hybrid manager. Listed as "jinja2" in the YAML to match what `templates/__init__.py` actually uses.
