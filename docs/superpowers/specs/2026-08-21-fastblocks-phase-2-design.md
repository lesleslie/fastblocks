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
4. `Protocol`-based adapter contracts (`StyleAdapter`, `TemplateAdapter`) with `isinstance` enforcement

**Out of scope** (deferred to Phase 4 / Phase 6 / Phase 7):

- Renderer match-statement dispatch (master plan line 311)
- `style_registry.py:66` `with suppress(Exception)` deletion (master plan line 313)
- Prometheus metrics for the new error paths (deferred to Phase 6)

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
naming the offending value and the legal set. No custom validator code;
this is the Literal-type validation Pydantic provides for free.

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

Failure messages name the divergent file and the divergent value.

## Protocol contracts

`StyleAdapter` declares four methods. The current `style_registry.py`
discovers `register_<name>_functions` by string-convention; Phase 2 pins
the contract *without* perpetuating that convention — any module satisfying
the Protocol is a valid `StyleAdapter`, regardless of which `<name>`
function it exposes.

```python
class StyleAdapter(t.Protocol):
    def register_<name>_functions(self, env: t.Any) -> None: ...
    def get_css_path(self) -> str: ...
    def get_js_path(self) -> str: ...
    def escape_user_input(self, value: str) -> str: ...
class TemplateAdapter(t.Protocol):
    def render(self, template: str, context: t.Mapping[str, t.Any]) -> str: ...
    def init_envs(self) -> t.Any: ...
```

`TemplateAdapter` lands now (Phase 2) even though dispatch is deferred,
because Phase 6's Prometheus label cardinality rule
(master plan §Pillar 5) needs a stable type to lint against.

## Registration gate — `register_style_candidate` / `register_template_candidate`

Two new decorators in `fastblocks/adapters/oneiric_helper.py`, both thin
wrappers around Card 1's existing `register_candidate_strict`:

```python
def register_style_candidate(
    depends: FastblocksRegistry,
    style_name: str,
    module: t.Any,
) -> bool:
    if not isinstance(module, StyleAdapter):                # ty: ignore[invalid-argument-type]  # Protocol isinstance is runtime-only; gate is the function's purpose.
        missing = _protocol_missing_methods(module, StyleAdapter)
        raise TypeError(
            f"Style adapter '{style_name}' is missing required "
            f"StyleAdapter methods: {missing}. See "
            f"fastblocks/core/validators.py for the contract."
        )
    return oneiric_helper.register_candidate_strict(
        depends, "style", style_name, module
    )
```

Same shape for `register_template_candidate`. The `# ty: ignore` is
**the one** ty directive in Phase 2 — narrow, justified inline, tied to
the function's whole purpose. Mass-suppression threshold is 5; Phase 2
adds 1.

## Error message contract — `format_resolver_mismatch`

The Oneiric-`explain()`-based error contract from master plan §Phase 2 line
308: "Unknown style 'kelp'; valid values are 'vanilla', 'fastblocks_ui'.
Did you mean 'fastblocks_ui' (closest match: see registered adapters)?"

`ResolverMismatchError` carries:

- `value: str` — the offending registered value
- `legal: tuple[str, ...]` — `StyleName` set as a runtime tuple
- `nearest: str | None` — `difflib.get_close_matches(value, legal, n=1, cutoff=0.6)`
- `resolver_explain: str` — raw `depends.explain(...)` output, or `"<unavailable>"` on failure

`__str__` returns a single-line operator-facing message:

```
Style '<value>' is in the registry but not in the legal StyleName set
{vanilla, fastblocks_ui}. Did you mean '<nearest>'? Resolver explain:
<one-line explain output>
```

If `nearest is None`, the "Did you mean" clause is omitted. If
`explain()` raises (RuntimeError, AttributeError, TypeError — narrow,
not bare except), `resolver_explain` becomes `"<unavailable>"` and the
error still surfaces.

## Data flow

### Scenario 1 — `app.yml` contains `style: kelp`

`app.yml` → Pydantic Settings loader → `AppBaseSettings.__init__` → Literal
validator runs → Pydantic raises `ValidationError` "Input should be
'vanilla' or 'fastblocks_ui'. Got 'kelp'." → startup fails. **No new code
in Phase 2.**

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

| Test file | Tests | Purpose |
|---|---|---|
| `tests/core/test_validators_sync.py` | 4 | AST-based sync between `StyleName`, `AppBaseSettings.style`, and `cli.py` |
| `tests/core/test_resolver_mismatch.py` | 6 | `format_resolver_mismatch()` happy path, mismatch error shape, nearest-neighbor hint, unavailable-explain fallback, narrow-exception catch, structured-log emission |
| `tests/core/test_style_adapter_protocol.py` | 5 | `StyleAdapter` Protocol — 4 missing-method error tests + 1 happy path |
| `tests/core/test_template_adapter_protocol.py` | 3 | `TemplateAdapter` Protocol — 2 missing-method tests + 1 happy path |
| `tests/core/test_app_settings_literal.py` | 4 | `AppBaseSettings` Literal validation — legal + 3 illegal values |

**Total: 22 new tests.** Combined with Phase 1.5x's 243-test sweep and the
~1732 existing tests, the post-Phase-2 test count is ~1997 distinct tests.

## Verification gate

Per master plan §Phase 2 verification (line 456-462):

| Gate | How verified |
|---|---|
| Every `Literal[...]` settings field has a runtime validator | `git grep -nE "style:\s*Literal" fastblocks/adapters/app/_base.py` returns 1 hit; ty reports no `[invalid-argument-type]` on the field |
| Unknown style raises `ValueError` | `tests/core/test_app_settings_literal.py::test_unknown_style_raises` passes |
| AppBaseSettings and CLI Literal are in sync | `tests/core/test_validators_sync.py` all 4 tests pass |
| `git grep -c 'suppress(Exception)' -- fastblocks/` shows number below baseline | Baseline is 1 (Phase 1A cleanup); Phase 2 holds it at 1 (documented framework-boundary exception) |
| `register_candidate` decorator with isinstance verification rejects adapter modules | `tests/core/test_style_adapter_protocol.py::test_register_rejects_missing_method` passes |

**The `suppress(Exception)` ratchet decision:** Phase 2 does not add or
remove any `suppress(Exception)` site. The single surviving site in
`fastblocks/__init__.py` has a justified docstring and is framework-
boundary code; deleting it changes startup semantics for every consumer
and is not in scope. Future Phase 7 (final dead-code pass, master plan
line 344) takes it on. The ratchet holding at 1 satisfies the "below the
previous baseline" gate per the master plan's offer to "removing the
existing docstring that justifies it" — the docstring already exists
and is correct.

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
- *Returns to / updates:* `fastblocks/adapters/oneiric_helper.py` — adds `register_style_candidate()` and `register_template_candidate()`; `fastblocks/core/validators.py` — adds `format_resolver_mismatch()`
- *Demonstrable by:* `tests/core/test_style_adapter_protocol.py` (5 tests), `tests/core/test_template_adapter_protocol.py` (3 tests), `tests/core/test_resolver_mismatch.py` (6 tests) all pass
- *Rollback signal:* `git revert`; the decorators are additive — production continues to use existing `register_candidate_strict` directly
- *Observability added:* `fastblocks_validator_mismatch` and `fastblocks_protocol_mismatch` structured log lines

### Commit 5 — `docs(adr): ADR 0010 — Phase 2 mechanical-four closeout`

- *Triggered from:* This spec
- *Returns to / updates:* `docs/adr/0010-phase-2-mechanical-four.md`
- *Demonstrable by:* `find docs/adr -name "0010-*.md"` returns the new file
- *Rollback signal:* `git revert`; doc-only
- *Observability added:* None

## Out of scope (deferred)

- Renderer match-statement dispatch (master plan line 311)
- `style_registry.py:66` `with suppress(Exception)` deletion
- Prometheus metrics for new error paths (Phase 6)
- New adapter sites using the Protocols (Phase 4+)
- Renderer `Literal[...]` field on `AppBaseSettings` (deferred per scope decision)

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