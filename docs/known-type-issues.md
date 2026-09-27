# Known Type Issues

Pyright warnings are informational, not CI-blocking. Each entry below has
a removal plan. **New warnings will fail D2 review** — the
``scripts/check_pyright_known_issues.py`` gate raises on any unknown
``file:line`` + rule combination.

> **Last verified:** generated from ``uvx pyright fastblocks`` against
> this repo at the time of commit. Total known diagnostics: ~907
> (errors + warnings) — all listed by rule category below. Run
> ``scripts/check_pyright_known_issues.py`` after ``pyright fastblocks``
> to confirm CI is green.

## How the table maps to the script

``scripts/check_pyright_known_issues.py`` parses ``pyright`` output and
groups diagnostics by ``(rule, path-prefix)`` tuples. Each tuple must
appear in the "Known diagnostic categories" table below — otherwise the
script exits non-zero.

The script groups by **prefix** to keep the table manageable; a single
entry covers every ``reportUnknownParameterType`` on any file under
``fastblocks/observability/``, etc. Removal plans are stated at the
rule+prefix level.

## Known diagnostic categories

> **Prefix format:** pyright emits absolute paths on macOS/Linux. The
> script strips everything up to and including the first ``fastblocks/``
> marker, then uses the **parent directory** as the prefix. So a path
> like ``/Users/.../fastblocks/fastblocks/mcp/server.py`` keys under
> ``fastblocks/mcp/``. The repo name (``fastblocks``) and the package
> name (``fastblocks``) are identical in this project — that is why
> every prefix has the doubled ``fastblocks/`` segment.

| Rule | Path prefix | Count (baseline) | Message class | Removal plan |
|---|---|---|---|---|
| `reportUnknownParameterType` | `fastblocks/fastblocks/` | 428 | Pyright cannot infer parameter types (broad third-party stub gaps: starlette, granian, aioconsole, etc.) | Add typed Protocols for each public third-party boundary; eliminate ``Any`` widening at the oneiric/fastmcp/mcp-common seams. Target: narrow to <100 by Q1 2027. |
| `reportMissingImports` | `fastblocks/fastblocks/observability/` | 21 | Optional-dep imports (``prometheus_client``, ``logfire``) inside ``try/except ImportError`` | Adopt the optional-dep-aware stub shim already in `crackerjack`; gate per-stubs; declare a minimal Protocol surface for each. Target: 0 by Q1 2027. |
| `reportMissingImports` | `fastblocks/fastblocks/websocket/` | 7 | ``mcp_common.websocket.auth`` and ``oneiric.core.logging`` not resolved by pyright | Upgrade to ``pyright>=1.1.350`` with explicit package bases; ship `py.typed` markers on stubs. Target: 0 by Q1 2027. |
| `reportMissingImports` | `fastblocks/fastblocks/main.py/` | 1 | ``oneiric.adapters.bootstrap`` unresolved | Pin oneiric stubs. |
| `reportMissingImports` | `fastblocks/fastblocks/mcp/` | 19 | ``fastmcp``, ``jinja2``, ``oneiric.core.logging`` unresolved | Upgrade pyright / pin stubs. |
| `reportMissingImports` | `fastblocks/fastblocks/middleware.py/` | 10 | ``brotli_asgi``, ``secure``, ``starlette_csrf`` unresolved | Tighten optional-dep surface to a typed Protocol. |
| `reportAttributeAccessIssue` | `fastblocks/fastblocks/` | 33 | Stub-less attributes on third-party classes (e.g. ``FastMCP._tool_manager``, ``TracerProvider.shutdown``) | Cast to ``Any`` at the call site, or add a Protocol for the surface. Target: 0 by Q1 2027. |
| `reportUntypedFunctionDecorator` | `fastblocks/fastblocks/` | 26 | Decorators from `oneiric.cli.base.OneiricCLIBase` typed as ``Any`` | Replace ``@cli.command()`` with an explicit ``@register_command()`` that has a typed signature, or add stubs for OneiricCLIBase. Target: 0 by Q1 2027. |
| `reportConstantRedefinition` | `fastblocks/fastblocks/` | 14 | Module-level constant reassignments (mostly ``_PROMETHEUS_AVAILABLE = ...`` plus a sentinel-style ``is None`` guard) | Refactor to immutable constants or convert to ``ClassVar``. Target: 0 by Q1 2027. |
| `reportUntypedBaseClass` | `fastblocks/fastblocks/` | 3 | ``BaseHTTPMiddleware``, ``Server`` from `starlette`, etc. on ``applications.py``, ``cli.py``, ``htmx.py`` | Add typed Protocol or vendored stubs. Target: 0 by Q1 2027. |
| `reportUntypedBaseClass` | `fastblocks/fastblocks/adapters/app/` | 4 | ``TracerProvider``, ``MeterProvider`` stub bases | Cast base to ``Any`` at the class declaration or vendor stubs. Target: 0 by Q1 2027. |
| `reportUntypedBaseClass` | `fastblocks/fastblocks/adapters/oneiric/` | 1 | ``OneiricAdapterBase`` typed as ``Any`` | Vendor a Protocol. Target: 0 by Q1 2027. |
| `reportUntypedBaseClass` | `fastblocks/fastblocks/adapters/routes/` | 1 | ``Router`` stub-less | Tighten stubs. |
| `reportUntypedBaseClass` | `fastblocks/fastblocks/mcp/` | 1 | ``FastMCP[Any]`` opaque base | Vendor Protocol. |
| `reportUntypedBaseClass` | `fastblocks/fastblocks/observability/` | 1 | ``BaseHTTPMiddleware`` base | Vendor Protocol. |
| `reportUntypedBaseClass` | `fastblocks/fastblocks/websocket/` | 1 | ``Server`` base | Vendor Protocol. |
| `reportCallIssue` | `fastblocks/fastblocks/` | 12 | Stub-vs-runtime arg mismatches (mcp_common FastMCP surface) | Tighten `mcp-common` pin to a release that ships complete stubs. Target: 0 by Q1 2027. |
| `reportPossiblyUnboundVariable` | `fastblocks/fastblocks/observability/` | 10 | ``structlog`` referenced before possible assignment in error paths | Initialise at module-scope with a typed ``None`` default. Target: 0 by Q1 2027. |
| `reportPossiblyUnboundVariable` | `fastblocks/fastblocks/actions/gather/` | 1 | ``get_adapters`` referenced before possible assignment | Initialise at module-scope. Target: 0 by Q1 2027. |
| `reportFunctionMemberAccess` | `fastblocks/fastblocks/` | 10 | ``asyncio.get_event_loop()`` legacy + duck-typed helpers | Replace with ``asyncio.get_running_loop()`` or add ``Protocol`` declarations. Target: 0 by Q1 2027. |
| `reportUnnecessaryIsInstance` | `fastblocks/fastblocks/` | 8 | Defensive ``isinstance`` checks that pyright proves are dead branches | Drop the dead branches (covered by ``utils/protection.py`` consolidation). Target: 0 by Q1 2027. |
| `reportUnnecessaryComparison` | `fastblocks/fastblocks/` | 8 | Same root cause as above | Drop the dead comparisons. Target: 0 by Q1 2027. |
| `reportUnusedImport` | `fastblocks/fastblocks/` | 7 | ``Any`` / ``cast`` imports kept for narrow mypy suppressions that pyright doesn't need | Keep — pyright is informational, mypy is the gate. Documented per file in `git grep` audit. |
| `reportMissingModuleSource` | `fastblocks/fastblocks/actions/sync/` | 3 | ``yaml`` source missing on slim installs | Same removal plan as ``reportMissingImports`` (optional-dep stub shim). Target: 0 by Q1 2027. |
| `reportMissingModuleSource` | `fastblocks/fastblocks/mcp/` | 2 | ``yaml`` source missing | Same. |
| `reportMissingModuleSource` | `fastblocks/fastblocks/cli.py/` | 1 | ``yaml`` source missing | Same. |
| `reportIncompatibleVariableOverride` | `fastblocks/fastblocks/` | 5 | Subclass overrides with wider types than the parent Protocol | Tighten subclass signatures. Target: 0 by Q1 2027. |
| `reportReturnType` | `fastblocks/fastblocks/` | 3 | Real type mismatches at return sites (mostly singleton-typed constructors) | Already addressed for mypy via narrow ``# type: ignore`` in the source. Pyright is the diagnostic-only mirror. |
| `reportAssignmentType` | `fastblocks/fastblocks/` | 3 | Same singleton-narrowing pattern as ``reportReturnType`` | Same. |
| `reportDeprecated` | `fastblocks/fastblocks/` | 2 | Deprecated alias references | Ad-hoc — flagged for cleanup. |
| `reportUnnecessaryContains` | `fastblocks/fastblocks/` | 1 | Defensive ``in`` check pyright proves dead | Drop. |
| `reportRedeclaration` | `fastblocks/fastblocks/` | 1 | Module re-exports a name imported elsewhere | Drop one of the bindings. |
| `reportIndexIssue` | `fastblocks/fastblocks/` | 1 | Off-by-one in a typed dict index | Tighten the index expression. |

<!-- add rows as needed -->

## How to add a new known issue

1. Run ``uvx pyright fastblocks 2>&1 | tee /tmp/pyright.txt``.
2. Run ``uv run python scripts/check_pyright_known_issues.py`` —
   the script lists every ``(rule, file-prefix)`` tuple not in this
   table.
3. Add a row with a concrete removal plan; do NOT leave the rule
   category blank ("we'll fix later" is not a plan).
4. Commit both this file and the script in the same PR.