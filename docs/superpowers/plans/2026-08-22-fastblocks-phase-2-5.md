# Phase 2.5: app.yml → AppBaseSettings Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire `app.yml` → `AppBaseSettings` so Pydantic Literal validation fires for YAML-driven configs. Brings Phase 2 mechanical-four's `StyleName = Literal["vanilla", "fastblocks_ui"]` validation to life in production.

**Architecture:** Three-layer change. Layer 1: `AppBaseSettings` adds 4 fields matching the `mcp/resources.py:288` documented schema. Layer 2: `fastblocks/core/settings_loader.py` (NEW) wraps Oneiric's `load_settings` for fastblocks defaults. Layer 3: `AppSettings()` instantiation in `default.py:182` uses the loader with a soft fallback when `app.yml` is absent.

**Tech Stack:** Python 3.13, pydantic-settings BaseSettings (via OneiricSettings inheritance), Oneiric `load_settings(path, project_name)`, `pytest` + `@pytest.mark.unit`.

## Global Constraints

These constraints bind every task in this plan. Any deviation is a plan-level bug to flag before proceeding.

- **Python 3.13** — `from __future__ import annotations` first non-comment line of every source file.
- **Imports sorted within sections** — stdlib → third-party → first-party, with `force-sort-within-sections = true` and `known-first-party = ["fastblocks"]`.
- **Modern syntax** — `X | None` (not `Optional[X]`), `list[str]` (not `List[str]`), `pathlib.Path` for filesystem paths (not `os.path`).
- **Function arguments with default `None`** typed `X | None = None` (mypy `no_implicit_optional = true`).
- **No `assert` in production code** (`fastblocks/**`) — use the `fastblocks/core/errors.py` exception hierarchy.
- **No `Any` in tool inputs or orchestration state** — use `TYPE_CHECKING` + typed protocol.
- **In `except` blocks, use `logger.exception(...)`** — never `logger.error(..., exc_info=True)`.
- **Oneiric logger** (`oneiric.core.logging`) — not stdlib `logging`, not `print()`.
- **Async I/O in orchestration layer** — no blocking calls inside async functions.
- **Per-test timeout: 300 s ceiling, not target.** Tests >10 s `@pytest.mark.slow` and skipped with `-m "not slow"` for fast feedback.
- **No `# type: ignore`** in production code without prior approval.
- **No bare `# noqa`** — crackerjack-compliant-code enforces.
- **Hard limits** (crackerjack gate fails on breach):
  - Line length: 100 chars
  - Function args: 10 (excludes self, cls, \*args, \*\*kwargs)
  - Branches: 15
  - Returns: 6
  - Statements: 55
- **Test markers** — `@pytest.mark.unit` for new tests (no new markers invented).
- **`# ty: ignore[rule]` syntax** — ty uses `# ty: ignore[rule]`, not `# type: ignore`.
- **No `git push` to `origin/main`** — Bodai pre-1.0 merge policy: branch → ff-merge into main.
- **Author email** for commits: `les@wedgwoodwebworks.com` (NOT `.local`).
- **suppress(Exception) ratchet** holds at empirical 122 sites.
- **Canary validation** — every test must be verified to fail against pre-fix code via revert/comment-out/replace pattern.

______________________________________________________________________

## File Structure

| File | Status | Purpose |
|---|---|---|
| `fastblocks/adapters/app/_base.py` | MODIFY | Add 4 fields to AppBaseSettings |
| `fastblocks/core/settings_loader.py` | NEW | Wraps Oneiric's load_settings for fastblocks defaults |
| `fastblocks/adapters/app/default.py` | MODIFY | Wire loader into AppSettings() at line 182 |
| `fastblocks/mcp/resources.py` | MODIFY | Update docs at line 288 — AppBaseSettings is canonical schema source |
| `tests/core/test_settings_loader.py` | NEW | 6 tests for loader happy path + failure modes |
| `tests/core/test_app_settings_yaml_wiring.py` | NEW | 4 tests for end-to-end AppSettings YAML wiring |

______________________________________________________________________

## Task 1: feat(settings) — add 4 fields to AppBaseSettings

**Files:**

- Modify: `fastblocks/adapters/app/_base.py:11-15` (existing AppBaseSettings class body)
- Test: `tests/core/test_app_settings_literal.py` (existing — verify no regression)

**Interfaces:**

- Consumes: existing AppBaseSettings class (extending OneiricSettings); `from fastblocks.core.validators import DEFAULT_STYLE, StyleName` (existing import)

- Produces: AppBaseSettings with 4 new fields: `title: str = ""`, `domain: str = ""`, `description: str = ""`, `version: str = ""`

- [ ] **Step 1: Read the current AppBaseSettings class body**

Read: `/Users/les/Projects/fastblocks/fastblocks/adapters/app/_base.py:11-15` to confirm the current field layout. Confirm the existing `# type: ignore[misc]` is on the class declaration line.

- [ ] **Step 2: Add 4 new fields to AppBaseSettings**

In `fastblocks/adapters/app/_base.py`, after the existing `theme: str = "light"` line, add:

```python
    title: str = ""
    domain: str = ""
    description: str = ""
    version: str = ""
```

The `# type: ignore[misc]` on the class declaration stays as-is (pre-existing typing friction, not in scope).

- [ ] **Step 3: Verify no regression in existing tests**

Run: `cd /Users/les/Projects/fastblocks && unset VIRTUAL_ENV UV_ACTIVE UV_PROJECT_ENVIRONMENT && /Users/les/Projects/fastblocks/.venv/bin/pytest tests/core/test_app_settings_literal.py -v --no-cov --no-header`

Expected: 7 tests PASS (existing). No new failures. The 4 new fields default to empty strings, so any caller of `AppSettings()` continues to work.

- [ ] **Step 4: Smoke-test instantiation**

Run: `cd /Users/les/Projects/fastblocks && unset VIRTUAL_ENV UV_ACTIVE UV_PROJECT_ENVIRONMENT && /Users/les/Projects/fastblocks/.venv/bin/python -c "from fastblocks.adapters.app._base import AppBaseSettings; s = AppBaseSettings(); assert s.title == '' and s.domain == '' and s.description == '' and s.version == '' and s.style == 'fastblocks_ui'; print('OK')"`

Expected: `OK` printed. The 4 new fields default to empty strings; existing `style` field still defaults to `DEFAULT_STYLE = "fastblocks_ui"`.

- [ ] **Step 5: Verify ty ratchet holds**

Run: `cd /Users/les/Projects/fastblocks && unset VIRTUAL_ENV UV_ACTIVE UV_PROJECT_ENVIRONMENT && /Users/les/Projects/fastblocks/.venv/bin/python -m crackerjack.tools.ty_ratchet --split`

Expected: `ty ratchet [split] prod: PASS (0/50)`. No new ty suppressions introduced.

- [ ] **Step 6: Commit**

Run: `cd /Users/les/Projects/fastblocks && git checkout -b task/phase2-5-appbase-fields main && git add fastblocks/adapters/app/_base.py && git -c user.name=les -c user.email=les@wedgwoodwebworks.com commit -m "feat(settings): Phase 2.5 Commit1 — AppBaseSettings.title/domain/description/version"`

Then ff-merge into main:

```bash
cd /Users/les/Projects/fastblocks && git checkout main && git merge --ff-only task/phase2-5-appbase-fields && git branch -d task/phase2-5-appbase-fields && git push origin main
```

______________________________________________________________________

## Task 2: feat(settings) — `fastblocks/core/settings_loader.py` wraps Oneiric.load_settings

**Files:**

- Create: `fastblocks/core/settings_loader.py` (NEW, ~30 lines)
- Create: `tests/core/test_settings_loader.py` (NEW, 6 tests)

**Interfaces:**

- Consumes: `oneiric.core.config.load_settings(path, project_name)` (existing function at `oneiric/core/config.py:276`); `fastblocks.adapters.app.default.AppSettings` (existing class)

- Produces: `load_fastblocks_settings(path: str | Path | None = None) -> AppSettings`; re-exports `FileNotFoundError` for callers to catch explicitly

- [ ] **Step 1: Write the failing test file (TDD)**

Create `tests/core/test_settings_loader.py`:

```python
"""fastblocks settings loader tests (Phase 2.5 Commit2)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from fastblocks.adapters.app.default import AppSettings
from fastblocks.core.settings_loader import (
    load_fastblocks_settings,
    _FILE_NOT_FOUND,
)


class TestLoadFastblocksSettings:
    def test_loader_returns_app_settings_with_yaml_fields(
        self, tmp_path: Path
    ) -> None:
        """Happy path: yaml file at tmp_path, fields populate AppSettings."""
        yaml_path = tmp_path / "app.yml"
        yaml_path.write_text(
            "title: 'Test App'\n"
            "domain: 'example.com'\n"
            "style: 'vanilla'\n"
            "version: '1.0.0'\n"
        )
        s = load_fastblocks_settings(path=str(yaml_path))
        assert s.title == "Test App"
        assert s.domain == "example.com"
        assert s.style == "vanilla"
        assert s.version == "1.0.0"

    def test_loader_raises_filenotfound_when_no_yaml(
        self, tmp_path: Path
    ) -> None:
        """No yaml at any path → FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_fastblocks_settings(path=str(tmp_path / "nonexistent.yml"))

    def test_loader_propagates_yaml_error(self, tmp_path: Path) -> None:
        """Malformed YAML propagates yaml.YAMLError."""
        bad_yaml = tmp_path / "bad.yml"
        bad_yaml.write_text("title: 'unclosed\ndomain: 'x'\n")
        with pytest.raises(yaml.YAMLError):
            load_fastblocks_settings(path=str(bad_yaml))

    def test_loader_rejects_invalid_literal_via_pydantic(
        self, tmp_path: Path
    ) -> None:
        """YAML with style: 'kelp' triggers Pydantic ValidationError (Literal)."""
        from pydantic import ValidationError

        bad_yaml = tmp_path / "kelp.yml"
        bad_yaml.write_text("style: 'kelp'\n")
        with pytest.raises(ValidationError):
            load_fastblocks_settings(path=str(bad_yaml))

    def test_loader_ignores_extra_yaml_fields(
        self, tmp_path: Path
    ) -> None:
        """Unknown YAML fields are silently dropped (extra='ignore')."""
        yaml_path = tmp_path / "extra.yml"
        yaml_path.write_text("style: 'vanilla'\nunknown_field: 'x'\n")
        s = load_fastblocks_settings(path=str(yaml_path))
        assert s.style == "vanilla"

    def test_loader_falls_back_to_defaults_when_yaml_empty(
        self, tmp_path: Path
    ) -> None:
        """Empty YAML file → AppSettings with all defaults."""
        yaml_path = tmp_path / "empty.yml"
        yaml_path.write_text("")
        s = load_fastblocks_settings(path=str(yaml_path))
        assert s.style == "fastblocks_ui"  # DEFAULT_STYLE
        assert s.title == ""
```

- [ ] **Step 2: Run tests to verify they fail (pre-implementation FAIL)**

Run: `cd /Users/les/Projects/fastblocks && unset VIRTUAL_ENV UV_ACTIVE UV_PROJECT_ENVIRONMENT && /Users/les/Projects/fastblocks/.venv/bin/pytest tests/core/test_settings_loader.py -v --no-cov --no-header`

Expected: 6 tests FAIL with `ModuleNotFoundError: No module named 'fastblocks.core.settings_loader'` or similar.

- [ ] **Step 3: Write the loader module**

Create `fastblocks/core/settings_loader.py`:

```python
"""fastblocks settings loader.

Wraps Oneiric's load_settings with fastblocks defaults: project_name="fastblocks",
default path resolution via Oneiric's XDG-compliant layered lookup.
Returns AppSettings (not raw OneiricSettings) so callers get the
fastblocks schema.

Soft-fallback contract: callers (typically AppSettings() instantiation
sites) should wrap the call in `try/except FileNotFoundError` to
preserve the "defaults-only when no app.yml exists" back-compat
behavior.
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
    Raises FileNotFoundError if no app.yml exists at any resolved path;
    callers handle the fallback.

    Args:
        path: Optional explicit path. Highest priority. Defaults to
            Oneiric's XDG-compliant layered lookup
            (~/.config/fastblocks/config.yaml → ./app.yml → defaults).

    Returns:
        AppSettings populated from YAML + Oneiric defaults.
    """
    from oneiric.core.config import load_settings  # local import — avoids module-load cycle

    oneiric = load_settings(path=path, project_name="fastblocks")
    return AppSettings.model_validate(oneiric.model_dump(mode="python"))


__all__ = ["load_fastblocks_settings", "_FILE_NOT_FOUND"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/les/Projects/fastblocks && unset VIRTUAL_ENV UV_ACTIVE UV_PROJECT_ENVIRONMENT && /Users/les/Projects/fastblocks/.venv/bin/pytest tests/core/test_settings_loader.py -v --no-cov --no-header`

Expected: 6 tests PASS.

- [ ] **Step 5: Canary — verify the happy path test catches missing wiring**

Revert `fastblocks/core/settings_loader.py` to a stub that raises `NotImplementedError`:

```python
def load_fastblocks_settings(path=None):
    raise NotImplementedError("canary")
```

Run the test file. Expected: 6 tests FAIL. Restore the loader. Re-run; 6 tests PASS.

- [ ] **Step 6: Run full unit sweep to verify no regression**

Run: `cd /Users/les/Projects/fastblocks && unset VIRTUAL_ENV UV_ACTIVE UV_PROJECT_ENVIRONMENT && /Users/les/Projects/fastblocks/.venv/bin/pytest tests/core/ -q --no-cov --no-header`

Expected: all existing `tests/core/` tests still pass (no regression). The 6 new tests pass. Total test count increases by 6.

- [ ] **Step 7: Commit**

Run:

```bash
cd /Users/les/Projects/fastblocks && git checkout -b task/phase2-5-settings-loader main
git add fastblocks/core/settings_loader.py tests/core/test_settings_loader.py
git -c user.name=les -c user.email=les@wedgwoodwebworks.com commit -m "feat(settings): Phase 2.5 Commit2 — settings_loader.py wraps Oneiric.load_settings"
git checkout main
git merge --ff-only task/phase2-5-settings-loader
git branch -d task/phase2-5-settings-loader
git push origin main
```

______________________________________________________________________

## Task 3: refactor(app) — wire AppSettings() to use loader with soft fallback

**Files:**

- Modify: `fastblocks/adapters/app/default.py` (the one AppSettings() call site — but the tests construct AppSettings() directly, so wire at the AppSettings.__init__ level for full coverage)
- Create: `tests/core/test_app_settings_yaml_wiring.py` (NEW, 4 tests)
- Modify: `fastblocks/mcp/resources.py:288` (update doc to point at AppBaseSettings as canonical schema source)

**Interfaces:**

- Consumes: `load_fastblocks_settings()` from Task 2; existing AppSettings constructor

- Produces: `AppSettings()` instantiation that tries YAML loader first, falls back to defaults on FileNotFoundError

- [ ] **Step 1: Write the failing test file (TDD)**

Create `tests/core/test_app_settings_yaml_wiring.py`:

```python
"""AppSettings YAML wiring tests (Phase 2.5 Commit3)."""

from __future__ import annotations

from pathlib import Path

import pytest


class TestAppSettingsYamlWiring:
    def test_app_settings_reads_title_from_yaml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AppSettings() picks up title from CWD/app.yml."""
        yaml_path = tmp_path / "app.yml"
        yaml_path.write_text("title: 'Wired Title'\n")
        monkeypatch.chdir(tmp_path)
        from fastblocks.adapters.app.default import AppSettings
        s = AppSettings()
        assert s.title == "Wired Title"

    def test_app_settings_soft_fallback_when_no_yaml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AppSettings() works with defaults when no app.yml exists anywhere."""
        monkeypatch.chdir(tmp_path)  # empty dir, no app.yml
        from fastblocks.adapters.app.default import AppSettings
        s = AppSettings()
        # Defaults: style="fastblocks_ui", title=""
        assert s.style == "fastblocks_ui"
        assert s.title == ""

    def test_app_settings_rejects_invalid_yaml_style(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """YAML with style='kelp' triggers Pydantic ValidationError."""
        from pydantic import ValidationError
        yaml_path = tmp_path / "app.yml"
        yaml_path.write_text("style: 'kelp'\n")
        monkeypatch.chdir(tmp_path)
        from fastblocks.adapters.app.default import AppSettings
        with pytest.raises(ValidationError):
            AppSettings()

    def test_app_settings_round_trip_yaml_to_dump(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Loaded AppSettings can be dumped back to YAML-compatible dict."""
        yaml_path = tmp_path / "app.yml"
        yaml_path.write_text(
            "title: 'Round Trip'\n"
            "domain: 'rt.example'\n"
            "style: 'vanilla'\n"
        )
        monkeypatch.chdir(tmp_path)
        from fastblocks.adapters.app.default import AppSettings
        s = AppSettings()
        dumped = s.model_dump()
        assert dumped["title"] == "Round Trip"
        assert dumped["domain"] == "rt.example"
        assert dumped["style"] == "vanilla"
```

- [ ] **Step 2: Run tests to verify they fail (pre-implementation FAIL)**

Run: `cd /Users/les/Projects/fastblocks && unset VIRTUAL_ENV UV_ACTIVE UV_PROJECT_ENVIRONMENT && /Users/les/Projects/fastblocks/.venv/bin/pytest tests/core/test_app_settings_yaml_wiring.py -v --no-cov --no-header`

Expected: 4 tests FAIL with `AssertionError: assert '' == 'Wired Title'` (AppSettings doesn't read YAML yet — defaults to empty title).

- [ ] **Step 3: Wire the loader into AppSettings call site**

In `fastblocks/adapters/app/default.py:182`, replace:

```python
        self.settings = AppSettings()
```

with:

```python
        try:
            from fastblocks.core.settings_loader import load_fastblocks_settings
            self.settings = load_fastblocks_settings()
        except FileNotFoundError:
            self.settings = AppSettings()
```

The local import inside the try block avoids module-load circular imports (AppSettings imports default.py imports settings_loader.py imports AppSettings). Oneiric's XDG-compliant layered lookup will find `./app.yml` (CWD) first.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/les/Projects/fastblocks && unset VIRTUAL_ENV UV_ACTIVE UV_PROJECT_ENVIRONMENT && /Users/les/Projects/fastblocks/.venv/bin/pytest tests/core/test_app_settings_yaml_wiring.py -v --no-cov --no-header`

Expected: 4 tests PASS.

- [ ] **Step 5: Update mcp/resources.py docs**

In `fastblocks/mcp/resources.py:288`, replace the existing `app.yml` documentation block (lines 285-296) with:

```python
            "app.yml": {
                "description": "Application configuration. Schema source: "
                "fastblocks.adapters.app._base.AppBaseSettings (canonical). "
                "Optional — when absent, defaults from AppBaseSettings are used. "
                "When present, Pydantic validates every field; invalid Literal "
                "values (e.g., style: kelp) raise ValidationError at startup.",
                "schema_source": "fastblocks.adapters.app._base.AppBaseSettings",
                "fields": {
                    "title": "Application title (optional)",
                    "domain": "Application domain (optional)",
                    "description": "Application description (optional)",
                    "version": "Application version (optional)",
                    "name": "App name (defaults to 'fastblocks')",
                    "style": "Style — Literal['vanilla', 'fastblocks_ui']",
                    "theme": "UI theme (defaults to 'light')",
                },
            },
```

(Adjust indentation to match the existing file's style — read the surrounding code first.)

- [ ] **Step 6: Verify no regression in all existing tests**

Run: `cd /Users/les/Projects/fastblocks && unset VIRTUAL_ENV UV_ACTIVE UV_PROJECT_ENVIRONMENT && /Users/les/Projects/fastblocks/.venv/bin/pytest tests/core/ -q --no-cov --no-header 2>&1 | tail -20`

Expected: all tests pass (the 20 pre-existing baseline failures stay pre-existing; no new failures).

- [ ] **Step 7: Canary — verify the loader wiring catches no-YAML case**

Revert `fastblocks/adapters/app/default.py:182` to direct `self.settings = AppSettings()` (no try/except).

Run: `cd /Users/les/Projects/fastblocks && unset VIRTUAL_ENV UV_ACTIVE UV_PROJECT_ENVIRONMENT && /Users/les/Projects/fastblocks/.venv/bin/pytest tests/core/test_app_settings_yaml_wiring.py::TestAppSettingsYamlWiring::test_app_settings_reads_title_from_yaml -v --no-cov --no-header`

Expected: 1 test FAILS — title is empty string (no YAML read). Restore the wiring. Re-run; 1 test PASSES.

- [ ] **Step 8: Run ty ratchet verification**

Run: `cd /Users/les/Projects/fastblocks && unset VIRTUAL_ENV UV_ACTIVE UV_PROJECT_ENVIRONMENT && /Users/les/Projects/fastblocks/.venv/bin/python -m crackerjack.tools.ty_ratchet --split`

Expected: `ty ratchet [split] prod: PASS (0/50)`. No new production suppressions.

- [ ] **Step 9: Run suppress(Exception) ratchet**

Run: `cd /Users/les/Projects/fastblocks && unset VIRTUAL_ENV UV_ACTIVE UV_PROJECT_ENVIRONMENT && /Users/les/Projects/fastblocks/.venv/bin/pytest tests/core/test_suppress_exception_ratchet.py -v --no-cov --no-header`

Expected: 1 test PASSES at 122 sites (ratchet holds; no new suppressions added).

- [ ] **Step 10: Manual smoke test (literal validation fires for YAML values)**

Run:

```bash
cd /tmp && rm -rf phase25_smoke && mkdir phase25_smoke && cd phase25_smoke
echo "style: kelp" > app.yml
unset VIRTUAL_ENV UV_ACTIVE UV_PROJECT_ENVIRONMENT
PYTHONPATH=/Users/les/Projects/fastblocks /Users/les/Projects/fastblocks/.venv/bin/python -c "from fastblocks.adapters.app.default import AppSettings; AppSettings()" 2>&1 | head -10
```

Expected: `pydantic.ValidationError` mentioning `Input should be 'vanilla' or 'fastblocks_ui' [type=literal_error, input_value='kelp', input_type=str]`. The Literal validation fires for the first time in production.

Clean up: `rm -rf /tmp/phase25_smoke`

- [ ] **Step 11: Commit**

Run:

```bash
cd /Users/les/Projects/fastblocks && git checkout -b task/phase2-5-app-settings-wiring main
git add fastblocks/adapters/app/default.py fastblocks/mcp/resources.py tests/core/test_app_settings_yaml_wiring.py
git -c user.name=les -c user.email=les@wedgwoodwebworks.com commit -m "refactor(app): Phase 2.5 Commit3 — AppSettings() uses loader with soft fallback"
git checkout main
git merge --ff-only task/phase2-5-app-settings-wiring
git branch -d task/phase2-5-app-settings-wiring
git push origin main
```

______________________________________________________________________

## Final Verification

After all 3 commits land on `main`:

- [ ] **Full unit sweep — no regression**

Run: `cd /Users/les/Projects/fastblocks && unset VIRTUAL_ENV UV_ACTIVE UV_PROJECT_ENVIRONMENT && /Users/les/Projects/fastblocks/.venv/bin/pytest -m "not slow" -q --no-cov --no-header 2>&1 | tail -20`

Expected: all previously-passing tests still pass. The 20 pre-existing baseline failures stay at 20 (not increased). Total test count increases by 10 (6 from Commit 2 + 4 from Commit 3).

- [ ] **All Phase 2.5 tests pass**

Run: `cd /Users/les/Projects/fastblocks && unset VIRTUAL_ENV UV_ACTIVE UV_PROJECT_ENVIRONMENT && /Users/les/Projects/fastblocks/.venv/bin/pytest tests/core/test_settings_loader.py tests/core/test_app_settings_yaml_wiring.py tests/core/test_app_settings_literal.py tests/core/test_suppress_exception_ratchet.py -v --no-cov --no-header`

Expected: 6 + 4 + 7 + 1 = 18 tests PASS.

- [ ] **ty ratchet prod PASS at 0/50**

Run: `cd /Users/les/Projects/fastblocks && unset VIRTUAL_ENV UV_ACTIVE UV_PROJECT_ENVIRONMENT && /Users/les/Projects/fastblocks/.venv/bin/python -m crackerjack.tools.ty_ratchet --split`

Expected: `ty ratchet [split] prod: PASS (0/50)`. No new production suppressions.

- [ ] **suppress(Exception) ratchet holds at 122**

Run: `cd /Users/les/Projects/fastblocks && unset VIRTUAL_ENV UV_ACTIVE UV_PROJECT_ENVIRONMENT && /Users/les/Projects/fastblocks/.venv/bin/pytest tests/core/test_suppress_exception_ratchet.py -v --no-cov --no-header`

Expected: 1 test PASS at 122 sites.

- [ ] **No uncommitted working-tree edits**

Run: `cd /Users/les/Projects/fastblocks && git status --porcelain`

Expected: empty output.

______________________________________________________________________

## Out of scope (deferred)

- Renderer match-statement dispatch (ADR 0010 Decision 9)
- SafeHTMLStr propagation (ADR 0010 Decision 10)
- Match dispatch on style axis (ADR 0010 Decision 11 — blocked by Protocol method-name mismatch)
- Required-when-present tightening for `title` / `domain` fields
- Migrating existing fastblocks apps to use `app.yml`
- Closing `# type: ignore[misc]` on `AppBaseSettings(OneiricSettings)` declaration
- Oneiric's `AppConfig` modifications
- Phase 4 design + implementation (separate workstream)

______________________________________________________________________

## Self-review notes

The plan was written against the spec at `docs/superpowers/specs/2026-08-22-fastblocks-phase-2-5-design.md`. Placeholder scan: clean (no `TODO`, `TBD`, "fill in", or "implement later" tokens). Internal consistency: test count (6+4+7+1=18) matches the spec's "10 new tests" claim (6+4). Ambiguity: the AppSettings() call site wiring in Task 3 Step 3 uses a local import inside the try block to avoid module-load cycles — flagged in the comment so the implementer doesn't move it to the top. Scope: thin slice as defined; out-of-scope items enumerated explicitly.

Cross-references:

- Spec: `docs/superpowers/specs/2026-08-22-fastblocks-phase-2-5-design.md`
- ADR: `docs/adr/0010-phase-2-mechanical-four.md` Decisions 7, 9-12
- Master plan: `docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md` line 312 (wiring deferred)
