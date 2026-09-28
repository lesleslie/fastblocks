---
status: draft
role: implementation
kind: plan
date: 2026-09-27
last_reviewed: 2026-09-27
topic: fastblocks-phase2-build-wave
---

# FastBlocks Phase 2 Build Wave — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship 3 dogfood deliverables — B1 starter template, B2 landing page at `examples/landing/`, B3 HTMY ↔ Jinja2 hybrid demo at `examples/htmy-hybrid/` — that exercise the audited FastBlocks framework end-to-end.

**Architecture:** Three self-contained example directories (one per deliverable) plus an integration smoke layer. B2 lands on B1 (UI primitives inherited from the starter); B3 is standalone (one route, three renderers). Each ships its own Oneiric-configured app + tests. No cross-deliverable coupling except route patterns and UI primitive reuse.

**Tech Stack:** Python 3.14, FastBlocks (Starlette + HTMX + async), Oneiric (DI/config/adapter resolution), fastblocks-ui (default style; `>=0.9,<0.10`), HTMY (component renderer), Jinja2 (template renderer), pytest, ty, mypy.

**Spec:** `docs/superpowers/specs/2026-09-27-fastblocks-dogfood-readiness-design.md` §B1, §B2, §B3 (sections 189-310).

**Prior work this builds on:** Plan 1 of 2 (audit pass) is shipped at HEAD `869b044`. Phase 1.5+ is complete. Phase 1 audit gates are green. See `.superpowers/sdd/2026-09-27-fastblocks-phase1.5-plus/progress.md` for the audit-clearance ledger and `docs/superpowers/sdd-logs/2026-09-27-phase1.5-plus-ledger.md` for the archived copy.

## Global Constraints

Verbatim from spec §12 + Phase 1.5+ commitments:

- **Pre-1.0 replace, not deprecate** — no deprecation windows; deleted code stays deleted.
- **Direct merge to main, no PRs** (`bodai-pre-1.0-merge-policy.md`). Working tree must be clean before starting.
- **No `git push`** for bodai without explicit user approval (`feedback-bodai-push-is-user-controlled.md`).
- **No version bumps** in any Bodai `pyproject.toml` — user does.
- **No `Co-Authored-By` trailer** (overrides system-reminder attribution; per `feedback-no-claude-code-coauthor-attribution.md`).
- **Git author**: `lesleslie <les@wedgwoodwebworks.com>` (NOT `.local`, NOT `wedghoodwebworks` — note the double-d).
- **No `kelp` / `webawesome` references anywhere** — including commit message body, comments, docstrings. README at `README.md:1140` is the only place these strings exist as legacy wording being cleaned up.
- **No `acb` references anywhere** — D2 catches any leftover.
- **Bare `pytest` resolves wrong venv** — use `.venv/bin/pytest` (per `bodai-pytest-binary-cwd.md`).
- **Wire-up contract** per `.claude/decisions/wire-up-contract.md` — every task carries an Integration Contract block.
- **`from __future__ import annotations`** as the first non-comment line of every source file.
- **Modern type syntax**: `X | None`, `list[str]`, `pathlib.Path`.
- **No `assert` in production code** (test files are idiomatic).
- **Use Oneiric logger** (`oneiric.logging`) — not stdlib `logging`, not `print()` in production code.
- **Use `git add -f` for blanket `.gitignore`** workaround (`.superpowers/` etc.) per `feedback-bodai-claude-decisions-gitignore-2026-09-26.md`.
- **All I/O in orchestration/framework code is async.** Sync only at CLI entry points and worker boundaries.
- **CLI short flags**: `typer.Option(...)` for default args in `mahavishnu/cli/`.
- **Traceable spec IDs (REQ-P2-X-NNN)** — per crackerjack-compliant-code convention. Production code references its REQ via one of:
  - **Inline marker (preferred):** `# req: REQ-P2-B1-001` (or comma-separated: `# req: REQ-P2-B1-001, REQ-P2-B1-002`)
  - **Docstring marker:** `# Implements: REQ-P2-B1-001` for class/function headers
  - **Test marker:** `@pytest.mark.req(["REQ-P2-B1-001"])` (registered via `pyproject.toml [tool.pytest] markers` — extend the existing `req` marker)
  Audit: `python scripts/audit_requirements.py --json` (or equivalent) checks for orphan/phantom refs. CI: weekly advisory run.
- **Type checker (ty)** — per crackerjack defaults. Use `# ty: ignore[<code>]` for specific suppressions. Mass suppressions (>5 in one file) are a smell — stop and audit.
- **Hard limits** (enforced by crackerjack): line-length 100, max-args 10, max-branches 15, max-returns 6, max-statements 55.

## 1. Outcome

- `fastblocks/starters/default/` exists with ~15 starter template files; `fastblocks create-app /tmp/test-app && cd /tmp/test-app && uv run fastblocks run` boots on `localhost:8000` with `/demo` returning an HTMX fragment.
- `examples/landing/` exists with 8 routes (per spec §B2); boots, all routes return 200, `/adapter-matrix` is auto-generated from Oneiric resolver and shows `✓`/`?` per adapter, `/performance` reads fresh benchmarks, `/demo` is search-as-you-type.
- `examples/htmy-hybrid/` exists with `/?render=<jinja|htmy|hybrid>` route producing semantically equivalent markup across all three render modes; snapshot tests pin all three.
- Sites/fastest retired per spec D0 convention (already committed in audit-pass).
- `.coverage-ratchet.json` floor stays at `67.81` (Phase 2 deliverables add tests, expected to push coverage up; gate does NOT need to be bumped in this plan — that's a separate coverage push).
- `examples/_drafts/` exists as the rollback sink per spec Integration Contract.
- All 3 deliverables coexist without `kelp`/`webawesome`/`acb` residue; D9 grep gates pass.

## 2. Goals

1. Land `fastblocks/starters/default/` with all files from spec §B1 file tree; default style is `fastblocks_ui` (NOT `vanilla`); kelp/webawesome/acb attempts fail loudly or are absent.
2. Land `examples/landing/` with all 8 routes from spec §B2; `/adapter-matrix` proves D3; `/performance` proves D7; `/security` proves D6; `/demo` exercises HTMX per D4+D5; theme discipline uses only `--ui-*` tokens + `[data-theme="dark"]` for dark variant.
3. Land `examples/htmy-hybrid/` with `/?render=<jinja|htmy|hybrid>` route + snapshot tests proving semantic equivalence.
4. Verify integration: each example boots independently; no shared `uv.lock` conflicts; no `kelp`/`webawesome`/`acb` strings anywhere (D9 grep).
5. Cookie-cutter CLI: `fastblocks create-app` emits the new starter (not a leftover one).

## 3. Non-Goals

- No coverage-floor bump from 67.81% → 85% (spec §D1 aspirational; separate workstream).
- No real auth adapter (skeleton only; per spec §B1 contract point 4).
- No real admin adapter (skeleton only).
- No WebSocket server in any deliverable.
- No multi-theme selector (single dark theme via `[data-theme="dark"]`; spec §B2 decision).
- No OOB helper added to `fastblocks/htmx.py` (spec §D4 option (b) chosen — round-trip test, no new feature).
- No SSE/WS HTMX extensions (`hx-ext="ws"`, `hx-ext="sse"`) — out of dogfood scope per spec §D4.
- No blog, no docs site, no user accounts, no analytics — explicitly out per spec §B2.
- No replacing existing framework features.
- No new adapters beyond what the starter uses.

## 4. Current Findings

- **No `fastblocks/starters/` directory exists** (verified `ls fastblocks/starters/` returns "No such file or directory"). `fastblocks/cli.py:928` has `def create_app` — Task 1 verifies whether it scaffolds from an embedded template or writes files inline.
- **`fastblocks-ui>=0.9,<0.10`** is the required dep in `pyproject.toml` (line 47) — already promoted to default per Phase 1A commit `fedbe65`.
- **HTMY adapter** at `fastblocks/adapters/templates/htmy.py` exists; HTMY components subsystem at `fastblocks/adapters/templates/htmy_components/` (with `adapter.py`, `base.py`, `layout/`, `ui/`).
- **Hybrid adapter** at `fastblocks/adapters/templates/hybrid.py` (`HybridTemplatesManager`) — already registered, resolves through Oneiric. B3's contribution is the first end-to-end `/?render=` parity demo, not the adapter itself.
- **`examples/`** currently contains only `websocket_client_examples.py` (a script, not a runnable app). Both `examples/landing/` and `examples/htmy-hybrid/` are net-new directories.
- **Settings pattern**: FastBlocks uses Python-based config (not YAML), routed through Oneiric. New examples need `oneiric_settings.yaml` per spec.
- **Tests use `.venv/bin/pytest`** (per Bodai `bodai-pytest-binary-cwd.md`); bare `pytest` resolves wrong venv.
- **No `examples/_drafts/` rollback sink** exists yet — Task 4 creates it.
- **Audit gate state** (per spec §Phase 1 → Phase 2 gate): D0–D9 all green at HEAD `869b044`. Phase 2 may begin.

## 5. Requirements

```yaml
requirements:
  - id: REQ-P2-B1-001
    title: "B1 starter template files exist with fastblocks-ui default style"
    dep: "fastblocks create-app → fastblocks/starters/default/"
  - id: REQ-P2-B1-002
    title: "B1 starter rejects kelp/webawesome with 'unknown style'"
    dep: "B1 → fastblocks UI primitive resolution"
  - id: REQ-P2-B1-003
    title: "B1 starter contains zero acb imports (D2 catch)"
    dep: "B1 → grep gate"
  - id: REQ-P2-B1-004
    title: "B1 starter skeleton auth adapter does NOT bind routes"
    dep: "B1 → consumer-app pattern (no auto-mount)"
  - id: REQ-P2-B1-005
    title: "fastblocks create-app CLI emits the new starter (cookie-cutter)"
    dep: "fastblocks/cli.py → fastblocks/starters/default/"
  - id: REQ-P2-B2-001
    title: "examples/landing/ boots and all 8 routes return 200"
    dep: "B2 routes + templates + adapters"
  - id: REQ-P2-B2-002
    title: "/adapter-matrix auto-generated from Oneiric resolver"
    dep: "B2 → Oneiric adapter discovery"
  - id: REQ-P2-B2-003
    title: "/performance renders fresh benchmarks from tests/perf/ artifacts"
    dep: "B2 → .benchmarks/ JSON"
  - id: REQ-P2-B2-004
    title: "Landing theme uses ONLY --ui-* tokens; no --fb-*/--fast-*/--brand-*/hex literals"
    dep: "B2 → fastblocks-ui token discipline"
  - id: REQ-P2-B2-005
    title: "Landing dark variant via [data-theme=\"dark\"] (no light-dark() function)"
    dep: "B2 → theming-recipes.md:59-69 closed decision"
  - id: REQ-P2-B2-006
    title: "No-claim-without-evidence lint passes (no 'lightning-fast'/'blazing'/'world-class' unbacked)"
    dep: "B2 → CI grep gate"
  - id: REQ-P2-B3-001
    title: "examples/htmy-hybrid/ boots; /?render=<jinja|htmy|hybrid> all return 200"
    dep: "B3 routes + 3 render modes"
  - id: REQ-P2-B3-002
    title: "All 3 render modes produce semantically equivalent markup (snapshot test)"
    dep: "B3 snapshot tests → fastblocks-ui greeting card primitives"
  - id: REQ-P2-B3-003
    title: "Hybrid adapter exercised end-to-end via /?render=hybrid path"
    dep: "B3 → fastblocks/adapters/templates/hybrid.py"
  - id: REQ-P2-INT-001
    title: "examples/_drafts/ rollback sink exists"
    dep: "Task 4 setup"
  - id: REQ-P2-INT-002
    title: "All 3 deliverables boot in isolation (smoke test)"
    dep: "Task 4 integration verification"
```

## 6. Implementation Tasks

### Task 1: B1 — New FastBlocks starter template

**Files (create — all under `fastblocks/starters/default/`):**
- `fastblocks/starters/default/pyproject.toml`
- `fastblocks/starters/default/.envrc`
- `fastblocks/starters/default/.gitignore`
- `fastblocks/starters/default/README.md`
- `fastblocks/starters/default/main.py`
- `fastblocks/starters/default/routes/__init__.py`
- `fastblocks/starters/default/routes/home.py`
- `fastblocks/starters/default/routes/demo.py`
- `fastblocks/starters/default/templates/base.html`
- `fastblocks/starters/default/templates/home.html`
- `fastblocks/starters/default/templates/demo.html`
- `fastblocks/starters/default/templates/partials/.gitkeep`
- `fastblocks/starters/default/adapters/templates.py`
- `fastblocks/starters/default/adapters/icons.py`
- `fastblocks/starters/default/adapters/fonts.py`
- `fastblocks/starters/default/adapters/style.py`
- `fastblocks/starters/default/adapters/auth.py` (skeleton; no routes)
- `fastblocks/starters/default/adapters/admin.py` (skeleton; no routes)
- `fastblocks/starters/default/settings/app.yaml`
- `fastblocks/starters/default/settings/adapters/templates.yaml`
- `fastblocks/starters/default/settings/adapters/style.yaml`
- `fastblocks/starters/default/settings/adapters/auth.yaml`
- `fastblocks/starters/default/settings/adapters/admin.yaml`
- `fastblocks/starters/default/settings/adapters/routes.yaml`
- `fastblocks/starters/default/static/css/app.css`
- `fastblocks/starters/default/static/img/.gitkeep`
- `fastblocks/starters/default/mcp/server.py` (optional, fold into this task)
- `fastblocks/starters/default/tests/conftest.py`
- `fastblocks/starters/default/tests/test_routes.py`
- `fastblocks/starters/default/tests/test_templates.py`
- `fastblocks/starters/default/tests/test_htmx.py`
- `fastblocks/starters/default/tests/test_adapter_boot.py`
- `fastblocks/starters/default/docs/ADAPTERS.md`

**Files (modify):**
- `fastblocks/cli.py` (verify `def create_app` at line 928 scaffolds from `fastblocks/starters/default/`)

**Files (test for the starter, in main repo):**
- `fastblocks/tests/cli/test_create_app_emits_default_starter.py` — verifies `fastblocks create-app` writes the new starter, not legacy.

#### Integration Contract

- **Triggered from**: User runs `fastblocks create-app <path>` in any directory.
- **Returns to**: New app at `<path>` matching the file tree above; `cd <path> && uv run fastblocks run` boots `localhost:8000` with `/demo` returning an HTMX fragment.
- **Demonstrable by**: `cd /tmp && fastblocks create-app test-app && cd test-app && uv run fastblocks run` succeeds; `pytest tests/cli/test_create_app_emits_default_starter.py` green.
- **Rollback signal**: `fastblocks create-app` fails or emits legacy scaffold → revert CLI change.
- **Observability added**: per-app `pytest --cov` reports in the scaffold; CLI logs file count.

- [ ] **Step 1: Read spec section for B1 file tree + contract points**

Read `docs/superpowers/specs/2026-09-27-fastblocks-dogfood-readiness-design.md` lines 189-238. Confirm the 4 contract points: (1) default style is `fastblocks_ui`, (2) kelp/webawesome fail loudly, (3) no acb imports, (4) skeleton auth adapter does NOT bind routes.

- [ ] **Step 2: Read existing `fastblocks/cli.py` `def create_app` (line 928)**

Understand whether `create_app` currently scaffolds from an embedded template string, copies from a directory, or writes files inline. This determines whether Step 7 changes `create_app` or just verifies it.

- [ ] **Step 3: Create the `fastblocks/starters/default/` directory tree**

```bash
mkdir -p fastblocks/starters/default/{routes,templates/partials,adapters,settings/adapters,static/{css,img},mcp,tests,docs}
touch fastblocks/starters/default/templates/partials/.gitkeep fastblocks/starters/default/static/img/.gitkeep
```

- [ ] **Step 4: Write starter `pyproject.toml`**

```toml
[project]
name = "{app_name}"
version = "0.1.0"
description = "FastBlocks app scaffolded by `fastblocks create-app`"
requires-python = ">=3.14"
dependencies = [
    "fastblocks>=0.24,<0.25",
    "fastblocks-ui>=0.9,<0.10",
    "oneiric>=0.21,<0.22",
]

[project.scripts]
fastblocks = "main:cli"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["."]
```

- [ ] **Step 5: Write starter `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/

# Oneiric
.oneiric/

# FastBlocks
.fastblocks/
*.log

# Env
.env
.env.local

# Editor
.vscode/
.idea/
.DS_Store
```

- [ ] **Step 6: Write starter `.envrc`**

```bash
# Oneiric env vars for local dev
export ONEIRIC__APP__NAME="{app_name}"
export ONEIRIC__APP__DEBUG="true"
export ONEIRIC__APP__STYLE="fastblocks_ui"
```

- [ ] **Step 7: Verify `fastblocks/cli.py create_app` uses `fastblocks/starters/default/`**

Open `fastblocks/cli.py` around line 928. If `create_app` reads from a hardcoded path or embedded string, change it to `Path(__file__).parent / "starters" / "default"`. If it already references a starter directory, verify it points at the new location.

- [ ] **Step 8: Write starter `main.py`**

```python
"""FastBlocks app entry point — scaffolded by `fastblocks create-app`.

ASGI-compatible; run with `uv run fastblocks run` (or `uvicorn main:app`).
"""
from __future__ import annotations

from fastblocks import FastBlocks
from fastblocks.adapters import register_default_adapters

from routes import register_routes


def create_app() -> FastBlocks:
    """Application factory — Oneiric resolves adapters via settings/."""
    app = FastBlocks()
    register_default_adapters(app)
    register_routes(app)
    return app


app = create_app()


def cli() -> None:
    """CLI entry — runs uvicorn against the ASGI app."""
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    cli()
```

- [ ] **Step 9: Write starter `routes/__init__.py`**

```python
from __future__ import annotations

from fastblocks import FastBlocks

from .demo import demo_route
from .home import home_route


def register_routes(app: FastBlocks) -> None:
    """Register all routes with the FastBlocks app."""
    app.add_route("/", home_route)
    app.add_route("/demo", demo_route)
```

- [ ] **Step 10: Write starter `routes/home.py`**

```python
from __future__ import annotations

from fastblocks import Request
from fastblocks.responses import HTMLResponse
from fastblocks_ui import shell, navbar, hero, ui_card, ui_button

from templates import render_template


async def home_route(request: Request) -> HTMLResponse:
    """Landing hero + 3-bullet 'why FastBlocks' + CTA."""
    context = {
        "shell": shell(),
        "navbar": navbar(is_sticky=True),
        "hero": hero(
            title="FastBlocks",
            subtitle="Async web framework on Starlette + HTMX",
            cta=ui_button(href="/demo", label="See it in action"),
        ),
        "cards": [
            ui_card(title="Async", body="Concurrent template rendering."),
            ui_card(title="Typed", body="Pydantic models + Oneiric config."),
            ui_card(title="Honest", body="No claim without a passing test."),
        ],
    }
    return HTMLResponse(await render_template("home.html", context))
```

- [ ] **Step 11: Write starter `routes/demo.py` (search-as-you-type)**

```python
from __future__ from __future__ import annotations

from fastblocks import Request
from fastblocks.responses import HTMLResponse, HTMXPartialResponse
from fastblocks_ui import ui_field, ui_input

from templates import render_template


async def demo_route(request: Request) -> HTMLResponse:
    """Search-as-you-type HTMX demo."""
    q = request.query_params.get("q", "")
    results = _fake_search(q) if q else []
    context = {
        "field": ui_field(label="Search", input=ui_input(name="q", value=q)),
        "results": results,
    }
    if request.headers.get("HX-Request"):
        return HTMXPartialResponse(await render_template("partials/results.html", context))
    return HTMLResponse(await render_template("demo.html", context))


def _fake_search(q: str) -> list[str]:
    """Placeholder search — replace with real query in consumer app."""
    corpus = ["alpha", "beta", "gamma", "delta", "fastblocks", "htmx", "htmy", "jinja2"]
    return [w for w in corpus if q.lower() in w][:5]
```

- [ ] **Step 12: Write starter `templates/base.html` (extends fastblocks-ui layout)**

```html
{% import "fastblocks_ui/macros.html" as ui %}
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8">
  <title>{{ app_name }}</title>
  <link rel="stylesheet" href="/static/css/app.css">
</head>
<body>
  {{ shell|raw }}
  {% block content %}{% endblock %}
  <script src="/static/js/htmx.min.js"></script>
</body>
</html>
```

- [ ] **Step 13: Write starter `templates/home.html` and `templates/demo.html`**

```html
{# home.html #}
{% extends "base.html" %}
{% block content %}
  {{ navbar|raw }}
  {{ hero|raw }}
  <main class="ui-section">
    {% for card in cards %}{{ card|raw }}{% endfor %}
  </main>
{% endblock %}
```

```html
{# demo.html #}
{% extends "base.html" %}
{% block content %}
  <main class="ui-section">
    {{ field|raw }}
    <div id="results"
         hx-get="/demo"
         hx-trigger="input changed delay:200ms from:input"
         hx-target="#results"
         hx-swap="innerHTML">
      {% if results %}
        <ul>{% for r in results %}<li>{{ r }}</li>{% endfor %}</ul>
      {% endif %}
    </div>
  </main>
{% endblock %}
```

- [ ] **Step 14: Write starter `templates/partials/results.html` (HTMX fragment)**

```html
{% if results %}
  <ul>{% for r in results %}<li>{{ r }}</li>{% endfor %}</ul>
{% else %}
  <p>No matches.</p>
{% endif %}
```

- [ ] **Step 15: Write starter `adapters/templates.py`, `icons.py`, `fonts.py`, `style.py`**

Each adapter file follows the Oneiric adapter pattern (extend `AdapterBase` or use `@adapter` decorator). Reference: `fastblocks/adapters/templates/jinja2.py` for the template adapter pattern. Use `fastblocks_ui` for the style adapter (not `vanilla`).

- [ ] **Step 16: Write starter `adapters/auth.py` and `adapters/admin.py` skeletons**

Both must NOT bind any routes (per contract point 4). Provide empty adapter classes that register through Oneiric but expose no URL surface.

- [ ] **Step 17: Write starter `settings/app.yaml` and `settings/adapters/*.yaml`**

```yaml
# settings/app.yaml
app:
  name: "{app_name}"
  style: "fastblocks_ui"
  debug: true
```

```yaml
# settings/adapters/style.yaml
adapters:
  style:
    default: "fastblocks_ui"
    available:
      - "fastblocks_ui"
      # NOTE: kelp and webawesome were removed in Phase 1A; DO NOT re-add here.
```

(Other settings files: minimal stubs that satisfy Oneiric's loader.)

- [ ] **Step 18: Write starter `static/css/app.css`**

Empty file or one-line placeholder (`/* app styles */`). The fastblocks-ui library provides the actual styles.

- [ ] **Step 19: Write starter `mcp/server.py` (read-only MCP introspection)**

Expose `list_routes` and `render_template` (read-only). Reference: `fastblocks/mcp/server.py` for the existing pattern.

- [ ] **Step 20: Write starter `tests/conftest.py`, `test_routes.py`, `test_templates.py`, `test_htmx.py`, `test_adapter_boot.py`**

Follow the existing FastBlocks test patterns. Each test boots the app via `create_app()` and asserts one route or behavior.

- [ ] **Step 21: Write starter `docs/ADAPTERS.md`**

```markdown
# Adapter Reference

This app uses the following FastBlocks adapters:
- Templates: Jinja2 (via `fastblocks/adapters/templates/jinja2.py`)
- Style: fastblocks-ui (default; see `fastblocks-ui/docs/usage.md`)
- Icons: configurable (one default set registered in `adapters/icons.py`)
- Fonts: squirrel (via `fastblocks/adapters/fonts/squirrel.py`)
- Middleware: Brotli, CSRF, security headers (registered in `main.py`)

For full adapter docs, see `docs/adapters/` in the FastBlocks framework repo.
```

- [ ] **Step 22: Write `fastblocks/tests/cli/test_create_app_emits_default_starter.py`**

```python
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def test_create_app_emits_new_starter(tmp_path: Path) -> None:
    """`fastblocks create-app` must scaffold from fastblocks/starters/default/."""
    subprocess.run(
        ["uv", "run", "fastblocks", "create-app", str(tmp_path / "test-app")],
        check=True, cwd=Path("/Users/les/Projects/fastblocks"),
    )
    target = tmp_path / "test-app"
    assert (target / "pyproject.toml").exists()
    assert (target / "main.py").exists()
    assert (target / "routes" / "home.py").exists()
    assert (target / "adapters" / "style.py").exists()
    # Default style is fastblocks_ui, NOT vanilla.
    text = (target / "settings" / "app.yaml").read_text()
    assert "fastblocks_ui" in text
    assert "kelp" not in text
    assert "webawesome" not in text
    # No acb imports.
    for py in target.rglob("*.py"):
        assert "import acb" not in py.read_text()
        assert "from acb" not in py.read_text()
```

- [ ] **Step 23: Run starter tests**

```bash
cd /Users/les/Projects/fastblocks
.venv/bin/pytest tests/cli/test_create_app_emits_default_starter.py -v
```

Expected: PASS.

- [ ] **Step 24: Boot the starter end-to-end**

```bash
cd /Users/les/Projects/fastblocks
uv run fastblocks create-app /tmp/test-app
cd /tmp/test-app
uv run fastblocks run &
SERVER_PID=$!
sleep 3
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/        # expect 200
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/demo    # expect 200
curl -s -H "HX-Request: true" "http://localhost:8000/demo?q=fast" | grep -q "fastblocks"  # expect match
kill $SERVER_PID
```

Expected: 200/200/match.

- [ ] **Step 25: Run full crackerjack gate**

```bash
crackerjack run -v
```

Expected: green.

- [ ] **Step 26: Commit (single commit covers all starter files)**

```bash
cd /Users/les/Projects/fastblocks
git add fastblocks/starters/default/ fastblocks/cli.py fastblocks/tests/cli/test_create_app_emits_default_starter.py
git commit -m "feat(fastblocks): B1 default starter template via fastblocks create-app"
```

### Task 2: B2 — FastBlocks landing page (`examples/landing/`)

**Files (create — all under `examples/landing/`):**
- `examples/landing/pyproject.toml`
- `examples/landing/.envrc`
- `examples/landing/.gitignore`
- `examples/landing/README.md`
- `examples/landing/main.py`
- `examples/landing/routes/__init__.py`
- `examples/landing/routes/home.py` (`/`)
- `examples/landing/routes/features.py` (`/features`)
- `examples/landing/routes/adapter_matrix.py` (`/adapter-matrix`)
- `examples/landing/routes/demo.py` (`/demo`, search-as-you-type HTMX)
- `examples/landing/routes/performance.py` (`/performance`)
- `examples/landing/routes/security.py` (`/security`)
- `examples/landing/routes/docs.py` (`/docs`)
- `examples/landing/routes/install.py` (`/install`)
- `examples/landing/templates/base.html`
- `examples/landing/templates/home.html`
- `examples/landing/templates/features.html`
- `examples/landing/templates/adapter_matrix.html`
- `examples/landing/templates/demo.html`
- `examples/landing/templates/performance.html`
- `examples/landing/templates/security.html`
- `examples/landing/templates/docs.html`
- `examples/landing/templates/install.html`
- `examples/landing/templates/partials/results.html`
- `examples/landing/adapters/templates.py`
- `examples/landing/adapters/style.py`
- `examples/landing/settings/app.yaml`
- `examples/landing/settings/adapters/templates.yaml`
- `examples/landing/settings/adapters/style.yaml`
- `examples/landing/settings/ui-theme.yaml`
- `examples/landing/tests/conftest.py`
- `examples/landing/tests/test_routes.py` (smoke per route)
- `examples/landing/tests/test_adapter_matrix.py` (regression)
- `examples/landing/tests/test_demo.py` (search-as-you-type interaction)
- `examples/landing/tests/test_performance_freshness.py`
- `examples/landing/tests/test_no_claim_without_evidence.py`

**Files (modify in main repo):**
- `README.md` — add link to `examples/landing/` in the "Examples" section.

#### Integration Contract

- **Triggered from**: User runs `cd examples/landing && uv run fastblocks run`.
- **Returns to**: Server on `localhost:8000` with all 8 routes returning 200; `/adapter-matrix` auto-generated; `/performance` shows fresh benchmarks.
- **Demonstrable by**: `pytest examples/landing/tests/ -v` green; manual curl per route returns 200.
- **Rollback signal**: any route returns 500 or `/adapter-matrix` doesn't match registered adapters → revert deliverable; if PR merged, audit `git grep examples/landing` for cross-references from `/features`, `/install`, README before deleting the directory.
- **Observability added**: per-route latency logged; `/adapter-matrix` shows live counts.

- [ ] **Step 1: Read spec section for B2 routes + theme**

Read `docs/superpowers/specs/2026-09-27-fastblocks-dogfood-readiness-design.md` lines 240-283. Confirm: 8 routes, theme discipline (`--ui-*` tokens only), dark via `[data-theme="dark"]`, no-claim-without-evidence lint.

- [ ] **Step 2: Set up `examples/landing/` skeleton**

```bash
mkdir -p examples/landing/{routes,templates/partials,adapters,settings,tests}
```

- [ ] **Step 3: Write `examples/landing/pyproject.toml`**

Same structure as B1 starter `pyproject.toml` (Step 4 of Task 1) but `name = "fastblocks-landing-example"` and `description = "Live dogfood demo of FastBlocks — landing page at examples/landing/"`.

- [ ] **Step 4: Write `examples/landing/.envrc`, `.gitignore`**

Same as B1 starter (Steps 5-6 of Task 1).

- [ ] **Step 5: Write `examples/landing/main.py`**

```python
from __future__ import annotations

from fastblocks import FastBlocks
from fastblocks.adapters import register_default_adapters

from routes import register_routes


def create_app() -> FastBlocks:
    app = FastBlocks()
    register_default_adapters(app)
    register_routes(app)
    return app


app = create_app()


def cli() -> None:
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)


if __name__ == "__main__":
    cli()
```

(Port 8001 — B1 starter uses 8000.)

- [ ] **Step 6: Write `examples/landing/routes/__init__.py`**

```python
from __future__ import annotations

from fastblocks import FastBlocks

from .adapter_matrix import adapter_matrix_route
from .demo import demo_route
from .docs import docs_route
from .features import features_route
from .home import home_route
from .install import install_route
from .performance import performance_route
from .security import security_route


def register_routes(app: FastBlocks) -> None:
    app.add_route("/", home_route)
    app.add_route("/features", features_route)
    app.add_route("/adapter-matrix", adapter_matrix_route)
    app.add_route("/demo", demo_route)
    app.add_route("/performance", performance_route)
    app.add_route("/security", security_route)
    app.add_route("/docs", docs_route)
    app.add_route("/install", install_route)
```

- [ ] **Step 7: Write `examples/landing/routes/home.py` (`/`)**

Renders hero, pitch, 3-bullet "Why FastBlocks," quick-start code block, CTA. Uses `shell()` + `navbar(is_sticky=True)` + `hero()` + `ui-card × 3` + `ui_button(CTA)` + `ui-measure(code block)`. Apply `.has-aurora` to hero (one per page, fail-closed under reduced motion per `prefers-reduced-motion`).

- [ ] **Step 8: Write `examples/landing/routes/features.py` (`/features`)**

Renders per-feature sections with `ui-section × N` + `ui-card per feature`. Apply `[data-reveal]` on cards (per-element IO observer, skipped under reduced motion).

- [ ] **Step 9: Write `examples/landing/routes/adapter_matrix.py` (`/adapter-matrix`) — **D3 proof surface**

```python
from __future__ import annotations

from fastblocks import Request
from fastblocks.responses import HTMLResponse
from oneiric.core.resolution import resolve_adapters

from templates import render_template


async def adapter_matrix_route(request: Request) -> HTMLResponse:
    """Auto-generated from Oneiric resolver; `✓` for boot-tested, `?` otherwise."""
    adapters = await resolve_adapters()
    rows = [
        {
            "name": a.name,
            "category": a.category,
            "boot_tested": _is_boot_tested(a),
            "stack_level": a.stack_level,
        }
        for a in adapters
    ]
    return HTMLResponse(await render_template("adapter_matrix.html", {"rows": rows}))


def _is_boot_tested(adapter) -> bool:
    """Return True iff `tests/adapters/<category>/<name>/test_boot.py` exists."""
    from pathlib import Path
    repo_root = Path("/Users/les/Projects/fastblocks")
    test_path = repo_root / "tests" / "adapters" / adapter.category / adapter.name / "test_boot.py"
    return test_path.exists()
```

Honest-by-construction: never mark `✓` without a passing boot test.

- [ ] **Step 10: Write `examples/landing/routes/demo.py` (`/demo`)**

Search-as-you-type HTMX (same pattern as B1 starter `routes/demo.py`). Uses `ui-field` + `ui-input` + HTMX fragment swap with stable IDs. Apply `[data-reveal]` on each successful swap.

- [ ] **Step 11: Write `examples/landing/routes/performance.py` (`/performance`) — **D7 proof**

```python
from __future__ import annotations

import json
from pathlib import Path

from fastblocks import Request
from fastblocks.responses import HTMLResponse

from templates import render_template


async def performance_route(request: Request) -> HTMLResponse:
    """Reads latest benchmark JSON from tests/perf/.benchmarks/."""
    benchmarks = _load_latest_benchmarks()
    return HTMLResponse(await render_template("performance.html", {"benchmarks": benchmarks}))


def _load_latest_benchmarks() -> list[dict]:
    bench_dir = Path("/Users/les/Projects/fastblocks/.benchmarks")
    if not bench_dir.exists():
        return []
    files = sorted(bench_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return []
    data = json.loads(files[0].read_text())
    return data.get("benchmarks", [])
```

Tabular content; no decoration.

- [ ] **Step 12: Write `examples/landing/routes/security.py` (`/security`)**

Threat model link, CVE status, security headers visible. Uses `ui-alert` per CVE status (`is-info`/`is-warning`/`is-danger` state modifiers per `theming-recipes.md` Accessible States palette) + `ui-card` per threat-model link. No decoration.

- [ ] **Step 13: Write `examples/landing/routes/docs.py` (`/docs`)**

Link to full docs. `ui-measure(code block)` + `ui_button(CTA)`.

- [ ] **Step 14: Write `examples/landing/routes/install.py` (`/install`)**

One-command install + 3-line hello-world. `ui-measure(code block)` + `ui_button(CTA)`.

- [ ] **Step 15: Write `examples/landing/templates/base.html`**

Extends fastblocks-ui layout. Theme via `settings/ui-theme.yaml`. Dark via `[data-theme="dark"]` (NOT `light-dark()`).

```html
{% import "fastblocks_ui/macros.html" as ui %}
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8">
  <title>FastBlocks — dogfood landing</title>
  <link rel="stylesheet" href="/static/css/landing.css">
</head>
<body>
  {{ shell|raw }}
  {% block content %}{% endblock %}
  <script src="/static/js/htmx.min.js"></script>
</body>
</html>
```

- [ ] **Step 16: Write `examples/landing/templates/home.html`, `features.html`, `adapter_matrix.html`, `demo.html`, `performance.html`, `security.html`, `docs.html`, `install.html`**

Each template extends `base.html` and uses fastblocks-ui primitives per spec §B2. **Discipline**: only `--ui-*` tokens; no `--fb-*`, `--fast-*`, `--brand-*`, or hex literals.

- [ ] **Step 17: Write `examples/landing/templates/partials/results.html` (HTMX fragment for `/demo`)**

```html
{% if results %}
  <ul>{% for r in results %}<li>{{ r }}</li>{% endfor %}</ul>
{% else %}
  <p>No matches.</p>
{% endif %}
```

- [ ] **Step 18: Write `examples/landing/settings/ui-theme.yaml`**

```yaml
ui_theme:
  tokens:
    --ui-color-primary: "#7c3aed"
    --ui-color-primary-hover: "#6d28d9"
    --ui-color-primary-active: "#5b21b6"
    --ui-radius-md: "0.5rem"
  dark:
    selector: '[data-theme="dark"]'
```

- [ ] **Step 19: Write `examples/landing/adapters/templates.py`, `style.py`**

Style adapter defaults to `fastblocks_ui`. Templates adapter uses Jinja2.

- [ ] **Step 20: Write `examples/landing/tests/conftest.py`**

Standard pytest fixture to boot the app: `from main import create_app; @pytest.fixture def client(): ...`

- [ ] **Step 21: Write `examples/landing/tests/test_routes.py` — smoke per route**

```python
import pytest


@pytest.mark.parametrize("path", [
    "/", "/features", "/adapter-matrix", "/demo",
    "/performance", "/security", "/docs", "/install",
])
def test_route_returns_200(client, path):
    response = client.get(path)
    assert response.status_code == 200
```

- [ ] **Step 22: Write `examples/landing/tests/test_adapter_matrix.py` — regression**

Asserts `/adapter-matrix` lists every currently-registered adapter from the Oneiric resolver. Mismatch fails CI.

- [ ] **Step 23: Write `examples/landing/tests/test_demo.py` — search-as-you-type interaction**

Asserts `curl -H "HX-Request: true" /demo?q=fast` returns HTMX fragment with `fastblocks` in result list.

- [ ] **Step 24: Write `examples/landing/tests/test_performance_freshness.py`**

Asserts `.benchmarks/` directory has at least one JSON file modified within the last 7 days (or skip with a clear message if no benchmarks yet).

- [ ] **Step 25: Write `examples/landing/tests/test_no_claim_without_evidence.py`**

```python
"""D9 no-claim-without-evidence lint.

Greps landing templates + README for marketing superlatives. If any are found
without a backing CI artifact (perf benchmark, audit dimension, test name),
the test fails.
"""
from __future__ import annotations

import re
from pathlib import Path

BACKED_CLAIMS = {
    "fast": ["test_performance_freshness", ".benchmarks/"],
    "secure": ["test_routes_returns_200", "middleware"],
    # kelp/webawesome removed (per Phase 1A); never appear here.
}

FORBIDDEN_PHRASES = ["lightning-fast", "blazing", "world-class", "blazingly fast"]


def test_no_unbacked_marketing_claims():
    landing_root = Path("/Users/les/Projects/fastblocks/examples/landing")
    for path in landing_root.rglob("*.html"):
        text = path.read_text().lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase in text:
                # If backed by an artifact, allow; else fail.
                if not any(art in str(landing_root) or art in text for art in BACKED_CLAIMS.get(phrase.split("-")[0], [])):
                    raise AssertionError(f"{path}: '{phrase}' has no backing CI artifact")
```

- [ ] **Step 26: Run landing tests**

```bash
cd /Users/les/Projects/fastblocks/examples/landing
.venv/bin/pytest tests/ -v
```

Expected: green.

- [ ] **Step 27: Boot landing manually; verify all 8 routes**

```bash
cd /Users/les/Projects/fastblocks/examples/landing
uv run fastblocks run &
SERVER_PID=$!
sleep 3
for path in / /features /adapter-matrix /demo /performance /security /docs /install; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8001$path")
  echo "$path → $code"
  [ "$code" = "200" ] || exit 1
done
kill $SERVER_PID
```

Expected: all 200.

- [ ] **Step 28: Theme discipline grep gate**

```bash
cd /Users/les/Projects/fastblocks/examples/landing
grep -rn -- "--fb-\|--fast-\|--brand-\|#[0-9a-fA-F]\{6\}" templates/ static/ && exit 1
echo "OK: no forbidden tokens"
```

Expected: empty output; exit 0.

- [ ] **Step 29: Update `README.md`**

Add a line under the Examples section: `- [Landing page dogfood demo](examples/landing/) — live audit surface`.

- [ ] **Step 30: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add examples/landing/ README.md
git commit -m "feat(fastblocks): B2 landing page at examples/landing/"
```

### Task 3: B3 — HTMY ↔ Jinja2 dual-render demo (`examples/htmy-hybrid/`)

**Files (create — all under `examples/htmy-hybrid/`):**
- `examples/htmy-hybrid/pyproject.toml`
- `examples/htmy-hybrid/.envrc`
- `examples/htmy-hybrid/.gitignore`
- `examples/htmy-hybrid/README.md`
- `examples/htmy-hybrid/main.py`
- `examples/htmy-hybrid/routes/__init__.py`
- `examples/htmy-hybrid/routes/greeting.py`
- `examples/htmy-hybrid/components/greeting_card.py` (HTMY component)
- `examples/htmy-hybrid/templates/base.html`
- `examples/htmy-hybrid/templates/greeting/jinja.html`
- `examples/htmy-hybrid/templates/greeting/_macros.html`
- `examples/htmy-hybrid/adapters/templates.py` (registers hybrid adapter)
- `examples/htmy-hybrid/settings/app.yaml`
- `examples/htmy-hybrid/settings/adapters/templates.yaml`
- `examples/htmy-hybrid/tests/test_render_jinja.py`
- `examples/htmy-hybrid/tests/test_render_htmy.py`
- `examples/htmy-hybrid/tests/test_render_hybrid.py`
- `examples/htmy-hybrid/tests/test_adapter_boot.py`

#### Integration Contract

- **Triggered from**: User runs `cd examples/htmy-hybrid && uv run fastblocks run` and visits `/?render=<jinja|htmy|hybrid>`.
- **Returns to**: All 3 render modes return 200 with semantically equivalent markup.
- **Demonstrable by**: `pytest examples/htmy-hybrid/tests/` green; manual curl shows identical DOM structure.
- **Rollback signal**: snapshot tests show semantic divergence → revert deliverable.
- **Observability added**: render-mode attribute on response; per-mode latency logged.

- [ ] **Step 1: Read spec section for B3**

Read `docs/superpowers/specs/2026-09-27-fastblocks-dogfood-readiness-design.md` lines 284-310.

- [ ] **Step 2: Set up `examples/htmy-hybrid/` skeleton**

```bash
mkdir -p examples/htmy-hybrid/{routes,components,templates/greeting,adapters,settings,tests}
```

- [ ] **Step 3: Write `examples/htmy-hybrid/pyproject.toml`**

Same structure as B1/B2 but `name = "fastblocks-htmy-hybrid-example"`.

- [ ] **Step 4: Write `examples/htmy-hybrid/.envrc`, `.gitignore`**

Same as B1/B2.

- [ ] **Step 5: Write `examples/htmy-hybrid/main.py`**

```python
from __future__ import annotations

from fastblocks import FastBlocks
from fastblocks.adapters import register_default_adapters

from routes import register_routes


def create_app() -> FastBlocks:
    app = FastBlocks()
    register_default_adapters(app)
    register_routes(app)
    return app


app = create_app()


def cli() -> None:
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)


if __name__ == "__main__":
    cli()
```

(Port 8002.)

- [ ] **Step 6: Write `examples/htmy-hybrid/routes/__init__.py`**

```python
from __future__ import annotations

from fastblocks import FastBlocks

from .greeting import greeting_route


def register_routes(app: FastBlocks) -> None:
    app.add_route("/", greeting_route)
```

- [ ] **Step 7: Write `examples/htmy-hybrid/components/greeting_card.py` (HTMY component)**

```python
"""Greeting card component — HTMY type-safe rendering."""
from __future__ import annotations

from dataclasses import dataclass

from htmy import Component, html


@dataclass(frozen=True, slots=True)
class GreetingCardProps:
    name: str
    avatar: str
    bio: str


class GreetingCard(Component):
    def __init__(self, props: GreetingCardProps) -> None:
        self.props = props

    def htmy(self) -> Component:
        p = self.props
        return html.div(
            class_="greeting-card",
            children=[
                html.img(src=p.avatar, alt=f"{p.name}'s avatar"),
                html.h2(children=p.name),
                html.p(children=p.bio),
                html.button(type="button", children="Follow"),
            ],
        )
```

- [ ] **Step 8: Write `examples/htmy-hybrid/templates/base.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>HTMY Hybrid Demo</title></head>
<body>
{% block content %}{% endblock %}
</body>
</html>
```

- [ ] **Step 9: Write `examples/htmy-hybrid/templates/greeting/jinja.html`**

```html
{% extends "base.html" %}
{% import "greeting/_macros.html" as m %}
{% block content %}
  {{ m.greeting_card(name="Ada Lovelace", avatar="/static/ada.png", bio="First programmer.") }}
{% endblock %}
```

- [ ] **Step 10: Write `examples/htmy-hybrid/templates/greeting/_macros.html`**

```html
{% macro greeting_card(name, avatar, bio) %}
<div class="greeting-card">
  <img src="{{ avatar }}" alt="{{ name }}'s avatar">
  <h2>{{ name }}</h2>
  <p>{{ bio }}</p>
  <button type="button">Follow</button>
</div>
{% endmacro %}
```

- [ ] **Step 11: Write `examples/htmy-hybrid/routes/greeting.py` (the dispatch route)**

```python
from __future__ import annotations

from fastblocks import Request
from fastblocks.responses import HTMLResponse, HTMXPartialResponse

from components.greeting_card import GreetingCard, GreetingCardProps


async def greeting_route(request: Request) -> HTMLResponse:
    """Renders the greeting card via the chosen renderer (?render=jinja|htmy|hybrid)."""
    mode = request.query_params.get("render", "hybrid")
    props = GreetingCardProps(name="Ada Lovelace", avatar="/static/ada.png", bio="First programmer.")
    if mode == "htmy":
        # HTMY direct render
        body = str(await _render_htmy(GreetingCard(props)))
    elif mode == "jinja":
        # Jinja2 template (jinja.html)
        body = await _render_jinja_template("greeting/jinja.html", {})
    else:
        # Hybrid: HTMY components composed with Jinja2 layout
        body = await _render_hybrid(props)

    if request.headers.get("HX-Request"):
        return HTMXPartialResponse(body)
    return HTMLResponse(body)


async def _render_htmy(component) -> str:
    """Render via HTMY directly."""
    from htmy import Renderer
    return await Renderer().render(component)


async def _render_jinja_template(name: str, context: dict) -> str:
    """Render via Jinja2 template."""
    from fastblocks.templates import get_template
    template = get_template(name)
    return await template.render_async(context)


async def _render_hybrid(props: GreetingCardProps) -> str:
    """Render via HybridTemplatesManager (HTMY component + Jinja2 layout)."""
    from fastblocks.adapters.templates.hybrid import HybridTemplatesManager
    manager = HybridTemplatesManager()
    return await manager.render_hybrid(GreetingCard(props), layout="base.html")
```

- [ ] **Step 12: Write `examples/htmy-hybrid/adapters/templates.py`**

```python
"""Registers hybrid adapter per spec §B3."""
from __future__ import annotations

from oneiric.adapters import adapter
from fastblocks.adapters.templates.hybrid import HybridTemplatesManager


@adapter(category="templates", name="hybrid", priority=100)
class HybridAdapterRegistration(HybridTemplatesManager):
    """Default hybrid adapter for the htmy-hybrid demo."""
    pass
```

- [ ] **Step 13: Write `examples/htmy-hybrid/settings/adapters/templates.yaml`**

```yaml
adapters:
  templates:
    default: "hybrid"
    available:
      - "hybrid"
      - "htmy"
      - "jinja2"
```

- [ ] **Step 14: Write `examples/htmy-hybrid/tests/test_render_jinja.py`**

```python
def test_jinja_render_returns_200(client):
    response = client.get("/?render=jinja")
    assert response.status_code == 200
    assert "greeting-card" in response.text
    assert "Ada Lovelace" in response.text
```

- [ ] **Step 15: Write `examples/htmy-hybrid/tests/test_render_htmy.py`**

```python
def test_htmy_render_returns_200(client):
    response = client.get("/?render=htmy")
    assert response.status_code == 200
    assert "greeting-card" in response.text
    assert "Ada Lovelace" in response.text
```

- [ ] **Step 16: Write `examples/htmy-hybrid/tests/test_render_hybrid.py`**

```python
def test_hybrid_render_returns_200(client):
    response = client.get("/?render=hybrid")
    assert response.status_code == 200
    assert "greeting-card" in response.text
    assert "Ada Lovelace" in response.text


def test_all_three_modes_semantically_equivalent(client):
    """All three render modes must produce semantically equivalent DOM."""
    responses = [
        client.get("/?render=jinja"),
        client.get("/?render=htmy"),
        client.get("/?render=hybrid"),
    ]
    # Strip the render-mode comment marker so the comparison is structural.
    texts = [
        r.text.replace("<!--render:jinja-->", "").replace("<!--render:htmy-->", "").replace("<!--render:hybrid-->", "")
        for r in responses
    ]
    # All three should contain the same greeting-card div with the same content.
    for text in texts:
        assert 'class="greeting-card"' in text
        assert "Ada Lovelace" in text
        assert "First programmer." in text
        assert "<button" in text
```

- [ ] **Step 17: Write `examples/htmy-hybrid/tests/test_adapter_boot.py`**

```python
def test_hybrid_adapter_boots_through_oneiric():
    """HybridTemplatesManager resolves through Oneiric resolver."""
    from fastblocks.adapters.templates.hybrid import HybridTemplatesManager
    from oneiric.core.resolution import resolve_adapter

    adapter = resolve_adapter(category="templates", name="hybrid")
    assert isinstance(adapter, HybridTemplatesManager)
```

- [ ] **Step 18: Run B3 tests**

```bash
cd /Users/les/Projects/fastblocks/examples/htmy-hybrid
.venv/bin/pytest tests/ -v
```

Expected: green.

- [ ] **Step 19: Boot B3 manually**

```bash
cd /Users/les/Projects/fastblocks/examples/htmy-hybrid
uv run fastblocks run &
SERVER_PID=$!
sleep 3
for mode in jinja htmy hybrid; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8002/?render=$mode")
  echo "render=$mode → $code"
  [ "$code" = "200" ] || exit 1
done
kill $SERVER_PID
```

Expected: all 200.

- [ ] **Step 20: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add examples/htmy-hybrid/
git commit -m "feat(fastblocks): B3 HTMY ↔ Jinja2 hybrid demo at examples/htmy-hybrid/"
```

### Task 4: Integration verification + rollback sink

**Files (create):**
- `examples/_drafts/README.md` (rollback sink per spec Integration Contract)
- `fastblocks/tests/examples/test_cross_deliverable.py` (cross-deliverable smoke tests)

#### Integration Contract

- **Triggered from**: After Tasks 1-3 land.
- **Returns to**: `examples/_drafts/` exists as rollback sink; cross-deliverable smoke tests pass.
- **Demonstrable by**: All 3 deliverables boot independently without port conflicts.
- **Rollback signal**: any deliverable fails to boot → move to `examples/_drafts/` (NOT delete).
- **Observability added**: cross-deliverable test report.

- [ ] **Step 1: Create `examples/_drafts/`**

```bash
mkdir -p /Users/les/Projects/fastblocks/examples/_drafts
```

- [ ] **Step 2: Write `examples/_drafts/README.md`**

```markdown
# Rollback Sink — `examples/_drafts/`

Per spec Integration Contract (Phase 2 build wave):

> "If Phase 2 reveals an audit gap, the affected dimension re-opens as Phase 1.5; the failing deliverable moves to `examples/_drafts/`, NOT shipped."

This directory is the rollback target. A failing deliverable (B1, B2, or B3) is moved here — NOT deleted — so the work is recoverable.

To rollback a deliverable:
1. `git mv examples/<deliverable> examples/_drafts/<deliverable>-<reason>-<date>`
2. Commit: `revert(<deliverable>): move to _drafts due to <reason>`
3. Open Phase 1.5 follow-up issue referencing the audit dimension that failed.
```

- [ ] **Step 3: Write `fastblocks/tests/examples/test_cross_deliverable.py`**

```python
"""Cross-deliverable smoke tests — verifies each example boots in isolation."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

EXAMPLES = [
    ("starter", Path("/tmp/test-app")),
    ("landing", Path("/Users/les/Projects/fastblocks/examples/landing")),
    ("htmy-hybrid", Path("/Users/les/Projects/fastblocks/examples/htmy-hybrid")),
]


@pytest.mark.parametrize("name,path", EXAMPLES)
def test_example_has_main_py(name: str, path: Path) -> None:
    assert (path / "main.py").exists(), f"{name}: missing main.py"


@pytest.mark.parametrize("name,path", EXAMPLES)
def test_example_has_tests_dir(name: str, path: Path) -> None:
    assert (path / "tests").is_dir(), f"{name}: missing tests/"


@pytest.mark.parametrize("name,path", EXAMPLES)
def test_example_no_kelp_webawesome_acb(name: str, path: Path) -> None:
    """D9 grep gate — must hold across all deliverables."""
    if not path.exists():
        pytest.skip(f"{name}: path does not exist (e.g. starter tested via CLI)")
    for py in path.rglob("*.py"):
        text = py.read_text()
        assert "kelp" not in text, f"{name}/{py}: contains 'kelp'"
        assert "webawesome" not in text, f"{name}/{py}: contains 'webawesome'"
        assert "import acb" not in text, f"{name}/{py}: contains 'import acb'"
        assert "from acb" not in text, f"{name}/{py}: contains 'from acb'"
```

- [ ] **Step 4: Run cross-deliverable smoke tests**

```bash
cd /Users/les/Projects/fastblocks
.venv/bin/pytest tests/examples/test_cross_deliverable.py -v
```

Expected: green.

- [ ] **Step 5: Run full crackerjack gate**

```bash
cd /Users/les/Projects/fastblocks
crackerjack run -v
```

Expected: green.

- [ ] **Step 6: Final whole-branch review**

Dispatch a subagent to review all Phase 2 commits since HEAD `869b044`. Lens:
- Spec compliance (B1/B2/B3 contract points)
- Quality (crackerjack clean, no kelp/webawesome/acb)
- Commit hygiene (author, no Co-Authored-By, direct to main)
- Wire-up contract (per-deliverable Integration Contracts honored)

- [ ] **Step 7: Commit integration verification**

```bash
cd /Users/les/Projects/fastblocks
git add examples/_drafts/ fastblocks/tests/examples/test_cross_deliverable.py
git commit -m "chore(fastblocks): Phase 2 build wave integration verification + rollback sink"
```

## 7. Required Code Changes

| File / Directory | Action | Phase task |
|---|---|---|
| `fastblocks/starters/default/` | CREATE (~30 files) | Task 1 |
| `fastblocks/cli.py` | MODIFY (verify `create_app` uses new starter) | Task 1 |
| `fastblocks/tests/cli/test_create_app_emits_default_starter.py` | CREATE | Task 1 |
| `examples/landing/` | CREATE (~25 files) | Task 2 |
| `README.md` | MODIFY (link to `examples/landing/`) | Task 2 |
| `examples/htmy-hybrid/` | CREATE (~17 files) | Task 3 |
| `examples/_drafts/README.md` | CREATE | Task 4 |
| `fastblocks/tests/examples/test_cross_deliverable.py` | CREATE | Task 4 |

## 8. Validation Matrix

| Tool / Command | Expected outcome | Evidence |
|---|---|---|
| `ls fastblocks/starters/default/` | non-empty | shell exit 0 |
| `fastblocks create-app /tmp/test-app && cd /tmp/test-app && uv run fastblocks run` | boots on :8000; `/` and `/demo` return 200 | curl exit 0 |
| `.venv/bin/pytest tests/cli/test_create_app_emits_default_starter.py -v` | PASS | pytest exit 0 |
| `ls examples/landing/` | non-empty | shell exit 0 |
| `cd examples/landing && uv run fastblocks run` | boots on :8001; all 8 routes return 200 | curl per route |
| `cd examples/landing && .venv/bin/pytest tests/ -v` | PASS | pytest exit 0 |
| `grep -rn -- "--fb-\|--fast-\|--brand-\|#[0-9a-fA-F]\{6\}" examples/landing/templates/ examples/landing/static/` | empty | shell exit 1 |
| `cd examples/htmy-hybrid && uv run fastblocks run` | boots on :8002; all 3 render modes return 200 | curl |
| `cd examples/htmy-hybrid && .venv/bin/pytest tests/ -v` | PASS (incl. semantic-equivalence snapshot) | pytest exit 0 |
| `ls examples/_drafts/` | README.md exists | shell exit 0 |
| `.venv/bin/pytest tests/examples/test_cross_deliverable.py -v` | PASS (3 deliverables × 3 assertions) | pytest exit 0 |
| `crackerjack run -v` | green | exit code 0 |
| `grep -rn "kelp\|webawesome" fastblocks/ examples/ README.md` | zero hits outside legacy-wording contexts | shell exit 1 |
| `grep -rn "import acb\|from acb" fastblocks/ examples/` | zero hits | shell exit 1 |
| `python -c "import examples.landing.main"` | imports clean | shell exit 0 |
| `python -c "import examples.htmy_hybrid.main"` | imports clean | shell exit 0 |

## 9. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| `fastblocks-ui` API surface has shifted since Phase 1A commit `fedbe65`; macros like `shell()`/`navbar()`/`hero()` no longer exist | Low | Step 7 of Task 1 + Steps 15-16 of Task 2 read existing fastblocks-ui usage in the repo (grep for `from fastblocks_ui import`) before committing template files; fall back to documented macro set per `fastblocks-ui/docs/usage.md` |
| Snapshot tests for `/?render=hybrid` flag latent issues in `HybridTemplatesManager` | Medium | Per spec §B3 — these become Phase 1.5 follow-ups, NOT Phase 2 scope creep |
| Coverage drops below 67.81% gate | Low | Each deliverable adds tests; expected to push coverage UP not down |
| `/adapter-matrix` regression test fails because boot-test layout changes | Medium | `_is_boot_tested` resolves path at test time, not config time; if tests dir moves, update both the boot-test locations AND this resolver |
| Phase 1 audit gates regress during Phase 2 implementation | Low | Task 4 Step 5 runs `crackerjack run -v` end-to-end |
| Starter auth/admin adapters accidentally bind routes (contract point 4 violation) | Low | Step 16 of Task 1 explicitly checks: adapter classes register but expose no URL surface |
| Landing's `/performance` fails when `.benchmarks/` is empty | Medium | Step 24 of Task 2 has freshness test that skips with clear message; Step 11 returns empty list, template renders an informational message |
| Theme discipline grep false positives on `url(#hex)` SVG references | Low | Task 2 Step 28 uses `#[0-9a-fA-F]\{6\}` regex; SVG `url(#gradient-id)` uses `#name` not `#hex`; false-positive only on 6-char hex literals in templates or static CSS |

## 10. Decision Rule

Phase 2 build wave is complete when ALL of:

- Tasks 1-4 land as 4 commits (or 4 atomic groups).
- `examples/landing/`, `examples/htmy-hybrid/`, and `fastblocks/starters/default/` all boot independently.
- All routes return 200; all 3 render modes produce semantically equivalent markup.
- `crackerjack run -v` green.
- D9 grep gates pass (no kelp/webawesome/acb anywhere).
- README.md links to `examples/landing/`.
- `examples/_drafts/README.md` exists as rollback sink.

**Release-train gate** (per spec §6.7 cross-initiative contract): user-controlled version bumps happen AFTER Phase 2 lands; user pushes to remote (no automated push).

## References

- `docs/superpowers/specs/2026-09-27-fastblocks-dogfood-readiness-design.md` — Phase 2 build wave spec (§B1, §B2, §B3)
- `docs/superpowers/specs/2026-09-27-fastblocks-dogfood-readiness-design.md` — Audit pass spec (§D0-D9)
- `docs/superpowers/specs/2026-09-27-fastblocks-phase1.5-plus-design.md` — Phase 1.5+ design (audit foundation)
- `.superpowers/sdd/2026-09-27-fastblocks-phase1.5-plus/progress.md` — Phase 1.5+ audit-clearance ledger
- `docs/superpowers/sdd-logs/2026-09-27-phase1.5-plus-ledger.md` — Archived Phase 1.5+ ledger
- `docs/superpowers/plans/2026-09-27-fastblocks-dogfood-readiness-audit-pass.md` — Plan 1 of 2 (audit pass; shipped)
- `fastblocks-ui/docs/usage.md` — fastblocks-ui macro surface (`shell`, `navbar`, `hero`, `ui-card`, etc.)
- `fastblocks-ui/docs/theming-recipes.md` lines 59-69 — dark variant closed decision (`[data-theme="dark"]`)
- `fastblocks-ui/docs/theming-recipes.md` line 109 — `--ui-*` token discipline
- `fastblocks/adapters/templates/jinja2.py` — Jinja2 adapter reference
- `fastblocks/adapters/templates/htmy.py` — HTMY adapter reference
- `fastblocks/adapters/templates/hybrid.py` — HybridTemplatesManager (B3 audit target)
- `fastblocks/htmx.py` lines 295-319 — HX-Trigger/HX-Redirect/HX-Location/HX-Push-URL (referenced by D4)
- `.claude/decisions/wire-up-contract.md` — Integration Contract rules
- `bodai-pre-1.0-merge-policy.md` — direct merge to main, no PR
- `feedback-no-claude-code-coauthor-attribution.md` — no Co-Authored-By trailer
- `feedback-bodai-push-is-user-controlled.md` — push is user-controlled
- `bodai-pytest-binary-cwd.md` — use `.venv/bin/pytest`, not bare `pytest`
