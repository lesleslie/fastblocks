# FastBlocks Ruff Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the reported FastBlocks Ruff checks pass while migrating affected callers to the installed Oneiric resolver contract and preserving or improving failure semantics.

**Architecture:** First establish one typed, process-wide Oneiric resolution boundary and remove stale ACB skip gates. Then remediate deterministic Ruff rules and classify broad exception handlers by boundary role. Internal code catches predictable exceptions; plugin, protocol, renderer, workflow, and batch boundaries retain broad handling only when they preserve diagnostics and explicit failure state. Validation proceeds by domain and ends with Ruff, pytest, public-import smoke, and Crackerjack gates.

**Tech Stack:** Python 3.13, FastBlocks, Oneiric 0.16.1, Pydantic v2, msgspec, pytest/pytest-asyncio, Ruff, Crackerjack.

## Global Constraints

- Preserve the existing working tree: it contains 80 dirty paths, five local commits ahead of `origin/main`, and unrelated untracked assets.
- Do not delete `*.backup.json`, archived test artifacts, or untracked template assets as part of this plan.
- Do not commit, push, amend, or rewrite history unless the user explicitly requests it.
- Use `from __future__ import annotations`, Python 3.13 syntax, `pathlib.Path`, and the existing Oneiric logger conventions.
- Do not add a global or per-file `BLE001` ignore.
- Keep justified broad catches local, diagnostic-preserving, and explicitly annotated when Ruff cannot infer the framework boundary.
- Security-sensitive failures fail closed; they must not return unsanitized input or a success result.
- Do not reintroduce `importlib.util.spec_from_file_location` plus `exec_module` for HTMY.
- Do not change the public FastBlocks template export surface or the externally consumed `jinja2_async_environment.loaders` exception classes.
- Run focused tests with `--no-cov -n 0`; project defaults enable coverage and xdist and are too noisy for red/green feedback.
- Do not claim completion while any requested gate or an explicitly required targeted test is failing.

______________________________________________________________________

## File Map

### Resolver and compatibility boundary

- Modify: `fastblocks/core/resolver.py` — process-wide resolver singleton and typed component resolution helpers.
- Modify: `fastblocks/adapters/oneiric_helper.py` — Candidate registration diagnostics and narrow exception contract.
- Modify: every affected production module that currently constructs `Resolver()` or calls unsupported `get`, `get_sync`, `set`, or awaits raw `resolve`, including `fastblocks/caching.py`, `fastblocks/middleware.py`, `fastblocks/applications.py`, `fastblocks/initializers.py`, `fastblocks/main.py`, `fastblocks/exceptions.py`, `fastblocks/actions/{gather,query,sync}`, `fastblocks/adapters`, `fastblocks/mcp`, and `fastblocks/_*_integration.py`.
- Create: `tests/core/test_resolver.py` — Candidate lookup, factory construction, missing component, and async factory contracts.

### Integration and stale-skip domain

- Modify: `fastblocks/_validation_integration.py`, `_events_integration.py`, `_workflows_integration.py`, `_health_integration.py`.
- Modify: `tests/test_validation_integration.py`, `tests/test_workflows_integration.py`, `tests/security/test_input_validation.py`, and the relevant event/health test modules.
- Create or extend focused tests for sanitizer failure, event delivery status, workflow skipped steps, health partial results, and current Oneiric availability aliases.

### Gather/query/application runtime domain

- Modify: `fastblocks/actions/gather/{application,components,middleware,models,routes,strategies,templates}.py`.
- Modify: `fastblocks/actions/query/parser.py`, `fastblocks/applications.py`, `fastblocks/caching.py`, `fastblocks/cli.py`, `fastblocks/core/style_registry.py`, `fastblocks/exceptions.py`, `fastblocks/htmx.py`, `fastblocks/initializers.py`, `fastblocks/main.py`.
- Modify or create: matching tests under `tests/actions/gather`, `tests/actions/query`, `tests/test_actions_gather.py`, `tests/test_applications*.py`, `tests/test_caching*.py`, `tests/test_cli*.py`, `tests/test_initializers*.py`, and `tests/core/test_style_registry.py`.

### Sync domain

- Modify: `fastblocks/actions/sync/{cache,settings,static,strategies,templates}.py`.
- Modify: `tests/actions/sync`, `tests/test_actions_sync.py`, and focused tests for parsing, per-item failure retention, rollback, cleanup, and resolver failures.

### Adapter domain

- Modify: `fastblocks/adapters/auth/_base.py`, `fonts/{_base,google,squirrel}.py`, `icons/{_base,fontawesome,heroicons,lucide,materialicons,phosphor,remixicon}.py`, `images/{_base,cloudflare,twicpics}.py`, `routes/default.py`, `sitemap/{_base,asgi,cached,core,dynamic,native,static}.py`, `style/{_base,kelp,vanilla}.py`.
- Modify: `fastblocks/adapters/templates/{_advanced_manager,_async_filters,_async_renderer,_base,_block_renderer,_enhanced_cache,_htmy_components,_language_server,htmy,jinja2}.py`.
- Modify or create: matching tests under `tests/adapters/{auth,fonts,icons,images,routes,sitemap,style,styles,templates}`, `tests/test_filesystem_loader.py`, and template performance tests.

### MCP, middleware, and WebSocket domain

- Modify: `fastblocks/mcp/{server,tools,cli,config_audit,config_health,config_migration,configuration,discovery,env_manager,health,registry}.py`, `fastblocks/middleware.py`, `fastblocks/websocket/{server,origin,auth,binding,tls_config}.py`.
- Modify or create: `tests/mcp`, `tests/websocket`, `tests/test_middleware*.py`, `tests/test_websocket_auth.py`, `tests/test_websocket_server.py`, and focused MCP initialization/diagnostic tests.

______________________________________________________________________

## Task 0: Capture the baseline and establish the Oneiric resolver contract

**Files:**

- Modify: `fastblocks/core/resolver.py:12-25`.
- Modify: `fastblocks/adapters/oneiric_helper.py:15-65`.
- Modify: all production modules listed in the resolver file map as later tasks migrate their calls.
- Create: `tests/core/test_resolver.py`.

**Interfaces:**

- Consumes: `oneiric.core.resolution.Resolver`, `Candidate`, and `Candidate.factory` from Oneiric 0.16.1.

- Produces: `get_resolver()`, `resolve_component()`, and `register_candidate()` contracts used by later tasks.

- [ ] **Step 1: Capture the dirty-tree and Ruff baseline without fixing it.**

Run from `/Users/les/Projects/fastblocks`:

```bash
git status --short
git diff --stat
uv run ruff check --no-fix fastblocks tests
uv run ruff format --check fastblocks tests
```

Record the output outside the source diff. The baseline is evidence only; do not use Ruff's
`fix = true` configuration during diagnosis.

- [ ] **Step 2: Write failing resolver contract tests.**

```python
# tests/core/test_resolver.py
from __future__ import annotations

from oneiric.core.resolution import Candidate

from fastblocks.core.resolver import get_resolver, resolve_component


def test_resolver_is_process_wide() -> None:
    assert get_resolver() is get_resolver()


def test_resolve_component_constructs_candidate_factory() -> None:
    resolver = get_resolver()
    resolver.register(
        Candidate(domain="fastblocks", key="test-component", factory=lambda: {"ok": True})
    )

    result = resolve_component(resolver, "fastblocks", "test-component")

    assert result == {"ok": True}


def test_resolve_component_returns_none_for_missing_candidate() -> None:
    assert resolve_component(get_resolver(), "fastblocks", "missing-component") is None
```

Run:

```bash
uv run pytest --no-cov -n 0 tests/core/test_resolver.py -q
```

Expected red phase: the helper is absent or the current raw `Resolver.resolve()` result is a
`Candidate`, not the concrete component expected by callers.

- [ ] **Step 3: Implement the smallest typed resolution boundary.**

Use `Candidate.factory` rather than nonexistent `get`, `get_sync`, or `set` methods. The
implementation must support synchronous factories and awaitable factories without exposing
`Candidate` objects to application callers:

```python
# fastblocks/core/resolver.py
import inspect
from collections.abc import Awaitable, Callable
from typing import cast

from oneiric.core.resolution import Candidate, Resolver

Factory = Callable[[], object | Awaitable[object]]


def _candidate_value(resolver: Resolver, domain: str, key: str) -> object | Awaitable[object] | None:
    candidate = resolver.resolve(domain, key)
    if candidate is None:
        return None
    if isinstance(candidate.factory, str):
        raise TypeError(f"String factories are not supported for {domain}:{key}")
    return cast(Factory, candidate.factory)()


def resolve_component(resolver: Resolver, domain: str, key: str) -> object | None:
    """Resolve and invoke a synchronous component factory."""
    value = _candidate_value(resolver, domain, key)
    if inspect.isawaitable(value):
        raise TypeError(f"Async factory requires resolve_component_async: {domain}:{key}")
    return value


async def resolve_component_async(
    resolver: Resolver, domain: str, key: str
) -> object | None:
    """Resolve and invoke a synchronous or asynchronous component factory."""
    value = _candidate_value(resolver, domain, key)
    if inspect.isawaitable(value):
        return await cast(Awaitable[object], value)
    return value
```

Use `resolve_component()` only from synchronous callers and `resolve_component_async()` from
async callers. Do not make the synchronous resolver call itself artificially async.

- [ ] **Step 4: Make Candidate registration diagnostic and narrow.**

Replace the current silent `except Exception` in `register_candidate` with explicit Pydantic
validation/value failures, log the traceback through the existing Oneiric logger, and return
`False` only for invalid registration data. A resolver implementation error must propagate.

- [ ] **Step 5: Migrate raw resolver call sites incrementally.**

For every affected call site, replace patterns such as:

```python
component = await depends.resolve("fastblocks", "cache")
styles = depends.get_sync("styles")
depends.set("config", config)
```

with the canonical resolver helper or `register_candidate(...)`. Keep the domain/key pair
explicit. Add a focused test whenever a call site previously relied on a nonexistent method.

Run after each module group:

```bash
uv run ruff check --no-fix fastblocks/core/resolver.py fastblocks/adapters/oneiric_helper.py
uv run pytest --no-cov -n 0 tests/core/test_resolver.py
```

Expected pass signal: no resolver API mismatch is hidden behind a broad catch, and all affected
callers receive a concrete component or an explicit missing-component result.

______________________________________________________________________

## Task 1: Repair stale integration skips and deterministic compatibility rules

**Files:**

- Modify: `tests/test_validation_integration.py`, `tests/test_workflows_integration.py`.
- Modify: `fastblocks/_validation_integration.py`, `_workflows_integration.py`, `_events_integration.py`, `_health_integration.py`.
- Create or modify: `tests/test_integration_contracts.py`.

**Interfaces:**

- Consumes: Task 0's resolver helper and current Oneiric availability flags.

- Produces: executing validation/workflow tests instead of silently skipped ACB suites; explicit integration failure contracts.

- [ ] **Step 1: Replace stale ACB availability imports with current Oneiric flags.**

Use the current FastBlocks integration names (`oneiric_validation_available`,
oneiric_workflows_available`, and the corresponding event/health flags) rather than removed `ACB\_\*\_AVAILABLE\` imports. Do not hide an import failure with a module-level skip.

- [ ] **Step 2: Run the suites to expose the real red phase.**

```bash
uv run pytest --no-cov -n 0 -rs \
  tests/security/test_input_validation.py \
  tests/test_validation_integration.py \
  tests/test_workflows_integration.py
```

Expected red phase: previously hidden resolver/lifecycle failures and the seven known workflow
failures become visible. Fix those failures in the owning source modules, not by reintroducing
skip guards.

- [ ] **Step 3: Add the fail-closed sanitizer regression first.**

```python
def test_sanitizer_failure_rejects_input(monkeypatch) -> None:
    from fastblocks._validation_integration import get_validation_service

    service = get_validation_service()
    assert service._sanitizer is not None

    def broken_sanitizer(_value: str) -> str:
        raise RuntimeError("sanitizer down")

    monkeypatch.setattr(service._sanitizer, "sanitize_html", broken_sanitizer)
    errors: list[str] = []
    value = "<script>alert(1)</script>"

    sanitized = service._sanitize_context_value("body", value, errors)

    assert sanitized != value
    assert errors and "Failed to sanitize body" in errors[0]
```

The test calls the actual service method and must fail before the fix because the current catch
returns the original unsafe value.

- [ ] **Step 4: Replace the fail-open catch with an explicit validation error.**

Add the module logger using the existing Oneiric convention:

```python
from oneiric.core.logging import get_logger

logger = get_logger(__name__)
```

Then change `_sanitize_context_value` as follows:

```python
try:
    return self._sanitizer.sanitize_html(value)
except Exception as exc:
    logger.exception("Input sanitization failed for %s", key)
    errors.append(f"Failed to sanitize {key}: {exc}")
    return ""
```

The empty string is a fail-closed sanitized value; `validate_template_context` already uses the
non-empty `errors` list to determine strict validity. Do not return the original input.

- [ ] **Step 5: Collapse the two nested security `if` statements.**

```python
if prevent_sql_injection and _contains_sql_injection(value):
    issues.append("potential SQL injection")
if prevent_path_traversal and _contains_path_traversal(value):
    issues.append("potential path traversal")
```

Run:

```bash
uv run ruff check --no-fix fastblocks/_validation_integration.py
uv run pytest --no-cov -n 0 tests/security/test_input_validation.py tests/test_validation_integration.py -q
```

- [ ] **Step 6: Pin event delivery and registration honesty.**

Add tests that a failing subscriber is recorded as failed and that failed registration does not
return a successful registration summary:

```python
async def test_publish_reports_failed_subscriber() -> None:
    from fastblocks._events_integration import (
        Event,
        EventPriority,
        EventPublisher,
        EventSubscription,
    )

    class BrokenHandler:
        async def handle(self, _event: Event) -> None:
            raise RuntimeError("subscriber failed")

    publisher = EventPublisher()
    await publisher.subscribe(EventSubscription("demo", BrokenHandler()))
    result = await publisher.publish(
        Event("demo", "test", {}, EventPriority.NORMAL)
    )

    assert result is False
```

Catch arbitrary subscriber failures at this deliberate plugin boundary, log with
`logger.exception`, preserve the handler identity in the diagnostic record, and make the
aggregate publish result false when any required delivery fails. Check registration return
values rather than returning `True` after a failed subscription.

- [ ] **Step 7: Make workflows and health results honest.**

For manual workflows, represent unsupported or failed steps in `step_results` rather than
silently returning success. For health aggregation, preserve successful component statuses and
attach per-component error details when one check fails. Retained broad catches must include a
local `# noqa: BLE001` with the boundary rationale and a diagnostic call.

- [ ] **Step 8: Narrow schema-specific catches.**

Catch Pydantic validation exceptions around `model_validate` and msgspec conversion exceptions
around msgspec calls. Keep outer integration catches only where they translate arbitrary
integration failures into documented result objects.

- [ ] **Step 9: Validate the integration domain.**

```bash
uv run ruff check --no-fix \
  fastblocks/_validation_integration.py fastblocks/_events_integration.py \
  fastblocks/_workflows_integration.py fastblocks/_health_integration.py
uv run pytest --no-cov -n 0 -rs \
  tests/security/test_input_validation.py \
  tests/test_validation_integration.py \
  tests/test_workflows_integration.py \
  tests/test_integration_contracts.py
```

Expected pass signal: the suites execute rather than skip, fail-closed validation is covered,
and delivery/workflow/health results preserve explicit failure state.

______________________________________________________________________

## Task 2: Remediate gather, query, cache, CLI, and core runtime findings

**Files:**

- Modify: `fastblocks/actions/gather/{application,components,middleware,models,routes,strategies,templates}.py`.
- Modify: `fastblocks/actions/query/parser.py`, `fastblocks/applications.py`, `fastblocks/caching.py`, `fastblocks/cli.py`.
- Modify: `fastblocks/core/style_registry.py`, `fastblocks/exceptions.py`, `fastblocks/htmx.py`, `fastblocks/initializers.py`, `fastblocks/main.py`.
- Modify tests under the corresponding `tests/actions`, `tests/core`, and root test modules.

**Interfaces:**

- Consumes: Task 0's resolver contract and Task 1's fail-closed integration behavior.

- Produces: explicit gather/query/cache failure results, correctly bound cache closures, CLI subprocess intent, and narrow import/validation catches.

- [ ] **Step 1: Add a failing closure-binding test for `B023`.**

```python
import asyncio

from starlette.datastructures import Headers, URL


async def test_cache_helpers_bind_each_cache_key(monkeypatch) -> None:
    from fastblocks.caching import _delete_cache_entries

    published: list[str] = []

    async def publish_cache_invalidation(**kwargs) -> None:
        published.append(kwargs["cache_key"])

    async def generate_key(_url, *, method, headers, varying_headers) -> str:
        return f"{method}-key"

    class FakeCache:
        async def delete(self, _key: str) -> None:
            return None

    class FakeLogger:
        def debug(self, _message: str) -> None:
            return None

    monkeypatch.setattr("fastblocks.caching.generate_cache_key", generate_key)
    monkeypatch.setattr(
        "fastblocks.adapters.templates._events_wrapper.publish_cache_invalidation",
        publish_cache_invalidation,
    )

    await _delete_cache_entries(
        URL("https://example.test"),
        Headers(),
        FakeCache(),
        FakeLogger(),
        {},
    )
    await asyncio.sleep(0)

    assert published == ["GET-key", "HEAD-key"]
```

The test must fail before the fix because both scheduled closures can observe the final loop
value; the implementation should bind `cache_key` as a default argument or pass it explicitly.

- [ ] **Step 2: Bind the loop variable at definition time.**

```python
for cache_key in cache_keys:
    def helper(key: str = cache_key) -> str:
        return key
    helpers.append(helper)
```

Prefer passing the key as an explicit factory argument when the surrounding API allows it.

- [ ] **Step 3: Replace bare `raise Exception` with a FastBlocks domain exception.**

Add or use the existing gather exception class in `fastblocks/exceptions.py`, preserve the
original exception with `raise GatherError(message) from exc`, and test that callers receive the
domain exception with the original cause.

- [ ] **Step 4: Narrow gather imports and configured processor lookups.**

For dynamic imports, catch only `ImportError`/`ModuleNotFoundError`, `AttributeError`, and
configuration `ValueError`. Do not use `suppress(Exception)` around resolver access. A broken
processor must be logged or returned as an explicit configuration error, not converted into an
empty processor list.

- [ ] **Step 5: Fix CLI subprocess intent explicitly.**

At `cli.py:137` and `cli.py:1063`, pass `check=False` if the existing CLI contract intentionally
inspects or tolerates nonzero exit codes. If the command must fail the CLI, pass `check=True` and
add a test for the resulting `CalledProcessError`. Do not silence `PLW1510` with a comment.

- [ ] **Step 6: Narrow style registry and parser catches.**

Treat a missing module as absence, but allow syntax errors, dependency failures, constructor
errors, and resolver failures to remain visible. Log retained framework-boundary failures with
`logger.exception` and return the documented structured result.

- [ ] **Step 7: Validate this domain.**

```bash
uv run ruff check --no-fix \
  fastblocks/actions/gather fastblocks/actions/query/parser.py \
  fastblocks/applications.py fastblocks/caching.py fastblocks/cli.py \
  fastblocks/core/style_registry.py fastblocks/exceptions.py \
  fastblocks/htmx.py fastblocks/initializers.py fastblocks/main.py
uv run pytest --no-cov -n 0 \
  tests/actions/gather tests/actions/query \
  tests/test_actions_gather.py tests/test_applications*.py \
  tests/test_caching*.py tests/test_cli*.py \
  tests/test_initializers*.py tests/core/test_style_registry.py
```

Expected pass signal: no reported rules remain in these files and the new closure/import/CLI
regressions are covered.

______________________________________________________________________

## Task 3: Remediate sync actions with batch-safe error semantics

**Files:**

- Modify: `fastblocks/actions/sync/strategies.py`, `cache.py`, `settings.py`, `static.py`, `templates.py`.
- Modify: `tests/actions/sync`, `tests/test_actions_sync.py`.

**Interfaces:**

- Consumes: Task 0's component resolution helper.

- Produces: sync results that preserve per-item errors, narrow internal parsing/IO catches, and do not mask primary failures with cleanup errors.

- [ ] **Step 1: Add failing tests for batch isolation and primary-error preservation.**

```python
async def test_sync_records_one_namespace_failure_and_continues(sync_runner) -> None:
    result = await sync_runner(namespaces=["good", "broken"])

    assert result.completed["good"] is True
    assert result.errors["broken"] == "namespace failed"


async def test_cleanup_does_not_replace_primary_sync_error(sync_runner) -> None:
    result = await sync_runner(fail_during_write=True, fail_during_cleanup=True)

    assert result.primary_error == "write failed"
    assert result.cleanup_errors == ["cleanup failed"]
```

Use the existing result model and storage/cache fakes; the key assertions must fail before
structured error retention is implemented.

- [ ] **Step 2: Collapse the two nested `SIM102` guards in `strategies.py`.**

```python
if check_missing and path not in existing:
    missing.append(path)
```

Preserve the existing fail-fast/collect-errors strategy flag.

- [ ] **Step 3: Narrow parsing and filesystem catches.**

Use `OSError`, `UnicodeError`, `json.JSONDecodeError`, `yaml.YAMLError`, `ValueError`, and
schema-specific exceptions only where those operations can raise them. Let programming errors
reach the outer sync boundary.

- [ ] **Step 4: Preserve per-item batch errors.**

For independent namespace/file loops, retain the broad catch only if the result records the
namespace or path and the exception. Add `logger.exception("Sync item failed: %s", item)` before
continuing. The retained catch gets a local `# noqa: BLE001` explaining pluggable storage/cache
implementations.

- [ ] **Step 5: Separate backup, transfer, local-write, and cache failures.**

Do not let backup or cache cleanup overwrite the primary transfer/write error. Use a `try/finally`
for task bookkeeping and attach secondary failures to the existing result object.

- [ ] **Step 6: Validate the sync domain.**

```bash
uv run ruff check --no-fix fastblocks/actions/sync
uv run pytest --no-cov -n 0 tests/actions/sync tests/test_actions_sync.py
```

Expected pass signal: all 69 originally reported sync handlers are either narrowed or justified,
and per-item failures remain observable.

______________________________________________________________________

## Task 4: Remediate adapters and template rendering boundaries

**Files:**

- Modify: all adapter files in the adapter file map, especially `adapters/oneiric_helper.py`,
  `auth/_base.py`, fonts, icons, images, routes, sitemap, style, and template modules.
- Modify or create: focused adapter/template tests listed in the file map.

**Interfaces:**

- Consumes: Task 0 resolver helpers and Task 3's explicit batch error contract.

- Produces: per-instance settings defaults, safe auth context state, loader/render distinction,
  cleanup-safe template behavior, and justified retained renderer boundaries.

- [ ] **Step 1: Add failing mutable-default and `ContextVar` tests.**

```python
from pydantic import SecretStr


def test_font_settings_lists_are_not_shared() -> None:
    first = GoogleFontsSettings()
    second = GoogleFontsSettings()
    first.font_weights.append("900")

    assert "900" not in second.font_weights


def test_auth_current_user_default_is_not_shared() -> None:
    first = AuthBase(SecretStr("secret"), object)
    second = AuthBase(SecretStr("secret"), object)

    assert first.current_user is not second.current_user
```

The first test must fail before replacing the Pydantic defaults because the appended weight leaks into
`second.font_weights`. The second test must fail before replacing the `ContextVar` default because
both `AuthBase` instances return the same `UnauthenticatedUser` object.

- [ ] **Step 2: Convert RUF012 settings defaults to `Field(default_factory=...)`.**

```python
font_weights: list[str] = Field(default_factory=lambda: ["400", "700"])
```

Apply this to all reported mutable class attributes in fonts, icons, images, sitemap, style,
templates, and `core/patterns.py` settings/model classes. Preserve exact default values.

- [ ] **Step 3: Replace the mutable auth `ContextVar` default with a sentinel.**

```python
_current_user: ContextVar[UnauthenticatedUser | None] = ContextVar(
    "current_user", default=None
)

@property
def current_user(self) -> UnauthenticatedUser:
    value = self._current_user.get()
    return value if value is not None else UnauthenticatedUser()
```

Ensure callers that set the context receive the same request-scoped object while absent context
gets a fresh default.

- [ ] **Step 4: Preserve renderer error meaning.**

`safe_await()` must not return `True` when the callable raises. Return the actual result or a
failure representation consistent with its caller. Validation failures should remain distinct
from validator implementation failures. Add tests for a raised `RuntimeError` and a genuine
invalid-template result.

- [ ] **Step 5: Distinguish loader absence from implementation failure.**

In `jinja2.py`, continue only on `TemplateNotFound`. Let loader syntax, permission, backend, and
programming failures propagate to the renderer boundary. In style registry and template adapter
resolution, catch only missing-module/attribute cases internally.

- [ ] **Step 6: Make cleanup and background-loop failures observable.**

Preserve the primary template load/compile exception if temporary-file cleanup fails. Keep
`asyncio.CancelledError` explicit in shutdown paths. For maintenance/warming loops, log failures
and update an existing health/metrics counter; ensure `task_done()` remains balanced.

- [ ] **Step 7: Preserve the intentional HTMY `exec` site.**

Do not remove the AST safety walk or its `# noqa: S102` annotation. Add no new dynamic import
mechanism. If `TRY203` remains at the deliberate re-raise, use a narrow local annotation and a
comment explaining why the original `SyntaxError` must propagate.

- [ ] **Step 8: Validate adapter/template behavior and exports.**

```bash
uv run ruff check --no-fix fastblocks/adapters
uv run pytest --no-cov -n 0 \
  tests/adapters/auth tests/adapters/fonts tests/adapters/icons \
  tests/adapters/images tests/adapters/routes tests/adapters/sitemap \
  tests/adapters/style tests/adapters/styles tests/adapters/templates \
  tests/test_filesystem_loader.py
uv run python - <<'PY'
import fastblocks.adapters.templates as templates
from jinja2_async_environment.loaders import (
    AsyncBaseLoader, LoaderNotFound, PackageLoaderError,
    PackageSpecNotFound, SourceType,
)
assert all(hasattr(templates, name) for name in templates.__all__)
assert all((AsyncBaseLoader, LoaderNotFound, PackageLoaderError,
            PackageSpecNotFound, SourceType))
PY
```

Expected pass signal: all mutable defaults are isolated, failures are not fabricated as success,
and the public template API remains intact.

______________________________________________________________________

## Task 5: Remediate MCP, middleware, and WebSocket rules and boundaries

**Files:**

- Modify: `fastblocks/mcp/{server,tools,cli,config_audit,config_health,config_migration,configuration,discovery,env_manager,health,registry}.py`.
- Modify: `fastblocks/middleware.py`, `fastblocks/websocket/{server,origin,auth,binding,tls_config}.py`.
- Create or modify: `tests/mcp/test_initialization_completeness.py`,
  `tests/mcp/test_dt005_timezone.py`, `tests/mcp/test_ble001_narrowed.py`,
  `tests/mcp/test_health_periodic_retry_logs.py`,
  `tests/websocket/test_server_exception_logging.py`.

**Interfaces:**

- Consumes: Task 0 resolver boundary and Task 1 explicit initialization/failure contracts.

- Produces: honest MCP initialization, structured tool errors, narrow config parsing, explicit
  timezone values, and diagnostic WebSocket exception handling.

- [ ] **Step 1: Add the MCP initialization failure test.**

```python
async def test_initialize_does_not_hide_registration_failure(monkeypatch) -> None:
    from fastblocks.mcp.server import FastBlocksMCPServer

    server = FastBlocksMCPServer()

    async def broken_registration() -> None:
        raise RuntimeError("registration failed")

    monkeypatch.setattr(server, "_register_tools", broken_registration)

    with pytest.raises(RuntimeError, match="registration failed"):
        await server.initialize()

    assert server._initialized is False
```

The test targets `FastBlocksMCPServer._register_tools`; it must fail before the inner
`with suppress(Exception)` in `_register_tools` is removed.

- [ ] **Step 2: Remove redundant exception objects from `logger.exception`.**

Change:

```python
logger.exception("tool failed: %s", exc)
```

to:

```python
logger.exception("tool failed")
```

Apply to all reported `TRY401` sites in `mcp/tools.py`, `adapters/app/default.py`, and
`websocket/server.py`, preserving any useful non-exception context in the message.

- [ ] **Step 3: Narrow config parsing and backup metadata catches.**

Use explicit exception tuples for JSON/YAML loads, serialization, schema validation, and
filesystem reads. The corrupted-backup loop may continue, but it must log the filename and
exception before continuing.

- [ ] **Step 4: Fix deterministic MCP rules.**

Apply `SIM102`, `B005`, `PLC0206`, `DTZ005`, `D205`, and related reported rules with actual
semantic-preserving code. For `datetime.now()`, import `UTC` and use `datetime.now(UTC)`; for
`fromtimestamp`, use `datetime.fromtimestamp(value, UTC)` and update both sides of freshness
comparisons consistently.

- [ ] **Step 5: Preserve structured protocol responses.**

MCP tool boundaries may catch arbitrary tool implementation failures, but must return the
existing serializable error schema and log a traceback. Do not turn validator implementation
failures into ordinary invalid-input responses without preserving the distinction internally.

- [ ] **Step 6: Add WebSocket diagnostic tests.**

```python
async def test_websocket_handler_logs_exception(caplog, websocket_server) -> None:
    with caplog.at_level("ERROR"):
        await websocket_server.handle_message(make_failing_message())

    assert "websocket message handling failed" in caplog.text.lower()
```

Use the repository logger capture fixture and actual message/server helpers. Keep origin URL
return types boolean and test malformed origin handling explicitly.

- [ ] **Step 7: Validate MCP/WebSocket.**

```bash
uv run ruff check --no-fix \
  fastblocks/mcp fastblocks/middleware.py fastblocks/websocket
uv run pytest --no-cov -n 0 \
  tests/mcp tests/websocket tests/test_middleware*.py \
  tests/test_websocket_auth.py tests/test_websocket_server.py \
  tests/unit/test_websocket_auth.py
```

Expected pass signal: MCP initialization failures are visible, tool failures remain structured,
and WebSocket exceptions are logged without redundant exception formatting.

______________________________________________________________________

## Task 6: Complete the BLE001 inventory and add justified boundary annotations

**Files:**

- Modify: the production paths listed in the Step 1 JSON report after Tasks 0–5; no path outside that report may be changed by this task.
- Modify: a focused test file for each retained broad boundary that lacks a contract test.

**Interfaces:**

- Consumes: all previous domain contracts.

- Produces: zero unclassified `BLE001` findings and a reviewable boundary inventory.

- [ ] **Step 1: Re-run Ruff and generate the authoritative remaining inventory.**

```bash
uv run ruff check --no-fix --output-format=json fastblocks tests > /tmp/fastblocks-ruff.json
```

Group every remaining `BLE001` by file and surrounding function. The original reported groups
are:

| Domain | Files | Original broad-handler group |
|---|---|---:|
| Integrations | `_events_integration.py`, `_health_integration.py`, `_validation_integration.py`, `_workflows_integration.py` | 35 |
| Gather/query/runtime | `actions/gather/*.py`, `actions/query/parser.py`, `applications.py`, `caching.py`, `cli.py`, `core/style_registry.py`, `exceptions.py`, `htmx.py`, `initializers.py`, `main.py` | 47+ |
| Sync | `actions/sync/{cache,settings,static,strategies,templates}.py` | 69 |
| Templates/adapters | `adapters/templates/*.py`, adapter families, `oneiric_helper.py` | 52+ |
| MCP/WebSocket | `mcp/*.py`, `middleware.py`, `websocket/*.py` | 40+ |

The post-resolver Ruff output is authoritative because resolver migration may remove or expose
handlers differently.

- [ ] **Step 2: Narrow every internal catch.**

For each parser/import/filesystem/schema/resolver site, replace `except Exception` with the
smallest tested exception tuple. Add a test that an unexpected `RuntimeError` is not swallowed
where the code is internal.

- [ ] **Step 3: Justify every retained boundary locally.**

A retained handler must follow this exact shape, adapted to its existing result type:

```python
except Exception as exc:  # noqa: BLE001 - third-party callback boundary
    logger.exception("Callback failed: %s", callback_name)
    errors.append(CallbackError(name=callback_name, cause=exc))
```

If the existing API cannot preserve diagnostics, change the result object or log format before
adding the annotation. Never add a bare `# noqa` without the boundary explanation.

- [ ] **Step 4: Review silent `continue` sites.**

For `S112` in Cloudflare, TwicPics, Jinja2 loader, and MCP configuration, keep processing the
remaining items only after logging the item identity and exception. Confirm cancellation is not
caught by the broad handler.

- [ ] **Step 5: Confirm no global suppression was added.**

```bash
rg -n 'BLE001|per-file-ignores|ignore\s*=|extend-ignore' pyproject.toml fastblocks | head -200
```

Expected: only local, justified annotations and no project-wide/per-file BLE001 suppression.

______________________________________________________________________

## Task 7: Run final wiring, orphan, and quality gates

**Files:**

- Modify only files required by failing verification.
- Do not modify the approved design document except to record a factual implementation outcome
  after the user requests it.

**Interfaces:**

- Consumes: all source/test changes from Tasks 0–6.

- Produces: verified lint-clean, test-validated FastBlocks remediation with explicit failure
  evidence.

- [ ] **Step 1: Run changed-file Ruff and format checks.**

```bash
uv run ruff check --no-fix fastblocks tests
uv run ruff format --check fastblocks tests
```

Expected: no Ruff diagnostics and no formatting drift.

- [ ] **Step 2: Run all focused domain suites together.**

```bash
uv run pytest --no-cov -n 0 \
  tests/core/test_resolver.py \
  tests/security/test_input_validation.py \
  tests/test_validation_integration.py \
  tests/test_workflows_integration.py \
  tests/actions/gather tests/actions/query tests/actions/sync \
  tests/adapters/auth tests/adapters/fonts tests/adapters/icons \
  tests/adapters/images tests/adapters/routes tests/adapters/sitemap \
  tests/adapters/style tests/adapters/styles tests/adapters/templates \
  tests/mcp tests/websocket
```

Expected: pass, with skips only where documented by existing optional-dependency policy. Stale
ACB skip conditions are not acceptable.

- [ ] **Step 3: Run the public API smoke checks.**

```bash
uv run python - <<'PY'
import fastblocks.adapters.templates as templates
from jinja2_async_environment.loaders import (
    AsyncBaseLoader, LoaderNotFound, PackageLoaderError,
    PackageSpecNotFound, SourceType,
)
assert all(hasattr(templates, name) for name in templates.__all__)
assert AsyncBaseLoader and LoaderNotFound and PackageLoaderError
assert PackageSpecNotFound and SourceType
PY
```

- [ ] **Step 4: Run the complete repository gates.**

Use the documented commands:

```bash
uv run pytest
uv run crackerjack run
```

If a gate fails, report the exact failing command and output; do not hide it with a rule ignore.

- [ ] **Step 5: Run the orphan/wiring audit.**

```bash
cd /Users/les/Projects/mahavishnu
python scripts/audit_orphans.py
```

For FastBlocks changes, verify that newly introduced resolver helpers, diagnostic result fields,
and test fixtures have callers and are wired into the actual runtime paths. Do not leave a new
helper unused.

- [ ] **Step 6: Compare the final dirty-tree inventory.**

```bash
git -C /Users/les/Projects/fastblocks status --short
git -C /Users/les/Projects/fastblocks diff --name-only
```

Confirm every newly changed path belongs to the file map or is a focused regression test. Leave
unrelated pre-existing modifications untouched.

______________________________________________________________________

## Rule Inventory and Ownership Matrix

The following reported rules are explicitly owned by the tasks above:

| Ruff rule | Ownership | Required treatment |
|---|---|---|
| `BLE001` | Tasks 1–6 | Narrow internals; retain only diagnostic framework boundaries. |
| `SIM102` | Tasks 1–5 | Combine nested guards without changing short-circuit behavior. |
| `DTZ005`, `DTZ006` | Tasks 1 and 5 | Use `UTC`; update both sides of comparisons. |
| `RUF012` | Task 4 | Pydantic `Field(default_factory=...)` with exact defaults. |
| `TRY401` | Tasks 4–5 | Remove redundant exception object from `logger.exception`. |
| `TRY203` | Task 4 | Preserve deliberate original exception propagation with a local rationale. |
| `TRY002` | Task 2 | Use the FastBlocks exception hierarchy and chain the cause. |
| `S102` | Task 4 | Preserve AST-validated HTMY execution and its existing annotation. |
| `S112` | Task 6 | Log failed item identity before continuing; do not catch cancellation. |
| `B018` | Tasks 1–2 | Remove or replace useless expression after confirming intended behavior. |
| `B023` | Task 2 | Bind the loop variable explicitly. |
| `B039` | Task 4 | Replace shared mutable `ContextVar` default with sentinel/fresh value. |
| `B005` | Task 5 | Replace multi-character `.strip()` with explicit operations. |
| `PLW1510` | Task 2 | Pass explicit `check=` matching the existing CLI contract. |
| `PLC0206` | Task 5 | Iterate with `.items()` where both key and value are used. |
| `D205` | Tasks 2 and 5 | Add the required blank line after docstring summaries. |

## Integration Contract

**Triggered from:** `uv run ruff check --no-fix fastblocks tests` and the Crackerjack quality workflow.

**Returns to / updates:** the process-wide Oneiric resolution boundary, affected FastBlocks
runtime modules, structured failure results, and focused regression tests.

**Demonstrable by:** zero requested Ruff findings, executing validation/workflow suites, resolver
contract tests, public API smoke checks, passing targeted tests, and passing full pytest and
Crackerjack gates.

**Rollback signal:** revert a wave if its focused tests show changed fallback behavior, if a
plugin boundary leaks unexpected exceptions, if timestamp/API contracts change without an
explicit compatibility test, or if resolver calls still rely on unsupported Oneiric methods.

**Observability added:** traceback logging at retained broad boundaries, failed-item identity in
batch results, explicit event/initialization/render/validation failure state, and resolver
registration/lookup diagnostics.

## Plan Self-Review

- **Spec coverage:** resolver compatibility, deterministic fixes, exception classification,
  security fail-closed behavior, batch cleanup, public API compatibility, targeted validation,
  full gates, observability, and dirty-tree safety each have explicit tasks.
- **Placeholder scan:** no deferred markers or vague error-handling instructions are present.
- **Type consistency:** Task 0 defines `resolve_component`; all later tasks consume that
  boundary. `register_candidate` remains the registration API and no task introduces a second
  resolver abstraction.
- **Scope check:** the plan is intentionally one coordinated remediation because all domain
  waves depend on the resolver contract and final Ruff inventory. Each task has an independent
  test gate and can be reviewed separately.
