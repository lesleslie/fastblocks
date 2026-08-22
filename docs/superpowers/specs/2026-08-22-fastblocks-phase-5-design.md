---
status: accepted
role: phase-5-design-spec
date: 2026-08-22
last_reviewed: 2026-08-22
supersedes: null
superseded_by: null
decision_date: 2026-08-22
topic: phase-5-test-infrastructure-rebuild
---

# Phase 5: Test Infrastructure Rebuild Design

## Status

**Accepted** (Phase 5 spec — companion to master plan
`docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md`
§Pillar 6 line 174-180, §Phase 5 line 341, §Phase 5 verification line 464-479).

## Scope decision

Phase 5 delivers the master plan's Pillar 6 (line 174-180) and Phase 5 row
(line 341): "Test infrastructure rebuild." The master plan's verification
gate (line 464-479) lists 13 distinct verification items plus
`asyncio.TaskGroup` cancellation propagation (line 478); Phase 5 ships
**13 of 14** verification items, with the `asyncio.TaskGroup` item
deferred to Phase 6 (production migration not done — Phase 5 is
strictly tests-only).

**In scope:**

1. **`tests/strategies.py`** — 4 Hypothesis strategies (`safe_user_input`,
   `unsafe_input`, `attrs_dict`, `htmy_component`) consumed by 5B and 5C.
2. **Hypothesis profile mechanics** — `dev`/`ci`/`debug` profiles registered
   in `tests/conftest.py`, env-var selector (`HYPOTHESIS_PROFILE`).
3. **Two new shared fixtures** — `clean_axe_core_page` (function-scoped
   Playwright page), `fastblocks_test_app` (session-scoped FastBlocks app).
4. **Three new pytest markers** — `a11y`, `property`, `slow` (registered in
   `pyproject.toml`).
5. **Property-based tests for the style × renderer matrix** — 4 cells ×
   100 Hypothesis examples.
6. **HTMY XSS regression matrix** — all 34 absorbed components with
   per-field assertions covering master plan §C4's three attack classes.
7. **Jinja2 SSTI regression** — adversarial input alphabet; asserts no
   autoescape bypass in `{{ }}`, `[[ ]]`, `| safe` filters, `Markup`
   round-trip.
8. **HTMY `hx_*` kwargs contract** — JSON-encoded variants
   (`hx-vals`, `hx-headers`).
9. **MCP server integration canary** — 7-name tuple from
   `profiles.FASTBLOCKS_TOOLS` registers cleanly; each tool is callable.
10. **axe-core a11y on 34 components** — 0 violations of color-contrast,
    label, button-name, link-name, image-alt, aria-roles.
11. **CSRF + HTMX integration** — 4 scenarios (no token → 403, valid
    header → 200, form field fallback → 200, expired token → 403).
12. **Static files test** — cache headers + brotli.
13. **Lifecycle integration** — `app.state.main_loop` + `app.state.jinja_env`
    bound at startup.
14. **Coverage ratchet** — bumped from 55.05% baseline to **65%**.

**Out of scope:**

- **`asyncio.TaskGroup` cancellation propagation** (master plan line 478) —
  Phase 6 ships the production migration first.
- **Coverage ratchet beyond 65%** — Phase 6's observability work lifts it
  further (master plan line 653 target is 70%; we stop at 65%).
- **Cross-Bodai-repo MCP canary** — only tests fastblocks's MCP server,
  not SplashStand's embedding of fastblocks.
- **HTMY XSS for Jinja2-rendered components** — Jinja2 doesn't have
  absorbed components; only HTMY does.
- **Production code changes** — Phase 5 is strictly tests-only per the
  user's "strict tests-only" decision.

## Why Phase 5 decomposes as Foundation → Matrix → Adversarial

Phase 5's master-plan verification gate is large (14 items). A monolithic
design risks the same multi-agent review surface that surfaced 5 P0
blockers on Phase 4 (deferred per `docs/adr/0011-phase-4-deferral.md`). The
decomposition is **structural, not by item-count**: each sub-phase has
clear prerequisites from the prior sub-phase, and a reviewer can approve
5A without needing to read 5B.

| Sub-phase | Deliverable | Hard dependency |
|---|---|---|
| **5A** Foundation | `tests/strategies.py`, Hypothesis profiles, fixtures, markers, zero-collection-error verification | None |
| **5B** Matrix coverage | Property-based matrix (4 cells × 100), HTMY XSS (34 components), Jinja2 SSTI, hx_* kwargs | 5A's `tests/strategies.py` |
| **5C** Adversarial integration | MCP canary, axe-core on 34, CSRF+HTMX, static files, lifecycle | 5A's `fastblocks_test_app` fixture |

**Why this ordering matters**: 5A ships the shared infrastructure (strategies,
fixtures, profiles) that 5B and 5C consume. If we discovered mid-5B that
strategies.py needs a different shape, we wouldn't have to redo 5C. The
ordering minimizes the "trough of wasted work" — each sub-phase uses the
prior sub-phase's output as a stable foundation.

## Architecture

Three layers, with `tests/strategies.py` as the shared root.

### Layer 1 — Foundation (`tests/strategies.py`)

Per master plan line 469, single top-level file with 4 custom strategies.

| Strategy | Built from | Consumers |
|---|---|---|
| `safe_user_input` | `st.text` with HTML-safe alphabet (Lu/Ll/Nd/Pc/Pd/Zs) | 5B matrix; 5C axe-core attributes |
| `unsafe_input` | `st.one_of(ssti_payloads_corpus, st.text)` — 15+ SSTI vectors from `tests/xss/ssti_payloads.json` plus random text with Po chars | 5B Jinja2 SSTI; 5B HTMY XSS matrix |
| `attrs_dict` | `st.dictionaries` over **21 whitelisted HTMY attribute names** × `safe ∪ unsafe` | 5B HTMY XSS matrix |
| `htmy_component` | `st.one_of(*st.builds(c, **field_strategies) for c in ABSORBED_COMPONENTS)` | 5B XSS matrix |

**Whitelisted attrs** (21 names): class, id, role, tabindex, data-test,
data-id, data-state, aria-label, aria-hidden, aria-expanded,
aria-controls, hx-get, hx-post, hx-target, hx-trigger, hx-swap, hx-vals,
hx-headers, hx-include, hx-confirm, name, value, type, placeholder,
title. (Counted at 21 by hand; §attrs_dict test asserts exact count.)

The whitelist covers master plan §C4's three attack classes:
- (a) attrs dict-key escaping — per-field dict assertions.
- (b) CSS-context vectors — `unsafe_input`'s Punctuation-other chars
  (`"`, `'`, `;`, `{}`, `()`).
- (c) aria-* attribute injection — `attrs_dict`'s whitelisted aria-* keys
  with unsafe values.

### Layer 2 — Matrix coverage (`tests/templates/`, `tests/xss/`, `tests/adapters/templates/`)

5B tests consume `tests/strategies.py` and exercise the style × renderer
matrix plus the security matrices.

### Layer 3 — Adversarial integration (`tests/mcp/`, `tests/a11y/`, `tests/integration/`)

5C tests use the `fastblocks_test_app` fixture and exercise cross-cutting
integration paths: MCP server, accessibility, CSRF, static files,
lifespan.

## Sub-phase 5A — Test infrastructure foundation

### 5A.1 — Strategy module (`tests/strategies.py`)

The strategy file's shape:

```python
"""Phase 5 Hypothesis strategies — shared between 5B and 5C tests.

Custom strategies for property-based testing across the style × renderer
matrix and the XSS regression matrix.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hypothesis import strategies as st

if TYPE_CHECKING:
    pass  # htmy_component imports ABSORBED_COMPONENTS lazily


# Curated SSTI + script payloads from tests/xss/ssti_payloads.json (15+ vectors)
_UNSAFE_PAYLOADS: tuple[str, ...] = (
    "{{7*7}}", "${7*7}", "#{7*7}}", "<%= 7*7 %>",
    "{{config.__class__.__init__.__globals__['os'].popen('id').read()}}",
    "${T(java.lang.Runtime).getRuntime().exec('id')}",
    "<script>alert(1)</script>",
    "\"><script>alert(1)</script>",
    "javascript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "<svg onload=alert(1)>",
    "'-alert(1)-'",
    "\"; alert(1); //",
    "{{request.application.__globals__.__builtins__.__import__('os').popen('id').read()}}",
)

_HTML_SAFE_CHARS = st.characters(
    whitelist_categories=("Lu", "Ll", "Nd", "Pc", "Pd", "Zs"),
    max_codepoint=0xFFFF,
)
_UNSAFE_CHARS = st.characters(
    whitelist_categories=("Lu", "Ll", "Nd", "Pc", "Pd", "Zs", "Po"),
    blacklist_characters=("\n", "\r", "\x00"),
)

safe_user_input: st.SearchStrategy[str] = st.text(
    alphabet=_HTML_SAFE_CHARS, min_size=0, max_size=200,
)

unsafe_input: st.SearchStrategy[str] = st.one_of(
    st.sampled_from(_UNSAFE_PAYLOADS),
    st.text(alphabet=_UNSAFE_CHARS, min_size=1, max_size=200),
)

attrs_dict: st.SearchStrategy[dict[str, str]] = st.dictionaries(
    keys=st.sampled_from([
        "class", "id", "role", "tabindex",
        "data-test", "data-id", "data-state",
        "aria-label", "aria-hidden", "aria-expanded", "aria-controls",
        "hx-get", "hx-post", "hx-target", "hx-trigger", "hx-swap",
        "hx-vals", "hx-headers", "hx-include", "hx-confirm",
        "name", "value", "type", "placeholder", "title",
    ]),
    values=st.one_of(safe_user_input, unsafe_input),
    max_size=10,
)


def htmy_component() -> st.SearchStrategy:
    """Strategy that yields an instance of one of the 34 absorbed HTMY components."""
    import dataclasses
    from fastblocks.adapters.templates.htmy_components import ABSORBED_COMPONENTS

    return st.one_of(*[
        st.builds(component, **{
            f.name: _infer_strategy(f.type)
            for f in dataclasses.fields(component)
        })
        for component in ABSORBED_COMPONENTS
        if dataclasses.is_dataclass(component)
    ])


def _infer_strategy(type_hint: type) -> st.SearchStrategy:
    """Map a dataclass field's type hint to a Hypothesis strategy."""
    if type_hint is str:
        return st.one_of(safe_user_input, unsafe_input)
    if type_hint is int:
        return st.integers(min_value=0, max_value=10_000)
    if type_hint is bool:
        return st.booleans()
    return safe_user_input  # fallback for unknown types
```

**One decision point**: the strategy file is **flat** (`tests/strategies.py`)
rather than a package (`tests/strategies/__init__.py`). The flat form is
sufficient for 4 strategies; a package is overkill until we cross ~10
strategies.

**Why `htmy_component()` is a function, not a module-level strategy**:
lazy import of `ABSORBED_COMPONENTS` avoids the import chain
`tests → fastblocks.adapters.templates.htmy_components → ...` causing
collection errors if `htmy_components` is in a broken state. The function
form defers the import to test execution time.

### 5A.2 — Hypothesis profile mechanics

`tests/conftest.py` adds:

```python
import os
from hypothesis import settings, Verbosity

HYPOTHESIS_PROFILE = os.environ.get("HYPOTHESIS_PROFILE", "ci")

settings.register_profile("dev",   max_examples=10,  deadline=None, derandomize=False, verbosity=Verbosity.normal)
settings.register_profile("ci",    max_examples=100, deadline=None, derandomize=False, verbosity=Verbosity.normal)
settings.register_profile("debug", max_examples=1,   deadline=None, derandomize=True,  verbosity=Verbosity.verbose)
settings.load_profile(HYPOTHESIS_PROFILE)
```

Per master plan line 469: `max_examples=100, deadline=None, derandomize=False`.
Per pytest-hypothesis-specialist audit (line 468): `derandomize=True` is a
debugging helper, NOT a CI-stability feature.

### 5A.3 — Two new shared fixtures

| Fixture | Scope | Purpose |
|---|---|---|
| `clean_axe_core_page` | function | Fresh Playwright page per test; closes browser context on teardown. Function scope is mandatory — Playwright pages aren't safe to share across tests. |
| `fastblocks_test_app` | session | Builds a minimal FastBlocks app once per session; reused by CSRF, static-files, lifecycle, MCP canary. Cuts setup overhead from 4× ~5s to 1× ~5s. |

The existing `clean_resolver` fixture (Phase 1.5, master plan line 296)
is unchanged. No conftest pollution beyond what's listed.

### 5A.4 — Three new markers

`pyproject.toml` updated:

```toml
[tool.pytest.ini_options]
markers = [
    # ... existing markers from CLAUDE.md ...
    "a11y: axe-core integration tests (requires Playwright browser)",
    "property: Hypothesis property-based tests",
    "slow: tests skipped in fast CI (full Hypothesis max_examples=100 + full axe-core on 34 components)",
]
```

| Marker | Applied to |
|---|---|
| `a11y` | `tests/a11y/test_components_a11y.py` |
| `property` | `tests/templates/test_style_renderer_property.py`, `tests/xss/test_htmy_component_xss_matrix.py` |
| `slow` | Axe-core on 34 components + property-based at max-100 |

## Sub-phase 5B — Matrix coverage

### 5B.1 — Style × renderer matrix (4 cells, 100 examples each)

Per master plan line 469: "Hypothesis property-based test for every cell
of the style × renderer matrix."

| Cell | style | renderer | What it tests |
|---|---|---|---|
| 1 | vanilla | jinja2 | Vanilla CSS, Jinja2 templates (`{{ var }}` and `[[ var ]]`) |
| 2 | vanilla | htmy | Vanilla CSS, HTMY components (no fastblocks-ui CSS bundle) |
| 3 | fastblocks_ui | jinja2 | fastblocks-ui CSS, Jinja2 templates |
| 4 | fastblocks_ui | htmy | fastblocks-ui CSS, HTMY components (full integration) |

**Per-cell invariant assertions**:
- For `safe_user_input`: rendered output contains the input verbatim.
- For `unsafe_input`: rendered output does **NOT** contain the raw payload
  in HTML context — must be escaped.
- The renderer's structural signature matches (Jinja2 → string-substitution
  shape; HTMY → component-tree shape).
- The style's CSS marker is correct (cells 1/2: no `fb-` class prefix on UI
  components; cells 3/4: `fb-` prefix).

**Test file**: `tests/templates/test_style_renderer_property.py`. One
`@given` per cell (4 total), `@settings(max_examples=100, deadline=None,
derandomize=False)` per master plan line 469.

**Unsupported cells** (per master plan line 111: "Cells are either
supported or unsupported"): unsupported cells fail at startup (Phase 1A/2
wiring), not in 5B. 5B only tests supported cells.

### 5B.2 — HTMY XSS matrix (34 components)

Per master plan line 470: "XSS regression test covers all 34 absorbed
components with per-field assertions."

**Test structure**: one test file with a single parameterized loop. For
each `component` in `ABSORBED_COMPONENTS`:

1. Build an instance with adversarial values for every dataclass field
   using `unsafe_input`.
2. Call `.htmy({})` to render.
3. Assert the rendered output does NOT contain the raw unsafe input
   (unless the field is documented as `SafeHTMLStr`).

**Test file**: `tests/xss/test_htmy_component_xss_matrix.py` —
parameterized over `ABSORBED_COMPONENTS`.

**Per-field assertions**:
- `str` fields → rendered output should HTML-escape the value (`<` → `&lt;`).
- `SafeHTMLStr` fields (per Phase 1B's absorption) → rendered output MAY
  contain raw value (trust boundary).
- `list[str]` fields → each element escaped.
- `dict[str, str]` fields (attrs) → values escaped; keys validated
  against the 21-name whitelist.

### 5B.3 — Jinja2 SSTI regression

Per master plan line 474: "adversarial inputs via `st.text(alphabet=...
<script>...)` round-tripped through `env.from_string(...)`; asserts no
autoescape bypass."

**Test file**: `tests/templates/test_jinja2_ssti.py`.

**Adversarial alphabet**: HTML delimiters + SSTI punctuation
(`{{`, `}}`, `[`, `]`, `<`, `>`, `$`, `#`, `%`, `;`, `'`, `"`, `/`, `\\`).

**Test invariants** (4 scenarios):
1. `env.from_string("{{ x }}").render(x=adversarial)` — rendered output
   contains the HTML-escaped adversarial input, never the raw input in
   HTML context.
2. `env.from_string("[[ x ]]").render(x=adversarial)` — fragment delimiter
   must respect autoescape (catches the real XSS vector if
   `jinja2_async_environment` skips escape for fragment performance).
3. `env.from_string("{{ x | safe }}").render(x=adversarial)` — the `| safe`
   filter is honored (output contains raw input); NOT a bypass.
4. `Markup(adversarial)` round-trip — `Markup` is the Jinja2 safe-string
   primitive; round-tripping should preserve the bytes.

### 5B.4 — HTMY hx_* kwargs contract

Per master plan line 475: "covers JSON-encoded variants: `hx-vals`,
`hx-headers`."

**Test file**: `tests/adapters/templates/test_htmy_hx_kwargs.py`.

**Test scenarios** (5):
1. `hx_vals={"id": 42, "name": "alice"}` → rendered as
   `hx-vals='{"id":42,"name":"alice"}'`.
2. `hx_headers={"X-CSRF-Token": "abc"}` → rendered as
   `hx-headers='{"X-CSRF-Token":"abc"}'`.
3. **JSON encoding does NOT bypass escape**: unsafe input as `hx_vals`
   value → JSON-encoded string still in HTML attribute context → must
   escape.
4. Nested dict: `{"user": {"id": 1}}` → serializes correctly.
5. Empty `hx_vals` → rendered as `hx-vals='{}'`.

## Sub-phase 5C — Adversarial integration

### 5C.1 — MCP server integration canary

Per master plan line 473: "spins up FastMCP server via `mcp_common`,
asserts the registered tool list equals the 7-name tuple from
`profiles.FASTBLOCKS_TOOLS` (catches the NameError regression history)."

**Test file**: `tests/mcp/test_server_canary.py`.

**Test scenarios** (3):
1. **Tools list tuple**: spin up `FastBlocksMCPServer`, call `list_tools()`,
   assert the result is exactly the 7-name tuple from
   `profiles.FASTBLOCKS_TOOLS`.
2. **Each tool is callable**: for each of the 7 names, call the tool with
   a minimal valid argument set, assert no `NameError` (catches the
   `tools.py:585-590` regression history).
3. **Resource list**: call `list_resources()`, assert all 7 resources
   per master plan line 209.

**Important caveat**: this canary validates the **current** registration
path (Phase 1.5's `register_fastblocks_tools`), not the deferred Phase 4
`apply_tool_profile` path. If Phase 4 is un-blocked, the canary needs to
be rewritten to validate the new registration. Documented in ADR 0011.

### 5C.2 — axe-core a11y on 34 components

Per master plan line 472: "axe-core integration test runs against the
output of each absorbed component's primary render path; zero violations
of color-contrast, label, button-name, link-name, image-alt, aria-roles."

**Test file**: `tests/a11y/test_components_a11y.py`.

**Test structure**: one parameterized test loop. For each `component` in
`ABSORBED_COMPONENTS`:

1. Build an instance with realistic defaults (non-adversarial).
2. Render to HTML via the component's primary render path.
3. Load into Playwright page (using `clean_axe_core_page` fixture).
4. Run `axe-playwright-python`'s `axe.run()` with the 6 master-plan rules.
5. Assert 0 violations.

**Edge case handling**: components with HTMX interactive states (modals,
dropdowns) may need additional props to satisfy `aria-roles` (e.g.,
`aria-modal="true"`). Tests supply realistic defaults — they don't
silently skip.

**Largest single test in Phase 5**: ~60-90s for browser startup + 34
renders.

### 5C.3 — CSRF + HTMX integration

Per master plan line 476: "CSRF + HTMX integration test asserts HTMX
POSTs succeed with the configured wiring."

**Test file**: `tests/integration/test_csrf_htmx.py`.

**Test scenarios** (4):
1. HTMX POST without CSRF token → 403.
2. HTMX POST with valid `X-CSRF-Token` header → 200.
3. HTMX POST with valid `csrf_token` form field (header missing) →
   middleware copies to header → 200.
4. HTMX POST with expired token → 403.

### 5C.4 — Static files test

Per master plan line 477: "Static-files test asserts cache headers +
brotli."

**Test file**: `tests/integration/test_static_files.py`.

**Test scenarios** (3):
1. `GET /static/ui.css` → 200 with `Cache-Control: public, max-age=31536000, immutable`.
2. `GET /static/ui.css` with `Accept-Encoding: br` → 200 with `Content-Encoding: br`.
3. `GET /static/nonexistent.css` → 404.

### 5C.5 — Lifecycle integration

Per master plan line 479: "LifespanManager asserts `app.state.main_loop`
and `app.state.jinja_env` are bound at startup, not per-request."

**Test file**: `tests/integration/test_lifespan.py`.

**Test scenarios** (2):
1. Lifespan startup: enter `LifespanManager`, assert `app.state.main_loop`
   is an `asyncio.AbstractEventLoop` AND `app.state.jinja_env` is a Jinja2
   `Environment`.
2. Lifespan teardown: exit `LifespanManager`, assert
   `app.state.main_loop` is unset.

## Verification gate

12 of 13 master-plan verification items (line 464-479) ship in Phase 5.
Item 14 (`asyncio.TaskGroup` cancellation propagation) is deferred to
Phase 6 with rationale.

| # | Verification item | Sub-phase | Master plan ref |
|---|---|---|---|
| 1 | `pytest --collect-only -q -p no:xdist` reports 0 errors | 5A | line 466 |
| 2 | `pytest --collect-only -q -p xdist -n auto` reports 0 errors | 5A | line 467 |
| 3 | Property-based test for every cell of style × renderer matrix | 5B | line 469 |
| 4 | `tests/strategies.py` exists with 4 strategies | 5A | line 469 |
| 5 | XSS regression test covers all 34 absorbed components with per-field assertions | 5B | line 470 |
| 6 | Accessibility contract test (axe-core on 34) | 5C | line 471-472 |
| 7 | axe-core integration: 0 violations of 6 rules | 5C | line 472 |
| 8 | MCP server integration test: 7-name tuple registered | 5C | line 473 |
| 9 | Jinja2 SSTI regression: no autoescape bypass | 5B | line 474 |
| 10 | HTMY component `hx_*` kwargs contract test (JSON-encoded variants) | 5B | line 475 |
| 11 | CSRF + HTMX integration test | 5C | line 476 |
| 12 | Static-files test asserts cache headers + brotli | 5C | line 477 |
| 13 | Lifecycle integration test asserts `app.state.main_loop` + `app.state.jinja_env` bound at startup | 5C | line 479 |
| ~~14~~ | ~~`asyncio.TaskGroup` cancellation propagation~~ | **DEFERRED to Phase 6** | line 478 |

## Coverage ratchet

**Current**: 55.05% (Phase 0 baseline, master plan line 650).
**Phase 5 target**: **65%** (+10pp).

The +10pp comes from:
- 5B matrix + XSS + SSTI + hx_* → ~5pp.
- 5C MCP canary → ~1pp.
- 5C integration tests (CSRF, static, lifecycle) → ~3pp.
- 5C axe-core → ~1pp.

**Why stop at 65%, not master plan's 70%**: remaining 5pp depends on
Phase 6's observability hooks. Lifting the ratchet beyond 65% before
Phase 6 ships creates a brittle floor. Documented in ADR 0012 (Phase 5
ADR, new) once it ships.

## Per-commit Integration Contracts (12 commits)

Per CLAUDE.md §Process Discipline. Each commit ships with an IC block.

### 5A — 3 commits

| # | Subject | Returns | Demonstrable by |
|---|---|---|---|
| 1 | `chore(tests): install pytest-hypothesis, playwright, axe-playwright-python` | `pyproject.toml` dev-deps; `playwright install chromium` | `uv pip list \| grep -E "(pytest-hypothesis\|playwright\|axe-playwright)"` |
| 2 | `feat(tests): tests/strategies.py — 4 Hypothesis strategies` | `tests/strategies.py` with 4 strategies | `python -c "from tests.strategies import safe_user_input, unsafe_input, attrs_dict, htmy_component; print('OK')"` |
| 3 | `chore(tests): zero-collection-error + Hypothesis profiles` | `tests/conftest.py` extensions + 3 new markers in `pyproject.toml` | `pytest --collect-only -q -p no:xdist` returns 0; `pytest --collect-only -q -p xdist -n auto` returns 0 |

### 5B — 4 commits

| # | Subject | Returns | Demonstrable by |
|---|---|---|---|
| 4 | `test(templates): property-based style × renderer matrix` | `tests/templates/test_style_renderer_property.py` (4 cells × 100) | 4 property-based tests pass |
| 5 | `test(xss): HTMY XSS matrix for all 34 absorbed components` | `tests/xss/test_htmy_component_xss_matrix.py` | 34 components × 3 attack vectors = ~100+ tests pass |
| 6 | `test(templates): Jinja2 SSTI regression` | `tests/templates/test_jinja2_ssti.py` | 4 SSTI scenarios pass |
| 7 | `test(adapters): HTMY hx_* kwargs contract test` | `tests/adapters/templates/test_htmy_hx_kwargs.py` | 5 hx_* scenarios pass |

### 5C — 5 commits

| # | Subject | Returns | Demonstrable by |
|---|---|---|---|
| 8 | `test(mcp): server integration canary` | `tests/mcp/test_server_canary.py` | 3 scenarios pass (tools tuple, each callable, resources) |
| 9 | `chore(tests): tests/a11y/ — axe-core on 34 components` | `tests/a11y/test_components_a11y.py` + `clean_axe_core_page` fixture | `pytest tests/a11y/ -v` passes; 0 axe-core violations |
| 10 | `test(integration): CSRF + HTMX` | `tests/integration/test_csrf_htmx.py` + `fastblocks_test_app` fixture | 4 CSRF scenarios pass |
| 11 | `test(integration): static files + lifecycle` | `tests/integration/test_static_files.py` + `tests/integration/test_lifespan.py` | 3 static + 2 lifecycle scenarios pass |
| 12 | `chore(ci): bump coverage ratchet to 65%` | `pyproject.toml` updated with `--cov-fail-under = 65` | `pytest --cov-fail-under=65` exits 0 |

**All 12 commits are independently revertible** per CLAUDE.md §Process
Discipline.

### Cumulative runtime estimate

| Sub-phase | Tests added (est.) | Runtime (est.) | Marker(s) |
|---|---|---|---|
| 5A | ~5 | ~2s | `unit` |
| 5B | ~130 | ~22-47s | `property`, `unit` |
| 5C | ~17 | ~76-108s | `a11y`, `integration`, `slow`, `unit` |
| **Total** | ~150 | ~100-150s (1.5-2.5 min) | — |

Well under the **5-min CI budget** (user decision).

## Failure modes

| Failure | Behavior | Recovery |
|---|---|---|
| Collection error on import | `pytest --collect-only` reports error | Fix import in 5A before merge |
| Property-based test finds a real bypass | Hypothesis reports failing example with seed | Document as known issue; fix in fastblocks; amend ADR 0012 (Phase 5 ADR, new) |
| MCP canary: tool name mismatch | Canary fails with diff | Fix `profiles.FASTBLOCKS_TOOLS` or `register_fastblocks_tools` to align |
| axe-core finds a11y violation | Test fails with axe report | Fix component's render path (or document as accepted) |
| Coverage ratchet doesn't reach 65% | `pytest --cov-fail-under` exits 1 | Add more tests OR amend ADR to lower target |
| Playwright browser binary missing | Test fails with `playwright._impl._errors.Error` | `playwright install chromium` in setup |

## Out of scope (deferred)

- **`asyncio.TaskGroup` cancellation propagation** (master plan line 478) —
  Phase 6 ships production migration first; tests-only Phase 5 doesn't
  touch production code.
- **Coverage ratchet beyond 65%** — Phase 6's observability work lifts
  it further (master plan line 653 target is 70%).
- **Cross-Bodai-repo MCP canary** — only tests fastblocks's MCP server,
  not SplashStand's embedding of fastblocks.
- **HTMY XSS for Jinja2-rendered components** — Jinja2 doesn't have
  absorbed components; only HTMY does.
- **Production code changes** — Phase 5 is strictly tests-only per the
  user's "strict tests-only" decision.
- **A11y for documentation site** — that's Phase 8 per master plan line 233.

## Acceptance criteria for "Phase 5 done"

All 12 verification items (#1-13 minus deferred #14) pass AND:
- Coverage ratchet at 65% (`pytest --cov-fail-under=65` exits 0).
- All 12 commits landed on `main` per Bodai pre-1.0 merge policy
  (worktree → ff-merge into main, no PRs).
- Per-commit canary validations hold: `crackerjack run` green, ty PASS,
  ruff PASS.
- Total Phase 5 CI runtime ≤ 5 min added to baseline (~37s baseline;
  verified by CI logs).

## Cross-references

- Master plan: `docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md`
  - §Pillar 6 (line 174-180)
  - §Phase 5 row (line 341)
  - §Phase 5 verification (line 464-479)
  - §Phase 0 preflight (line 608-621) — confirmed no Phase N.5 needed
- Phase 0 baseline pytest: master plan line 635-655
- Phase 1A's `with suppress(Exception)` removal: master plan line 467
- Phase 1B's `SafeHTMLStr` propagation: master plan line 268; deferred
  per ADR 0010 Decision 10
- Phase 1.5's `clean_resolver` fixture: master plan line 296
- Phase 1.5's `FastblocksRegistry` facade: master plan line 292
- Phase 2's `StyleName` Literal: `fastblocks/core/validators.py`
- Phase 2.5's `AppBaseSettings`: `fastblocks/adapters/app/_base.py`
- Phase 4 deferral: `docs/adr/0011-phase-4-deferral.md`
- CLAUDE.md §Process Discipline (Integration Contract requirement):
  `CLAUDE.md` (project root)
- `tests/xss/ssti_payloads.json` corpus: existing Phase 1B XSS test
  corpus (15+ vectors)
- `profiles.FASTBLOCKS_TOOLS`: `fastblocks/mcp/profiles.py:113`
- `tests/conftest.py` extensions (Hypothesis profiles): new in this design
- `ABSORBED_COMPONENTS`: `fastblocks/adapters/templates/htmy_components/__init__.py`
