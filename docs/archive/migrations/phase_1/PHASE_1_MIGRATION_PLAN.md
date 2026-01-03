# Phase 1: Core Runtime Migration - Implementation Plan

## Migration Strategy

We'll migrate the core runtime files in this order:

### 1. `fastblocks/main.py` - Core Registration and DI

**ACB → Oneiric Mapping:**

- `from acb import ensure_registration, register_pkg` → `from oneiric.core.resolution import register_pkg`
- `from acb.adapters import register_adapters, root_path` → Oneiric adapter system
- `from acb.depends import depends` → `oneiric.core.resolution.Resolver`

### 2. `fastblocks/initializers.py` - Package Registration

**ACB → Oneiric Mapping:**

- `from acb import register_pkg` → `from oneiric.core.resolution import register_pkg`
- `from acb.config import AdapterBase, Config` → Oneiric settings
- `from acb.depends import depends` → Oneiric resolver

### 3. `fastblocks/middleware.py` - Middleware DI

**ACB → Oneiric Mapping:**

- `from acb.debug import debug` → Oneiric logging
- `from acb.depends import depends` → Oneiric resolver
- `from acb.adapters import get_adapter` → Oneiric adapter resolution

### 4. `fastblocks/exceptions.py` - Exception Handling DI

**ACB → Oneiric Mapping:**

- `from acb.depends import depends` → Oneiric resolver

### 5. `fastblocks/caching.py` - Caching DI

**ACB → Oneiric Mapping:**

- `from acb.actions.hash import hash` → Oneiric hashing
- `from acb.adapters import get_adapter` → Oneiric adapter resolution
- `from acb.depends import depends` → Oneiric resolver

## Implementation Approach

1. **Incremental Migration**: Migrate one file at a time, test after each
1. **Dual Import Strategy**: Use try/except blocks to maintain compatibility during transition
1. **Logging**: Add migration logs to track progress
1. **Testing**: Verify each component works after migration

## Migration Order

```bash
# 1. main.py - Core runtime
# 2. initializers.py - Package registration
# 3. middleware.py - Request processing
# 4. exceptions.py - Error handling
# 5. caching.py - Performance layer
```

## Verification Plan

After each migration:

1. Run basic import test: `python -c "import fastblocks.main"`
1. Test core functionality: `python -m fastblocks --help`
1. Verify no regression in existing functionality

Let's start with the first file: `fastblocks/main.py`
