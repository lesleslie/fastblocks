# FastBlocks Project Context

## Project Overview

FastBlocks is an asynchronous web application framework built on Starlette, specifically designed for rapid delivery of server-side rendered HTMX/Jinja template blocks. It combines modern Python async capabilities with server-side rendering to create dynamic, interactive web applications with minimal JavaScript.

Key features of FastBlocks include:

- Built on the Starlette ASGI framework for high performance
- Native HTMX integration for creating dynamic interfaces
- Asynchronous architecture leveraging the Asynchronous Component Base (ACB) framework
- Advanced asynchronous Jinja2 template system with fragments and partials support
- Modular, component-based architecture with pluggable adapters
- Performance optimizations including caching, Brotli compression, and HTML/CSS/JS minification
- Type safety with Pydantic v2 for validation
- Universal database support for SQL and NoSQL databases
- Dependency injection system with automatic resolution

## Project Structure

```
fastblocks/
├── actions/         # Utility functions (gather, sync, minify, query)
│   ├── gather/      # Component discovery and collection
│   ├── minify/      # Code and asset optimization
│   ├── query/       # Database query utilities
│   └── sync/        # Bidirectional synchronization
├── adapters/        # Integration modules for external systems
│   ├── app/         # Application configuration
│   ├── auth/        # Authentication providers
│   ├── admin/       # Admin interface adapters
│   ├── routes/      # Routing adapters
│   ├── sitemap/     # Sitemap generation
│   └── templates/   # Template engine adapters
├── __init__.py
├── __main__.py
├── applications.py  # FastBlocks application class
├── caching.py       # Caching system
├── cli.py           # Command-line interface
├── decorators.py    # Decorators for middleware
├── exceptions.py    # Exception handling
├── htmx.py          # Native HTMX support
├── initializers.py  # Application initialization
├── main.py          # Entry point
├── middleware.py    # ASGI middleware components
└── pyproject.toml.tmpl
```

## Core Components

### Application Architecture

- Built on Starlette ASGI framework, extending its application class and middleware system
- Uses the Asynchronous Component Base (ACB) framework for dependency injection, configuration management, and pluggable components
- Follows a component-based architecture with automatic discovery and registration of modules

### Templates System

- Advanced asynchronous Jinja2 template system with fragments and partials support
- Uses `[[` and `]]` delimiters instead of `{{` and `}}` to avoid conflicts with JavaScript
- Supports template blocks for HTMX partial updates
- Pluggable template adapters with multiple implementations (currently jinja2)
- Multi-layer loader system (Redis cache, cloud storage, filesystem)

### Routing

- Extends Starlette's routing with enhanced features for HTMX and server-side rendering
- Automatic route discovery and registration
- Support for path parameters and HTTP methods

### Middleware

- Comprehensive middleware stack including:
  - HTMX middleware for processing HTMX-specific headers
  - CSRF protection middleware
  - Session middleware
  - Brotli compression middleware
  - Security headers middleware
  - Cache middleware with rule-based configuration
  - Cache control middleware
  - Current request middleware

### HTMX Integration

- Native HTMX support built directly into the framework
- Extended request object with HTMX-specific attributes
- Specialized response class for HTMX interactions
- Template blocks for rendering specific fragments
- Response helpers for setting HTMX-specific headers

### Adapters System

- Pluggable adapter pattern for various components:
  - App: Application configuration
  - Auth: Authentication providers
  - Admin: Admin interface providers
  - Routes: Route management
  - Templates: Template engine adapters
  - Sitemap: Sitemap generation
- Each adapter category includes a base class and multiple implementations
- Allows for cloud provider flexibility and simplified migrations

### Caching

- Built-in caching system with Redis backend
- Rule-based caching configuration
- Automatic cache key generation
- Cache control headers management
- Response caching with TTL settings

## Key Technologies

- **Python 3.13+**: Primary programming language
- **Starlette**: ASGI framework foundation
- **ACB (Asynchronous Component Base)**: Dependency injection and component architecture
- **Jinja2**: Template engine with async support
- **HTMX**: Lightweight JavaScript library for dynamic interfaces
- **Pydantic v2**: Data validation and configuration management
- **Redis**: Caching backend
- **SQLAlchemy/SQLModel**: Database ORM support
- **Brotli**: Compression algorithm
- **Typer**: CLI framework

## Development Workflow

### Building and Running

```bash
# Create a new FastBlocks project
python -m fastblocks create

# Run in development mode with hot-reloading
python -m fastblocks dev

# Run in production mode
python -m fastblocks run

# Run with Granian (high-performance ASGI server)
python -m fastblocks dev --granian

# Run in Docker
python -m fastblocks run --docker
```

### Testing

```bash
# Run all tests
python -m pytest

# Run tests with coverage
python -m pytest --cov=fastblocks

# Run specific test files
python -m pytest tests/adapters/templates/
```

### CLI Commands

- `create`: Create a new FastBlocks project
- `dev`: Run in development mode
- `run`: Run in production mode
- `components`: Show available FastBlocks components
- `version`: Display FastBlocks version

## Configuration

FastBlocks uses ACB's configuration system based on Pydantic:

- YAML files for environment-specific settings
- Secret files for sensitive information
- Environment variables for overrides
- Web-specific settings for templates, routing, middleware, etc.

## Testing Approach

The test suite follows these principles:

- Uses pytest as the testing framework
- Employs comprehensive mocking to avoid filesystem operations
- Implements adapter-aware testing patterns
- Focuses on semantic action testing
- Maintains test isolation with proper fixture management
- Uses mock implementations of ACB modules to prevent filesystem access

## Best Practices

1. **Adapter Pattern**: Use the pluggable adapter system for extensibility
1. **Dependency Injection**: Leverage ACB's dependency injection for component access
1. **HTMX Integration**: Use template blocks for dynamic UI updates
1. **Template Design**: Follow the fragment-based approach for HTMX interactions
1. **Caching**: Implement rule-based caching for performance optimization
1. **Error Handling**: Use the structured exception handling system
1. **Configuration**: Follow ACB's configuration patterns with Pydantic models
