# jinja2-async-environment Usage Pattern for FastBlocks

**Date**: 2025-10-26
**Component**: FastBlocks Templates Adapter
**Status**: Recommended Action Required
**Priority**: Medium (affects template inheritance reliability)

## Summary

FastBlocks' `AsyncTemplateRenderer` currently uses Jinja2's standard `template.render_async()` API pattern (line 338 of `_async_renderer.py`), which is **incompatible with template inheritance** when using jinja2-async-environment.

## Current Implementation

**File**: `fastblocks/adapters/templates/_async_renderer.py`

**Lines 324-339** - `_render_standard()` method:

```python
async def _render_standard(self, render_context: RenderContext) -> str:
    """Render template using standard mode."""
    if not self.base_templates or not self.base_templates.app:
        raise RuntimeError("Templates not initialized")

    template = self.base_templates.app.env.get_template(render_context.template_name)

    # Use secure environment if requested
    if render_context.secure_render and self.hybrid_manager:
        env = self.hybrid_manager._get_template_environment(secure=True)
        template = env.get_template(render_context.template_name)

    rendered = await template.render_async(render_context.context)  # ❌ LINE 338
    return t.cast(str, rendered)
```

## The Problem

jinja2-async-environment generates templates as **async generators** that must be iterated with `async for`. Jinja2's standard `render_async()` method is designed for the core Jinja2 async implementation and does NOT properly handle jinja2-async-environment's async generator pattern for **template inheritance**.

**Impact**:

- ✅ **Simple templates work fine** (no inheritance)
- ❌ **Templates with inheritance fail** with `TypeError: 'async for' requires an object with __aiter__ method, got coroutine`
- ❌ **Block rendering** may fail in inherited templates

## Root Cause

The jinja2-async-environment library:

1. Generates async templates as **async generator functions** via custom code generation
1. These generators must be **directly called** and iterated with `async for`
1. The library's own tests **bypass `render_async()` entirely** and call `template.root_render_func()` directly

Using `render_async()` creates a mismatch between what jinja2-async-environment generates and what Jinja2's standard API expects.

## Recommended Fix

### Option A: Use root_render_func() Pattern ✅ RECOMMENDED

Change the rendering pattern to match how jinja2-async-environment is designed:

**Before** (current code - line 338):

```python
rendered = await template.render_async(render_context.context)
return t.cast(str, rendered)
```

**After** (correct pattern):

```python
# Use root_render_func directly for jinja2-async-environment compatibility
# This is required for template inheritance to work properly
ctx = template.new_context(render_context.context)
result = []
async for chunk in template.root_render_func(ctx):
    result.append(chunk)
return "".join(result)
```

**Why This Works**:

- `template.root_render_func()` returns an **async generator** (correct type)
- Iterating with `async for` properly consumes the generator
- Template inheritance and blocks work correctly
- Matches jinja2-async-environment's intended usage pattern

### Option B: Keep render_async() and Accept Limitations ⚠️

If you choose to keep the current pattern:

- **Simple templates will continue working**
- **Template inheritance will be unreliable**
- **Users must avoid using Jinja2 inheritance features** (extends, blocks, super)

This is **not recommended** as it severely limits template functionality.

## Implementation Steps (Option A)

1. **Update `_render_standard()` method** (lines 324-339):

```python
async def _render_standard(self, render_context: RenderContext) -> str:
    """Render template using standard mode.

    Uses root_render_func() directly for jinja2-async-environment compatibility.
    This pattern is required for template inheritance to work properly.
    """
    if not self.base_templates or not self.base_templates.app:
        raise RuntimeError("Templates not initialized")

    template = self.base_templates.app.env.get_template(render_context.template_name)

    # Use secure environment if requested
    if render_context.secure_render and self.hybrid_manager:
        env = self.hybrid_manager._get_template_environment(secure=True)
        template = env.get_template(render_context.template_name)

    # Use root_render_func directly instead of render_async()
    # This is required for jinja2-async-environment compatibility
    ctx = template.new_context(render_context.context)
    result = []
    async for chunk in template.root_render_func(ctx):
        result.append(chunk)
    return "".join(result)
```

2. **Update `_render_block()` method** (lines 356-371) if needed:

The current implementation uses `template.render_block()` which is synchronous. If you need async block rendering with inheritance, you may need to adjust this as well.

3. **Test with inheritance templates**:

Create a test to verify template inheritance works:

```python
# templates/base.html
"""
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}Default Title{% endblock %}</title>
</head>
<body>
    {% block content %}{% endblock %}
</body>
</html>
"""

# templates/child.html
"""
{% extends "base.html" %}

{% block title %}{{ page_title }}{% endblock %}

{% block content %}
<h1>{{ heading }}</h1>
<p>{{ message }}</p>
{% endblock %}
"""


# Test code
async def test_inheritance():
    render_context = RenderContext(
        template_name="child.html",
        context={
            "page_title": "Test Page",
            "heading": "Welcome",
            "message": "Template inheritance works!",
        },
    )
    result = await renderer.render(render_context)
    assert "<title>Test Page</title>" in result.content
    assert "<h1>Welcome</h1>" in result.content
```

## Additional Considerations

### Streaming Mode

Your `_render_streaming()` method (lines 393-416) already uses an async generator pattern:

```python
async def _stream_template_chunks(
    self, template: t.Any, render_context: RenderContext
) -> AsyncIterator[str]:
    """Internal async generator for streaming template chunks."""
    async for chunk in template.generate_async(
        render_context.context
    ):  # ✅ Already correct
        # Yield chunks of specified size
        if len(chunk) > render_context.chunk_size:
            for i in range(0, len(chunk), render_context.chunk_size):
                yield chunk[i : i + render_context.chunk_size]
        else:
            yield chunk
```

This is already correct and uses the proper async iteration pattern. However, you may want to verify that `template.generate_async()` works with inheritance, or switch to using `root_render_func()` here as well for consistency.

### Secure Rendering

If using the hybrid manager's secure environment (line 334-336), ensure that secure environment also properly generates jinja2-async-environment compatible templates.

### Performance Impact

**None expected**. The `root_render_func()` pattern is actually the **more direct** approach with potentially **better performance** since it:

- Bypasses Jinja2's `render_async()` wrapper
- Directly uses the compiled template function
- Eliminates compatibility layer overhead

## Testing Recommendations

1. **Create inheritance test suite**:

   - Simple inheritance (extends + blocks)
   - Nested inheritance (3+ levels)
   - Multiple blocks in child templates
   - Super() calls to parent blocks

1. **Test all render modes**:

   - Standard mode (most important)
   - Fragment mode
   - Block mode
   - Streaming mode
   - HTMX mode

1. **Test edge cases**:

   - Empty blocks
   - Blocks with complex logic
   - Blocks with nested templates (include)
   - Dynamic block names

## Related Issues

This issue was discovered while fixing the ACB templates adapter, which uses the same jinja2-async-environment library. The same pattern fix was applied to ACB and should be applied here.

**Related Documentation**:

- jinja2-async-environment bug analysis: `https://github.com/lesleslie/jinja2-async-environment/blob/main/docs/TEMPLATE_INHERITANCE_BUG_ANALYSIS.md`
- ACB templates adapter implementation: `https://github.com/lesleslie/acb/blob/main/acb/adapters/templates/jinja2.py`

## Conclusion

**Recommendation**: Implement Option A (use root_render_func pattern) to ensure reliable template inheritance support in FastBlocks.

**Time Estimate**: 15-20 minutes for implementation + testing
**Risk**: Low (direct pattern replacement)
**Impact**: High (enables full Jinja2 template inheritance features)

This change will make FastBlocks' template rendering fully compatible with jinja2-async-environment's architecture while maintaining all existing functionality.
