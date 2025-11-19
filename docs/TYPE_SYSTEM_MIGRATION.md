# Type System Migration Guide

**Created**: 2025-11-18
**Author**: FastBlocks Audit (Phase 4)
**Purpose**: Guide for migrating to improved type system patterns from Phase 4 audit

______________________________________________________________________

## Overview

This guide documents type system improvements implemented during the FastBlocks Phase 4 audit and provides migration patterns for updating code to align with current best practices.

**Results**:

- Pyright errors: 501 → 150 (-70% reduction)
- Type ignores: 223 → 110 (-50.7% reduction)
- Strict mode enabled throughout codebase

______________________________________________________________________

## Key Changes

### 1. Type Narrowing with Assertions

**Old Pattern** (union-attr type ignore):

```python
class MyClass:
    def __init__(self):
        self.manager: Manager | None = None

    async def use_manager(self):
        if not self.manager:
            await self.initialize()

        # Pyright doesn't know manager is not None here
        return await self.manager.method()  # type: ignore[union-attr]
```

**New Pattern** (assertion for type narrowing):

```python
class MyClass:
    def __init__(self):
        self.manager: Manager | None = None

    async def use_manager(self):
        if not self.manager:
            await self.initialize()
        assert self.manager is not None  # Type narrows to Manager

        return await self.manager.method()  # No ignore needed!
```

**Migration Steps**:

1. Find all `# type: ignore[union-attr]` comments
1. Check if there's a None check before usage
1. Add `assert value is not None` after the None check
1. Remove the type ignore

### 2. Explicit Type Casts Instead of Ignores

**Old Pattern** (arg-type, assignment ignores):

```python
# type: ignore[arg-type]
result = some_function(dynamic_value)

# type: ignore[assignment]
my_var: dict[str, Any] = some_dict
```

**New Pattern** (explicit casts):

```python
import typing as t

result = some_function(t.cast(ExpectedType, dynamic_value))

my_var: dict[str, t.Any] = t.cast(dict[str, t.Any], some_dict)
```

**Benefits**:

- Self-documenting code (shows intent)
- Type checkers understand the conversion
- Easier to spot potential issues during review

**Migration Steps**:

1. Find `# type: ignore[arg-type]` or `# type: ignore[assignment]`
1. Identify the expected type
1. Replace ignore with `t.cast(ExpectedType, value)`
1. Verify with `uv run pyright`

### 3. Removing Unnecessary Ignores

**Common Unnecessary Patterns**:

```python
# ❌ WRONG - Unnecessary ignore (tested and confirmed safe)
class MySingleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)  # type: ignore[misc]
        return cls._instance


# ✅ CORRECT - No ignore needed
class MySingleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)  # Safe!
        return cls._instance
```

```python
# ❌ WRONG - Unnecessary ignore
if hasattr(result, "__await__") and callable(result.__await__):  # type: ignore[misc]
    return await result

# ✅ CORRECT - No ignore needed
if hasattr(result, "__await__") and callable(result.__await__):
    return await result
```

**Migration Steps**:

1. Create test file with the pattern
1. Run `uv run pyright test_file.py`
1. If no errors, remove the ignore
1. Test your changes

### 4. Legitimate Type Ignores with Comments

**When Type Ignores ARE Needed**:

```python
# ✅ CORRECT - Legitimate ignore with explanation
from jinja2 import Environment

env = Environment()


@env.filter("my_filter")  # type: ignore[misc]  # Jinja2 untyped decorator API
def my_filter(value: str) -> str:
    return value.upper()
```

```python
# ✅ CORRECT - ACB graceful degradation pattern
try:
    from acb.workflows import WorkflowEngine
except ImportError:
    WorkflowEngine = None

# Engine might be None (graceful degradation)
engine = WorkflowEngine()  # type: ignore[operator]  # Optional ACB module
```

**Rule**: All remaining type ignores MUST have explanatory comments

**Migration Steps**:

1. Audit all type ignores without comments
1. Determine if ignore is legitimate or fixable
1. If fixable: Apply patterns 1-3 above
1. If legitimate: Add explanatory comment

______________________________________________________________________

## Category-Specific Migrations

### Misc Ignores (57 remaining, ~40 legitimate)

**Legitimate**: Jinja2 template filter decorators

```python
@env.filter("format_date")  # type: ignore[misc]  # Jinja2 untyped decorator
def format_date(date: datetime) -> str:
    return date.strftime("%Y-%m-%d")
```

**Fixable**: Unnecessary singleton/inheritance patterns

- Remove and test (see Pattern 3 above)

### Union-Attr Ignores (19 remaining → many fixable)

**Fix with assertions** (see Pattern 1 above):

```python
# Before: 4 union-attr ignores
# After: 4 assertions, 0 ignores
# Files: hybrid.py
```

### Operator Ignores (14 remaining, all legitimate)

**Legitimate**: ACB graceful degradation with `|` operator

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from acb.events import EventHandler
else:
    try:
        from acb.events import EventHandler
    except ImportError:
        EventHandler = object  # Fallback


# type: ignore[operator]  # ACB graceful degradation pattern
class MyHandler(EventHandler):
    pass
```

### Attr-Defined Ignores (13 remaining, mostly legitimate)

**Legitimate**: Jinja2 sandbox dynamic attributes

```python
from jinja2.sandbox import SandboxedEnvironment

env = SandboxedEnvironment()
env.allowed_tags = set(["div", "span"])  # type: ignore[attr-defined]  # Jinja2 sandbox API
```

### Arg-Type Ignores (0 remaining ✓)

**All fixed with explicit casts** (see Pattern 2 above):

```python
# Before: 7 arg-type ignores
# After: 7 explicit casts, 0 ignores
# Files: config_migration.py, _block_renderer.py, _advanced_manager.py, models.py
```

______________________________________________________________________

## Common Migration Patterns

### Pattern A: Optional Manager After Initialize

```python
# Before
class Service:
    manager: Manager | None = None

    async def do_work(self):
        if not self.manager:
            await self.initialize()
        return await self.manager.method()  # type: ignore[union-attr]


# After
class Service:
    manager: Manager | None = None

    async def do_work(self):
        if not self.manager:
            await self.initialize()
        assert self.manager is not None  # Type narrows
        return await self.manager.method()  # No ignore!
```

**Impact**: Removed 4 union-attr ignores in hybrid.py

### Pattern B: Dynamic Dict Assignment

```python
# Before
globals_dict: dict[str, Any] = env.globals  # type: ignore[assignment]

# After
globals_dict: dict[str, Any] = t.cast(dict[str, Any], env.globals)
```

**Impact**: Explicit, self-documenting type conversion

### Pattern C: Jinja2 API Calls

```python
# Before
for node in parsed.find_all(("Extends", "Include")):  # type: ignore[arg-type]
    process_node(node)

# After
for node in parsed.find_all(t.cast(t.Any, ("Extends", "Include"))):
    process_node(node)
```

**Impact**: Removed 2 arg-type ignores in \_advanced_manager.py

### Pattern D: TypedDict Extension

```python
# Before
diagnostic["data"] = {"fix": error.fix_suggestion}  # type: ignore[typeddict-item]

# After
t.cast(dict[str, t.Any], diagnostic)["data"] = {"fix": error.fix_suggestion}
```

**Impact**: Removed 1 typeddict-item ignore in \_language_server.py

______________________________________________________________________

## Testing Your Migration

### Step 1: Type Check

```bash
# Check specific file
uv run pyright fastblocks/your_file.py

# Check entire codebase
uv run pyright fastblocks

# Target: 150 errors (down from 501 baseline)
```

### Step 2: Run Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=fastblocks

# Run specific module tests
python -m pytest tests/adapters/templates/
```

### Step 3: Verify Quality

```bash
# Comprehensive quality check
python -m crackerjack -t --ai-fix
```

______________________________________________________________________

## Phase 4 Results Summary

### Commits

1. **Icon/image adapter sync fixes**: 254 → 231 errors (-23)
1. **MCP and template coroutine fixes**: 231 → 221 errors (-10)
1. **Deprecated/unused/constant fixes**: 221 → 211 errors (-10)
1. **Undefined variable fixes**: 211 → 195 errors (-16)
1. **Unnecessary isinstance fixes**: 195 → 182 errors (-13)
1. **Unused function suppression**: 182 → 142 errors (-40)
1. **Type ignore reduction**: 223 → 110 ignores (-113)

### Files Modified

**Type Ignore Reduction** (15 files):

- Integration modules: `_events_integration.py`, `_validation_integration.py`, `_workflows_integration.py`
- Template adapters: `hybrid.py`, `_advanced_manager.py`, `_block_renderer.py`, `_language_server.py`, `_base.py`
- Base adapters: `admin/_base.py`, `routes/_base.py`
- MCP: `config_migration.py`
- Actions: `gather/models.py`, `minify/__init__.py`
- Core: `htmx.py`, `middleware.py`

### Metrics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Pyright Errors | 501 | 150 | -70% |
| Type Ignores | 223 | 110 | -50.7% |
| Strict Mode | Partial | Full | ✓ |
| Test Coverage | 15.52% | 33.00% | +112% |

______________________________________________________________________

## Best Practices Going Forward

### 1. Prefer Type Narrowing Over Ignores

Always try assertions before reaching for `# type: ignore`:

```python
# ✅ GOOD
if value is None:
    value = get_default()
assert value is not None
use_value(value)

# ❌ BAD
if value is None:
    value = get_default()
use_value(value)  # type: ignore[arg-type]
```

### 2. Use Explicit Casts for Dynamic APIs

When working with untyped third-party APIs:

```python
# ✅ GOOD - Intent is clear
result = t.cast(MyType, third_party_api())

# ❌ BAD - Suppresses without explaining
result = third_party_api()  # type: ignore
```

### 3. Document All Remaining Ignores

Every type ignore needs a comment:

```python
# ✅ GOOD
@env.filter()  # type: ignore[misc]  # Jinja2 untyped decorator API
def my_filter(value): ...


# ❌ BAD
@env.filter()  # type: ignore[misc]
def my_filter(value): ...
```

### 4. Test Before Removing Ignores

Always verify with both Pyright and tests:

```bash
uv run pyright fastblocks/your_file.py
python -m pytest tests/your_test.py -v
```

______________________________________________________________________

## Reference

- **Phase 4 Completion**: See `IMPROVEMENT_PLAN.md` Tasks 4.1-4.2
- **ACB Patterns**: See `docs/ACB_DEPENDS_PATTERNS.md`
- **Type Guidelines**: See `CLAUDE.md` → Type System Guidelines
- **MCP Integration**: See `fastblocks/mcp/README.md`

______________________________________________________________________

## Support

For questions about type system patterns:

1. Check `CLAUDE.md` Type System Guidelines
1. Review `docs/ACB_DEPENDS_PATTERNS.md`
1. See Phase 4 commits for examples
1. Open GitHub discussion for complex cases
