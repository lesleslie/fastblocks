# FastBlocks Style/Renderer Architecture Consolidation

**Date:** 2026-08-21
**Status:** Approved 2026-08-21 after 4-reviewer adversarial review + plan audit (security-auditor, architecture-council, fastblocks-specialist, outside-AI)
**Branch:** in-place on fastblocks main
**Repository:** `/Users/les/Projects/fastblocks`
**Target versions:** `fastblocks 0.30.0` (style cleanup + default flip + RCE fix — MAJOR bump: silent→loud break for `style="kelp"`/`"webawesome"` users; optional→required promotion of `fastblocks-ui` and `htmy`) + `fastblocks 0.31.x` (absorption + cross-repo shim).

## Context

`fastblocks/adapters/style/` today ships four style adapters — `vanilla`, `kelp`, `webawesome`, `fastblocks_ui` — and `config.app.style: str = "vanilla"` (`fastblocks/adapters/app/_base.py:12`) is the default. Three of them are wrong in different ways:

1. **`kelp` and `webawesome` are silent-failure traps** (CLAUDE.md:234-235). Each carries *three* independent bugs:

   - (a) `register_kelp_functions` / `register_webawesome_functions` call `@env.global_(...)` and `@env.filter(...)` as if those were Jinja `Environment` decorator methods. They are not — confirmed by grepping every installed package under `.venv/`. The real API is plain `env.globals[name] = func` / `env.filters[name] = func` assignment, which is what `init_envs()` and `fastblocks_ui.py` both use.
   - (b) Their closures call `depends.get_sync("styles")` / `depends.set(...)` on a `oneiric.core.resolution.Resolver` that exposes only `register(candidate)` / `resolve(domain, key, ...)`. The methods don't exist on the installed `oneiric 0.3.x`.
   - (c) XSS surface (CLAUDE.md:235): `kelp.py`'s `_build_kelp_component_html` / `kelp_component()` and `webawesome.py`'s `wa_button()` / `wa_card()` interpolate `content` / `text` / attributes straight into f-strings with no HTML escaping. Currently masked by both dead-code bugs above — once (a)/(b) are fixed and these helpers actually get invoked from a real Jinja environment, every component output becomes a live XSS vector if any of that content comes from user input.

   All three bugs are silently swallowed by `with suppress(Exception)` at the call sites, so selecting `style="kelp"` or `style="webawesome"` registers nothing. These are not legacy waiting to be revived; they are traps.

2. **`fastblocks_ui` is the only working style adapter** (`fastblocks/adapters/style/fastblocks_ui.py`). It uses the real Jinja API, lazy-imports `fastblocks_ui` (optional dep), resolves real shipped CSS/JS asset paths via `fastblocks_ui.get_css_path()` / `get_js_path()`, delegates class lookups to the real component manifest, and delegates rendering to the real (already-escaping) `fastblocks_ui` helpers. But it lives in an optional dependency group (`fastblocks_ui = ["fastblocks-ui>=0.7,<0.8"]` at `pyproject.toml:102-109`) and requires an opt-in `config.app.style = "fastblocks_ui"` to activate. The "safe default" is unstyled.

3. **`fastblocks-htmy` is a separate PyPI package** at `/Users/les/Projects/fastblocks-htmy/` — 24 source files across `fastblocks_htmy/` (`__init__.py`, `base.py`, `adapter.py`, `py.typed`), a nested `fastblocks_htmy/fastblocks/` (`__init__.py`, `adapter.py`), and `fastblocks_htmy/{ui,layout}/*.py` for typed components. It depends on `fastblocks-ui>=0.8,<0.9` + `htmy[lxml]>=0.13,<0.14` (the standalone's actual pins — `[lxml]` extra is required by the AST-sandboxed source loader) and ships a `py.typed` PEP 561 marker. It is **not** a competing CSS framework — it is a typed component layer on top of `fastblocks-ui`'s CSS. There are zero known non-fastblocks consumers (see "Pre-conditions" below for verification).

4. **`htmy.py` retains an active RCE vector** that the spec must close (this is a NEW critical finding from review). `fastblocks/adapters/templates/htmy.py:300-354` (`_load_from_cached_bytecode`) and `htmy.py:356-399` (`_load_from_source`) both use `importlib.util.spec_from_file_location()` + `spec.loader.exec_module()` — the exact RCE-vector path that CLAUDE.md:130 documents as removed by Phase 1.3's AST-sandboxed loader in `_htmy_components.py`. The advanced registry in `_htmy_components.py` correctly routes through `load_component_from_source()` (AST-sandboxed), but `HTMYTemplates.render_component` falls back to the legacy `HTMYComponentRegistry` for any path that doesn't go through `render_component_advanced`, so the unsafe path is still reachable. Task C must delete it.

A second-order issue: `style` confuses two distinct axes — *where CSS comes from* and *how Python types become HTML*. `kelp` and `webawesome` are the symptom; the cause is the conflation.

## Goals

- Drop the broken `kelp` and `webawesome` style adapters and all their references (adapters, CLI enum, README, tests, template variants, backup files). Users configured to those values will fail loudly with `unknown style` from `style_registry.py` immediately at 0.30.0 upgrade — the correct behavior for removed APIs. (With user-confirmed zero external consumers, no deprecation-cycle intermediate release is needed.)
- Promote `fastblocks-ui` to the default style layer and a regular runtime dependency, pinning the version range the standalone `fastblocks-htmy` already requires (`>=0.8,<0.9`) so transitive resolution stays consistent.

**Goals for 0.31.x (absorption + cross-repo shim):**
- Absorb the standalone `fastblocks-htmy` PyPI package source into `fastblocks`. Drop `fastblocks-htmy` from `[project].dependencies` entirely (the spec does NOT pin the package being absorbed — that creates a self-referential dep and dual source of truth). Pin `htmy[lxml]>=0.13,<0.14` and `fastblocks-ui>=0.8,<0.9` directly. The standalone `fastblocks-htmy 0.6.x` becomes a shim-only release that re-exports from `fastblocks.adapters.templates.htmy_components`. (Lives in 0.31.x — NOT 0.30.0. The 0.30.0 release has no absorption.)
- Close the active RCE vector in `htmy.py` (Finding 2 from fastblocks-specialist review). **This ships in 0.30.0**, not 0.31.x — the RCE fix is independent of the absorption.

**Goals spanning both releases:**
- Introduce the architectural separation: `style` means CSS source only (`vanilla` | `fastblocks_ui`); the `renderer` axis (`jinja2` | `htmy`) is documented as the next-iteration north star but not introduced as a config in this PR.
- Keep `vanilla` as an explicit opt-in for unstyled apps.
- **Behavioral verification:** gates must prove the *user-facing behavior* changed, not just that types and imports resolve. New tests cover (i) default-styled rendering emits the right HTML, (ii) `style="kelp"` raises with the documented message, (iii) absorbed components render escaped output for user-supplied payloads.
- All intermediate phases leave the working tree and test suite green.
- **Do not delete** the standalone `fastblocks-htmy` repo in this PR — that's a separate decision after the shim cycle (see Migration notes).

## Non-goals

- Refactoring unrelated to the style/renderer axis.
- Fixing `StyleBase` / `StyleBaseSettings` internals beyond what's required to delete the broken adapters.
- Replacing the AST-sandboxed source loader (`load_component_from_source` in `_htmy_components.py`). That loader is the security-critical RCE-vector mitigation from Phase 1.3 and is preserved untouched. The RCE-vector closure in Task C is about the *separate* `spec_from_file_location + exec_module` path in `htmy.py`, which is NOT the AST-sandboxed loader.
- Touching the ~40 pre-existing dirty files in the working tree (quarantined per the dirty-tree isolation procedure below).
- Re-introducing the `try/except ImportError: SandboxedEnvironment = Environment` pattern from before the ty-cleanup.
- Adding `# type: ignore` or `# ty: ignore` to make ty pass. Convert to proper annotations.
- Amending or rewriting any published commit. Bodai merges directly to main pre-1.0; preserve the linear log.
- Pushing to main until ty + pytest + crackerjack are all green.
- Deleting `/Users/les/Projects/fastblocks-htmy/` (separate decision; see Migration notes).

## Architecture (target)

| Axis | Today | Target |
|---|---|---|
| `style` (CSS source) | 4 options, 2 broken traps | 2 options, both correct (`vanilla`, `fastblocks_ui`) |
| `renderer` (component model) | conflated under `style` | separate axis; documented north star only in this PR |

`AppBaseSettings.style: str = "fastblocks_ui"` is the new default. `vanilla` remains as an explicit opt-in for unstyled apps.

The `renderer` axis is documented in `fastblocks/core/style_registry.py`'s docstring as the unifying abstraction: `style` × `renderer` becomes a 2×2 matrix where every cell is either coherent or unavailable. Concrete renderer values (`jinja2` | `htmy`) and their interaction with `style` are out of scope for this PR — only the axis is named.

## Approach

### Sequencing rules

- One task at a time. Do not start task N+1 until task N's verification gates pass AND task N+1's pre-conditions (cross-task deps) hold.
- **Cross-task preconditions:**
  - Task B → no precondition.
  - Task C → **MUST NOT begin until Task B's `pyproject.toml` change is committed AND `python -c "import fastblocks_ui; print(fastblocks_ui.__version__)"` succeeds with `[project].dependencies` resolving `fastblocks-ui` as a non-optional dep** (the absorbed components transitively require `fastblocks-ui` at import time).
  - Task D → no precondition beyond A+B+C green.
- Pre-existing dirty files stay out of every commit. Quarantine procedure below.

### Dirty-tree quarantine procedure

Before Task A's implementer subagent starts:

```bash
# From the cleanest available ref. Bodai merges are direct to main, so
# `git log` may already have landed work — use git worktree to isolate.
git worktree add ../fastblocks-taskA -b task/A clean_commit_sha
cd ../fastblocks-taskA
# All Task A work happens in the worktree. The main checkout's dirty
# files remain untouched. Same procedure for B, C, D.
```

If worktrees aren't available, use:

```bash
# Stash dirty state into a single quarantine commit before Task A.
git stash -u --keep-index --include-untracked -m "WIP: quarantine before style/renderer spec"
git add -p  # interactively stage ONLY the quarantine diff; reject everything else
git commit -m "WIP: pre-spec quarantine"
```

Every task commit uses targeted `git add <pathspec>` (never `git add -A`, `git commit -a`). This is a hard-don't from CLAUDE.md and per `drift-bundling-recovery.md` memory.

### Task A — Style layer cleanup (delete kelp + webawesome)

**Files to delete** (per `git ls-files fastblocks/ | grep -iE "kelp|webawesome"`):

- `fastblocks/adapters/style/kelp.py` (~900 lines)
- `fastblocks/adapters/style/kelp.py.backup` (54-byte metadata sidecar; safe to delete with the parent)
- `fastblocks/adapters/style/kelp.py.backup.json` (if present)
- `fastblocks/adapters/style/webawesome.py` (~650 lines)
- `fastblocks/adapters/style/webawesome.py.backup` (if present)
- `fastblocks/cli.py.backup` (contains a stale `webawesome` enum entry mirroring `cli.py`)
- `fastblocks/adapters/app/_templates/kelp/` (whole directory; contains `components/__init__.py`)
- `fastblocks/adapters/app/_templates/webawesome/` (whole directory)

**Files to update:**

- `fastblocks/core/style_registry.py` — drop the long "Note for anyone writing a new `register_<name>_functions`" docstring passage that exists specifically to explain why kelp/webawesome would raise `AttributeError`. Keep the defensive `with suppress(Exception)` rationale for legitimate silent-no-op styles (e.g. `vanilla`).
- `fastblocks/adapters/style/__init__.py` — drop `kelp`, `webawesome` from `__all__` / re-exports.
- `fastblocks/adapters/style/README.md` — drop mentions; rewrite per-style sections.
- `fastblocks/cli.py:62-65` — `Styles(StrEnum)` currently has only `bulma = "bulma"`, `webawesome = "webawesome"`, `custom = "custom"` (verified — no `vanilla` or `fastblocks_ui` members exist). Drop `bulma`, `webawesome`, `custom`. Add `vanilla = "vanilla"` and `fastblocks_ui = "fastblocks_ui"` so the enum reflects the 2 surviving styles. After the change, replace the `StrEnum` with `Literal["vanilla", "fastblocks_ui"]` for stronger static guarantees. Also update `cli.py:929, 957, 1079, 1093` which reference `Styles.bulma` as the default arg — replace with `Styles.vanilla` (or the new default).
- `CHANGELOG.md` — add a "Removed" section under 0.30.0 calling out the silent-failure hazard + XSS surface as the reason. State the loud-fail upgrade path.
- `CLAUDE.md` — append to the "Real bugs found" section (around line 234-235): a deprecation note documenting that kelp/webawesome were removed in 0.30.0 because they were broken dead code with a masked XSS surface, and that prior `style=kelp` / `style=webawesome` configurations now fail loudly with `unknown style` from `style_registry.py`.
- `README.md` — strip the kelp/webawesome mentions at lines 1139 and 1390; replace with `vanilla` / `fastblocks_ui`.
- `tests/adapters/styles/test_styles_comprehensive.py` — remove the `from fastblocks.adapters.style.webawesome import (WebAwesomeStyle, WebAwesomeStyleSettings)` import at lines 8-11. There is no single `TestWebAwesomeStyle` class to delete; `WebAwesomeStyle` and `WebAwesomeStyleSettings` are used inline in `TestStyleIntegration` (around line 154) at lines 159, 172, 189, 204, 217, 218, 251. Drop `WebAwesomeStyle` and `WebAwesomeStyleSettings` from the `adapters = [...]` lists; drop the `test_settings_customization` WebAwesome branch (lines 216-223, including the `webawesome.settings = WebAwesomeStyleSettings()` assignment); drop the framework-switching assertions on `webawesome_button` (lines 189-200).
- `tests/adapters/style/test_fastblocks_ui_style.py` — audit any test that assumed `vanilla` as the default. Update.

**Verification (after A):**

- `git ls-files --modified --others --cached fastblocks/ settings/ | xargs grep -n "kelp\|webawesome\|KelpStyle\|WebAwesomeStyle"` → no hits (scope excludes pre-existing dirty state, per Fb-spec F16)
- `find fastblocks/ -type f \( -name "*.html" -o -name "*.jinja2" -o -name "*.tmpl" \) -exec grep -l "kelp\|webawesome" {} \;` → empty (template variant grep, per Fb-spec F4)
- `uv run ty check fastblocks/` → "All checks passed!"
- `uv run pytest -q -m "not slow" --no-header` → ≥ 1714 passed, 0 fail (≥ because the audit may add tests; record the new baseline in CHANGELOG if it changes)
- `python -c "from fastblocks.adapters.app._base import AppBaseSettings; AppBaseSettings().model_dump()"` → exits 0 (settings import doesn't reference removed adapters)
- `python -c "from fastblocks.adapters.style import vanilla, fastblocks_ui"` → both import without raising (kelp/webawesome import paths fail loudly — the desired behavior)

### Task B — Promote fastblocks-ui to default

**Files to update:**

- `pyproject.toml` — move `"fastblocks-ui>=0.8,<0.9"` (NOTE: corrected from the plan's `>=0.7,<0.8`, which conflicts with the version range the standalone `fastblocks-htmy` already requires — see "Pre-conditions" below) from the optional `fastblocks_ui = [...]` group into `[project].dependencies` directly. Delete the `fastblocks_ui = [...]` group entirely.
- `fastblocks/adapters/app/_base.py:12` — change `style: str = "vanilla"` to `style: str = "fastblocks_ui"`.
- `tests/adapters/style/test_fastblocks_ui_style.py` — audit tests assuming `vanilla` default. Update.

**Pre-flight gate (must pass BEFORE the pyproject change is committed):**

```bash
uv pip install 'fastblocks-ui>=0.8,<0.9'
python -c "import fastblocks_ui; assert callable(fastblocks_ui.get_css_path); assert callable(fastblocks_ui.get_js_path)"
```

If the helpers don't exist in the pinned range, the task fails — do not commit with a placeholder or `# type: ignore`.

**Verification (after B):**

- `git grep -n "fastblocks_ui =" pyproject.toml` → no hits (the optional group is gone)
- `git grep -n "fastblocks-ui" pyproject.toml` → exactly one hit, in `[project].dependencies`
- `python -c "from fastblocks.adapters.style import fastblocks_ui; print(fastblocks_ui.__version__)"` works
- `uv run crackerjack run` → ty PASS, refurb PASS, ruff PASS
- `uv run pytest -q -m "not slow" --no-header` → ≥ 1714 passed, 0 fail

### Task C — Collapse fastblocks-htmy into fastblocks

This is the largest task. It is decomposed into 4 sub-tasks; each gets its own commit and verification gate so partial failures can be bisected (per AI H4).

**Pre-conditions:**

- Task B must be merged (per Sequencing rules).
- `fastblocks-htmy`'s PyPI reverse-deps query must return zero non-Bodai projects (per Arch F8). **`pip install --dry-run` does NOT query reverse deps** — it only resolves forward dependencies. Use this 4-source protocol (cross-reference all four):
  ```bash
  # 1. Direct deps declared by fastblocks-htmy 0.5.x (forward deps only)
  curl -s https://pypi.org/pypi/fastblocks-htmy/0.5.0/json | jq '.info.requires_dist'
  # 2. Actual reverse-deps source — dependent repos
  curl -s https://libraries.io/pypi/fastblocks-htmy/dependents
  # 3. Download counts as proxy for active users
  curl -s https://pypistats.org/api/packages/fastblocks-htmy/recent
  # 4. GitHub code search
  open "https://github.com/search?q=%22import+fastblocks_htmy%22&type=code"
  #    excluding known Bodai repos
  ```
  If any external consumer exists, abort Task C and re-plan.
- Pre-merge analysis (per AI H1): diff public method signatures between `fastblocks_htmy/base.py` and `_htmy_components.py`. Enumerate name collisions with proposed resolution (alias, merge, raise). Produce a commit-by-commit migration path for users who depended on either definition. This is a precondition for sub-task C2 — the result must be reviewed and the chosen default documented in the spec.

**Sub-task C1 — Pin transitive deps correctly (the convergent critical fix).**

The plan and earlier spec draft instructed adding `"fastblocks-htmy>=0.5,<0.6"` to `[project].dependencies`. **This is wrong** for four converging reasons (security-auditor F1, ai-engineer C3, architecture-council F1+F2, fastblocks-specialist F1):

- Pinning `fastblocks-htmy` as a dep of the package that absorbed its source creates a self-referential dependency: users install two copies of `Button`/`Field`/etc. with different module paths.
- The standalone `fastblocks_htmy/__init__.py:58-81` runs `_check_fastblocks_ui()` at import time and emits `RuntimeWarning` for any `fastblocks-ui` outside `[0.8, 0.9)`. Pinning the standalone package forces the warning to fire whenever fastblocks pins a different range.
- It sets the wrong ecosystem precedent for future "absorb an external package" decisions.
- The transitive intent (pin `htmy` + `fastblocks-ui` versions) is achieved by pinning them directly.

**Fix:** Do NOT add `fastblocks-htmy` to `[project].dependencies`. Instead, pin the transitive deps directly:

```toml
[project]
dependencies = [
    # ... existing ...
    "fastblocks-ui>=0.8,<0.9",    # already added in Task B
    "htmy[lxml]>=0.13,<0.14",     # NEW: was transitively pinned via fastblocks-htmy;
                                   # [lxml] extra is required by load_component_from_source (AST-sandboxed parser)
]
```

**Verification (after C1):**

- `git grep -n "fastblocks-htmy" pyproject.toml` → exactly one hit, in `[project.optional-dependencies]` (NOT in `[project.dependencies]`)
- `uv pip install -e .` resolves without warning
- `python -c "import fastblocks; import htmy; import fastblocks_ui"` succeeds

**Sub-task C2 — Reconcile base classes (per Fb-spec F5 + Arch F3).**

The existing `_htmy_components.py:371` defines `ComponentBase(ABC)` with `add_child`/`remove_child`/`children`/`parent`. The standalone `fastblocks_htmy/base.py:8` defines `FastBlocksComponent` with `_markup` + `htmy` + `__html__` + `__str__`. The 20+ typed UI components (`Button`, `Field`, `Tabs`, etc.) all inherit from `FastBlocksComponent`, not from `ComponentBase`. These are not aliases of each other.

**Decision (pinned here, not delegated to the implementer):** `FastBlocksComponent` becomes the canonical base class for absorbed `ui/` and `layout/` components. `_htmy_components.ComponentBase` is preserved for legacy code paths in `_htmy_components.py` (it's used by `AdvancedHTMYComponentRegistry`'s discovery loader). The two classes coexist; `FastBlocksComponent` is the user-facing base for typed components. **`ComponentBase` is NOT a drop-in replacement for `FastBlocksComponent`** — the two have different APIs (tree-building vs markup rendering) and are not interchangeable. CHANGELOG must call this out.

**Action:** Copy `fastblocks_htmy/base.py` → `fastblocks/adapters/templates/htmy_components/base.py` verbatim. Document the rename in CHANGELOG: `FastBlocksComponent` is now the canonical base for absorbed typed components. Existing `ComponentBase` in `_htmy_components.py` is preserved for the legacy registry path.

**Verification (after C2):**

- `python -c "from fastblocks.adapters.templates.htmy_components import FastBlocksComponent; from fastblocks.adapters.templates._htmy_components import ComponentBase"` works
- Existing tests for `_htmy_components.ComponentBase` still pass

**Sub-task C3 — Remove RCE vector from htmy.py (per Fb-spec F2 — NEW critical finding).**

`fastblocks/adapters/templates/htmy.py:300-354` (`_load_from_cached_bytecode`) and `htmy.py:356-399` (`_load_from_source`) both use `importlib.util.spec_from_file_location()` + `spec.loader.exec_module()` — the exact RCE-vector path CLAUDE.md:130 documents as removed by Phase 1.3. The advanced registry in `_htmy_components.py` correctly routes through `load_component_from_source()` (AST-sandboxed), but `HTMYTemplates.render_component` falls back to the legacy `HTMYComponentRegistry` for any path that doesn't go through `render_component_advanced`, so the unsafe path is still reachable.

**Action:**

- Delete `_load_from_cached_bytecode` and `_load_from_source` from `htmy.py`.
- `HTMYComponentRegistry` keeps `discover_components()` and `register_trusted_components()` only. Any component loading request goes through `load_component_from_source()` from `_htmy_components.py`.
- Add a unit test asserting that `importlib.util.spec_from_file_location` does not appear in `htmy.py` (a `grep` regression test).

**Verification (after C3):**

- `grep -n "spec_from_file_location\|exec_module" fastblocks/adapters/templates/htmy.py` → no hits
- `uv run ty check fastblocks/` → "All checks passed!"
- `uv run pytest -q -m "not slow" --no-header` → all current tests still pass; the unsafe path is unreachable

**Sub-task C4 — Absorb and verify.**

Now that deps are pinned (C1), base classes reconciled (C2), and the RCE vector closed (C3), the source move itself is mechanical.

**Source to absorb:** `/Users/les/Projects/fastblocks-htmy/fastblocks_htmy/` — 24 files:

```
fastblocks_htmy/__init__.py
fastblocks_htmy/base.py
fastblocks_htmy/adapter.py
fastblocks_htmy/fastblocks/__init__.py
fastblocks_htmy/fastblocks/adapter.py
fastblocks_htmy/py.typed
fastblocks_htmy/ui/__init__.py
fastblocks_htmy/ui/_generated.py
fastblocks_htmy/ui/breadcrumb.py
fastblocks_htmy/ui/button.py
fastblocks_htmy/ui/dropdown.py
fastblocks_htmy/ui/field.py
fastblocks_htmy/ui/navbar.py
fastblocks_htmy/ui/select.py
fastblocks_htmy/ui/table.py
fastblocks_htmy/ui/tabs.py
fastblocks_htmy/ui/validation_summary.py
fastblocks_htmy/layout/__init__.py
fastblocks_htmy/layout/_generated.py
fastblocks_htmy/layout/columns.py
fastblocks_htmy/layout/container.py
fastblocks_htmy/layout/nav_groups.py
fastblocks_htmy/layout/nav_list.py
```
(NOTE: the standalone's `layout/` subpackage has exactly **6** files — `__init__.py`, `_generated.py`, `columns.py`, `container.py`, `nav_groups.py`, `nav_list.py`. There is **no** `layout/navbar.py` — the `navbar.py` lives in `ui/`, not `layout/`. The earlier spec draft miscounted.)

**Target layout** (under `fastblocks/adapters/templates/`):

- `_htmy_components.py` — `ComponentBase`, `DataclassComponentBase`, `HTMXComponentMixin`, AST-sandboxed source loader (`load_component_from_source`), lifecycle manager, validator, scaffolder, `AdvancedHTMYComponentRegistry`. **Existing file, unchanged.**
- `htmy.py` — `HTMYTemplates`, `HTMYTemplatesSettings`, `HTMYComponentRegistry` (now loader-free), `register_trusted_components` integration. **Existing file, modified per C3.**
- `htmy_components/` *(new package, supersedes standalone `fastblocks_htmy/`)*:
  - `py.typed` — PEP 561 marker carried over (from Fb-spec F9: typing affordance only, no runtime guards affected).
  - `__init__.py` — re-exports the full **34-name** public surface (32 component classes + `FastBlocksComponent` base + `__version__`): `Shell, NavList, NavGroups, Drawer, Burger, Alert, Breadcrumb, Button, Card, Checkbox, Column, Columns, Container, Dialog, Field, Footer, Hero, Input, Level, Media, Dropdown, Navbar, Pagination, Progress, Section, Select, Switch, Table, Tabs, Tile, Title, ValidationSummary, FastBlocksComponent, __version__`. **Delete the `_check_fastblocks_ui()` runtime warning** (declarative pyproject pin is authoritative; Fb-spec F6). Replace it with a soft `warnings.warn(...)` (per plan-audit R2) so manual `pip install fastblocks-ui==0.9.0 --force-reinstall` is still surfaced at runtime. Add a top-of-file `__absorbed_from__: fastblocks-htmy@0.5.0 (commit <sha>, fetched 2026-08-21)` provenance line (per Sec F4).
  - `base.py` — verbatim copy of `fastblocks_htmy/base.py` (per C2).
  - `ui/__init__.py`, `ui/button.py`, `ui/field.py`, `ui/tabs.py`, `ui/table.py`, `ui/breadcrumb.py`, `ui/dropdown.py`, `ui/select.py`, `ui/navbar.py`, `ui/validation_summary.py`, `ui/_generated.py` — verbatim copies. The `_generated.py` files are checked-in static snapshots (per AI H2); add a header comment saying so with the date of the last manual regen.
  - `layout/__init__.py`, `layout/container.py`, `layout/columns.py`, `layout/nav_list.py`, `layout/nav_groups.py`, `layout/_generated.py` — verbatim copies (6 files total — NO `layout/navbar.py`; that file does not exist in the standalone).
  - `adapter.py` — adapted from `fastblocks_htmy/fastblocks/adapter.py`. The 5 public functions (`trusted_components()`, `register_with_htmy_adapter()`, `asset_paths()`, `asset_urls()`, `template_globals()`) carry over verbatim. The `depends.resolve("fastblocks", "htmy")` example in the module docstring is removed (per Sec F2 — same dead-API pattern as kelp/webawesome bug (b)).

**Integration-glue ownership (per Arch F4):** `fastblocks.adapters.templates.htmy_components.adapter` is the canonical integration glue. `fastblocks.adapters.templates.htmy.HTMYTemplates` proxies to it via a thin re-export. Users import from `fastblocks.adapters.templates.htmy_components` only.

**Top-of-file module docstring** (in `_htmy_components.py` and the new `htmy_components/__init__.py`):

```python
"""Previously distributed as the standalone ``fastblocks-htmy`` PyPI package.

This module was absorbed into fastblocks proper on 2026-08-21 (fastblocks 0.31.x);
see CHANGELOG.md for the migration. Users who previously pinned
``fastblocks-htmy>=0.5,<0.6`` should drop that dependency and import from
``fastblocks.adapters.templates.htmy_components`` instead. ``fastblocks-htmy
0.6.x`` is a shim-only release that re-exports from this module.
"""
```

**Verification (after C4):**

- `diff -r fastblocks/adapters/templates/htmy_components/ /Users/les/Projects/fastblocks-htmy/fastblocks_htmy/ --brief` (excluding `__pycache__`, `*.pyc`) → only intended reconcile differences appear (the `__init__.py` docstring additions, `__absorbed_from__` line, removal of `_check_fastblocks_ui`). This is the integrity gate (per Sec F4).
- `python -c "from fastblocks.adapters.templates.htmy_components import *"` — imports all 34 names (32 components + `FastBlocksComponent` + `__version__`) without error (per Fb-spec F10 — surfaces any missing import in `_generated.py` or `__init__.py` re-exports).
- `python -c "from fastblocks.adapters.templates.htmy_components import Button"` works
- `python -c "from fastblocks.adapters.templates.htmy_components import Field, Tabs, Table"` works
- `python -c "from fastblocks.adapters.templates.htmy_components.layout import Container, Columns"` works
- **Behavioral XSS regression test** (per Sec F5 + AI H3 + Arch F7): for each absorbed component with user-supplied string fields, instantiate with `label="<script>alert(1)</script>"` (or equivalent field) and assert the rendered output contains `&lt;script&gt;` and not `<script>`. The fastblocks-ui helpers escape by default (`ui/button.py:37-48` delegates to `fastblocks_ui._button(...)` which the spec confirms escapes every interpolated value); the regression test pins this contract. A single failing test should block C4 completion.
- `grep -n "SafeStr\|__html__" fastblocks/adapters/templates/htmy_components/` → every match is a `htmy.SafeStr` wrap of a `fastblocks_ui.<helper>` call, no raw f-string interpolation into wrapped output.
- `grep -nE "\{self\.[a-z_]+\}" fastblocks/adapters/templates/htmy_components/ui/ fastblocks/adapters/templates/htmy_components/layout/` → only flag dataclass fields routed through `fastblocks_ui` helpers.
- `uv run ty check fastblocks/` → "All checks passed!"
- `uv run pytest -q -m "not slow" --no-header` → ≥ 1714 passed, 0 fail

### Task D — Reclassify architecture (clean-up of all three)

**Files to update:**

- `fastblocks/core/style_registry.py` — update the module-level docstring to clarify:
  - `style` = CSS source only (currently `vanilla`, `fastblocks_ui`).
  - The future `renderer` axis (Python types → HTML) is the unifying abstraction for the next architectural PR. Today `jinja2` is the implicit renderer; `htmy` is available via `fastblocks/adapters/templates/htmy.py` but not exposed as a `style_registry` axis. The docstring should name the axis without introducing a config knob.

  Drop the long passages about kelp/webawesome's `AttributeError` traps — those no longer apply. Keep the defensive `with suppress(Exception)` rationale for legitimate silent-no-op styles (e.g. `vanilla`).

- `fastblocks/adapters/style/__init__.py` — update module docstring to reflect the 2-style state.

- `fastblocks/adapters/style/README.md` — rewrite to describe the `style` axis in isolation, with `vanilla` / `fastblocks_ui` as the two values. Link to `style_registry.py` for the broader architectural context.

**Verification (after D):**

- `git grep -n "renderer" fastblocks/core/style_registry.py` → exactly the docstring references
- `git grep -n "kelp\|webawesome" fastblocks/ settings/` → no hits
- `uv run ty check fastblocks/` → "All checks passed!"
- `uv run crackerjack run` → all hooks PASS

## Migration notes

### For users on `style="kelp"` or `style="webawesome"`

**Before fastblocks 0.30.0:** their app runs, but those styles register nothing (silent). Their pages render as if `vanilla` was selected.

**Deprecation cycle skipped:** with user-confirmed zero external consumers of fastblocks, fastblocks-ui, and fastblocks-htmy, the spec does NOT include a 0.29.x deprecation release. Users on `style="kelp"`/`"webawesome"` fail loudly at 0.30.0 upgrade with no intermediate warning. This is deliberate — the cross-release deprecation-cycle concern that would normally apply is collapsed by the zero-consumer assertion.

**In fastblocks 0.30.0:** their app fails at startup with `unknown style: 'kelp'` from `fastblocks/core/style_registry.py` (or similar from `fastblocks/adapters/app/_base.py` validation). This is the correct behavior — silent-failure was a bug, not a feature.

**Upgrade path:**

1. Edit their app's settings: `config.app.style = "fastblocks_ui"` (recommended) or `config.app.style = "vanilla"` (explicit unstyled).
2. If they depended on kelp/webawesome's specific CSS classes or component helpers (e.g. `wa_button`, `kelp_component`), those names no longer exist. Their templates will fail at render time with `UndefinedError` from Jinja. The fix is to switch to the `fastblocks-ui` equivalents (`ui_button`, `ui_card`, etc., registered by `register_fastblocks_ui_functions`).
3. If they had user-supplied content flowing through `kelp_component()` / `wa_button()` / `wa_card()`, that was an XSS hazard waiting for the dead-code bugs to be fixed. The fix is moot now (the helpers are gone), but they should still audit any prior app versions in production for stored XSS payloads.

**No data migration is required** — this is a configuration + template change, not a database schema change. CHANGELOG lists the breaking changes under "Removed" for 0.30.0.

### For users on the standalone `fastblocks-htmy` PyPI package

**Before fastblocks 0.31.x:** they `uv add fastblocks-htmy` and import from `fastblocks_htmy`. The package pins `fastblocks-ui>=0.8,<0.9` + `htmy[lxml]>=0.13,<0.14` as transitive deps.

**In fastblocks 0.31.x** (NOT 0.30.0 — the absorption ships in 0.31.x): `fastblocks.adapters.templates.htmy_components` exposes the same public surface. They can drop `fastblocks-htmy` from their deps and switch the import.

**Deprecation cycle for `fastblocks-htmy` the PyPI package:**

1. `fastblocks-htmy 0.5.x` is the **last full implementation** release. It stays installable. Users on 0.5.x see no change.
2. `fastblocks-htmy 0.6.x` is a **shim-only release**. Its `__init__.py` contains:

   ```python
   try:
       from fastblocks.adapters.templates.htmy_components import (
           Button, Field, Tabs, Table, Breadcrumb, Dropdown, Select,
           Navbar, ValidationSummary, Container, Columns, NavGroups,
           NavList, Shell, Drawer, Burger, Alert, Card, Checkbox,
           Column, Dialog, Footer, Hero, Input, Level, Media, Pagination,
           Progress, Section, Switch, Tile, Title, FastBlocksComponent,
           __version__,
           # ... full 34-name surface ...
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

   The explicit `ImportError` (per Sec F6) prevents the silent `ModuleNotFoundError: fastblocks` that users with only `fastblocks-htmy` installed would otherwise hit.

3. After one release cycle (~30 days post-0.31.0 — NOT post-0.30.0; the shim cycle starts when the absorbed source lands), archive the standalone repo (GitHub "Archived" toggle + `pyproject.toml` `private = true`) but do NOT delete the directory on disk.
4. After one more release cycle, deletion is a separate decision. **Out of scope for this PR.**

### For `vanilla`-style users (per Sec F7)

After fastblocks 0.30.0, `fastblocks-ui` becomes a **required** dependency even for `vanilla` users. Air-gapped environments mirroring a curated subset of PyPI must mirror `fastblocks-ui>=0.8,<0.9` before upgrading. The `vanilla` style adapter still works as the explicit opt-out, but the package install is now unconditional.

## Real-bug policy

When a task surfaces code calling an API that doesn't exist, or HTML output that escapes user input, or any other silent-failure pattern, the protocol is:

1. **Stop** — don't silently fix.
2. **Surface** — name the file, line, the wrong behavior, and what the corrected behavior is.
3. **Ask** — confirm whether the code path is exercised or dead.
4. **Document** — append to the spec's "Real bugs found" section so the count and resolution are tracked.

## Sequencing & reporting

- One task at a time. Do not start task N+1 until task N's verification gates pass AND task N+1's pre-conditions hold.
- After each task, report:
  - Files deleted / moved / created.
  - Ty diagnostics before and after.
  - Pytest pass count (and any baseline shift).
  - Crackerjack hook status.
  - Any real bugs surfaced and how they were resolved.
- Commit per task (Task C has 4 sub-task commits: C1, C2, C3, C4). Pre-existing dirty files stay out of every commit (quarantine procedure above).
- Final commit message should reference this spec path (`docs/superpowers/specs/2026-08-21-style-renderer-architecture.md`).
- Do not push to main until ty + pytest + crackerjack are all green.
- Reviewer (read-only) checklist for each task commit:
  - (a) `git diff --stat HEAD~1` lists only files in the task's spec section.
  - (b) `uv run ty check fastblocks/` returns 0 diagnostics.
  - (c) `uv run pytest -q -m "not slow"` returns ≥ 1714 passed.
  - (d) Task-specific verification gates (kelp/webawesome grep, dep pins, full-surface import, etc.).
  - (e) CHANGELOG and CLAUDE.md updates present per the Files to update list.

## Risks

- **`fastblocks-htmy 0.5.x` runtime warning re-emerge**: the absorbed `__init__.py` must not include `_check_fastblocks_ui()` even if the standalone source has it. The deletion is mandatory; pin the version range declaratively in pyproject instead.
- **`_generated.py` file staleness**: the absorbed `ui/_generated.py` and `layout/_generated.py` are checked-in static snapshots. If the manifest schema changes post-merge, regen is manual. Add a header comment naming the snapshot date.
- **`fastblocks-ui` CSS asset path coverage**: `fastblocks_ui.py` resolves `get_css_path()` / `get_js_path()` lazily inside `get_stylesheet_links()` / `get_script_tags()`. The pre-flight gate in Task B (above) verifies these exist in the pinned range.
- **Cross-task implementation drift**: Task C has 4 sub-tasks; a subagent could legitimately attempt them out of order if the cross-task precondition isn't explicit. The Sequencing rules section pins the order.
- **Test pollution**: the existing legacy `HTMYComponentRegistry` in `htmy.py` is preserved (loader-free after C3). Tests asserting on it must continue to pass. If any test depends on a specific `fastblocks-htmy` import path, the merge must update those tests.
- **Working tree contention**: the work happens in worktrees per the quarantine procedure. The pre-existing dirty tree (~40 files) in the main checkout belongs to prior sessions and is not part of this scope.
- **Conftest collection-error count** (per Fb-spec F15): CLAUDE.md:233 acknowledges ~19 pre-existing collection errors under xdist. The spec doesn't change conftest.py, so the count should stay stable. If it changes, record the new baseline in CHANGELOG.
- **No-PR merge policy**: Bodai merges directly to main pre-1.0. There is no PR review gate. Each task's commit is the unit of review, so commits must be clean, well-described, and reference the relevant spec section.

## Verification gates (every commit)

| Gate | Command | Expected |
|---|---|---|
| Per task | `uv run ty check fastblocks/` | "All checks passed!" |
| Per task | `uv run pytest -q -m "not slow" --no-header` | ≥ 1714 passed, 0 fail |
| Final | `uv run crackerjack run` | ty PASS, refurb PASS, ruff PASS |
| After A | `git ls-files --modified --others --cached fastblocks/ settings/ \| xargs grep -n "kelp\|webawesome\|KelpStyle\|WebAwesomeStyle"` | no hits |
| After A | `python -c "from fastblocks.adapters.style import vanilla, fastblocks_ui"` | both import, no kelp/webawesome import path |
| After B | `python -c "import fastblocks_ui; assert callable(fastblocks_ui.get_css_path); assert callable(fastblocks_ui.get_js_path)"` | exits 0 |
| After B | `git grep -n "fastblocks_ui =" pyproject.toml` | no hits |
| After C1 | `git grep -n "fastblocks-htmy" pyproject.toml` | exactly one hit in `[project.optional-dependencies]` |
| After C3 | `grep -n "spec_from_file_location\|exec_module" fastblocks/adapters/templates/htmy.py` | no hits |
| After C4 | `diff -r fastblocks/adapters/templates/htmy_components/ /Users/les/Projects/fastblocks-htmy/fastblocks_htmy/ --brief` | only intended differences |
| After C4 | `python -c "from fastblocks.adapters.templates.htmy_components import *"` | all 34 names importable (32 components + `FastBlocksComponent` + `__version__`) |
| After C4 | XSS regression test (instantiate each absorbed component with `<script>` payload) | every render produces escaped output |
| After D | `git grep -n "renderer" fastblocks/core/style_registry.py` | exactly docstring references |
| Smoke | `python -c "from fastblocks.adapters.style import fastblocks_ui; print(fastblocks_ui.__version__)"` | works |

## Real bugs found (running log)

The 4-reviewer adversarial review surfaced the following real bugs that the spec fixes (per Real-bug policy):

- **R1 — Active RCE vector in `htmy.py`** (fastblocks-specialist Finding 2, NEW): `htmy.py:300-354` and `htmy.py:356-399` use `spec_from_file_location + exec_module` — the RCE path CLAUDE.md:130 documents as removed by Phase 1.3. Task C3 closes it.
- **R2 — `_check_fastblocks_ui()` runtime warning** (security-auditor F1, ai-engineer C3, fastblocks-specialist F6): the standalone `fastblocks_htmy/__init__.py:58-81` warns whenever `fastblocks-ui` is outside `[0.8, 0.9)`. Task C4 deletes the function; declarative pyproject pin is authoritative.
- **R3 — Dual source of truth** (architecture-council F1, security-auditor F1, ai-engineer C3): absorbing `fastblocks-htmy` source *and* requiring it as a runtime dep creates duplicate classes and self-referential package metadata. Task C1 fixes the dep string.

Medium/low findings carried forward for tracking (not blocking, can ship in follow-ups):

- M1 — Test baseline shift under vanilla default flip (Fb-spec F7).
- M2 — `kelp.py.backup.json` deletion semantics (Fb-spec F8).
- M3 — CLI `--help` text mentions kelp/webawesome (Fb-spec F14).
- M4 — Pre-existing dirty files conftest pollution (Fb-spec F15).
- M5 — Subagent pattern not specified (`/vishnu` vs `mahavishnu-orchestrator`, ai-engineer L1).
- M6 — Cache invalidation for lazy asset-path resolution (ai-engineer L2).
- M7 — "Known Tech Debt" vs "Real bugs found" terminology inconsistency (architecture-council F14).

## Reference artifacts

- Spec for the just-completed ty cleanup (template for spec structure): `/Users/les/Projects/fastblocks/docs/superpowers/specs/2026-08-20-fastblocks-ty-cleanup-design.md`
- Plan for the just-completed ty cleanup: `/Users/les/Projects/fastblocks/docs/superpowers/plans/2026-08-20-fastblocks-ty-cleanup.md`
- Source of `fastblocks-htmy` to absorb: `/Users/les/Projects/fastblocks-htmy/fastblocks_htmy/`
- CLAUDE.md known-bug note for kelp/webawesome: lines 234-235 (silent failure + XSS surface)
- Working style adapter for `fastblocks-ui` (model after this): `/Users/les/Projects/fastblocks/fastblocks/adapters/style/fastblocks_ui.py`
- Existing legacy htmy components module (the partial to reconcile with): `/Users/les/Projects/fastblocks/fastblocks/adapters/templates/_htmy_components.py`
- Existing legacy htmy templates adapter (RCE vector lives here): `/Users/les/Projects/fastblocks/fastblocks/adapters/templates/htmy.py`
- AppBaseSettings (the `style: str = "vanilla"` line that changes): `/Users/les/Projects/fastblocks/fastblocks/adapters/app/_base.py:12`
- pyproject.toml (the optional `fastblocks_ui = [...]` group that moves): `/Users/les/Projects/fastblocks/pyproject.toml:102-109`
- Standalone `fastblocks-htmy` pyproject.toml (for transitive pin ranges): `/Users/les/Projects/fastblocks-htmy/pyproject.toml`
- 4-reviewer adversarial review transcripts (security, architecture, outside-AI, domain):
  - security-auditor: 9 findings (1 critical, 3 high, 4 medium, 2 low)
  - architecture-council: 14 findings (2 critical, 6 high, 4 medium, 2 low)
  - ai-engineer (outside perspective): 15 findings (3 critical, 4 high, 5 medium, 3 low)
  - fastblocks-specialist: 16 findings (2 critical, 4 high, 6 medium, 4 low)
- Companion plan: `/Users/les/Projects/fastblocks/docs/superpowers/plans/2026-08-21-style-renderer-architecture.md`
