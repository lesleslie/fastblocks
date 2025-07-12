# Gather Action

The Gather action provides unified component discovery and collection for FastBlocks applications. It consolidates scattered gathering patterns throughout the framework, providing parallel processing, standardized error handling, and consistent caching strategies.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Usage](#usage)
  - [Routes](#routes)
  - [Templates](#templates)
  - [Middleware](#middleware)
  - [Models](#models)
  - [Application](#application)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Examples](#examples)
- [Performance Considerations](#performance-considerations)
- [Related Actions](#related-actions)

## Overview

The Gather action replaces scattered import_module + loop patterns with a unified, high-performance system for component discovery. It provides semantic interfaces for gathering routes, templates, middleware, models, and application components with parallel execution and intelligent caching.

## Features

- **Parallel processing** with configurable concurrency limits
- **Standardized error handling** with retry logic and partial success strategies
- **Unified caching** with configurable cache keys and TTL
- **Adapter integration** through protocols and dynamic imports
- **Comprehensive result tracking** with detailed metadata
- **Semantic interfaces** following ACB action patterns

## Usage

Import the gather action from FastBlocks:

```python
from fastblocks.actions.gather import gather
```

### Routes

Gather routes from adapters and base route files with parallel discovery:

```python
# Basic route gathering
routes_result = await gather.routes()
print(f"Found {routes_result.total_routes} routes")

# Custom sources and patterns
routes_result = await gather.routes(
    sources=["adapters", "base_routes"],
    patterns=["_routes.py", "routes.py"],
    include_base=True,
    include_adapters=True
)

# Access discovered routes
for route in routes_result.routes:
    print(f"Route: {route.path} -> {route.endpoint}")

# Check for errors
if routes_result.has_errors:
    for error in routes_result.errors:
        print(f"Error: {error}")
```

### Templates

Gather template components including loaders, extensions, processors, and filters:

```python
# Basic template gathering
templates_result = await gather.templates()
print(f"Gathered {templates_result.total_components} template components")

# Custom configuration
templates_result = await gather.templates(
    template_paths=[AsyncPath("templates"), AsyncPath("custom_templates")],
    loader_types=["redis", "storage", "filesystem"],
    extension_modules=["myapp.extensions"],
    admin_mode=True
)

# Access components
print(f"Loaders: {len(templates_result.loaders)}")
print(f"Extensions: {len(templates_result.extensions)}")
print(f"Filters: {len(templates_result.filters)}")
print(f"Context processors: {len(templates_result.context_processors)}")
```

### Middleware

Gather and build middleware stacks with position management:

```python
# Basic middleware gathering
middleware_result = await gather.middleware()
print(f"Built stack with {middleware_result.total_middleware} components")

# Custom middleware configuration
middleware_result = await gather.middleware(
    user_middleware=[
        Middleware(CustomMiddleware, param="value")
    ],
    system_overrides={
        MiddlewarePosition.SECURITY: CustomSecurityMiddleware
    },
    include_defaults=True,
    debug_mode=False
)

# Access middleware stack
for middleware in middleware_result.middleware_stack:
    print(f"Middleware: {middleware.cls.__name__}")
```

### Models

Gather SQLModel and Pydantic models from various sources:

```python
# Basic model gathering
models_result = await gather.models()
print(f"Discovered {models_result.total_models} models")

# Custom model gathering
models_result = await gather.models(
    sources=["base", "adapters", "custom"],
    patterns=["models.py", "_models.py"],
    include_admin=True,
    base_classes=[SQLModel, BaseModel]
)

# Access models by type
print(f"SQL models: {len(models_result.sql_models)}")
print(f"NoSQL models: {len(models_result.nosql_models)}")
print(f"Admin models: {len(models_result.admin_models)}")

# Access by adapter
for adapter_name, models in models_result.adapter_models.items():
    print(f"Adapter {adapter_name}: {len(models)} models")
```

### Application

Gather application components for initialization:

```python
# Basic application gathering
app_result = await gather.application()
print(f"Loaded {app_result.total_components} application components")

# Custom application gathering
app_result = await gather.application(
    include_adapters=True,
    include_acb_modules=True,
    include_dependencies=True,
    adapter_patterns=["__init__.py", "models.py", "views.py"],
    dependency_patterns=["models", "config", "cache"]
)

# Access components
print(f"Adapters: {len(app_result.adapters)}")
print(f"ACB modules: {len(app_result.acb_modules)}")
print(f"Dependencies: {len(app_result.dependencies)}")
print(f"Initializers: {len(app_result.initializers)}")
```

## API Reference

### Core Methods

#### `gather.routes()`

Gather routes from various sources with parallel discovery.

```python
async def routes(
    *,
    sources: list[str] = None,
    patterns: list[str] = None,
    include_base: bool = True,
    include_adapters: bool = True,
    strategy: GatherStrategy = None,
) -> RouteGatherResult
```

**Parameters:**
- `sources` (list[str], optional): Source types ["adapters", "base_routes", "custom"]
- `patterns` (list[str], optional): Filename patterns ["_routes.py", "routes.py"]
- `include_base` (bool, default=True): Include base routes from root_path/routes.py
- `include_adapters` (bool, default=True): Include routes from adapters
- `strategy` (GatherStrategy, optional): Custom gathering strategy

**Returns:**
- `RouteGatherResult`: Contains discovered routes and metadata

#### `gather.templates()`

Gather template components including loaders, extensions, and filters.

```python
async def templates(
    *,
    template_paths: list[AsyncPath] = None,
    loader_types: list[str] = None,
    extension_modules: list[str] = None,
    context_processor_paths: list[str] = None,
    filter_modules: list[str] = None,
    admin_mode: bool = False,
    strategy: GatherStrategy = None,
) -> TemplateGatherResult
```

**Parameters:**
- `template_paths` (list[AsyncPath], optional): Template search directories
- `loader_types` (list[str], optional): Loader types ["redis", "storage", "filesystem", "package"]
- `extension_modules` (list[str], optional): Module paths for Jinja2 extensions
- `context_processor_paths` (list[str], optional): Paths to context processor functions
- `filter_modules` (list[str], optional): Modules containing template filters
- `admin_mode` (bool, default=False): Include admin-specific components
- `strategy` (GatherStrategy, optional): Custom gathering strategy

**Returns:**
- `TemplateGatherResult`: Contains loaders, extensions, processors, and filters

#### `gather.middleware()`

Gather and build middleware stack with position management.

```python
async def middleware(
    *,
    user_middleware: list[Middleware] = None,
    system_overrides: dict[MiddlewarePosition, t.Any] = None,
    include_defaults: bool = True,
    debug_mode: bool = False,
    error_handler: t.Any = None,
    strategy: GatherStrategy = None,
) -> MiddlewareGatherResult
```

**Parameters:**
- `user_middleware` (list[Middleware], optional): User-defined middleware list
- `system_overrides` (dict, optional): Overrides for system middleware positions
- `include_defaults` (bool, default=True): Include default FastBlocks middleware
- `debug_mode` (bool, default=False): Enable debug mode for middleware
- `error_handler` (t.Any, optional): Custom error handler for ServerErrorMiddleware
- `strategy` (GatherStrategy, optional): Custom gathering strategy

**Returns:**
- `MiddlewareGatherResult`: Contains complete middleware stack

#### `gather.models()`

Gather SQLModel and Pydantic models from various sources.

```python
async def models(
    *,
    sources: list[str] = None,
    patterns: list[str] = None,
    include_base: bool = True,
    include_adapters: bool = True,
    include_admin: bool = True,
    base_classes: list[type] = None,
    strategy: GatherStrategy = None,
) -> ModelGatherResult
```

**Parameters:**
- `sources` (list[str], optional): Source types ["base", "adapters", "custom"]
- `patterns` (list[str], optional): Filename patterns ["models.py", "_models.py"]
- `include_base` (bool, default=True): Include base models from root_path/models.py
- `include_adapters` (bool, default=True): Include models from adapters
- `include_admin` (bool, default=True): Gather admin-enabled models
- `base_classes` (list[type], optional): Base classes to check for inheritance
- `strategy` (GatherStrategy, optional): Custom gathering strategy

**Returns:**
- `ModelGatherResult`: Contains SQL models, NoSQL models, and metadata

#### `gather.application()`

Gather application components for initialization.

```python
async def application(
    *,
    include_adapters: bool = True,
    include_acb_modules: bool = True,
    include_dependencies: bool = True,
    include_initializers: bool = True,
    adapter_patterns: list[str] = None,
    dependency_patterns: list[str] = None,
    strategy: GatherStrategy = None,
) -> ApplicationGatherResult
```

**Parameters:**
- `include_adapters` (bool, default=True): Include enabled adapters
- `include_acb_modules` (bool, default=True): Include ACB framework modules
- `include_dependencies` (bool, default=True): Include application dependencies
- `include_initializers` (bool, default=True): Include initialization functions
- `adapter_patterns` (list[str], optional): File patterns in adapters ["__init__.py", "models.py"]
- `dependency_patterns` (list[str], optional): Dependency module patterns
- `strategy` (GatherStrategy, optional): Custom gathering strategy

**Returns:**
- `ApplicationGatherResult`: Contains adapters, modules, dependencies, and initializers

## Configuration

### GatherStrategy

Configure gathering behavior with strategy options:

```python
from fastblocks.actions.gather import GatherStrategy, ErrorStrategy

strategy = GatherStrategy(
    parallel=True,                    # Enable parallel execution
    max_concurrent=10,               # Maximum concurrent tasks
    timeout=30.0,                    # Timeout in seconds
    error_strategy=ErrorStrategy.PARTIAL_SUCCESS,  # Error handling strategy
    cache_strategy=CacheStrategy.MEMORY_CACHE,     # Caching strategy
    retry_attempts=2,                # Number of retry attempts
    retry_delay=0.1                  # Delay between retries
)
```

### Error Strategies

- `FAIL_FAST`: Raise on first error
- `COLLECT_ERRORS`: Collect all errors, return at end
- `IGNORE_ERRORS`: Skip errors, continue processing
- `PARTIAL_SUCCESS`: Return successful results, log errors

### Cache Strategies

- `NO_CACHE`: No caching
- `MEMORY_CACHE`: In-memory caching
- `PERSISTENT`: Persistent caching across restarts

## Examples

### Complete Application Setup

```python
from fastblocks.actions.gather import gather

async def setup_application():
    """Complete application setup using gather action."""

    # Gather all components
    routes = await gather.routes()
    templates = await gather.templates(admin_mode=True)
    middleware = await gather.middleware(debug_mode=True)
    models = await gather.models(include_admin=True)
    app_components = await gather.application()

    # Create FastAPI application
    app = FastAPI()

    # Add routes
    for route in routes.routes:
        app.add_route(route)

    # Setup middleware stack
    for middleware in reversed(middleware.middleware_stack):
        app.add_middleware(middleware.cls, **middleware.kwargs)

    # Setup templates
    template_env = await create_template_environment(templates)

    # Register models for admin
    if models.admin_models:
        setup_admin(models.admin_models)

    return app
```

### Custom Component Discovery

```python
from fastblocks.actions.gather import gather, GatherStrategy, ErrorStrategy

async def discover_custom_components():
    """Discover components with custom configuration."""

    strategy = GatherStrategy(
        parallel=True,
        max_concurrent=5,
        error_strategy=ErrorStrategy.PARTIAL_SUCCESS
    )

    # Custom route discovery
    routes = await gather.routes(
        sources=["adapters", "custom"],
        patterns=["api_routes.py", "web_routes.py"],
        strategy=strategy
    )

    # Custom template discovery
    templates = await gather.templates(
        template_paths=[
            AsyncPath("templates"),
            AsyncPath("themes/default"),
            AsyncPath("custom_templates")
        ],
        loader_types=["filesystem", "redis"],
        strategy=strategy
    )

    return routes, templates
```

### Error Handling

```python
from fastblocks.actions.gather import gather

async def robust_gathering():
    """Example of robust error handling."""

    try:
        result = await gather.routes()

        if result.has_errors:
            logger.warning(f"Route gathering had {len(result.errors)} errors")

            for error in result.errors:
                logger.error(f"Route error: {error}")

        # Process successful routes
        logger.info(f"Successfully gathered {result.total_routes} routes")

        for adapter, routes in result.adapter_routes.items():
            logger.info(f"Adapter {adapter}: {len(routes)} routes")

    except Exception as e:
        logger.error(f"Critical error in route gathering: {e}")
        # Fallback to minimal routes
        result = RouteGatherResult(routes=create_default_routes())

    return result
```

## Performance Considerations

### Parallel Processing
- **Concurrency**: Adjust `max_concurrent` based on I/O vs CPU workload
- **Timeout**: Set appropriate timeouts for network operations
- **Memory**: Large concurrent operations may require significant memory

### Caching
- **Memory usage**: Cached results are stored in memory
- **Cache keys**: Unique keys prevent cache collisions
- **TTL**: Cached results persist until manual clear or restart

### Component Discovery
- **File I/O**: Discovery involves filesystem scanning and module imports
- **Import time**: Dynamic imports may be slower than static imports
- **Error recovery**: Partial success allows processing despite some failures

### Best Practices
- Use caching for repeated gather operations
- Configure appropriate concurrency limits
- Handle errors gracefully with partial success
- Clear caches when components change

## Related Actions

- [Sync Action](../sync/README.md): Synchronize gathered components with storage
- [Minify Action](../minify/README.md): Optimize gathered assets
- [ACB Actions](https://github.com/fastblocks/acb/tree/main/acb/actions): Core utility actions
