# FastBlocks Core Features

> **FastBlocks Documentation**: [Main](../README.md) | [Core Features](./README.md) | [Actions](./actions/README.md) | [Adapters](./adapters/README.md)

FastBlocks provides a set of core features that form the foundation of the framework. These components work together to create a powerful, asynchronous web application framework optimized for server-side rendering with HTMX. The modular, component-based architecture enables "batteries-included but customizable" application development, allowing you to benefit from comprehensive defaults while maintaining the flexibility to replace, customize, or extend any component.

## Framework Architecture

### Relationship with Starlette

FastBlocks extends [Starlette](https://www.starlette.io/) to provide enhanced capabilities for server-side rendered applications:

- **Application Class**: The `FastBlocks` class directly inherits from Starlette's `Starlette` class
- **Middleware System**: Uses and extends Starlette's middleware system with additional components
- **Routing**: Builds on Starlette's routing system with HTMX-specific enhancements
- **Request/Response**: Extends Starlette's request and response objects for HTMX integration

By extending Starlette, FastBlocks maintains compatibility with the ASGI ecosystem while adding specialized features for server-side rendering.

### Relationship with ACB

FastBlocks is built on top of [Asynchronous Component Base (ACB)](https://github.com/lesleslie/acb), which provides the underlying infrastructure. FastBlocks extends ACB with web-specific features:

- **ACB Foundation**: Dependency injection, configuration system, component registration, and adapter pattern
- **FastBlocks Extensions**: Web-specific components like HTMX integration, template rendering, and middleware

This separation of concerns allows FastBlocks to focus on web application features while leveraging ACB's robust component architecture.

### Component-Based Architecture Benefits

FastBlocks' component-based architecture provides several significant advantages:

- **Selective Inclusion**: Use only the components you need for your application
- **Granular Replacements**: Replace individual components without rewriting the entire application
- **Clear Boundaries**: Well-defined interfaces between components simplify testing and maintenance
- **Consistent Patterns**: Common patterns across components reduce learning curve and cognitive load
- **Independent Evolution**: Components can evolve at different rates while maintaining compatibility
- **Infrastructure Flexibility**: Swap infrastructure components to support different cloud providers
- **Deployment Options**: Support both traditional and containerized deployments with the same codebase

## Table of Contents

- [Application Class](#application-class)
- [Middleware](#middleware)
  - [Default Middleware Stack](#default-middleware-stack)
  - [Available Middleware Components](#available-middleware-components)
    - [CSRFMiddleware](#csrfmiddleware)
    - [SessionMiddleware](#sessionmiddleware)
    - [HtmxMiddleware](#htmxmiddleware)
    - [CurrentRequestMiddleware](#currentrequestmiddleware)
    - [BrotliMiddleware](#brotlimiddleware)
    - [SecureHeadersMiddleware](#secureheadersmiddleware)
    - [CacheMiddleware](#cachemiddleware)
    - [CacheControlMiddleware](#cachecontrolmiddleware)
  - [Custom Middleware](#custom-middleware)
- [Exception Handling](#exception-handling)
- [Dependency Injection](#dependency-injection)
- [Configuration System](#configuration-system)
- [Caching](#caching)

## Application Class

The `FastBlocks` class extends Starlette's application class with additional features specifically designed for HTMX and template-based applications.

### Starlette Extension

FastBlocks directly inherits from Starlette's application class:

```python
from starlette.applications import Starlette

class FastBlocks(Starlette):
    """FastBlocks application class extending Starlette."""
```

This inheritance means that FastBlocks maintains full compatibility with Starlette's API while adding specialized features for server-side rendering and HTMX integration.

### Usage Example

```python
from fastblocks.applications import FastBlocks
from starlette.routing import Route

async def homepage(request):
    # FastBlocks adds template rendering capabilities to the request object
    return await request.app.templates.app.render_template(
        request, "index.html", context={"title": "FastBlocks Demo"}
    )

routes = [
    Route("/", endpoint=homepage)
]

app = FastBlocks(routes=routes)
```

### Key Extensions to Starlette

- **Automatic Template Setup**: Templates are automatically configured and made available via `app.templates`
- **Enhanced Request Objects**: Extends Starlette's request objects with HTMX-specific properties
- **Middleware Configuration**: Automatic configuration of middleware based on application settings
- **Model Integration**: Automatic integration with SQLAlchemy models via `app.models`
- **Logging Integration**: Automatic configuration of logging with support for Logfire
- **Error Handling**: Enhanced error handling with custom error pages

## Middleware

FastBlocks includes a comprehensive middleware stack that enhances the functionality of your application. These middleware components process requests and responses at various stages of the request lifecycle.

### Extending Starlette's Middleware System

FastBlocks builds on Starlette's middleware system, which follows the ASGI specification. While Starlette provides a basic middleware framework, FastBlocks extends it with:

- **Pre-configured Stack**: A carefully ordered set of middleware components
- **HTMX-specific Middleware**: Components designed for server-side rendering with HTMX
- **Configuration-driven**: Middleware that can be enabled/disabled through configuration
- **Enhanced Security**: Additional security-focused middleware components

### Default Middleware Stack

```python
# Default middleware stack
middleware = [
    CSRFMiddleware,               # CSRF protection
    SessionMiddleware,            # Session management
    HtmxMiddleware,               # HTMX request processing
    CurrentRequestMiddleware,     # Request context
    BrotliMiddleware,             # Response compression
    SecureHeadersMiddleware,      # Security headers (production only)
]
```

### Available Middleware Components

#### CSRFMiddleware

Provides protection against Cross-Site Request Forgery attacks by requiring a CSRF token for state-changing requests.

```python
from fastblocks.middleware import CSRFMiddleware
from starlette.applications import Starlette

app = Starlette()
app = CSRFMiddleware(app, secret="your-secret-key")
```

#### SessionMiddleware

Manages user sessions via cookies.

```python
from fastblocks.middleware import SessionMiddleware
from starlette.applications import Starlette

app = Starlette()
app = SessionMiddleware(app, secret_key="your-secret-key")
```

#### HtmxMiddleware

Processes HTMX-specific headers and makes HTMX request information available in the request object.

```python
from fastblocks.middleware import HtmxMiddleware
from starlette.applications import Starlette

app = Starlette()
app = HtmxMiddleware(app)
```

#### CurrentRequestMiddleware

Makes the current request available via a context variable, allowing access to the request outside of the request handler.

```python
from fastblocks.middleware import CurrentRequestMiddleware, get_request
from starlette.applications import Starlette

app = Starlette()
app = CurrentRequestMiddleware(app)

# Later, in any function
def some_function():
    request = get_request()
    if request is not None:
        # Use request
        pass
```

#### BrotliMiddleware

Compresses responses using Brotli compression to reduce payload sizes.

```python
from fastblocks.middleware import BrotliMiddleware
from starlette.applications import Starlette

app = Starlette()
app = BrotliMiddleware(app, quality=3)
```

#### SecureHeadersMiddleware

Adds security headers to responses in production environments.

```python
from fastblocks.middleware import SecureHeadersMiddleware
from starlette.applications import Starlette

app = Starlette()
app = SecureHeadersMiddleware(app)
```

#### CacheMiddleware

Caches HTTP responses based on configurable rules to improve performance.

```python
from fastblocks.middleware import CacheMiddleware
from fastblocks.caching import Rule
from acb.adapters import import_adapter
from acb.depends import depends
from starlette.applications import Starlette

Cache = import_adapter("cache")
cache = depends.get(Cache)

# Define caching rules
rules = [
    Rule(match="/api/*", ttl=60),  # Cache API responses for 60 seconds
    Rule(match="/static/*", ttl=3600),  # Cache static content for 1 hour
]

app = Starlette()
app = CacheMiddleware(app, cache=cache, rules=rules)
```

##### Using the Cache Decorator

You can also apply caching to specific route handlers using the `@cached` decorator:

```python
from fastblocks.decorators import cached
from acb.adapters import import_adapter
from acb.depends import depends
from starlette.responses import JSONResponse

Cache = import_adapter("cache")
cache = depends.get(Cache)

@cached(cache=cache)
async def my_endpoint(request):
    return JSONResponse({"data": "This response will be cached"})
```

##### Cache Rules

Cache rules determine which requests and responses should be cached:

```python
from fastblocks.caching import Rule
import re

# Cache all requests
rule = Rule(match="*")

# Cache specific paths
rule = Rule(match="/api/products")

# Cache using regex pattern
rule = Rule(match=re.compile(r"/api/products/\d+"))

# Cache multiple patterns
rule = Rule(match=["/api/products", "/api/categories"])

# Cache with specific TTL (time-to-live)
rule = Rule(match="/api/products", ttl=60)  # 60 seconds

# Cache only specific status codes
rule = Rule(match="/api/products", status=[200, 304])
```

#### CacheControlMiddleware

Simplifies the management of cache control headers for HTTP responses.

```python
from fastblocks.middleware import CacheControlMiddleware
from starlette.applications import Starlette

app = Starlette()
app = CacheControlMiddleware(app, max_age=300, public=True)
```

##### Using the Cache Control Decorator

You can also apply cache control headers to specific route handlers using the `@cache_control` decorator:

```python
from fastblocks.decorators import cache_control
from starlette.responses import JSONResponse

@cache_control(max_age=300, public=True)
async def my_endpoint(request):
    return JSONResponse({"data": "This response will have cache headers"})
```

##### Cache Control Directives

Available cache control directives:

```python
from fastblocks.decorators import cache_control

# Set max-age
@cache_control(max_age=300)

# Set s-maxage (for shared caches)
@cache_control(s_maxage=600)

# Set public/private
@cache_control(public=True)
@cache_control(private=True)

# Set no-cache/no-store
@cache_control(no_cache=True)
@cache_control(no_store=True)

# Set must-revalidate
@cache_control(must_revalidate=True)

# Set proxy-revalidate
@cache_control(proxy_revalidate=True)

# Set immutable
@cache_control(immutable=True)

# Set stale-while-revalidate
@cache_control(stale_while_revalidate=60)

# Set stale-if-error
@cache_control(stale_if_error=300)
```

### Custom Middleware

You can create your own middleware by following the ASGI middleware pattern:

```python
class CustomMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Process request
        # ...

        async def send_wrapper(message):
            # Process response
            # ...
            await send(message)

        await self.app(scope, receive, send_wrapper)
```

Then apply your middleware to your application:

```python
from starlette.applications import Starlette

app = Starlette()
app = CustomMiddleware(app)
```

## Exception Handling

FastBlocks provides enhanced exception handling with custom error pages and detailed error information in debug mode:

```python
# Exception handlers are configured automatically
self.exception_handlers = {
    404: handle_exception,
    500: handle_exception,
}
```

The `handle_exception` function renders appropriate error pages based on the exception and whether the request is an HTMX request.

## Dependency Injection

FastBlocks leverages ACB's dependency injection system to manage component dependencies:

```python
from acb.depends import depends
from acb.config import Config

@depends.inject
async def process_data(data, config: Config = depends(), logger = depends("logger")):
    logger.info(f"Processing data with app: {config.app.name}")
    # Process data...
    return result
```

### Key Features

- **Automatic Injection**: Dependencies are automatically injected into functions and methods
- **Component Registration**: Components are automatically registered and discovered
- **Lazy Loading**: Dependencies are only initialized when needed
- **Testing Support**: Dependencies can be easily mocked for testing

## Configuration System

FastBlocks uses ACB's configuration system based on Pydantic:

```python
from acb.config import Config
from acb.depends import depends

config = depends.get(Config)

# Access configuration values
secret_key = config.app.secret_key
debug_mode = config.debug.fastblocks
```

### Configuration Sources

- **YAML Files**: Environment-specific settings in YAML format
- **Secret Files**: Secure storage of sensitive information
- **Environment Variables**: Override configuration via environment variables

## Caching

FastBlocks includes a powerful caching system for templates, HTTP responses, and other data:

```python
from acb.depends import depends
from acb.adapters import import_adapter

Cache = import_adapter("cache")
cache = depends.get(Cache)

# Cache data
await cache.set("my_key", "my_value", ttl=60)

# Retrieve cached data
value = await cache.get("my_key")
```

### Caching Features

- **Template Caching**: Templates are cached for improved performance
- **Bytecode Caching**: Jinja2 template bytecode is cached in Redis
- **Distributed Caching**: Redis-based caching for distributed deployments
- **Namespace Support**: Cache keys are organized by namespaces
- **HTTP Response Caching**: Middleware for caching HTTP responses

### Response Caching

FastBlocks provides middleware for caching HTTP responses:

```python
from fastblocks.decorators import cached, cache_control
from acb.adapters import import_adapter

Cache = import_adapter("cache")
cache = depends.get(Cache)

# Apply caching to a route handler
@cached(cache=cache)
async def my_endpoint(request):
    return JSONResponse({"data": "This response will be cached"})

# Apply cache control headers
@cache_control(max_age=300, public=True)
async def another_endpoint(request):
    return JSONResponse({"data": "This response will have cache headers"})
```

You can also apply caching to your entire application:

```python
from fastblocks.middleware import CacheMiddleware
from starlette.applications import Starlette

app = Starlette()
app = CacheMiddleware(app, cache=cache)
```

The caching system supports:

- **Rule-based caching**: Configure which responses should be cached based on patterns
- **Automatic cache invalidation**: Cache is automatically invalidated on POST, PUT, PATCH, DELETE requests
- **Cache control headers**: Easily add cache control headers to responses
- **Cache helpers**: Utilities for working with cached responses
