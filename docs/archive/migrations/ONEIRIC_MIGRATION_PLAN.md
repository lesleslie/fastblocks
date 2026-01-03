# FastBlocks Oneiric Migration Plan

**Status:** Draft (active)
**Owner:** Platform Core
**Scope:** FastBlocks runtime + adapters + MCP server migration from ACB to Oneiric
**References:**

- oneiric/docs/analysis/ADAPTER_OBSOLESCENCE_ANALYSIS.md
- oneiric/docs/ONEIRIC_VS_ACB.md
- oneiric/docs/STRATEGIC_ROADMAP.md
- oneiric/docs/MCP_SERVER_CLI_STANDARD.md
- mcp-common/docs/ONEIRIC_CLI_FACTORY_IMPLEMENTATION.md
- crackerjack/docs/MIGRATION_GUIDE_0.47.0.md
- crackerjack/docs/archive/implementation-plans/ONEIRIC_MIGRATION_EXECUTION_PLAN.md

______________________________________________________________________

## Progress Tracking

Update checkboxes as tasks are completed. Add dates or notes inline when needed.

### Phase 0: Alignment + Baselines

- [ ] Confirm Oneiric cutover posture (no hybrid ACB path).
- [ ] Confirm hard break: no compatibility shims, legacy support, or migration layers.
- [ ] Confirm Oneiric + mcp-common versions are sourced from `pyproject.toml` and `uv.lock`.
- [ ] Capture baseline ACB usage: `rg -n "\\bacb\\b" fastblocks > acb_baseline.txt`.
- [ ] Record baseline MCP CLI commands: `fastblocks mcp --help > mcp_cli_baseline.txt`.
- [ ] Capture client config snippets from `.fastblocks/settings.local.json` and environment variables.
- [ ] Run pre-migration health check: `fastblocks health --probe > health_baseline.json`.
- [ ] Define cutover recovery plan (revert tag + rollback steps) with owner and trigger criteria.
- [ ] Block Phase 1 start until recovery plan is approved.
  **Exit gate (approval: you)**
- [ ] Recovery plan includes explicit trigger thresholds (health probe failure, CLI regression, adapter smoke failure).
- [ ] Baselines attached (ACB scan output, MCP CLI commands, client config snippets, health probe).
- [ ] Oneiric + mcp-common version sources documented (`pyproject.toml`, `uv.lock`).
- [ ] Rollback procedure tested in staging environment.

### Phase 1: Core Runtime Migration (ACB -> Oneiric)

- [ ] Replace ACB registration/DI in `fastblocks/main.py` with Oneiric resolver/lifecycle entrypoint.
  - Replace `from acb import ensure_registration, register_pkg` with Oneiric equivalents
  - Replace `from acb.adapters import register_adapters, root_path` with Oneiric adapter registry
  - Replace `from acb.depends import depends` with Oneiric dependency injection
- [ ] Replace ACB usage in `fastblocks/initializers.py`.
  - Replace `from acb import register_pkg` with Oneiric package registration
  - Replace `from acb.config import AdapterBase, Config` with Oneiric config models
  - Replace `from acb.depends import depends` with Oneiric DI
- [ ] Replace ACB DI in `fastblocks/middleware.py`.
  - Replace `from acb.debug import debug` with Oneiric logging
  - Replace `from acb.depends import depends` with Oneiric dependency injection
  - Replace `from acb.adapters import get_adapter` with Oneiric adapter resolution
- [ ] Replace ACB DI in `fastblocks/exceptions.py`.
  - Replace `from acb.depends import depends` with Oneiric DI
- [ ] Replace ACB usage in `fastblocks/caching.py`.
  - Replace `from acb.actions.hash import hash` with Oneiric hashing utilities
  - Replace `from acb.adapters import get_adapter` with Oneiric adapter resolution
  - Replace `from acb.depends import depends` with Oneiric DI
- [ ] Update integration modules to Oneiric domains:
  - [ ] events (`fastblocks/_events_integration.py`)
  - [ ] health (`fastblocks/_health_integration.py`)
  - [ ] validation (`fastblocks/_validation_integration.py`)
  - [ ] workflows (`fastblocks/_workflows_integration.py`)
- [ ] Update imports and type hints throughout core modules.
- [ ] Verify all ACB imports removed: `rg -n "\\bacb\\b" fastblocks/main.py fastblocks/initializers.py fastblocks/middleware.py fastblocks/exceptions.py fastblocks/caching.py` returns 0.
  **Config migration (code-handled)**
- [ ] Add settings migration module: map legacy keys/env vars to Oneiric settings.
- [ ] Log warnings for deprecated keys; fail fast on missing mandatory mappings.
- [ ] Emit a one-time migration report in logs.
- [ ] Add tests for config migration with sample legacy configs.
  **Exit gate (approval: you)**
- [ ] Core runtime starts/stops using Oneiric resolver with no DI errors.
- [ ] Health endpoint returns OK and includes Oneiric resolver status.
- [ ] Config loads through Oneiric settings; no implicit ACB fallback.
- [ ] All core module tests pass with Oneiric integration.
- [ ] Performance metrics within 10% of baseline (startup time, memory usage).

### Phase 2: Adapter Re-architecture (Required)

**Source:** `oneiric/docs/analysis/ADAPTER_OBSOLESCENCE_ANALYSIS.md` explicitly states:
"Rearchitecture Needed: admin, app adapters," and recommends moving admin -> services and app -> core.

- [ ] Define admin services boundary (responsibilities, APIs, data access patterns).
  - Document specific admin routes: `/admin/`, `/admin/users`, `/admin/settings`
  - Define service boundaries: auth, user management, system settings
- [ ] Produce admin route map and target service/module placements.
  - Create `fastblocks/services/admin/` directory structure
  - Map routes to service modules with clear ownership
- [ ] Define admin service API surface (inputs/outputs/errors).
  - Document REST API contracts for each admin endpoint
  - Define error handling patterns and status codes
- [ ] Migrate admin routes/handlers out of adapters into services domain.
  - Move `fastblocks/adapters/admin/` → `fastblocks/services/admin/`
  - Update route registrations to use new service endpoints
- [ ] Move admin adapter to services domain (admin -> services).
  - Create `fastblocks/services/admin/__init__.py` with service registry
  - Update imports from `fastblocks.adapters.admin` to `fastblocks.services.admin`
- [ ] Define core app layer responsibilities (startup, routing, config ownership).
  - Document core responsibilities: app lifecycle, route registration, config management
  - Define boundaries between core and other layers
- [ ] Produce app responsibility map and target module placements.
  - Create `fastblocks/core/` directory structure
  - Map core functions to appropriate modules
- [ ] Define core app API surface (startup, routing, config ownership).
  - Document core API contracts and extension points
  - Define configuration schema and validation rules
- [ ] Migrate app adapter responsibilities into core application layer.
  - Move `fastblocks/adapters/app/` → `fastblocks/core/`
  - Update core app initialization and lifecycle management
- [ ] Move app adapter to core application layer (app -> core).
  - Create `fastblocks/core/__init__.py` with core registry
  - Update imports from `fastblocks.adapters.app` to `fastblocks.core`
- [ ] Update documentation and imports referencing admin/app adapters.
  - Update all import statements in codebase
  - Update README files and examples
- [ ] Add validation tests for new service/core boundaries.
  - Test service isolation and API contracts
  - Test core functionality and extension points
    **Exit gate (approval: you)**
- [ ] Admin service boundary + route map + API surface docs complete.
- [ ] App core responsibilities + API surface docs complete.
- [ ] At least one admin route and one app core flow migrated and validated.
- [ ] Imports updated; old adapter entrypoints no longer referenced.
- [ ] Service/core boundary tests pass.
- [ ] Performance metrics within 15% of baseline for migrated routes.

### Phase 3: Adapter Conversion (ACB -> Oneiric)

Convert each adapter category to Oneiric registration, metadata, lifecycle, and settings models.

**Global adapter tasks:**

- [ ] Replace `acb.depends` usage inside adapters with Oneiric access patterns.
- [ ] Replace `acb.adapters` metadata/registration with Oneiric adapter metadata registration.
- [ ] Ensure every adapter has init/health/cleanup coverage.
- [ ] Add Oneiric settings models for adapter configuration.

**Adapter categories:**

- [ ] templates: define Oneiric settings model (`fastblocks/adapters/templates/`)
- [ ] templates: migrate registration/metadata to Oneiric
- [ ] templates: implement init/health/cleanup lifecycle
- [ ] templates: complete adapter smoke checklist
- [ ] auth: define Oneiric settings model (`fastblocks/adapters/auth/`)
- [ ] auth: migrate registration/metadata to Oneiric
- [ ] auth: implement init/health/cleanup lifecycle
- [ ] auth: complete adapter smoke checklist
- [ ] routes: define Oneiric settings model (`fastblocks/adapters/routes/`)
- [ ] routes: migrate registration/metadata to Oneiric
- [ ] routes: implement init/health/cleanup lifecycle
- [ ] routes: complete adapter smoke checklist
- [ ] admin services: define Oneiric service settings/registry (Phase 2 output)
- [ ] admin services: implement init/health/cleanup lifecycle
- [ ] admin services: complete service smoke checklist
- [ ] app core: define Oneiric core settings/registry (Phase 2 output)
- [ ] app core: implement init/health/cleanup lifecycle
- [ ] app core: complete core smoke checklist
- [ ] images: define Oneiric settings model (`fastblocks/adapters/images/`)
- [ ] images: migrate registration/metadata to Oneiric
- [ ] images: implement init/health/cleanup lifecycle
- [ ] images: complete adapter smoke checklist
- [ ] icons: define Oneiric settings model (`fastblocks/adapters/icons/`)
- [ ] icons: migrate registration/metadata to Oneiric
- [ ] icons: implement init/health/cleanup lifecycle
- [ ] icons: complete adapter smoke checklist
- [ ] fonts: define Oneiric settings model (`fastblocks/adapters/fonts/`)
- [ ] fonts: migrate registration/metadata to Oneiric
- [ ] fonts: implement init/health/cleanup lifecycle
- [ ] fonts: complete adapter smoke checklist
- [ ] style: define Oneiric settings model (`fastblocks/adapters/style/`)
- [ ] style: migrate registration/metadata to Oneiric
- [ ] style: implement init/health/cleanup lifecycle
- [ ] style: complete adapter smoke checklist
- [ ] sitemap: define Oneiric settings model (`fastblocks/adapters/sitemap/`)
- [ ] sitemap: migrate registration/metadata to Oneiric
- [ ] sitemap: implement init/health/cleanup lifecycle
- [ ] sitemap: complete adapter smoke checklist
  **Exit gate (approval: you)**
- [ ] Oneiric settings model exists for each adapter category.
- [ ] Each adapter passes init/health/cleanup + one basic operation check.
- [ ] `acb.depends` and `acb.adapters` usage removed in adapters.
- [ ] Admin/app adapters removed or relocated per Phase 2 outputs.

### Phase 4: MCP Server Migration (mcp-common CLI Factory)

- [ ] Replace `acb.create_mcp_server` in `fastblocks/mcp/server.py` with `MCPServerCLIFactory`.
  - Replace `from acb import create_mcp_server` with `from mcp_common.cli import MCPServerCLIFactory`
  - Update server initialization to use factory pattern
- [ ] Add FastBlocks MCP settings extending `MCPServerSettings`.
  - Create `fastblocks/mcp/settings.py` with Oneiric settings model
  - Define FastBlocks-specific MCP configuration
- [ ] Adopt `.oneiric_cache/` snapshots and standard flags (start/stop/restart/status/health).
  - Update cache directory from `.fastblocks/` to `.oneiric_cache/`
  - Implement standard CLI flags and help text
- [ ] Update MCP tooling registration (`fastblocks/mcp/resources.py`, `fastblocks/mcp/tools.py`).
  - Update tool registration to use Oneiric tool registry
  - Update resource registration to use Oneiric resource patterns
- [ ] Update MCP CLI entrypoints (e.g., `fastblocks/cli.py`, `fastblocks/__main__.py`) to new command surface.
  - Replace old CLI commands with new standard commands
  - Update help text and command documentation
- [ ] Update MCP README and CLI docs (new command syntax).
  - Document new command syntax and usage examples
  - Update all CLI examples in documentation
- [ ] Update MCP client configuration examples (replace `--start-mcp-server` with `start`).
  - Update configuration examples to use new command structure
  - Provide migration guide for existing clients
- [ ] Add MCP error handling and graceful degradation.
  - Implement fallback mechanisms for MCP failures
  - Add comprehensive error logging and monitoring
    **Exit gate (approval: you)**
- [ ] MCP lifecycle commands `start/stop/restart/status/health` succeed.
- [ ] `.oneiric_cache/` contains PID + snapshot files; health JSON valid.
- [ ] MCP tools register and run via new CLI surface.
- [ ] MCP error handling tested with simulated failures.
- [ ] Performance metrics within 10% of baseline for MCP operations.

### Phase 5: Validation Gates + Cutover

**Crackerjack-style gates (required):**

- [ ] MCP lifecycle commands work: `start/stop/restart/status/health`.
- [ ] `health --probe` returns live data (not cached snapshot).
- [ ] `.oneiric_cache/runtime_health.json` exists and is valid JSON.
- [ ] `.oneiric_cache/` contains PID + snapshot files with correct permissions.
- [ ] Zero ACB imports remain: `rg -n "\\bacb\\b" fastblocks` returns 0.
- [ ] Remove `acb` from `pyproject.toml`.
- [ ] Refresh `uv.lock` to reflect ACB removal.

**Functional parity:**

- [ ] Define parity matrix (core runtime, admin services, app core, MCP tools, key adapters).
- [ ] Parity matrix is functional-only (no performance/regression metrics).
- [ ] Execute parity matrix and record pass/fail evidence.
- [ ] MCP tools register and execute.
- [ ] Core runtime start/stop is stable.
- [ ] Adapter/service resolution works in Oneiric.
- [ ] Adapter category smoke checks pass (init/health/cleanup + basic usage).

**Performance validation:**

- [ ] Measure and record baseline performance metrics.
- [ ] Compare Oneiric performance against baseline.
- [ ] Validate performance within acceptable thresholds (≤15% degradation).
- [ ] Test under load conditions (concurrent requests, high traffic).

**Error handling validation:**

- [ ] Test graceful degradation scenarios.
- [ ] Validate error messages and logging.
- [ ] Test recovery from failure states.
- [ ] Validate fallback mechanisms.

**Security validation:**

- [ ] Validate authentication and authorization.
- [ ] Test secure configuration handling.
- [ ] Validate data protection mechanisms.
- [ ] Test audit logging and monitoring.

**Incremental rollout strategy:**

- [ ] Implement feature flags for critical components.
- [ ] Create canary deployment plan.
- [ ] Define rollback triggers and thresholds.
- [ ] Implement monitoring and alerting for rollout.

**Exit gate (approval: you)**

- [ ] Functional parity matrix completed with evidence.
- [ ] Zero ACB imports; `acb` removed from deps; `uv.lock` refreshed.
- [ ] Rollback rehearse completed in staging (revert tag + rollback steps).
- [ ] Performance validation completed and within thresholds.
- [ ] Error handling and security validation completed.
- [ ] Incremental rollout plan approved and tested.

### Phase 6: Docs + Release

- [ ] Update FastBlocks docs to Oneiric-only usage.
- [ ] Add migration notes for MCP clients and CLI command changes.
- [ ] Release notes include ACB removal and Oneiric cutover details.

______________________________________________________________________

## Notes

- Keep this plan current as tasks complete. Add dates or short notes next to checkboxes.
- Use Crackerjack migration docs as reference for CLI adoption and validation gates.

______________________________________________________________________

## Appendix E: Technical Enhancements Guide

## Appendix C: Config Migration Module (Code-Handled)

**Goal:** migrate legacy config keys/env vars to Oneiric settings at runtime with explicit validation.

**Scope**

- Read legacy config inputs (files, env vars, CLI flags) used by ACB.
- Map to Oneiric settings fields with explicit conversion rules.
- Warn on deprecated keys, fail fast on missing mandatory mappings.

**Implementation checklist**

- [ ] Create `fastblocks/config/migration.py` (or equivalent) for legacy->Oneiric mapping.
- [ ] Define a mapping table with defaults and coercion rules.
- [ ] Add validation: missing required fields raise a clear exception.
- [ ] Emit a one-time migration report in logs (mapped keys, deprecated keys, missing keys).
- [ ] Add tests for at least one legacy config file and env-var mapping scenario.
- [ ] Add performance validation for config loading (≤50ms for typical configs).
- [ ] Add error handling for malformed config files.

**Example mapping table (structure only)**

```python
LEGACY_TO_ONEIRIC = {
    "ACB_FOO_ENABLED": ("oneiric.foo.enabled", bool),
    "ACB_BAR_URL": ("oneiric.bar.url", str),
    "ACB_CACHE_TTL": ("oneiric.cache.ttl", int),
    "ACB_DEBUG_MODE": ("oneiric.debug.enabled", bool),
}
```

**Validation commands:**

```bash
# Test config migration with sample legacy config
python -c "from fastblocks.config.migration import migrate_config; migrate_config('tests/legacy_config.json')"

# Test config migration with environment variables
ACB_FOO_ENABLED=true ACB_BAR_URL="http://example.com" python -c "from fastblocks.config.migration import migrate_config; print(migrate_config())"
```

______________________________________________________________________

## Appendix D: Staging Rollback Runbook (Stub)

**Purpose:** validate rollback steps before cutover and document exact commands.

**Pre-conditions**

- [ ] Staging environment mirrors prod config shape and Oneiric deps.
- [ ] Current release tag identified (e.g., `vX.Y.Z`).
- [ ] Rollback tag identified (e.g., `vX.Y.(Z-1)`).
- [ ] Backup current staging environment state.

**Rollback rehearsal steps**

- [ ] Deploy Oneiric build to staging:
  ```bash
  git checkout vX.Y.Z
  uv sync
  fastblocks start --env staging
  ```
- [ ] Run Phase 5 parity matrix and record results:
  ```bash
  fastblocks health --probe > oneiric_health.json
  pytest tests/parity_matrix.py --report=parity_results.json
  ```
- [ ] Trigger rollback using documented steps:
  ```bash
  git checkout vX.Y.(Z-1)
  uv sync
  fastblocks start --env staging
  ```
- [ ] Verify health, CLI commands, and key adapters on rollback version:
  ```bash
  fastblocks health --probe > rollback_health.json
  fastblocks mcp status
  pytest tests/smoke_tests.py
  ```
- [ ] Record timestamps and evidence for approval:
  ```bash
  echo "Rollback completed at $(date)" > rollback_evidence.txt
  fastblocks health --probe >> rollback_evidence.txt
  git log --oneline -5 >> rollback_evidence.txt
  ```

**Rollback validation criteria:**

- [ ] Health endpoint returns OK status
- [ ] MCP server starts and responds to commands
- [ ] Core runtime functionality restored
- [ ] Adapter smoke tests pass
- [ ] Performance metrics within expected ranges

**Emergency rollback procedure:**

```bash
# Emergency rollback script
#!/bin/bash
set -e

# Stop current services
echo "Stopping current services..."
fastblocks stop || true

# Checkout rollback version
echo "Rolling back to $ROLLBACK_TAG..."
git checkout $ROLLBACK_TAG

# Sync dependencies
echo "Syncing dependencies..."
uv sync

# Start services
echo "Starting rollback services..."
fastblocks start --env production

# Verify health
echo "Verifying rollback health..."
fastblocks health --probe

echo "Rollback completed successfully"
```

## Appendix A: Parity Matrix Template (Functional Only)

Use this table to capture pass/fail evidence for core flows. Keep entries short and link to logs or commands used.

| Area | Scenario | Expected Result | Status | Evidence |
| --- | --- | --- | --- | --- |
| Core runtime | Start service | App starts without errors | [ ] | `fastblocks start` |
| Core runtime | Stop service | Clean shutdown, no orphaned tasks | [ ] | `fastblocks stop` |
| Core runtime | Config load | Settings resolved via Oneiric | [ ] | `fastblocks config show` |
| Core runtime | Routing | Basic route returns expected response | [ ] | `curl http://localhost:8000/` |
| Core runtime | Dependency resolution | Oneiric resolver returns expected instance | [ ] | `fastblocks di resolve <service>` |
| Admin services | Admin route access | Admin endpoints respond as expected | [ ] | `curl http://localhost:8000/admin` |
| Admin services | Admin auth (if applicable) | Access controls enforced | [ ] | `curl -u admin:password http://localhost:8000/admin` |
| App core | App route access | Core app endpoints respond as expected | [ ] | `curl http://localhost:8000/api/health` |
| MCP CLI | start | Server starts via new CLI factory | [ ] | `fastblocks mcp start` |
| MCP CLI | status | Reports accurate status | [ ] | `fastblocks mcp status` |
| MCP CLI | health --probe | Live health returned (not cached) | [ ] | `fastblocks health --probe` |
| MCP CLI | stop/restart | Clean stop and restart | [ ] | `fastblocks mcp stop && fastblocks mcp start` |
| MCP tools | tool registration | Tools listed and callable | [ ] | `fastblocks mcp tools list` |
| MCP tools | tool execution | Sample tool returns expected output | [ ] | `fastblocks mcp tools execute <tool>` |
| Adapter resolution | Adapter load | Oneiric adapter registry resolves adapters | [ ] | `fastblocks adapters list` |

**Performance validation commands:**

```bash
# Measure startup time
TIMEFORMAT='%3R'; time fastblocks start 2>&1 | grep real

# Measure request response time
curl -w "Total: %{time_total}s\n" -o /dev/null -s http://localhost:8000/

# Measure memory usage
ps aux | grep fastblocks | grep -v grep | awk '{print $4, $5, $6, $11}'
```

**Error handling validation commands:**

```bash
# Test graceful degradation
fastblocks start --disable-cache

# Test error recovery
fastblocks start && pkill -9 fastblocks && fastblocks start

# Test fallback mechanisms
fastblocks start --fallback-mode
```

______________________________________________________________________

## Appendix E: Technical Enhancements Guide

**Type System Migration:**

- [ ] Document ACB → Oneiric type system differences
- [ ] Create type migration guide for developers
- [ ] Update type hints throughout codebase
- [ ] Add type validation tests

**Async/Await Pattern Migration:**

- [ ] Document ACB → Oneiric async pattern differences
- [ ] Update async function signatures
- [ ] Validate async context management
- [ ] Test async error handling

**Dependency Injection Migration:**

- [ ] Document ACB → Oneiric DI pattern differences
- [ ] Update DI container configuration
- [ ] Validate DI resolution performance
- [ ] Test DI error handling

**Code Examples:**

**ACB → Oneiric Type Migration:**

```python
# ACB style
from acb.config import Config
from typing import Optional


class ACBConfig(Config):
    debug: Optional[bool] = False


# Oneiric style
from oneiric.config import Settings
from typing import Optional


class OneiricSettings(Settings):
    debug: Optional[bool] = False

    class Config:
        env_prefix = "ONEIRIC_"
```

**ACB → Oneiric Async Migration:**

```python
# ACB style
from acb.depends import depends


@depends.inject
async def acb_service():
    # ACB async context
    pass


# Oneiric style
from oneiric.di import inject


@inject
async def oneiric_service():
    # Oneiric async context
    pass
```

**ACB → Oneiric DI Migration:**

```python
# ACB style
from acb.depends import depends


class ACBService:
    @depends.inject
    def __init__(self, config: Config):
        self.config = config


# Oneiric style
from oneiric.di import inject


class OneiricService:
    @inject
    def __init__(self, settings: Settings):
        self.settings = settings
```

**Validation Commands:**

```bash
# Validate type system migration
mypy fastblocks --strict

# Validate async patterns
python -m asyncio fastblocks/tests/async_tests.py

# Validate DI resolution
fastblocks di validate

# Test type performance
python -c "from fastblocks.config import Settings; import timeit; print(timeit.timeit(lambda: Settings(), number=1000))"
```

## Appendix B: Adapter Smoke Checklist

Use this checklist for each adapter category (templates, auth, routes, images, icons, fonts, style, sitemap).

**Per-adapter checks**

- [ ] Init: adapter loads with Oneiric settings model.
- [ ] Health: health check reports OK (or expected degraded state).
- [ ] Basic operation: primary function works (see category examples).
- [ ] Cleanup: teardown/dispose runs without errors if supported.
- [ ] Performance: response time within expected thresholds.
- [ ] Error handling: graceful degradation on failure.

**Category examples (fill in for each adapter)**

- templates: render a simple template with substitutions.
  ```bash
  fastblocks templates render --template "test.html" --context '{"title": "Test"}'
  ```
- auth: authenticate a test user and verify session or token output.
  ```bash
  curl -X POST http://localhost:8000/auth/login -d '{"username": "test", "password": "test"}'
  ```
- routes: register a sample route and receive expected response.
  ```bash
  curl http://localhost:8000/test-route
  ```
- images: transform or proxy a sample image request.
  ```bash
  curl http://localhost:8000/images/transform?url=http://example.com/image.jpg&width=200
  ```
- icons: fetch/resolve a sample icon asset.
  ```bash
  curl http://localhost:8000/icons/fontawesome/solid/heart
  ```
- fonts: serve or resolve a sample font asset.
  ```bash
  curl http://localhost:8000/fonts/google/roboto
  ```
- style: load a sample stylesheet or style bundle.
  ```bash
  curl http://localhost:8000/styles/main.css
  ```
- sitemap: generate a sitemap and validate output format.
  ```bash
  curl http://localhost:8000/sitemap.xml
  ```

**Adapter validation commands:**

```bash
# List all adapters
fastblocks adapters list

# Check adapter health
fastblocks adapters health <adapter_name>

# Test adapter basic operation
fastblocks adapters test <adapter_name>

# Measure adapter performance
TIMEFORMAT='%3R'; time fastblocks adapters test <adapter_name> 2>&1 | grep real
```
