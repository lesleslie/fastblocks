# FastBlocks Core Features

> **FastBlocks Documentation**: [Main](../README.md) | [Core Features](./README.md) | [Actions](./actions/README.md) | [Adapters](./adapters/README.md)

FastBlocks provides a set of core features that form the foundation of the framework. These components work together to create a powerful, asynchronous web application framework optimized for server-side rendering with HTMX.

## Table of Contents

- [Application Class](#application-class)
- [Middleware Stack](#middleware-stack)
- [Exception Handling](#exception-handling)
- [Dependency Injection](#dependency-injection)
- [Configuration System](#configuration-system)
- [Caching](#caching)

## Application Class

The `FastBlocks` class extends Starlette's application class with additional features specifically designed for HTMX and template-based applications.

```python
from fastblocks.applications import FastBlocks
from starlette.routing import Route

async def homepage(request):
    return await request.app.templates.app.render_template(
        request, "index.html", context={"title": "FastBlocks Demo"}
    )

routes = [
    Route("/", endpoint=homepage)
]

app = FastBlocks(routes=routes)
```

### Key Features

- **Automatic Template Setup**: Templates are automatically configured and made available via `app.templates`
- **Debug Mode**: Enhanced debugging with detailed error pages when in debug mode
- **Middleware Configuration**: Automatic configuration of middleware based on application settings
- **Model Integration**: Automatic integration with SQLAlchemy models via `app.models`

## Middleware Stack

FastBlocks includes a comprehensive middleware stack that enhances the functionality of your application:

```python
# Default middleware stack
middleware = [
    ProcessTimeHeaderMiddleware,  # Performance monitoring
    CSRFMiddleware,               # CSRF protection
    SessionMiddleware,            # Session management
    HtmxMiddleware,               # HTMX request processing
    CurrentRequestMiddleware,     # Request context
    BrotliMiddleware,             # Response compression
    SecureHeadersMiddleware,      # Security headers (production only)
]
```

### Key Middleware Components

- **ProcessTimeHeaderMiddleware**: Measures and logs request processing time
- **CSRFMiddleware**: Provides protection against Cross-Site Request Forgery attacks
- **SessionMiddleware**: Manages user sessions via cookies
- **HtmxMiddleware**: Processes HTMX-specific headers and request information
- **CurrentRequestMiddleware**: Makes the current request available via a context variable
- **BrotliMiddleware**: Compresses responses using Brotli compression
- **SecureHeadersMiddleware**: Adds security headers to responses in production environments

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
def process_data(data, config: Config = depends(), logger = depends("logger")):
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

FastBlocks includes a powerful caching system for templates and other data:

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
