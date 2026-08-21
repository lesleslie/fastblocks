# Changelog

All notable changes to FastBlocks will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.30.0] - Unreleased

### Removed

- **`kelp`, `bulma`, `webawesome`, `custom` style adapters** (`fastblocks.adapters.style.{kelp,webawesome}` and `fastblocks.adapters.app._templates.{kelp,webawesome,bulma,custom}/`). Each carried multiple silent-failure traps — decorator-API misuse, wrong-Resolver-API calls, masked XSS surface — all swallowed by `with suppress(Exception)` at the call sites. `bulma` and `custom` lacked even a backing adapter and fell through to the silent no-op default. After upgrade, `config.app.style = "kelp"` (or `"webawesome"` / `"bulma"` / `"custom"`) fails loudly at startup with `unknown style` from `style_registry.py`. This is the desired behavior for removed APIs.

  **Migration:** set `config.app.style = "fastblocks_ui"` (recommended) or `"vanilla"` (explicit unstyled). User-confirmed zero external consumers of fastblocks, fastblocks-ui, or fastblocks-htmy; no deprecation-cycle intermediate release.

## [0.21.0] - 2026-08-21

### Added

- Add JWT authentication to FastBlocks WebSocket
- Add TLS configuration module for WebSocket
- Add WebSocket server for UI update streams
- fastblocks: Document tool-profile opt-out (W4.9)
- fastblocks: P1 scaffold docs/ CI guard test module
- fastblocks: P2 doc-accuracy CI guard with baseline xfails
- Fix all Oneiric Candidate registrations across adapters
- Integrate TLS/WSS support and Prometheus metrics into Fastblocks WebSocket server
- phase4: Add security scanning infrastructure (Task 4.4 partial)
- ratchet: Mirror fastblocks pyproject.toml to current coverage
- rem: Phases 1-4 — security hardening, ACB→Oneiric, perf bounds, mechanical refactors
- security: Phase 1.1 — strict WebSocket auth + origin allowlist + sanitized errors

### Changed

- Add CLI test skeleton (needs mocking infrastructure)
- Apply automatic formatting from ruff-format and mdformat
- Fastblocks (quality: 71/100) - 2025-11-19 13:24:11
- Fastblocks (quality: 71/100) - 2026-06-18 12:32:36
- Fastblocks (quality: 72/100) - 2026-01-03 00:26:24
- Fastblocks (quality: 72/100) - 2026-06-15 00:34:33
- fastblocks: Add real-bug #8 (SandboxedEnvironment dead attributes) to tally
- fastblocks: Append ty cleanup final report (374 → 0)
- fastblocks: Clean up stale Oneiric import comments and reorder jinja2 imports
- fastblocks: Ty cleanup 374 → 0 — phased by cascade leverage
- fastblocks: Ty cleanup design (374 → 0)
- fastblocks: Use collections.abc Callable instead of typing.Callable in middleware
- phase4-task2: Remove 1 unnecessary async for type ignore (153→152)
- phase4-task2: Remove 17 more unnecessary type ignores (170→153)
- phase4-task2: Remove 20 type ignores using explicit casts (152→132)
- phase4-task2: Remove 53 unnecessary type ignores (223→170)
- Update config, deps
- Update core functionality

### Fixed

- adapters: Add missing get_stylesheet_links to IconsBase and fix font test
- Add acb.console mock to enable CLI tests
- Align fastblocks [tool.coverage.report].fail_under with ratchet
- Align fastblocks ratchet with pyproject mirror (49.13%)
- Async/await improvements - event-based wait and proper task gathering
- Correct Oneiric Candidate registration for Templates adapter
- Correct performance test mock setup and method calls
- fastblocks: 3 bucket-B real bugs from ty deferred-minors
- fastblocks: Align dependency resolver contract
- fastblocks: Align PROFILE_REGISTRATIONS keys with real ToolProfile enum (M1)
- fastblocks: Cast Oneiric candidate.factory to Callable[..., Any]
- fastblocks: Complete async htmx fallbacks
- fastblocks: Complete ruff remediation plan (Tasks 0-7)
- fastblocks: Correct validation docstrings per reviewer feedback
- fastblocks: Declare framework-injected and singleton-guarded attrs
- fastblocks: Drop redundant attr-defined suppressions on sitemap self.config
- fastblocks: Drop try/except fallback for SandboxedEnvironment import
- fastblocks: Honor ChoiceLoader source contract
- fastblocks: Honor ChoiceLoader source contract
- fastblocks: Htmx duplicate header last-match-wins in _get_header
- fastblocks: Initialize validation sanitizer state
- fastblocks: Map wrong Resolver API calls to correct surface
- fastblocks: Migrate Oneiric 0.13+ sync resolver API + refurb cleanup
- fastblocks: Move oneiric_helper imports to top of file (PEP 8 I001)
- fastblocks: P0 correct WebSocket auth env-var names (silent prod JWT failure)
- fastblocks: P10 doc-accuracy guard live; CHANGELOG entry for remediation wave
- fastblocks: P3 ACB narrative rewrite — README/QWEN/RULES
- fastblocks: P4 docs/ guide ACB narrative rewrite + WebSocket MCP section deletion
- fastblocks: P5 adapter README ACB rewrite + main.py→default.py + reg + count
- fastblocks: P6 CLAUDE.md / CHANGELOG.md / CONTRIBUTING.md accuracy
- fastblocks: P8 remove leaked .backup.json files; add .gitignore pattern
- fastblocks: P9 phantom filename refs in docs/README.md
- fastblocks: Phase 2a - unresolved-reference in gather actions
- fastblocks: Phase 2b - unresolved-import for optional/legacy modules
- fastblocks: Phase 2b-followup - ty ignore syntax for unresolved-imports
- fastblocks: Phase 2c - invalid-argument-type fixes
- fastblocks: Phase 2c-fix - repair broken indentation in _base.py
- fastblocks: Phase 2d - missing-argument fixes
- fastblocks: Phase 2d-followup - missing-argument via ty: ignore
- fastblocks: Phase 2e - invalid-method-override fixes
- fastblocks: Phase 2f - invalid-assignment fixes
- fastblocks: Phase 2g - invalid-return-type fixes
- fastblocks: Phase 2h-batch1 - unresolved-attribute fixes (sync + icons + events)
- fastblocks: Phase 2h-batch2 - unresolved-attribute (templates + core)
- fastblocks: Phase 2i - one-off errors (return-type, not-iterable, etc)
- fastblocks: Remove 4 unused ty: ignore directives
- fastblocks: Remove 6 redundant-cast calls
- fastblocks: Remove dead allowed_tags/allowed_attributes setters on SandboxedEnvironment
- fastblocks: Replace bare type:ignore with proper annotations across 5 files
- fastblocks: Replace depends.get with resolve_instance in 3 sites
- fastblocks: Resolve 5 ty/furb findings from rebase
- fastblocks: Resolve final ty/furb findings from rebase merge
- fastblocks: Restore resolve_instance helper for main integration
- fastblocks: Satisfy ty/refurb/mypy in W4.9 tool-profile test
- fastblocks: Scope or remove 33 blanket `# type: ignore` suppressions
- fastblocks: Use single-rule type: ignore on SandboxedEnvironment fallback
- fastblocks: Wire _registration get_global_template_context to resolve_instance
- fastblocks: Wire production call sites to resolve_instance
- Fix async mock issues in component tests
- Fix hardcoded absolute paths in structure tests
- Make depends.resolve() calls async for Oneiric compatibility
- Phase 1 improvements - dead code, unused vars, ACB patterns
- phase2: Add await to depends.get() in actions/gather module
- phase2: Add await to depends.get() in actions/sync module
- phase2: Add await to depends.get() in integration files
- phase2: Correct sitemap/routes to use depends.get_sync() instead of Inject
- phase2: Fix coroutine errors in actions/query/parser.py
- phase2: Fix coroutine errors in adapters/app/default.py
- phase2: Fix coroutine errors in adapters/routes/default.py
- phase2: Fix coroutine errors in cli and template filters
- phase2: Fix coroutine errors in filters and adapter modules
- phase2: Fix coroutine errors in sitemap and admin adapters
- phase2: Fix final coroutine errors in middleware.py
- phase2: Fix remaining coroutine errors in actions module
- phase2: Fix remaining coroutine errors in templates and mcp modules
- phase3: Fix systematic test bugs for quick wins
- phase4: Fix all 10 reportUnnecessaryIsInstance errors (195→182)
- phase4: Fix all 17 reportUndefinedVariable errors (211→195)
- phase4: Fix deprecated/unused/constant errors (10 easy wins)
- phase4: Fix remaining sync depends.get() in MCP and templates
- phase4: Fix sync depends.get() and class names in icon/image adapters
- phase4: Fix sync depends.get() in initializers and template registration
- phase4: Reduce type ignores from 129 to 110 (target <111 achieved)
- phase4: Suppress reportUnusedFunction for template filters (182→142)
- Post-merge cleanup and test fixes
- Resolve test failures for filters and HTMY component discovery
- security,correctness: RCE path, dead middleware, broken cache and MCP surface
- source: Hoist debug shim, SQL/path-traversal detection, MockAsyncPath-safe compile, CliRunner-safe async
- tests: Add async/await to caching test functions
- tests: Update sync_cache mocks for resolve_instance
- tests: Use is_success property instead of success boolean check
- types: AI-fix pass 2 — 175 mypy errors (↓14 from 189)
- Update cache sync tests for Oneiric depends.resolve()
- Update config, core, deps, docs, tests
- Update config, core, deps, docs, tests
- Update config, core, deps, docs, tests
- Update config, core, docs, tests
- Update config, core, tests
- Update deps, tests
- Update filter test to use depends.get_sync()
- Update remaining sync tests for Oneiric depends.resolve()
- validation: Rename _check_sql_injection_in_context parameter 'sanitized' to 'context'

### Documentation

- Add JetBrains plugin iframe for custom delimiter support
- Consolidate and cleanup documentation structure
- fastblocks: Design test recovery plan
- fastblocks: Plan test recovery waves
- fastblocks: Record sanitized test recovery results
- fastblocks: Record test recovery baseline
- fastblocks: Record test recovery baseline
- fastblocks: Record test recovery results
- fastblocks: Use non-self-referential final HEAD label in handoff
- HIGH PRIORITY README audit fixes
- Phase 6 — regen CLAUDE.md, CHANGELOG, AGENTS additions, 0.7→0.8 migration
- phase4: Add type system guidelines and migration guide
- phase4: Complete Task 4.3 documentation updates
- phase4: Complete Task 4.4 Security Hardening
- phase4: Mark Task 4.3 complete in IMPROVEMENT_PLAN
- phase4: Update IMPROVEMENT_PLAN with Phase 4 completion (254→142 errors)
- phase4: Update IMPROVEMENT_PLAN with Task 4.2 completion
- Replace iframe with GitHub-compatible plugin badges
- Simplify README, add Kelp UI, expand HTMY info, update comparisons
- Standardize breadcrumb navigation across all READMEs
- Update config, deps, docs
- Update documentation
- Update improvement plan with Phase 1 progress
- Update IMPROVEMENT_PLAN for Phase 3 start
- Update IMPROVEMENT_PLAN for Phase 3 start
- Update IMPROVEMENT_PLAN with Phase 2 completion
- Update IMPROVEMENT_PLAN with Phase 2 progress
- Update IMPROVEMENT_PLAN.md - Phase 3 completed (33% coverage achieved)
- Update MEDIUM PRIORITY adapter READMEs
- Update, cleanup, and consolidate test documentation

### Testing

- Add ACB depends registry cleanup fixture
- Add comprehensive tests for actions sync modules (85 tests)
- Add comprehensive tests for MCP configuration and tools modules
- Comprehensive test suite improvements and enhancements
- coverage: Add comprehensive query parser tests (0% → 43%)
- Drop stale acb imports, fix MockAsyncPath async-iter, refresh CLI structure assertion
- fastblocks: Align CLI resolver and validation fixtures
- fastblocks: Align SQLAdmin init with sync Oneiric resolver
- fastblocks: Expose AsyncRedisBytecodeCache on mocked top-level jinja2_async_environment
- fastblocks: Isolate security async lifecycle
- fastblocks: Return real values from template filters
- fastblocks: Sync resolver mocks in test_components no-adapter paths
- Fix 36 pre-existing failures (98→64, +53 passing)
- htmy: Add comprehensive registry and templates tests
- templates: Enhance jinja2 template adapter tests

### Internal

- Bump version to 0.18.1
- Bump version to 0.18.2
- Bump version to 0.18.3
- Bump version to 0.18.4
- Bump version to 0.18.5
- Bump version to 0.18.6
- Bump version to 0.18.7
- Bump version to 0.19.0
- Bump version to 0.20.0
- deps: Phase 5 — ~= pins, drop unused session-buddy
- deps: Resolve fastblocks-ui from PyPI
- fastblocks: Add .betterleaks.toml to silence hook false positives
- fastblocks: Gitignore runtime scan artifacts and resolver cache staging
- gitignore: Add backup file patterns to silence checkpoint tool artifacts
- Untrack and delete 1 historical *.backup/*.bak files
- Update LICENSE copyright to 2026, standardize license field

## [Unreleased] - 2026-08-19

### Documentation Remediation Wave

Remediated all ~75 findings from the 2026-08-19 four-agent doc audit.
Full plan at `docs/superpowers/plans/2026-08-19-fastblocks-doc-remediation.md`.

Critical safety:

- `WEBSOCKET_GUIDE.md:398` env-var names corrected (silent prod JWT
  failure risk closed).

ACB → Oneiric narrative rewritten across top-level docs (README, QWEN,
RULES), 8 user-facing guides (ONEIRIC_GUIDE, ONEIRIC_DEPENDS_PATTERNS,
GETTING_STARTED, ARCHITECTURE, COMPARISONS, SECURITY, NOTES,
LESSONS_LEARNED), and 12 adapter READMEs. ~50 `from acb.*` import
blocks replaced with verified Oneiric equivalents.

CI guard added at `tests/docs/test_doc_accuracy.py` with 30 assertions
covering: ACB import prohibitions, fabricated CLI/MCP tool names,
phantom ports, phantom filenames, env-var parity, coverage target
parity, and `.backup.json` leak detection. Word-boundary regex
prevents substring false-positives (e.g. `broadcast_ui_update` does
not match `broadcast_ui_updated`).

Other fixes: 7 small accuracy fixes in CLAUDE.md / CHANGELOG.md /
CONTRIBUTING.md; 4 phantom WS env-vars removed from WEBSOCKET_GUIDE.md
(source had no references); 16 `.backup.json` files removed from git
history; `.gitignore` updated with `*.backup.json` and `*.bak` patterns;
3 phantom filename references replaced in `docs/README.md`; 4 stale
coverage %s aligned with the 49.13% pyproject floor.

CHANGELOG.md, `docs/TYPE_SYSTEM_MIGRATION.md`, and `docs/LESSONS_LEARNED.md`
are exempted from the coverage and prohibited-import scans because they
are historical records documenting past code. User-authorized 2026-08-19.

## [0.20.0] - 2026-06-18

### Added

- Add JWT authentication to FastBlocks WebSocket
- Add TLS configuration module for WebSocket
- Add WebSocket server for UI update streams
- Integrate TLS/WSS support and Prometheus metrics into Fastblocks WebSocket server
- rem: Phases 1-4 — security hardening, ACB→Oneiric, perf bounds, mechanical refactors
- security: Phase 1.1 — strict WebSocket auth + origin allowlist + sanitized errors

### Changed

- Fastblocks (quality: 71/100) - 2026-06-18 12:32:36
- Fastblocks (quality: 72/100) - 2026-06-15 00:34:33

### Fixed

- types: AI-fix pass 2 — 175 mypy errors (↓14 from 189)

### Documentation

- Phase 6 — regen CLAUDE.md, CHANGELOG, AGENTS additions, 0.7→0.8 migration

### Testing

- Fix 36 pre-existing failures (98→64, +53 passing)

### Internal

- deps: Phase 5 — ~= pins, drop unused session-buddy
- gitignore: Add backup file patterns to silence checkpoint tool artifacts
- Untrack and delete 1 historical *.backup/*.bak files
- Update LICENSE copyright to 2026, standardize license field

## [Unreleased]

### BREAKING CHANGES

- **ACB → Oneiric migration complete.** FastBlocks no longer depends on ACB. The
  `acb` extra (`[dependency-groups].cache`) has been removed from `pyproject.toml`.
  The four integration modules (`_events_integration`, `_health_integration`,
  `_validation_integration`, `_workflows_integration`) now share a single
  process-wide Oneiric resolver via `fastblocks.core.resolver.get_resolver()`. The
  per-module `Resolver()` instantiation is gone. Imports of
  `from oneiric.core.resolution import Resolver` from inside those modules have
  been replaced with `from fastblocks.core.resolver import get_resolver`. If
  your code imported ACB types (`Depends`, `Inject`, `depends.get`, etc.) and
  re-exported them, those names are no longer available — see
  `docs/migrations/0.7-to-0.8.md` for the Oneiric equivalents.

- **HTMY component loader: `exec_module` RCE path removed.** The
  `_load_component_from_source` function in
  `fastblocks/adapters/templates/_htmy_components.py` now uses `ast.parse` plus
  a class walker. Modules that import anything other than class / function
  definitions, or that call `exec` / `eval` / `compile` / `__import__` at
  top level, are rejected at load time. If you shipped a component that relied
  on import-time side effects, refactor it to a class body.

- **`fastblocks.mcp.websocket_tools` is being removed** **Removed in 0.8.0**. The
  seven WebSocket control tools (`fastblocks_start_websocket`,
  `fastbands_stop_websocket`, `fastblocks_broadcast_ui`, etc.) are product
  operations and belong in a consumer app's MCP server, not in the framework.
  Use the underlying Python API (`from fastblocks.websocket import FastblocksWebSocketServer`) directly until the 0.8.0 deletion.

- **`fastblocks.mcp.config_cli` Click wizard is being removed** (slated for
  0.8.0). The wizard is interactive, wrong-shaped for an MCP server, and the
  underlying `ConfigurationManager` / `ConfigurationAuditor` / `EnvironmentManager`
  Python APIs are unchanged.

- **`fastblocks.mcp.tools.create_template` and `fastblocks.mcp.tools.create_component`
  MCP wrappers are being removed** **Removed in 0.8.0**. The underlying Python
  APIs in `fastblocks/adapters/templates/_htmy_components.py` and the CLI
  commands (`fastblocks create template`, `fastblocks create app`) stay.

- **MCP `configure_adapter` tool removed **Removed in 0.8.0**.** The replacement
  is the typed Python API `AdapterRegistry.configure(adapter_name: str, **fields: Any)`,
  which rejects unknown field names against the per-adapter settings schema.

#### WebSocket Auth (Phase 1.1)

- `FASTBLOCKS_JWT_SECRET` is now required at startup in non-test processes. A
  missing or default (`"dev-secret-change-in-production"`) secret raises at
  server startup instead of silently accepting connections.
- `FASTBLOCKS_AUTH_ENABLED` defaults to `true`. Explicitly set to `false` only
  in local development; the old default of `false` was removed.
- WebSocket server requires explicit allowed origins via
  `FASTBLOCKS_WS_ALLOWED_ORIGINS` (comma-separated). An empty value means no
  external origin is permitted.

### Added

- **`fastblocks.core.resolver.get_resolver()`** — the canonical shared Oneiric
  Resolver. Use this in any new code that needs to resolve adapters; do not
  import `oneiric.core.resolution.Resolver` directly inside `fastblocks/`.

- **`fastblocks.core.patterns.SingletonMeta`** — a thread-safe singleton
  metaclass. Use it for any new stateful integration class instead of rolling a
  new `_instance` + `__new__` + `hasattr` guard.

- **`tests/mcp/test_ci_guard.py`** — CI guard that fails the build if any
  deleted symbol name reappears (e.g. `from fastblocks.mcp.websocket_tools import ...`, `@mcp.tool()` named `fastblocks_start_websocket`).

- **`fastblocks/websocket/binding.py`** — `BindAddress` enum (loopback /
  private-LAN) for the WebSocket host allowlist. WebSocket startup that binds
  to `0.0.0.0` / `::` without an explicit capability token is rejected.

- **Security headers default-on** (`Content-Security-Policy`,
  `X-Frame-Options`, `X-Content-Type-Options`, CSRF). Moved from deployed-only
  to default-on with a `security_headers_strict: bool` setting.

- **Basic auth rate-limit + lockout** in `fastblocks/adapters/auth/basic.py`.
  Token-bucket rate limiter (10 attempts / 5 min / username) + account lockout
  (25 consecutive failures). Username-format check `^[A-Za-z0-9_.-]{1,64}$`;
  password format enforced via `mcp_common.security.api_keys.APIKeyValidator`.

- **Sanitized WebSocket error responses.** The server no longer echoes
  `str(e)` of an internal exception back to the client. A stable
  `INTERNAL_ERROR` code is returned; the original exception is logged
  server-side.

- **CLI subcommands.** `create` is now three Typer subcommands:
  `create_app(app_name, style, domain)`, `create_template(style)`,
  `create_ide_config(output_dir, ide)`. The grammar strings for Vim and
  Emacs are now in `fastblocks/cli/grammars/{vim.vim, emacs.el}` instead of
  inlined in `cli.py`.

### Changed

- **Dependencies pinned with `~=` (compatible release)** for 18 runtime deps
  (`anyio`, `brotli-asgi`, `granian[reload]`, `htmy[lxml]`, `mcp-common`,
  `minify-html`, `oneiric`, `pydantic`, `pyfiglet`, `rcssmin`, `rjsmin`,
  `secure`, `starception`, `starlette`, `starlette-async-jinja`,
  `starlette-csrf`, `typer`, `uvicorn`). The same convention is applied to
  the test / dev side. **`sentry-sdk[starlette]` is the only `>=` pin**
  in the runtime graph — its only published 3.x line is the prerelease
  `3.0.0a7`.

- **Dropped `session-buddy>=0.9.4`** from the dev dependency group. It had
  zero importers in the tree.

- **`Pydantic SQLIdentifier` validator** replaces the substring SQL-injection
  detector in `_validation_integration.py`. The previous 22-string substring
  matcher was fail-open; the new validator is fail-closed (rejects single-token
  inputs that don't match `^[A-Za-z_][A-Za-z0-9_]*$`).

- **Oneiric resolver singleton** — the 4 integration modules no longer each
  instantiate their own `Resolver()`. See "BREAKING CHANGES" above.

- **Logger migration: `oneiric.core.logging.get_logger`** is now used in
  `fastblocks/websocket/server.py`, `fastblocks/websocket/auth.py`,
  `fastblocks/websocket/tls_config.py`, `fastblocks/shell/adapter.py`,
  `fastblocks/mcp/server.py`, `fastblocks/mcp/tools.py`,
  `fastblocks/mcp/websocket_tools.py`, `fastblocks/mcp/resources.py`,
  `fastblocks/mcp/__main__.py`. Stdlib `logging.getLogger` is no longer used in
  production code; new code should not introduce it.

- **`fastblocks/htmx.py` async refactor.** Three inlined
  `try: asyncio.create_task(...) except RuntimeError: ...` blocks collapsed
  to single-line `_run_async_safely(coro)` calls. Per-thread event loop cached
  via `threading.local()`. New `run_async_native(coro)` async variant for
  callers already in an async context.

- **`ComponentLifecycleManager.set_component_state`** now retains the spawned
  hook task in `self._in_flight: set[asyncio.Task]` to prevent fire-and-forget
  GC. New `async set_component_state_async(...)` and `async drain_in_flight()`
  for callers that want to await hook completion.

- **`PerformanceOptimizer.template_stats`** is now bounded. The old
  `defaultdict(list)` grew unboundedly per template; it is now an `OrderedDict`
  (global LRU over templates) + `collections.deque(maxlen=1024)` per template.
  Eviction count is exposed as the `evictions_total` property.

- **`jinja2.get_loader()`** now uses a module-level
  `@lru_cache(maxsize=16) _build_cached_loader`. The `FileSystemLoader` has
  a read-through cache `@lru_cache(maxsize=1000) _read_through(path, mtime)`
  and explicit `invalidate(path)` / `invalidate_all()` classmethods. The
  previous code wrote the template back to remote storage on every read
  (write amplification); that is now gone.

- **Workflow executor dedup.** `execute_cache_warming`,
  `execute_template_cleanup`, `execute_performance_optimization` are folded
  into a single `execute_optimization(target: Literal["cache", "templates", "performance"], flags: dict[str, bool])` plus three thin wrappers. Seven
  placeholder action handlers now raise `NotImplementedError` so the workflow
  reports failure rather than silently returning `{"status": "skipped"}`.

### Fixed

- **Test-collection errors reduced from 19 to 8** in `pytest -m "not slow"`,
  driven by the Phase 5 lockfile cleanup (the dead `session-buddy` and
  other stale transitive deps were causing conftest `mcp_common.websocket`
  stubs to fail). Total test count: `1201 → 1218 passing`,
  `85 → 79 failing`. Net: +17 passing, -6 failing, -11 collection errors.

- **Mypy no-implicit-optional** in module headers. `from __future__ import annotations` added to `_validation_integration.py`,
  `_workflows_integration.py`, `caching.py`, `cli.py`. `Optional[X]` →
  `X | None` in `_htmy_components.py:165`.

- **Coverage ratchet +1.47%** on the targeted modules
  that received new tests in Phases 1-4.

- **Security test consolidation (Phase 2.4).** XSS, SQL injection, and
  path-traversal payload sets are now the single source of truth in
  `tests/security/test_input_validation.py`. Duplicate checks in
  `tests/test_validation_integration.py` (`TestSecurityFeatures`,
  `TestTemplateContextValidation`, `TestFormInputValidation`,
  `TestAPIValidation`) are annotated with `# TODO: Duplicate of tests/security/test_input_validation.py` and will be removed in the
  next consolidation pass.

### Removed

- `acb>=0.31.12` from `[dependency-groups].cache` (the group is now empty
  and was removed entirely).
- `session-buddy>=0.9.4` from the dev dependency group (no importers).
- `t.cast(t.Coroutine[...], result); asyncio.run(coro)` sync→async trampolines
  in `caching.py` (already gone in an earlier commit; the plan text was
  based on stale state).
- Inline Vim / Emacs grammar strings from `cli.py` (now in
  `fastblocks/cli/grammars/`).
- The naive 22-string SQL-injection substring detector in
  `_validation_integration.py:485` (replaced by `SQLIdentifier` validator).

## [0.18.7] - 2025-12-19

### Changed

- Update deps, tests

## [0.18.6] - 2025-12-12

### Changed

- Update config, deps

## [0.18.5] - 2025-12-12

### Changed

- Update config, deps, docs

## [0.18.4] - 2025-12-09

### Changed

- Update config, core, deps, docs, tests

## [0.18.3] - 2025-11-26

### Changed

- Update config, core, deps, docs, tests

## [0.18.2] - 2025-11-19

### Changed

- Fastblocks (quality: 71/100) - 2025-11-19 13:24:11
- Update config, core, deps, docs, tests

## [0.18.1] - 2025-11-19

### Added

- Integrate ACB hash actions for 50x performance improvement
- phase4: Add security scanning infrastructure (Task 4.4 partial)

### Changed

- Add CLI test skeleton (needs mocking infrastructure)
- Apply automatic formatting from ruff-format and mdformat
- phase4-task2: Remove 1 unnecessary async for type ignore (153→152)
- phase4-task2: Remove 17 more unnecessary type ignores (170→153)
- phase4-task2: Remove 20 type ignores using explicit casts (152→132)
- phase4-task2: Remove 53 unnecessary type ignores (223→170)
- Update config, core, deps, docs, tests
- Update config, core, docs, tests
- Update documentation

### Fixed

- adapters: Add missing get_stylesheet_links to IconsBase and fix font test
- Add acb.console mock to enable CLI tests
- Async/await improvements - event-based wait and proper task gathering
- docs: Update 26 files
- Fix async mock issues in component tests
- Fix hardcoded absolute paths in structure tests
- Phase 1 improvements - dead code, unused vars, ACB patterns
- phase2: Add await to depends.get() in actions/gather module
- phase2: Add await to depends.get() in actions/sync module
- phase2: Add await to depends.get() in integration files
- phase2: Correct sitemap/routes to use depends.get_sync() instead of Inject
- phase2: Fix coroutine errors in actions/query/parser.py
- phase2: Fix coroutine errors in adapters/app/default.py
- phase2: Fix coroutine errors in adapters/routes/default.py
- phase2: Fix coroutine errors in cli and template filters
- phase2: Fix coroutine errors in filters and adapter modules
- phase2: Fix coroutine errors in sitemap and admin adapters
- phase2: Fix final coroutine errors in middleware.py
- phase2: Fix remaining coroutine errors in actions module
- phase2: Fix remaining coroutine errors in templates and mcp modules
- phase3: Fix systematic test bugs for quick wins
- phase4: Fix all 10 reportUnnecessaryIsInstance errors (195→182)
- phase4: Fix all 17 reportUndefinedVariable errors (211→195)
- phase4: Fix deprecated/unused/constant errors (10 easy wins)
- phase4: Fix remaining sync depends.get() in MCP and templates
- phase4: Fix sync depends.get() and class names in icon/image adapters
- phase4: Fix sync depends.get() in initializers and template registration
- phase4: Reduce type ignores from 129 to 110 (target \<111 achieved)
- phase4: Suppress reportUnusedFunction for template filters (182→142)
- Post-merge cleanup and test fixes
- tests: Add async/await to caching test functions
- tests: Use is_success property instead of success boolean check

### Documentation

- Add JetBrains plugin iframe for custom delimiter support
- Consolidate and cleanup documentation structure
- HIGH PRIORITY README audit fixes
- phase4: Add type system guidelines and migration guide
- phase4: Complete Task 4.3 documentation updates
- phase4: Complete Task 4.4 Security Hardening
- phase4: Mark Task 4.3 complete in IMPROVEMENT_PLAN
- phase4: Update IMPROVEMENT_PLAN with Phase 4 completion (254→142 errors)
- phase4: Update IMPROVEMENT_PLAN with Task 4.2 completion
- Replace iframe with GitHub-compatible plugin badges
- Simplify README, add Kelp UI, expand HTMY info, update comparisons
- Standardize breadcrumb navigation across all READMEs
- Update improvement plan with Phase 1 progress
- Update IMPROVEMENT_PLAN for Phase 3 start
- Update IMPROVEMENT_PLAN for Phase 3 start
- Update IMPROVEMENT_PLAN with Phase 2 completion
- Update IMPROVEMENT_PLAN with Phase 2 progress
- Update IMPROVEMENT_PLAN.md - Phase 3 completed (33% coverage achieved)
- Update MEDIUM PRIORITY adapter READMEs
- Update, cleanup, and consolidate test documentation

### Testing

- Add ACB depends registry cleanup fixture
- Add comprehensive tests for actions sync modules (85 tests)
- Add comprehensive tests for MCP configuration and tools modules
- Comprehensive test suite improvements and enhancements
- coverage: Add comprehensive query parser tests (0% → 43%)
- htmy: Add comprehensive registry and templates tests
- templates: Enhance jinja2 template adapter tests

## [0.17.0] - 2025-01-10

### BREAKING CHANGES

- **Dependency Management Modernization**: Migrated from `[project.optional-dependencies]` to `[dependency-groups]` following PEP 735 and modern UV standards
  - ⚠️ Old syntax `uv add "fastblocks[admin]"` **no longer works**
  - ✅ New syntax: `uv add --group admin`
  - All feature groups (admin, monitoring, sitemap) now use dependency groups
  - Zero self-references - eliminates circular dependency errors
  - Full UV compatibility with modern dependency group standards
  - See MIGRATION-0.17.0.md for upgrade instructions

### Changed

- **Dependency Organization**: Migrated all optional dependencies to dependency groups:
  - Feature groups: admin, monitoring, sitemap
  - Development tools: dev
  - Clear categorization with section headers

### Removed

- `[project.optional-dependencies]` section (replaced by `[dependency-groups]`)

## [0.16.0] - 2025-09-28

### Changed

- Fastblocks (quality: 73/100) - 2025-09-26 08:21:21

### Fixed

- test: Update 55 files

## [0.15.2] - 2025-09-22

### Documentation

- config: Update CHANGELOG, pyproject

## [0.15.1] - 2025-09-21

### Fixed

- test: Update 83 files

## [0.13.2] - 2024-12-15

### Added

- Enhanced null safety in template loaders with robust dependency resolution fallbacks
- Comprehensive uvicorn logging configuration with InterceptHandler integration
- Template reload exclusions in CLI development server configuration
- Improved error handling for ACB adapter registration and retrieval
- Enhanced dependency injection patterns with direct ACB imports
- Lazy loading system for app and logger components with fallback mechanisms

### Changed

- **BREAKING**: Simplified dependency management by using direct ACB imports instead of wrapper system
  - Use `from acb.adapters import import_adapter` instead of internal dependency wrappers
  - Use `from acb.depends import depends` for dependency injection
  - Use `from acb.config import Config` for configuration access
- Improved FastBlocksApp initialization process with streamlined startup
- Enhanced template system with better error handling and null safety
- Updated CLI commands with optimized uvicorn and granian configuration
- Improved middleware stack management with position-based ordering
- Enhanced template loader dependency resolution with fallback mechanisms

### Fixed

- Template loader dependency resolution when ACB adapters are not available
- Null pointer exceptions in template loading when dependencies are missing
- Uvicorn logging conflicts with ACB logging system
- Template reload exclusions for better development experience
- Error handling in adapter registration process
- Dependency injection fallbacks for optional components

### Performance

- Optimized template loader with parallel path checking
- Improved bytecode caching with Redis integration
- Enhanced middleware stack caching and position management
- Reduced startup time with lazy loading for non-critical components

### Developer Experience

- Better error messages for adapter registration failures
- Improved CLI logging configuration for cleaner development output
- Enhanced template reload behavior excluding settings and templates directories
- Comprehensive test coverage for ACB integration changes
- Better documentation for dependency injection patterns

## [0.13.1] - 2024-12-13

### Fixed

- Import errors in middleware module
- Missing type annotations in core modules
- Documentation links and references

## [0.13.0] - 2024-12-10

### Added

- **Direct ACB Imports (v0.13.2+)**: Simplified dependency injection using direct ACB imports
- **Adapter Metadata (v0.14.0+)**: All adapters include static MODULE_ID and MODULE_STATUS for ACB 0.19.0 compliance
- Enhanced middleware system with position-based ordering via MiddlewarePosition enum
- Advanced caching system with rule-based configuration and automatic invalidation
- Cache control middleware for simplified cache header management
- Process time header middleware for request performance monitoring
- Current request middleware for global request access via context variables

### Changed

- **BREAKING**: Dependency injection now uses direct ACB imports instead of wrapper system
- Middleware registration uses position-based system for predictable ordering
- Template system uses modern `Inject[Type]` pattern (ACB 0.25.1+)
- Improved error handling with structured exception hierarchy

### Performance

- 50x faster cache key generation with ACB's CRC32C hashing
- 10x faster content hashing with Blake3
- Enhanced template caching with Redis bytecode cache
- Optimized middleware stack execution

## [0.12.0] - 2024-11-15

### Added

- HTMY component integration alongside Jinja2 templates
- Native HTMX support with HtmxRequest and HtmxResponse classes
- Universal query interface supporting multiple model types
- Sitemap generation with multiple strategies (native, static, dynamic, cached)

### Changed

- Template system now uses `[[` and `]]` delimiters instead of `{{` and `}}`
- Enhanced async template rendering with fragment support

## [0.11.0] - 2024-10-20

### Added

- Initial stable release
- Starlette-based ASGI application framework
- Jinja2 async template system
- ACB integration for dependency injection
- Multiple adapter support (auth, admin, routes, templates)
- Comprehensive CLI for project management
- Built-in middleware stack (CSRF, session, compression, security)

### Features

- Server-side rendering with HTMX focus
- Pluggable adapter architecture
- Multi-database support (SQL and NoSQL)
- Brotli compression and minification
- Type-safe configuration with Pydantic
- Automatic route and component discovery
