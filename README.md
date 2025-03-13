<p align="center">
<img src="https://drive.google.com/uc?id=1pMUqyvgMkhGYoLz3jBibZDl3J63HEcCC">
</p>

> **FastBlocks Documentation**: [Main](./README.md) | [Core Features](./fastblocks/README.md) | [Actions](./fastblocks/actions/README.md) | [Adapters](./fastblocks/adapters/README.md)

# FastBlocks

[![Code style: crackerjack](https://img.shields.io/badge/code%20style-crackerjack-000042)](https://github.com/lesleslie/crackerjack)

## What is FastBlocks?

FastBlocks is an asynchronous web application framework inspired by FastAPI and built on Starlette, specifically designed for the rapid delivery of server-side rendered HTMX/Jinja template blocks. It combines the power of modern Python async capabilities with the simplicity of server-side rendering to create dynamic, interactive web applications with minimal JavaScript.

## Key Features

- **Starlette Foundation**: Built on the [Starlette](https://www.starlette.io/) ASGI framework for high performance
- **HTMX Integration**: First-class support for HTMX to create dynamic interfaces with server-side rendering
- **Asynchronous Architecture**: Built on [Asynchronous Component Base (ACB)](https://github.com/lesleslie/acb) for high-performance async operations
- **Template-Focused**: Advanced asynchronous Jinja2 template system with fragments and partials support
- **Modular Design**: Pluggable adapters for authentication, admin interfaces, routing, and more
- **Performance Optimized**: Built-in Redis caching, Brotli compression, and HTML/CSS/JS minification
- **Type Safety**: Leverages Pydantic v2 for validation and type safety
- **Admin Interface**: Integrated SQLAlchemy Admin support for database management
- **Dependency Injection**: Simple yet powerful dependency injection system

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Architecture Overview](#architecture-overview)
- [Core Components](#core-components)
  - [Templates](#templates)
  - [Routing](#routing)
  - [Middleware](#middleware)
  - [HTMX Integration](#htmx-integration)
- [Adapters](#adapters)
- [Actions](#actions)
- [Configuration](#configuration)
- [Examples](#examples)
- [Documentation](#documentation)
- [License](#license)
- [Acknowledgements](#acknowledgements)

## Installation

Install FastBlocks using [pdm](https://pdm.fming.dev):

```bash
pdm add fastblocks
```

### Optional Dependencies

FastBlocks supports various optional dependencies for different features:

| Feature Group | Components | Installation Command |
|---------------|------------|----------------------|
| Admin | SQLAlchemy Admin interface | `pdm add "fastblocks[admin]"` |
| Sitemap | Automatic sitemap generation | `pdm add "fastblocks[sitemap]"` |
| Monitoring | Sentry and Logfire integration | `pdm add "fastblocks[monitoring]"` |
| Complete | All dependencies | `pdm add "fastblocks[admin,sitemap,monitoring]"` |
| Development | Development tools | `pdm add -G dev "fastblocks"` |

## Quick Start

Create a simple FastBlocks application:

```python
from starlette.routing import Route
from acb.adapters import import_adapter
from acb.depends import depends

# Import adapters
Templates, App = import_adapter(), import_adapter()

@depends.inject
async def homepage(request, templates: Templates = depends()):
    return await templates.app.render_template(
        request, "index.html", context={"title": "FastBlocks Demo"}
    )

routes = [
    Route("/", endpoint=homepage)
]

# Create the application
app = depends.get(App)
```

Create a basic template at `templates/index.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>[[ title ]]</title>
    <!-- HTMX for interactivity -->
    <script src="https://unpkg.com/htmx.org@1.9.6"></script>
</head>
<body>
    <h1>[[ title ]]</h1>

    <div hx-get="/block/counter" hx-trigger="load">
        Loading counter...
    </div>

    <button hx-post="/block/counter" hx-target="previous div">
        Increment
    </button>
</body>
</html>
```

Create a template block at `templates/blocks/counter.html`:

```html
<div>
    <h2>Counter: [[ count ]]</h2>
</div>
```

Run your application:

```bash
uvicorn myapp:app --reload
```

## Architecture Overview

FastBlocks follows a component-based architecture with automatic discovery and registration of modules:

```
fastblocks/
├── actions/         # Utility functions (minify)
├── adapters/        # Integration modules for external systems
│   ├── app/         # Application configuration
│   ├── auth/        # Authentication adapters
│   ├── admin/       # Admin interface adapters
│   ├── routes/      # Routing adapters
│   ├── sitemap/     # Sitemap generation
│   └── templates/   # Template engine adapters
├── applications.py  # FastBlocks application class
├── middleware.py    # ASGI middleware components
└── ...
```

## Core Components

### Templates

FastBlocks uses an enhanced asynchronous Jinja2 template system with support for:

- **Async Template Loading**: Load templates asynchronously from file system, cloud storage, or Redis
- **Template Fragments**: Render specific blocks of templates for HTMX partial updates
- **Custom Delimiters**: Uses `[[` and `]]` for variables instead of `{{` and `}}` to avoid conflicts with JavaScript frameworks
- **Bytecode Caching**: Redis-based bytecode caching for improved performance

### Routing

The routing system extends Starlette's routing with:

- **Automatic Route Discovery**: Routes are automatically discovered and registered
- **HTMX-Aware Endpoints**: Built-in support for HTMX requests and responses
- **Block Rendering**: Specialized endpoints for rendering template blocks

### Middleware

FastBlocks includes several middleware components:

- **HTMX Middleware**: Adds HTMX-specific request information
- **CSRF Protection**: Built-in CSRF protection for forms
- **Session Middleware**: Cookie-based session management
- **Compression**: Brotli compression for reduced payload sizes
- **Secure Headers**: Security headers for production environments

### HTMX Integration

FastBlocks is designed to work seamlessly with HTMX:

- **HtmxRequest**: Extended request object with HTMX-specific attributes
- **Template Blocks**: Specialized endpoints for rendering template fragments
- **Push URL**: Automatic URL updates for browser history

## Adapters

FastBlocks uses a pluggable adapter system for various components:

- **App**: Application configuration and initialization
- **Auth**: Authentication providers (Basic, etc.)
- **Admin**: Admin interface providers (SQLAdmin)
- **Routes**: Route management and discovery
- **Templates**: Template engine adapters (Jinja2)
- **Sitemap**: Sitemap generation

For more information about adapters, see the [Adapters Documentation](./fastblocks/adapters/README.md).

## Actions

Actions are utility functions that perform specific tasks:

- **Minify**: HTML, CSS, and JavaScript minification

For more information about actions, see the [Actions Documentation](./fastblocks/actions/README.md).

## Configuration

FastBlocks uses ACB's configuration system based on Pydantic:

```python
from acb.config import Config
from acb.depends import depends

config = depends.get(Config)

# Access configuration values
secret_key = config.app.secret_key
debug_mode = config.debug.fastblocks
```

## Examples

### Creating a Dynamic Counter with HTMX

```python
from starlette.routing import Route
from acb.adapters import import_adapter
from acb.depends import depends

# Import adapters
Templates, App = import_adapter(), import_adapter()

counter = 0

@depends.inject
async def get_counter(request, templates: Templates = depends()):
    return await templates.app.render_template(
        request, "blocks/counter.html", context={"count": counter}
    )

@depends.inject
async def increment_counter(request, templates: Templates = depends()):
    global counter
    counter += 1
    return await templates.app.render_template(
        request, "blocks/counter.html", context={"count": counter}
    )

routes = [
    Route("/block/counter", endpoint=get_counter, methods=["GET"]),
    Route("/block/counter", endpoint=increment_counter, methods=["POST"]),
]

# Create the application
app = depends.get(App)
```

## Documentation

For more detailed documentation about FastBlocks components:

- [**Core Features**](./fastblocks/README.md): Applications, middleware, and core functionality
- [**Actions**](./fastblocks/actions/README.md): Utility functions like minification
- [**Adapters**](./fastblocks/adapters/README.md): Pluggable components for various features
  - [**App Adapter**](./fastblocks/adapters/app/README.md): Application configuration
  - [**Auth Adapter**](./fastblocks/adapters/auth/README.md): Authentication providers
  - [**Admin Adapter**](./fastblocks/adapters/admin/README.md): Admin interface
  - [**Routes Adapter**](./fastblocks/adapters/routes/README.md): Routing system
  - [**Templates Adapter**](./fastblocks/adapters/templates/README.md): Template engine
  - [**Sitemap Adapter**](./fastblocks/adapters/sitemap/README.md): Sitemap generation

## License

This project is licensed under the terms of the BSD 3-Clause license.

## Acknowledgements

ACB "blocks" logo used by permission from <a href="https://andycoeband.com">Andy Coe Band</a>

Special thanks to the following open-source projects that power FastBlocks:
- [Starlette](https://www.starlette.io/)
- [HTMX](https://htmx.org/)
- [Jinja2](https://jinja.palletsprojects.com/)
- [Pydantic](https://pydantic-docs.helpmanual.io/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [ACB](https://github.com/lesleslie/acb)
- [jinja2-async-environment](https://github.com/lesleslie/jinja2-async-environment)
- [starlette-async-jinja](https://github.com/lesleslie/starlette-async-jinja)
