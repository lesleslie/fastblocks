# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

FastBlocks is an asynchronous web framework built on Starlette, designed for server-side-rendered HTMX/Jinja template blocks. It is **public, framework-level software** — it is not an end-user product. Production deployments are expected to live in consumer applications (e.g. SplashStand) that import FastBlocks as a library. The framework's MCP surface is read-only introspection of the framework itself; product operations (creating customer sites, broadcasting component updates, configuring adapters) belong in the consumer application, not here.

## Daily Commands

All commands run from the repo root unless noted.

```bash
# Install (dev extras are PEP 735 dependency-groups)
uv sync --group dev

# Run the full suite (xdist is the default — see pyproject.toml [tool.pytest])
uv run pytest

# Run a single test
uv run pytest tests/test_htmx.py::TestHtmxDetails::test_specific -v
uv run pytest tests/adapters/templates/ -k "test_loader"

# Coverage (target 80%; floor 10% with --cov-fail-under)
uv run pytest --cov=fastblocks --cov-report=term-missing
uv run pytest --cov=fastblocks --cov-report=html  # htmlcov/

# Quality gate (this is the CI gate — runs ruff, mypy, pyright, bandit, complexipy,
# vulture, refurb, codespell, pyproject-fmt)
uv run crackerjack run

# Lint only (fast feedback)
uv run ruff check fastblocks tests
uv run ruff format fastblocks tests
uv run mypy fastblocks
uv run pyright fastblocks

# Pre-commit hooks
pre-commit run --all-files
```

## Project Structure (the parts that need context)

```
fastblocks/
├── applications.py        # FastBlocks(Starlette) — the app class
├── main.py                # Lazy app + logger loader (entry point)
├── cli.py                 # Typer CLI; subcommands: create_app, create_template,
│                          #   create_ide_config. Grammar strings live under
│                          #   fastblocks/cli/grammars/ (vim.vim, emacs.el).
├── htmx.py                # HTMX request/response helpers; per-thread event loop
│                          #   via _run_async_safely; do NOT create fresh loops.
├── caching.py             # Cache rules + helpers; uses oneiric.core.logging.
├── middleware.py          # Security headers default-on; Brotli; CSRF.
├── exceptions.py          # ErrorSeverity(str, Enum), ErrorCategory(str, Enum)
│                          #   — both mix in str so str(member) == member.value.
├── _events_integration.py # These 4 underscore-prefixed files share one
├── _health_integration.py # Oneiric resolver via
├── _validation_integration.py  # fastblocks.core.resolver.get_resolver().
├── _workflows_integration.py   # Do not import oneiric.core.resolution.Resolver
│                                directly — go through the shared singleton.
├── actions/               # Stateless utility functions: gather, sync, query,
│                          #   minify. Used by both framework and consumers.
├── adapters/              # Pluggable component system (see below).
│   ├── app/  auth/  admin/  fonts/  icons/  images/  routes/  sitemap/
│   ├── style/             # Kelp CSS adapter (memoized via lru_cache)
│   ├── templates/
│   │   ├── jinja2.py      # Async Jinja2 loader; @lru_cache _build_cached_loader
│   │   │                  #   and FileSystemLoader read-through cache.
│   │   ├── _htmy_components.py  # HTMY component loader; AST.parse class walker
│   │   │                  #   (DO NOT reintroduce exec_module — that was an RCE).
│   │   ├── _performance_optimizer.py  # Bounded LRU; per-template deque(maxlen=1024).
│   │   └── htmy.py
│   └── oneiric_helper.py  # register_candidate() used by all adapters
├── core/
│   ├── patterns.py        # SingletonMeta — thread-safe singleton metaclass.
│   │                      # Use this for any new stateful integration; do not
│   │                      # roll a fresh _instance + __new__ + hasattr guard.
│   └── resolver.py        # get_resolver() returns the process-wide Oneiric
│                          #   Resolver singleton. All 4 _*_integration modules
│                          #   import this; tests should too.
├── mcp/                   # Read-only framework MCP tools (introspection only).
│                          #   - list_adapters, list_templates, validate_template,
│                          #     render_template, list_components, validate_component,
│                          #     check_adapter_health.
│                          #   - Resources: template_syntax, template_filters,
│                          #     htmy_component_catalog, settings_documentation,
│                          #     best_practices, htmx_patterns.
│                          #   The dangerous tools (create_template,
│                          #   create_component, configure_adapter,
│                          #   websocket_tools, config_cli) are slated for
│                          #   removal in 0.8.0; product operations belong in
│                          #   consumer apps.
├── shell/                 # Admin shell adapter (Phase 1).
├── websocket/
│   ├── server.py          # FastblocksWebSocketServer — UI update broadcasts.
│   ├── auth.py            # WebSocketAuthenticator (JWT). Module-level env
│                          #   reads: FASTBLOCKS_JWT_SECRET, FASTBLOCKS_TOKEN_EXPIRY,
│                          #   FASTBLOCKS_AUTH_ENABLED. NOTE: these are read at
│                          #   import time, not call time — see "Known tech debt" below.
│   ├── binding.py         # BindAddress enum (loopback / private LAN).
│   └── tls_config.py      # TLS cert configuration for WSS.
└── cli/grammars/          # vim.vim, emacs.el (extracted from cli.py in Phase 4).

tests/
├── conftest.py            # 3,410 LOC. The mcp_common.websocket stub installer
│                          #   lives here at session scope. Marker-based
│                          #   gating only (per-test stubs blocked by module-level
│                          #   `from mcp_common.websocket import ...` at collection).
├── mcp/test_ci_guard.py   # CI guard: greps for deleted symbol names
│                          #   (fastblocks_start_websocket etc.); fails on hit.
└── websocket/, adapters/auth/, mcp/ — most new test files use
    @pytest.mark.websocket for marker-based selection.
```

## The Big Architectural Picture

### Starlette → FastBlocks → Adapters → Oneiric (in that order)

Starlette provides the ASGI runtime. FastBlocks extends `Starlette` in `applications.py`, adds HTMX-aware request/response helpers, security middleware, and template integration. **All template engines, auth, admin, routes, etc. are pluggable adapters** registered through the Oneiric resolver. There is no `import Templates; templates = Templates()` — instead:

```python
from fastblocks.core.resolver import get_resolver
resolver = get_resolver()
templates = resolver.resolve("fastblocks", "templates")
```

The `register_candidate()` calls in each adapter module (e.g. `adapters/templates/jinja2.py`) register the adapter under a `(domain, key)` pair. The `Resolver` instance is the **single shared singleton** (one per process); do not instantiate a new `Resolver()` per module.

### Templates: jinja2_async_environment + htmy

Two template engines, one API surface. The Jinja2 path is async-aware via `jinja2_async_environment` + `starlette-async-jinja`; fragments use the `[[ ... ]]` delimiters. The HTMY path is class-based: a component is a `@dataclass` with an `htmy(context)` method. The `_load_component_from_source` in `_htmy_components.py` is a **deliberate ast.parse class walker** — it rejects any module with `Import` / `ImportFrom` / calls to `exec` / `eval` / `compile` / `__import__`. The old `importlib.util.spec_from_file_location + exec_module` path is gone; do not reintroduce it (it was an RCE vector).

### WebSocket auth: env-driven, no defaults

`fastblocks/websocket/auth.py` reads `FASTBLOCKS_JWT_SECRET`, `FASTBLOCKS_TOKEN_EXPIRY`, `FASTBLOCKS_AUTH_ENABLED` at **import time** (module-level `os.getenv`). The server `FastblocksWebSocketServer(WebSocketServer)` in `server.py` requires a JWT secret to issue tokens; if `JWT_SECRET == "dev-secret-change-in-production"` you get a warning, not a refusal. **Known tech debt**: the plan calls for hard-fail on the dev-secret in non-test processes; that work is not yet landed. New code in this area should call `os.getenv(...)` at use-time, not module load.

### MCP surface is read-only for framework introspection

MCP is **read-only for framework introspection** (7 tools: `list_adapters`,
`list_templates`, `validate_template`, `render_template`, `list_components`,
`validate_component`, `check_adapter_health`). Product operations (WebSocket
lifecycle, adapter configuration, site buildout) belong in consumer projects
such as SplashStand.

There is no MCP path to create a template, create a component, configure an
adapter, or start a WebSocket — those operations belong in a consumer app's MCP
server, not here. The `tests/mcp/test_ci_guard.py` test fails the build if any
of the deleted symbol names (`fastblocks_start_websocket`,
`fastblocks_create_template`, `fastblocks_create_component`,
`fastblocks_configure_adapter`, or `from fastblocks.mcp.websocket_tools import
...`) reappear. Keep it that way.

To configure an adapter from Python, use the typed API:
`AdapterRegistry.configure(adapter_name: str, **fields: Any)`, which validates
field names against the per-adapter settings schema and rejects unknown keys.

### Async / sync boundaries

All I/O in the orchestration layer is async. The two places this gets violated:
- `caching.py` historically had `asyncio.run(coro)` sync→async trampolines — those are gone as of Phase 3.4 (no-op for the file; the work had already been done in an earlier commit).
- `htmx.py` used to create a fresh event loop on every call to `htmx_trigger`/`htmx_redirect`/`htmx_refresh`. Phase 4.3 collapsed this into `_run_async_safely(coro)`, which uses a per-thread cached loop via `threading.local()`. There is also `run_async_native(coro)` for callers already in an async context — prefer that.

## Project Conventions (the ones not in `pyproject.toml`)

- **`from __future__ import annotations` as the first non-comment line of every source file** (after any module docstring).
- Imports sorted within each section (stdlib → third-party → first-party; `known-first-party = ["fastblocks"]`).
- `X | None` not `Optional[X]`; `list[str]` not `List[str]`; `pathlib.Path` not `os.path`.
- Function arguments with default `None` must be typed `X | None = None` (mypy `no_implicit_optional = true`).
- No `assert` in production code (`fastblocks/**`). Use the `fastblocks/exceptions.py` hierarchy.
- In `except` blocks, use `logger.exception(...)`, never `logger.error(..., exc_info=True)`.
- **Use `oneiric.core.logging.get_logger`** — not stdlib `logging`, not `print()`. The Phase 4.A migration moved 9 files off stdlib `logging`; do not roll it back.
- `~=` (compatible release) for stable runtime dependencies; `>=` only for early-development / pre-1.0 / prerelease packages (e.g. `sentry-sdk[starlette]>=3.0.0a7`).

## Test Conventions

- Project pytest markers (don't invent new ones): `unit`, `integration`, `e2e`, `property`, `slow`, `timeout`, `ci`, `crackerjack`, plus `@pytest.mark.websocket` (added in Phase 3.0 to document tests that need the `mcp_common.websocket` stub).
- `asyncio_mode = "auto"` — no need for `@pytest.mark.asyncio`.
- Per-test timeout: 300 s ceiling. Tests >10 s should be `@pytest.mark.slow` and skipped with `-m "not slow"` for fast feedback.
- The `tests.*` namespace has relaxed typing (`disallow_untyped_defs = false`).
- Asserts are idiomatic in tests.

## Reference Documentation

- `docs/ARCHITECTURE.md` — Starlette + adapter layering (note: still describes the project as ACB-based; the codebase actually moved to Oneiric in Phase 3.1 and the doc is stale; the code is the source of truth).
- `docs/SECURITY.md` — Security guidelines.
- `docs/ONEIRIC_GUIDE.md` — Oneiric integration patterns (also still titled "ACB Guide"; ignore the title).
- `docs/GETTING_STARTED.md` — Step-by-step quick start.
- `fastblocks/adapters/README.md` — Adapters reference.
- `fastblocks/actions/README.md` — Actions reference.
- `tests/TESTING.md` — Test suite instructions.

## Known Tech Debt (don't try to "fix" without coordination)

1. **WebSocket auth reads env at import time, not call time** (`fastblocks/websocket/auth.py:17-24`). The plan calls for this to be moved to use-time reads, with `JWT_SECRET == "dev-secret-change-in-production"` hard-failing in non-test processes. Not yet landed.
2. **The 4 leftover `t.cast(Coroutine, ...)` calls in `caching.py`** were partially removed in Phase 4.A but the plan-text count of 8 was based on stale state — only 4 existed at the time the agent ran. If you find more in `caching.py`, remove them; if not, leave it.
3. **Docs lag the code.** `README.md`, `docs/ARCHITECTURE.md`, `docs/ONEIRIC_GUIDE.md` (and several others) still describe the project as ACB-based. The actual code is Oneiric-only since Phase 3.1. Don't trust those docs for the architectural truth; trust `fastblocks/core/resolver.py` and the `fastblocks.core.resolver.get_resolver()` call sites.
4. **19→8 collection errors** in `pytest -m "not slow"` are pre-existing; most are conftest `mcp_common.websocket` stub pollution under xdist. Per-test gating was attempted in Phase 3.0 and reverted because test files do `from mcp_common.websocket import ...` at module level (collection time, before any per-test hook can run). The marker-based `pytest.mark.websocket` is the current workaround.

## Reminder

Crackerjack is the quality gate. Before declaring any task done, run `uv run crackerjack run` and confirm it passes. If a single test fails, do not declare success.
