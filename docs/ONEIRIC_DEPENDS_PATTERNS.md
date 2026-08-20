# Oneiric Depends Patterns - `resolve_component_async()` Behavior

**Created**: 2025-11-18
**Updated**: 2026-08-19 (Phase 4 — Oneiric migration)
**Author**: FastBlocks Audit
**Purpose**: Document correct usage of `resolve_component_async()` and
its sync sibling `resolve_component()` to prevent common async-context
and coroutine-access errors.

______________________________________________________________________

## Critical Understanding: Async resolution

### The Problem

**Calling the resolver from a sync context (or without `await`) returns
either `None`, a coroutine, or raises `TypeError` depending on the
factory's signature.**

```python
# ❌ WRONG - forgot to await in async handler
templates = resolve_component_async(resolver, "fastblocks", "templates")
templates.app.render_template(...)  # AttributeError on coroutine

# ✅ CORRECT - await to get the resolved object
templates = await resolve_component_async(resolver, "fastblocks", "templates")
templates.app.render_template(...)  # Works!
```

### Factory Return Types

```
resolve_component_async(..., sync_factory)        → object            (awaitable)
resolve_component_async(..., async_factory)       → object            (awaitable, awaits internally)
resolve_component(..., sync_factory)              → object
resolve_component(..., async_factory)             → TypeError raised + coroutine closed
resolve_component_async(..., unknown key)         → None
```

**Always `await` `resolve_component_async()`. Use `resolve_component()`
only in sync code paths where the factory is known to be sync.**

______________________________________________________________________

## Correct Usage Patterns

### Pattern 1: Module-Level Resolver + Per-Handler Resolution

```python
# ✅ CORRECT - Async handler
from fastblocks.core.resolver import get_resolver, resolve_component_async

resolver = get_resolver()  # process-wide singleton


async def my_handler(request):
    templates = await resolve_component_async(resolver, "fastblocks", "templates")
    return await templates.app.render_template(request, "home.html")
```

### Pattern 2: Resolver + Conditional Access with Error Handling

```python
async def get_templates_safely():
    """Resolve templates with graceful fallback."""
    from fastblocks.core.resolver import get_resolver, resolve_component_async

    resolver = get_resolver()
    try:
        templates = await resolve_component_async(
            resolver, "fastblocks", "templates"
        )
        return templates
    except Exception:
        return None
```

### Pattern 3: Sync Code Path

```python
from fastblocks.core.resolver import get_resolver, resolve_component


def build_settings() -> dict[str, object]:
    """Sync helper — uses the sync resolver helper."""
    resolver = get_resolver()
    config = resolve_component(resolver, "fastblocks", "config")
    return {"deployed": bool(config and getattr(config, "deployed", False))}
```

If the registered factory returns a coroutine, `resolve_component()`
raises `TypeError("Async factory requires resolve_component_async: ...")`
and closes the unawaited coroutine — never silently discards it.

### Pattern 4: Class Initialization

```python
from fastblocks.core.resolver import get_resolver, resolve_component_async


class MyService:
    def __init__(self) -> None:
        # Resolve inside __init__ — caller must be async or pre-await.
        self.resolver = get_resolver()

    async def setup(self) -> None:
        self.templates = await resolve_component_async(
            self.resolver, "fastblocks", "templates"
        )
```

______________________________________________________________________

## Common Anti-Patterns (Causing 500 / TypeError)

### Anti-Pattern 1: Missing `await`

```python
# � WRONG - 150+ instances in legacy codebase
async def get_config():
    config = resolve_component_async(resolver, "fastblocks", "config")  # coroutine!
    return config.deployed  # AttributeError


# ✅ CORRECT
async def get_config():
    config = await resolve_component_async(resolver, "fastblocks", "config")
    return config.deployed
```

### Anti-Pattern 2: Accessing Coroutine Attributes

```python
# ❌ WRONG
templates = resolve_component_async(resolver, "fastblocks", "templates")  # coroutine
templates.app.render_template(...)  # AttributeError!


# ✅ CORRECT
templates = await resolve_component_async(resolver, "fastblocks", "templates")
await templates.app.render_template(...)
```

### Anti-Pattern 3: Comparison with `None` Before Awaiting

```python
# ❌ WRONG - coroutine is never None
config = resolve_component_async(resolver, "fastblocks", "config")
if config is None:  # Always False - coroutine != None
    ...


# ✅ CORRECT
config = await resolve_component_async(resolver, "fastblocks", "config")
if config is None:
    ...
```

### Anti-Pattern 4: Sync Function Context

```python
# ❌ WRONG - Can't await in sync function
def sync_function():
    config = resolve_component_async(resolver, "fastblocks", "config")  # can't await
    return config.deployed


# ✅ CORRECT - Make function async
async def async_function():
    config = await resolve_component_async(resolver, "fastblocks", "config")
    return config.deployed


# OR use the sync helper (preferred for sync code paths)
def sync_function():
    config = resolve_component(resolver, "fastblocks", "config")
    return config and config.deployed
```

______________________________________________________________________

## Migration Guide

### Step 1: Identify Problematic Calls

Search for: `resolve_component_async\(` (or `resolve_component\(`).

Check if the result is:

1. Awaited immediately
1. Passed to an async function
1. **Accessed without await** ← FIX THIS

### Step 2: Add Await

```python
# Before
config = resolve_component_async(resolver, "fastblocks", "config")

# After
config = await resolve_component_async(resolver, "fastblocks", "config")
```

### Step 3: Ensure Async Context

The calling function must be `async def`:

```python
# Before
def my_function():
    config = resolve_component_async(resolver, "fastblocks", "config")  # Can't await!


# After
async def my_function():
    config = await resolve_component_async(resolver, "fastblocks", "config")
```

### Step 4: Update Function Callers

If you made a function async, update all callers:

```python
# Before
result = my_function()

# After
result = await my_function()
```

______________________________________________________________________

## Locations Requiring Fixes (historical — pre-Oneiric audit)

The legacy ACB codebase had ~150 missing-await errors. The Oneiric
migration in 0.8.0 surfaced them and most were fixed in
`_events_integration`, `_health_integration`,
`_validation_integration`, and `_workflows_integration`. New code
should follow the patterns above from the start.

______________________________________________________________________

## Type Checking

### Enable Strict Checking

```bash
# Check for coroutine access errors
uv run pyright fastblocks/_health_integration.py

# Look for patterns like:
# "Cannot access attribute 'X' for class 'CoroutineType'"
# "Condition will always evaluate to False" (coroutine != None)
```

### Expected Errors Before Fix

```
error: Cannot access attribute "deployed" for class "CoroutineType[Any, Any, Any]"
error: Cannot access attribute "app" for class "CoroutineType[Any, Any, Any]"
error: Condition will always evaluate to False since the types
       "CoroutineType[Any, Any, Any]" and "None" have no overlap
```

### Expected After Fix

```
0 errors, 0 warnings, 0 information
```

______________________________________________________________________

## Performance Considerations

### Sequential vs Parallel Fetching

```python
# ❌ SLOW - Sequential
templates = await resolve_component_async(resolver, "fastblocks", "templates")
cache = await resolve_component_async(resolver, "fastblocks", "cache")
config = await resolve_component_async(resolver, "fastblocks", "config")

# ✅ FAST - Parallel (if dependencies are independent)
templates, cache, config = await asyncio.gather(
    resolve_component_async(resolver, "fastblocks", "templates"),
    resolve_component_async(resolver, "fastblocks", "cache"),
    resolve_component_async(resolver, "fastblocks", "config"),
)
```

### Caching Results

```python
# Cache at module level for repeated access
_templates_cache: object | None = None


async def get_templates():
    global _templates_cache
    if _templates_cache is None:
        resolver = get_resolver()
        _templates_cache = await resolve_component_async(
            resolver, "fastblocks", "templates"
        )
    return _templates_cache
```

______________________________________________________________________

## Summary

**Key Takeaways:**

1. ✅ **`resolve_component_async()` returns the resolved object directly when awaited**
1. ✅ **Always `await` it; never access attributes on the coroutine**
1. ✅ **Use `resolve_component()` only in sync code paths**
1. ✅ **Functions using the resolver must be `async def`**
1. ✅ **Update all callers to `await` async functions**

**Impact:**

- Prevents runtime AttributeErrors
- Enables proper type checking
- Improves IDE support

**Next Steps:**

1. Run `uv run pyright fastblocks` to surface any remaining coroutine-access bugs
2. Run tests to ensure no breakage
