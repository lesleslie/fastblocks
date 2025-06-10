# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastBlocks is an asynchronous web application framework, inspired by FastAPI and built on Starlette, specifically designed for the rapid delivery of server-side rendered HTMX/Jinja template blocks. It combines modern Python async capabilities with server-side rendering to create dynamic, interactive web applications with minimal JavaScript.

## Key Architecture Components

- **Starlette Foundation**: FastBlocks extends Starlette's application class and middleware system
- **ACB Integration**: Built on [Asynchronous Component Base (ACB)](https://github.com/lesleslie/acb), providing dependency injection, configuration management, and pluggable components
- **Template-Focused**: Advanced asynchronous Jinja2 template system with fragments and partials support
- **Adapters Pattern**: Pluggable components for authentication, admin interfaces, routing, templates, etc.
- **HTMX Integration**: First-class support for HTMX to create dynamic interfaces with server-side rendering

## Directory Structure

The project is organized into these main components:

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
└── caching.py       # Caching system
```

## Development Commands

### Running Tests

```bash
# Run all tests
python -m pytest

# Run specific tests
python -m pytest tests/adapters/templates/

# Run with coverage
python -m pytest --cov=fastblocks

# Run a single test file
python -m pytest tests/test_cli.py

# Run tests with output
python -m pytest -s
```

### Code Quality Tools

```bash
# Run linting with ruff
ruff check

# Format code with ruff
ruff format

# Run type checking
pyright

# Run full pre-commit checks
pre-commit run --all-files
```

### Testing with Crackerjack

```bash
# Run tests with AI assistance
python -m crackerjack --ai-agent

# Show output during test execution
python -m crackerjack -s
```

## Important Notes for Development

1. **Testing Guidelines**:
   - Tests should never create actual files or directories
   - Use the mocking framework provided in the project
   - Ensure proper method delegation in mock classes

2. **Code Style**:
   - Project uses ruff for linting and formatting
   - Uses Google docstring format
   - Target Python version is 3.13+

3. **Dependency Management**:
   - Project uses PDM for dependency management
   - Also supports uv for lockfile generation

4. **Type Safety**:
   - Project uses strict typing with pyright
   - Type annotations are added with autotyping

5. **Template System**:
   - FastBlocks uses `[[` and `]]` for template variables instead of `{{` and `}}`
   - Templates are rendered asynchronously
