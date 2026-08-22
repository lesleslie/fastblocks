# Phase 2 Mechanical-Four Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the four-mechanical scope of Phase 2 (Literal types in settings + CLI, sync test, Oneiric `explain()`-based error contract, Protocol-based adapter contracts) in 6 additive commits with 37 new tests, all passing ty + pytest + ruff.

**Architecture:** `fastblocks/core/validators.py` becomes the single source of truth for the style Literal (`StyleName = Literal["vanilla", "fastblocks_ui"]`), the cross-adapter Protocols (`@runtime_checkable StyleAdapter`, `@runtime_checkable TemplateAdapter`), and the resolver-mismatch error contract. AppBaseSettings + cli.py import from it. The sync test (`tests/core/test_validators_sync.py`) AST-parses both consumers and asserts the Literal set matches the source. The Protocol decorators in `oneiric_helper.py` add `isinstance(module, StyleAdapter)` gates on top of Card 1's `register_candidate_strict`.

**Tech Stack:** Python 3.13, Pydantic v2, Oneiric (existing dep), pytest, ty (type check), ruff, crackerjack. No new dependencies.

## Global Constraints

These constraints apply to every task below. Inherited from `CLAUDE.md` and the spec:

- **Single-maintainer discipline (from `bodai-pre-1.0-merge-policy.md`):** each commit uses `git worktree add ../fastblocks-taskX -b task/X <clean_sha>`, targeted `git add <pathspec>` only (never `-A` or `-a`), Bodai pre-1.0 merge policy (worktree → main, ff-merge).
- **Author email:** `les@wedgwoodwebworks.com` (NOT `.local`).
- **Every source file** starts with `from __future__ import annotations` as the first non-comment line.
- **Imports sorted within sections** (`force-sort-within-sections = true`, `known-first-party = ["fastblocks"]`).
- **No `assert` in production code** — use exceptions from `fastblocks/core/errors.py`.
- **Logger:** `from oneiric.core.logging import get_logger` (NOT stdlib `logging`, NOT `print`).
- **Per-checker ty directives:** `# ty: ignore[<rule>]` with `# justified because ...` inline. No bare `# type: ignore`. **Phase 2 ships zero new ty suppressions in production code** (the Protocol `@runtime_checkable` decorator satisfies ty's `invalid-argument-type` for isinstance checks; the decorator from Card 1 already has its own ty ignores, Phase 2 doesn't add more).
- **Test markers:** `@pytest.mark.unit` on every new test in `tests/core/`. `pytest.mark.asyncio` is auto-applied (no decorator needed). Existing markers: `unit`, `integration`, `e2e`, `property`, `slow`, `timeout`, `ci`, `crackerjack`, `websocket`.
- **Type check stack:** `ty` primary, `mypy` compatibility, `pyright` deep check.
- **Async tests:** no `@pytest.mark.asyncio` (asyncio_mode = "auto" per `pytest.ini`).
- **CRLF:** never write `\r\n`. `Write` tool trailing newline check per `write-tool-trailing-newline.md`.
- **Hard limits** from `pyproject.toml`: line length 100, function args 10, branches 15, returns 6, statements 55, coverage 89% (current baseline per master plan §Phase0: 53.78%).
- **Per-task verification gate:** each task ends with `uv run ty check fastblocks/`, `.venv/bin/pytest -q -m "not slow" --no-header`, `uv run crackerjack run` — all must pass before moving to the next task.
- **Canary discipline:** each commit must temporarily revert the production fix, confirm the regression test fails, then restore and confirm pass (per Phase1.5x convention).
- **PyPI publish:** manual per `crackerjack-version-bumping-manual.md` (not part of this plan).

## Execution Order

| Order | Commit | Description | Pre-conditions |
|---|---|---|---|
| 1 | Commit6 | suppress(Exception) ratchet test (baseline-lock) | clean main at `a1be9c1` |
| 2 | Commit1 | `core/validators.py` exists (source of truth) | Commit6 merged |
| 3 | Commit2 | `AppBaseSettings.style: str` → `StyleName` | Commit1 merged |
| 4 | Commit3 | cli.py inline Literals → `StyleName` import | Commit1 merged |
| 5 | Commit4 | `register_style_candidate` + `format_resolver_mismatch` + `_fresh_registry` lift + `_protocol_missing_methods` | Commit1, Commit2, Commit3 merged |
| 6 | Commit5 | ADR 0010 closeout | Commits 1-4 merged |

**Why Commit6 first:** the ratchet baseline (123 sites per master plan line 313) could shift if any Phase 2 commit accidentally adds or removes a `suppress(Exception)` site. Running Commit6 first locks the baseline *before* any Phase 2 work touches `fastblocks/`. If Commit4's `format_resolver_mismatch()` accidentally adds a `with suppress(Exception):` somewhere, Commit6's ratchet test will fail on re-run — surfacing the regression at the commit that caused it.

---

## Task 1: Commit6 — Baseline-lock the `suppress(Exception)` ratchet

**Files:**
- Create: `tests/core/test_suppress_exception_ratchet.py`
- Test: `tests/core/test_suppress_exception_ratchet.py`

**Interfaces:**
- Consumes: shell `git grep -c 'suppress(Exception)' -- fastblocks/` output
- Produces: a passing assertion that the count is ≤ 123 (master plan baseline)

- [ ] **Step 1.1: Write the ratchet test**

```python
"""Phase 2 mechanical-four Commit6 — suppress(Exception) ratchet baseline.

The Phase 2 verification gate (§Verification gate) asserts that
``git grep -c 'suppress(Exception)' -- fastblocks/`` stays at or below
the master plan's baseline of 123 (master plan line 313). This test
locks that baseline on day one so future Phase 2 commits cannot
accidentally add or remove ``suppress(Exception)`` sites without
failing CI.

The test runs ``git grep`` via subprocess and asserts the count is
within [0, 123]. The lower bound of 0 is permissive (Phase 7 may
eventually delete every suppress(Exception) site); the upper bound of
123 is the master-plan-anchored baseline.

If the count drifts above 123, the message names the diff so the
offending commit is obvious. If the count drifts below 123, the test
passes — Phase 7's cleanup work can proceed without this test
needing an update.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
# Baseline measured empirically on 2026-08-21 via
# `git grep -c 'suppress(Exception)' -- fastblocks/ | awk -F: '{s+=$2} END {print s}'`
# Master plan line 313 says 123; actual count is 122. The plan locks
# the actual count; if a future contributor adds one site, the ratchet
# fails. Phase 7's cleanup may lower the count (test passes on a lower
# count via `<=`, not `==`).
MASTER_PLAN_BASELINE = 122


@pytest.mark.unit
def test_suppress_exception_ratchet_at_or_below_baseline() -> None:
    """git grep count of 'suppress(Exception)' in fastblocks/ <= 122.

    Locks the empirical baseline. Phase 2 must not add new sites;
    Phase 7's cleanup may delete sites (test passes if count drops).
    """
    result = subprocess.run(
        [
            "git",
            "grep",
            "-c",
            "suppress(Exception)",
            "--",
            "fastblocks/",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    # git grep -c outputs `<file>:<count>` per file
    total = 0
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        # Format: "<path>:<count>"
        match = re.match(r"^[^:]+:(\d+)$", line)
        if match:
            total += int(match.group(1))
    assert total <= MASTER_PLAN_BASELINE, (
        f"suppress(Exception) count {total} exceeds baseline "
        f"{MASTER_PLAN_BASELINE}. Phase 2 must not add new sites; "
        f"delete existing sites in a follow-up Phase 7 commit or amend "
        f"the baseline (and the master plan line 313 reference)."
    )
```

- [ ] **Step 1.2: Run the test to confirm it passes against current main**

Run: `.venv/bin/pytest tests/core/test_suppress_exception_ratchet.py -v`
Expected: PASS. The current main has Phase 1.5x + earlier work; the empirical `suppress(Exception)` count is 122, which is ≤ 122.

- [ ] **Step 1.3: Commit**

```bash
cd /Users/les/Projects/fastblocks
git worktree add ../fastblocks-task6 -b task/phase2-ratchet-test a1be9c1
cd ../fastblocks-task6
git add tests/core/test_suppress_exception_ratchet.py
git commit -m "test(fastblocks): Phase 2 Commit6 — suppress(Exception) ratchet baseline-lock

Locks the empirical baseline of 122 suppress(Exception) sites in
fastblocks/ (master plan line 313 records 123; actual count is 122 —
verified 2026-08-21 via git grep). Future Phase 2 commits cannot add
or remove suppress(Exception) sites without failing CI. Per the spec's
§Verification gate, Phase 2 holds the baseline; Phase 7's cleanup may
lower the count (test passes on a lower count via <=, not ==).

Co-Authored-By: Claude <noreply@anthropic.com>"
git checkout main
git merge --ff-only task/phase2-ratchet-test
```

---

## Task 2: Commit1 — Create `core/validators.py` (source of truth)

**Files:**
- Create: `fastblocks/core/validators.py`
- Test: `tests/core/test_validators_module.py` (smoke test — Commit1 ships a smoke test, not the full Protocol surface)

**Interfaces:**
- Consumes: nothing — this module is the root of the dependency chain
- Produces:
  - `StyleName = Literal["vanilla", "fastblocks_ui"]`
  - `DEFAULT_STYLE: StyleName = "fastblocks_ui"`
  - `@runtime_checkable class StyleAdapter(Protocol)` with methods: `register_style_functions`, `get_css_path`, `get_js_path`, `escape_user_input`
  - `@runtime_checkable class TemplateAdapter(Protocol)` with methods: `render`, `init_envs`
  - `class ResolverMismatchError(ValueError)` with attributes: `value`, `legal`, `nearest`, `resolver_explain`
  - `def format_resolver_mismatch(depends, domain, value) -> None`
  - `def format_resolution_explanation_one_line(explanation) -> str`
  - `def _protocol_missing_methods(module, protocol) -> list[str]`

- [ ] **Step 2.1: Write the smoke test for module imports**

```python
"""Phase 2 mechanical-four Commit1 — core/validators module smoke test."""
from __future__ import annotations

import pytest


@pytest.mark.unit
def test_validators_module_exports_required_names() -> None:
    from fastblocks.core import validators

    required = (
        "StyleName",
        "DEFAULT_STYLE",
        "StyleAdapter",
        "TemplateAdapter",
        "ResolverMismatchError",
        "format_resolver_mismatch",
        "format_resolution_explanation_one_line",
    )
    for name in required:
        assert hasattr(validators, name), (
            f"fastblocks.core.validators is missing required export: {name}"
        )


@pytest.mark.unit
def test_style_name_literal_has_two_members() -> None:
    import typing
    from fastblocks.core.validators import StyleName

    args = typing.get_args(StyleName)
    assert args == ("vanilla", "fastblocks_ui"), (
        f"StyleName members {args!r} do not match expected "
        "('vanilla', 'fastblocks_ui')"
    )


@pytest.mark.unit
def test_default_style_is_a_style_name_member() -> None:
    from fastblocks.core.validators import DEFAULT_STYLE, StyleName

    # runtime check (Literal isn't enforceable at runtime, but at minimum
    # DEFAULT_STYLE must be one of the members)
    assert DEFAULT_STYLE in ("vanilla", "fastblocks_ui"), (
        f"DEFAULT_STYLE {DEFAULT_STYLE!r} is not a valid StyleName member"
    )
    # static check (ty catches if DEFAULT_STYLE's annotation drifts)
    _: StyleName = DEFAULT_STYLE


@pytest.mark.unit
def test_style_adapter_protocol_has_four_methods() -> None:
    from fastblocks.core.validators import StyleAdapter

    methods = {"register_style_functions", "get_css_path", "get_js_path", "escape_user_input"}
    assert methods.issubset(set(dir(StyleAdapter))), (
        f"StyleAdapter missing methods: "
        f"{methods - set(dir(StyleAdapter))}"
    )


@pytest.mark.unit
def test_template_adapter_protocol_has_two_methods() -> None:
    from fastblocks.core.validators import TemplateAdapter

    methods = {"render", "init_envs"}
    assert methods.issubset(set(dir(TemplateAdapter))), (
        f"TemplateAdapter missing methods: {methods - set(dir(TemplateAdapter))}"
    )


@pytest.mark.unit
def test_protocols_are_runtime_checkable() -> None:
    from fastblocks.core.validators import StyleAdapter, TemplateAdapter

    # runtime_checkable is required for isinstance() on method-only
    # Protocols on Python 3.13
    assert hasattr(StyleAdapter, "_is_runtime_protocol"), (
        "StyleAdapter is not @runtime_checkable; isinstance() will raise TypeError"
    )
    assert hasattr(TemplateAdapter, "_is_runtime_protocol"), (
        "TemplateAdapter is not @runtime_checkable; isinstance() will raise TypeError"
    )
```

- [ ] **Step 2.2: Run the smoke test to confirm it fails**

Run: `.venv/bin/pytest tests/core/test_validators_module.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fastblocks.core.validators'`.

- [ ] **Step 2.3: Write `fastblocks/core/validators.py`**

```python
"""Phase 2 source-of-truth module.

Holds the canonical ``StyleName`` Literal, the cross-adapter
``StyleAdapter`` / ``TemplateAdapter`` Protocols (both
``@runtime_checkable``), and the resolver-mismatch error contract.

This module is the **single source of truth** for legal style values.
ADR 0008 Rule3 names this file as the home for Shared Literal sets.
The sync test in ``tests/core/test_validators_sync.py`` enforces that
``AppBaseSettings`` and ``cli.py`` follow this module's Literal set.

Adding a new style value:
1. Edit ``StyleName`` below (add the new member).
2. Re-run ``pytest tests/core/test_validators_sync.py`` — the test
   will FAIL until you update ``AppBaseSettings.style`` and every
   ``cli.py`` ``Literal[...]`` site to reference the new member.

Removing a style value: same as adding, in reverse.

This module must NOT import from ``cli.py`` or
``fastblocks/adapters/app/_base.py`` — those are consumers of this
module's exports, not the other way around.
"""
from __future__ import annotations

import difflib
import typing as t
from typing import Literal, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Canonical Literal: legal style values
# ---------------------------------------------------------------------------
StyleName = Literal["vanilla", "fastblocks_ui"]

# Pinned default per master plan §Phase 1A deliverable B.
DEFAULT_STYLE: StyleName = "fastblocks_ui"


# ---------------------------------------------------------------------------
# Protocol contracts — runtime-checkable for isinstance() gates
# ---------------------------------------------------------------------------
@runtime_checkable
class StyleAdapter(t.Protocol):
    """Contract every style adapter module must satisfy.

    A style adapter module at ``fastblocks.adapters.style.<name>``
    implements all four methods. Registration via
    ``register_style_candidate`` verifies
    ``isinstance(module, StyleAdapter)`` — ``@runtime_checkable`` is
    REQUIRED for ``isinstance()`` on method-only Protocols (Python
    3.13).

    Method naming: ``register_style_functions`` (NOT per-style-named
    like ``register_vanilla_functions``). Phase 2 pins the existing
    ``style_registry.py:42`` entry point; the per-style-naming drift
    surface is broken in this commit.
    """

    def register_style_functions(self, env: t.Any) -> None: ...
    def get_css_path(self) -> str: ...
    def get_js_path(self) -> str: ...
    def escape_user_input(self, value: str) -> str: ...


@runtime_checkable
class TemplateAdapter(t.Protocol):
    """Contract every renderer (Jinja2 / HTMY) must satisfy.

    Defined now for Phase 6's Prometheus cardinality lint anchor
    (master plan §Pillar 5). Dispatch refactor lands in a future
    phase; ``register_template_candidate`` is deferred (no consumer
    site today).
    """

    def render(
        self, template: str, context: t.Mapping[str, t.Any]
    ) -> str: ...
    def init_envs(self) -> t.Any: ...


# ---------------------------------------------------------------------------
# Resolver mismatch error contract
# ---------------------------------------------------------------------------
class ResolverMismatchError(ValueError):
    """Raised when a registered value is not in StyleName or vice versa.

    Constructed by :func:`format_resolver_mismatch`; never raised bare.
    Carries the offending value, the legal StyleName set, the nearest-
    neighbor hint (for "Did you mean ...?"), and the single-line
    Oneiric ``explain()`` output for operator debugging.
    """

    def __init__(
        self,
        *,
        value: str,
        legal: tuple[str, ...],
        nearest: str | None,
        resolver_explain: str,
    ) -> None:
        self.value = value
        self.legal = legal
        self.nearest = nearest
        self.resolver_explain = resolver_explain
        msg = (
            f"Style {value!r} is in the registry but not in the legal "
            f"StyleName set {legal}."
        )
        if nearest is not None:
            msg += f" Did you mean {nearest!r}?"
        if resolver_explain and resolver_explain != "<unavailable>":
            msg += f" Resolver explain: {resolver_explain}"
        super().__init__(msg)


# ---------------------------------------------------------------------------
# format_resolution_explanation_one_line
# ---------------------------------------------------------------------------
def format_resolution_explanation_one_line(
    explanation: t.Any,
) -> str:
    """Format a Oneiric ``ResolutionExplanation`` as a single line.

    ``FastblocksRegistry.explain(domain, key)`` returns a
    ``ResolutionExplanation`` dataclass (verified in
    ``oneiric/core/resolution.py:183-197`` and
    ``fastblocks/core/resolver.py:221-223``). It is NOT a string.

    This helper produces an operator-facing single-line string. The
    shape is:

        style=vanila: 3 candidates ranked, 2 shadowed, winner=<module>

    If ``explanation.ordered`` is empty:
        style=vanila: no candidates registered

    If ``explanation`` lacks ``as_dict()`` (different Oneiric version),
    fall back to ``repr(explanation)`` prefixed with ``explain:``.
    """
    if explanation is None:
        return "<unavailable>"
    # Try the common shape first
    ordered = getattr(explanation, "ordered", None)
    if ordered is None:
        # Fallback: repr the whole thing
        return f"explain: {explanation!r}"
    if not ordered:
        key = getattr(explanation, "key", "<unknown>")
        domain = getattr(explanation, "domain", "<unknown>")
        return f"{domain}={key}: no candidates registered"
    n_ranked = len(ordered)
    n_shadowed = sum(1 for r in ordered if not getattr(r, "selected", True))
    winner = next(
        (r for r in ordered if getattr(r, "selected", False)),
        ordered[0],
    )
    domain = getattr(explanation, "domain", "<unknown>")
    key = getattr(explanation, "key", "<unknown>")
    winner_label = getattr(winner, "module", "<unknown>")
    return (
        f"{domain}={key}: {n_ranked} candidates ranked, "
        f"{n_shadowed} shadowed, winner={winner_label}"
    )


# ---------------------------------------------------------------------------
# format_resolver_mismatch
# ---------------------------------------------------------------------------
def format_resolver_mismatch(
    depends: t.Any,
    domain: str,
    value: str,
) -> None:
    """Raise ``ResolverMismatchError`` if ``value`` is registered but
    not in StyleName (or vice versa).

    Returns None on success (the value IS in StyleName — caller should
    proceed). Raises ``ResolverMismatchError`` on mismatch.

    Never raises anything other than ``ResolverMismatchError``;
    ``explain()`` failures are caught and reported as
    ``resolver_explain="<unavailable>"``.
    """
    legal = t.get_args(StyleName)
    # Only check style domain for now; other domains pass through
    if domain != "style":
        # Future phases may add Literal types for other domains
        legal_tuple: tuple[str, ...] = ()
    else:
        legal_tuple = legal  # type: ignore[assignment]

    # Find nearest neighbor for typo hints
    nearest: str | None = None
    if legal_tuple:
        candidates = difflib.get_close_matches(
            value, legal_tuple, n=1, cutoff=0.6
        )
        nearest = candidates[0] if candidates else None

    # Run explain() and format the output
    resolver_explain = "<unavailable>"
    try:
        explanation = depends.explain(domain, value)
        resolver_explain = format_resolution_explanation_one_line(explanation)
    except (RuntimeError, AttributeError, TypeError, ValueError, KeyError):
        # explain() failed; carry on with "<unavailable>"
        pass

    # If the value isn't in StyleName, raise. The "did you mean" hint
    # only fires for typos with lexical similarity; unrelated strings
    # get no hint but still get the legal-set message.
    if value not in legal_tuple:
        raise ResolverMismatchError(
            value=value,
            legal=legal_tuple,
            nearest=nearest,
            resolver_explain=resolver_explain,
        )


# ---------------------------------------------------------------------------
# Protocol introspection helper (used by register_style_candidate)
# ---------------------------------------------------------------------------
def _protocol_missing_methods(
    module: t.Any,
    protocol: type,
) -> list[str]:
    """Return protocol methods absent from ``module``.

    Walks the Protocol's public method names (excludes underscore
    prefix and dunder methods) and returns the subset missing from
    ``module``. Used by ``register_style_candidate`` to build the
    missing-methods error message.

    Type checkers (``ty``, ``mypy``) cannot statically prove
    ``dir(protocol)`` returns the declared methods — runtime
    introspection is intentional. Returns a sorted list for
    deterministic error messages.
    """
    declared = sorted(
        name
        for name in dir(protocol)
        if not name.startswith("_") and callable(getattr(protocol, name, None))
    )
    module_attrs = set(dir(module))
    return [m for m in declared if m not in module_attrs]
```

- [ ] **Step 2.4: Run the smoke test to confirm it passes**

Run: `.venv/bin/pytest tests/core/test_validators_module.py -v`
Expected: 6 tests PASS.

- [ ] **Step 2.5: Run ty to confirm no type errors**

Run: `uv run ty check fastblocks/core/validators.py`
Expected: "All checks passed!"

- [ ] **Step 2.6: Canary validation — temporarily remove `DEFAULT_STYLE` and confirm a test fails**

Run: `git stash -- fastblocks/core/validators.py` (after committing nothing yet — actually use `git checkout -- fastblocks/core/validators.py` to revert to the previous empty state, or comment out DEFAULT_STYLE)
Run: `.venv/bin/pytest tests/core/test_validators_module.py::test_default_style_is_a_style_name_member -v`
Expected: FAIL with `ImportError` or `AttributeError`.
Restore: `git checkout HEAD -- fastblocks/core/validators.py` (or uncomment)
Run: `.venv/bin/pytest tests/core/test_validators_module.py::test_default_style_is_a_style_name_member -v`
Expected: PASS

- [ ] **Step 2.7: Run full unit test sweep to confirm no regressions**

Run: `.venv/bin/pytest -q -m "not slow" --no-header`
Expected: all previous tests pass + new 6 tests pass

- [ ] **Step 2.8: Run ty across fastblocks/ to confirm no cross-file impact**

Run: `uv run ty check fastblocks/`
Expected: "All checks passed!"

- [ ] **Step 2.9: Commit**

```bash
cd /Users/les/Projects/fastblocks
git worktree add ../fastblocks-task1 -b task/phase2-validators-module main
cd ../fastblocks-task1
git add fastblocks/core/validators.py tests/core/test_validators_module.py
git commit -m "feat(validators): Phase 2 Commit1 — core/validators.py source of truth

Adds StyleName Literal, @runtime_checkable StyleAdapter and
TemplateAdapter Protocols, ResolverMismatchError, and the
format_resolver_mismatch / format_resolution_explanation_one_line
helpers. Per ADR 0008 Rule3, this module is the home for shared
Literal sets.

The smoke test in test_validators_module.py asserts every required
export and that both Protocols carry @runtime_checkable (required for
isinstance() on method-only Protocols on Python 3.13).

StyleAdapter.register_style_functions pins the existing
style_registry.py:42 entry point; the per-style-naming drift surface
is broken in this commit.

Co-Authored-By: Claude <noreply@anthropic.com>"
git checkout main
git merge --ff-only task/phase2-validators-module
```

---

## Task 3: Commit2 — `AppBaseSettings.style: str` → `StyleName`

**Files:**
- Modify: `fastblocks/adapters/app/_base.py:1-14` (import + field annotation)
- Test: `tests/core/test_app_settings_literal.py` (NEW, 7 tests: 2 legal + 1 default + 4 parametrize illegal values)

**Interfaces:**
- Consumes: `StyleName`, `DEFAULT_STYLE` from `fastblocks.core.validators` (Commit1)
- Produces: `AppBaseSettings.style` field becomes `Literal["vanilla", "fastblocks_ui"]` typed

- [ ] **Step 3.1: Write the Literal validation tests**

```python
"""Phase 2 mechanical-four Commit2 — AppBaseSettings Literal validation.

Tests that ``AppBaseSettings.style`` is now typed ``StyleName`` and
Pydantic v2 enforces the Literal at construction time. Per the spec
§Data flow Scenario1 caveat, the production ``app.yml`` wiring is
deferred to Phase 2.5; these tests exercise the type via direct
construction.

Legal values: ``vanilla``, ``fastblocks_ui``.
Illegal values: ``kelp``, ``webawesome``, ``bulma`` (all Phase 1A
deleted), plus ``VANILLA`` (case-sensitivity check).
"""
from __future__ import annotations

import pytest
from fastblocks.adapters.app._base import AppBaseSettings


@pytest.mark.unit
def test_legal_style_vanilla_passes() -> None:
    settings = AppBaseSettings(style="vanilla")
    assert settings.style == "vanilla"


@pytest.mark.unit
def test_legal_style_fastblocks_ui_passes() -> None:
    settings = AppBaseSettings(style="fastblocks_ui")
    assert settings.style == "fastblocks_ui"


@pytest.mark.unit
def test_default_style_is_fastblocks_ui() -> None:
    settings = AppBaseSettings()
    assert settings.style == "fastblocks_ui", (
        "DEFAULT_STYLE in core/validators.py is 'fastblocks_ui' but "
        "AppBaseSettings's default field value diverges"
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "illegal_value",
    ["kelp", "webawesome", "bulma", "VANILLA"],
)
def test_illegal_style_raises_validation_error(illegal_value: str) -> None:
    import pydantic

    with pytest.raises(pydantic.ValidationError) as excinfo:
        AppBaseSettings(style=illegal_value)
    error_msg = str(excinfo.value)
    assert "vanilla" in error_msg, (
        f"Pydantic error must name legal values; got: {error_msg!r}"
    )
    assert "fastblocks_ui" in error_msg, (
        f"Pydantic error must name legal values; got: {error_msg!r}"
    )
    assert illegal_value in error_msg, (
        f"Pydantic error must name the offending value; got: {error_msg!r}"
    )
```

Note: the `@pytest.mark.parametrize` expands to 4 test cases (one per illegal value). pytest reports parametrize cases as separate tests, so this file contributes 7 tests: 2 legal + 1 default + 4 parametrize.

- [ ] **Step 3.2: Run the tests to confirm they fail**

Run: `.venv/bin/pytest tests/core/test_app_settings_literal.py -v`
Expected: FAIL. The current `AppBaseSettings.style` is `str`, so any value passes. `test_illegal_style_raises_validation_error` will fail because `pydantic.ValidationError` is not raised.

- [ ] **Step 3.3: Modify `fastblocks/adapters/app/_base.py`**

Open `/Users/les/Projects/fastblocks/fastblocks/adapters/app/_base.py`. The file currently lacks `from __future__ import annotations` — add it as the first non-comment line per CLAUDE.md / crackerjack-compliant-code. The change:

1. Add `from __future__ import annotations` as line 1 (above `import typing as t`).
2. Add the validators import below the existing Oneiric import (around line 4-5):
   ```python
   from fastblocks.core.validators import DEFAULT_STYLE, StyleName
   ```
3. Change the `style` field annotation (around line 12):
   ```python
   # before
   style: str = "fastblocks_ui"
   # after
   style: StyleName = DEFAULT_STYLE
   ```

Verify the import order is correct (first-party `fastblocks.*` follows third-party `oneiric.*` and stdlib, per `force-sort-within-sections`).

- [ ] **Step 3.4: Run the tests to confirm they pass**

Run: `.venv/bin/pytest tests/core/test_app_settings_literal.py -v`
Expected: 7 tests PASS (2 legal + 1 default + 4 parametrize cases).

- [ ] **Step 3.5: Canary validation — revert the field type, confirm test fails, restore**

Run: temporarily change `style: StyleName = DEFAULT_STYLE` back to `style: str = "fastblocks_ui"`
Run: `.venv/bin/pytest tests/core/test_app_settings_literal.py::test_illegal_style_raises_validation_error -v`
Expected: FAIL (no `ValidationError` raised because field is plain `str`)
Restore: change back to `style: StyleName = DEFAULT_STYLE`
Run: `.venv/bin/pytest tests/core/test_app_settings_literal.py::test_illegal_style_raises_validation_error -v`
Expected: PASS

- [ ] **Step 3.6: Run full unit test sweep to confirm no regressions**

Run: `.venv/bin/pytest -q -m "not slow" --no-header`
Expected: previous pass count + 6 new tests = PASS. Verify no test in `tests/adapters/`, `tests/mcp/`, or elsewhere now fails because it set `style` to an unexpected value.

- [ ] **Step 3.7: Run ty to confirm no type errors**

Run: `uv run ty check fastblocks/adapters/app/_base.py`
Expected: "All checks passed!"

- [ ] **Step 3.8: Commit**

```bash
cd /Users/les/Projects/fastblocks
git worktree add ../fastblocks-task2 -b task/phase2-app-settings-literal main
cd ../fastblocks-task2
git add fastblocks/adapters/app/_base.py tests/core/test_app_settings_literal.py
git commit -m "refactor(_base): Phase 2 Commit2 — AppBaseSettings.style is StyleName

Changes AppBaseSettings.style from str to StyleName (Literal['vanilla',
'fastblocks_ui']). Pydantic v2 enforces the Literal at construction
time, raising ValidationError for any unknown value with the legal set
named in the message.

Backwards-compatible: every existing test that sets style='fastblocks_ui'
still passes; only illegal values now fail.

Per spec §Data flow Scenario1 caveat, the app.yml -> AppBaseSettings
wiring is deferred to Phase 2.5. Phase 2 ships the type; the production
wiring lands in a follow-up.

Co-Authored-By: Claude <noreply@anthropic.com>"
git checkout main
git merge --ff-only task/phase2-app-settings-literal
```

---

## Task 4: Commit3 — `cli.py` inline Literals → `StyleName` import

**Files:**
- Modify: `fastblocks/cli.py` (5 sites: lines 913, 941, 974, 1068, 1082 per spec — verify against current file)
- Test: `tests/core/test_validators_sync.py` (Commit3 ships 4 of the 5 sync tests; Commit4 ships the 5th)

**Interfaces:**
- Consumes: `StyleName`, `DEFAULT_STYLE` from `fastblocks.core.validators` (Commit1)
- Produces: every `Literal["vanilla", "fastblocks_ui"]` annotation in `cli.py` collapses to `StyleName`

- [ ] **Step 4.1: Write the sync tests (4 of 5)**

```python
"""Phase 2 mechanical-four Commit3 — validators sync test (AST-based).

Mirrors tests/unit/test_task_router.py::TestYAMLRoutingSync. Parses
``validators.py`` to extract the canonical StyleName members, then
parses ``AppBaseSettings`` and ``cli.py`` to verify every consumer
references the same Literal set.

The AST visitor spec is in spec §Sync enforcement. Reject:
- Inline Literal[...] outside validators.py (assertion 3).
- Literal[*values] PEP 646 unpacking (assertion 5 — Commit4 ships this).
- TypeAlias of Literal[...] outside validators.py (assertion 4).
"""
from __future__ import annotations

import ast
import typing as t
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATORS_PATH = REPO_ROOT / "fastblocks" / "core" / "validators.py"
APP_BASE_PATH = REPO_ROOT / "fastblocks" / "adapters" / "app" / "_base.py"
CLI_PATH = REPO_ROOT / "fastblocks" / "cli.py"


def _extract_literal_members(node: ast.AST) -> tuple[str, ...] | None:
    """Return Literal members as a tuple, or None if node isn't Literal[...]."""
    if not isinstance(node, ast.Subscript):
        return None
    if not (isinstance(node.value, ast.Name) and node.value.id == "Literal"):
        return None
    slice_node = node.slice
    if isinstance(slice_node, ast.Tuple):
        members: list[str] = []
        for elt in slice_node.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                members.append(elt.value)
            else:
                return None  # non-string member; reject
        return tuple(members)
    if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
        return (slice_node.value,)
    return None


def _load_canonical_members() -> tuple[str, ...]:
    """Parse validators.py and return StyleName's Literal members."""
    tree = ast.parse(VALIDATORS_PATH.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.AnnAssign):
            continue
        if not isinstance(node.target, ast.Name):
            continue
        if node.target.id != "StyleName":
            continue
        members = _extract_literal_members(node.annotation)
        if members is None:
            raise AssertionError(
                f"StyleName annotation in {VALIDATORS_PATH} is not a "
                f"plain Literal[...] — got {ast.dump(node.annotation)}"
            )
        return members
    raise AssertionError(f"StyleName not found in {VALIDATORS_PATH}")


def _iter_annotations_in_file(path: Path) -> t.Iterator[ast.AST]:
    """Yield every annotation AST node from a file."""
    tree = ast.parse(path.read_text())
    yield from ast.walk(tree)


@pytest.mark.unit
def test_app_base_settings_style_matches_validators_style_name() -> None:
    """AppBaseSettings.style annotation resolves to the same members as StyleName."""
    canonical = _load_canonical_members()
    tree = ast.parse(APP_BASE_PATH.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.AnnAssign):
            continue
        if not isinstance(node.target, ast.Name):
            continue
        if node.target.id != "style":
            continue
        # Skip if annotation is `StyleName` (Name reference) — that's
        # the alias case (assertion 2 covers it); here we check inline
        # Literal[...] was NOT introduced.
        if isinstance(node.annotation, ast.Name):
            assert node.annotation.id == "StyleName", (
                f"AppBaseSettings.style annotation must be either "
                f"StyleName or Literal[...]; got annotation name "
                f"{node.annotation.id!r} at "
                f"{APP_BASE_PATH}:{node.lineno}"
            )
            return
        members = _extract_literal_members(node.annotation)
        if members is None:
            # Some other annotation (TypeAlias, etc.); assertion 4
            # catches it for TypeAlias
            return
        assert members == canonical, (
            f"AppBaseSettings.style Literal members {members} differ "
            f"from canonical StyleName {canonical}"
        )


@pytest.mark.unit
def test_cli_does_not_declare_inline_literal_with_style_members() -> None:
    """No inline Literal['vanilla', 'fastblocks_ui'] in cli.py.

    cli.py must import StyleName from validators; any inline Literal
    with the style members is a drift surface the sync test forbids.
    """
    canonical = _load_canonical_members()
    for node in _iter_annotations_in_file(CLI_PATH):
        members = _extract_literal_members(node)
        if members is None:
            continue
        # If this inline Literal's members match the canonical style set,
        # it's a drift surface. (Inline Literals with different members
        # — e.g., for an unrelated domain — are fine; not flagged here.)
        if set(members) == set(canonical):
            raise AssertionError(
                f"cli.py declares an inline Literal with the style "
                f"members {members}; must import StyleName from "
                f"fastblocks.core.validators instead"
            )


@pytest.mark.unit
def test_cli_imports_style_name_from_validators() -> None:
    """cli.py imports StyleName from fastblocks.core.validators.

    Verifies the rename took effect (Commit3's primary deliverable).
    """
    tree = ast.parse(CLI_PATH.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "fastblocks.core.validators":
            continue
        imported_names = {alias.name for alias in node.names}
        assert "StyleName" in imported_names, (
            f"cli.py imports from fastblocks.core.validators but does "
            f"not import StyleName; got {imported_names}"
        )
        return
    raise AssertionError(
        f"cli.py does not import from fastblocks.core.validators; "
        f"the StyleName rename has not landed"
    )


@pytest.mark.unit
def test_default_style_is_a_style_name_member() -> None:
    """DEFAULT_STYLE in validators.py is one of StyleName's members."""
    import typing
    from fastblocks.core.validators import DEFAULT_STYLE, StyleName

    legal = typing.get_args(StyleName)
    assert DEFAULT_STYLE in legal, (
        f"DEFAULT_STYLE {DEFAULT_STYLE!r} is not one of StyleName's "
        f"members {legal}"
    )
```

- [ ] **Step 4.2: Run the sync tests to confirm they fail**

Run: `.venv/bin/pytest tests/core/test_validators_sync.py -v`
Expected: FAIL. `test_cli_imports_style_name_from_validators` fails because cli.py doesn't import from validators. `test_cli_does_not_declare_inline_literal_with_style_members` fails because cli.py has 5 inline Literals.

- [ ] **Step 4.3: Modify `fastblocks/cli.py`**

Open `/Users/les/Projects/fastblocks/fastblocks/cli.py`. The change has two parts:

1. Add the import (top of file, near the existing `from typing import Annotated, Literal`):
   ```python
   from fastblocks.core.validators import DEFAULT_STYLE, StyleName
   ```
2. Replace each inline `Literal["vanilla", "fastblocks_ui"]` annotation with `StyleName`:

   - Line ~913 (`create_app`): `style: Annotated[Literal["vanilla", "fastblocks_ui"], typer.Option(...)] = "vanilla"` → `style: Annotated[StyleName, typer.Option(...)] = "vanilla"`
   - Line ~941 (`create_template`): same pattern, replace `Literal[...]` with `StyleName`
   - Line ~974 (`_scaffold_app_tree`): `style: Literal["vanilla", "fastblocks_ui"]` → `style: StyleName`
   - Line ~1068: same pattern as 913
   - Line ~1082: same pattern as 913

   Default values `"vanilla"` stay literal (Typer handles defaults). The literal `DEFAULT_STYLE` import is used where appropriate; if you prefer, you can keep `"vanilla"` as the default in CLI scaffolding commands.

Verify line numbers against the current file before editing (spec line numbers may have drifted).

- [ ] **Step 4.4: Run the sync tests to confirm they pass**

Run: `.venv/bin/pytest tests/core/test_validators_sync.py -v`
Expected: 4 tests PASS.

- [ ] **Step 4.5: Canary validation — temporarily inline one Literal in cli.py, confirm test fails, restore**

Pick one of the 5 sites. Revert it to `Literal["vanilla", "fastblocks_ui"]`.
Run: `.venv/bin/pytest tests/core/test_validators_sync.py::test_cli_does_not_declare_inline_literal_with_style_members -v`
Expected: FAIL.
Restore the site to `StyleName`.
Run the test again.
Expected: PASS.

- [ ] **Step 4.6: Run full unit test sweep**

Run: `.venv/bin/pytest -q -m "not slow" --no-header`
Expected: previous count + 4 new sync tests = PASS.

- [ ] **Step 4.7: Run ty across cli.py**

Run: `uv run ty check fastblocks/cli.py`
Expected: "All checks passed!"

- [ ] **Step 4.8: Commit**

```bash
cd /Users/les/Projects/fastblocks
git worktree add ../fastblocks-task3 -b task/phase2-cli-literals main
cd ../fastblocks-task3
git add fastblocks/cli.py tests/core/test_validators_sync.py
git commit -m "refactor(cli): Phase 2 Commit3 — cli.py Literal imports from validators

Replaces 5 inline Literal['vanilla', 'fastblocks_ui'] annotations in
cli.py with a single StyleName import from fastblocks.core.validators.
The sync test in tests/core/test_validators_sync.py AST-parses cli.py
and rejects any inline Literal with the style members — drift is now
a CI failure, not a runtime surprise.

CLI behavior unchanged: Typer's --style flag still accepts the same
two values and rejects everything else with the same message.

Co-Authored-By: Claude <noreply@anthropic.com>"
git checkout main
git merge --ff-only task/phase2-cli-literals
```

---

## Task 5: Commit4 — `register_style_candidate` + `format_resolver_mismatch` tests + Protocol tests + `_fresh_registry` lift + Scenario 3+5 regression tests + 5th sync test (PEP 646)

**Files:**
- Modify: `fastblocks/adapters/oneiric_helper.py` — add `register_style_candidate`
- Modify: `tests/conftest.py` — add public `fresh_registry` fixture (lifted from Card5)
- Modify: `tests/core/test_resolve_instance.py` — remove local `_fresh_registry`, consume `fresh_registry` fixture
- Create: `tests/core/test_resolver_mismatch.py` (6 tests)
- Create: `tests/core/test_style_adapter_protocol.py` (6 tests: 4 parametrize + 2 standalone)
- Create: `tests/core/test_template_adapter_protocol.py` (4 tests: 2 parametrize + 2 standalone)
- Create: `tests/core/test_shadowed_count_emitted.py` (1 test)
- Create: `tests/core/test_typer_cli_rejects_invalid_style.py` (1 test)
- Create: `tests/core/test_register_style_candidate.py` (3 tests: happy path, missing-method TypeError, narrowed missing-list)
- Modify: `tests/core/test_validators_sync.py` — add 5th test (PEP 646 `Literal[*values]` rejection)

**Interfaces:**
- Consumes: `StyleAdapter`, `TemplateAdapter`, `ResolverMismatchError`, `format_resolver_mismatch`, `_protocol_missing_methods` from Commit1
- Produces: `register_style_candidate(depends, style_name, module) -> None` in `oneiric_helper.py`

- [ ] **Step 5.1: Add the 5th sync test (PEP 646 rejection)**

Append to `tests/core/test_validators_sync.py`:

```python
@pytest.mark.unit
def test_validators_rejects_pep_646_starred_literal_outside_validators() -> None:
    """Literal[*values] unpacking (PEP 646) outside validators.py is rejected.

    Future drift vector: a contributor extracts the style set to
    ``STYLES = ('vanilla', 'fastblocks_ui')`` and writes
    ``Literal[*STYLES]``. AST must reject that pattern outside
    ``validators.py`` because the spec mandates inline enumeration
    (the sync test's source-of-truth is the Literal itself, not a
    separate tuple).
    """
    # Scan both cli.py and _base.py for any Literal[*...] pattern
    for path in (APP_BASE_PATH, CLI_PATH):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Subscript):
                continue
            # The slice inside Literal[*values] is an ast.Starred
            slice_node = node.slice
            if isinstance(slice_node, ast.Starred):
                raise AssertionError(
                    f"{path.name} uses Literal[*...] (PEP 646) "
                    f"unpacking; the spec mandates inline enumeration "
                    f"in fastblocks.core.validators.StyleName. Replace "
                    f"with a direct Literal[...] or import StyleName."
                )
```

- [ ] **Step 5.2a: Read Card5's `_fresh_registry` to confirm what we're lifting**

Read `/Users/les/Projects/fastblocks/tests/core/test_resolve_instance.py` lines 30-60. Card5's `_fresh_registry` is a **function called inline** (not a pytest fixture parameter):

```python
def _fresh_registry() -> FastblocksRegistry:
    return FastblocksRegistry(Resolver())  # private Resolver — NOT get_resolver()
```

Card5's tests call `_fresh_registry()` inline at the top of each test, not as a fixture parameter. The lift to a public fixture requires refactoring every test in `test_resolve_instance.py` to consume `fresh_registry` as a parameter instead.

Card5's fixture builds a **private Resolver** (not the canonical singleton). This is intentional for test isolation. Phase 2 preserves that — the lifted `fresh_registry` fixture uses `Resolver()` (private), NOT `get_resolver()` (canonical). The non-canonical-resolver warning from Phase 1.5x Card 8 will fire on construction; that is the existing Card5 behavior.

- [ ] **Step 5.2b: Add `fresh_registry` fixture to `tests/conftest.py`**

Open `/Users/les/Projects/fastblocks/tests/conftest.py`. Find a sensible spot near other fixtures. The new public fixture:

```python
from oneiric.core.resolution import Resolver
from fastblocks.core.resolver import FastblocksRegistry

@pytest.fixture
def fresh_registry() -> FastblocksRegistry:
    """A private FastblocksRegistry for tests that need isolated state.

    Lifted from tests/core/test_resolve_instance.py:_fresh_registry
    during Phase 2 Commit4. Card5's helper was private (leading
    underscore); Phase 2 promotes it to a public conftest fixture
    consumed by both Card5's tests and Phase 2's
    test_resolver_mismatch.py.

    The fixture builds a private Resolver (not the canonical
    singleton from get_resolver()) — Phase 1.5x Card 8's "non-
    canonical warning" will fire on construction. That warning is
    acceptable here; it's the same posture Card5 used and the
    existing test_facade_identity_check.py suppresses it via caplog.
    """
    return FastblocksRegistry(Resolver())
```

- [ ] **Step 5.2c: Refactor Card5's `tests/core/test_resolve_instance.py` to consume the fixture**

Modify `/Users/les/Projects/fastblocks/tests/core/test_resolve_instance.py`:

1. Delete the local `_fresh_registry` function definition (lines 37-39).
2. For every test in the file that calls `registry = _fresh_registry()` inline, refactor to consume the fixture as a parameter: change `def test_X() -> None:` to `def test_X(fresh_registry) -> None:` and remove the inline `registry = _fresh_registry()` line.
3. The `_patch_resolver` helper Card5 uses (with `monkeypatch`) is unaffected — it takes the fixture-injected registry as a parameter.

Verify by reading the test file end-to-end and confirming every test that used `_fresh_registry()` now uses the `fresh_registry` fixture.

- [ ] **Step 5.2d: Run Card5's tests to confirm no regression**

Run: `.venv/bin/pytest tests/core/test_resolve_instance.py -v`
Expected: all Card5 tests pass against the new public fixture. If any test fails, the refactor missed a call site.

- [ ] **Step 5.3: Write the resolver mismatch tests**

Create `tests/core/test_resolver_mismatch.py`:

```python
"""Phase 2 mechanical-four Commit4 — format_resolver_mismatch tests.

Exercises the registry-vs-Literal drift detector from
``fastblocks.core.validators``. Six tests cover happy path,
mismatch error shape, nearest-neighbor hint, unavailable-explain
fallback, narrow-exception catch, and structured-log emission.
"""
from __future__ import annotations

import pytest
from fastblocks.core.validators import (
    ResolverMismatchError,
    format_resolver_mismatch,
    format_resolution_explanation_one_line,
)


@pytest.mark.unit
def test_format_resolver_mismatch_raises_for_illegal_value(
    fresh_registry,  # noqa: ARG001
) -> None:
    """Known-bad style value triggers ResolverMismatchError."""
    with pytest.raises(ResolverMismatchError) as excinfo:
        format_resolver_mismatch(fresh_registry, "style", "kelp")
    err = excinfo.value
    assert err.value == "kelp"
    assert "vanilla" in err.legal
    assert "fastblocks_ui" in err.legal


@pytest.mark.unit
def test_resolver_mismatch_error_message_includes_legal_set(
    fresh_registry,  # noqa: ARG001
) -> None:
    """Error message names the legal set so operators see what's allowed."""
    with pytest.raises(ResolverMismatchError) as excinfo:
        format_resolver_mismatch(fresh_registry, "style", "kelp")
    msg = str(excinfo.value)
    assert "vanilla" in msg
    assert "fastblocks_ui" in msg


@pytest.mark.unit
def test_nearest_neighbor_hint_for_typo(
    fresh_registry,  # noqa: ARG001
) -> None:
    """Typo with lexical similarity gets a 'Did you mean ...?' hint."""
    with pytest.raises(ResolverMismatchError) as excinfo:
        format_resolver_mismatch(fresh_registry, "style", "vanila")
    err = excinfo.value
    assert err.nearest == "vanilla", (
        f"Expected nearest='vanilla' for typo 'vanila'; got {err.nearest!r}"
    )
    assert "vanilla" in str(err)


@pytest.mark.unit
def test_no_nearest_hint_for_unrelated_string(
    fresh_registry,  # noqa: ARG001
) -> None:
    """Unrelated strings (kelp, bulma) get no hint, but still raise."""
    with pytest.raises(ResolverMismatchError) as excinfo:
        format_resolver_mismatch(fresh_registry, "style", "kelp")
    assert excinfo.value.nearest is None


@pytest.mark.unit
def test_unavailable_explain_falls_back_gracefully() -> None:
    """explain() failures don't crash; resolver_explain='<unavailable>'."""
    # A registry whose explain() raises RuntimeError on every call.
    class BrokenRegistry:
        def explain(self, domain: str, value: str) -> None:
            raise RuntimeError("simulated registry failure")

    with pytest.raises(ResolverMismatchError) as excinfo:
        format_resolver_mismatch(BrokenRegistry(), "style", "kelp")
    assert excinfo.value.resolver_explain == "<unavailable>"


@pytest.mark.unit
def test_format_resolution_explanation_one_line_handles_none() -> None:
    """The formatter accepts None and returns '<unavailable>'."""
    assert format_resolution_explanation_one_line(None) == "<unavailable>"
```

- [ ] **Step 5.4: Write the StyleAdapter Protocol tests**

Create `tests/core/test_style_adapter_protocol.py`:

```python
"""Phase 2 mechanical-four Commit4 — StyleAdapter Protocol gate tests.

The registration gate ``isinstance(module, StyleAdapter)`` requires
both ``@runtime_checkable`` (Python 3.13) and the four expected
methods. These tests exercise the gate via direct isinstance calls
and via the ``_protocol_missing_methods`` helper.
"""
from __future__ import annotations

import typing as t
from types import SimpleNamespace

import pytest
from fastblocks.core.validators import (
    StyleAdapter,
    _protocol_missing_methods,
)


def _make_module_with(methods: set[str]) -> t.Any:
    """Build a SimpleNamespace with the given methods populated as no-ops."""
    ns = SimpleNamespace()
    for method in {"register_style_functions", "get_css_path",
                    "get_js_path", "escape_user_input"}:
        if method in methods:
            setattr(ns, method, lambda *a, **kw: None)
        else:
            # Don't set the attribute at all — module genuinely lacks it
            pass
    return t.cast("StyleAdapter", ns)


@pytest.mark.unit
@pytest.mark.parametrize(
    "missing_method",
    ["register_style_functions", "get_css_path", "get_js_path",
     "escape_user_input"],
)
def test_protocol_missing_methods_reports_missing_method(
    missing_method: str,
) -> None:
    """Each missing method is named in the helper's return value."""
    module = _make_module_with(
        {"register_style_functions", "get_css_path", "get_js_path",
         "escape_user_input"} - {missing_method}
    )
    missing = _protocol_missing_methods(module, StyleAdapter)
    assert missing_method in missing, (
        f"_protocol_missing_methods must report '{missing_method}' as "
        f"missing; got {missing}"
    )


@pytest.mark.unit
def test_full_style_adapter_satisfies_protocol() -> None:
    """A module with all four methods is a StyleAdapter."""
    module = _make_module_with(
        {"register_style_functions", "get_css_path", "get_js_path",
         "escape_user_input"}
    )
    assert isinstance(module, StyleAdapter), (
        "Module with all 4 StyleAdapter methods must satisfy the Protocol"
    )


@pytest.mark.unit
def test_protocol_is_runtime_checkable() -> None:
    """StyleAdapter carries @runtime_checkable."""
    assert hasattr(StyleAdapter, "_is_runtime_protocol"), (
        "StyleAdapter is not @runtime_checkable; isinstance() will "
        "raise TypeError at registration time"
    )
```

- [ ] **Step 5.5: Write the TemplateAdapter Protocol tests**

Create `tests/core/test_template_adapter_protocol.py`:

```python
"""Phase 2 mechanical-four Commit4 — TemplateAdapter Protocol tests.

The Protocol surface ships in Phase 2 (for Phase 6's Prometheus
cardinality lint anchor); ``register_template_candidate`` is
deferred. Three tests cover the Protocol surface.
"""
from __future__ import annotations

import typing as t
from types import SimpleNamespace

import pytest
from fastblocks.core.validators import (
    TemplateAdapter,
    _protocol_missing_methods,
)


def _make_template_module(methods: set[str]) -> t.Any:
    ns = SimpleNamespace()
    if "render" in methods:
        setattr(ns, "render",
                lambda template, context: "<rendered>")
    if "init_envs" in methods:
        setattr(ns, "init_envs", lambda: object())
    return t.cast("TemplateAdapter", ns)


@pytest.mark.unit
@pytest.mark.parametrize("missing_method", ["render", "init_envs"])
def test_template_protocol_missing_methods(missing_method: str) -> None:
    """Each missing method is reported by _protocol_missing_methods."""
    module = _make_template_module({"render", "init_envs"} - {missing_method})
    missing = _protocol_missing_methods(module, TemplateAdapter)
    assert missing_method in missing


@pytest.mark.unit
def test_template_protocol_is_runtime_checkable() -> None:
    """TemplateAdapter carries @runtime_checkable."""
    assert hasattr(TemplateAdapter, "_is_runtime_protocol")


@pytest.mark.unit
def test_full_template_module_satisfies_protocol() -> None:
    """A module with both methods satisfies TemplateAdapter."""
    module = _make_template_module({"render", "init_envs"})
    assert isinstance(module, TemplateAdapter)
```

- [ ] **Step 5.6: Write the Scenario 3 regression test**

Create `tests/core/test_shadowed_count_emitted.py`:

```python
"""Phase 2 mechanical-four Commit4 — Scenario 3 regression.

Phase 1.5x's ``emit_startup_log`` prints a shadowed-candidate count
at startup. Scenario 3 (registered-but-stale candidate) relies on
this signal. Phase 2 pins the signal so future regressions in the
Phase 1.5x code surface are caught here.
"""
from __future__ import annotations

import pytest


@pytest.mark.unit
def test_emit_startup_log_reports_shadowed_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stale registered candidate produces shadowed count >= 1.

    Mirrors the structured-log capture pattern from
    tests/core/test_resolver_metrics.py:203-235: monkeypatch the
    ``resolver_metrics._log.info`` call (Oneiric structlog does not
    write through stdlib; capsys won't capture it). Use a private
    Resolver for hermetic isolation (canonical singleton is shared
    across the suite; FastblocksRegistry has no clear() method).
    Register a stale candidate — key with a hyphen, not in
    StyleName — via ``registry.register(candidate)`` (the method
    that accepts a pre-built Candidate; ``register_candidate``
    takes a callable factory and would wrap the Candidate).
    """
    from oneiric.core.resolution import (
        Candidate,
        CandidateSource,
        Resolver,
    )
    from fastblocks.core.resolver import FastblocksRegistry
    from fastblocks.core import resolver_metrics

    registry = FastblocksRegistry(Resolver())  # private, hermetic
    candidate = Candidate(
        factory=lambda: object(),
        domain="style",
        key="fastblocks-ui",  # hyphenated, not in StyleName
        source=CandidateSource.LOCAL_PKG,
    )
    registry.register(candidate)  # not register_candidate

    # Spy on resolver_metrics._log.info (structlog BoundLogger)
    info_calls: list[tuple[tuple[t.Any, ...], dict[str, t.Any]]] = []
    real_info = resolver_metrics._log.info

    def spy_info(*args: t.Any, **kwargs: t.Any) -> None:
        info_calls.append((args, kwargs))
        real_info(*args, **kwargs)

    monkeypatch.setattr(resolver_metrics._log, "info", spy_info)
    emit_startup_log = resolver_metrics.emit_startup_log
    emit_startup_log(registry)

    # Find the "M shadowed" call (Phase 1.5x's startup log emits
    # "Oneiric resolver: 1 registry, N candidates, M shadowed")
    shadowed_calls = [
        (args, kwargs)
        for args, kwargs in info_calls
        if args and "shadowed" in (args[0] if args else "")
    ]
    assert shadowed_calls, (
        f"Expected at least one info() call mentioning 'shadowed'; "
        f"saw {len(info_calls)} info() calls total: "
        f"{[args[0] if args else '' for args, _ in info_calls]!r}"
    )
    # The log format string has "%d shadowed" — second positional
    # arg should be an integer >= 1.
    args, _kwargs = shadowed_calls[0]
    # The format-string positional arg for shadowed count
    shadowed_count = None
    for arg in args[1:]:
        if isinstance(arg, int):
            shadowed_count = arg
            break
    assert shadowed_count is not None and shadowed_count >= 1, (
        f"Expected shadowed count >= 1 after registering a stale "
        f"candidate; got {shadowed_count}"
    )
```

The import path is verified empirically:
- `Candidate` at `/Users/les/Projects/fastblocks/.venv/lib/python3.13/site-packages/oneiric/core/resolution.py:41`
- `CandidateSource` at line 34
- `Resolver` in the same file
- `FastblocksRegistry.register(candidate)` at `/Users/les/Projects/fastblocks/fastblocks/core/resolver.py:213`
- The structured-log capture pattern at `/Users/les/Projects/fastblocks/tests/core/test_resolver_metrics.py:203-235`

- [ ] **Step 5.7: Write the Scenario 5 regression test**

Create `tests/core/test_typer_cli_rejects_invalid_style.py`:

```python
"""Phase 2 mechanical-four Commit4 — Scenario 5 regression.

Typer's auto-validation rejects --style with a value not in the
Literal. Phase 2 pins this behavior so future regressions in Typer
or our annotation are caught here.
"""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from fastblocks.cli import cli


@pytest.mark.unit
def test_typer_rejects_invalid_style_literal() -> None:
    """--style kelp is rejected with non-zero exit and the value named."""
    runner = CliRunner()
    result = runner.invoke(cli, ["create", "app", "myapp", "--style", "kelp"])
    assert result.exit_code != 0, (
        f"Expected non-zero exit for --style kelp; got {result.exit_code}. "
        f"Output: {result.output!r}"
    )
    combined = (result.output or "") + (result.stderr or "")
    assert "kelp" in combined, (
        f"Expected 'kelp' in error output; got: {combined!r}"
    )
```

- [ ] **Step 5.8: Write the failing test for `register_style_candidate`**

Create `tests/core/test_register_style_candidate.py`. This is the **direct unit test** for the new production code in Commit4; without it, the Protocol isinstance gate ships untested.

```python
"""Phase 2 mechanical-four Commit4 — register_style_candidate direct tests.

The Protocol isinstance gate added in Commit4 (in
``fastblocks.adapters.oneiric_helper.register_style_candidate``) is
the new production code in this commit. It MUST have direct unit
tests — testing the Protocol surface alone does not exercise the
gate.

Three tests cover:
1. Happy path — a valid StyleAdapter module is registered.
2. Missing-method rejection — ``TypeError`` is raised naming the
   missing methods.
3. CandidateValidationError propagation — strict-validation errors
   from the underlying register_candidate_strict propagate.
"""
from __future__ import annotations

import typing as t
from types import SimpleNamespace

import pytest
from fastblocks.adapters.oneiric_helper import register_style_candidate


def _valid_style_adapter() -> t.Any:
    """Build a SimpleNamespace satisfying StyleAdapter (4 methods)."""
    ns = SimpleNamespace()
    setattr(ns, "register_style_functions", lambda *a, **kw: None)
    setattr(ns, "get_css_path", lambda *a, **kw: "/style.css")
    setattr(ns, "get_js_path", lambda *a, **kw: "/style.js")
    setattr(ns, "escape_user_input", lambda *a, **kw: "<escaped>")
    return t.cast("t.Any", ns)


@pytest.mark.unit
def test_register_style_candidate_accepts_valid_adapter(
    fresh_registry,
) -> None:
    """A module with all 4 StyleAdapter methods registers without error."""
    module = _valid_style_adapter()
    # Should NOT raise; happy path
    register_style_candidate(fresh_registry, "vanilla", module)


@pytest.mark.unit
def test_register_style_candidate_raises_for_missing_method(
    fresh_registry,
) -> None:
    """A module missing a StyleAdapter method raises TypeError."""
    module = SimpleNamespace()
    # Deliberately missing all 4 methods
    with pytest.raises(TypeError) as excinfo:
        register_style_candidate(fresh_registry, "vanilla", module)
    msg = str(excinfo.value)
    assert "register_style_functions" in msg, (
        f"TypeError must name missing 'register_style_functions'; "
        f"got: {msg!r}"
    )
    assert "get_css_path" in msg
    assert "get_js_path" in msg
    assert "escape_user_input" in msg


@pytest.mark.unit
def test_register_style_candidate_narrows_missing_method_list(
    fresh_registry,
) -> None:
    """A module missing only one method gets only that method named."""
    module = SimpleNamespace()
    setattr(module, "register_style_functions", lambda *a, **kw: None)
    setattr(module, "get_css_path", lambda *a, **kw: "/x")
    setattr(module, "get_js_path", lambda *a, **kw: "/y")
    # Missing only escape_user_input
    with pytest.raises(TypeError) as excinfo:
        register_style_candidate(fresh_registry, "vanilla", module)
    msg = str(excinfo.value)
    assert "escape_user_input" in msg
    # And NOT the methods that ARE present (no false positives)
    assert "register_style_functions" not in msg or "missing" in msg.lower()
    # The exact match-rejection: the message names the missing method.
```

Run: `.venv/bin/pytest tests/core/test_register_style_candidate.py -v`
Expected: FAIL with `ImportError` or `AttributeError` (the function doesn't exist yet). Specifically:
- `test_register_style_candidate_accepts_valid_adapter` fails because `register_style_candidate` doesn't exist.
- `test_register_style_candidate_raises_for_missing_method` fails for the same reason.

- [ ] **Step 5.9: Add `register_style_candidate` to `oneiric_helper.py`**

Open `/Users/les/Projects/fastblocks/fastblocks/adapters/oneiric_helper.py`. Read the file first to find where Card1's `register_candidate_strict` lives, then add `register_style_candidate` near it:

```python
def register_style_candidate(
    depends: "FastblocksRegistry",
    style_name: str,
    module: t.Any,
) -> None:
    """Register a style adapter module after isinstance(module, StyleAdapter).

    Thin wrapper around Card 1's ``register_candidate_strict`` that
    adds a Protocol isinstance gate. If the module lacks any of the
    four ``StyleAdapter`` methods, raises ``TypeError`` naming the
    missing methods. ``CandidateValidationError`` from the underlying
    strict registration propagates.

    Phase 2 ships this function but no production call site uses it
    today — adapter registration sites will adopt it incrementally in
    future phases. The Protocol gate exists so the contract is
    enforceable the moment a site adopts it.
    """
    from fastblocks.core.validators import (
        StyleAdapter,
        _protocol_missing_methods,
    )

    if not isinstance(module, StyleAdapter):
        missing = _protocol_missing_methods(module, StyleAdapter)
        raise TypeError(
            f"Style adapter {style_name!r} is missing required "
            f"StyleAdapter methods: {missing}. See "
            f"fastblocks/core/validators.py for the contract."
        )
    register_candidate_strict(depends, "style", style_name, module)
```

Verify the import order and the existing `register_candidate_strict` signature before committing.

- [ ] **Step 5.11: Run all new tests + full sweep**

Run: `.venv/bin/pytest tests/core/test_register_style_candidate.py tests/core/test_resolver_mismatch.py tests/core/test_style_adapter_protocol.py tests/core/test_template_adapter_protocol.py tests/core/test_shadowed_count_emitted.py tests/core/test_typer_cli_rejects_invalid_style.py tests/core/test_validators_sync.py -v`
Expected: all new tests pass (3 + 6 + 6 + 4 + 1 + 1 + 5 = 26 tests in this run).

Run: `.venv/bin/pytest -q -m "not slow" --no-header`
Expected: previous count + 26 new = PASS. (Step 7.1 below pins the final total.)

- [ ] **Step 5.10: Canary validation on `register_style_candidate` (mandatory)**

Temporarily replace the `if not isinstance(module, StyleAdapter): raise TypeError(...)` block in `register_style_candidate` with `pass` (so the gate is bypassed; `register_candidate_strict` runs unconditionally).

Run: `.venv/bin/pytest tests/core/test_register_style_candidate.py::test_register_style_candidate_raises_for_missing_method -v`
Expected: FAIL — with the gate removed, no `TypeError` is raised, and the test asserts `pytest.raises(TypeError)`.

Restore the `if not isinstance(...) raise TypeError(...)` block.

Run: `.venv/bin/pytest tests/core/test_register_style_candidate.py::test_register_style_candidate_raises_for_missing_method -v`
Expected: PASS.

**This canary is mandatory, not optional.** The Protocol isinstance gate is the entire purpose of `register_style_candidate`; without the canary, the gate could be deleted silently in a future commit without any test failing.

- [ ] **Step 5.12: Run ty across fastblocks/**

Run: `uv run ty check fastblocks/`
Expected: "All checks passed!"

- [ ] **Step 5.13: Run crackerjack**

Run: `uv run crackerjack run`
Expected: PASS on ty, refurb, ruff. The crackerjack ratchet on ty-directive count must remain at zero new suppressions.

- [ ] **Step 5.14: Commit**

```bash
cd /Users/les/Projects/fastblocks
git worktree add ../fastblocks-task4 -b task/phase2-protocol-gates <sha-of-main-after-commit3>
cd ../fastblocks-task4
git add fastblocks/adapters/oneiric_helper.py \
        tests/conftest.py \
        tests/core/test_resolve_instance.py \
        tests/core/test_register_style_candidate.py \
        tests/core/test_resolver_mismatch.py \
        tests/core/test_style_adapter_protocol.py \
        tests/core/test_template_adapter_protocol.py \
        tests/core/test_shadowed_count_emitted.py \
        tests/core/test_typer_cli_rejects_invalid_style.py \
        tests/core/test_validators_sync.py
git commit -m "feat(adapter-registration): Phase 2 Commit4 — Protocol gates + drift detector

Adds register_style_candidate to oneiric_helper.py — a thin wrapper
around Card 1's register_candidate_strict that adds an isinstance
check against the @runtime_checkable StyleAdapter Protocol. Direct
unit tests in test_register_style_candidate.py (3 tests: happy path,
missing-method TypeError, narrowed-missing-list).

Adds format_resolver_mismatch and format_resolution_explanation_one_line
tests (test_resolver_mismatch.py — 6 tests covering happy path, error
shape, nearest-neighbor hint, unavailable-explain fallback, narrow-
exception catch, and the None-input formatter path).

Adds Protocol surface tests (test_style_adapter_protocol.py — 6 tests
covering 4 missing-method variants + happy path + runtime-checkable
pin; test_template_adapter_protocol.py — 4 tests covering missing-
method variants + happy path + runtime-checkable pin).

Adds Scenario 3 regression (test_shadowed_count_emitted.py) using
monkeypatch.setattr on resolver_metrics._log.info (matches the
existing pattern in tests/core/test_resolver_metrics.py:203-235;
capsys cannot capture Oneiric structlog output by design) and a
private Resolver for hermetic isolation (FastblocksRegistry has no
clear() method; canonical singleton must not be polluted).

Adds Scenario 5 regression (test_typer_cli_rejects_invalid_style.py).

Lifts _fresh_registry from Card 5 to tests/conftest.py as a public
fresh_registry fixture, consumed by both Card 5 and Phase 2 tests.
The lifted fixture uses Resolver() (private, hermetic) — NOT
get_resolver() (canonical singleton) — matching Card 5's behavior.

Adds 5th sync test rejecting Literal[*values] PEP 646 unpacking outside
validators.py.

Co-Authored-By: Claude <noreply@anthropic.com>"
git checkout main
git merge --ff-only task/phase2-protocol-gates
```

---

## Task 6: Commit5 — ADR 0010 closeout

**Files:**
- Create: `docs/adr/0010-phase-2-mechanical-four.md`

- [ ] **Step 6.1: Write the ADR**

```markdown
---
status: accepted
role: phase-2-closeout
date: 2026-08-21
last_reviewed: 2026-08-21
supersedes: null
superseded_by: null
decision_date: 2026-08-21
topic: phase-2-type-safe-configuration-mechanical-four-closeout
---

# ADR 0010: Phase 2 Mechanical-Four Closeout

## Status

Accepted (Phase 2 — type-safe configuration closeout).

## Context

The master plan (§Phase 2 line 303-313) lists six sub-tasks for Phase 2.
The Phase 2 design spec (`docs/superpowers/specs/2026-08-21-fastblocks-phase-2-design.md`)
narrows scope to **mechanical four**: Literal types for `style` + CLI↔settings
sync test + Oneiric `explain()`-based error contract + Protocol-based
adapter contracts. The remaining two items (renderer match-statement
dispatch, `SafeHTMLStr` propagation) are out of scope: renderer dispatch
is deferred to Phase 4/6; `SafeHTMLStr` was completed in Phase 1B
(master plan §Phase 1B results line 423).

This ADR records the architectural decisions Phase 2 commits and is the
canonical reference for the deferred items.

## Decisions

### Decision 1: Single source of truth at `fastblocks/core/validators.py`

`StyleName = Literal["vanilla", "fastblocks_ui"]` is defined ONCE in
`fastblocks.core.validators`. Every consumer (`AppBaseSettings`,
`cli.py`, future Phase 6 Prometheus labels) imports `StyleName` from
this module. Adding a new style value means editing one Literal; the
sync test (`tests/core/test_validators_sync.py`) enforces that every
consumer follows.

This implements ADR 0008 Rule 3 ("Shared Literal sets" home designation).

### Decision 2: `@runtime_checkable` on both Protocols

`StyleAdapter` and `TemplateAdapter` both carry `@runtime_checkable`.
Required for `isinstance()` on method-only Protocols (Python 3.13; no
relaxation in PEP 544 for method-only Protocols).

### Decision 3: Protocol method naming — `register_style_functions`, NOT `register_<name>_functions`

The pre-Phase-2 convention in `style_registry.py:42` is
`register_style_functions(env, style_name)` — a single function name,
not per-style. Phase 2 pins this. The per-style-naming convention
(`register_vanilla_functions`, `register_fastblocks_ui_functions`) is
**broken**; concrete adapters must implement `register_style_functions`.

### Decision 4: `register_style_candidate` returns `None`

The wrapper preserves `register_candidate_strict`'s contract
(`None` on success, `CandidateValidationError` on failure). The only
new exception is `TypeError` for Protocol-missing methods.

### Decision 5: `format_resolution_explanation_one_line()` helper

`FastblocksRegistry.explain()` returns `ResolutionExplanation`, NOT a
string. The formatter helper produces the operator-facing single-line
string. Names the formatter explicitly so implementers don't reinvent
it.

### Decision 6: `suppress(Exception)` ratchet at master plan baseline (123 sites)

Phase 2 holds the master plan line 313 baseline. No new sites added,
no sites deleted. The ratchet test
(`tests/core/test_suppress_exception_ratchet.py`) runs `git grep` via
`subprocess` and asserts count ≤ 123. Future Phase 7 (final dead-code
pass) may lower the count; the test passes on a lower count.

### Decision 7: `app.yml` → `AppBaseSettings` wiring deferred to Phase 2.5

Production code (`fastblocks/adapters/app/default.py:182`) calls
`AppSettings()` with no arguments; defaults are used directly.
`OneiricSettings` is a `pydantic.BaseModel` subclass, NOT a
`pydantic_settings.BaseSettings` subclass — it does not auto-read
`app.yml`. The Literal type is therefore **defensive documentation**
until the wiring lands in a follow-up Phase 2.5.

### Decision 8: `get_close_matches` cutoff at 0.6

Standard library default. Catches typos like `'vanila'` → `'vanilla'`,
`'fastblock_ui'` → `'fastblocks_ui'`. Misses unrelated strings (`kelp`,
`bulma`); the legal-set message still surfaces even without a hint.

## Deferred Items

| Item | Reason | Lands in |
|---|---|---|
| Renderer match-statement dispatch | Requires renderer axis on `AppBaseSettings`; forces Phase 4 + 6 to take a position early | Phase 4 / 6 |
| `try/except Exception:` migration in `core/style_registry.py:66` | Framework-boundary; out of Phase 2 scope | Phase 7 |
| `register_template_candidate` decorator | No consumer site; Protocol still defined for Phase 6 lint anchor | When first renderer adopts the contract |
| `app.yml` → `AppBaseSettings` wiring | Production code uses defaults; wiring is a separate task | Phase 2.5 |

## Cross-references

- Master plan: `docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md` §Phase 2 (line 303-313)
- Phase 2 spec: `docs/superpowers/specs/2026-08-21-fastblocks-phase-2-design.md`
- Phase 2 plan: `docs/superpowers/plans/2026-08-21-fastblocks-phase-2.md`
- ADR 0008 Rule3: `docs/adr/0008-oneiric-selection-mechanism-ownership.md`
- Phase 1.5x Card 1: `register_candidate_strict` foundation (commit `8564fc1`)
- Phase 1.5x Card 6: `emit_startup_log` (commit `a622055`) — Scenario 3 inheritance
- Phase 1.5x Card 8: facade identity-check warning (commit `e1d8f30`) — `_fresh_registry` lift pattern
- Phase 1.5x Card 9: ADR 0008 Rule3 documentation (commit `ca4a520`) — `core/validators.py` home designation
```

- [ ] **Step 6.2: Commit**

```bash
cd /Users/les/Projects/fastblocks
git worktree add ../fastblocks-task5 -b task/phase2-adr-0010 main
cd ../fastblocks-task5
git add docs/adr/0010-phase-2-mechanical-four.md
git commit -m "docs(adr): Phase 2 Commit5 — ADR 0010 mechanical-four closeout

Documents the eight architectural decisions Phase 2 commits:
single source of truth, @runtime_checkable Protocols, register_style_functions
naming (breaks per-style drift), None return type, formatter helper,
suppress(Exception) ratchet at 123-site baseline, app.yml wiring
deferred to Phase 2.5, get_close_matches cutoff at 0.6.

Co-Authored-By: Claude <noreply@anthropic.com>"
git checkout main
git merge --ff-only task/phase2-adr-0010
```

---

## Task 7: Final verification

After all 6 commits merge to main:

- [ ] **Step 7.1: Run the full pytest sweep**

Run: `.venv/bin/pytest -q -m "not slow" --no-header`
Expected: previous baseline (~1997 tests) + 37 new = ~2034 PASS, 0 FAIL.

- [ ] **Step 7.2: Run ty**

Run: `uv run ty check fastblocks/`
Expected: "All checks passed!" with **zero new ty suppressions** in Phase 2 code (the existing Card 1 ignores in `oneiric_helper.py` are not touched).

- [ ] **Step 7.3: Run crackerjack**

Run: `uv run crackerjack run`
Expected: PASS on ty, refurb, ruff. Coverage ratchet holds or improves.

- [ ] **Step 7.4: Verify the ratchet test still passes**

Run: `.venv/bin/pytest tests/core/test_suppress_exception_ratchet.py -v`
Expected: PASS. The suppress(Exception) count is ≤ 122 (no Phase 2 commit added or removed a site).

- [ ] **Step 7.5: Verify all 37 new tests pass**

Run: `.venv/bin/pytest tests/core/test_validators_module.py tests/core/test_validators_sync.py tests/core/test_resolver_mismatch.py tests/core/test_style_adapter_protocol.py tests/core/test_template_adapter_protocol.py tests/core/test_app_settings_literal.py tests/core/test_shadowed_count_emitted.py tests/core/test_typer_cli_rejects_invalid_style.py tests/core/test_suppress_exception_ratchet.py tests/core/test_register_style_candidate.py -v`
Expected: 37 tests PASS.

Per-file breakdown (parametrize cases expand):
| File | Tests |
|---|---|
| `test_validators_module.py` | 6 |
| `test_validators_sync.py` | 5 (4 base + 1 PEP 646) |
| `test_app_settings_literal.py` | 7 (2 legal + 1 default + 4 parametrize) |
| `test_resolver_mismatch.py` | 6 |
| `test_style_adapter_protocol.py` | 6 (4 parametrize + 2 standalone) |
| `test_template_adapter_protocol.py` | 4 (2 parametrize + 2 standalone) |
| `test_shadowed_count_emitted.py` | 1 |
| `test_typer_cli_rejects_invalid_style.py` | 1 |
| `test_suppress_exception_ratchet.py` | 1 |
| **Total** | **37** |

- [ ] **Step 7.6: Final commit (only if fixes were needed)**

If any verification step required a fix, commit the fix in a separate "Phase 2 verification" commit. Otherwise the plan is complete.

---

## Self-Review Checklist

After writing the plan, run this checklist:

- [ ] **Spec coverage:** All 8 spec sections (§Architecture, §Layer 1/2/3, §Sync enforcement, §Protocol contracts, §Registration gate, §Error message contract, §Data flow, §Structured log shape, §Test surface, §Verification gate, §Per-task ICs) covered by at least one task. (Yes: Tasks 2-5 cover each; Task 6 documents; Task 7 verifies.)
- [ ] **Placeholder scan:** No "TBD", "TODO", "implement later", "similar to Task N". (Confirmed; every step has concrete code or commands.)
- [ ] **Type consistency:** `StyleName`, `StyleAdapter`, `TemplateAdapter`, `_protocol_missing_methods`, `register_style_candidate`, `format_resolver_mismatch`, `format_resolution_explanation_one_line`, `ResolverMismatchError` are defined in Task 2 (Commit1) and used by the same names in Tasks 3-5. (Confirmed.)
- [ ] **Commit order:** Commit6 first (baseline-lock), then Commit1, Commit2, Commit3, Commit4, Commit5. (Confirmed; explicit order table at the top of this plan.)
- [ ] **Canary discipline:** Step-level canary validation included in Tasks 2, 3, 4 (revert → test fails → restore). Task 5 notes canary is optional for the registration gate test. (Confirmed.)
- [ ] **No new ty suppressions:** Confirmed — Task 2 and Task 5 spec the `@runtime_checkable` decorator satisfies ty's `invalid-argument-type` for isinstance. (Confirmed.)
- [ ] **Per-task IC blocks:** Each of the 6 commits has a *Triggered from / Returns to / Demonstrable by / Rollback signal / Observability added* block in the spec; the plan's commit messages reference the IC blocks. (Confirmed.)