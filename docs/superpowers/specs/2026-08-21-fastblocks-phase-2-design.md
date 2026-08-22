---
status: accepted
role: phase-2-design-spec
date: 2026-08-21
last_reviewed: 2026-08-21
supersedes: null
superseded_by: null
decision_date: 2026-08-21
topic: phase-2-type-safe-configuration-mechanical-four
---

# Phase 2: Type-safe Configuration — Mechanical-Four Design

## Status

**Accepted** (Phase 2 spec — companion to the master plan
`docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md`).

## Scope decision

Phase 2 of the master plan (§Phase 2 line 303-313) lists six sub-tasks. The
scope decision for THIS spec is **mechanical four**:

1. `Literal[...]` types for the `style` domain (CLI + settings)
2. CLI↔settings Literal sync test
3. Oneiric-`explain()`-based error contract for registered-but-not-in-Literal drift
4. `Protocol`-based adapter contracts (`StyleAdapter`) with `isinstance` enforcement.
   `TemplateAdapter` is **defined** for Phase 6's Prometheus cardinality lint
   (Phase 6's label-set `Literal[...]` rule needs a stable type to lint
   against), but its `register_template_candidate` decorator is **deferred**
   — no template-renderer registration call site exists today, and adding
   the decorator without a consumer would be a scope leak. Phase 2 ships
   the `TemplateAdapter` Protocol + tests, not the registration decorator.

**Out of scope** (deferred to Phase 4 / Phase 6 / Phase 7 / Phase 2.5):

- Renderer match-statement dispatch (master plan line 311)
- `fastblocks/core/style_registry.py:66` `try/except Exception:` to `with suppress(Exception)` migration (master plan line 313 misattributes this — the file uses `try/except`, not `with suppress`; the surviving `with suppress(Exception)` site in `fastblocks/__init__.py:10` is the framework-boundary placeholder Phase 1A left)
- Prometheus metrics for the new error paths (deferred to Phase 6)
- `register_template_candidate` decorator (deferred — no consumer site)
- `app.yml` → `AppBaseSettings` wiring (deferred to Phase 2.5; Phase 2 ships the type, the wiring lands in a follow-up)

**Already done in earlier phases** (master plan §Phase 1B results line 423
records "XSS regression test passes"; the master plan's own Section §Phase1B
notes `SafeHTMLStr = NewType(...)` was completed in Phase 1B):

- `SafeHTMLStr = NewType(...)` propagation

## Why mechanical four, not all six

The match-statement renderer dispatch (deferred item) requires a renderer
axis to exist on `AppBaseSettings`. The renderer axis doesn't exist today;
adding it is a larger commitment that touches HTMY/Jinja2 dispatch sites and
forces Phase 4 (MCP tool tagging) and Phase 6 (Prometheus labels) to take a
position on renderer semantics before they're ready. Deferring keeps Phase 2
focused on the loud-failure property Pillar 1 demands without dragging
forward the renderer design.

The `suppress(Exception)` ratchet is held at 1 (the surviving site in
`fastblocks/__init__.py`) per the master plan's own offer to "remove the
existing docstring that justifies it" instead of deleting the suppress. The
`__init__.py` site is a framework-boundary exception with an existing
justified docstring; deleting it changes startup semantics for every
consumer and isn't part of the mechanical-four scope.

## Architecture

Three layers, each with a single owner.

### Layer 1 — `fastblocks/core/validators.py` (NEW, source of truth)

The home ADR 0008 Rule3 names for "Shared Literal sets." This spec is the
implementation pin of that ADR.

Defines:

- `StyleName = Literal["vanilla", "fastblocks_ui"]` — the canonical Literal.
- `DEFAULT_STYLE: StyleName = "fastblocks_ui"` — pinned default per
  master plan §Phase 1A deliverable B.
- `class StyleAdapter(t.Protocol)` — cross-style adapter contract.
- `class TemplateAdapter(t.Protocol)` — cross-renderer adapter contract
  (defined now; dispatch refactor deferred to Phase 4/6).
- `class ResolverMismatchError(ValueError)` — raised by
  `format_resolver_mismatch()`.
- `def format_resolver_mismatch(depends, domain, value) -> None` — surfaces
  registry-vs-Literal drift with a "Did you mean ...?" hint.

No imports from `cli.py`, no imports from `adapters/app/_base.py`, no
runtime side effects. Adding a new style value means editing ONLY this
Literal; the sync test in `tests/core/test_validators_sync.py` enforces
that every consumer follows.

### Layer 2 — `fastblocks/adapters/app/_base.py` (settings consumer)

`AppBaseSettings.style` is the only field touched:

```python
from __future__ import annotations

# before
class AppBaseSettings(OneiricSettings):
    name: str = "fastblocks"
    style: str = "fastblocks_ui"
    theme: str = "light"

# after
from fastblocks.core.validators import DEFAULT_STYLE, StyleName

class AppBaseSettings(OneiricSettings):
    name: str = "fastblocks"
    style: StyleName = DEFAULT_STYLE
    theme: str = "light"
```

Pydantic v2 raises `ValidationError` at app startup with a clear message
naming the offending value and the legal set. Actual message format:
`Input should be 'vanilla' or 'fastblocks_ui' [type=literal_error,
input_value='kelp', input_type=str]`. No custom validator code; this
is the Literal-type validation Pydantic provides for free.

### Layer 3 — `fastblocks/cli.py` (CLI consumer)

Five call sites currently inline the Literal:

- Line 913: `create_app`'s `--style` option
- Line 941: `create_template`'s `--style` option
- Line 974: `_scaffold_app_tree`'s `style` parameter
- Line 1068: scaffold's `--style` option
- Line 1082: scaffold's `--style` option

All five collapse to:

```python
from fastblocks.core.validators import DEFAULT_STYLE, StyleName
# ...
style: StyleName = DEFAULT_STYLE,
```

Typer picks up the Literal annotation automatically (since `StyleName`
resolves to `Literal["vanilla", "fastblocks_ui"]`). No behavior change.

## Sync enforcement — `tests/core/test_validators_sync.py`

AST-based test mirroring `tests/unit/test_task_router.py::TestYAMLRoutingSync`.
Four assertions:

1. `validators.StyleName`'s `Literal` members equal `AppBaseSettings.style`'s
   resolved annotation members.
2. Every `cli.py` call site that imports `StyleName` references the same
   module-level name (not a re-declared inline Literal).
3. No inline `Literal["vanilla", "fastblocks_ui"]` exists outside
   `validators.py`.
4. `DEFAULT_STYLE` is one of `StyleName`'s members.

**AST visitor specification** (correctness I4 fix). `ast.literal_eval`
cannot parse `Literal[...]` — it's an `ast.Subscript` node, not a
literal. The test uses a custom walker:

```python
def extract_literal_args(node: ast.AST) -> tuple[str, ...] | None:
    """Return Literal members as a tuple, or None if node isn't Literal[...]."""
    if not isinstance(node, ast.Subscript):
        return None
    if not (isinstance(node.value, ast.Name) and node.value.id == "Literal"):
        return None
    slice_node = node.slice
    # Literal["a", "b"] → ast.Tuple of ast.Constant
    if isinstance(slice_node, ast.Tuple):
        members = tuple(ast.literal_eval(elt) for elt in slice_node.elts)
        return members  # type: ignore[return-value]
    # Literal["a"] → ast.Constant directly
    if isinstance(slice_node, ast.Constant):
        return (ast.literal_eval(slice_node),)
    return None
```

**Bypass paths the test must reject:**

- `Literal[*StyleName.__args__]` — `ast.Subscript` with `ast.Starred` slice → reject.
- `Literal[*values]` where `values` is a module-level tuple → reject; forces
  all legal values to be enumerated inline.
- Type aliases outside `validators.py`: `MyStyle: TypeAlias = Literal[...]` → reject.
  The spec's home is `validators.py`; aliases elsewhere defeat the single
  source of truth.
- `typing.get_args(StyleName)[0]` runtime patterns — outside AST scope, not
  caught. Document as known limitation; rely on code review + ruff for
  runtime-resolved Literal patterns.

Failure messages name the divergent file and the divergent value.

## Protocol contracts

`StyleAdapter` declares four methods. The current `style_registry.py:42`
exposes a single function `register_style_functions(env, style_name)` —
Phase 2 pins that as the Protocol method (NOT a per-style-named method
like `register_vanilla_functions` / `register_fastblocks_ui_functions`).
Renaming the Protocol method breaks the per-style-naming drift surface
in one move and matches the entry point that's already in production.

```python
from __future__ import annotations

import typing as t
from typing import Protocol, runtime_checkable

@runtime_checkable
class StyleAdapter(t.Protocol):
    """Contract every style adapter module must satisfy.

    A style adapter module at fastblocks.adapters.style.&lt;name&gt;
    implements all four methods. Registering it via
    ``register_style_candidate`` verifies isinstance(module,
    StyleAdapter) — ``@runtime_checkable`` is REQUIRED for
    isinstance() on method-only Protocols (Python 3.13).
    """
    def register_style_functions(self, env: t.Any) -> None: ...
    def get_css_path(self) -> str: ...
    def get_js_path(self) -> str: ...
    def escape_user_input(self, value: str) -> str: ...

@runtime_checkable
class TemplateAdapter(t.Protocol):
    """Contract every renderer (Jinja2 / HTMY) must satisfy.

    The renderer axis is separate from the style axis; this Protocol
    pins the cross-renderer surface so Phase 4's MCP tool tagging and
    Phase 6's Prometheus labels have a stable shape to read against.
    Phase 2 only DEFINES the Protocol; the match-statement dispatch
    refactor that uses it lands in a future phase.
    """
    def render(self, template: str, context: t.Mapping[str, t.Any]) -> str: ...
    def init_envs(self) -> t.Any: ...
```

`TemplateAdapter` lands now (Phase 2) even though dispatch is deferred,
because Phase 6's Prometheus label cardinality rule
(master plan §Pillar 5) needs a stable type to lint against.

## Registration gate — `register_style_candidate`

One new function in `fastblocks/adapters/oneiric_helper.py`, a thin
wrapper around Card 1's existing `register_candidate_strict`:

```python
from fastblocks.core.validators import StyleAdapter, _protocol_missing_methods

def register_style_candidate(
    depends: FastblocksRegistry,
    style_name: str,
    module: t.Any,
) -> None:
    if not isinstance(module, StyleAdapter):
        missing = _protocol_missing_methods(module, StyleAdapter)
        raise TypeError(
            f"Style adapter '{style_name}' is missing required "
            f"StyleAdapter methods: {missing}. See "
            f"fastblocks/core/validators.py for the contract."
        )
    oneiric_helper.register_candidate_strict(
        depends, "style", style_name, module
    )
```

**Return type is `None`, not `bool`.** `register_candidate_strict`
(verified in commit `8564fc1`) returns `None` on success and raises
`CandidateValidationError` on validation failure. The wrapper preserves
that contract — `CandidateValidationError` propagates; the only new
exception is `TypeError` for missing Protocol methods.

**The `# ty: ignore` is NOT needed here.** `@runtime_checkable` makes
`isinstance(module, StyleAdapter)` a valid call from `ty`'s perspective
because the Protocol is annotated as runtime-checkable. Phase 2 ships
with **zero** ty suppressions in production code. (`register_candidate_strict`
itself carries its own ty ignores from Card 1; Phase 2 doesn't add more.)

`register_template_candidate` is **deferred** (no consumer call site
exists). `TemplateAdapter` Protocol is still defined and tested (Phase 6's
Prometheus cardinality lint needs it); only the decorator waits.

## Error message contract — `format_resolver_mismatch`

The Oneiric-`explain()`-based error contract from master plan §Phase 2 line
308: "Unknown style 'kelp'; valid values are 'vanilla', 'fastblocks_ui'.
Did you mean 'fastblocks_ui' (closest match: see registered adapters)?"

`ResolverMismatchError` carries:

- `value: str` — the offending registered value
- `legal: tuple[str, ...]` — `StyleName` set as a runtime tuple
- `nearest: str | None` — `difflib.get_close_matches(value, legal, n=1, cutoff=0.6)`
- `resolver_explain: str` — `format_resolution_explanation_one_line(depends.explain(...))` output, or `"<unavailable>"` on failure

**One-line explain formatter.** `FastblocksRegistry.explain(domain, key)`
returns a `ResolutionExplanation` dataclass (not a string — verified in
`oneiric/core/resolution.py:183-197` and `fastblocks/core/resolver.py:221-223`).
A new helper `format_resolution_explanation_one_line(explanation)` in
`core/validators.py` produces a single-line operator-facing string.
Default shape:

```
style=vanila: 3 candidates ranked, 2 shadowed, winner=<module>.<cls>
```

If `explanation.ordered` is empty: `"style=vanila: no candidates registered"`.
If `explanation.as_dict()` is unavailable (different Oneiric version):
fall back to `repr(explanation)` and prefix with `"explain:"`.

**Hint example** (corrected from the v1 spec). For `value='kelp'` against
`legal=('vanilla', 'fastblocks_ui')`, `get_close_matches` returns `[]`
at `cutoff=0.6` (verified empirically). The hint only fires for typos
with lexical similarity (e.g., `value='vanila'` → `vanilla`,
`value='fastblock_ui'` → `fastblocks_ui`). For unrelated strings the
"Did you mean" clause is omitted — the legal-set message still surfaces.
The example in the spec uses `value='vanila'` (a typo that triggers the
hint) rather than `'kelp'` (which doesn't).

`__str__` returns a single-line operator-facing message:

```
Style 'vanila' is in the registry but not in the legal StyleName set
{vanilla, fastblocks_ui}. Did you mean 'vanilla'? Resolver explain:
style=vanila: 3 candidates ranked, 2 shadowed, winner=...
```

If `nearest is None`, the "Did you mean" clause is omitted. If
`explain()` raises (`RuntimeError`, `AttributeError`, `TypeError`,
`ValueError`, `KeyError` — narrow but slightly wider than the original
set; these are the exception types that can arise from the explain
code path), `resolver_explain` becomes `"<unavailable>"` and the
error still surfaces.

## Data flow

### Scenario 1 — `app.yml` contains `style: kelp`

`app.yml` → Oneiric Settings loader → `AppBaseSettings.__init__` → Literal
validator runs → Pydantic raises `ValidationError` "Input should be
'vanilla' or 'fastblocks_ui' [type=literal_error, input_value='kelp',
input_type=str]" → startup fails. **No new code in Phase 2** for the
type itself; the wiring path (how `app.yml` reaches `AppBaseSettings`) is
**out of Phase 2 scope** (see caveat below).

**Wiring caveat.** Production code calls `AppSettings()` with no arguments
(verified at `fastblocks/adapters/app/default.py:182`); defaults are used
directly. `OneiricSettings` does not auto-read `app.yml` (it's a
`pydantic.BaseModel`, not `pydantic_settings.BaseSettings`). The Literal
type is therefore **defensive documentation until the wiring lands**. Any
operator who explicitly passes `AppSettings(style="kelp")` or
`AppSettings.model_validate({...})` will see the ValidationError; the
common "load `app.yml` at startup" path is a separate Phase 2.5 wiring
task and is **explicitly deferred**. Phase 2 ships the type and the test
that proves it fires; the production wiring lands in a follow-up.

### Scenario 2 — `app.yml` contains `style: fastblocks_ui` but no adapter registered

`app.yml` → Pydantic → `AppBaseSettings` validated → `Oneiric.resolve("style", "fastblocks_ui")` →
no candidate → `format_resolver_mismatch(depends, "style", "fastblocks_ui")` raises
`ResolverMismatchError`. **New code:** `format_resolver_mismatch()` in
`core/validators.py`.

### Scenario 3 — registered-but-stale candidate

A registered `("style", "fastblocks-ui")` candidate with a hyphen is
*not* in the user's `app.yml`. `app.yml` contains `style: fastblocks_ui`
(Pydantic passes). Oneiric resolves successfully. The stale candidate
is reported via Phase 1.5's `emit_startup_log` (`M shadowed` count).
**No new code in Phase 2** — Phase 1.5's startup log already surfaces it.

### Scenario 4 — sync test scenario

Developer adds `"kelpui"` to `StyleName` but forgets to update a
`cli.py` call site. `tests/core/test_validators_sync.py` runs in CI,
fails with the divergent file and value named. **The sync test is the
architectural keystone.**

### Scenario 5 — operator passes `--style kelp` on the CLI

Typer parses `StyleName` (= `Literal["vanilla", "fastblocks_ui"]`) →
Typer rejects with "Invalid value for '--style': 'kelp' is not one of
'vanilla', 'fastblocks_ui'." **No new code in Phase 2** — Typer + Literal.

## Structured log shape

One log line per error path, emitted at WARNING level via Oneiric's
structured logger (`from oneiric.core.logging import get_logger`):

| Scenario | Log key | Shape |
|---|---|---|
| Pydantic literal mismatch | n/a — Pydantic raises, FastBlocks re-raises | Oneiric logger NOT called |
| Resolver mismatch | `fastblocks_validator_mismatch` | `domain=<str> value=<str> legal=<tuple> nearest=<str\|None> explain=<str>` |
| Sync-test failure | n/a — CI test failure | pytest assertion message |
| Shadowed candidate | `fastblocks_resolver_shadowed` | inherited from Phase 1.5's `emit_startup_log` |
| Protocol `isinstance` failure | `fastblocks_protocol_mismatch` | `protocol=<str> module=<str> missing=<list[str]>` |

All five use `_log = get_logger("fastblocks.validators")` so an operator
can grep startup logs with one prefix. **No Prometheus metrics added in
Phase 2** — Phase 6 reserves the Prometheus push.

## Test surface

| Test file | Tests | Markers | Purpose |
|---|---|---|---|
| `tests/core/test_validators_sync.py` | 5 | `@pytest.mark.unit` | AST-based sync between `StyleName`, `AppBaseSettings.style`, and `cli.py` (4 base assertions + 1 PEP 646 `Literal[*values]` rejection per architecture I-4) |
| `tests/core/test_resolver_mismatch.py` | 6 | `@pytest.mark.unit` | `format_resolver_mismatch()` happy path, mismatch error shape, nearest-neighbor hint, unavailable-explain fallback, narrow-exception catch, structured-log emission |
| `tests/core/test_style_adapter_protocol.py` | 5 | `@pytest.mark.unit` | `StyleAdapter` Protocol — 4 missing-method error tests (assert `pytest.raises(TypeError, match=...)`) + 1 happy-path (module-shaped + instance-shaped) |
| `tests/core/test_template_adapter_protocol.py` | 3 | `@pytest.mark.unit` | `TemplateAdapter` Protocol — 2 missing-method tests + 1 happy path |
| `tests/core/test_app_settings_literal.py` | 6 | `@pytest.mark.unit` | `AppBaseSettings` Literal validation — 2 legal values (`vanilla`, `fastblocks_ui`) + 4 illegal values (`kelp`, `webawesome`, `bulma`, `VANILLA` for case-sensitivity) |
| `tests/core/test_shadowed_count_emitted.py` | 1 | `@pytest.mark.unit` | Scenario 3 regression: register a stale candidate with a hyphen, call `emit_startup_log`, assert shadowed count ≥ 1 in the log |
| `tests/core/test_typer_cli_rejects_invalid_style.py` | 1 | `@pytest.mark.unit` | Scenario 5 regression: invoke `create_app` via `typer.testing.CliRunner` with `--style kelp`, expect non-zero exit and `kelp` in stderr |
| `tests/core/test_suppress_exception_ratchet.py` | 1 | `@pytest.mark.unit` | Ratchet test: run `git grep -c 'suppress(Exception)' -- fastblocks/` via `subprocess`, assert count ≤ 123 (master plan baseline) |

**Total: 28 new tests.** Combined with Phase 1.5x's 243-test sweep and the
~1732 existing tests, the post-Phase-2 test count is ~2003 distinct tests.

**`_fresh_registry` lift.** Card5's `_fresh_registry` helper is currently
a private function at `tests/core/test_resolve_instance.py:37`. Phase 2
**promotes it to `tests/conftest.py` as a public `@pytest.fixture`
named `fresh_registry`** (no leading underscore). Both Card5's
`test_resolve_instance.py` and Phase 2's `test_resolver_mismatch.py`
consume it via the standard pytest fixture mechanism.

**Card8 `caplog` pattern does NOT transfer to Protocol tests.** Card8
captures a WARNING-level log emitted by the identity-check. Protocol
`isinstance()` returns `False` (does not log); missing methods raise
`TypeError` (does not log). The 5 Protocol tests in
`test_style_adapter_protocol.py` use `pytest.raises(TypeError, match=...)`
to assert the missing-method names. The 6 `test_resolver_mismatch.py`
tests use `caplog` for the structured-log emission assertion
(`fastblocks_validator_mismatch`).

## Verification gate

Per master plan §Phase 2 verification (line 456-462):

| Gate | How verified |
|---|---|
| Every `Literal[...]` settings field has a runtime validator | `AppBaseSettings.style` is typed `StyleName` (resolves to `Literal["vanilla", "fastblocks_ui"]`); Pydantic v2 inherits the literal-validation behavior from `OneiricSettings`; `tests/core/test_app_settings_literal.py` 2 legal + 4 illegal-value tests confirm runtime validation fires |
| Unknown style raises the literal-validation error | `tests/core/test_app_settings_literal.py` confirms `pydantic.ValidationError` is raised for `kelp`, `webawesome`, `bulma`, `VANILLA` (4 illegal values) with the legal set named in the message — actual Pydantic format `Input should be 'vanilla' or 'fastblocks_ui' [type=literal_error, input_value='kelp', input_type=str]` |
| AppBaseSettings and CLI Literal are in sync | `tests/core/test_validators_sync.py` all 5 tests pass (4 base + 1 PEP 646 rejection) |
| `git grep -c 'suppress(Exception)' -- fastblocks/` shows number at or below baseline | Baseline is **123** (per master plan line 313; the v1 spec's "1 (Phase 1A cleanup)" claim was wrong — Phase 1A reduced the count from 123 toward but did not eliminate it). Phase 2 holds the baseline (no additions, no deletions). `tests/core/test_suppress_exception_ratchet.py` asserts ≤ 123. |
| `register_candidate` decorator with isinstance verification rejects adapter modules | `tests/core/test_style_adapter_protocol.py::test_register_rejects_missing_method` passes (asserts `pytest.raises(TypeError, match=...)`) |
| `Protocol` isinstance gate is `runtime_checkable` | `StyleAdapter` and `TemplateAdapter` both carry `@runtime_checkable`; `tests/core/test_style_adapter_protocol.py::test_protocol_is_runtime_checkable` imports and asserts the decorator presence |
| Oneiric `explain()` output is formatted single-line | `tests/core/test_resolver_mismatch.py::test_explain_output_single_line` exercises `format_resolution_explanation_one_line()` with a known `ResolutionExplanation` shape |
| `app.yml` → `AppBaseSettings` wiring works (or is explicitly deferred) | Phase 2 ships the type; wiring is **deferred to Phase 2.5** and called out in §Data flow Scenario1 caveat |

**The `suppress(Exception)` ratchet decision** (corrected from v1):
Phase 2 does not add or remove any `suppress(Exception)` site. Master plan
line 313 records the baseline as **123 sites**; Phase 1A cleanup reduced
the count from an earlier baseline but did not reach 0. Phase 2 holds the
baseline — no additions, no deletions. The framework-boundary exceptions
documented in `fastblocks/__init__.py` and `fastblocks/core/style_registry.py`
are real and intentional; future Phase 7 (final dead-code pass, master plan
line 344) takes on the cleanup.

## Per-task Integration Contracts

Per master plan §Process (line 553), each commit ships with IC block. Five
commits, all additive or backwards-compatible.

### Commit 1 — `feat(validators): add core/validators.py with StyleName + Protocols`

- *Triggered from:* ADR 0008 Rule3 "Shared Literal sets" home designation
- *Returns to / updates:* Nothing in production yet — module exists but no caller imports it
- *Demonstrable by:* `python -c "from fastblocks.core.validators import StyleName, StyleAdapter, TemplateAdapter"` succeeds
- *Rollback signal:* `git revert`; no production behavior changed
- *Observability added:* `_log = get_logger("fastblocks.validators")` for future structured logs

### Commit 2 — `refactor(_base): AppBaseSettings.style is StyleName not str`

- *Triggered from:* Phase 1.5x Card 1 (`register_candidate_strict`) + Commit 1
- *Returns to / updates:* `fastblocks/adapters/app/_base.py` — `style: str` → `style: StyleName`
- *Demonstrable by:* `tests/core/test_app_settings_literal.py` 4/4 pass; existing ~1732 tests still pass (backwards-compatible — every existing test sets `style="fastblocks_ui"`)
- *Rollback signal:* `git revert`; restores `style: str` behavior
- *Observability added:* Pydantic's literal-validation error is the loud-failure surface Pillar 1 demands

### Commit 3 — `refactor(cli): cli.py Literal annotations import from core.validators`

- *Triggered from:* Commit 2's pattern; cli.py's inline Literals are the drift surface
- *Returns to / updates:* `fastblocks/cli.py` — 5 inline `Literal["vanilla", "fastblocks_ui"]` annotations → single `StyleName` import
- *Demonstrable by:* `tests/core/test_validators_sync.py` 4/4 pass; Typer CLI invocation `python -m fastblocks create app test --style vanilla` still works
- *Rollback signal:* `git revert`; restores inline Literals
- *Observability added:* None (CLI behavior unchanged)

### Commit 4 — `feat(adapter-registration): Protocol-based isinstance gate + format_resolver_mismatch`

- *Triggered from:* Commits 1-3 supply the Protocols; `register_candidate_strict` from Card 1 supplies the registration surface
- *Returns to / updates:* `fastblocks/adapters/oneiric_helper.py` — adds `register_style_candidate()` only (the `register_template_candidate` decorator is deferred — no consumer site); `fastblocks/core/validators.py` — adds `format_resolver_mismatch()` AND `format_resolution_explanation_one_line()`
- *Demonstrable by:* `tests/core/test_style_adapter_protocol.py` (5 tests), `tests/core/test_template_adapter_protocol.py` (3 tests, Protocol-only — no decorator), `tests/core/test_resolver_mismatch.py` (6 tests) all pass
- *Rollback signal:* `git revert`; the decorator is additive — production continues to use existing `register_candidate_strict` directly
- *Observability added:* `fastblocks_validator_mismatch` and `fastblocks_protocol_mismatch` structured log lines

### Commit 5 — `docs(adr): ADR 0010 — Phase 2 mechanical-four closeout`

- *Triggered from:* This spec
- *Returns to / updates:* `docs/adr/0010-phase-2-mechanical-four.md`
- *Demonstrable by:* `find docs/adr -name "0010-*.md"` returns the new file
- *Rollback signal:* `git revert`; doc-only
- *Observability added:* None

### Commit 6 — `test(ratchet): pin suppress(Exception) count ≤ 123`

- *Triggered from:* Testing review C3 — the verification gate is decorative without an automated ratchet test
- *Returns to / updates:* `tests/core/test_suppress_exception_ratchet.py` (NEW)
- *Demonstrable by:* `pytest tests/core/test_suppress_exception_ratchet.py` passes; running `git grep -c 'suppress(Exception)' -- fastblocks/` returns ≤ 123
- *Rollback signal:* `git revert`; test-only
- *Observability added:* None

## Out of scope (deferred)

- Renderer match-statement dispatch (master plan line 311)
- `try/except Exception:` → `with suppress(Exception)` migration in `core/style_registry.py:66` (Phase 1A partially cleaned; remaining `try/except Exception:` patterns are framework-boundary and out of scope)
- Prometheus metrics for new error paths (Phase 6)
- New adapter sites using the Protocols (Phase 4+)
- Renderer `Literal[...]` field on `AppBaseSettings` (deferred per scope decision)
- `app.yml` → `AppBaseSettings` wiring (Phase 2.5 — explicit follow-up)

## Cross-references

- Master plan: `docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md` §Phase 2 (line 303-313), §Pillar 1 (line 97-107)
- ADR 0008 Rule3 validator homes: `docs/adr/0008-oneiric-selection-mechanism-ownership.md` (Card 9 closed this)
- Phase 1.5x Card 1: `register_candidate_strict` for Phase 2 (commit `8564fc1`)
- Phase 1.5x Card 7: 62 migrated files spot-check (commit `08698a3`) — gives us the canonical-singleton fixture reused in Phase 2 tests
- Phase 1.5x Card 8: facade identity-check warning (commit `e1d8f30`) — `caplog`-suppress pattern reused
- Phase 1.5x Card 9: ADR 0008 Rule3 validator homes documentation (commit `ca4a520`) — names `core/validators.py` as the home
- Phase 1.5x Card 10: `emit_startup_log` pre-app emit (commit `4ebd223`) — `M shadowed` count inherited for Scenario 3
- Sync-test precedent: `tests/unit/test_task_router.py::TestYAMLRoutingSync`
- `SimpleNamespace` ty-noise precedent: crackerjack-compliant-code skill §"`Mock(spec=X)` and `SimpleNamespace`"
- `from oneiric.core.logging import get_logger`: crackerjack-compliant-code §"Use the Oneiric logger"
- Per-checker ty directive syntax: crackerjack-compliant-code §"ty, since Phase I"