---
status: accepted
role: phase-2-5-design-spec
date: 2026-08-22
last_reviewed: 2026-08-22
supersedes: null
superseded_by: null
decision_date: 2026-08-22
topic: phase-2-5-app-yml-wiring
---

# Phase 2.5: app.yml → AppBaseSettings Wiring Design

## Status

**Accepted** (Phase 2.5 spec — companion to master plan
`docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md` §Decision 7 line 86-92 / line 312).

## Scope decision

Phase 2.5 closes the wiring gap identified in ADR 0010 Decision 7:
`OneiricSettings` is a `pydantic-settings.BaseSettings` subclass but
`AppBaseSettings` is instantiated with no arguments today
(`fastblocks/adapters/app/default.py:182`), so the
`StyleName = Literal["vanilla", "fastblocks_ui"]` validation that
shipped in Phase 2 mechanical-four only fires when an operator
explicitly passes `AppSettings(style="kelp")` or similar direct call —
not on `app.yml`-driven config. Phase 2.5 brings the validation to life.

**In scope:**

1. Add 4 fields to `AppBaseSettings` matching the documented
   `mcp/resources.py:288` schema: `title`, `domain`, `description`,
   `version`.
2. Add `fastblocks/core/settings_loader.py` — thin wrapper around
   Oneiric's `load_settings(path, project_name)` that returns
   `AppSettings` (not raw OneiricSettings).
3. Wire `AppSettings()` call sites to use the loader with a **soft
   fallback** when `app.yml` is absent (defaults preserved).
4. Document the canonical schema source in `mcp/resources.py` (point
   readers at `AppBaseSettings`).
5. Test the load path + failure modes.

**Out of scope:**

- Modifying Oneiric's `AppConfig` (Oneiric's app-level config; different
  concern from fastblocks's app-level config).
- Migrating existing fastblocks apps to use `app.yml` (the soft
  fallback preserves back-compat; operators add `app.yml` when they
  want to override defaults).
- Closing the `# type: ignore[misc]` on `AppBaseSettings(OneiricSettings)`
  declaration (pre-existing typing friction; not a Phase 2.5 concern).
- Renderer axis / match dispatch / SafeHTMLStr (all separately deferred
  in ADR 0010 Decisions 9-11).

## Why Phase 2.5 is a thin slice

The mechanical work is small:

1. `OneiricSettings` already extends `pydantic-settings.BaseSettings`
   (verified at `oneiric/core/config.py:245` with
   `model_config = SettingsConfigDict(env_prefix="ONEIRIC_", ...)`).
   The YAML-loading machinery is already in the inheritance chain.
2. Oneiric's `load_settings(path, project_name)` is the
   XDG-compliant layered YAML loader with priority order (path arg >
   env var > XDG user > project local > project committed > defaults).
   Phase 2.5 wraps it for fastblocks defaults.
3. The documented `app.yml` schema in `mcp/resources.py:288` is
   **drifted** from `AppBaseSettings` actual fields (different field
   names). Phase 2.5 reconciles by making `AppBaseSettings` the
   source of truth.

## Architecture

Three layers.

### Layer 1 — `AppBaseSettings` (modified)

`fastblocks/adapters/app/_base.py` adds 4 fields:

```python
class AppBaseSettings(OneiricSettings):  # type: ignore[misc]
    """App base settings. Source of truth for app.yml schema."""

    # Existing fields (unchanged)
    name: str = "fastblocks"
    style: StyleName = DEFAULT_STYLE
    theme: str = "light"

    # NEW: matches mcp/resources.py:288 documented schema
    title: str = ""
    domain: str = ""
    description: str = ""
    version: str = ""
```

**Why top-level, not nested under `app: AppConfig`**: Oneiric's
`AppConfig` (oneiric/core/config.py:49-52) holds `name/environment/debug`
— Oneiric's app-level concern. fastblocks's app-level config
(`style/theme/title/domain/description/version`) is a different concern.
Nesting under Oneiric's `app` would require modifying Oneiric's data
model (out of scope) and would couple fastblocks's app schema to
Oneiric's app schema unnecessarily.

### Layer 2 — `fastblocks/core/settings_loader.py` (NEW)

Thin wrapper around Oneiric's `load_settings`:

```python
"""fastblocks settings loader.

Wraps Oneiric's load_settings with fastblocks defaults: project_name="fastblocks",
default path resolution (./app.yml then ./settings/fastblocks.yml then
XDG paths via Oneiric's XDG-compliant layered lookup). Returns AppSettings
(not raw OneiricSettings) so callers get the fastblocks schema.
"""

from __future__ import annotations

from pathlib import Path

from fastblocks.adapters.app.default import AppSettings

# Re-export so callers can catch the "missing file" case explicitly.
_FILE_NOT_FOUND = FileNotFoundError


def load_fastblocks_settings(
    path: str | Path | None = None,
) -> AppSettings:
    """Load AppSettings from app.yml (or fallback path).

    Wraps Oneiric's load_settings for fastblocks defaults.
    Raises FileNotFoundError if no app.yml exists at any of the
    resolved paths; callers handle the fallback.

    Args:
        path: Optional explicit path. Highest priority. Defaults to
            Oneiric's XDG-compliant layered lookup.

    Returns:
        AppSettings populated from YAML + Oneiric defaults.
    """
    from oneiric.core.config import load_settings  # local import — avoids module-load cycle

    oneiric = load_settings(path=path, project_name="fastblocks")
    return AppSettings.model_validate(oneiric.model_dump(mode="python"))
```

**Why a wrapper, not a direct call to Oneiric's loader**:

1. Pins `project_name="fastblocks"` so XDG paths resolve to
   `~/.config/fastblocks/config.yaml` (not Oneiric's default).
2. Returns `AppSettings`, not `OneiricSettings` — callers don't need
   to know about the Oneiric intermediary type.
3. Provides a single place to add fastblocks-specific loading
   extensions later (e.g., CLI args, environment-prefix overrides).

### Layer 3 — Call site wiring

`fastblocks/adapters/app/default.py:182` (and any other
`AppSettings()` instantiation sites):

```python
from fastblocks.core.settings_loader import load_fastblocks_settings

# Before:
self.settings = AppSettings()

# After:
try:
    self.settings = load_fastblocks_settings()
except FileNotFoundError:
    # Soft fallback: app.yml is optional. Existing fastblocks apps
    # without app.yml keep working with defaults.
    self.settings = AppSettings()
```

Other `AppSettings()` call sites (5 total — verified via
`grep -rn 'AppSettings()' fastblocks/`) follow the same pattern.

## Failure modes

| Failure | Behavior |
|---|---|
| `app.yml` absent at every resolved path | `FileNotFoundError` from Oneiric's loader; caller catches and uses defaults. **Soft fallback per user choice.** |
| `app.yml` malformed YAML | `yaml.YAMLError` propagates from Oneiric's loader. Loud startup error with file:line. |
| `app.yml` has invalid Literal value (e.g., `style: kelp`) | `pydantic.ValidationError` from `AppSettings.model_validate`. Literal validation fires for the first time in production. Message format: `Input should be 'vanilla' or 'fastblocks_ui' [type=literal_error, input_value='kelp', input_type=str]`. |
| `app.yml` has extra unknown field (e.g., `typo: x`) | `extra="ignore"` (inherited from OneiricSettings). Silently dropped. |
| Required field (`title`, `domain`) absent | `""` default (no startup error). Future tightening: Pydantic `Field(...)` without default when app.yml is present, but separate decision. |

## Data flow

### Scenario 1 — Existing fastblocks app, no app.yml

```
fastblocks-cli create app myapp
    → scaffolds <myapp>/settings/<settings>.yml (CLI scaffold)
    → user runs the app

cd <myapp>
fastblocks run
    │
    ▼
App.__init__
    │
    ▼
AppSettings()  ← current call
    │
    ▼
Phase 2.5 wiring:
    try: self.settings = load_fastblocks_settings()
    except FileNotFoundError:
        self.settings = AppSettings()   ← soft fallback, current behavior preserved
    │
    ▼
AppSettings() uses defaults: name="fastblocks", style="fastblocks_ui", theme="light", title="", domain="", ...
```

### Scenario 2 — User adds app.yml with override

```
# <myapp>/app.yml (or ./app.yml)
title: "My Application"
domain: "example.com"
style: "vanilla"          ← override the default
theme: "dark"
version: "1.0.0"
```

```
App.__init__
    │
    ▼
load_fastblocks_settings()
    │
    ▼
Oneiric.load_settings(path=None, project_name="fastblocks")
    │
    ▼
XDG-compliant layered lookup:
    1. ./app.yml  ← found, used
    │
    ▼
OneiricSettings.model_validate(yaml.safe_load(...))
    │
    ▼
AppSettings.model_validate(oneiric.model_dump(mode="python"))
    │
    ▼
Pydantic validation:
    style="vanilla" → Literal["vanilla", "fastblocks_ui"] matches → PASS
    title="My Application" → str default → PASS
    domain="example.com" → str default → PASS
    version="1.0.0" → str default → PASS
    │
    ▼
AppSettings instance with overridden fields
```

### Scenario 3 — User has invalid YAML value

```
# <myapp>/app.yml
style: "kelp"   ← not in StyleName Literal
```

```
App.__init__
    │
    ▼
load_fastblocks_settings() raises pydantic.ValidationError
    │
    ▼
Loud startup error: "Input should be 'vanilla' or 'fastblocks_ui'
    [type=literal_error, input_value='kelp', input_type=str]"
    │
    ▼
App fails to start — first time Literal validation fires in production
```

## Test surface

| File | Tests | Markers | Purpose |
|---|---|---|---|
| `tests/core/test_settings_loader.py` | 6 | `@pytest.mark.unit` | Happy path, missing file (FileNotFoundError), malformed YAML, invalid Literal, extra fields ignored, defaults-only fallback |
| `tests/core/test_app_settings_yaml_wiring.py` | 4 | `@pytest.mark.unit` | AppSettings reads title/domain/style/theme from YAML; soft fallback path; end-to-end via `AppSettings.model_validate`; round-trip via `model_dump` |
| `tests/core/test_app_settings_literal.py` | (already exists, 7 tests) | `@pytest.mark.unit` | Existing tests still pass — no regression |

**Total: 10 new tests.** Combined with Phase 2 mechanical-four's 40 tests, the post-Phase-2.5 test count is 50 distinct Phase 2 tests + the existing 1800+ baseline.

### Canary validation discipline (per Phase 2 mechanical-four pattern)

Each new test file is verified to fail against pre-fix code via the canary pattern:

| Canary | Action | Expected failure |
|---|---|---|
| Loader happy path | Revert `default.py:182` to `AppSettings()` direct call | `test_settings_loader.py::test_loader_returns_app_settings_with_yaml_fields` fails — no loader wired |
| Soft fallback | Delete the `try/except FileNotFoundError` wrapper | `test_settings_loader.py::test_loader_raises_filenotfound_when_no_yaml` fails — caller cannot catch the no-yaml case |
| YAML malformed | Hand-craft a YAML file with a syntax error | `test_settings_loader.py::test_loader_propagates_yaml_error` fails — no error propagation |
| Literal validation | Set `style: kelp` in test YAML | `test_app_settings_yaml_wiring.py::test_app_settings_rejects_invalid_yaml_style` fails — Literal validation not wired |

## Verification gate

- All 10 new tests pass
- Existing `test_app_settings_literal.py` (7 tests) still passes — no regression
- Pre-existing 20 baseline failures unchanged
- `crackerjack run` passes (no new ruff/ty/security regressions)
- `uv run ty check fastblocks/adapters/app/_base.py` — `# type: ignore[misc]` count unchanged (1)
- `git grep -c 'suppress(Exception)' -- fastblocks/` — ratchet holds (122 sites)
- Manual smoke: `cd <scaffolded-app>; echo 'style: kelp' > app.yml; fastblocks run` → loud ValidationError

## Per-task Integration Contracts

Per master plan §Process, each commit ships with IC block. Three commits.

### Commit 1 — `feat(settings): add title/domain/description/version to AppBaseSettings`

- *Triggered from:* ADR 0010 Decision 7 (wiring deferred to Phase 2.5); `mcp/resources.py:288` schema documentation
- *Returns to / updates:* `fastblocks/adapters/app/_base.py` — 4 new fields with empty-string defaults
- *Demonstrable by:* `python -c "from fastblocks.adapters.app._base import AppBaseSettings; s = AppBaseSettings(); assert s.title == '' and s.domain == '' and s.description == '' and s.version == ''"` succeeds
- *Rollback signal:* `git revert`; the 4 new fields default to empty strings, no behavior change
- *Observability added:* None — these are configuration defaults

### Commit 2 — `feat(settings): fastblocks/core/settings_loader.py wraps Oneiric.load_settings`

- *Triggered from:* Commit 1; Oneiric's `load_settings(path, project_name)` already exists
- *Returns to / updates:* NEW `fastblocks/core/settings_loader.py`; 6 new tests in `tests/core/test_settings_loader.py`
- *Demonstrable by:* `tests/core/test_settings_loader.py` 6/6 pass
- *Rollback signal:* `git revert`; loader is additive, no caller yet
- *Observability added:* None — wrapper is pure plumbing

### Commit 3 — `refactor(app): AppSettings() instantiation uses loader with soft fallback`

- *Triggered from:* Commit 2; closes the wiring gap
- *Returns to / updates:* `fastblocks/adapters/app/default.py:182` (and 4 other call sites); `tests/core/test_app_settings_yaml_wiring.py` (NEW, 4 tests); `fastblocks/mcp/resources.py:288` doc update pointing at `AppBaseSettings` as canonical schema
- *Demonstrable by:* `tests/core/test_app_settings_yaml_wiring.py` 4/4 pass; manual smoke (loud ValidationError on `style: kelp`); existing scaffolded apps still work without app.yml
- *Rollback signal:* `git revert`; call sites revert to `AppSettings()` direct, no behavior change
- *Observability added:* Pydantic's `ValidationError` is the loud-failure surface for invalid YAML values; Oneiric's structured logger captures the loader path (inherited)

## Out of scope (deferred)

- Renderer match-statement dispatch (ADR 0010 Decision 9)
- SafeHTMLStr propagation (ADR 0010 Decision 10)
- Match dispatch on style axis (ADR 0010 Decision 11)
- Required-when-present tightening for `title` / `domain` (separate decision when YAML-driven apps become the norm)
- Migrating existing fastblocks apps to use `app.yml` (operator-driven, not framework-driven)
- Closing `# type: ignore[misc]` on `AppBaseSettings(OneiricSettings)` (pre-existing typing friction)
- Oneiric's `AppConfig` modifications (different concern from fastblocks's app config)

## Cross-references

- Master plan: `docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md` §Decision 7 (ADR 0010 line 86-92), §Phase 2 line 312 (wiring deferred)
- ADR 0010 Decision 7: `docs/adr/0010-phase-2-mechanical-four.md` (wiring deferred)
- ADR 0010 Decisions 9-12: same file (Phase 2 finish deferrals, 2026-08-22)
- Phase 2 mechanical-four spec: `docs/superpowers/specs/2026-08-21-fastblocks-phase-2-design.md`
- OneiricSettings source: `oneiric/core/config.py:245` (BaseSettings subclass)
- Oneiric `load_settings`: `oneiric/core/config.py:276` (XDG-compliant layered loader)
- Oneiric `AppConfig`: `oneiric/core/config.py:49-52` (different concern — not modified)
- AppSettings call sites: `grep -rn 'AppSettings()' fastblocks/ --include='*.py'`
- `app.yml` documented schema: `fastblocks/mcp/resources.py:288`
- CLI scaffold for `app.yml`: `fastblocks/cli.py:1019-1023`
