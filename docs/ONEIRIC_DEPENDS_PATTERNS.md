# ACB Depends Patterns - depends.get() Behavior

**Created**: 2025-11-18
**Author**: FastBlocks Audit
**Purpose**: Document correct usage of `depends.get()` to prevent coroutine access errors

______________________________________________________________________

## Critical Understanding: depends.get() is Async

### The Problem

**`depends.get()` returns a coroutine, NOT the actual object.**

```python
# ❌ WRONG - Returns coroutine
config = depends.get("config")
print(type(config))  # <class 'coroutine'>
config.deployed  # AttributeError: coroutine has no 'deployed'

# ✅ CORRECT - Await to get object
config = await depends.get("config")
print(type(config))  # <class 'acb.config.Config'>
config.deployed  # Works!
```

### Test Results

```
depends.get('config')     → <coroutine object>  (must await)
depends.get('templates')  → <coroutine object>  (must await)
depends.get('cache')      → <coroutine object>  (must await)
depends.get('query')      → <coroutine object>  (must await)
```

**All `depends.get()` calls return coroutines and MUST be awaited.**

______________________________________________________________________

## Correct Usage Patterns

### Pattern 1: Module-Level Access in Async Functions

```python
# ✅ CORRECT - Async function
async def my_handler(request):
    config = await depends.get("config")  # Await the coroutine
    templates = await depends.get("templates")

    if config.deployed:
        return await templates.app.render_template(request, "prod.html")
    return await templates.app.render_template(request, "dev.html")
```

### Pattern 2: Function Parameter Injection (Preferred)

```python
from acb.depends import Inject, depends


# ✅ BEST - Modern ACB 0.25.1+ pattern
@depends.inject
async def my_handler(request, config: Inject[Config], templates: Inject[Templates]):
    # config and templates are already resolved objects!
    if config.deployed:
        return await templates.app.render_template(request, "prod.html")
```

**Benefits:**

- No manual `await depends.get()` needed
- Type hints work correctly
- IDE autocomplete works
- Cleaner, more testable code

### Pattern 3: Class Initialization

```python
from acb.depends import Inject, depends


class MyService:
    @depends.inject
    def __init__(self, config: Inject[Config]):
        # config is already resolved
        self.config = config
        self.is_prod = config.deployed
```

### Pattern 4: Conditional Access with Error Handling

```python
async def get_templates_safely():
    """Get templates with graceful fallback."""
    try:
        templates = await depends.get("templates")
        return templates
    except Exception:
        return None
```

______________________________________________________________________

## Common Anti-Patterns (Causing 501 Errors)

### Anti-Pattern 1: Missing await

```python
# ❌ WRONG - 150+ instances in codebase
def get_config():
    config = depends.get("config")  # Returns coroutine!
    return config.deployed  # Error: coroutine has no 'deployed'


# ✅ CORRECT
async def get_config():
    config = await depends.get("config")
    return config.deployed
```

### Anti-Pattern 2: Accessing Coroutine Attributes

```python
# ❌ WRONG - Found in middleware.py, initializers.py, etc.
templates = depends.get("templates")  # Coroutine
templates.app.render_template(...)  # Error!

# ✅ CORRECT
templates = await depends.get("templates")
await templates.app.render_template(...)
```

### Anti-Pattern 3: Comparison with None

```python
# ❌ WRONG - Coroutine is never None
config = depends.get("config")  # Coroutine
if config is None:  # Always False - coroutine != None
    ...

# ✅ CORRECT
config = await depends.get("config")
if config is None:
    ...
```

### Anti-Pattern 4: Non-Async Function Context

```python
# ❌ WRONG - Can't await in sync function
def sync_function():
    config = depends.get("config")  # Can't await here!
    return config.deployed


# ✅ CORRECT - Make function async
async def async_function():
    config = await depends.get("config")
    return config.deployed


# OR use injection (preferred)
@depends.inject
def sync_with_injection(config: Inject[Config]):
    return config.deployed  # Works in sync function!
```

______________________________________________________________________

## Migration Guide

### Step 1: Identify Problematic Calls

Search for: `depends.get\(["\']`

Check if the result is:

1. Awaited immediately
1. Passed to an async function
1. **Accessed without await** ← FIX THIS

### Step 2: Add Await

```python
# Before
config = depends.get("config")

# After
config = await depends.get("config")
```

### Step 3: Ensure Async Context

Function must be `async def`:

```python
# Before
def my_function():
    config = depends.get("config")  # Can't await!


# After
async def my_function():
    config = await depends.get("config")  # Can await!
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

## Locations Requiring Fixes

### High Priority (Integration Files - ~60 errors)

1. **`fastblocks/_health_integration.py`** - 30+ coroutine access errors
1. **`fastblocks/_events_integration.py`** - 15+ errors
1. **`fastblocks/_validation_integration.py`** - 10+ errors
1. **`fastblocks/_workflows_integration.py`** - 15+ errors

Pattern: All missing `await` on `depends.get()` calls

### Medium Priority (Actions - ~30 errors)

1. **`fastblocks/actions/gather/middleware.py`** - 2 errors
1. **`fastblocks/actions/gather/routes.py`** - 2 errors
1. **`fastblocks/actions/gather/templates.py`** - 5 errors
1. **`fastblocks/actions/query/parser.py`** - 6 errors
1. **`fastblocks/actions/sync/*.py`** - 15+ errors

### Lower Priority (Adapters - ~60 errors)

1. **`fastblocks/middleware.py`** - 15 errors
1. **`fastblocks/adapters/app/default.py`** - 10 errors
1. **`fastblocks/adapters/admin/sqladmin.py`** - 1 error
1. **`fastblocks/adapters/auth/*.py`** - 6 errors
1. **`fastblocks/adapters/icons/*.py`** - 50+ errors (type stub issues)

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
config = await depends.get("config")
templates = await depends.get("templates")
cache = await depends.get("cache")

# ✅ FAST - Parallel (if dependencies are independent)
config, templates, cache = await asyncio.gather(
    depends.get("config"),
    depends.get("templates"),
    depends.get("cache"),
)
```

### Caching Results

```python
# Cache at module level for repeated access
_config_cache = None


async def get_config():
    global _config_cache
    if _config_cache is None:
        _config_cache = await depends.get("config")
    return _config_cache
```

______________________________________________________________________

## Summary

**Key Takeaways:**

1. ✅ **`depends.get()` ALWAYS returns a coroutine**
1. ✅ **MUST use `await` to get the actual object**
1. ✅ **Prefer `@depends.inject` with `Inject[Type]` parameters**
1. ✅ **Functions using `depends.get()` must be `async def`**
1. ✅ **Update all callers to `await` the function**

**Impact:**

- Fixes ~150 of 501 Pyright errors
- Prevents runtime AttributeErrors
- Enables proper type checking
- Improves IDE support

**Next Steps:**

1. Fix integration files (highest error density)
1. Fix actions module
1. Fix adapters
1. Verify with `uv run pyright fastblocks`
1. Run tests to ensure no breakage
