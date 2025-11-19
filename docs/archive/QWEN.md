# FastBlocks QWEN.md

## Project Overview

FastBlocks is an asynchronous web application framework built on Starlette, specifically designed for the rapid delivery of server-side rendered HTMX/Jinja template blocks. It combines modern Python async capabilities with server-side rendering to create dynamic, interactive web applications with minimal JavaScript.

The framework is built on the Asynchronous Component Base (ACB) framework, leveraging ACB's powerful adapter pattern for seamless component swapping, cloud provider migrations, and tailored customizations without extensive code changes. FastBlocks serves as a prime example of ACB's capabilities, showcasing how ACB's dependency injection, configuration management, and pluggable adapter system can create enterprise-grade applications.

### Key Features

- **Starlette Foundation**: Built on the Starlette ASGI framework for high performance
- **Native HTMX Integration**: Built-in HTMX support for creating dynamic interfaces with server-side rendering
- **Asynchronous Architecture**: Built on Asynchronous Component Base (ACB) with dependency injection and pluggable components
- **Template-Focused**: Advanced asynchronous Jinja2 template system with fragments and partials support using `[[` and `]]` delimiters
- **Modular Design**: Pluggable adapters for authentication, admin interfaces, routing, templates, and sitemap generation
- **Cloud Flexibility**: Easily switch between cloud providers by swapping adapters
- **Performance Optimized**: Built-in caching system, Brotli compression, and HTML/CSS/JS minification
- **Type Safety**: Leverages Pydantic v2 for validation and type safety throughout
- **Universal Database Support**: Works with SQL (PostgreSQL, MySQL, SQLite) and NoSQL (MongoDB, Firestore, Redis) databases
- **Multiple Model Types**: Supports SQLModel, SQLAlchemy, Pydantic, msgspec, attrs, and Redis-OM
- **Admin Interface**: Integrated SQLAlchemy Admin support for database management
- **Dependency Injection**: Robust dependency injection system with automatic resolution

## Architecture

### Core Components

- **Applications**: The `FastBlocks` class extends Starlette's application class, providing enhanced middleware management and initialization
- **Middleware**: Comprehensive middleware stack including HTMX processing, CSRF protection, session management, compression, and security headers
- **HTMX Integration**: Native HTMX support with `HtmxRequest`, `HtmxResponse`, and helper functions
- **Adapters**: Pluggable components following ACB patterns with standardized interfaces
- **Templates**: Advanced asynchronous Jinja2 template system with FastBlocks-specific delimiters (`[[` and `]]`)

### Adapter System

FastBlocks uses a sophisticated adapter system that enables pluggable components:

- **App**: Application configuration and initialization
- **Auth**: Authentication providers (Basic, etc.)
- **Admin**: Admin interface providers (SQLAdmin)
- **Routes**: Route management and discovery
- **Templates**: Template engine adapters (Jinja2, HTMY)
- **Sitemap**: Sitemap generation strategies
- **Images**: Cloud-based image processing (Cloudinary, ImageKit, etc.)
- **Styles**: CSS frameworks (Bulma, WebAwesome, etc.)
- **Icons**: Icon libraries (FontAwesome, Lucide, etc.)
- **Fonts**: Web font management

## Building and Running

### Prerequisites

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) package manager (recommended) or pip

### Installation

```bash
uv add fastblocks
```

### Creating a New Project

Use the CLI to create a new project:

```bash
python -m fastblocks create
```

### Running Applications

Development mode with hot-reloading:

```bash
python -m fastblocks dev
```

Production mode:

```bash
python -m fastblocks run
```

With Granian server:

```bash
python -m fastblocks dev --granian
```

### Optional Dependencies

FastBlocks uses PEP 735 dependency groups:

```bash
uv add --group admin      # SQLAlchemy Admin interface
uv add --group sitemap    # Automatic sitemap generation
uv add --group monitoring # Sentry and Logfire integration
uv add --group dev        # Development tools
```

## Development Conventions

### Dependency Injection

FastBlocks follows modern ACB patterns using `Inject()` for type-safe dependency injection:

```python
from acb.adapters import import_adapter
from acb.depends import Inject

Templates = import_adapter("templates")


async def homepage(request, templates: Templates = Inject()):
    return await templates.app.render_template(
        request, "index.html", context={"title": "FastBlocks Demo"}
    )
```

### Template Delimiters

FastBlocks uses `[[` and `]]` instead of `{{` and `}}` to avoid conflicts with JavaScript frameworks:

```html
<title>[[ title ]]</title>
<h1>Welcome, [[ user.name ]]!</h1>
```

### Middleware Positioning

FastBlocks has a position-based middleware system with defined positions:

- CSRF: 0
- SESSION: 1
- HTMX: 2
- CURRENT_REQUEST: 3
- COMPRESSION: 4
- SECURITY_HEADERS: 5

## Testing

FastBlocks includes comprehensive test coverage with files organized by component:

- `test_applications.py` - Application class functionality
- `test_middleware.py` - Middleware functionality
- `test_htmx.py` - HTMX integration
- `test_templates_base.py` - Template system testing
- `test_cli_comprehensive.py` - CLI functionality testing
- And many more specialized test files

Test configuration is in `pyproject.toml` with pytest settings, including async support and coverage reporting.

## CLI Commands

- `create`: Create a new FastBlocks project
- `dev`: Run in development mode with hot-reloading
- `run`: Run in production mode
- `components`: Show available adapters and components
- `scaffold`: Create new HTMY components
- `list`: List discovered HTMY components
- `validate`: Validate a specific component
- `info`: Get detailed component information
- `syntax-check`: Check template syntax
- `format-template`: Format template files
- `generate-ide-config`: Generate IDE configurations
- `start-language-server`: Start the language server
- `mcp`: Start the Model Context Protocol server

## Project Structure

```
fastblocks/
├── actions/          # Utility functions (minify, gather, sync)
├── adapters/         # Integration modules for external systems
│   ├── admin/        # Admin interface adapters
│   ├── app/          # Application configuration
│   ├── auth/         # Authentication adapters
│   ├── routes/       # Routing adapters
│   ├── sitemap/      # Sitemap generation
│   └── templates/    # Template engine adapters
├── applications.py   # FastBlocks application class
├── caching.py        # Caching functionality
├── cli.py           # Command-line interface
├── decorators.py    # Utility decorators
├── exceptions.py    # Custom exception classes
├── htmx.py          # Native HTMX support
├── middleware.py    # ASGI middleware components
└── initializers.py  # Application initialization logic
```

## Quick Start Example

```python
from starlette.routing import Route
from acb.adapters import import_adapter
from acb.depends import Inject

Templates = import_adapter("templates")
App = import_adapter("app")


async def homepage(request, templates: Templates = Inject()):
    return await templates.app.render_template(
        request, "index.html", context={"title": "FastBlocks Demo"}
    )


routes = [Route("/", endpoint=homepage)]

app: App = Inject()
```

## Development Environment

FastBlocks uses a modern Python development environment with:

- Python 3.13+ requirement
- uv package manager
- Pydantic v2 for configuration and validation
- Ruff for linting and formatting
- pytest for testing
- Type checking with strict mode
- Pre-commit hooks for code quality
