# FastBlocks: Actions

Actions are modular, self-contained utility functions that perform specific tasks in the FastBlocks framework. They follow semantic patterns and are designed to streamline common operations in web application development.

## Table of Contents

- [Overview](#overview)
- [Available Actions](#available-actions)
  - [Gather](#gather)
  - [Sync](#sync)
  - [Minify](#minify)
- [Action Philosophy](#action-philosophy)
- [Best Practices](#best-practices)
- [Creating Custom Actions](#creating-custom-actions)

## Overview

FastBlocks actions provide utility functions for web application tasks like component gathering, synchronization, and optimization. They are:

- **Semantic**: Follow verb-based naming with operation-specific methods
- **Adapter-aware**: Use protocols and dynamic imports to work with adapters
- **Self-contained**: Each action focuses on specific functionality
- **Async-friendly**: Built for async/await patterns
- **Error-resilient**: Include comprehensive error handling and retry logic

## Available Actions

FastBlocks comes with several built-in actions for web application development:

| Action | Description | Key Methods |
|--------|-------------|-------------|
| **Gather** | Component discovery and collection | `gather.routes()`, `gather.templates()`, `gather.middleware()`, `gather.models()`, `gather.application()` |
| **Sync** | Bidirectional synchronization | `sync.templates()`, `sync.settings()`, `sync.cache()` |
| **Minify** | Code and asset optimization | `minify.html()`, `minify.css()`, `minify.js()` |

### Gather

The Gather action consolidates component discovery patterns throughout FastBlocks, providing unified interfaces for collecting routes, templates, middleware, models, and application components.

#### Key Features:
- **Parallel processing** with concurrency control
- **Standardized error handling** and retry logic
- **Unified caching** strategies across components
- **Adapter integration** through protocols

#### Usage Example:
```python
from fastblocks.actions.gather import gather

# Gather routes from adapters and base files
routes_result = await gather.routes()
print(f"Found {routes_result.total_routes} routes")

# Gather template components
templates_result = await gather.templates()
print(f"Loaded {len(templates_result.loaders)} template loaders")

# Gather middleware stack
middleware_result = await gather.middleware()
print(f"Built stack with {middleware_result.total_middleware} components")

# Gather models from various sources
models_result = await gather.models()
print(f"Discovered {models_result.total_models} models")

# Gather application components
app_result = await gather.application()
print(f"Loaded {app_result.total_components} application components")
```

**[→ Read the full Gather documentation](./gather/README.md)**

### Sync

The Sync action provides bidirectional synchronization between filesystem and cloud storage with intelligent conflict resolution and cache consistency management.

#### Key Features:
- **Bidirectional sync** with configurable conflict resolution
- **Incremental sync** based on modification times and content hashes
- **Atomic operations** with backup capability
- **Cache coordination** and invalidation

#### Usage Example:
```python
from fastblocks.actions.sync import sync

# Sync templates between filesystem and storage
templates_result = await sync.templates()
print(f"Synced {len(templates_result.synced_items)} templates")

# Sync settings with config reload
settings_result = await sync.settings(reload_config=True)
print(f"Synced settings for {len(settings_result.adapters_affected)} adapters")

# Refresh cache layers for consistency
cache_result = await sync.cache(operation="refresh")
print(f"Refreshed {len(cache_result.invalidated_keys)} cache entries")
```

**[→ Read the full Sync documentation](./sync/README.md)**

### Minify

The Minify action provides code and asset optimization for web applications, reducing file sizes for better performance.

#### Key Features:
- **HTML minification** with whitespace and comment removal
- **CSS optimization** with redundancy elimination
- **JavaScript compression** with safe transformations
- **Preserves functionality** while reducing size

#### Usage Example:
```python
from fastblocks.actions.minify import minify

# Minify HTML content
html_content = "<html><body>  <h1>Hello</h1>  </body></html>"
minified_html = minify.html(html_content)

# Minify CSS
css_content = "body { margin: 0; padding: 0; }"
minified_css = minify.css(css_content)

# Minify JavaScript
js_content = "function hello() { console.log('Hello, World!'); }"
minified_js = minify.js(js_content)
```

**[→ Read the full Minify documentation](./minify/README.md)**

## Action Philosophy

FastBlocks actions follow a semantic pattern inspired by ACB's action system:

### Semantic Naming
- **Actions are verbs**: `gather`, `sync`, `minify`
- **Methods are operations**: `.routes()`, `.templates()`, `.cache()`
- **Clear intent**: Each method has a specific, obvious purpose

### Adapter Awareness
Actions work with adapters through protocols and dynamic imports:

```python
# ✅ Good: Dynamic import via protocol
storage = depends.get("storage")
await storage.templates.read(path)

# ✅ Good: Dynamic class import
module = __import__("fastblocks.adapters.templates.jinja2", fromlist=["ChoiceLoader"])
ChoiceLoader = getattr(module, "ChoiceLoader")

# ❌ Avoid: Direct adapter imports
from fastblocks.adapters.templates.jinja2 import ChoiceLoader
```

### Error Resilience
All actions include:
- **Comprehensive error handling** with meaningful messages
- **Retry logic** with exponential backoff
- **Partial success** strategies for batch operations
- **Graceful degradation** when optional components fail

## Best Practices

### 1. Use Semantic Interfaces
```python
# ✅ Semantic and clear
await gather.routes()
await sync.templates()
await minify.css(content)

# ❌ Generic and unclear
await process_components("routes")
await transfer_files("templates", "bidirectional")
```

### 2. Handle Results Properly
```python
result = await gather.templates()

if result.has_errors:
    logger.warning(f"Template gathering had {len(result.errors)} errors")

for error in result.errors:
    logger.error(f"Template error: {error}")

print(f"Successfully gathered {result.total_components} template components")
```

### 3. Use Strategy Configuration
```python
from fastblocks.actions.gather import GatherStrategy

strategy = GatherStrategy(
    parallel=True,
    max_concurrent=5,
    timeout=30.0,
    error_strategy=ErrorStrategy.PARTIAL_SUCCESS
)

result = await gather.routes(strategy=strategy)
```

### 4. Leverage Caching
```python
# Actions automatically cache results based on parameters
result1 = await gather.routes()  # Executes gathering
result2 = await gather.routes()  # Returns cached result

# Clear cache when needed
from fastblocks.actions.gather.strategies import clear_cache
clear_cache("routes:base:adapters")
```

## Creating Custom Actions

FastBlocks follows the ACB semantic action pattern. Create custom actions by:

### 1. Directory Structure
```
myproject/
├── actions/
│   ├── __init__.py
│   └── validate/
│       ├── __init__.py
│       └── README.md
```

### 2. Action Implementation
```python
# myproject/actions/validate/__init__.py
__all__ = ["validate"]

class Validate:
    """Semantic validate action for data validation operations."""

    @staticmethod
    def email(email: str) -> bool:
        """Validate an email address."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    async def url(url: str) -> bool:
        """Validate a URL by checking accessibility."""
        # Implementation with async HTTP check
        return True

# Export semantic action instance
validate = Validate()
```

### 3. Usage
```python
from myproject.actions.validate import validate

is_valid_email = validate.email("user@example.com")
is_accessible = await validate.url("https://example.com")
```

### 4. Documentation
Create a `README.md` following the pattern of existing actions with:
- Clear overview and features
- Usage examples with code
- API reference with parameters and return types
- Performance considerations
- Related actions

## Related Resources

- [ACB Actions Documentation](https://github.com/fastblocks/acb/tree/main/acb/actions)
- [FastBlocks Adapters Documentation](../adapters/README.md)
- [FastBlocks Core Documentation](../README.md)
