# FastBlocks Project Context

## Project Overview

FastBlocks is an asynchronous web application framework built on Starlette, specifically designed for the rapid delivery of server-side rendered HTMX/Jinja template blocks. It combines modern Python async capabilities with server-side rendering to create dynamic, interactive web applications with minimal JavaScript.

The framework is built on the **Asynchronous Component Base (ACB)** framework (now migrated to Oneiric), leveraging ACB's powerful adapter pattern for seamless component swapping, cloud provider migrations, and tailored customizations without extensive code changes.

### Key Features
- **Starlette Foundation**: Built on the Starlette ASGI framework for high performance
- **Native HTMX Integration**: Built-in HTMX support for creating dynamic interfaces with server-side rendering
- **Asynchronous Architecture**: Built on Asynchronous Component Base (ACB) / Oneiric, providing dependency injection, configuration management, and pluggable components
- **Dual Template Systems**: Advanced asynchronous Jinja2 template system with fragments and partials support, plus HTMY for type-safe Python-based component creation
- **Modular Design**: Pluggable adapters for authentication, admin interfaces, routing, templates, and sitemap generation
- **Cloud Flexibility**: Easily switch between cloud providers or create hybrid deployments by swapping adapters
- **Performance Optimized**: Built-in caching system, Brotli compression, and HTML/CSS/JS minification
- **Type Safety**: Leverages Pydantic v2 for validation and type safety throughout

## Architecture

### Core Components
- `fastblocks/applications.py`: Contains the main application class and initialization logic
- `fastblocks/middleware.py`: Implements various middleware components
- `fastblocks/cli.py`: Command-line interface implementation
- `fastblocks/decorators.py`: Framework-specific decorators
- `fastblocks/actions/`: Contains reusable action components
- `fastblocks/adapters/`: Pluggable adapter implementations
- `fastblocks/mcp/`: MCP (Middleware Communication Protocol) related components

### Dependency Injection System
The framework uses Oneiric (migrated from ACB) for dependency injection, with a resolver system that manages component lifecycle and dependencies. The `depends` object provides access to injected services throughout the application.

### Migration Status
The project has completed a migration from ACB to Oneiric for the dependency injection system. The codebase reflects this transition with migration comments indicating the change.

## Building and Running

### Prerequisites
- Python 3.13+

### Setup Commands
```bash
# Install dependencies
uv sync

# Run the demo application
uv run python -m fastblocks serve

# Run tests
uv run python -m pytest

# Run tests with coverage
uv run python -m pytest --cov=fastblocks

# Format code
uv run ruff format .

# Lint code
uv run ruff check --fix .
```

### Development Commands
- `uv run python -m fastblocks --help`: Show CLI options
- `uv run python -m crackerjack -t --ai-fix`: Run quality gate with auto-fixes
- `uv build`: Create distribution packages

## Development Conventions

### Coding Style
- Format with `ruff format`
- Lint with `ruff check --fix` before committing
- Use 4-space indentation
- Follow `snake_case` for functions and module globals
- Use `PascalCase` for classes
- Use `SCREAMING_SNAKE_CASE` for constants
- Include type hints for all public APIs

### Testing Guidelines
- Use pytest with appropriate markers (`@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.benchmark`)
- Mirror runtime structure inside `tests/` directory
- Target at least 31% coverage (as configured)
- Include both happy-path and cancellation tests for async code

### Commit Guidelines
- Follow Conventional Commit style: `type(scope): summary`
- Keep commits focused
- Separate refactor-only changes in `refactor(*)` commits

## Project Structure
```
fastblocks/
├── actions/          # Reusable action components
├── adapters/         # Pluggable adapter implementations  
├── mcp/              # Middleware Communication Protocol components
├── applications.py   # Main application class
├── caching.py        # Caching utilities
├── cli.py           # Command-line interface
├── middleware.py    # Middleware components
├── main.py          # Entry point
└── ...
docs/               # Documentation
tests/              # Test suite
pyproject.toml      # Project configuration and dependencies
README.md           # Main project documentation
```

## Important Notes
- The project has undergone a significant migration from ACB to Oneiric for dependency injection
- The framework supports both traditional Jinja2 templates and HTMY (Python-based templates)
- HTMX integration is a core feature, enabling server-side rendered dynamic interfaces
- The adapter pattern enables pluggable components for different implementations (auth, templates, etc.)
- The project uses uv for dependency management and project tasks