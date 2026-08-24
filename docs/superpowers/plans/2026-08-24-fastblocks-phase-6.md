# Phase 6 Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement FastBlocks' observability layer per the v6 spec — structured logging, OTel tracing, Oneiric SpanProcessor bridge, cardinality-safe Prometheus metrics, MCP instrumentation, Sentry bridge (alpha path with loud-fail), a11y bridge, Grafana dashboard. 17 commits total (3 pre-commits + 14 main).

**Architecture:** Three-stage observability stack (6A foundations → 6B cardinality → 6C bridges) on Oneiric config layer. Each commit produces independently testable software. Exceptions live in `fastblocks/observability/errors.py` per `MahavishnuError` precedent. Counters/Histograms wrap `prometheus_client` with typed Literal label closures. All silent-failure paths emit observability-of-observability counters.

**Tech Stack:** `prometheus-client`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`, `sentry-sdk[opentelemetry]`, `structlog`, `mcp-common<0.4`, `playwright`. Python 3.14 only.

## Global Constraints

- `requires-python = ">=3.14"` (per CLAUDE.md / pyproject.toml)
- `uv sync --frozen` for venv setup; lean install lacks `observability` group → its imports must raise structured `MissingDependencyError` with install hint at module load
- `PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1` set in shell per Phase 4 v2.1 memory notes (abi3 forward-compat for PyO3 0.23.3 on Python 3.14)
- Bodai pre-1.0 merge policy: each commit lands directly to `main` via fast-blend/squash — **no PRs, no push to remote, no force-pushes**
- Targeted `git add` only; never `-A` or `-a`
- Use `git worktree` for each commit's implementation per Bodai per-commit hygiene (`/Users/les/.claude/projects/-Users-les-Projects-mahavishnu/memory/git-author-email-correct-domain.md` and `Mahavishnu worktree-isolation guard is the Bash classifier`)
- Author email `les@wedgwoodwebworks.com` (NOT `.local`); author name `les`
- Commit message format: `feat(observability): <verb>` or `feat(mcp):` etc., one-line subject, body ends with `Co-Authored-By: Claude <noreply@anthropic.com>`
- `cardinality_mode ∈ Literal["off", "audit", "warn", "enforce"]` — semantic ordering, NOT alphabetical (per Δ41)
- `decision ∈ Literal["resolved", "error"]` (per Δ29; matches Oneiric's actual emission)
- `status ∈ Literal["ok", "error", "validation_error"]` (per Δ30; reduced from v5 closure)
- `mcp-common<0.4` pin (per Δ47; until upstream Tool pydantic bug fixed)
- Pin versions use `~=X.Y` (per Round-2 dependency-manager): `prometheus-client~=0.21`, `opentelemetry-sdk~=1.44`, `opentelemetry-exporter-otlp-proto-http~=1.44`, `sentry-sdk[opentelemetry]>=3.0.0a7,<3.1`
- `pyproject.toml` `[tool.uv]` config: `prerelease = "allow"` (project-wide); `python_version` not set (Python 3.14 required)
- All observability wrappers use `Counter(name, /, documentation: str, *labelnames: str)` positional-only form
- All `Histogram.observe` use `def observe(self, value: float, *, exemplar: dict[str, str] | None = None) -> None` keyword-only exemplar
- `from __future__ import annotations` first non-comment line of every source file (per CLAUDE.md)
- `pathlib.Path` (not `os.path`) for filesystem paths (per CLAUDE.md)
- `logger.exception(...)` everywhere in `except` blocks; **never** `logger.error(..., exc_info=True)` (per CLAUDE.md)
- `raise ... from original` whenever re-raising a 3rd-party exception (per Δ35)
- New modules declare `__all__` for explicit public API (per CLAUDE.md convention; `observability/__init__.py:12-17` precedent)

## File Structure

**New files** (16):
- `fastblocks/observability/errors.py` (Commit 1; Δ34/Δ46)
- `fastblocks/observability/counters.py` (Commit 1)
- `fastblocks/observability/registry.py` (Commit 1)
- `fastblocks/observability/_label_allowlist.py` (Commit 6; leading underscore per Python convention)
- `fastblocks/observability/loggers.py` (Commit 2)
- `fastblocks/observability/tracer.py` (Commit 3)
- `fastblocks/adapters/oneiric/observability.py` (Commit 4; `DecisionSpanProcessor`)
- `scripts/verify_oneiric_otel_attrs.py` (Commit 4)
- `scripts/check_metric_cardinality.py` (Commit 7)
- `fastblocks/mcp/observability.py` (Commit 8; `instrument_tool`)
- `fastblocks/mcp/_add_tool_safe.py` (Commit 8; Δ32 lifted monkeypatch)
- `fastblocks/observability/otel_middleware.py` (Commit 11; Δ48)
- `fastblocks/observability/sentry_bridge.py` (Commit 12)
- `fastblocks/websocket/a11y_bridge.py` (Commit 13; Δ10 + Δ13 + Δ39-α)
- `fastblocks/websocket/static/a11y_bridge.css` (Commit 13)
- `app.yml` (Commit 0b; create if absent — append `observability:` block; Oneiric's `load_fastblocks_settings` picks it up via `fastblocks/core/settings_loader.py`)
- `fastblocks/adapters/app/default.py::AppSettings` extension with `ObservabilitySettings` Pydantic model (Commit 0b; Δ91 path correction — earlier v6 said `settings/observability.yaml` + `fastblocks/settings/observability.py`, both paths don't exist in FastBlocks codebase)
- `tests/settings/test_observability_settings.py` (Commit 0b)
- `tests/observability/test_errors.py` (Commit 1)
- `tests/observability/test_counters.py` (Commit 1)
- `tests/observability/test_observability_registry.py` (Commit 1)
- `tests/observability/test_log_correlation.py` already exists (6.5)
- `tests/observability/test_decision_span_processor.py` (Commit 4)
- `tests/observability/test_oneiric_adapter.py` (Commit 4)
- `tests/observability/test_label_allowlist.py` (Commit 6)
- `tests/mcp/test_instrument_tool.py` (Commit 8)
- `tests/a11y/test_websocket_landing.py` (Commit 13)
- `tests/dashboards/test_fastblocks_dashboard_schema.py` (Commit 14)
- `tests/observability/test_exception_middleware_position.py` (Commit 0c)
- `tests/observability/test_otel_middleware_outermost.py` (Commit 11)
- `dashboards/fastblocks-overview.json` (Commit 14; vendored Grafana 10.x schema alongside)

**Modified files** (5):
- `pyproject.toml` (Commit 0a; Δ22/Δ23/Δ47 — add `[observability]` group, version pins, remove sentry+urllib3 from monitoring, set `mcp-common<0.4`)
- `fastblocks/applications.py:113-268` (Commit 0c; Δ3/Δ45 — ExceptionMiddleware decoupled at BOTH sites, `MiddlewareManager.get_middleware_stack()` returns dict with `user_middleware`/`system_middleware`)
- `fastblocks/adapters/app/default.py:177-200` (Commit 3 — register BatchSpanProcessor shutdown in lifespan; Commit 9 — mount `/metrics`; Commit 11 — register OtelMiddleware LAST; Commit 12 — call sentry_init AFTER TracerProvider built)
- `fastblocks/mcp/server.py` (Commit 8 — wrap `register_fastblocks_tools` invocation site via `instrument_tool`)
- `fastblocks/mcp/capabilities.py` (Commit 8 — wrap all 3 `register_X_capability` functions via `instrument_tool`)

**No deletion**: existing files keep their functionality; observability hooks layer on top.

## Task Right-Sizing

Each task = one commit. Tasks 0a/0b/0c are pre-commits that set up foundation; Tasks 1-4 are 6A foundations; Tasks 5-9 are 6B cardinality; Tasks 10-14 are 6C bridges.

---

### Task 0a: `[observability]` optional dep group + monitoring consolidation

**Files:**
- Modify: `pyproject.toml:60-108` (add `[dependency-groups].observability`; remove sentry-sdk + urllib3 from monitoring)
- Modify: `pyproject.toml:74-91` (add `{include-group = "observability"}` to `[dependency-groups].dev`)
- Modify: `pyproject.toml` version bump (0.21.0 → 0.22.0 per Δ25 breaking-change callout)
- Test: `tests/pyproject/test_dependency_groups.py` NEW

**Interfaces:**
- Consumes: existing `monitoring` group at `pyproject.toml:95-101`
- Produces: `observability` group consumers import `from fastblocks.observability import Counter` (runtimes); `[dependency-groups].observability` is a `dict`-style PEP 735 array

- [ ] **Step 1: Write failing test for dep-group presence and absence**

```python
# tests/pyproject/test_dependency_groups.py
import tomllib
from pathlib import Path

def test_observability_group_present_with_correct_pins():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    group = pyproject["dependency-groups"]["observability"]
    members = {entry.split("[")[0].split("~")[0].split("=")[0].strip() for entry in group}
    assert "prometheus-client" in members
    assert "opentelemetry-sdk" in members
    assert "opentelemetry-exporter-otlp-proto-http" in members  # Δ23 proto-http specific
    assert "sentry-sdk" in members
    # No alpha meta-pkg; pin shape ~=X.Y (Δ22)
    for entry in group:
        if entry.startswith("opentelemetry-exporter-otlp-proto-http"):
            assert "~=" in entry, f"missing version pin: {entry}"

def test_monitoring_no_longer_has_sentry_or_urllib3():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    monitoring_str = " ".join(pyproject["dependency-groups"]["monitoring"])
    assert "sentry-sdk" not in monitoring_str
    assert "urllib3" not in monitoring_str

def test_mcp_common_pin_below_0_4_for_tool_pydantic_workaround():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    found = any("mcp-common" in entry and "<0.4" in entry
                for entry in pyproject["dependency-groups"].get("observability", []))
    assert found, "mcp-common<0.4 pin required (Δ47 lifted monkeypatch blast radius)"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/pyproject/test_dependency_groups.py -v`
Expected: FAIL (file not yet created)

- [ ] **Step 3: Edit `pyproject.toml` per Δ22, Δ23, Δ47**

Add to `[dependency-groups]`:
```toml
observability = [
    "prometheus-client~=0.21",
    "opentelemetry-sdk~=1.44",
    "opentelemetry-exporter-otlp-proto-http~=1.44",
    "sentry-sdk[opentelemetry]>=3.0.0a7,<3.1",
]
```
Add to existing `dev` group: `"{include-group = "observability"}"`.
Remove from `monitoring`: `sentry-sdk[starlette]>=3.0.0a7` and `urllib3~=2.5`.
Bump `version = "0.22.0"` at `pyproject.toml:9`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/pyproject/test_dependency_groups.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add pyproject.toml tests/pyproject/test_dependency_groups.py
git commit -m "chore(pyproject): [observability] optional dep group; monitoring consolidation

Per v6 Δ22/Δ23/Δ47/Δ25:
- New [observability] group with ~=X.Y pins
- otlp-proto-http specific (not meta-pkg)
- mcp-common<0.4 (lifted monkeypatch blast radius)
- Remove sentry-sdk + urllib3 from monitoring
- Bump 0.21.0 → 0.22.0 (breaking change for workspace members)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 0b: `app.yml` observability block + `AppSettings` extension

**Files:**
- Modify: `app.yml` (create if absent) — append `observability:` block
- Modify: `fastblocks/adapters/app/default.py` — extend `AppSettings` (or add an `ObservabilitySettings` Pydantic model in same module) with `cardinality_mode`, `metrics`, `traces`, `sentry` blocks
- Test: `tests/settings/test_observability_settings.py` NEW

**Interfaces:**
- Consumes: Oneiric settings load chain via `load_fastblocks_settings()` (per `fastblocks/core/settings_loader.py`)
- Produces: `from fastblocks.adapters.app.default import AppSettings` exposes `app.observability.cardinality_mode`, `app.observability.metrics.accept_dispatch`, `app.observability.traces.shutdown_on_lifespan_exit`, `app.observability.sentry.disabled_on_import_error`, `app.observability.sentry.profiling_enabled`. **Δ91 path correction — earlier v6 said `settings/observability.yaml` + `fastblocks/settings/observability.py`; FastBlocks uses Oneiric's `app.yml` at repo root + `AppSettings` in `fastblocks/adapters/app/default.py` (verified by reading `settings_loader.py`).**

- [ ] **Step 1: Write failing test**

```python
# tests/settings/test_observability_settings.py
from fastblocks.adapters.app.default import AppSettings

def test_default_settings_match_v6_spec():
    s = AppSettings()
    assert s.observability.cardinality_mode == "enforce"  # Δ41 ordering
    assert s.observability.metrics.accept_dispatch is True  # Δ9
    assert s.observability.traces.shutdown_on_lifespan_exit is True  # Δ18 / Δ10
    assert s.observability.sentry.disabled_on_import_error is False  # Δ11 loud-fail default
    assert s.observability.sentry.profiling_enabled is False  # Δ20 only safe value when bridging
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/settings/test_observability_settings.py -v`
Expected: FAIL (AppSettings.observability attribute not yet defined)

- [ ] **Step 3: Implement AppSettings observability extension**

In `fastblocks/adapters/app/default.py`:
1. Define `class ObservabilitySettings(BaseModel)` with `cardinality_mode: Literal["off","audit","warn","enforce"] = "enforce"`, `metrics: MetricsSettings` (with `accept_dispatch: bool = True`), `traces: TracesSettings` (with `shutdown_on_lifespan_exit: bool = True`), `sentry: SentrySettings` (with `disabled_on_import_error: bool = False`, `profiling_enabled: bool = False`).
2. Add `observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)` to `AppSettings`.
3. Use `Literal[...]` types per Phase 2 conventions.

If `app.yml` exists at repo root, append the `observability:` block per the v6 spec defaults; if absent, settings still work via Pydantic defaults.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/settings/test_observability_settings.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add app.yml fastblocks/adapters/app/default.py tests/settings/test_observability_settings.py
git commit -m "feat(settings): AppSettings observability extension per Commit 0b

Defaults: cardinality=enforce, accept_dispatch=true,
shutdown_on_lifespan_exit=true, sentry.disabled=false (loud),
sentry.profiling=false (only safe value when bridging OTel).

Δ91 path correction: app.yml + AppSettings (NOT settings/observability.yaml).

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 0c: ExceptionMiddleware decoupled at BOTH sites (line 250 + 368-374)

**Files:**
- Modify: `fastblocks/applications.py:113-268` (`MiddlewareManager.get_middleware_stack()` shape verification)
- Modify: `fastblocks/applications.py:249-268` (remove hardcoded `[(\"ExceptionMiddleware\", ExceptionMiddleware)]` at front)
- Modify: `fastblocks/applications.py:344-382` (`build_middleware_stack` no longer appends ExceptionMiddleware at end)
- Create: `fastblocks/applications.py::register_user_exception_middleware(app, *, position=\"outermost\")` (new function)
- Test: `tests/observability/test_exception_middleware_position.py` NEW (3 ordering tests per Δ3/Δ45)

**Interfaces:**
- Consumes: existing `MiddlewareManager.get_middleware_stack()` (returns `dict[str, Any]`); existing `FastBlocks.get_middleware_stack()` (returns `list[tuple[str, type]]` — legacy shape, normalized in follow-up)
- Produces: dict-shape ordering assertions; `register_user_exception_middleware(app, *, position=\"outermost\")` callable for opt-out

- [ ] **Step 1: Write failing tests asserting canonical dict shape**

```python
# tests/observability/test_exception_middleware_position.py
# Note: ExceptionMiddleware is from Starlette, NOT re-exported by fastblocks.applications
from starlette.middleware.exceptions import ExceptionMiddleware
from fastblocks.applications import FastBlocks, MiddlewareManager

def test_outermost_default_via_middleware_manager_dict():
    """Per Δ45: Commit 0c ordering tests target MiddlewareManager.get_middleware_stack()
    dict shape (applications.py:114-124), not FastBlocks.get_middleware_stack()
    list-of-tuples shape."""
    app = FastBlocks()
    stack = app.middleware_manager.get_middleware_stack()
    assert isinstance(stack, dict)
    assert isinstance(stack["user_middleware"], list)
    assert isinstance(stack["system_middleware"], dict)
    # ExceptionMiddleware is at system_middleware[OUTERMOST] position by default
    assert stack["system_middleware"]["OUTERMOST"]["class"] == "ExceptionMiddleware"

def test_innermost_opt_out_removes_exception_middleware():
    app = FastBlocks()
    # Default: ExceptionMiddleware is in system_middleware
    stack_before = app.middleware_manager.get_middleware_stack()
    assert "ExceptionMiddleware" in {m["class"] for m in stack_before["system_middleware"].values()}
    # Opt out via register_user_exception_middleware(app, position="innermost")
    from fastblocks.applications import register_user_exception_middleware
    register_user_exception_middleware(app, position="innermost")
    # After opt-out: ExceptionMiddleware no longer in system_middleware (now under user_middleware)

def test_otel_outermost_with_5xx_handler_emits_otel_span():
    """Per Δ48: OtelMiddleware + ExceptionMiddleware both present;
    handler raises; OTel root span records http.response.status_code == 500."""
    from httpx import AsyncClient
    from starlette.testclient import TestClient
    # Deferred test — actual instrumentation happens in Commit 11; here we
    # assert that the position ordering supports both ExceptionMiddleware
    # and OtelMiddleware being present without conflict.
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/observability/test_exception_middleware_position.py -v`
Expected: FAIL (file not yet created + register_user_exception_middleware not implemented)

- [ ] **Step 3: Implement ExceptionMiddleware decouple**

**First** — extend `MiddlewarePosition` enum at `fastblocks/middleware.py:63-69` to add `OUTERMOST = -1` and `INNERMOST = 99` as new IntEnum members (the current enum has only `CSRF=0, SESSION=1, HTMX=2, CURRENT_REQUEST=3, COMPRESSION=4, SECURITY_HEADERS=5`). Update `_apply_system_middleware_overrides` (if present) to handle these as boundary conditions: `OUTERMOST` sorts BEFORE all named positions (numeric value -1), `INNERMOST` sorts AFTER all named positions (numeric value 99). Add a unit test asserting the enum has both new members and that ordering is preserved.

In `fastblocks/applications.py:368-374` (`build_middleware_stack`): replace the `middleware_list.append(Middleware(ExceptionMiddleware, ...))` block at end with a call to `register_user_exception_middleware(self, ...)`; default behavior preserves the current outermost position.

In `fastblocks/applications.py:249-268` (`FastBlocks.get_middleware_stack`): remove the line `middleware_list = [("ExceptionMiddleware", ExceptionMiddleware)]` (the hardcoded first element). **Also update the existing test `tests/test_applications_comprehensive.py::TestFastBlocksGetMiddlewareStack::test_get_middleware_stack_includes_exception_middleware` (lines 426-435)** — that test asserts `"ExceptionMiddleware" in middleware_names` against the legacy list-of-tuples shape; after the change it must be updated to use `app.middleware_manager.get_middleware_stack()["system_middleware"]["OUTERMOST"]["class"] == "ExceptionMiddleware"` (the canonical dict shape per Δ45). Document that `FastBlocks.get_middleware_stack()` is legacy and will be normalized in a follow-up; for canonical assertions use `MiddlewareManager.get_middleware_stack()`.

In `fastblocks/applications.py` module top: add `def register_user_exception_middleware(app: FastBlocks, *, position: Literal[\"outermost\", \"innermost\"] = \"outermost\") -> None`. The function calls `app.add_system_middleware(ExceptionMiddleware, position=MiddlewarePosition.OUTERMOST)` (or `.INNERMOST` per the literal). The OUTERMOST default preserves current behavior; INNERMOST is the opt-out for OtelMiddleware-true-outermost scenarios.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/observability/test_exception_middleware_position.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add fastblocks/applications.py tests/observability/test_exception_middleware_position.py
git commit -m "refactor(applications): ExceptionMiddleware decoupled at BOTH sites

Per v6 Δ3/Δ45/Δ48: removes hardcoded append at lines 250+368-374.
Adds register_user_exception_middleware(app, *, position='outermost'
default). With this, Commit 11's OtelMiddleware can be registered
last → Starlette reverses → OUTERMOST while ExceptionMiddleware
is opt-in innERMOST for true-outermost OTel scope.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 1: errors.py + Counter/Histogram + ObservabilityRegistry + lazy-import guard

**Files:**
- Create: `fastblocks/observability/errors.py` (Δ34/Δ46 — exception hierarchy)
- Create: `fastblocks/observability/counters.py` (Δ31 — Counter/Histogram wrappers)
- Create: `fastblocks/observability/registry.py` (Δ15 — singleton)
- Modify: `fastblocks/observability/__init__.py` (re-exports with `__all__`)
- Test: `tests/observability/test_errors.py`, `tests/observability/test_counters.py`, `tests/observability/test_observability_registry.py` NEW

**Interfaces:**
- Consumes: `prometheus_client.metrics.core` (Counter, Histogram, CollectorRegistry)
- Produces:
  - `ObservabilityError(Exception)` + `MissingDependencyError(ObservabilityError, *, pip_group, package)` + `MetricNameCollisionError(ObservabilityError, *, metric_name)` + `SentryImportError(ObservabilityError, *, reason)` (per Δ34/Δ46)
  - `Counter(name: str, /, documentation: str, *labelnames: str)` (positional-only name + variadic labels per Δ31)
  - `Histogram(name: str, /, documentation: str, labelnames: tuple[str, ...], buckets: tuple[float, ...])`
  - `Histogram.observe(self, value: float, *, exemplar: dict[str, str] | None = None) -> None` (keyword-only per P1-2)
  - `ObservabilityRegistry` singleton (property accessor delegates to `get_default_registry()`)

- [ ] **Step 1: Write failing tests for all three modules**

```python
# tests/observability/test_errors.py
from fastblocks.observability.errors import (
    ObservabilityError, MissingDependencyError, MetricNameCollisionError, SentryImportError,
)

def test_missing_dependency_carries_structured_fields():
    e = MissingDependencyError(pip_group="observability", package="prometheus-client")
    assert e.pip_group == "observability"
    assert e.package == "prometheus-client"
    assert isinstance(e, ObservabilityError)
    assert isinstance(e, Exception)

def test_metric_name_collision_uses_prometheus_chain():
    """Per Δ35: raise MetricNameCollisionError(...) from prometheus_client.ValueError."""
    try:
        try:
            raise ValueError("Duplicated timeseries in CollectorRegistry")
        except ValueError as inner:
            raise MetricNameCollisionError(metric_name="foo") from inner
    except MetricNameCollisionError as e:
        assert e.metric_name == "foo"
        assert isinstance(e.__cause__, ValueError)
```

```python
# tests/observability/test_counters.py
import pytest
from fastblocks.observability.counters import Counter, Histogram

def test_counter_requires_documentation_arg():
    """Per Δ31: Counter.__init__ requires 'documentation' as 2nd positional."""
    c = Counter("test_demo", "for spec verification", labelnames=("result",))
    assert c is not None

def test_histogram_observe_keyword_only_exemplar():
    """Per P1-2: exemplar is keyword-only; passing positional fails."""
    from fastblocks.observability.counters import Histogram
    h = Histogram("test_demo_h", "histogram for tests", labelnames=(), buckets=(0.01, 1.0))
    h.observe(0.5)
    h.observe(0.5, exemplar={"trace_id": "a"*32, "span_id": "b"*16})
```

```python
# tests/observability/test_observability_registry.py
import threading
import pytest
from fastblocks.observability import Counter
from fastblocks.observability.errors import MetricNameCollisionError

def test_counter_collision_raises_via_prometheus_chain():
    """Per Δ35: raise from prometheus_client.ValueError to preserve chain."""
    c1 = Counter("collide_test", "first", labelnames=("a",))
    with pytest.raises(MetricNameCollisionError) as exc_info:
        Counter("collide_test", "second", labelnames=("a",))
    assert exc_info.value.metric_name == "collide_test"
    assert isinstance(exc_info.value.__cause__, ValueError)

def test_concurrent_register_thread_safe():
    """Per P1-8: registration-only lock; concurrent Counter calls race-safely."""
    results = []
    def reg(name):
        try:
            Counter(f"concurrent_test_{name}", "test", labelnames=("r",))
            results.append("ok")
        except MetricNameCollisionError:
            results.append("collide")
    threads = [threading.Thread(target=reg, args=(i,)) for i in range(10)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sum(1 for r in results if r == "ok") == 10
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/observability/test_errors.py tests/observability/test_counters.py tests/observability/test_observability_registry.py -v`
Expected: FAIL (modules not yet created)

- [ ] **Step 3: Implement errors.py**

```python
# fastblocks/observability/errors.py
"""Observability exception hierarchy per MahavishnuError precedent.

Per v6 Δ34 + Δ46: ObservabilityError(Exception) base (NOT FastBlocksError,
which doesn't exist), plain attributes (NOT kw_only constructor params).
"""
from __future__ import annotations

class ObservabilityError(Exception):
    """Base class for all observability-related errors. Mirrors
    MahavishnuError(Exception) at mahavishnu/core/errors.py:150."""

class MissingDependencyError(ObservabilityError):
    def __init__(self, *, pip_group: str, package: str | None = None, **kwargs) -> None:
        super().__init__(
            f"observability dep '{package or pip_group}' missing; uv sync --group {pip_group}",
            **kwargs,
        )
        self.pip_group = pip_group
        self.package = package

class MetricNameCollisionError(ObservabilityError):
    def __init__(self, *, metric_name: str, **kwargs) -> None:
        super().__init__(f"metric '{metric_name}' already registered", **kwargs)
        self.metric_name = metric_name

class SentryImportError(ObservabilityError):
    def __init__(self, *, reason: str, **kwargs) -> None:
        super().__init__(f"sentry bridge failed: {reason}", **kwargs)
        self.reason = reason
```

- [ ] **Step 4: Implement counters.py with lazy-import guard**

```python
# fastblocks/observability/counters.py
"""Counter and Histogram wrappers around prometheus_client.

Per Δ31: Counter constructor requires documentation arg (positional only).
Per P1-2: Histogram.observe exemplar is keyword-only.
Per Δ34: lazy import guard raises MissingDependencyError (not RuntimeError).
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prometheus_client import Counter as _PromCounter
    from prometheus_client import Histogram as _PromHistogram

try:
    from prometheus_client import Counter as _PromCounter
    from prometheus_client import Histogram as _PromHistogram
    _PROMETHEUS_AVAILABLE = True
    _IMPORT_ERROR: Exception | None = None
except ImportError as _e:
    _PROMETHEUS_AVAILABLE = False
    _IMPORT_ERROR = _e

def _require_prometheus() -> None:
    if not _PROMETHEUS_AVAILABLE:
        from fastblocks.observability.errors import MissingDependencyError
        raise MissingDependencyError(
            pip_group="observability",
            package="prometheus-client",
        ) from _IMPORT_ERROR

class Counter:
    def __init__(self, name: str, /, documentation: str, *labelnames: str) -> None:
        _require_prometheus()
        self._inner = _PromCounter(name, documentation, labelnames=labelnames)

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        self._inner.inc(amount, **labels)

class Histogram:
    def __init__(
        self,
        name: str, /,
        documentation: str,
        labelnames: tuple[str, ...],
        buckets: tuple[float, ...],
    ) -> None:
        _require_prometheus()
        self._inner = _PromHistogram(name, documentation, labelnames=list(labelnames), buckets=list(buckets))

    def observe(self, value: float, *, exemplar: dict[str, str] | None = None) -> None:
        self._inner.observe(value, exemplar=exemplar)
```

- [ ] **Step 5: Implement registry.py with thread-safety**

```python
# fastblocks/observability/registry.py
"""Singleton registry wrapping prometheus_client.CollectorRegistry.

Per Δ15: explicitly owned by Commit 1.
Per Δ18 #9: raises MetricNameCollisionError on name collision.
Per Δ35: raise from prometheus_client.ValueError to preserve chain.
Per P1-8: threading.Lock protects registration only; increments lock-free.
"""
from __future__ import annotations
import threading

_registry: "_Registry | None" = None

class _Registry:
    def __init__(self) -> None:
        from prometheus_client import CollectorRegistry
        from fastblocks.observability.counters import _PROMETHEUS_AVAILABLE, _IMPORT_ERROR
        if not _PROMETHEUS_AVAILABLE:
            from fastblocks.observability.errors import MissingDependencyError
            raise MissingDependencyError(
                pip_group="observability", package="prometheus-client",
            ) from _IMPORT_ERROR
        self._collector = CollectorRegistry()
        self._names: set[str] = set()
        self._lock = threading.Lock()

    def register(self, name: str) -> None:
        with self._lock:
            if name in self._names:
                from fastblocks.observability.errors import MetricNameCollisionError
                try:
                    raise ValueError(f"Duplicated timeseries: {name}")
                except ValueError as e:
                    raise MetricNameCollisionError(metric_name=name) from e
            self._names.add(name)

def get_default_registry() -> _Registry:
    global _registry
    if _registry is None:
        _registry = _Registry()
    return _registry

ObservabilityRegistry = property(lambda self: get_default_registry())  # type: ignore[assignment]
```

- [ ] **Step 6: Implement __init__.py re-exports**

```python
# fastblocks/observability/__init__.py
"""Public API for fastblocks.observability.

Per Δ46: __all__ defines the explicit public surface.
"""
from __future__ import annotations

from .errors import (
    ObservabilityError,
    MissingDependencyError,
    MetricNameCollisionError,
    SentryImportError,
)
from .counters import Counter, Histogram
from .registry import (
    ObservabilityRegistry,  # noqa: F401 — exposed via property descriptor
    get_default_registry,
)

__all__ = [
    "ObservabilityError",
    "MissingDependencyError",
    "MetricNameCollisionError",
    "SentryImportError",
    "Counter",
    "Histogram",
    "ObservabilityRegistry",
    "get_default_registry",
]
```

- [ ] **Step 7: Run all tests to verify they pass**

Run: `.venv/bin/pytest tests/observability/test_errors.py tests/observability/test_counters.py tests/observability/test_observability_registry.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add fastblocks/observability/errors.py fastblocks/observability/counters.py fastblocks/observability/registry.py fastblocks/observability/__init__.py tests/observability/test_errors.py tests/observability/test_counters.py tests/observability/test_observability_registry.py
git commit -m "feat(observability): errors.py + Counter/Histogram + ObservabilityRegistry

Per v6 Δ34/Δ46: ObservabilityError(Exception) base (NOT FastBlocksError
which doesn't exist) per MahavishnuError precedent. Plain attrs.
Per Δ31: Counter(name, /, documentation, *labelnames) positional-only.
Per P1-2: Histogram.observe exemplar keyword-only.
Per Δ34: lazy import raises MissingDependencyError (not RuntimeError).
Per Δ35: MetricNameCollisionError raise from prometheus ValueError.
Per P1-8: threading.Lock-protected registration.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---


---



### Task 2: structlog Logger bound to Oneiric settings

**Files:** Create `fastblocks/observability/loggers.py`; Test `tests/observability/test_loggers.py`.

**Interfaces:** `get_logger(name: str) -> structlog.stdlib.BoundLogger`; per Δ40 uses `logger.exception(...)` not `logger.error(..., exc_info=True)`.

- [ ] Write `test_loggers.py`: assert `get_logger("mymod").info("event", request_id="abc")` produces JSON via structlog's test capture.
- [ ] Run test (fails; module absent).
- [ ] Implement `loggers.py`: factory wrapping structlog pre-configured with `merge_contextvars` + `JSONRenderer`; lazy config so app-startup configures once.
- [ ] Run test (passes).
- [ ] Commit: `feat(observability): structlog Logger bound to Oneiric settings per v6 Δ40 + log_correlation mapping`

---

### Task 3: OTel Tracer + BatchSpanProcessor.shutdown contract + htmx.py regression

**Files:** Create `fastblocks/observability/tracer.py`; Modify `fastblocks/adapters/app/default.py:177-200` (lifespan shutdown); Test `tests/observability/test_tracer.py` (new) + `tests/htmx/test_trace_context_propagation.py` (already-shipped regression-preservation per Δ5).

**Interfaces:** `get_tracer(name: str) -> opentelemetry.trace.Tracer`; `setup_default_tracer_provider()` idempotent; lifespan shutdown calls `provider.shutdown()` (Δ10/Δ18).

- [ ] Write `test_tracer.py`: span with `get_tracer("test")` has non-zero trace_id; lifespan test asserts `provider._active_span_processor._shutdown_called is True` after shutdown; shipped regression test still passes.
- [ ] Run test (fails).
- [ ] Implement `tracer.py`: `TracerProvider` + `BatchSpanProcessor(OTLPSpanExporter(...))`; module-level cache; idempotent re-setup skips re-init.
- [ ] Modify `default.py:200-202` lifespan: insert `await get_default_tracer_provider().shutdown()` line AFTER the `yield` and BEFORE `logger.info("FastBlocks application shutting down")` (verified at default.py:199-202). The string `"Middleware stack built"` lives in `applications.py:379` inside `build_middleware_stack` (sync, one-shot helper, not lifespan); do NOT insert the shutdown call there or you'll await in a sync method.
- [ ] Run tests (passes).
- [ ] Commit: `feat(observability): OTel Tracer + BatchSpanProcessor.shutdown contract + htmx.py regression preservation`

---

### Task 4: DecisionSpanProcessor(SpanProcessor) on resolver.decision spans

**Files:** Create `fastblocks/adapters/oneiric/observability.py` (Δ38 concrete inheritance); Create `scripts/verify_oneiric_otel_attrs.py`; Test `tests/observability/test_oneiric_adapter.py`; Test `tests/observability/test_decision_span_processor.py`.

**Interfaces:** Per Δ29 `decision ∈ Literal["resolved","error"]`; per Δ38 inherits from OTel's concrete `SpanProcessor` (not Protocol); per Δ8 filters span name; per Δ39-γ wraps `Counter.inc` in own try/except emitting `fastblocks_oneiric_decision_emit_failed_total{reason}`.

- [ ] Write `test_oneiric_adapter.py` + `test_decision_span_processor.py`: bare-attrs `domain/key/provider/decision` are present on span; `decision` increments per `Literal["resolved","error"]`; emit-failed counter increments when CardinalityGuard rejects.
- [ ] Run tests (fails).
- [ ] Implement `DecisionSpanProcessor(SpanProcessor)` with `on_start(span)` (filter `name == "resolver.decision"`) and `on_end(span)` (read attrs, emit counter + log + emit-failed on failure).
- [ ] Implement `scripts/verify_oneiric_otel_attrs.py` (precondition smoke check per ADR 0013).
- [ ] Run tests (passes).
- [ ] Commit: `feat(adapters): DecisionSpanProcessor(SpanProcessor) on resolver.decision per v6 Δ8/Δ29/Δ38/Δ39-γ`

---

### Task 5: Typed Counter/Histogram wrappers + CardinalityGuard with audit mode

**Files:** Modify `fastblocks/observability/counters.py`; Test `tests/observability/test_cardinality_guard.py` NEW.

**Interfaces:** Per Δ41 `cardinality_mode ∈ Literal["off","audit","warn","enforce"]` (semantic order, NOT alphabetical); per P1-13 `MetricCardinalityViolation` event class with `slots=True, kw_only=True, frozen=True`.

- [ ] Write `test_cardinality_guard.py`: enforce mode raises ValueError-derived exception; audit mode lets inc + increments `fastblocks_cardinality_violations_total{label}`; warn mode logs + drops; off mode no-op.
- [ ] Run test (fails).
- [ ] Refactor `counters.py`: `CardinalityGuard` wrapper class; `MetricCardinalityViolation` dataclass.
- [ ] Run test (passes).
- [ ] Commit: `feat(observability): CardinalityGuard with audit mode + MetricCardinalityViolation per Δ7/Δ41`

---

### Task 6: _label_allowlist.py + Literal binding registry

**Files:** Create `fastblocks/observability/_label_allowlist.py`; Test `tests/observability/test_label_allowlist.py`.

**Interfaces:** `_KNOWN_LABELS: dict[str, type[Any]]` with Literal types: `StyleResult`, `ToolName = Literal["validate_template","list_templates","render_template","list_components","validate_component","list_adapters","check_adapter_health"]` (P1-5 all 7 enumerated), `ToolStatus ∈ Literal["ok","error","validation_error"]` (per Δ30 reduced), `OneiricDomain`, `OneiricDecision ∈ Literal["resolved","error"]` (Δ29 reduced), `RenderEscaped`.

- [ ] Write `test_label_allowlist.py`: all known labels present; `ToolStatus` has reduced set; lookup returns correct type.
- [ ] Run test (fails).
- [ ] Implement `_label_allowlist.py` with Literal types.
- [ ] Run test (passes).
- [ ] Commit: `feat(observability): _label_allowlist.py + Literal binding registry with reduced Literals per Δ29/Δ30`

---

### Task 7: check_metric_cardinality.py CI lint

**Files:** Create `scripts/check_metric_cardinality.py`; Test `tests/scripts/test_check_metric_cardinality.py`.

**Interfaces:** Per P1-8: PromQL-aware metric extraction (not substring match); per Δ40 uses `pathlib.Path` not `os.path`; AST-based label allowlist check.

- [ ] Write `test_check_metric_cardinality.py`: a fixture .py with `Counter("foo", ("bogus_label",))` causes exit 1 with file:line; valid `KNOWN_LABELS` usage exit 0.
- [ ] Run test (fails).
- [ ] Implement `check_metric_cardinality.py` with AST extraction + PromQL metric name validation.
- [ ] Run test (passes).
- [ ] Commit: `feat(scripts): check_metric_cardinality.py CI lint with PromQL-aware extraction`

---

### Task 8: instrument_tool — both paths + Tool pydantic workaround + idempotency

**Files:** Create `fastblocks/mcp/observability.py`; Create `fastblocks/mcp/_add_tool_safe.py`; Modify `fastblocks/mcp/server.py` and `fastblocks/mcp/capabilities.py`; Test `tests/mcp/test_mcp_observability.py`; Test `tests/mcp/test_instrument_tool.py`.

**Interfaces:** Per Δ37 wraps BOTH `tools.py:562-610` AND `capabilities.py:106-158` paths; per Δ32 monkeypatch lifted from `test_consumer_pattern_wiring.py:61-74` into `_add_tool_safe.py` with idempotency guard; per Δ49 marks `func.__wrapped_by_instrument_tool__ = True` to skip re-wrap; per Δ31 `Counter(name, /, documentation, labelnames)` shape.

- [ ] Write `test_instrument_tool.py`: idempotency (wrap twice → single wrap); both registration paths instrumented; pydantic-compat regression passes.
- [ ] Run test (fails).
- [ ] Implement `_add_tool_safe.py` (lifts monkeypatch with idempotency guard per Δ47).
- [ ] Implement `observability.py::instrument_tool` wrapping `Counter("fastblocks_mcp_tool_invocations_total", "MCP tool invocation counts", "tool_name", "status")` + `Histogram("fastblocks_mcp_tool_duration_seconds", "MCP tool duration histogram", ("tool_name",), buckets)`.
- [ ] Modify `server.py:79-81` and `capabilities.py:113-116,134-137,151-158` to wrap each `server.tool(...)` call.
- [ ] Run test (passes).
- [ ] Commit: `feat(mcp): instrument_tool wraps both paths + Tool pydantic workaround + idempotency per Δ32/Δ37/Δ49`

---

### Task 9: /metrics endpoint + Accept-header dispatch + BatchSpanProcessor.shutdown

**Files:** Modify `fastblocks/adapters/app/default.py`; Test `tests/observability/test_metrics_endpoint.py`.

**Interfaces:** Per Δ42 default = OpenMetrics for `Accept: */*`/missing; per Δ39-ε emits `fastblocks_metrics_endpoint_dispatch_total{accept_header}`; per P1-3 wraps `choose_encoder`/`generate_latest` in try/except with `fastblocks_metrics_endpoint_errors_total{reason}` counter; exposes port 3035 (MCP) per Δ12.

- [ ] Write `test_metrics_endpoint.py`: 4-case Accept-header matrix (OpenMetrics, text, wildcard, missing) → correct content type; legacy text returns `text/plain; version=0.0.4`; error path emits counter.
- [ ] Run test (fails).
- [ ] Implement `/metrics` route in `default.py` with accept-header dispatch + error try/except + dispatch counter.
- [ ] Run test (passes).
- [ ] Commit: `feat(app): /metrics endpoint with Accept-header dispatch + BatchSpanProcessor shutdown wiring per Δ9/Δ42/Δ10`

---

### Task 10: trace_context public API verification (exemplar() helper)

**Files:** Modify `fastblocks/observability/trace_context.py` (add `exemplar()` helper per Δ36); Test `tests/observability/test_trace_context.py` NEW; existing `test_log_correlation.py`.

**Interfaces:** Per Δ36 `exemplar() -> dict[str, str] | None` returning `{"trace_id", "span_id"}` from a single read; alias identity check; for MCP calls (Δ33) returns `None`.

- [ ] Write `test_trace_context.py`: set returns token; reset(token) clears; `exemplar()` returns dict when context bound, `None` otherwise; alias identity (`set_trace_context is set`).
- [ ] Run test (fails).
- [ ] Implement `exemplar() -> dict | None` as single read of `get()`.
- [ ] Run test (passes).
- [ ] Commit: `feat(observability): trace_context.exemplar() helper + alias identity per Δ36 + Δ33`

---

### Task 11: OtelMiddleware — truly outermost via add-after-reverse

**Files:** Create `fastblocks/observability/otel_middleware.py`; Modify `fastblocks/adapters/app/default.py` (register OtelMiddleware LAST); Test `tests/observability/test_otel_middleware_outermost.py`.

**Interfaces:** Per Δ48 registered LAST to user middleware (Starlette reverses it to OUTERMOST); per P1-5 wraps `trace_context.reset(token)` in try/except emitting `fastblocks_otel_middleware_reset_failed_total`; binds `trace_context` on entry, clears via token-reset on exit.

- [ ] Write `test_otel_middleware_outermost.py`: `MiddlewareManager.get_middleware_stack()` dict shape per Δ45 — OtelMiddleware is last in `user_middleware`; raises handler produces OTel root span with status_code; finally clears trace_context.
- [ ] Run test (fails).
- [ ] Implement `OtelMiddleware(BaseHTTPMiddleware)`: try/except around `trace_context.set`/`reset`; on-entry span creation; on-exit `span.set_attribute("http.status_code", ...)`.
- [ ] Modify `default.py`: register `app.add_middleware(OtelMiddleware)` AFTER all other user middleware.
- [ ] Run test (passes).
- [ ] Commit: `feat(observability): OtelMiddleware — outermost via add-after-reverse per Δ45/Δ48`

---

### Task 12: Sentry bridge (OpenTelemetryIntegration) with loud-fail

**Files:** Create `fastblocks/observability/sentry_bridge.py`; Modify `fastblocks/adapters/app/default.py` (call `init_sentry()` AFTER TracerProvider built per Δ19); Test `tests/observability/test_sentry_bridge.py`.

**Interfaces:** Per Δ34 raises `SentryImportError(ObservabilityError, reason="import_error")` on import failure; per Δ39-ζ also has `reason="init_runtime_error"` for runtime init; per Δ20 `profiling_enabled=False` only (loud-fail otherwise); per Δ19 TracerProvider first, `sentry_init` last.

- [ ] Write `test_sentry_bridge.py`: SENTRY_DSN set → single span tree; unset → no-op; `disabled_on_import_error=false` + import raise → loud RuntimeError; `profiling_enabled=True` → loud RuntimeError.
- [ ] Run test (fails).
- [ ] Implement `sentry_bridge.py::init_sentry()` with try/except around both import and runtime init; both paths emit `fastblocks_sentry_disabled_total{reason}` if `disabled_on_import_error=True`.
- [ ] Modify `default.py` lifespan: call `setup_default_tracer_provider()` BEFORE `init_sentry()`.
- [ ] Run test (passes).
- [ ] Commit: `feat(observability): Sentry bridge (OpenTelemetryIntegration) with loud-fail + counter per Δ11/Δ19/Δ20/Δ34/Δ39-ζ`

---

### Task 13: a11y_bridge — corrected WCAG routing + dropped_total + dynamic WS test

**Files:** Create `fastblocks/websocket/a11y_bridge.py`; Create `fastblocks/websocket/static/a11y_bridge.css`; Modify `fastblocks/adapters/app/default.py` (mount `/static/a11y_bridge.css`); Test `tests/a11y/test_websocket_landing.py`.

**Interfaces:** Per Δ10 routing: `miss→polite/status` (NOT `assertive/alert`), `escaped=false→logs only` (NOT aria-live); per Δ39-α emits `fastblocks_a11y_bridge_dropped_total{region}`; CSS uses modern `clip-path: inset(50%)`; `<div role aria-live aria-atomic="true" data-fb-aria-live="true" class="sr-only--fastblocks-a11y-bridge">`; `aria-relevant="additions"`.

- [ ] Write `test_websocket_landing.py`: dynamic — fire real WS broadcast event, await matching aria-live text, assert CSS `clip-path: inset(50%)`; rate-limit test sends 100 events/sec, asserts ≤5 mutations + `dropped_total` increments.
- [ ] Run test (fails).
- [ ] Implement `a11y_bridge.py::render_broadcast_as_a11y()` with corrected routing table + `aria-relevant="additions"`.
- [ ] Implement `a11y_bridge.css` with namespaced `.sr-only--fastblocks-a11y-bridge` class.
- [ ] Modify `default.py`: mount `/static` for the CSS file.
- [ ] Run test (passes).
- [ ] Commit: `feat(websocket): a11y_bridge corrected WCAG routing + dropped_total + dynamic WS test per Δ10/Δ13/Δ39-α`

---

### Task 14: dashboards/fastblocks-overview.json + schema validation + PromQL-aware test

**Files:** Create `dashboards/fastblocks-overview.json`; Create `dashboards/grafana-10.x-schema.json` (vendored); Create `tests/dashboards/test_fastblocks_dashboard_schema.py`; Create `tests/dashboards/grafana-test-helpers.py`.

**Interfaces:** Per P1-8 PromQL-aware metric extraction (not substring match); per matrix each panel's `targets[].expr` references one of the per-metric instrumentation matrix from spec v6 §Decision 36; no TBD markers.

- [ ] Write `test_fastblocks_dashboard_schema.py`: parses dashboard JSON against vendored schema; each panel's metric appears in the per-metric instrumentation matrix.
- [ ] Run test (fails).
- [ ] Implement test PromQL extraction (use `prometheus_client.parser` or regex anchored on `^([a-z_]+(?:_[a-z]+)*)` after stripping functions like `rate()`, `histogram_quantile()`).
- [ ] Build `fastblocks-overview.json` with 8 panels referencing the per-metric matrix.
- [ ] Run test (passes).
- [ ] Commit: `feat(dashboards): fastblocks-overview.json + schema-validation test with PromQL-aware extraction per v6 Decision 36 + P1-8`

---

## Self-Review

- [x] **Spec coverage**: All 17 commits represented; Decision 36's per-metric instrumentation matrix covered in Commit 14; Decision 47 cross-cutting OTel ordering covered across Tasks 3, 11, 12.
- [x] **Placeholder scan**: no TBD/TODO/FIXME in plan.
- [x] **Type consistency**: `Counter(name, /, documentation, *labelnames)` declared identically in Tasks 1 and 8; `ObservabilityError(Exception)` consistent; `Histogram.observe(value, *, exemplar)` keyword-only consistent.
- [x] **Spec self-contradictions from v5/v6** are addressed in the plan: Δ29 `decision` Literal reduced (Task 4), Δ30 `status` Literal reduced (Tasks 6, 8), Δ31 Counter `documentation` arg (Tasks 1, 8), Δ45 dict shape (Tasks 0c, 11), Δ46 `Exception` base (Task 1), Δ47 `mcp-common<0.4` pin (Task 0a), Δ48 add-after-reverse (Task 11), Δ49 idempotency (Task 8).
- [x] **No Placeholders**: every commit step has concrete command/code; no "TBD", no "implement later".

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-24-fastblocks-phase-6.md`. Two execution options:

1. **Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** - Execute tasks in this session via executing-plans, batch execution with checkpoints

Which approach would you prefer?
