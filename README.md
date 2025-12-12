<p align="center">
<img src="./images/fastblocks-logo.png" alt="FastBlocks Logo">
</p>

> **FastBlocks Documentation**: [Main](#fastblocks) | [Core Features](#fastblocks) | [Actions](./fastblocks/actions/README.md) | [Adapters](./fastblocks/adapters/README.md)

# FastBlocks

[![Code style: crackerjack](https://img.shields.io/badge/code%20style-crackerjack-000042)](https://github.com/lesleslie/crackerjack)
[![Python: 3.13+](https://img.shields.io/badge/python-3.13%2B-green)](https://www.python.org/downloads/)
![Coverage](https://img.shields.io/badge/coverage-33.00%25-yellow)

> _Last reviewed: 2025-11-19_

## What is FastBlocks?

FastBlocks is an asynchronous web application framework, inspired by FastAPI and built on Starlette, specifically designed for the rapid delivery of server-side rendered HTMX/Jinja template blocks. It combines modern Python async capabilities with server-side rendering to create dynamic, interactive web applications with minimal JavaScript.

Unlike monolithic frameworks or micro-frameworks that require extensive configuration, FastBlocks offers a modular, component-based architecture that provides batteries-included functionality while maintaining exceptional flexibility. Built on the **[Asynchronous Component Base (ACB)](https://github.com/lesleslie/acb)** framework, FastBlocks leverages ACB's powerful adapter pattern for seamless component swapping, cloud provider migrations, and tailored customizations without extensive code changes.

FastBlocks serves as a prime example of ACB's capabilities, showcasing how ACB's dependency injection, configuration management, and pluggable adapter system can create enterprise-grade applications. All FastBlocks adapters (templates, auth, admin, routing, storage) follow ACB's standardized interfaces, ensuring consistency and interoperability.

## Key Concepts

If you're new to FastBlocks, here are the key concepts to understand:

1. **Server-Side Rendering**: Unlike frameworks that rely heavily on JavaScript for interactivity, FastBlocks renders HTML on the server and sends only what's needed to the browser.

1. **HTMX**: A lightweight JavaScript library that allows you to access modern browser features directly from HTML, without writing JavaScript. FastBlocks is built with HTMX in mind.

1. **Template Blocks**: Small pieces of HTML that can be rendered independently and injected into the page, enabling dynamic updates without full page reloads.

1. **Adapters**: Pluggable components that provide standardized interfaces to different implementations (templates, authentication, admin interfaces, etc.). This architecture facilitates seamless provider switching, multi-cloud deployments, and targeted customizations without restructuring your application.

1. **Dependency Injection**: A pattern that automatically provides components to your functions when needed, reducing boilerplate code.

1. **Asynchronous Architecture**: Built on Python's async/await syntax for high performance and efficient handling of concurrent requests.

## Key Features

- **Starlette Foundation**: Built on the [Starlette](https://www.starlette.io/) ASGI framework for high performance, extending its application class and middleware system
- **Native HTMX Integration**: Built-in HTMX support (not a dependency) for creating dynamic interfaces with server-side rendering
- **Asynchronous Architecture**: Built on [Asynchronous Component Base (ACB)](https://github.com/lesleslie/acb), providing dependency injection, configuration management, and pluggable components
- **Dual Template Systems**: Advanced asynchronous Jinja2 template system with fragments and partials support using `[[` and `]]` delimiters, plus HTMY for type-safe Python-based component creation
- **Async Template Stack**: Powered by [jinja2-async-environment](https://github.com/lesleslie/jinja2-async-environment) and [starlette-async-jinja](https://github.com/lesleslie/starlette-async-jinja) for true non-blocking rendering, template inheritance safety, and HTMX-friendly block streaming
- **Modular Design**: Pluggable adapters for authentication, admin interfaces, routing, templates, and sitemap generation
- **Cloud Flexibility**: Easily switch between cloud providers or create hybrid deployments by swapping adapters
- **Performance Optimized**: Built-in caching system, Brotli compression, and HTML/CSS/JS minification
- **Type Safety**: Leverages Pydantic v2 for validation and type safety throughout
- **Universal Database Support**: Works with SQL (PostgreSQL, MySQL, SQLite) and NoSQL (MongoDB, Firestore, Redis) databases
- **Multiple Model Types**: Supports SQLModel, SQLAlchemy, Pydantic, msgspec, attrs, and Redis-OM
- **Admin Interface**: Integrated SQLAlchemy Admin support for database management
- **Dependency Injection**: Robust dependency injection system with automatic resolution
- **Batteries Included, But Replaceable**: Comprehensive defaults with the ability to customize or replace any component

## Documentation Map

- [Getting Started Guide](./docs/GETTING_STARTED.md) – step-by-step quick start plus common HTMX patterns
- [Core Framework Reference](./README.md#fastblocks) – applications, middleware, core architecture
- [Actions Library](./fastblocks/actions/README.md) – minification, gathering, query utilities, and more
- [Adapters Reference](./fastblocks/adapters/README.md) – overview of pluggable adapters
- [Templates Adapter Guide](./fastblocks/adapters/templates/README.md) – async Jinja stack and filters
- [Technical Docs Index](./docs/README.md) – ACB guide, migration notes, archived docs
- [Async Jinja Troubleshooting](./docs/JINJA2_ASYNC_ENVIRONMENT_USAGE.md) – inheritance-safe rendering guidance
- [Architecture Guide](./docs/ARCHITECTURE.md) – Starlette + ACB layering, SSR pipeline, and project layout
- [Comparisons & Decision Guide](./docs/COMPARISONS.md) – framework comparisons and key advantages
- [Template Examples](./docs/examples/TEMPLATE_EXAMPLES.md) – snippets for layout, fragments, and HTMX swaps
- [Testing Guide](./tests/TESTING.md) – instructions for running the FastBlocks test suite

## Why Choose FastBlocks?

FastBlocks pairs server-side rendering with HTMX-first workflows, a flexible adapter ecosystem, and the familiarity of Starlette + ACB. Teams typically choose FastBlocks when they want:

- **HTML-first iteration speed** without giving up async performance or modern tooling
- **Composable infrastructure** thanks to adapters for templates, auth, routes, admin, and storage
- **Multi-cloud optionality** driven by configuration instead of rewrites
- **Enterprise-grade defaults** (SQLAdmin, security middleware, monitoring hooks) that stay replaceable

Need a deeper comparison against FastAPI, FastHTML, FastHX, FastHTMX, or Litestar? Want the full breakdown of multi-cloud, SSR, performance, and DX advantages? See the [Comparisons & Decision Guide](./docs/COMPARISONS.md) for detailed tables, “choose FastBlocks when…” scenarios, and enterprise capability checklists.

- **Content Management Systems**: Where initial load performance is critical
- **Internal Tools**: Rapid development and maintenance are prioritized
- **Multi-Cloud Environments**: Organizations needing infrastructure flexibility
- **Team Collaboration**: Designers can work with HTML/CSS while developers handle Python logic
- **Prototype to Production**: Rapid prototyping that scales to enterprise needs

FastBlocks combines the development speed of modern frameworks with the infrastructure flexibility needed for enterprise deployment. Unlike monolithic frameworks that lock you into specific implementations, FastBlocks provides comprehensive defaults (batteries included) while maintaining the flexibility to customize or replace any component to suit your specific needs. This makes it an excellent choice for teams that want to move fast without sacrificing long-term flexibility or architectural control.

## Table of Contents

- [Why Choose FastBlocks?](#why-choose-fastblocks)
- [Key Concepts](#key-concepts)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Common Patterns](#common-patterns)
- [Architecture Overview](#architecture-overview)
- [Core Components](#core-components)
  - [Templates](#templates)
  - [Routing](#routing)
  - [Middleware](#middleware)
  - [HTMX Integration](#htmx-integration)
  - [HTMY Components](#htmy-components)
- [Database Models and Queries](#database-models-and-queries)
- [Adapters](#adapters)
- [Actions](#actions)
- [Configuration](#configuration)
- [Command-Line Interface (CLI)](#command-line-interface-cli)
  - [Creating a New Project](#creating-a-new-project)
  - [Running Your Application](#running-your-application)
  - [CLI Options](#cli-options)
- [Migration Guide](#migration-guide)
- [Examples](#examples)
- [Documentation](#documentation)
- [License](#license)
- [Acknowledgements](#acknowledgements)

## Installation

Install FastBlocks using [uv](https://docs.astral.sh/uv/):

```bash
uv add fastblocks
```

### Requirements

- Python 3.13 or higher

### Optional Dependencies

FastBlocks uses **PEP 735 dependency groups** for optional features. Install the groups you need:

| Feature Group | Components | Installation Command |
|---------------|------------|----------------------|
| Admin | SQLAlchemy Admin interface | `uv add --group admin` |
| Sitemap | Automatic sitemap generation | `uv add --group sitemap` |
| Monitoring | Sentry and Logfire integration | `uv add --group monitoring` |
| Multiple Groups | Install multiple features at once | `uv add --group admin --group monitoring --group sitemap` |
| Development | Development tools | `uv add --group dev` |

**Note**: Version 0.17.0+ uses dependency groups instead of extras. See [MIGRATION-0.17.0.md](./docs/migrations/MIGRATION-0.17.0.md) for details.

You can also install FastBlocks using pip:

```bash
pip install fastblocks
```

**Note**: pip does not support PEP 735 dependency groups. For optional features with pip, install dependencies manually:

```bash
# Admin interface
pip install sqladmin>=0.21

# Monitoring
pip install "logfire[starlette]>=3.24" "sentry-sdk[starlette]>=2.32"
```

## Getting Started

Follow the [Getting Started guide](./docs/GETTING_STARTED.md) for a full step-by-step tutorial, including HTMX counter blocks, configuration files, and common interaction patterns. The guide consolidates everything that used to live in this README—Quick Start, Common Patterns, and dependency injection examples—so the landing page stays scannable.

Here's the core of every FastBlocks app:

```python
from starlette.routing import Route
from acb.adapters import import_adapter
from acb.depends import Inject, depends

Templates = import_adapter("templates")
App = import_adapter("app")


@depends.inject
async def homepage(request, templates: Inject[Templates]):
    return await templates.app.render_template(
        request, "index.html", context={"title": "FastBlocks Demo"}
    )


routes = [Route("/", endpoint=homepage)]
app = depends.get(App)
```

Next steps:

1. Create an `index.html` template that uses `[[ title ]]`
1. Add HTMX-friendly blocks like `/block/counter`
1. Configure the app via `settings/app.yml`
1. Browse the HTMX, forms, and DI examples in `docs/GETTING_STARTED.md`

## Architecture Overview

FastBlocks extends Starlette’s ASGI runtime with HTMX-aware requests and middleware, and relies on ACB for dependency injection plus the adapter pattern. The end result is a layered architecture where:

- Starlette provides routing, middleware, and ASGI lifecycle
- FastBlocks augments it with SSR-friendly helpers, template streaming, and HTMX ergonomics
- ACB supplies dependency injection, configuration, and pluggable adapters

For a detailed walkthrough—including Starlette integration points, modern `Inject[Type]` usage, HTMX SSR rationale, and the full project structure diagram—see the [Architecture Guide](./docs/ARCHITECTURE.md).

## Core Components

### Templates

FastBlocks uses an enhanced asynchronous Jinja2 template system designed specifically for HTMX integration and server-side rendering.

#### Key Features

- **Async Template Loading**: Load templates asynchronously from file system, cloud storage, or Redis
- **Template Fragments**: Render specific blocks of templates for HTMX partial updates
- **Custom Delimiters**: Uses `[[` and `]]` for variables instead of `{{` and `}}` to avoid conflicts with JavaScript frameworks
- **Bytecode Caching**: Redis-based bytecode caching for improved performance
- **Built-in Filters**: Includes filters for minification, URL encoding, and more
- **Null Safety**: Enhanced dependency resolution with automatic fallbacks for missing components
- **Error Recovery**: Graceful handling of cache, storage, and dependency failures

**PyCharm/JetBrains IDE Support**: For better template editing experience with FastBlocks' custom `[[` `]]` delimiters, install our official JetBrains plugin:

[![JetBrains Plugin](https://img.shields.io/badge/JetBrains-FastBlocks%20Template%20Support-000000?style=for-the-badge&logo=jetbrains)](https://plugins.jetbrains.com/plugin/28680)
[![Plugin Downloads](https://img.shields.io/jetbrains/plugin/d/28680?style=flat-square&label=downloads)](https://plugins.jetbrains.com/plugin/28680)
[![Plugin Version](https://img.shields.io/jetbrains/plugin/v/28680?style=flat-square&label=version)](https://plugins.jetbrains.com/plugin/28680)

#### Async Template Stack

FastBlocks layers two companion libraries to keep template rendering fully asynchronous from loaders to HTTP responses:

- **[jinja2-async-environment](https://github.com/lesleslie/jinja2-async-environment)** supplies the event-loop friendly `Environment`, async filesystem/cloud/Redis loaders, and generator-based rendering strategy that preserves template inheritance, macros, and fragments without blocking.
- **[starlette-async-jinja](https://github.com/lesleslie/starlette-async-jinja)** adapts that environment into Starlette's `TemplateResponse`, powering `render_template()` and `render_template_block()` plus HTMX-aware headers and streaming responses.

Because both projects are maintained alongside FastBlocks, upgrades stay in lockstep: Redis bytecode caching, secure template environments, and block streaming land here as soon as they are available upstream. See `docs/JINJA2_ASYNC_ENVIRONMENT_USAGE.md` for architectural details and troubleshooting patterns.

#### Basic Template Usage

```python
from acb.adapters import import_adapter
from acb.depends import Inject, depends

Templates = import_adapter("templates")


@depends.inject
async def homepage(request, templates: Inject[Templates]):
    # Render a full template
    return await templates.app.render_template(
        request,
        "index.html",  # Template file path relative to templates directory
        context={"title": "FastBlocks Demo", "user": {"name": "John"}},
    )
```

#### Template Structure

FastBlocks templates use Jinja2 syntax with custom delimiters:

```html
<!DOCTYPE html>
<html>
<head>
    <title>[[ title ]]</title>  <!-- Note the [[ ]] delimiters instead of {{ }} -->
</head>
<body>
    <h1>Welcome, [[ user.name ]]!</h1>

    {% block content %}
    <p>This is the default content.</p>
    {% endblock %}
</body>
</html>
```

#### Template Inheritance

You can use Jinja2's template inheritance:

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html>
<head>
    <title>[[ title ]]</title>
    <link rel="stylesheet" href="/static/css/style.css">
    {% block head %}{% endblock %}
</head>
<body>
    <header>
        <nav><!-- Navigation --></nav>
    </header>

    <main>
        {% block content %}{% endblock %}
    </main>

    <footer>
        &copy; [[ current_year ]] FastBlocks Demo
    </footer>
</body>
</html>
```

```html
<!-- templates/home.html -->
{% extends "base.html" %}

{% block head %}
<script src="https://unpkg.com/htmx.org@1.9.10"></script>
{% endblock %}

{% block content %}
<h1>Welcome to [[ title ]]</h1>
<div id="counter-container" hx-get="/block/counter" hx-trigger="load">
    Loading...
</div>
{% endblock %}
```

#### Template Blocks for HTMX

Create template blocks specifically for HTMX responses:

```html
<!-- templates/blocks/counter.html -->
{% block counter_block %}
<div class="counter">
    <h2>Count: [[ count ]]</h2>
    <button hx-post="/block/counter" hx-target="#counter-container">Increment</button>
</div>
{% endblock %}
```

```python
from acb.depends import Inject, depends


@depends.inject
async def counter_block(request, templates: Inject[Templates]):
    count = request.session.get("count", 0)
    if request.method == "POST":
        count += 1
        request.session["count"] = count

    # Render just the counter block
    return await templates.app.render_template_block(
        request,
        "blocks/counter.html",  # Template file
        "counter_block",  # Block name within the template
        context={"count": count},
    )
```

#### Custom Filters

FastBlocks includes several built-in filters and you can add your own:

```python
from acb.adapters import import_adapter

Templates = import_adapter("templates")


# Register a custom filter
@Templates.filter()
def capitalize_words(value: str) -> str:
    return " ".join(word.capitalize() for word in value.split())
```

Usage in templates:

```html
<h1>[[ user.name | capitalize_words ]]</h1>
```

#### Built-in Filters

FastBlocks includes several useful filters:

- **minify_html**: Minifies HTML content
- **minify_js**: Minifies JavaScript content
- **minify_css**: Minifies CSS content
- **map_src**: URL-encodes strings for use in URLs

#### Enhanced Dependency Resolution

The template system includes robust dependency resolution with automatic fallbacks:

- **Automatic Fallbacks**: If cache or storage dependencies are unavailable, the system continues with file-based templates
- **Null Safety**: All operations check for null dependencies and provide sensible defaults
- **Error Recovery**: Template loading failures are handled gracefully with meaningful error messages

### Routing

The routing system extends Starlette's routing with enhanced features for HTMX and server-side rendering.

#### Key Features

- **Automatic Route Discovery**: Routes are automatically discovered and registered
- **HTMX-Aware Endpoints**: Built-in support for HTMX requests and responses
- **Block Rendering**: Specialized endpoints for rendering template blocks

#### Basic Routing

FastBlocks supports Starlette's routing patterns with additional features:

```python
from starlette.routing import Route, Mount
from acb.adapters import import_adapter
from acb.depends import Inject, depends

Templates = import_adapter("templates")


@depends.inject
async def homepage(request, templates: Inject[Templates]):
    return await templates.app.render_template(
        request, "index.html", context={"title": "FastBlocks Demo"}
    )


@depends.inject
async def about(request, templates: Inject[Templates]):
    return await templates.app.render_template(
        request, "about.html", context={"title": "About Us"}
    )


# Define your routes
routes = [
    Route("/", endpoint=homepage),
    Route("/about", endpoint=about),
    Mount("/static", StaticFiles(directory="static"), name="static"),
]
```

#### Route Discovery

FastBlocks can automatically discover and register routes from your application:

```python
# routes.py
from starlette.routing import Route
from acb.adapters import import_adapter
from acb.depends import Inject, depends

Templates = import_adapter("templates")


@depends.inject
async def homepage(request, templates: Inject[Templates]):
    return await templates.app.render_template(
        request, "index.html", context={"title": "FastBlocks Demo"}
    )


# Export routes to be automatically discovered
routes = [
    Route("/", endpoint=homepage),
]
```

#### Path Parameters

You can use path parameters in your routes:

```python
@depends.inject
async def user_profile(request, templates: Inject[Templates]):
    user_id = request.path_params["user_id"]
    # Fetch user data...
    return await templates.app.render_template(
        request, "user/profile.html", context={"user_id": user_id}
    )


routes = [
    Route("/users/{user_id}", endpoint=user_profile),
]
```

#### HTMX-Specific Routes

Create routes specifically for HTMX interactions:

```python
@depends.inject
async def load_more_items(request, templates: Inject[Templates]):
    page = int(request.query_params.get("page", 1))
    # Fetch items for the requested page...
    items = [f"Item {i}" for i in range((page - 1) * 10, page * 10)]

    # Return just the items block for HTMX to insert
    return await templates.app.render_template_block(
        request, "items.html", "items_block", context={"items": items, "page": page}
    )


routes = [
    Route("/api/items", endpoint=load_more_items),
]
```

### Middleware

FastBlocks includes a comprehensive middleware stack that enhances application functionality:

- **HTMX Middleware**: Processes HTMX-specific headers and makes HTMX request information available
- **CSRF Protection**: Built-in CSRF protection requiring tokens for state-changing requests
- **Session Middleware**: Cookie-based session management with secure defaults
- **Compression**: Brotli compression for reduced payload sizes and improved performance
- **Secure Headers**: Security headers for production environments
- **Cache Middleware**: HTTP response caching with rule-based configuration and automatic invalidation
- **Cache Control Middleware**: Simplified management of cache control headers
- **Process Time Header Middleware**: Measures and logs request processing time for monitoring
- **Current Request Middleware**: Makes the current request available via context variable for global access

#### Advanced Middleware Features

**Cache Middleware with Rules**:

```python
from fastblocks.middleware import CacheMiddleware
from fastblocks.caching import Rule

# Define caching rules
rules = [
    Rule(match="/api/*", ttl=60),  # Cache API responses for 60 seconds
    Rule(match="/static/*", ttl=3600),  # Cache static content for 1 hour
]

app = CacheMiddleware(app, cache=cache, rules=rules)
```

**Cache Control Headers**:

```python
from fastblocks.decorators import cache_control


@cache_control(max_age=300, public=True)
async def my_endpoint(request):
    return JSONResponse({"data": "This response will have cache headers"})
```

**Response Caching Decorator**:

```python
from fastblocks.decorators import cached


@cached(cache=cache)
async def my_endpoint(request):
    return JSONResponse({"data": "This response will be cached"})
```

#### Middleware Ordering

FastBlocks uses a position-based middleware system to ensure middleware components are executed in the correct order. The middleware execution flow follows the ASGI specification:

1. The last middleware in the list is the first to process the request
1. The first middleware in the list is the last to process the request

The actual execution flow is:

- ExceptionMiddleware (outermost - first to see request, last to see response)
- System middleware (ordered by MiddlewarePosition enum)
- User-provided middleware
- ServerErrorMiddleware (innermost - last to see request, first to see response)

#### Adding Custom Middleware

You can add custom middleware to your FastBlocks application in two ways:

1. **User Middleware**: Added to the user middleware stack

```python
# Add a middleware to the end of the user middleware stack
app.add_middleware(CustomMiddleware, option="value")

# Add a middleware at a specific position in the user middleware stack
app.add_middleware(CustomMiddleware, position=0, option="value")
```

2. **System Middleware**: Replace middleware at specific positions defined by the MiddlewarePosition enum

```python
from fastblocks.middleware import MiddlewarePosition

# Replace the compression middleware with a custom implementation
app.add_system_middleware(
    CustomMiddleware, position=MiddlewarePosition.COMPRESSION, option="value"
)
```

#### Example: Custom Middleware

Here's a complete example of creating and adding custom middleware:

```python
from typing import Any
from starlette.types import ASGIApp, Receive, Scope, Send
from fastblocks import FastBlocks
from fastblocks.middleware import MiddlewarePosition


# Define a simple custom middleware
class CustomHeaderMiddleware:
    """A middleware that adds a custom header to responses."""

    def __init__(self, app: ASGIApp, header_name: str, header_value: str) -> None:
        self.app = app
        self.header_name = header_name
        self.header_value = header_value

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_header(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                headers.append((self.header_name.encode(), self.header_value.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_header)


# Create a FastBlocks application
app = FastBlocks()

# Add a custom middleware to the user middleware stack
app.add_middleware(
    CustomHeaderMiddleware, header_name="X-Custom-User", header_value="User-defined"
)

# Replace the compression middleware with a custom implementation
app.add_system_middleware(
    CustomHeaderMiddleware,
    position=MiddlewarePosition.COMPRESSION,
    header_name="X-Custom-Compression",
    header_value="Replaced",
)
```

#### Middleware Positions

The `MiddlewarePosition` enum defines the positions of middleware in the system stack:

```python
class MiddlewarePosition(IntEnum):
    # Core middleware (always present)
    PROCESS_TIME = 0  # First middleware to see request, last to see response
    CSRF = 1  # Security middleware should be early in the chain
    SESSION = 2  # Session handling (if auth enabled)
    HTMX = 3  # HTMX request processing
    CURRENT_REQUEST = 4  # Request context tracking
    COMPRESSION = 5  # Response compression
    SECURITY_HEADERS = 6  # Security headers for responses
```

You can get a dictionary of middleware positions using the `get_middleware_positions()` function:

```python
from fastblocks.middleware import get_middleware_positions

positions = get_middleware_positions()
print(positions)  # {'PROCESS_TIME': 0, 'CSRF': 1, ...}
```

### HTMX Integration

FastBlocks includes **native HTMX support** built directly into the framework. This implementation provides seamless integration with HTMX without requiring external dependencies.

#### Native Implementation Details

FastBlocks' HTMX support is provided through:

- **`fastblocks.htmx` module**: Core HTMX functionality with ACB integration
- **HTMX Middleware**: Automatically processes HTMX headers in the middleware stack
- **No external dependencies**: All HTMX support is built into FastBlocks

#### Key HTMX Features in FastBlocks

- **HtmxRequest**: Extended request object with HTMX-specific attributes
- **HtmxResponse**: Specialized response class for HTMX interactions
- **Template Blocks**: Specialized endpoints for rendering template fragments
- **Push URL**: Automatic URL updates for browser history
- **Response Headers**: Helper methods for setting HTMX-specific response headers
- **Response Helpers**: Built-in functions like `htmx_trigger()`, `htmx_redirect()`, and `htmx_refresh()`

#### Using HTMX Request Properties

FastBlocks extends Starlette's request object with HTMX-specific properties:

```python
from starlette.routing import Route
from acb.adapters import import_adapter
from acb.depends import Inject, depends

Templates = import_adapter("templates")


@depends.inject
async def product_detail(request, templates: Inject[Templates]):
    product_id = request.path_params["product_id"]

    # Check if this is an HTMX request
    if request.htmx:
        # Access HTMX-specific properties
        is_boosted = request.htmx.boosted  # True if hx-boost was used
        trigger = request.htmx.trigger  # ID of the element that triggered the request
        target = request.htmx.target  # ID of the target element

        # For HTMX requests, render just the product details block
        return await templates.app.render_template_block(
            request,
            "products/detail.html",
            "product_detail_block",
            context={"product_id": product_id},
        )

    # For regular requests, render the full page
    return await templates.app.render_template(
        request, "products/detail.html", context={"product_id": product_id}
    )


routes = [Route("/products/{product_id}", endpoint=product_detail)]
```

#### Setting HTMX Response Headers

FastBlocks makes it easy to set HTMX-specific response headers:

```python
from starlette.responses import Response
from starlette.routing import Route
from acb.adapters import import_adapter
from acb.depends import Inject, depends

Templates = import_adapter("templates")


@depends.inject
async def search_results(request, templates: Inject[Templates]):
    query = request.query_params.get("q", "")

    # Render the search results
    response = await templates.app.render_template_block(
        request,
        "search/results.html",
        "results_block",
        context={"query": query, "results": []},
    )

    # Set HTMX-specific headers
    response.headers["HX-Push-Url"] = f"/search?q={query}"  # Update browser URL
    response.headers["HX-Trigger"] = "search-complete"  # Trigger client-side events

    return response


routes = [Route("/search", endpoint=search_results)]
```

#### Common HTMX Patterns

Here are some common HTMX patterns you can use with FastBlocks:

- **Click to Load**: `<button hx-get="/more" hx-target="#content">Load More</button>`
- **Form Submission**: `<form hx-post="/submit" hx-swap="outerHTML">...</form>`
- **Infinite Scroll**: `<div hx-get="/next-page" hx-trigger="revealed" hx-swap="afterend"></div>`
- **Active Search**: `<input type="text" name="q" hx-get="/search" hx-trigger="keyup changed delay:500ms" hx-target="#results">`
- **Confirmation Dialog**: `<button hx-delete="/item/1" hx-confirm="Are you sure?">Delete</button>`

### HTMY Components

FastBlocks includes support for [HTMY](#htmy-components), a Python-based HTML component library that brings type safety and component reusability to your templates.

#### When to Use HTMY vs Jinja2

**Choose HTMY when:**

- You want type-safe component definitions with Python dataclasses or Pydantic models
- Building reusable components with complex logic and state management
- You prefer Python over template syntax for component creation
- Working with teams that are more comfortable with Python than template languages
- You need IDE autocomplete, type checking, and refactoring support for component properties

**Choose Jinja2 when:**

- Working with designers who prefer HTML/template syntax
- Building page layouts and simple content rendering
- You need the full Jinja2 ecosystem (filters, macros, template inheritance)
- Rapid prototyping with minimal boilerplate
- Traditional template-based workflows

#### Basic HTMY Component

```python
# templates/components/user_card.py
from dataclasses import dataclass
from typing import Any


@dataclass
class UserCard:
    """A reusable user card component with type safety."""

    name: str
    email: str
    avatar_url: str = "/static/default-avatar.png"
    role: str = "User"

    def htmy(self, context: dict[str, Any]) -> str:
        """Render the component as HTML."""
        return f'''
        <div class="user-card">
            <img src="{self.avatar_url}" alt="{self.name}" class="avatar">
            <div class="user-info">
                <h3>{self.name}</h3>
                <span class="role">{self.role}</span>
                <p class="email">{self.email}</p>
            </div>
        </div>
        '''
```

#### HTMY with HTMX Integration

HTMY components work seamlessly with HTMX for dynamic interactions:

```python
from dataclasses import dataclass
from typing import Any


@dataclass
class InteractiveButton:
    """Button component with HTMX attributes."""

    text: str
    endpoint: str
    target: str
    method: str = "get"
    variant: str = "primary"

    def htmy(self, context: dict[str, Any]) -> str:
        return f'''
        <button
            class="btn-{self.variant}"
            hx-{self.method}="{self.endpoint}"
            hx-target="{self.target}"
            hx-swap="innerHTML">
            {self.text}
        </button>
        '''


@dataclass
class LoadMoreCard:
    """Card that loads more content via HTMX."""

    title: str
    initial_content: str
    load_endpoint: str

    def htmy(self, context: dict[str, Any]) -> str:
        return f'''
        <div class="load-more-card">
            <h3>{self.title}</h3>
            <div id="content-container">
                {self.initial_content}
            </div>
            <button
                hx-get="{self.load_endpoint}"
                hx-target="#content-container"
                hx-swap="beforeend">
                Load More
            </button>
        </div>
        '''
```

#### Using HTMY Components in Routes

```python
from starlette.routing import Route
from acb.adapters import import_adapter
from acb.depends import Inject, depends
from templates.components.user_card import UserCard

Templates = import_adapter("templates")


@depends.inject
async def user_profile(request, templates: Inject[Templates]):
    # Create component with type safety and IDE autocomplete
    user_card = UserCard(
        name="Jane Doe",
        email="jane@example.com",
        role="Administrator",
        avatar_url="/static/avatars/jane.jpg",
    )

    # Render the component
    return await templates.app.render_component(request, component=user_card)
```

#### Mixing HTMY and Jinja2

Combine both template systems for maximum flexibility:

```python
# Use HTMY component within Jinja2 template
from acb.adapters import import_adapter
from acb.depends import Inject, depends
from templates.components.user_card import UserCard

Templates = import_adapter("templates")


@depends.inject
async def dashboard(request, templates: Inject[Templates]):
    # Create HTMY components
    user_card = UserCard(name="John Doe", email="john@example.com")

    # Render Jinja2 template with HTMY component in context
    return await templates.app.render_template(
        request,
        "dashboard.html",
        context={"user_component": user_card.htmy({}), "stats": {...}},
    )
```

```html
<!-- templates/dashboard.html (Jinja2) -->
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard</title>
</head>
<body>
    <div class="container">
        <!-- HTMY component rendered inline -->
        [[ user_component | safe ]]

        <!-- Traditional Jinja2 content -->
        <div class="stats">
            {% for stat in stats %}
            <div class="stat-card">[[ stat.value ]]</div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
```

**Benefits of this hybrid approach:**

- **Type Safety**: HTMY components provide full type checking and IDE support
- **Flexibility**: Use the right tool for each part of your application
- **Reusability**: Create component libraries that work across projects
- **Team Collaboration**: Designers work with Jinja2, developers build components with HTMY
- **Progressive Enhancement**: Start with Jinja2, add HTMY components as needed

## Adapters

FastBlocks uses a pluggable adapter system for modular integration with external services and frameworks. Adapters provide standardized interfaces to different implementations, enabling seamless provider switching and customization without code changes.

### Available Adapter Categories

- **Images**: Cloud-based image processing and optimization (Cloudinary, ImageKit, Cloudflare Images, TwicPics)
- **Styles**: CSS frameworks and styling systems
  - **Bulma**: Modern CSS framework based on Flexbox
  - **Web Awesome**: Comprehensive icon library and UI components from Font Awesome
  - **Kelp**: Lightweight UI library for HTML-first development, powered by modern CSS and Web Components
  - **Vanilla**: Custom CSS with minimal framework overhead
- **Icons**: Icon libraries with SVG/font support (FontAwesome, Lucide, Phosphor, Heroicons, Remix, Material)
- **Fonts**: Web font loading and optimization (Google Fonts, Font Squirrel)
- **App**: Application configuration and initialization
- **Auth**: Authentication providers (Basic, etc.)
- **Admin**: Admin interface providers (SQLAdmin)
- **Routes**: Route management and discovery
- **Templates**: Template engine adapters (Jinja2, HTMY)
- **Sitemap**: Sitemap generation strategies

### Adapter Architecture

All adapters follow ACB 0.19.0+ patterns with:

- **MODULE_ID**: Static UUID7 for unique identification
- **MODULE_STATUS**: Adapter stability status (stable, beta, alpha, experimental)
- **Protocol-Based Design**: Standardized interfaces for consistent behavior
- **Dependency Injection**: Automatic registration via ACB's `depends.set()`

### Using Adapters

Adapters are accessed through ACB's dependency injection system:

```python
from acb.adapters import import_adapter
from acb.depends import Inject, depends

# Get adapter instances
Templates = import_adapter("templates")
Images = import_adapter("images")


# Use in route handlers with modern @depends.inject decorator and Inject[Type] pattern
@depends.inject
async def my_view(request, templates: Inject[Templates]):
    return await templates.app.render_template(request, "index.html")
```

### Documentation

For comprehensive adapter documentation including:

- Creating custom adapters
- Adapter configuration and settings
- MCP server foundation
- Health monitoring
- Best practices and troubleshooting
- Integration patterns

See the [**Adapters Documentation**](./fastblocks/adapters/README.md).

## Database Models and Queries

FastBlocks provides comprehensive database support through ACB's universal model and query system:

### Supported Model Types

FastBlocks automatically detects and supports multiple model frameworks:

| Model Type | Use Case | Example |
|------------|----------|---------|
| **SQLModel** | Type-safe SQL with validation | `class User(SQLModel, table=True): ...` |
| **SQLAlchemy** | Traditional ORM | `class User(Base): __tablename__ = "users"` |
| **Pydantic** | API models & validation | `class UserSchema(BaseModel): ...` |
| **msgspec** | High-performance serialization | `class User(msgspec.Struct): ...` |
| **Redis-OM** | Redis object mapping | `class User(HashModel): ...` |

### Database Support

- **SQL Databases**: PostgreSQL, MySQL/MariaDB, SQLite (including Turso)
- **NoSQL Databases**: MongoDB, Google Firestore, Redis

### Universal Query Interface

FastBlocks provides multiple query patterns that work consistently across all database types:

```python
from acb.depends import Inject, depends

# Modern pattern: Type-safe dependency access
query = depends.get(Query)

# Simple queries (Active Record style)
users = await query.for_model(User).simple.all()
user = await query.for_model(User).simple.find(1)

# Repository pattern (with built-in caching)
repo = query.for_model(User).repository()
active_users = await repo.find_active()

# Advanced query builder
results = await (
    query.for_model(User)
    .advanced.where("active", True)
    .where_gt("age", 21)
    .order_by_desc("created_at")
    .limit(10)
    .all()
)
```

**Key Benefits:**

- **Database Agnostic**: Switch databases without changing application code
- **Type Safety**: Full type checking across all operations
- **Multiple Patterns**: Choose the query style that fits your needs
- **Automatic Detection**: Models are discovered based on their base class

## Actions

Actions are utility functions that perform specific tasks:

- **Gather**: Discover and consolidate routes, templates, middleware, models, and application components
- **Sync**: Bidirectional synchronization of templates, settings, and cache across environments
- **Minify**: HTML, CSS, and JavaScript minification

For more information about actions, see the [Actions Documentation](./fastblocks/actions/README.md).

## Configuration

FastBlocks uses ACB's configuration system based on Pydantic, which provides a unified way to manage settings from multiple sources:

```python
from acb.config import Config
from acb.depends import Inject, depends

# Modern pattern: Type-safe dependency access
config = depends.get(Config)

# Access configuration values
secret_key = config.app.secret_key
debug_mode = config.debug.fastblocks
```

### Configuration Sources

- **YAML Files**: Environment-specific settings in YAML format (settings/app.yml, settings/debug.yml, etc.)
- **Secret Files**: Secure storage of sensitive information
- **Environment Variables**: Override configuration via environment variables

### FastBlocks-Specific Configuration

FastBlocks extends ACB's configuration system with web-specific settings for templates, routing, middleware, and more. These settings are automatically loaded and validated using Pydantic models.

## Command-Line Interface (CLI)

FastBlocks includes a powerful CLI tool to help you create and run applications.

### Installation

When you install FastBlocks, the CLI is automatically available:

```bash
python -m fastblocks --help
```

### Creating a New Project

Create a new FastBlocks project with the `create` command:

```bash
python -m fastblocks create
```

You'll be prompted for:

- **app_name**: Name of your application
- **style**: UI framework to use (bulma, webawesome, kelp, or custom)
- **domain**: Application domain

This will create a new directory with the following structure:

```
myapp/
├── __init__.py
├── .envrc
├── adapters/
│   └── __init__.py
├── actions/
│   └── __init__.py
├── main.py
├── models.py
├── pyproject.toml
├── routes.py
├── settings/
│   ├── adapters.yml
│   ├── app.yml
│   └── debug.yml
└── templates/
    ├── base/
    │   └── blocks/
    └── style/
        ├── blocks/
        └── theme/
```

### Running Your Application

Run your application in development mode with hot-reloading:

```bash
python -m fastblocks dev
```

The development server includes enhanced features:

- **Optimized Logging**: Uvicorn logging is integrated with ACB's InterceptHandler for cleaner output
- **Smart Reloading**: Excludes `tmp/*`, `settings/*`, and `templates/*` directories from reload monitoring for better performance
- **Template Development**: Templates are excluded from reload to prevent unnecessary restarts during template development

Run your application in production mode:

```bash
python -m fastblocks run
```

Run your application with Granian (high-performance ASGI server):

```bash
python -m fastblocks dev --granian
```

Run your application in a Docker container:

```bash
python -m fastblocks run --docker
```

### CLI Options

#### Create Command

```bash
python -m fastblocks create --app-name myapp --style bulma --domain example.com
```

#### Dev Command

```bash
python -m fastblocks dev [--granian] [--host HOST] [--port PORT]
```

Running with hot-reloading enabled for development.

#### Run Command

```bash
python -m fastblocks run [--docker] [--granian] [--host HOST] [--port PORT]
```

Run in production mode.

#### Components Command

```bash
python -m fastblocks components
```

Show available FastBlocks components and their status.

## Migration Guide

### Updating from Version 0.13.1 to 0.13.2

Version 0.14.0 introduces ACB 0.19.0 compatibility with adapter metadata requirements and continues the simplified dependency management with direct ACB imports. While existing code will continue to work, we recommend updating to the new patterns for better performance and maintainability.

#### Import Pattern Changes

**Before (v0.13.1 and earlier):**

```python
# Old wrapper-based imports
from fastblocks.dependencies import Templates, App
from fastblocks.config import config
```

**After (v0.13.2 - v0.24.x):**

```python
# Direct ACB imports with depends.get()
from acb.adapters import import_adapter
from acb.depends import depends
from acb.config import Config

Templates = import_adapter("templates")
App = import_adapter("app")
config = depends.get(Config)
```

**Modern (ACB 0.25.1+):**

```python
# Modern Inject[Type] pattern with type safety
from acb.adapters import import_adapter
from acb.depends import Inject, depends
from acb.config import Config

Templates = import_adapter("templates")
App = import_adapter("app")
config = depends.get(Config)
```

#### Route Handler Updates

**Before (v0.13.1 and earlier):**

```python
@depends.inject
async def homepage(request, templates=depends(Templates)):
    return await templates.render_template(request, "index.html")
```

**After (v0.13.2 - v0.24.x):**

```python
@depends.inject
async def homepage(request, templates: Templates = depends()):
    return await templates.app.render_template(request, "index.html")
```

**Modern (ACB 0.25.1+):**

```python
# Requires @depends.inject decorator with Inject[Type]
@depends.inject
async def homepage(request, templates: Inject[Templates]):
    return await templates.app.render_template(request, "index.html")
```

The modern pattern provides type safety, cleaner code, better performance, and improved developer experience with full IDE support.

#### Template System Improvements

Version 0.13.2 includes enhanced null safety in template loaders:

- Automatic fallback when dependencies are unavailable
- Improved error messages for missing templates
- Better handling of cache and storage failures
- Enhanced dependency resolution order

#### CLI Enhancements

The CLI now includes:

- Optimized uvicorn logging configuration
- Template reload exclusions for better development experience
- Enhanced error reporting for configuration issues

## Examples

### Creating a Dynamic Counter with HTMX

```python
from starlette.routing import Route
from acb.adapters import import_adapter
from acb.depends import Inject, depends

# Import adapters
Templates = import_adapter("templates")
App = import_adapter("app")

counter = 0


@depends.inject
async def get_counter(request, templates: Inject[Templates]):
    return await templates.app.render_template(
        request, "blocks/counter.html", context={"count": counter}
    )


@depends.inject
async def increment_counter(request, templates: Inject[Templates]):
    global counter
    counter += 1
    return await templates.app.render_template(
        request, "blocks/counter.html", context={"count": counter}
    )


routes = [
    Route("/block/counter", endpoint=get_counter, methods=["GET"]),
    Route("/block/counter", endpoint=increment_counter, methods=["POST"]),
]

# Create the application with modern pattern
app = depends.get(App)
```

## Documentation

For more detailed documentation about FastBlocks components:

- [**Core Features**](./README.md#fastblocks): Applications, middleware, and core functionality
- [**Actions**](./fastblocks/actions/README.md): Utility functions like minification
- [**Adapters**](./fastblocks/adapters/README.md): Pluggable components for various features
  - [**App Adapter**](./fastblocks/adapters/app/README.md): Application configuration
  - [**Auth Adapter**](./fastblocks/adapters/auth/README.md): Authentication providers
  - [**Admin Adapter**](./fastblocks/adapters/admin/README.md): Admin interface
  - [**Routes Adapter**](./fastblocks/adapters/routes/README.md): Routing system
  - [**Templates Adapter**](./fastblocks/adapters/templates/README.md): Template engine
  - [**Sitemap Adapter**](./fastblocks/adapters/sitemap/README.md): Sitemap generation
- [**Running Tests**](./tests/TESTING.md): Comprehensive guide to testing FastBlocks components

## License

This project is licensed under the terms of the BSD 3-Clause license.

## Acknowledgements

Special thanks to the following open-source projects that power FastBlocks:

### Foundation

- [Starlette](https://www.starlette.io/) - The ASGI framework that FastBlocks directly extends, providing the web application foundation
- [Asynchronous Component Base (ACB)](https://github.com/lesleslie/acb) - The core infrastructure providing dependency injection, configuration, and component architecture

### Frontend & Templates

- [HTMX](https://htmx.org/) - The lightweight JavaScript library for dynamic interfaces
- [Jinja2](https://jinja.palletsprojects.com/) - The template engine
- [jinja2-async-environment](https://github.com/lesleslie/jinja2-async-environment) - Asynchronous Jinja2 environment
- [starlette-async-jinja](https://github.com/lesleslie/starlette-async-jinja) - Starlette integration for async Jinja2
- [Bulma](https://bulma.io/) - Modern CSS framework based on Flexbox for beautiful responsive designs
- [Kelp](https://kelp.com/) - Lightweight UI library for HTML-first development, powered by modern CSS and Web Components

### Data & Validation

- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation and settings management
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL toolkit and ORM
- [SQLModel](https://sqlmodel.tiangolo.com/) - Modern SQL databases with Python, designed by the creator of FastAPI
- [SQLAdmin](https://github.com/aminalaee/sqladmin) - Admin interface for SQLAlchemy models with Starlette integration

### Components & Rendering

- [HTMY](#htmy-components) - Python-based HTML components with type safety
- [asgi-htmx](https://github.com/florimondmanca/asgi-htmx) - ASGI HTMX integration (enhanced and integrated into FastBlocks)
- [asgi-sitemaps](https://github.com/florimondmanca/asgi-sitemaps) - ASGI sitemap generation (enhanced and integrated into FastBlocks)

### Performance & Infrastructure

- [Redis](https://redis.io/) - In-memory data structure store for caching and sessions
- [aiocache](https://github.com/aio-libs/aiocache) - Async cache interface and implementations
- [Brotli](https://github.com/google/brotli) - Compression algorithm for better performance
- [Loguru](https://github.com/Delgan/loguru) - Async-compatible logging

### Development Tools

- [Uvicorn](https://www.uvicorn.org/) - Lightning-fast ASGI server implementation
- [Granian](https://github.com/emmett-framework/granian) - Alternative high-performance ASGI server
- [Typer](https://typer.tiangolo.com/) - Modern CLI framework for building command-line interfaces
- [icecream](https://github.com/gruns/icecream) - Enhanced debugging utilities
- [bevy](https://github.com/bevyengine/bevy) - Rust game engine inspiration for ACB architecture
- [msgspec](https://github.com/jcrist/msgspec) - High-performance serialization library
- [attrs](https://github.com/python-attrs/attrs) - Classes without boilerplate

### Development Environment

- [PyCharm](https://www.jetbrains.com/pycharm/) - The premier Python IDE that powered the development of FastBlocks

## Special Acknowledgments

**FastAPI Inspiration**: FastBlocks draws significant inspiration from [FastAPI](https://fastapi.tiangolo.com/) by Sebastián Ramírez. FastAPI's elegant approach to modern Python web development, type safety, automatic validation, and developer experience served as a guiding light for FastBlocks' design philosophy. While FastBlocks focuses on server-side rendering with HTMX rather than API development, it embraces FastAPI's commitment to developer productivity, type safety, and modern Python features.

FastBlocks incorporates enhanced versions of **asgi-htmx** by Marcelo Trylesinski and **asgi-sitemaps** by Florian Dahlitz. These excellent libraries provided the foundation for FastBlocks' native HTMX and sitemap functionality. The original implementations have been enhanced with ACB integration, improved error handling, caching capabilities, and FastBlocks-specific optimizations while maintaining the quality and design principles of the original work.

We extend our sincere gratitude to all the maintainers and contributors of these outstanding open-source projects that make FastBlocks possible.
