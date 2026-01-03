# Phase 0: Alignment + Baselines - COMPLETE

## Baseline Capture Summary

### 1. ACB Usage Baseline

- **Total ACB occurrences**: 218 across the codebase
- **Detailed usage captured**: `acb_usage_detailed.txt`
- **Key files with ACB usage**:
  - `fastblocks/main.py`: Core registration and DI
  - `fastblocks/initializers.py`: Package registration
  - `fastblocks/cli.py`: Multiple depends imports
  - `fastblocks/_events_integration.py`: Events and DI
  - `fastblocks/exceptions.py`: Dependency injection
  - `fastblocks/caching.py`: Adapter resolution
  - `fastblocks/mcp/server.py`: MCP server creation

### 2. MCP CLI Baseline

- **Current MCP command**: `python -m fastblocks mcp [OPTIONS]`
- **Options**:
  - `--port/-p`: Port for MCP server (default: auto)
  - `--host`: Host to bind MCP server to (default: localhost)
- **Current implementation**: Uses ACB's `create_mcp_server()`

### 3. Health Probe Baseline

- **Status**: Not currently available in FastBlocks CLI
- **Note**: Health functionality will be added as part of Oneiric migration

### 4. Dependency Baseline

- **Current dependencies in pyproject.toml**:
  - `acb>=0.31.12` (current ACB dependency)
  - `oneiric>=0.3.4` (new Oneiric dependency)
  - `mcp-common>=0.3.3` (MCP common with Oneiric support)

### 5. Recovery Plan

- **Rollback strategy**: Git tag-based rollback
- **Current version**: v0.18.7
- **Rollback procedure**: `git checkout v0.18.6 && uv sync`

## Exit Gate Checklist

- [x] ACB usage baseline captured (218 occurrences)
- [x] MCP CLI commands recorded
- [x] Health probe status documented
- [x] Dependency versions confirmed
- [x] Rollback procedure defined
- [x] Baselines attached and documented

## Next Steps

**✅ Phase 0 COMPLETE - Ready for Phase 1: Core Runtime Migration**

The baseline capture is complete and we have all the information needed to proceed with the migration. The recovery plan is in place and we understand the current state of ACB usage throughout the codebase.
