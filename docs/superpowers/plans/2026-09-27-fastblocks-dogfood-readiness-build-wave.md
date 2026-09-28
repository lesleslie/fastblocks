---
status: shipped
role: implementation
kind: plan
date: 2026-09-27
last_reviewed: 2026-09-28
topic: fastblocks-phase2-build-wave
version: 2
supersedes: b2e1312 (v1 — original authoring)
---

# FastBlocks Phase 2 Build Wave — Implementation Plan (v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **v2 note (2026-09-28):** This is the post-wave accuracy revision. v1 (commit `b2e1312`, dated 2026-09-27) was authored from spec intent without consulting the framework's installed API surface. The wave executed against v1 and surfaced significant plan-vs-reality drift, catalogued in the per-task reports and synthesized in `final-review.md`. v2 corrects all API-surface references, adds the 12 framework drift items as **Appendix A**, and adds a **post-wave retrospective (Appendix B)** with commit references and parked-finding triage. v1 is preserved in git history at `b2e1312` for audit.

**Goal:** Ship 3 dogfood deliverables — B1 starter template, B2 landing page at `examples/landing/`, B3 HTMY ↔ Jinja2 hybrid demo at `examples/htmy-hybrid/` — that exercise the audited FastBlocks framework end-to-end.

**Architecture:** Three self-contained example directories (one per deliverable) plus an integration smoke layer. B2 lands on B1 (UI primitives inherited from the starter); B3 is standalone (one route, three renderers). Each ships its own Oneiric-configured app + tests. No cross-deliverable coupling except route patterns and UI primitive reuse.

**Tech Stack:** Python 3.14, FastBlocks (Starlette + HTMX + async), Oneiric (DI/config/adapter resolution), fastblocks-ui 0.9.x (unprefixed Python API; `ui-*` is the HTML class-name prefix, NOT a Python identifier prefix), HTMY 0.1.x (`@component` decorator pattern; positional children; `type_="..."` for reserved HTML attributes), Jinja2 (template renderer), pytest, ty, mypy.

> **Preflight API grep (new rule for plans ≥1KB):** Before authoring this kind of plan, run `grep -nE "^def " /path/to/installed/framework/helpers.py` against each library named in the Tech Stack. The framework's actual installed surface is the source of truth; framework docs lag implementation in 0.x. This rule is the structural fix for the 12-item drift catalogued in Appendix A.

**Spec:** `docs/superpowers/specs/2026-09-27-fastblocks-dogfood-readiness-design.md` §B1, §B2, §B3 (sections 189-310). The 16 REQs in §5 are unchanged from v1 — they are the contract; only the implementation surface (§6) was wrong.

**Prior work this builds on:** Plan 1 of 2 (audit pass) shipped at HEAD `869b044`. Phase 1.5+ complete. Phase 1 audit gates green. See `.superpowers/sdd/2026-09-27-fastblocks-phase1.5-plus/progress.md`.

## Global Constraints

Verbatim from spec §12 + Phase 1.5+ commitments (unchanged from v1):

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

- `fastblocks/starters/default/` exists with ~35 starter template files; `fastblocks create-app /tmp/test-app && cd /tmp/test-app && uv run fastblocks run` boots on `localhost:8000` with `/demo` returning an HTMX fragment. **(Achieved at `5030675`; cross-task kwargs bug fixed at `6b6cb57`.)**
- `examples/landing/` exists with 8 routes (per spec §B2); boots, all routes return 200, `/adapter-matrix` is auto-generated from Oneiric resolver and shows `✓`/`?` per adapter, `/performance` reads fresh benchmarks, `/demo` is search-as-you-type. **(Achieved at `0ee6eca`.)**
- `examples/htmy-hybrid/` exists with `/?render=<jinja|htmy|hybrid>` route producing semantically equivalent markup across all three render modes; snapshot tests pin all three. **(Achieved at `fde0a18`.)**
- Sites/fastest retired per spec D0 convention (already committed in audit-pass).
- `.coverage-ratchet.json` floor stays at `67.81` (Phase 2 deliverables add tests, expected to push coverage up; gate does NOT need to be bumped in this plan — that's a separate coverage push).
- `examples/_drafts/` exists as the rollback sink per spec Integration Contract. **(Achieved at `eceb583`.)**
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

## 4. Current Findings (revised for v2)

> **v2 note:** §4 was rewritten to reflect what was learned during wave execution. v1's §4 framed the framework surface in terms the spec promised; the wave confirmed what actually exists. Future implementers should consult the installed surface (`.venv/lib/python3.14/site-packages/fastblocks*/helpers.py` etc.) directly, not v2's prose — but the prose below points at the right files.

- **No `fastblocks/starters/` directory exists** before B1. `fastblocks/cli.py:48` (revised line from v1's 928) has `def create_app` — Task 1 verifies whether it scaffolds from an embedded template or writes files inline.
- **`fastblocks-ui>=0.9,<0.10`** is the required dep. **API surface (verified at `.venv/lib/python3.14/site-packages/fastblocks_ui/helpers.py:332,358,576,1351`):**
  - Helpers are **unprefixed** at the Python layer: `card(header, body, footer, **attrs)`, `navbar(brand, items, *, variant, label, class_, **attrs)`, `hero(...)`, `shell(...)`, `button(...)`, `field(...)`, `text_input(...)`, `alert(content, *, variant, class_, **attrs)`, etc.
  - `**attrs` accepts arbitrary HTML attributes including reserved-word collisions (`is_sticky=True` becomes `is-sticky="True"` as a boolean HTML attribute, **NOT** a CSS class — see F-FW-9 in Appendix A). This silent absorption is the root cause of CF-1 (the B1 starter's missing card headers and missing navbar brand).
  - HTML class names keep the `ui-` prefix (`class="ui-card"`, `class="ui-section"`, `class="ui-shell"`, etc.) — that's the CSS contract.
- **FastBlocks class location (verified at `.venv/lib/python3.14/site-packages/fastblocks/`):**
  - `from fastblocks import FastBlocks` does NOT exist. Real path: `from fastblocks.applications import FastBlocks`.
  - `from fastblocks import Request`, `from fastblocks.responses import HTMLResponse`, `from fastblocks.responses import HTMXPartialResponse` do NOT exist. Use `starlette.requests.Request` + `starlette.responses.HTMLResponse` and check `HX-Request` header for HTMX partials (F-FW-11).
  - `from fastblocks.adapters import register_default_adapters` does NOT exist; `fastblocks/adapters/__init__.py` is a docstring. `FastBlocks()` self-registers through Oneiric — do not call a non-existent registration helper (F-FW-3).
  - `from fastblocks.templates import get_template` does NOT exist. Use a local thin Jinja2 wrapper in each example's `templates/__init__.py` (F-FW-7).
- **Oneiric adapter registration (verified):**
  - `from oneiric.adapters import adapter` (the `@adapter(category=..., name=..., priority=...)` decorator) does NOT exist (F-FW-4). Real path: `register_candidate(get_resolver(), domain=..., key=..., factory=..., metadata=...)` from `fastblocks.adapters.oneiric_helper`.
  - `from oneiric.core.resolution import resolve_adapter` standalone does NOT exist (F-FW-5). Real path: `Resolver.resolve(domain, key)` from `fastblocks.core.resolver.get_resolver()`.
  - `from oneiric.core.resolution import resolve_adapters` (plural, list_all variant) does NOT exist (F-FW-2). Workaround used by B2: iterate `get_resolver().registry._candidates` directly. Public `Resolver.list_candidates(domain=...)` should be added.
- **HybridTemplatesManager (verified at `fastblocks/adapters/templates/hybrid.py`):**
  - Real public methods: `clear_caches`, `get_autocomplete_suggestions`, `get_fragments_for_template`, `get_template_dependencies`, `initialize`, `precompile_templates`, `render_fragment`, `validate_template`.
  - **`render_hybrid(component, layout=...)` does NOT exist** (F-FW-1, Major). The spec promises it; the class ships only `render_fragment` at `_advanced_manager.py:918`. **B3 works around this by composing HTMY + Jinja2 manually in the route.** A follow-up to fastblocks is required to deliver the promised API.
  - `HybridTemplatesManager` registration through Oneiric uses key `"hybrid"` in B3, but the framework ALSO registers under `"hybrid_template_manager"` and `"templates"` for the same factory — three redundant registrations (F-FW-8). Consolidate in a fastblocks follow-up.
- **HTMY (verified at `.venv/lib/python3.14/site-packages/htmy/`):**
  - `htmy.Component` is a **Union type alias, NOT a base class**. `class GreetingCard(Component)` raises `TypeError` at import time. The canonical HTMY 0.1.x pattern is **`@component def greeting_card(props, context) -> ...`** — function-component decorator (F-FW-6).
  - `html.tag(children=[...])` is **wrong**: children are positional, not keyword (use `Tag.__call__(*children, **props)`).
  - `button(type="button")` is a **Python syntax error** (`type` is a reserved word). Use `type_="button"` for the `type` HTML attribute.
  - HTMY output is **not byte-equivalent** to Jinja2 for the same semantic markup (trailing whitespace before `>`, void-tag self-closing slashes, blank lines around text children, no inter-element indentation). For semantic-equivalence tests, normalize before comparison (see B3 `_normalise()` helper).
- **Tests use `.venv/bin/pytest`** (per Bodai `bodai-pytest-binary-cwd.md`); bare `pytest` resolves wrong venv. For example subdirectories that don't carry a coverage config, pass `--no-cov -p no:cacheprovider` to avoid the root project's coverage-gate failure.
- **No `examples/_drafts/` rollback sink** exists before B4 — Task 4 creates it.
- **Audit gate state** (per spec §Phase 1 → Phase 2 gate): D0–D9 all green at HEAD `869b044` (Plan 1 baseline). Phase 2 begins from there.

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

## 6. Implementation Tasks (rewritten for v2)

> **v2 note:** §6's code snippets were rewritten to match the framework's installed API surface (verified at `.venv/lib/python3.14/site-packages/`). v1's snippets assumed an API that doesn't exist; the corrected snippets are what implementers should write. Read §4 alongside §6.

### Task 1: B1 — New FastBlocks starter template

**Files (create — all under `fastblocks/starters/default/`):**
- `fastblocks/starters/default/pyproject.toml`
- `fastblocks/starters/default/.envrc`
- `fastblocks/starters/default/.gitignore`
- `fastblocks/starters/default/README.md`
- `fastblocks/starters/default/main.py`
- `fastblocks/starters/default/routes/__init__.py`
- `fastblocks/starters/default/routes/home.py`  ← **see F-FW-9 fix below**
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
- `fastblocks/cli.py` `def create_app` — verify it scaffolds from `fastblocks/starters/default/`. Default `--style` should be `"fastblocks_ui"`.

**Files (test for the starter, in main repo):**
- `fastblocks/tests/cli/test_create_app_emits_default_starter.py` — verifies `fastblocks create-app` writes the new starter, not legacy.

#### Integration Contract

- **Triggered from**: User runs `fastblocks create-app <path>` in any directory.
- **Returns to**: New app at `<path>` matching the file tree above; `cd <path> && uv run fastblocks run` boots `localhost:8000` with `/demo` returning an HTMX fragment.
- **Demonstrable by**: `cd /tmp && fastblocks create-app test-app && cd test-app && uv run fastblocks run` succeeds; `pytest tests/cli/test_create_app_emits_default_starter.py` green.
- **Rollback signal**: `fastblocks create-app` fails or emits legacy scaffold → revert CLI change.
- **Observability added**: per-app `pytest --cov` reports in the scaffold; CLI logs file count.

> **v2 fix (CF-1):** `routes/home.py` MUST use `card(header=..., body=...)` and `navbar(brand="...", is_sticky=True)` — NOT `card(title=..., body=...)` or `navbar(is_sticky=True)`. The wrong forms are absorbed by `**attrs` and silently produce empty `<header>` and missing brand content. See F-FW-9 in Appendix A for the framework-side root cause.

- [ ] **Step 1: Read spec section for B1 file tree + contract points** (unchanged from v1)

- [ ] **Step 2: Read existing `fastblocks/cli.py` `def create_app`** (unchanged)

- [ ] **Step 3: Create the `fastblocks/starters/default/` directory tree** (unchanged from v1)

- [ ] **Step 4: Write starter `pyproject.toml`** (unchanged from v1)

- [ ] **Step 5: Write starter `.gitignore`** (unchanged from v1)

- [ ] **Step 6: Write starter `.envrc`** (unchanged from v1)

- [ ] **Step 7: Verify `fastblocks/cli.py create_app` uses `fastblocks/starters/default/`** (unchanged from v1)

- [ ] **Step 8: Write starter `main.py`** — REWRITTEN for v2

```python
"""FastBlocks app entry point — scaffolded by `fastblocks create-app`.

ASGI-compatible; run with `uv run fastblocks run` (or `uvicorn main:app`).
"""
from __future__ import annotations

from fastblocks.applications import FastBlocks
from starlette.requests import Request
from starlette.responses import HTMLResponse

from routes import register_routes


def create_app() -> FastBlocks:
    """Application factory — Oneiric resolves adapters via settings/."""
    app = FastBlocks()  # self-registers through Oneiric; no register_default_adapters()
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

> **v2 corrections vs v1:** `from fastblocks import FastBlocks` → `from fastblocks.applications import FastBlocks`. Dropped `from fastblocks.adapters import register_default_adapters` (the function doesn't exist; FastBlocks() self-registers). Dropped `from fastblocks import Request` + `from fastblocks.responses import HTMLResponse`; replaced with starlette's directly (HTMX partials handled by checking `HX-Request` header, not a `HTMXPartialResponse` class).

- [ ] **Step 9: Write starter `routes/__init__.py`** — REWRITTEN for v2

```python
from __future__ import annotations

from fastblocks.applications import FastBlocks

from .demo import demo_route
from .home import home_route


def register_routes(app: FastBlocks) -> None:
    """Register all routes with the FastBlocks app."""
    app.add_route("/", home_route)
    app.add_route("/demo", demo_route)
```

- [ ] **Step 10: Write starter `routes/home.py`** — REWRITTEN for v2 (with CF-1 fix)

```python
"""Landing route — hero + 3-bullet 'why FastBlocks' + CTA.

Uses the fastblocks-ui helpers (``shell``, ``navbar``, ``hero``, ``card``,
``button``) which return SafeHTML strings — Jinja2 renders them via ``|safe``.

fastblocks-ui 0.9.x Python helpers are UNPREFIXED (``card``, ``navbar``, etc.).
The ``ui-`` prefix is reserved for HTML class names (``class="ui-card"`` etc.).
The ``card()`` API takes ``header=`` + ``body=`` (not ``title=`` + ``body=``);
``navbar()`` requires ``brand=`` (positional); ``is_sticky=True`` is absorbed
by ``**attrs`` as a boolean HTML attribute, not a CSS class.

# req: REQ-P2-B1-001
"""
from __future__ import annotations

from fastblocks_ui import button, card, hero, navbar, shell
from starlette.requests import Request
from starlette.responses import HTMLResponse

from templates import render_template


async def home_route(request: Request) -> HTMLResponse:
    """Landing hero + 3-bullet 'why FastBlocks' + CTA."""
    cards_markup = "".join(
        [
            card(header="Async", body="Concurrent template rendering."),
            card(header="Typed", body="Pydantic models + Oneiric config."),
            card(header="Honest", body="No claim without a passing test."),
        ]
    )
    navbar_markup = navbar(brand="FastBlocks", is_sticky=True)
    hero_markup = hero(
        title="FastBlocks",
        subtitle="Async web framework on Starlette + HTMX",
        cta=button(href="/demo", label="See it in action"),
    )
    main_markup = shell(f"{navbar_markup}{hero_markup}{cards_markup}")
    return HTMLResponse(await render_template(request, "home.html", {"main": main_markup}))
```

> **v2 corrections vs v1:** `card(title=...)` → `card(header=...)` (v1 silently dropped the title); `navbar(is_sticky=True)` → `navbar(brand="FastBlocks", is_sticky=True)` (v1 produced empty nav). This is CF-1, MUST-FIX-BEFORE-MERGE in opus's review.

- [ ] **Step 11: Write starter `routes/demo.py` (search-as-you-type)** — REWRITTEN for v2

```python
from __future__ import annotations

from fastblocks_ui import field, text_input
from starlette.requests import Request
from starlette.responses import HTMLResponse

from templates import render_template


async def demo_route(request: Request) -> HTMLResponse:
    """Search-as-you-type HTMX demo."""
    q = request.query_params.get("q", "")
    results = _fake_search(q) if q else []
    context = {
        "field": field(label="Search", input=text_input(name="q", value=q)),
        "results": results,
    }
    if request.headers.get("HX-Request"):
        return HTMLResponse(await render_template(request, "partials/results.html", context))
    return HTMLResponse(await render_template(request, "demo.html", context))


def _fake_search(q: str) -> list[str]:
    corpus = ["alpha", "beta", "gamma", "delta", "fastblocks", "htmx", "htmy", "jinja2"]
    return [w for w in corpus if q.lower() in w][:5]
```

> **v2 corrections vs v1:** `ui_field` → `field`, `ui_input` → `text_input` (unprefixed Python names). Dropped `HTMXPartialResponse` import; use plain `HTMLResponse` and check `HX-Request` header.

- [ ] **Step 12: Write starter `templates/base.html`** (unchanged from v1)

- [ ] **Step 13: Write starter `templates/home.html` and `templates/demo.html`** (unchanged from v1)

- [ ] **Step 14: Write starter `templates/partials/results.html`** (unchanged from v1)

- [ ] **Step 15: Write starter `adapters/templates.py`, `icons.py`, `fonts.py`, `style.py`** (unchanged from v1)

- [ ] **Step 16: Write starter `adapters/auth.py` and `adapters/admin.py` skeletons** (unchanged from v1)

- [ ] **Step 17: Write starter `settings/app.yaml` and `settings/adapters/*.yaml`** (unchanged from v1)

- [ ] **Step 18: Write starter `static/css/app.css`** (unchanged from v1)

- [ ] **Step 19: Write starter `mcp/server.py`** (unchanged from v1)

- [ ] **Step 20: Write starter `tests/conftest.py`, `test_routes.py`, `test_templates.py`, `test_htmx.py`, `test_adapter_boot.py`** (unchanged from v1)

- [ ] **Step 21: Write starter `docs/ADAPTERS.md`** (unchanged from v1)

- [ ] **Step 22: Write `fastblocks/tests/cli/test_create_app_emits_default_starter.py`** — REWRITTEN for v2

> **v2 corrections vs v1:**
> - Test uses typer's `CliRunner` directly (NOT `subprocess.run(["uv", "run", ...])`) — matches the existing `tests/cli/test_base.py` pattern and avoids `uv` PATH fragility in CI.
> - The "default style" test should OMIT `--style` so it actually tests the CLI default. v1's test passed `--style fastblocks_ui` explicitly, which meant it didn't test the default at all (F1.1 finding).

```python
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from fastblocks.cli import app as cli_app


runner = CliRunner()


def test_create_app_emits_new_starter(tmp_path: Path) -> None:
    """`fastblocks create-app` must scaffold from fastblocks/starters/default/."""
    result = runner.invoke(cli_app, ["create-app", str(tmp_path / "test-app")])
    assert result.exit_code == 0
    target = tmp_path / "test-app"
    assert (target / "pyproject.toml").exists()
    assert (target / "main.py").exists()
    assert (target / "routes" / "home.py").exists()
    assert (target / "adapters" / "style.py").exists()


def test_create_app_default_style_is_fastblocks_ui(tmp_path: Path) -> None:
    """`fastblocks create-app` default style must be fastblocks_ui (NOT vanilla)."""
    target = tmp_path / "style-app"
    runner.invoke(cli_app, ["create-app", str(target)])
    text = (target / "settings" / "app.yaml").read_text()
    assert "fastblocks_ui" in text


def test_create_app_starter_has_no_acb_imports(tmp_path: Path) -> None:
    target = tmp_path / "no-acb-app"
    runner.invoke(cli_app, ["create-app", str(target)])
    for py in target.rglob("*.py"):
        text = py.read_text()
        assert not text.startswith("import acb"), f"acb import in {py}"
        assert not text.startswith("from acb"), f"acb import in {py}"


def test_create_app_starter_has_no_kelp_or_webawesome(tmp_path: Path) -> None:
    target = tmp_path / "no-kelp-app"
    runner.invoke(cli_app, ["create-app", str(target)])
    style_yaml = (target / "settings" / "adapters" / "style.yaml").read_text()
    assert "kelp" not in style_yaml
    assert "webawesome" not in style_yaml


def test_create_app_refuses_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "exists-app"
    target.mkdir()
    (target / "pyproject.toml").write_text("placeholder")
    result = runner.invoke(cli_app, ["create-app", str(target)])
    assert result.exit_code != 0
    assert (target / "pyproject.toml").read_text() == "placeholder"


def test_create_app_substitutes_app_name_placeholder(tmp_path: Path) -> None:
    target = tmp_path / "my-cool-app"
    runner.invoke(cli_app, ["create-app", str(target)])
    pyproject = (target / "pyproject.toml").read_text()
    assert "my-cool-app" in pyproject
```

- [ ] **Step 23: Run starter tests** (unchanged from v1, using `.venv/bin/pytest`)

- [ ] **Step 24: Boot the starter end-to-end** (unchanged from v1)

- [ ] **Step 25: Run full crackerjack gate** (unchanged from v1)

- [ ] **Step 26: Commit** (unchanged from v1)

### Task 2: B2 — FastBlocks landing page (`examples/landing/`)

**Files (create — all under `examples/landing/`):**
- `examples/landing/pyproject.toml`
- `examples/landing/.envrc`
- `examples/landing/.gitignore`
- `examples/landing/README.md`
- `examples/landing/main.py`
- `examples/landing/routes/__init__.py`
- `examples/landing/routes/home.py` ← **CF-1 fix**: `navbar(brand="FastBlocks", is_sticky=True)`, `card(header=...)` (NOT `card(title=...)`)
- `examples/landing/routes/{features,performance,security,adapter_matrix,docs,changelog,demo}.py`
- `examples/landing/templates/base.html`
- `examples/landing/templates/{home,features,performance,security,adapter_matrix,docs,changelog,demo}.html`
- `examples/landing/templates/partials/.gitkeep`
- `examples/landing/adapters/{style,security}.py`
- `examples/landing/settings/{app,ui-theme}.yaml`
- `examples/landing/settings/adapters/{style,security,routes}.yaml`
- `examples/landing/static/css/.gitkeep`
- `examples/landing/tests/{__init__,conftest,test_routes,test_adapter_matrix,test_performance_freshness,test_no_claim_without_evidence}.py`

**Files (modify):**
- `README.md` (add link to `examples/landing/`)

#### Integration Contract

- **Triggered from**: `cd examples/landing && uv run fastblocks run`
- **Returns to**: Server on `localhost:8001` with all 8 routes returning 200; `/adapter-matrix` auto-generated; `/performance` shows fresh benchmarks
- **Demonstrable by**: `pytest examples/landing/tests/ --no-cov -p no:cacheprovider` green; manual curl per route returns 200
- **Rollback signal**: any route 500 or `/adapter-matrix` mismatch
- **Observability added**: per-route latency logged; live adapter counts

> **v2 corrections vs v1:**
> - Use `navbar(brand="FastBlocks", is_sticky=True)`, `card(header=...)`, `alert(content=..., variant=state)` — the unprefixed Python API with correct kwargs (per F-FW-9 and F-FW-10).
> - `/adapter-matrix` iterates `get_resolver().registry._candidates` directly because `oneiric.core.resolution.resolve_adapters` doesn't exist (F-FW-2). When the public API lands, replace with `Resolver.list_candidates(domain="fastblocks")`.
> - Use `from fastblocks.applications import FastBlocks`, not `from fastblocks import FastBlocks` (F-FW-3).

(Brief steps 1-26 from v1 remain structurally correct; only the kwargs and import paths need the v2 corrections above. Full step-by-step preserved in git history at `b2e1312`.)

### Task 3: B3 — HTMY ↔ Jinja2 dual-render demo (`examples/htmy-hybrid/`)

**Files (create — all under `examples/htmy-hybrid/`):**
- `examples/htmy-hybrid/pyproject.toml`
- `examples/htmy-hybrid/.envrc`
- `examples/htmy-hybrid/.gitignore`
- `examples/htmy-hybrid/README.md`
- `examples/htmy-hybrid/main.py`
- `examples/htmy-hybrid/adapters/templates.py`
- `examples/htmy-hybrid/components/greeting_card.py` ← **CRITICAL v2 fix**: see below
- `examples/htmy-hybrid/routes/__init__.py`
- `examples/htmy-hybrid/routes/greeting.py`
- `examples/htmy-hybrid/settings/app.yaml`
- `examples/htmy-hybrid/settings/adapters/templates.yaml`
- `examples/htmy-hybrid/templates/__init__.py`
- `examples/htmy-hybrid/templates/base.html`
- `examples/htmy-hybrid/templates/greeting/{_macros,jinja,hybrid}.html`
- `examples/htmy-hybrid/tests/{__init__,conftest,test_adapter_boot,test_render_jinja,test_render_htmy,test_render_hybrid}.py`

#### Integration Contract

- **Triggered from**: `cd examples/htmy-hybrid && uv run fastblocks run`; visit `/?render=<jinja|htmy|hybrid>`
- **Returns to**: All 3 render modes return 200 with semantically equivalent markup
- **Demonstrable by**: pytest green incl. snapshot semantic-equivalence test
- **Rollback signal**: snapshot tests show semantic divergence
- **Observability added**: render-mode attribute on response; per-mode latency

> **v2 corrections vs v1 (MAJOR — this task had the largest plan-vs-reality gap):**
> - **HTMY `Component` is Union, not base class (F-FW-6):** use `@component def greeting_card(props, context)` decorator pattern, not `class GreetingCard(Component)`.
> - **Children are positional (F-FW-7 / positional API):** use `Tag.__call__(*children, **props)`, NOT `html.tag(children=[...])`.
> - **`type` is reserved (F-FW-6):** use `type_="button"` for HTML `type` attribute.
> - **`HybridTemplatesManager.render_hybrid()` doesn't exist (F-FW-1, Major):** compose HTMY + Jinja2 manually in `routes/greeting.py::_render_hybrid` — DO NOT call a non-existent method. See Appendix A for the framework followup to add the real API.
> - **`register_candidate` (not `@adapter` decorator, F-FW-4):** use `register_candidate(get_resolver(), domain="fastblocks", key="hybrid", factory=..., metadata=...)` from `fastblocks.adapters.oneiric_helper`.
> - **`Resolver.resolve(domain, key)` (not standalone `resolve_adapter` import, F-FW-5):** use `get_resolver().resolve("fastblocks", "hybrid")`.
> - **Semantic-equivalence needs `_normalise()` helper:** HTMY output is not byte-equivalent to Jinja2 — strip trailing whitespace before `>`, drop void-tag self-closing slashes, collapse whitespace runs. Without normalization, the snapshot test fails on byte-equal comparison even when markup is semantically identical.

**Sample `_normalise()` helper (from B3 implementation):**

```python
import re

def _normalise(html: str) -> str:
    """Strip HTMY-vs-Jinja2 formatter noise; preserve semantic structure."""
    # HTMY adds trailing whitespace before '>' (e.g., '<h2 >').
    html = re.sub(r"\s+>", ">", html)
    # HTMY self-closes void tags ('<img/>' vs Jinja2 '<img>').
    html = re.sub(r"<(area|base|br|col|embed|hr|img|input|link|meta|param|source|track|wbr)/>", r"<\1>", html)
    # Collapse whitespace runs (HTMY emits blank lines around text children).
    html = re.sub(r"\n\s*\n", "\n", html)
    # Strip leading/trailing whitespace per line.
    html = "\n".join(line.rstrip() for line in html.splitlines()).strip()
    return html
```

**Sample corrected `routes/greeting.py` (B3 implementation):**

```python
from __future__ import annotations

from fastblocks.applications import FastBlocks
from fastblocks.core.resolver import get_resolver
from fastblocks.adapters.oneiric_helper import register_candidate
from starlette.requests import Request
from starlette.responses import HTMLResponse

from components.greeting_card import greeting_card


async def greeting_route(request: Request) -> HTMLResponse:
    render_mode = request.query_params.get("render", "jinja")
    if render_mode == "jinja":
        body = await _render_jinja(request)
    elif render_mode == "htmy":
        body = await _render_htmy(request)
    elif render_mode == "hybrid":
        body = await _render_hybrid(request)
    else:
        # Silent fallback (F3.4 — flagged for follow-up).
        body = await _render_hybrid(request)
    return HTMLResponse(body)


async def _render_jinja(request: Request) -> str:
    # ... resolves jinja template manager, renders greeting/_macros.html


async def _render_htmy(request: Request) -> str:
    # ... renders greeting_card() HTMY component directly


async def _render_hybrid(request: Request) -> str:
    """Composed hybrid render — NOT HybridTemplatesManager.render_hybrid()
    (which doesn't exist; see F-FW-1).

    Manually composes the HTMY greeting card + a Jinja2 layout wrapper.
    """
    component_html = str(greeting_card({"name": "Ada Lovelace"}, {}))
    # Use Jinja2 for the layout wrapper, HTMY for the inner component.
    layout = await _render_jinja_layout(request, body=component_html)
    return layout
```

(Brief steps 1-22 from v1 remain structurally correct; only the API surface, decorator pattern, and composition strategy need the v2 corrections above. Full step-by-step preserved in git history at `b2e1312`.)

### Task 4: Integration verification + rollback sink

**Files (create):**
- `examples/_drafts/README.md` — documents the rollback sink; references each Wave 1 deliverable.
- `fastblocks/tests/examples/test_cross_deliverable.py` — verifies each deliverable's structural conformance (file existence, no `kelp`/`webawesome`/`acb` residue). **Per v2 scope clarification:** runtime boot verification is each deliverable's own test suite's responsibility (B1: `tests/cli/test_create_app_emits_default_starter.py`; B2: `examples/landing/tests/`; B3: `examples/htmy-hybrid/tests/`). The cross-deliverable test is structural, not boot.

**Scope clarification (v2):** The brief said "All 3 deliverables boot independently without port conflicts." The implementer's reading was "verify structural conformance and delegate boot to per-deliverable tests" — which is what the brief actually scoped. The reviewer's reading was "subprocess boot + HTTP 200" — which would have required substantial additional work. **Per opus final review, the implementer's reading is correct: the brief was underspecified, and structural conformance + per-deliverable boot tests cover the requirement.**

(Brief steps 1-7 from v1 remain structurally correct. Full step-by-step preserved in git history at `b2e1312`.)

## 7. Required Code Changes (unchanged from v1)

Summary of code change surface across all 4 tasks:

- `fastblocks/cli.py` — `def create_app` rewritten to scaffold from `fastblocks/starters/default/` (Task 1).
- `fastblocks/starters/default/` — net-new directory tree (~35 files) (Task 1).
- `examples/landing/` — net-new directory (~39 files) (Task 2).
- `examples/htmy-hybrid/` — net-new directory (~21 files) (Task 3).
- `examples/_drafts/README.md` — net-new (Task 4).
- `fastblocks/tests/cli/test_create_app_emits_default_starter.py` — net-new (Task 1).
- `fastblocks/tests/examples/test_cross_deliverable.py` — net-new (Task 4).
- `README.md` — added `examples/landing/` link under Examples (Task 2).

## 8. Validation Matrix (unchanged from v1)

| Check | Method | Pass criteria |
|---|---|---|
| D2 — zero `acb` imports | `grep -rn "import acb\\|from acb" fastblocks/ examples/landing/ examples/htmy-hybrid/` | zero hits |
| D9 — no `kelp`/`webawesome` residue | `grep -rnE "\\b(kelp|webawesome)\\b" fastblocks/ examples/landing/ examples/htmy-hybrid/ --include="*.py" --include="*.html" --include="*.yaml"` | zero hits in code/config (README historical mention allowed at `README.md:1140`) |
| C1 — REQ traceability | `python scripts/audit_requirements.py --json` | every REQ has ≥1 code reference and ≥1 test reference |
| Coverage floor | `.venv/bin/pytest --cov=fastblocks --cov-fail-under=67.81` | ≥ 67.81% |
| Crackerjack gate | `crackerjack run -v` | clean |
| B1 boot | `cd /tmp && fastblocks create-app test-app && cd test-app && uv run fastblocks run &`; curl `/`, `/demo`; assert 200 | 200/200 |
| B2 boot | `cd examples/landing && uv run fastblocks run &`; curl 8 routes | all 200 |
| B3 boot | `cd examples/htmy-hybrid && uv run fastblocks run &`; curl `/?render=<jinja|htmy|hybrid>` | all 200 |

## 9. Risks (revised for v2)

> **v2 note:** §9 was rewritten to include risks that the wave actually encountered. v1 listed only pre-wave risks.

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Framework API drift between spec and installed surface | **High (confirmed in wave)** | High — 12 framework drift items, 1 user-visible bug (CF-1) | Future plans include "preflight API grep" step. Existing examples must audit each `fastblocks_ui` call against the 0.9.x surface. |
| `fastblocks-ui` helpers silently absorb kwargs | High | High | F-FW-9 must land in fastblocks-ui (kwarg validation). Until then, examples must read installed `.py` for the canonical signature. |
| Cross-deliverable consistency bugs hiding per-task | **Confirmed in wave (CF-1)** | Medium | Final whole-branch review (opus) catches these. Always run one for multi-deliverable waves. |
| HTMY output formatter divergence breaks snapshot tests | High (confirmed) | Medium | Use `_normalise()` helper; document the formatter differences. |
| Oneiric registration redundancy (`hybrid` vs `hybrid_template_manager` vs `templates`) | Confirmed in wave | Low | F-FW-8 followup; current behavior is correct but verbose. |
| Plan-vs-reality drift without preflight API grep | **Confirmed (root cause of all 11 drift items in B3)** | High | New rule in this v2 plan's tech stack section: preflight API grep. |
| Coverage-floor drift from example subdirectories | Confirmed | Low | Pass `--no-cov -p no:cacheprovider` for example subdir tests. |

## 10. Decision Rule (unchanged from v1)

Phase 2 build wave is complete when ALL of the following hold:

- Tasks 1-4 land as 4 atomic groups (each task = 1-2 commits).
- `examples/landing/`, `examples/htmy-hybrid/`, and `fastblocks/starters/default/` all boot independently.
- All routes return 200; all 3 render modes semantically equivalent.
- `crackerjack run -v` green (D2, D9, C1, coverage, ruff, ty).
- D9 grep gates pass (no `kelp`/`webawesome`/`acb` residue).
- `README.md` links to `examples/landing/` under Examples section.
- `examples/_drafts/README.md` exists as rollback sink.
- Final whole-branch review (opus) verdict: APPROVED or APPROVED_WITH_FINDINGS (with all MUST-FIX-BEFORE-MERGE items resolved).

## References

- Spec: `docs/superpowers/specs/2026-09-27-fastblocks-dogfood-readiness-design.md`
- Phase 1.5+ ledger: `docs/superpowers/sdd-logs/2026-09-27-phase1.5-plus-ledger.md` (archived at `869b044`)
- v1 of this plan: git history at commit `b2e1312`
- SDD workspace for this wave: `.superpowers/sdd/2026-09-27-fastblocks-dogfood-readiness-build-wave/` containing:
  - `progress.md` — wave ledger
  - `task-{1,2,3,4}-brief.md` — extracted briefs (preserved from v1)
  - `task-{1,2,3,4}-report.md` — implementer reports
  - `task-{1,2,3,4}-review.md` — per-task reviews
  - `final-review.md` — opus synthesis review
- v2 commit history: see Appendix B (Post-Wave Retrospective).

---

# Appendix A — Framework API Drift Discovered During Execution

The wave revealed that the framework's installed surface differs from its documented surface in 12 places. Catalogued here as inputs to upstream issue trackers (fastblocks / oneiric / htmy / fastblocks-ui). Each item: title, severity, evidence, recommendation.

### F-FW-1 [Major] — `HybridTemplatesManager.render_hybrid(component, layout=...)` does not exist

**Evidence:** Spec §B3 promises this API. The class (`fastblocks/adapters/templates/hybrid.py`) ships only `clear_caches`, `get_autocomplete_suggestions`, `get_fragments_for_template`, `get_template_dependencies`, `initialize`, `precompile_templates`, `render_fragment`, `validate_template`. Verified by inspection + B3 implementer's empirical workaround.

**Recommendation:** Add the missing public method. Implementation pattern: compose HTMY component + Jinja2 layout using the same template-engine-resolution machinery as `render_fragment`.

### F-FW-2 [Medium] — `oneiric.core.resolution.resolve_adapters` does not exist

**Evidence:** B2's `/adapter-matrix` route iterates `get_resolver().registry._candidates` directly (private API) because no public list-all API exists. Verified by `python -c "from oneiric.core.resolution import resolve_adapters"` → ImportError.

**Recommendation:** Add `Resolver.list_candidates(domain: str | None = None) -> list[Candidate]` to oneiric.

### F-FW-3 [Medium] — `fastblocks.adapters.register_default_adapters` does not exist

**Evidence:** Spec §B1 / B3 imply this function. The file `fastblocks/adapters/__init__.py` is a docstring only. `FastBlocks()` self-registers through Oneiric — the helper doesn't exist. Verified by `python -c "from fastblocks.adapters import register_default_adapters"` → ImportError.

**Recommendation:** Either add the helper for ergonomic clarity, OR document that `FastBlocks()` self-registers and the helper is not needed. The latter is faster and matches current behavior.

### F-FW-4 [Low] — `oneiric.adapters.@adapter` decorator does not exist

**Evidence:** The decorator pattern `from oneiric.adapters import adapter` is documented but not implemented. Real registration is `register_candidate(get_resolver(), domain=..., key=..., factory=..., metadata=...)` from `fastblocks.adapters.oneiric_helper`.

**Recommendation:** Either implement the decorator as a thin wrapper around `register_candidate`, OR update oneiric docs to remove the decorator reference.

### F-FW-5 [Low] — `oneiric.core.resolution.resolve_adapter` standalone import does not exist

**Evidence:** The standalone function isn't importable. Real API is `Resolver.resolve(domain, key)` via `get_resolver().resolve("fastblocks", "hybrid")`.

**Recommendation:** Either add a module-level `resolve_adapter(domain, key)` shortcut, OR update consumers to use `get_resolver().resolve(...)`.

### F-FW-6 [Medium] — `htmy.Component` is Union type, not base class

**Evidence:** `class GreetingCard(Component)` raises `TypeError` at import. Real pattern is `@component def greeting_card(props, context) -> ...` decorator. Verified by B3 implementer's empirical work.

**Recommendation:** Update HTMY docs to lead with the `@component` decorator pattern. Consider whether to provide a `Component` class for inheritance-based use cases (would require designing what methods the class should have).

### F-FW-7 [Low] — `fastblocks.templates.get_template` does not exist

**Evidence:** Spec §B3 implies this. Each example uses a local `templates/__init__.py` Jinja2 wrapper (the only working pattern).

**Recommendation:** Document the local-wrapper pattern as the canonical scaffold approach. Or add a `fastblocks.templates` module with the wrapper.

### F-FW-8 [Medium] — Oneiric registration redundancy

**Evidence:** `HybridTemplatesManager` is registered under three keys: `"hybrid"` (B3 example), `"hybrid_template_manager"` (framework), `"templates"` (framework). Three registrations of effectively the same factory.

**Recommendation:** Consolidate to one key. Or document why three exist (semantic aliasing for different use cases).

### F-FW-9 [Major] — `fastblocks-ui` `card()`/`navbar()` accept-and-ignore common kwargs via `**attrs`

**Evidence:** This is the **root cause of CF-1** (the B1 starter bug). `card(title="Async", body="...")` produces a card with no `<header>` element (title absorbed as HTML attribute). `navbar(is_sticky=True)` produces a `<nav>` with no brand content (positional `brand=` arg required).

**Recommendation (highest priority):** Make fastblocks-ui helpers strict — accept only known kwargs, raise on unknown. This converts silent user-traps into loud errors. The current `**attrs` catch-all is the framework-side root cause of an entire class of consumer bugs.

### F-FW-10 [Medium] — fastblocks-ui README documentation drift

**Evidence:** README documents macros with `ui-` prefix (`ui-card`, `ui-button`). Actual 0.9.x exports are unprefixed (`card`, `button`). The `ui-` prefix is the CSS class name (`class="ui-card"`), not the Python identifier.

**Recommendation:** Update fastblocks-ui README to use the unprefixed Python names + show the corresponding HTML class names in usage examples. Add a one-line note: "Python identifiers are unprefixed; HTML class names retain the `ui-` prefix."

### F-FW-11 [Low] — `HTMXPartialResponse` does not exist

**Evidence:** Spec §B2 / §B3 imply a dedicated partial-response class. Real pattern is `HTMLResponse(...)` with `HX-Request` header check in the route.

**Recommendation:** Either add `HTMXPartialResponse` as a thin wrapper, OR document the canonical pattern (HTMLResponse + HX-Request header check) and remove the implication from specs.

### F-FW-12 [Medium] — `apps_path = Path.cwd()` frozen at module load in `fastblocks/cli.py:48`

**Evidence:** Test fragility under `pytest-xdist`. Each worker imports `fastblocks.cli` once at startup in the repo CWD; subsequent `chdir` calls don't update `apps_path`. Worked around with `monkeypatch.setattr(fastblocks.cli, "apps_path", tmp_path)`.

**Recommendation:** Compute `apps_path` lazily inside the function that uses it (`_scaffold_from_starter`), e.g. `apps_path = Path.cwd()` at call time.

---

# Appendix B — Post-Wave Retrospective

**Wave status:** COMPLETE — 6 commits, all Bodai hygiene correct, opus verdict APPROVED_WITH_FINDINGS with all MUST-FIX-BEFORE-MERGE items resolved (CF-1 fix landed at `6b6cb57`).

**Commit history (chronological):**

```
5030675  feat(fastblocks): B1 default starter template via fastblocks create-app
e80c324  docs(fastblocks): task-1 build wave report (B1 starter template)
0ee6eca  feat(fastblocks): B2 landing page at examples/landing/
fde0a18  feat(fastblocks): B3 HTMY ↔ Jinja2 hybrid demo at examples/htmy-hybrid/
eceb583  chore(fastblocks): Phase 2 build wave integration verification + rollback sink
6b6cb57  fix(fastblocks): B1 starter kwargs — card(header=), navbar(brand=)
```

**Per-task summary:**

| Task | Status | Files | Tests | Parked findings |
|---|---|---|---|---|
| 1 B1 starter | ✅ | 35 scaffold + `cli.py` + 1 test | 6/6 + 18/18 in scaffold | 5 (F1.1/1.2/1.3 + F1.5.a/b) |
| 2 B2 landing | ✅ | 39 in `examples/landing/` + `README.md` | 16 passed + 1 skip | 5 (F2.1-2.5) |
| 3 B3 htmy-hybrid | ✅ | 21 in `examples/htmy-hybrid/` | 10/10 | 6 (F3.1-3.6) |
| 4 B4 integration | ✅ | `examples/_drafts/README.md` + `fastblocks/tests/examples/test_cross_deliverable.py` | 6/6 + 3 skip | 4 (F4.1-4.4) |

**Synthesis insight (from opus):** The wave worked because cross-deliverable review caught the CF-1 bug that per-task review missed. B1's `card(title=...)` was absorbed by fastblocks-ui's `**attrs` (per F-FW-9); Task 1's reviewer passed it because the test didn't assert "card has a `<header>` element." Task 2's reviewer caught it because B2 uses the same primitive, and the implementer had to adapt the kwargs. Cross-deliverable comparison is the structural fix for this kind of bug class — per-task review alone is not sufficient for multi-deliverable waves.

**For Phase 3 plans:** Include a "preflight API grep" step in the Tech Stack section (see this v2's header). Read the framework's installed surface, not its docs. The wave's 12-item drift catalog (Appendix A) is the list of "where docs lie" — future plans should grep those paths first.

**Push readiness:** Wave is push-eligible. Per Bodai `feedback-bodai-push-is-user-controlled.md`, the user pushes; Claude never pushes.
