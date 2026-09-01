# FastBlocks Style/Renderer Architecture Consolidation

**Date:** 2026-08-21
**Status:** Approved after 4-reviewer spec review + 4-reviewer plan audit (security-auditor, architecture-council, fastblocks-specialist, outside-AI)
**Branch:** in-place on fastblocks main
**Repository:** `/Users/les/Projects/fastblocks`
**Target versions:** `fastblocks 0.30.0` (independent fixes) + `fastblocks 0.31.x` (absorption mechanics + cross-repo shim)

## Goal

Consolidate FastBlocks' style adapter layer into a clean two-axis architecture
(`style` = CSS source × `renderer` = component model) by: dropping the broken
`kelp`/`bulma`/`webawesome`/`custom` style adapters, promoting `fastblocks-ui`
to the default style layer + runtime dependency, closing the live RCE vector
in `htmy.py`, and absorbing the standalone `fastblocks-htmy` PyPI package into
`fastblocks` proper.

Work is split across two releases because each release has its own deprecation
lifecycle. The 0.30.0 work is independently valuable (drops broken code,
promotes working default, closes a security bug) and doesn't depend on the
absorption landing. The 0.31.x work is the absorption mechanics plus a
cross-repo shim release. Each release has its own verification gate and
rollback signal.

## Why two releases, not one

| Concern | Single-release plan | Two-release plan |
|---|---|---|
| Reviewer load | One PR bundles four changes (style cleanup, dep change, security fix, source absorption); high cognitive load | Each PR has one theme; reviewer focus is sharper |
| Rollback granularity | Reverting requires undoing everything; the broken-style trap stays until the entire PR lands | 0.30.0 can roll back to `style="vanilla"`-default for the *style* changes (A, B, D) without touching htmy code ¹ |
| PyPI blast radius | One release ships all the breaking changes; any external consumer hits them simultaneously | 0.30.0 hard-breaks `style="kelp"`/`"bulma"`/`"webawesome"`/`"custom"` (verified-zero-consumers); 0.31.x only affects users importing from `fastblocks_htmy` (zero verified external consumers per Arch F8) |
| Failure mode visibility | If 0.31.x work fails, 0.30.0's independently-valuable fixes are blocked | 0.30.0 ships even if 0.31.x is delayed |

¹ **Security footnote on rollback:** A full 0.30.0 revert restores the `_load_from_cached_bytecode` / `_load_from_source` paths deleted by Task C3 — the same RCE vectors the release closed. If the regression triggering the revert is style-only (A, B, D), prefer a scoped revert of those commits only, preserving the C3 RCE fix. The "without touching htmy code" claim above refers to *writing new htmy code*, not to security-impacting restore via full-revert.

User-confirmed: zero external consumers of fastblocks, fastblocks-ui, or
fastblocks-htmy. This collapses the cross-release deprecation-cycle concern
that would normally apply (no 0.29.x intermediate warning release; users on
`style="kelp"` etc. fail loudly at 0.30.0).

## Architecture (target)

| Axis | Today | Target |
|---|---|---|
| `style` (CSS source) | 4 options, 2 broken traps (kelp, webawesome), 2 untested (bulma, custom) | 2 options, both correct (`vanilla`, `fastblocks_ui`) |
| `renderer` (component model) | conflated under `style` | separate axis; documented north star only in this PR |

`AppBaseSettings.style: str = "fastblocks_ui"` is the new default; `vanilla`
remains as an explicit opt-in for unstyled apps.

The `renderer` axis is documented in `fastblocks/core/style_registry.py`'s
docstring as the unifying abstraction: `style` × `renderer` becomes a 2×2 matrix
where every cell is either coherent or unavailable. Concrete renderer values
(`jinja2` | `htmy`) and their interaction with `style` are out of scope for
this PR — only the axis is named.

______________________________________________________________________

# Release 1: fastblocks 0.30.0 — independent fixes

**Theme:** Tighten the codebase before introducing deprecation-cycle churn. Each
task is independently valuable and would ship as a standalone improvement if
the absorption were deferred further.

## Deliverables

### A — Style layer cleanup (drop kelp + bulma + webawesome + custom)

Delete the four broken-or-untested style adapters. Per CLAUDE.md:234-235 +
fastblocks-specialist plan-audit, `kelp`/`webawesome` each carry three
independent bugs (decorator-API misuse, wrong-Resolver-API, masked XSS
surface) silently swallowed by `with suppress(Exception)`. `bulma` and
`custom` have only template variant directories under
`fastblocks/adapters/app/_templates/{bulma,custom}/` and no backing
`fastblocks/adapters/style/{bulma,custom}.py` adapter — they fall through to
the silent-no-op default. Users configured to any of these values silently
render as unstyled.

**Files to delete:**

- `fastblocks/adapters/style/kelp.py`, `kelp.py.backup`, `kelp.py.backup.json`
- `fastblocks/adapters/style/webawesome.py`, `webawesome.py.backup`
- `fastblocks/cli.py.backup` (stale `webawesome` enum entry)
- `fastblocks/adapters/app/_templates/kelp/` (whole directory)
- `fastblocks/adapters/app/_templates/webawesome/` (whole directory)
- `fastblocks/adapters/app/_templates/bulma/` (whole directory)
- `fastblocks/adapters/app/_templates/custom/` (whole directory)

**Files to update:**

- `fastblocks/core/style_registry.py` — drop kelp/bulma/webawesome/custom from the known-style list; remove the long docstring passage that documents why kelp/webawesome would raise `AttributeError`
- `fastblocks/adapters/style/__init__.py` — drop from `__all__` / re-exports
- `fastblocks/adapters/style/README.md` — strip mentions
- `fastblocks/cli.py:62-65` — `Styles(StrEnum)` currently has **3 members** (verified — no `vanilla` or `fastblocks_ui` exist): `bulma = "bulma"`, `webawesome = "webawesome"`, `custom = "custom"`. Drop `bulma`, `webawesome`, `custom` AND add `vanilla = "vanilla"` and `fastblocks_ui = "fastblocks_ui"` so the enum reflects the 2 surviving styles. After the change, replace the `StrEnum` with `Literal["vanilla", "fastblocks_ui"]` for stronger static guarantees.
- `fastblocks/cli.py:929, 957, 1079, 1093` — these reference `Styles.bulma` as default; replace with `Styles.vanilla` (or the new default) per fastblocks-specialist audit
- `fastblocks/adapters/app/_base.py:12` — `style: str = "vanilla"` will be flipped to `"fastblocks_ui"` in Deliverable B; A just removes the broken-style branches from `_base.py`'s fallback path
- `fastblocks/adapters/app/README.md:188` — strip kelp/bulma/webawesome/custom mentions and the `style: str = "vanilla"` line
- `fastblocks/adapters/templates/_base.py:133` — `style = getattr(self.config.app, "style", "vanilla")` runtime fallback. Update default to `"fastblocks_ui"` (matching Deliverable B) so the runtime fallback doesn't silently re-introduce the old default
- `fastblocks/adapters/icons/README.md:65` — drop "copy `register_webawesome_functions` as the reference pattern" instruction (the reference function is being deleted)
- `CHANGELOG.md` — "Removed" section under 0.30.0
- `CLAUDE.md` — append to "Real bugs found" section (resolved): "kelp/webawesome removed in 0.30.0 because they were broken dead code with masked XSS surface; prior `style=kelp`/`style=webawesome` configurations now fail loudly with `unknown style` from `style_registry.py`. bulma/custom removed because they lacked backing adapters."
- `README.md` — strip kelp/webawesome/bulma/custom mentions
- `tests/adapters/styles/test_styles_comprehensive.py` — **not a single-block deletion**: the import block at lines 8-11 imports both `WebAwesomeStyle` AND `WebAwesomeStyleSettings` (per fastblocks-specialist re-review). `WebAwesomeStyle` is used inline in `TestStyleIntegration` (around line 154) at lines 159, 172, 189, 204, 217, 251; `WebAwesomeStyleSettings` is also assigned at line 218 (`webawesome.settings = WebAwesomeStyleSettings()`). Remove both `WebAwesomeStyle` and `WebAwesomeStyleSettings` from imports, drop `WebAwesomeStyle` from the `adapters = [...]` lists, drop the `test_settings_customization` WebAwesome branch (lines 216-223), drop the framework-switching assertions on `webawesome_button` (lines 189-200). No `TestWebAwesomeStyle` class exists as a single deletable block.
- `tests/adapters/style/test_fastblocks_ui_style.py` — audit tests assuming `vanilla` default
- **All `style: str = "vanilla"` references in tests** (per fastblocks-specialist audit): `tests/test_cli_direct.py:78`, `tests/test_templates_base.py:209`, `tests/ensure_cli.py:70`, `tests/test_cli_coverage.py:82`, `tests/adapters/app/test_app_coverage.py:259,313`, `tests/adapters/app/test_app_structure.py:38,64,83`, `tests/adapters/app/ensure_adapter.py:37`. Flip to `"fastblocks_ui"` or make them explicit-construction tests that don't depend on the default.
- **Pre-deletion check** (per fastblocks-specialist + outside-AI): before deleting any `*.backup.json` file, run `cat fastblocks/adapters/style/kelp.py.backup.json | head -5` and `grep -rn 'kelp.*\.backup\.\|webawesome.*\.backup\.' tests/ fastblocks/` to confirm zero test/fixture references. If any code imports a backup, keep the file or migrate the fixture into `tests/conftest.py`.

**Integration Contract (A):**

- **Triggered from:** post-ty-cleanup main (HEAD `ffef487`); working tree clean except for the new spec + plan files (intentional).
- **Returns to / updates:** `fastblocks/adapters/style/{__init__.py,kelp.py,kelp.py.backup,kelp.py.backup.json,webawesome.py,webawesome.py.backup,README.md}`, `fastblocks/adapters/app/{__init__.py,_base.py,README.md,_templates/{kelp,webawesome,bulma,custom}/}`, `fastblocks/adapters/templates/_base.py:133`, `fastblocks/adapters/icons/README.md:65`, `fastblocks/cli.py` (+ `.backup`), `fastblocks/core/style_registry.py`, `pyproject.toml`, `CHANGELOG.md`, `CLAUDE.md`, `README.md`, `tests/adapters/{styles,style,app}/*`, `tests/{test_cli_direct,test_templates_base,ensure_cli,test_cli_coverage}.py`.
- **Demonstrable by:** `python -c "from fastblocks.adapters.style import vanilla, fastblocks_ui"` works; `git grep -nE "kelp|webawesome|bulma|custom|KelpStyle|WebAwesomeStyle|BulmaStyle" fastblocks/ tests/ settings/` returns 0 hits; `git ls-files --modified --others --cached fastblocks/ settings/ | xargs grep -n "kelp\|webawesome\|bulma\|custom"` returns 0 hits; `find fastblocks/ -type f \( -name "*.html" -o -name "*.jinja2" -o -name "*.tmpl" \) -exec grep -l "kelp\|webawesome\|bulma\|custom" {} \;` returns empty; `python -c "from fastblocks.adapters.app._base import AppBaseSettings; AppBaseSettings().model_dump()"` exits 0.
- **Rollback signal:** `git revert` of the A merge commit. Pytest remains green. `style_registry.py` reverts the known-style list. No security impact: A's deletions remove broken code; reverting A restores it (the bugs were masked but not exploitable on their own).
- **Observability added:** startup log line on `from fastblocks import FastBlocks` → `style=<value> resolved from fastblocks.core.style_registry`; counter metric `fastblocks_style_resolve_total{result=hit|miss, style=<value>}` so any `unknown style` miss is countable post-rollout.

### B — Promote fastblocks-ui to default

Move `fastblocks-ui` from optional dep group to `[project].dependencies`. Make
it the default `AppBaseSettings.style`.

**Files to update:**

- `pyproject.toml` — move `"fastblocks-ui>=0.8,<0.9"` from the optional `fastblocks_ui = [...]` group into `[project].dependencies` directly. **Pin corrected** from the prior plan's `>=0.7,<0.8` to `>=0.8,<0.9` to match the range the standalone `fastblocks-htmy` already requires (per spec). Delete the `fastblocks_ui = [...]` group entirely.
- `fastblocks/adapters/app/_base.py:12` — `style: str = "vanilla"` → `style: str = "fastblocks_ui"`
- `fastblocks/adapters/templates/_base.py:133` — `style = getattr(self.config.app, "style", "vanilla")` → `style = getattr(self.config.app, "style", "fastblocks_ui")` (matches Deliverable A's preemptive update)
- `tests/adapters/style/test_fastblocks_ui_style.py` — audit tests assuming `vanilla` default
- `tests/adapters/app/test_app_structure.py:64` (`assert AppBaseSettingsType.style == "vanilla"`) and the 7+ other test sites listed in Deliverable A — all flipped to `"fastblocks_ui"` or made explicit-construction

**Pre-flight gate (must pass BEFORE the pyproject change is committed):**

```bash
uv pip install 'fastblocks-ui>=0.8,<0.9'
python -c "import fastblocks_ui; assert callable(fastblocks_ui.get_css_path); assert callable(fastblocks_ui.get_js_path)"
# Extended per security-auditor audit — verify escape correctness of helpers the absorbed components delegate to
python -c "from fastblocks_ui import button as b; out = b('<script>alert(1)</script>', variant=None, size=None, href=None, type='button', class_=None); assert '<script>' not in out and '&lt;script&gt;' in out"
# Repeat for container, columns, navbar, table, tabs, field, breadcrumb, dropdown, select, validation_summary
# Snapshot the escape behavior in tests/style/test_fastblocks_ui_escape_contract.py so crackerjack gates every release against drift
```

If any helper fails the pre-flight or the escape check returns unescaped output, the task fails — do not commit with a placeholder or `# type: ignore`.

**Integration Contract (B):**

- **Triggered from:** Deliverable A's verification gates green.
- **Returns to / updates:** `pyproject.toml`, `fastblocks/adapters/app/_base.py:12`, `fastblocks/adapters/templates/_base.py:133`, `tests/adapters/{style,app}/*`, `tests/test_cli_direct.py:78`, `tests/test_templates_base.py:209`, `tests/ensure_cli.py:70`, `tests/test_cli_coverage.py:82`, `tests/adapters/app/ensure_adapter.py:37`.
- **Demonstrable by:** `git grep -n "fastblocks_ui =" pyproject.toml` returns 0 hits; `git grep -n "fastblocks-ui" pyproject.toml` returns exactly 1 hit in `[project].dependencies`; `python -c "from fastblocks import FastBlocks; FastBlocks().config.app.style"` returns `"fastblocks_ui"`; `uv run ty check fastblocks/` "All checks passed!"; `uv run pytest -q -m "not slow" --no-header` ≥ 1714 passed; `uv run crackerjack run` all hooks PASS.
- **Rollback signal:** `git revert` of the B merge commit. Default reverts to `style="vanilla"`. No security impact (B is a default flip, not a code-path change).
- **Observability added:** startup log line emits `style=fastblocks_ui (default)` vs `style=fastblocks_ui (explicit)` so we can count users overriding the default post-rollout.

### C3 — Close live RCE in htmy.py (restructured from a single bullet into three explicit steps)

`fastblocks/adapters/templates/htmy.py:300-354` (`_load_from_cached_bytecode`)
and `htmy.py:356-399` (`_load_from_source`) use
`importlib.util.spec_from_file_location()` + `spec.loader.exec_module()` — the
exact RCE path CLAUDE.md:130 documents as removed by Phase 1.3. The advanced
registry in `_htmy_components.py` correctly routes through
`load_component_from_source()` (AST-sandboxed), but
`HTMYTemplates.render_component` falls back to the legacy
`HTMYComponentRegistry` for any path that doesn't go through
`render_component_advanced`, and `HTMYComponentRegistry.get_component_class`
(lines 279-298) calls both `_load_from_*` methods unconditionally.

**Files to update** — three discrete steps:

1. **Delete the unsafe loaders.** Remove `_load_from_cached_bytecode` (lines 300-354) and `_load_from_source` (lines 356-399) from `htmy.py`.
1. **Rewrite the caller.** `HTMYComponentRegistry.get_component_class` at `htmy.py:279-298` calls both deleted methods. Replace its body to defer to `AdvancedHTMYComponentRegistry.load_component_from_source(component_path, source, registry=AdvancedHTMYComponentRegistry)` from `_htmy_components.py`. If no advanced registry is available, raise `ComponentNotFound` matching the trusted-only fallback contract. Do NOT copy-paste `_load_from_source` minus the `importlib.util` guard — that would silently restore the RCE vector.
1. **Audit tests.** Any tests in `tests/adapters/templates/` that called `HTMYTemplates.get_component_class` directly must be updated or deleted. The legacy `HTMYComponentRegistry` path is preserved (loader-free); tests asserting on `discover_components()` / `register_trusted_components()` continue to pass.

**Integration Contract (C3):**

- **Triggered from:** independent of A and B (RCE fix is self-contained).
- **Returns to / updates:** `fastblocks/adapters/templates/htmy.py` (lines 279-399 area), `tests/adapters/templates/test_htmy_loader_safety.py` (new file).
- **Demonstrable by:** `grep -nE "importlib|__import__|exec\s*\(|eval\s*\(" fastblocks/adapters/templates/htmy.py` returns 0 hits (broader than the original `spec_from_file_location\|exec_module` regex, per security-auditor audit — catches `importlib.util` reintroduction, `__import__`, dynamic compile-and-exec patterns); `python -m pytest tests/adapters/templates/test_htmy_loader_safety.py` passes (new test that opens `htmy.py`, scans with the same regex, asserts clean match); `uv run ty check fastblocks/` "All checks passed!"; `uv run pytest -q -m "not slow"` all current tests still pass.
- **Rollback signal:** **NOT a simple `git revert` of the merge commit** — a full revert restores `_load_from_cached_bytecode` / `_load_from_source` and re-opens the RCE vector. If the regression triggering the rollback is style-only (A/B/D), prefer scoped revert of those commits only, preserving C3. If C3 itself regresses, the rollback procedure is: (a) ship a follow-up patch that re-introduces the loaders with a documented security review, (b) mark the issue as a known regression.
- **Observability added:** import-time assertion at `htmy.py` module load that runs the broader RCE grep and `RuntimeError`s if it fails (fails loud at startup if the path is reintroduced); counter metric `fastblocks_htmy_load_attempts_total{source=ast_sandboxed|legacy_unsafe}` so any reintroduction of the unsafe path is observable in production.

### D — Reclassify architecture (doc-only)

Document the future `renderer` axis as the unifying abstraction. Pure doc
change; doesn't require any absorption to land.

**Files to update:**

- `fastblocks/core/style_registry.py` — update docstring: `style` = CSS source only; `renderer` axis (`jinja2` | `htmy`) is the next-iteration north star, not introduced as a config knob in this PR. Drop the long passages about kelp/webawesome's `AttributeError` traps (no longer apply after A).
- `fastblocks/adapters/style/__init__.py` — update module docstring to 2-style state
- `fastblocks/adapters/style/README.md` — rewrite to describe the `style` axis in isolation
- **Cross-link to CLAUDE.md "Architecture" section** (per outside-AI audit): one-line entry pointing back to `style_registry.py`'s renderer-axis docstring, so the architectural commitment doesn't get tidied away in a future docstring edit

**Integration Contract (D):**

- **Triggered from:** A and B complete (D drops kelp/webawesome passages from docstrings).
- **Returns to / updates:** `fastblocks/core/style_registry.py` docstring, `fastblocks/adapters/style/__init__.py` docstring, `fastblocks/adapters/style/README.md`, `CLAUDE.md` "Architecture" section.
- **Demonstrable by:** `git grep -n "renderer" fastblocks/core/style_registry.py` returns exactly the docstring references (not imports, not calls); `git grep -n "kelp\|webawesome" fastblocks/ settings/` returns 0 hits; `uv run ty check fastblocks/` "All checks passed!"; `uv run crackerjack run` all hooks PASS.
- **Rollback signal:** `git revert` of the D merge commit. Doc-only rollback — no security impact, no test impact.
- **Observability added:** none (doc-only).

## Ordering within 0.30.0

A, B, C3 are independent — run in parallel or sequentially in any order. D
requires A and B complete (drops kelp/webawesome passages from docstrings).
C3 has the security-fix character and can ship first if prioritization is
needed.

## Verification gates (every commit)

- `uv run ty check fastblocks/` → "All checks passed!" (do NOT add suppressions)
- `uv run pytest -q -m "not slow" --no-header` → ≥ 1714 passed, 0 fail
- `uv run crackerjack run` → ty PASS, refurb PASS, ruff PASS

**Task-specific gates:**

| After | Gate | Expected |
|---|---|---|
| A | `git ls-files --modified --others --cached fastblocks/ settings/ \| xargs grep -nE "kelp\|webawesome\|bulma\|custom\|KelpStyle\|WebAwesomeStyle\|BulmaStyle"` | no hits |
| A | `find fastblocks/ -type f \( -name "*.html" -o -name "*.jinja2" -o -name "*.tmpl" \) -exec grep -lE "kelp\|webawesome\|bulma\|custom" {} \;` | empty |
| A | `python -c "from fastblocks.adapters.style import vanilla, fastblocks_ui"` | both import, no kelp/bulma/webawesome/custom import path |
| A | `python -c "from fastblocks.adapters.app._base import AppBaseSettings; AppBaseSettings().model_dump()"` | exits 0 |
| A | `cat fastblocks/adapters/style/kelp.py.backup.json \| head -5; grep -rnE 'kelp.*\.backup\.\|webawesome.*\.backup\.' tests/ fastblocks/` | no fixture references before deletion |
| B | `git grep -n "fastblocks_ui =" pyproject.toml` | no hits |
| B | `git grep -n "fastblocks-ui" pyproject.toml` | exactly one hit, in `[project].dependencies` |
| B | `python -c "from fastblocks.adapters.style import fastblocks_ui; print(fastblocks_ui.__version__)"` | works |
| B | `python -m pytest tests/style/test_fastblocks_ui_escape_contract.py` (new file) | passes — every helper escapes `<script>` |
| C3 | `grep -nE "importlib\|__import__\|exec\s*\(\|eval\s*\(" fastblocks/adapters/templates/htmy.py` | no hits |
| C3 | `python -m pytest tests/adapters/templates/test_htmy_loader_safety.py` (new file) | passes — Python-level guard against reintroduction |
| C3 | `grep -nE "load_from_cached_bytecode\|load_from_source" fastblocks/adapters/templates/htmy.py` | no hits (callers fully removed) |
| D | `git grep -n "renderer" fastblocks/core/style_registry.py` | exactly docstring references |
| D | `git grep -n "kelp\|webawesome\|bulma\|custom" fastblocks/ settings/` | no hits |

## Air-gapped upgrade note (Release 1)

Users with curated PyPI mirrors (corporate air-gap, locked-down distro) must
mirror `fastblocks-ui>=0.8,<0.9` before upgrading to fastblocks 0.30.0.
The `vanilla` style adapter continues to work as the explicit unstyled
opt-out, but the package install is now unconditional. Air-gapped installs
must pre-stage `fastblocks-ui`. Mirror-policy implications belong in the
upstream `fastblocks-ui` distribution channel, not fastblocks proper, but
the breaking nature of "vanilla users now need fastblocks-ui too" must be
in the CHANGELOG.

## Integration Contract (Release 1)

- **Triggered from:** post-ty-cleanup main (HEAD `ffef487`); working tree clean except for the new spec + plan files.
- **Returns to / updates:** per-task ICs above (A, B, C3, D). Release-level scope = union of per-task updates.
- **Demonstrable by:** union of per-task Demonstrable-by clauses. Smoke: `python -c "from fastblocks import FastBlocks; FastBlocks().config.app.style" == "fastblocks_ui"`; kelp/bulma/webawesome/custom grep returns 0 hits; `grep -nE "importlib|__import__|exec\s*\(|eval\s*\(" fastblocks/adapters/templates/htmy.py` returns 0 hits; `uv run ty check fastblocks/` "All checks passed!"; `uv run pytest -q -m "not slow" --no-header` ≥ 1714 passed; `uv run crackerjack run` all hooks PASS.
- **Rollback signal:** **scoped revert preferred over full revert.** Per-task ICs above define which commits are safe to revert. C3 is NOT safe to revert in isolation (re-introduces RCE); if a C3 regression triggers, ship a follow-up patch with documented security review, not a revert. The release-level rollback signal is "scoped revert of A, B, D commits; preserve C3." The comparison table's "0.30.0 can roll back to style='vanilla'-default" wording refers to writing *new* htmy code, not to security-impacting restore via full-revert.
- **Observability added:** startup log line `style=<value>, fastblocks_ui_version=<X.Y.Z>, htmy_path=AST-sandboxed`; counter metric `fastblocks_style_resolve_total{result, style}`; import-time assertion in `htmy.py` that the RCE grep returns 0 hits; escape contract test pinning `fastblocks_ui` helper behavior.

______________________________________________________________________

# Release 2: fastblocks 0.31.x — absorption mechanics

**Theme:** Move `fastblocks-htmy` source into `fastblocks` proper, pin
transitive deps directly, ship a cross-repo shim release so any external
`import fastblocks_htmy` keeps working through the deprecation cycle.

## Pre-conditions (all must hold before any 0.31.x work begins)

1. **0.30.0 merged to main.** All independently-valuable fixes are in.
1. **PyPI reverse-deps confirmation** — protocol (per architecture-council audit; `pip install --dry-run` does NOT query reverse deps, contrary to the original plan):
   ```bash
   # 1. Confirm what fastblocks-htmy 0.5.x declared as its own deps (direct deps only — not reverse)
   curl -s https://pypi.org/pypi/fastblocks-htmy/0.5.0/json | jq '.info.requires_dist'
   # 2. List dependent repos (this is the actual reverse-deps source)
   curl -s https://libraries.io/pypi/fastblocks-htmy/dependents
   # 3. Download counts as a proxy for active users
   curl -s https://pypistats.org/api/packages/fastblocks-htmy/recent
   # 4. GitHub code search: https://github.com/search?q=%22import+fastblocks_htmy%22&type=code
   #    excluding known Bodai repos. Cross-reference all four sources. If any external
   #    consumer exists, abort and re-plan.
   ```
1. **Pre-merge analysis complete.** Diff public method signatures between `fastblocks_htmy/base.py` and `_htmy_components.py`. Enumerate name collisions with proposed resolution (alias, merge, raise). Produce a commit-by-commit migration path for users who depended on either definition. Result reviewed and chosen default documented in CHANGELOG before C2 starts.
1. **Standalone-repo pre-flight:** `git -C /Users/les/Projects/fastblocks-htmy status` must be clean before starting C5; if dirty, abort and surface (per architecture-council audit).
1. **C1 prerequisite:** B's `fastblocks_ui = [...]` group is gone (`git grep -n "fastblocks_ui =" pyproject.toml` returns no hits) AND `fastblocks-ui>=0.8,<0.9` is in `[project].dependencies`.

## Deliverables

### C1 — Pin transitive deps correctly (the convergent critical fix)

**Standalone sub-task of spec Task C.** The plan and earlier spec draft instructed adding `"fastblocks-htmy>=0.5,<0.6"` to `[project].dependencies`. This is wrong for four converging reasons (security-auditor F1, ai-engineer C3, architecture-council F1+F2, fastblocks-specialist F1):

- Pinning `fastblocks-htmy` as a dep of the package that absorbed its source creates a self-referential dependency.
- The standalone `fastblocks_htmy/__init__.py:58-81` runs `_check_fastblocks_ui()` at import time and emits `RuntimeWarning` for any `fastblocks-ui` outside `[0.8, 0.9)`.
- Sets the wrong ecosystem precedent for future "absorb an external package" decisions.
- The transitive intent is achieved by pinning `htmy` + `fastblocks-ui` directly.

**Files to update:**

- `pyproject.toml` — **EDIT, don't add.** `htmy[lxml]~=0.9` is already at `pyproject.toml:48`. Replace it with `htmy[lxml]>=0.13,<0.14` (preserve the `lxml` extra — it's required by the AST-sandboxed parser; per fastblocks-specialist audit, dropping it would silently break `load_component_from_source`). Do NOT add `fastblocks-htmy` to `[project].dependencies`. Result:
  ```toml
  [project]
  dependencies = [
      # ... existing ...
      "fastblocks-ui>=0.8,<0.9",        # already added in 0.30.0 Deliverable B
      "htmy[lxml]>=0.13,<0.14",         # was "~=0.9" at pyproject.toml:48; bumped to match standalone fastblocks-htmy's pin
  ]
  ```

**Pre-flight gate** (per architecture-council audit, mirroring Deliverable B):

```bash
uv pip install 'htmy[lxml]>=0.13,<0.14'
python -c "import htmy; print(htmy.__version__)"
```

If the range is no longer resolvable on PyPI, abort C1 and pin a different range.

**Integration Contract (C1):**

- **Triggered from:** 0.30.0 merged + Deliverable B verified (the `[project].dependencies` entry for `fastblocks-ui>=0.8,<0.9` exists; the optional `fastblocks_ui = [...]` group is gone).
- **Returns to / updates:** `pyproject.toml` (line 48 region).
- **Demonstrable by:** `git grep -n "htmy" pyproject.toml` shows the new `>=0.13,<0.14` pin (and the `lxml` extra); `git grep -n "~=0.9" pyproject.toml | grep htmy` returns 0 hits; `git grep -nE "fastblocks-htmy|fastblocks_htmy" pyproject.toml` returns 0 hits in `[project].dependencies` (only acceptable in `[project.optional-dependencies]` if a dev/test group references it); `uv pip install -e .` resolves without warning; `python -c "import fastblocks; import htmy; import fastblocks_ui"` succeeds.
- **Rollback signal:** `git revert` of the C1 merge commit. No security impact (C1 is a dep-string edit).
- **Observability added:** startup log line emits resolved `htmy==<version>` so any silent dep downgrade is observable post-rollout.

### C2 — Reconcile base classes

**Standalone sub-task of spec Task C.** The existing `_htmy_components.py:371` defines `ComponentBase(ABC)` with `add_child` / `remove_child` / `children` / `parent`. The standalone `fastblocks_htmy/base.py:8` defines `FastBlocksComponent` with `_markup` + `htmy` + `__html__` + `__str__`. The 20+ typed UI components (`Button`, `Field`, `Tabs`, etc.) all inherit from `FastBlocksComponent`, not from `ComponentBase`. These are not aliases.

**Decision (pinned, not delegated to implementer):** `FastBlocksComponent` becomes the canonical base class for absorbed `ui/` and `layout/` components. `_htmy_components.ComponentBase` is preserved for legacy code paths in `_htmy_components.py` (used by `AdvancedHTMYComponentRegistry`'s discovery loader). The two classes coexist; `FastBlocksComponent` is the user-facing base for typed components. **`ComponentBase` is NOT a drop-in replacement for `FastBlocksComponent`** (per fastblocks-specialist audit) — the two have different APIs (tree-building vs markup rendering) and are not interchangeable. CHANGELOG must call this out.

**Files to create / update:**

- Create `fastblocks/adapters/templates/htmy_components/__init__.py` (new package) — **minimal placeholder** (per fastblocks-specialist re-review; avoids the C2/C4 `__init__.py` overwrite conflict). Contents: `from .base import FastBlocksComponent` and a docstring noting "full 34-name export lands in C4." C4 will overwrite this file with the complete 34-name re-export + soft warning + provenance line.
- Create `fastblocks/adapters/templates/htmy_components/base.py` — verbatim copy of `fastblocks_htmy/base.py`
- `CHANGELOG.md` — document the rename: `FastBlocksComponent` is now the canonical base for absorbed typed components. Existing `ComponentBase` in `_htmy_components.py` is preserved for the legacy registry path. Explicit note: "ComponentBase and FastBlocksComponent are NOT interchangeable."

**Integration Contract (C2):**

- **Triggered from:** C1 merged.
- **Returns to / updates:** `fastblocks/adapters/templates/htmy_components/{__init__.py,base.py}` (new files), `CHANGELOG.md`.
- **Demonstrable by:** `python -c "from fastblocks.adapters.templates.htmy_components import FastBlocksComponent; from fastblocks.adapters.templates._htmy_components import ComponentBase"` works; existing tests for `_htmy_components.ComponentBase` still pass; `uv run ty check fastblocks/` "All checks passed!".
- **Rollback signal:** `git revert` of the C2 merge commit. The new `htmy_components/` package is removed; no callers exist yet (C4 absorbs the callers). No security impact.
- **Observability added:** none (C2 is two new files plus a CHANGELOG entry).

### C4 — Absorb and verify

**Standalone sub-task of spec Task C.** Move the **24 source files** from `/Users/les/Projects/fastblocks-htmy/fastblocks_htmy/` into `fastblocks/adapters/templates/htmy_components/`. Reconcile with the existing legacy `_htmy_components.py`. Add the top-of-file "previously distributed as standalone PyPI package" docstring (per spec Task C). Update `htmy.py` to import from the now-internal `htmy_components` package.

**Sub-package restructure** (per architecture-council re-review): The standalone's `fastblocks_htmy/fastblocks/__init__.py` is **intentionally NOT recreated** at the top level. The only sibling is `fastblocks_htmy/fastblocks/adapter.py` (which carries 5 public functions: `trusted_components()`, `register_with_htmy_adapter()`, `asset_paths()`, `asset_urls()`, `template_globals()`). The target layout hoists `adapter.py` to `fastblocks/adapters/templates/htmy_components/adapter.py` at the top level — the empty `fastblocks_htmy/fastblocks/` sub-package is not recreated in fastblocks proper. The resulting `htmy_components/` package has 22 files (24 source - 2 dropped: `fastblocks_htmy/fastblocks/__init__.py` not recreated, no replacement). The `diff -r` integrity gate therefore compares 22 vs 24 files; expected differences are exactly the absence of `fastblocks_htmy/fastblocks/` and the small edits to `__init__.py`.

**Files to create / update:**

- New files (under `fastblocks/adapters/templates/htmy_components/`):
  - `py.typed` — PEP 561 marker (per security-auditor audit, verify `py.typed` exists at every parent package: `fastblocks/`, `fastblocks/adapters/`, `fastblocks/adapters/templates/`, `fastblocks/adapters/templates/htmy_components/`; add any missing markers)
  - `__init__.py` — re-exports the full **34-name** public surface (32 typed component classes + `FastBlocksComponent` base + `__version__`): `Shell, NavList, NavGroups, Drawer, Burger, Alert, Breadcrumb, Button, Card, Checkbox, Column, Columns, Container, Dialog, Field, Footer, Hero, Input, Level, Media, Dropdown, Navbar, Pagination, Progress, Section, Select, Switch, Table, Tabs, Tile, Title, ValidationSummary, FastBlocksComponent, __version__`. **Replace** `_check_fastblocks_ui()` with a soft `warnings.warn(f'fastblocks-ui {installed} outside tested range [0.8, 0.9); behavior undefined', RuntimeWarning, stacklevel=1)` so manual `pip install fastblocks-ui==0.9.0 --force-reinstall` is still surfaced at runtime (per security-auditor audit). Add top-of-file provenance: `__absorbed_from__: fastblocks-htmy@0.5.0 (commit <sha>, fetched 2026-08-21)` (per security-auditor audit, version tags persist across force-pushes; SHA + date for traceability).
  - `base.py` — verbatim copy of `fastblocks_htmy/base.py` (per C2)
  - `ui/` — verbatim copies of `__init__.py`, `_generated.py`, `button.py`, `field.py`, `tabs.py`, `table.py`, `breadcrumb.py`, `dropdown.py`, `select.py`, `navbar.py`, `validation_summary.py` (11 files)
  - `layout/` — verbatim copies of `__init__.py`, `_generated.py`, `container.py`, `columns.py`, `nav_list.py`, `nav_groups.py` (6 files — **`layout/navbar.py` does NOT exist in standalone**; per fastblocks-specialist audit, the layout subpackage has 6 files, not 7)
  - `adapter.py` — adapted from `fastblocks_htmy/fastblocks/adapter.py`. The 5 public functions (`trusted_components()`, `register_with_htmy_adapter()`, `asset_paths()`, `asset_urls()`, `template_globals()`) carry over verbatim. The `depends.resolve("fastblocks", "htmy")` example in the module docstring is removed (same dead-API pattern as kelp/webawesome bug (b)).
- `fastblocks/adapters/templates/htmy.py` — update imports to reference `fastblocks.adapters.templates.htmy_components` instead of any external `fastblocks_htmy` import
- `CHANGELOG.md` — "Absorbed" section under 0.31.x
- `CLAUDE.md` — append to "Real bugs found" / "Architecture" sections

**XSS regression test scope** (per security-auditor audit — the original `instantiate each absorbed component with <script>alert(1)</script>` is field-blind): enumerate the user-controlled renderable surface per component. Cover:

- `attrs: dict[str, Any]` on Button / Container / etc.
- `content: object = None` on Container — pin behavior explicitly: `Container(content='<div>safe</div>')` returns `<div>safe</div>` (no double-escape); `Container(content='<script>')` returns `<script>` (no escape, per Container's "pre-rendered HTML" docstring contract)
- list-valued fields: `Fieldset.entries`, `NavList.items`
- `class_: object = None` accepting a malicious object with `__str__`
- nested rendering: `Dialog(Button(...))`, `Container(Column(Field(...), Field(...)))`

Snapshot the per-component field/test matrix in `tests/__snapshots__/xss_surface.json` so crackerjack gates every release against regression.

**`_generated.py` snapshot regen** (per outside-AI audit): add header comment to absorbed `_generated.py` files naming format `# AUTO-GENERATED snapshot YYYY-MM-DD from fastblocks-ui manifest <version>. Regenerate by running scripts/regenerate_htmy_components.py`. Spec the regen script in a separate ADR (out of scope for this plan).

**Integration Contract (C4):**

- **Triggered from:** C1 and C2 merged.
- **Returns to / updates:** `fastblocks/adapters/templates/htmy_components/` (new package, ~22 files), `fastblocks/adapters/templates/htmy.py`, `pyproject.toml` (if `py.typed` markers need to be added at parent packages), `CHANGELOG.md`, `CLAUDE.md`, `tests/__snapshots__/xss_surface.json` (new file).
- **Demonstrable by:** `diff -r fastblocks/adapters/templates/htmy_components/ /Users/les/Projects/fastblocks-htmy/fastblocks_htmy/ --brief` (excluding `__pycache__`, `*.pyc`) shows only intended reconcile differences (the `__init__.py` docstring additions, `__absorbed_from__` line, replacement of `_check_fastblocks_ui` with soft warning, the `fastblocks_htmy/fastblocks/__init__.py` which is intentionally NOT recreated at the top level — see "Sub-package restructure" note below); `python -c "from fastblocks.adapters.templates.htmy_components import *"` imports all 34 names without error; `python -c "from fastblocks.adapters.templates.htmy_components import Button, Field, Tabs, Table"` works; `python -c "from fastblocks.adapters.templates.htmy_components.layout import Container, Columns"` works; `find fastblocks -name py.typed` returns one marker per package directory (`fastblocks/`, `fastblocks/adapters/`, `fastblocks/adapters/templates/`, `fastblocks/adapters/templates/htmy_components/`); `python -m pytest tests/xss/test_component_xss.py` (new file) passes — every absorbed component escapes per the `xss_surface.json` matrix; `grep -nE "\{self\.[a-z_]+\}" fastblocks/adapters/templates/htmy_components/ui/ fastblocks/adapters/templates/htmy_components/layout/` shows only dataclass fields routed through `fastblocks_ui` helpers; `uv run ty check fastblocks/` "All checks passed!"; `uv run pytest -q -m "not slow" --no-header` ≥ 1714 passed.
- **Rollback signal:** the 0.6.x shim (C5) remains a valid import path indefinitely. `fastblocks` users who depended on the internal module path can `git revert` the C4 absorption commit. `fastblocks-ui` / `htmy` version pins (C1) are independent and remain stable.
- **Observability added:** counter metric `fastblocks_htmy_component_render_total{component=<name>, escaped=true|false}` so any future escape regression is countable; import-time assertion in `htmy_components/__init__.py` that the soft warning is registered (visible at startup log).

### C5 — Cross-repo shim release

**Cross-repo deliverable; coordinated with `les` (the user, sole owner of the standalone repo per `git log` on `/Users/les/Projects/fastblocks-htmy`)** per architecture-council audit. Ship `fastblocks-htmy 0.6.x` to PyPI as a shim-only release that re-exports from `fastblocks`. **Pinned release ordering:** ships within 24 hours of fastblocks 0.31.x publication. **PyPI publish steps are manual** per `crackerjack-version-bumping-manual.md` memory — neither this plan nor any subagent dispatches them; the user owns the PyPI token and the bump/tag/push/publish sequence.

**Files to update in standalone repo:**

- `/Users/les/Projects/fastblocks-htmy/fastblocks_htmy/__init__.py` — replace implementation with the shim:
  ```python
  try:
      from fastblocks.adapters.templates.htmy_components import (
          Button, Field, Tabs, Table, Breadcrumb, Dropdown, Select,
          Navbar, ValidationSummary, Container, Columns, NavGroups,
          NavList, Shell, Drawer, Burger, Alert, Card, Checkbox,
          Column, Dialog, Footer, Hero, Input, Level, Media, Pagination,
          Progress, Section, Switch, Tile, Title, FastBlocksComponent,
          __version__,
      )
  except ImportError as exc:
      raise ImportError(
          "fastblocks-htmy 0.6.x is a shim-only release. Install "
          "fastblocks>=0.31.0 to use the typed components, or pin "
          "fastblocks-htmy<0.6 for the last full implementation."
      ) from exc

  import warnings
  warnings.warn(
      "fastblocks-htmy is deprecated; import from "
      "fastblocks.adapters.templates.htmy_components instead.",
      DeprecationWarning,
      stacklevel=2,
  )
  ```
  (Per security-auditor audit: original said `fastblocks>=0.30.0` — corrected to `0.31.0` because absorption ships in 0.31.x, not 0.30.0.)
- `/Users/les/Projects/fastblocks-htmy/pyproject.toml` — bump to `0.6.0`; update description to "Deprecated shim; install fastblocks>=0.31.0". **Add `[project].dependencies = ["fastblocks>=0.31.0"]`** so `pip install fastblocks-htmy==0.6.0` auto-installs fastblocks and the shim's import-time code can resolve `fastblocks.adapters.templates.htmy_components`. Without this, users hit the spec's documented ImportError fallback.
- After ~30 days post-0.31.0 (NOT post-0.30.0; the shim cycle starts when absorption lands): GitHub "Archived" toggle + `private = true` in pyproject

**Supply-chain mitigations (per security-auditor re-review — REQUIRED before C5 ships):**

The shim is published to PyPI by `les` manually. PyPI package publication is a one-way door: once `fastblocks-htmy==0.6.0` is on PyPI, every `pip install fastblocks-htmy==0.6.x` hits it before any local fastblocks code runs. Without mitigations, a compromised PyPI token or force-push to the standalone repo can replace the shim contents with arbitrary code that runs at import time on every consumer.

Required pre-flight before publishing:

1. **PyPI 2FA confirmed active** on the `les` account. Verify at https://pypi.org/manage/account/. If 2FA is not configured, configure it before publishing — without 2FA, a phished token publishes a malicious 0.6.x.
1. **PEP 740 attestations enabled** for the project (`pyproject.toml` `[project].attestations = { source = "publish" }` or similar). This provides cryptographic proof of the wheel's origin and contents.
1. **Hash-pinned install** for any CI / production install of `fastblocks-htmy==0.6.x`: `pip install --require-hashes -r requirements-htmy-shim.txt` where the requirements file lists `--hash=sha256:...` for each wheel. This catches a malicious replacement even if PyPI serves a different wheel.
1. **Threat model documented** in a one-line entry under CHANGELOG.md or the spec's Migration notes: "fastblocks-htmy 0.6.x is a security-sensitive shim; users in production environments must use hash-pinned installs."

These mitigations apply to anyone installing the shim from PyPI, not just the publishing side.

**Coordination contract (per architecture-council audit):**

- Owner: `les` (single-owner; verified via `git -C /Users/les/Projects/fastblocks-htmy log --format='%an' | sort -u`)
- Release ordering: ships within 24h of fastblocks 0.31.0 publication
- PyPI publish: manual sequence (build, twine upload, manual version bump) per `crackerjack-version-bumping-manual.md`
- Standalone-repo pre-flight: `git -C /Users/les/Projects/fastblocks-htmy status` must be clean before starting C5; if dirty, abort and surface

**Integration Contract (C5):**

- **Triggered from:** fastblocks 0.31.x release candidate green + standalone repo's main is clean + PyPI publish credentials verified.
- **Returns to / updates:** `/Users/les/Projects/fastblocks-htmy/fastblocks_htmy/__init__.py`, `/Users/les/Projects/fastblocks-htmy/pyproject.toml`, GitHub "Archived" toggle (deferred ~30 days post-release).
- **Demonstrable by:** `pip install fastblocks-htmy==0.6.0 && python -c "from fastblocks_htmy import Button; print(Button)"` re-exports from `fastblocks` and emits `DeprecationWarning`; `pip install fastblocks-htmy==0.6.0 && python -c "from fastblocks_htmy import FastBlocksComponent"` works; `pypi show fastblocks-htmy` reports version `0.6.0` and the deprecation notice.
- **Rollback signal:** the 0.6.x shim remains a valid import path indefinitely. If the shim itself ships broken, the rollback procedure is: yank `fastblocks-htmy==0.6.0` from PyPI (manual, per `crackerjack-version-bumping-manual.md`) and publish `0.6.1` with the fix. The standalone repo's `main` branch can be `git reset --hard` to the previous commit (Bodai pre-1.0 policy permits this for unpushed commits; for already-pushed commits, force-push is required).
- **Observability added:** `pypistats` download counter for `fastblocks-htmy` trending to zero over 30 days (proxy for users migrating to the absorbed package); DeprecationWarning counter on `import fastblocks_htmy` (already in place via the shim itself); GitHub "Archived" badge visible in repo header.

## Ordering within 0.31.x

C1 → C2 → C4 → C5. Each sub-task commits independently with its own verification gate so partial failures can be bisected.

## Verification gates (every commit)

- `uv run ty check fastblocks/` → "All checks passed!"
- `uv run pytest -q -m "not slow" --no-header` → ≥ 1714 passed, 0 fail
- `uv run crackerjack run` → ty PASS, refurb PASS, ruff PASS

**Task-specific gates:**

| After | Gate | Expected |
|---|---|---|
| C1 | `git grep -nE "fastblocks-htmy\|fastblocks_htmy" pyproject.toml` | 0 hits in `[project.dependencies]`; only in dev/test groups if at all |
| C1 | `git grep -n "~=0.9" pyproject.toml \| grep htmy` | 0 hits (old pin replaced) |
| C1 | `git grep -n "htmy" pyproject.toml` | shows `>=0.13,<0.14` with `lxml` extra |
| C1 | `uv pip install -e .` | resolves without warning |
| C1 | `python -c "import fastblocks; import htmy; import fastblocks_ui"` | succeeds |
| C2 | `python -c "from fastblocks.adapters.templates.htmy_components import FastBlocksComponent; from fastblocks.adapters.templates._htmy_components import ComponentBase"` | works |
| C4 | `diff -r fastblocks/adapters/templates/htmy_components/ /Users/les/Projects/fastblocks-htmy/fastblocks_htmy/ --brief` (excluding `__pycache__`) | only intended reconcile differences |
| C4 | `python -c "from fastblocks.adapters.templates.htmy_components import *"` | all 34 names importable (32 components + `FastBlocksComponent` + `__version__`) |
| C4 | `python -c "from fastblocks.adapters.templates.htmy_components import Button, Field, Tabs, Table"` | works |
| C4 | `python -c "from fastblocks.adapters.templates.htmy_components.layout import Container, Columns"` | works |
| C4 | `find fastblocks -name py.typed` | one marker per package directory |
| C4 | `python -m pytest tests/xss/test_component_xss.py` | passes — every absorbed component escapes per `xss_surface.json` |
| C4 | `grep -nE "\{self\.[a-z_]+\}" fastblocks/adapters/templates/htmy_components/ui/ fastblocks/adapters/templates/htmy_components/layout/` | only dataclass fields routed through `fastblocks_ui` helpers |
| C4 | `grep -rnE "layout/navbar" fastblocks/adapters/templates/htmy_components/` | 0 hits (file doesn't exist; verify the layout/ subpackage matches the standalone's 6 files) |
| C5 | `pip install fastblocks-htmy==0.6.0 && python -c "from fastblocks_htmy import Button; print(Button)"` | re-exports from `fastblocks`; emits `DeprecationWarning` (note: `--upgrade` if 0.5.x already installed) |
| C5 | `pip install fastblocks-htmy==0.6.0 && python -c "from fastblocks_htmy import FastBlocksComponent"` | works (33rd name covered by shim) |
| C5 | `pypi show fastblocks-htmy` | reports version `0.6.0` and the deprecation notice |

## Integration Contract (Release 2)

- **Triggered from:** fastblocks 0.30.0 merged + PyPI reverse-deps confirmation (libraries.io + pypistats + GitHub code search) + pre-merge analysis complete + standalone repo's main is clean + Deliverable B's `fastblocks_ui = [...]` group is gone.
- **Returns to / updates:** per-task ICs above (C1, C2, C4, C5). Release-level scope = union.
- **Demonstrable by:** `python -c "from fastblocks.adapters.templates.htmy_components import Button"` works; `python -c "from fastblocks.adapters.templates.htmy_components.layout import Container, Columns"` works; `python -c "from fastblocks.adapters.templates.htmy_components import *"` imports all 34 names without error; XSS regression test passes (every absorbed component escapes per `xss_surface.json`); after C5 ships, `pip install fastblocks-htmy==0.6.0 && python -c "from fastblocks_htmy import Button"` re-exports from `fastblocks` and emits `DeprecationWarning`.
- **Rollback signal:** the 0.6.x shim remains a valid import path indefinitely. `fastblocks` 0.31.x users who depended on the internal module path can `git revert` the C4 absorption commit. `fastblocks-ui` / `htmy` version pins (C1) are independent. C5 rollback = yank + republish as 0.6.1.
- **Observability added:** union of per-task observability. CHANGELOG 0.31.x "Absorbed" section; standalone `fastblocks-htmy` GitHub repo gets "Archived" toggle ~30 days post-release; CLAUDE.md updated to reflect the absorption under "Real bugs found" / "Architecture" sections; runtime counter `fastblocks_htmy_component_render_total`; pypistats download trending-to-zero.

______________________________________________________________________

# Cross-cutting concerns

## Process

Subagent-Driven Development per CLAUDE.md:

0. **Commit the plan** to `docs/superpowers/plans/2026-08-21-style-renderer-architecture.md` on the working branch before dispatching any implementer subagent. Pin the commit SHA in the dispatched task brief. (Per outside-AI audit.)
1. Spec approved at `/Users/les/Projects/fastblocks/docs/superpowers/specs/2026-08-21-style-renderer-architecture.md` (covering A+B+C1+C2+C3+C4+D as one cohesive design).
1. Plan = this document. One task per sub-task (A, B, C1, C2, C3, C4, C5, D).
1. Execute task-by-task with a fresh implementer subagent per task + scoped reviews.
1. Commit per task. Pre-existing dirty files stay out of every commit.
1. **Each task commit must include an Integration Contract block per CLAUDE.md §Process Discipline** — use the per-task ICs in this plan as templates. Implementer subagents should be told in their brief: "Your task's IC block defines what 'done' means."

## Worktree quarantine

Each task commits in its own worktree to isolate from any pre-existing
dirty state:

```bash
# From the cleanest available ref. Bodai merges are direct to main, so
# `git log` may already have landed work — use git worktree to isolate.
git worktree add ../fastblocks-taskX -b task/X clean_commit_sha
cd ../fastblocks-taskX
```

If `git worktree add` fails or is disabled, fall back to:

```bash
git stash -u --keep-index --include-untracked -m "WIP: quarantine before style/renderer spec"
```

Do NOT improvise; the spec fallback is the only sanctioned alternative.

**Landing procedure** (per architecture-council audit): from the main checkout
after the task's commit is ready on its branch, run:

```bash
# From the main checkout (which has the unrelated dirty state):
git fetch ../fastblocks-taskX task/X:refs/tasks/X
git merge --ff-only refs/tasks/X
```

This avoids `git checkout main` in a dirty tree (which would clobber files
per `git-stash-and-checkout-collision.md` memory) and avoids `git stash`
mid-stream (which risks drift-bundling per `drift-bundling-recovery.md`
memory).

Every task commit uses targeted `git add <pathspec>` (never `git add -A`,
`git commit -a`). This is a hard-don't from CLAUDE.md and per
`drift-bundling-recovery.md` memory.

## Real-bug policy

When a task surfaces code calling an API that doesn't exist, HTML output that
fails to escape user input, or any other silent-failure pattern:

1. **Stop** — don't silently fix.
1. **Surface** — name the file, line, the wrong behavior, and the corrected behavior.
1. **Ask** — confirm whether the code path is exercised or dead.
1. **Document** — append to the spec's "Real bugs found" section.

## Hard don'ts

- Do NOT touch any pre-existing dirty files in the working tree. They belong to other work. (At the time of this plan's writing, the only working-tree changes are the new spec + plan files; both are intentional and don't need quarantining.)
- Do NOT re-introduce the `try/except ImportError: SandboxedEnvironment = Environment` pattern from before the ty-cleanup. If you see any reference to that pattern, surface it.
- Do NOT add `# type: ignore` or `# ty: ignore` to make ty pass. Convert to proper annotations.
- Do NOT amend or rewrite any published commit. Bodai merges directly to main pre-1.0; preserve the linear log.
- Do NOT push to main until ty + pytest + crackerjack are all green.
- Do NOT delete `/Users/les/Projects/fastblocks-htmy/` (the source files are absorbed; the standalone repo is archived separately after ~30 days).
- Do NOT pin `fastblocks-htmy` as a runtime dep of `fastblocks` (creates self-referential dep per spec C1).
- Do NOT full-revert a 0.30.0 release to roll back style-only changes; revert A/B/D only (C3's revert restores the RCE vector).
- **Do NOT `git revert` the C3 commit under any circumstance** — the RCE vector is restored immediately. If C3 regresses, ship a forward-fix patch with documented security review (see C3's rollback signal). Each task must commit independently — never bundle A/B/D with C3 in a single commit.
- Do NOT copy-paste `_load_from_source` minus the `importlib.util` guard as a "replacement" in C3; route through the AST-sandboxed `load_component_from_source()` from `_htmy_components.py`.

## Reviewer checklist (per task commit)

For each task commit dispatched for review, the read-only reviewer verifies:

- (a) `git diff --stat HEAD~1` lists only files in the task's spec/plan section
- (b) `uv run ty check fastblocks/` returns 0 diagnostics
- (c) `uv run pytest -q -m "not slow"` returns ≥ 1714 passed
- (d) Task-specific verification gates pass (per the tables above)
- (e) CHANGELOG and CLAUDE.md updates present per the Files to update list
- (f) No `fastblocks-htmy` runtime dep added (per C1 fix)
- (g) No `try/except ImportError: SandboxedEnvironment = Environment` pattern re-introduced
- (h) For C3 specifically: `get_component_class` at `htmy.py:279-298` was rewritten to route through `load_component_from_source()`, not just deleted
- (i) For C4 specifically: XSS test covers `attrs`, `content` (with the escape-by-default contract pinned), list-valued fields, nested rendering

## Reference artifacts

- Spec for this plan: `/Users/les/Projects/fastblocks/docs/superpowers/specs/2026-08-21-style-renderer-architecture.md`
- Spec for the just-completed ty cleanup (template for spec structure): `/Users/les/Projects/fastblocks/docs/superpowers/specs/2026-08-20-fastblocks-ty-cleanup-design.md`
- Plan for the just-completed ty cleanup (template for plan structure): `/Users/les/Projects/fastblocks/docs/superpowers/plans/2026-08-20-fastblocks-ty-cleanup.md`
- Source of `fastblocks-htmy` to absorb: `/Users/les/Projects/fastblocks-htmy/fastblocks_htmy/`
- CLAUDE.md known-bug note for kelp/webawesome: lines 234-235 (silent failure + XSS surface)
- Working style adapter for `fastblocks-ui` (model after this): `/Users/les/Projects/fastblocks/fastblocks/adapters/style/fastblocks_ui.py`
- Existing legacy htmy components module (the partial to reconcile with): `/Users/les/Projects/fastblocks/fastblocks/adapters/templates/_htmy_components.py`
- Existing legacy htmy templates adapter (RCE vector lives here, partially closed by C3): `/Users/les/Projects/fastblocks/fastblocks/adapters/templates/htmy.py`
- AppBaseSettings (the `style: str = "vanilla"` line that changes in Deliverable B): `/Users/les/Projects/fastblocks/fastblocks/adapters/app/_base.py:12`
- pyproject.toml (the optional `fastblocks_ui = [...]` group that moves in Deliverable B; the existing `htmy[lxml]~=0.9` that gets replaced in C1): `/Users/les/Projects/fastblocks/pyproject.toml`
- Standalone `fastblocks-htmy` pyproject.toml (for transitive pin ranges): `/Users/les/Projects/fastblocks-htmy/pyproject.toml`

______________________________________________________________________

# Fresh-session prompt (paste verbatim into a new session)

```
# Task: FastBlocks style/renderer architecture consolidation (two releases)

**Working directory:** `/Users/les/Projects/fastblocks` (main branch)
**Pre-existing state:** ty-cleanup just finished — 0 ty diagnostics, pytest 1714 passing, HEAD is `ffef487` (post-ty-cleanup + version bump). Working tree currently shows ONLY the two new files `docs/superpowers/{plans,specs}/2026-08-21-style-renderer-architecture.md` (intentional, do NOT delete). No other dirty files at the time of this plan's writing.

**CRITICAL: do your work in a worktree**, not in `/Users/les/Projects/fastblocks` directly. From the main checkout, run `git worktree add ../fastblocks-taskX -b task/X ffef487` before starting any task. Landing procedure documented in the plan's "Worktree quarantine" section.

## TL;DR

Collapse 4 styles to 2 (drop kelp/bulma/webawesome/custom), promote fastblocks-ui to default, close htmy.py RCE, absorb fastblocks-htmy. Two releases: 0.30.0 fixes, 0.31.x absorption.

## Context

Three architectural decisions were made about the style adapter layer and need to be executed across two releases:

**Release 1: fastblocks 0.30.0 — independent fixes:**
1. **Drop `kelp`, `bulma`, `webawesome`, `custom` style adapters** (Deliverable A). Per CLAUDE.md:234, kelp and webawesome have three masked bugs; bulma and custom lack backing adapters. All silent-fail. After A, only `vanilla` and `fastblocks_ui` remain.
2. **Promote `fastblocks-ui` to the default style layer** (Deliverable B). Pin `>=0.8,<0.9`. Move from optional dep group to `[project].dependencies`. Change `AppBaseSettings.style` default to `"fastblocks_ui"`.
3. **Close the live RCE in `htmy.py`** (Deliverable C3). Three steps: delete `_load_from_cached_bytecode` and `_load_from_source`; rewrite `get_component_class` at `htmy.py:279-298` to route through `load_component_from_source()` from `_htmy_components.py`; audit tests.
4. **Document the future `renderer` axis** (Deliverable D, doc-only). Update `style_registry.py` docstring.

**Release 2: fastblocks 0.31.x — absorption mechanics:**
5. **Pin transitive deps directly** (Deliverable C1). Edit (not add) the existing `htmy[lxml]~=0.9` to `htmy[lxml]>=0.13,<0.14`. Do NOT add `fastblocks-htmy` to `[project].dependencies`.
6. **Reconcile base classes** (Deliverable C2). `FastBlocksComponent` (from `fastblocks_htmy/base.py`) becomes the canonical base. `_htmy_components.ComponentBase` is preserved for the legacy registry path. NOT interchangeable.
7. **Absorb source and verify** (Deliverable C4). Move 24 source files from `/Users/les/Projects/fastblocks-htmy/fastblocks_htmy/` into `fastblocks/adapters/templates/htmy_components/`. Replace `_check_fastblocks_ui()` with a soft warning. Add per-component XSS regression test. Update `htmy.py` to import from internal module. Re-export all 34 names (32 components + `FastBlocksComponent` + `__version__`).
8. **Ship cross-repo shim release** (Deliverable C5). `fastblocks-htmy 0.6.x` becomes a shim. Owner: `les`. Ships within 24h of fastblocks 0.31.x publication. Manual PyPI publish per `crackerjack-version-bumping-manual.md`.

User-confirmed: zero external consumers. The cross-release split exists for reviewable-commit and rollback-granularity reasons, not deprecation-cycle reasons (no 0.29.x intermediate warning).

## Required deliverables

See `/Users/les/Projects/fastblocks/docs/superpowers/plans/2026-08-21-style-renderer-architecture.md` for the per-task Files to update lists, per-task Integration Contract blocks, and verification gates. The plan also references the spec at `/Users/les/Projects/fastblocks/docs/superpowers/specs/2026-08-21-style-renderer-architecture.md` for the underlying rationale.

**Release 1 tasks (0.30.0):** A, B, C3, D. A, B, C3 are independent; D requires A+B.
**Release 2 tasks (0.31.x):** C1, C2, C4, C5 in that order. Pre-conditions: 0.30.0 merged; libraries.io + pypistats + GitHub code search confirms zero external consumers; pre-merge analysis of base-class collisions complete; standalone repo's main is clean; Deliverable B's `fastblocks_ui = [...]` group is gone.

## Verification gates (every commit)

- `uv run ty check fastblocks/` → "All checks passed!" (do NOT add suppressions)
- `uv run pytest -q -m "not slow" --no-header` → 1714 passed, no regression
- `uv run crackerjack run` → ty PASS, refurb PASS, ruff PASS

Task-specific gates listed in the plan.

## Hard don'ts

- Do NOT full-revert 0.30.0 to roll back style-only changes (C3 revert restores the RCE vector); revert A/B/D only.
- Do NOT copy-paste `_load_from_source` minus the `importlib.util` guard as a "replacement" in C3.
- Do NOT pin `fastblocks-htmy` as a runtime dep of `fastblocks` (C1 fix).
- Do NOT delete `/Users/les/Projects/fastblocks-htmy/` (archived separately after ~30 days).
- Do NOT add `# type: ignore` or `# ty: ignore` to make ty pass.
- Do NOT amend or rewrite any published commit. Bodai merges directly to main pre-1.0.

## Each commit must include an Integration Contract block

Per CLAUDE.md §Process Discipline, every task commit must include an Integration Contract (Triggered from / Returns to / updates / Demonstrable by / Rollback signal / Observability added). Use the per-task ICs in the plan as templates. If you find yourself writing a commit without an IC, stop and add it.

## Reference artifacts

- Plan: `/Users/les/Projects/fastblocks/docs/superpowers/plans/2026-08-21-style-renderer-architecture.md`
- Spec: `/Users/les/Projects/fastblocks/docs/superpowers/specs/2026-08-21-style-renderer-architecture.md`
- Source of `fastblocks-htmy` to absorb: `/Users/les/Projects/fastblocks-htmy/fastblocks_htmy/`
- CLAUDE.md known-bug note for kelp/webawesome: lines 234-235
- Working style adapter for `fastblocks-ui` (model after this): `/Users/les/Projects/fastblocks/fastblocks/adapters/style/fastblocks_ui.py`
- Existing legacy htmy components module (the partial to reconcile with): `/Users/les/Projects/fastblocks/fastblocks/adapters/templates/_htmy_components.py`
```
