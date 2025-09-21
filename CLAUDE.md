# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastBlocks is an asynchronous web application framework, inspired by FastAPI and built on Starlette, specifically designed for the rapid delivery of server-side rendered HTMX/Jinja template blocks. It combines modern Python async capabilities with server-side rendering to create dynamic, interactive web applications with minimal JavaScript.

## Key Architecture Components

- **Starlette Foundation**: FastBlocks extends Starlette's application class and middleware system
- **ACB Integration**: Built on [Asynchronous Component Base (ACB)](https://github.com/lesleslie/acb), providing dependency injection, configuration management, and pluggable components
  - **ACB Version Compatibility**: FastBlocks v0.14.0+ requires ACB v0.19.0+
  - **See ACB CLAUDE.md**: For detailed ACB patterns, configuration, and troubleshooting
- **Template-Focused**: Advanced asynchronous Jinja2 template system with fragments and partials support using jinja2-async-environment
- **HTMY Integration**: Built-in support for HTMY components, enabling Python-based component creation alongside Jinja2 templates
- **Adapters Pattern**: Pluggable components for authentication, admin interfaces, routing, templates, etc.
- **HTMX Integration**: First-class support for HTMX to create dynamic interfaces with server-side rendering
- **Direct ACB Imports** (v0.13.2+): Simplified dependency injection using direct ACB imports instead of wrapper system
- **Adapter Metadata** (v0.14.0+): All adapters include static MODULE_ID and MODULE_STATUS for ACB 0.19.0 compliance

## Directory Structure

```
fastblocks/
├── actions/         # Utility functions (gather, sync, query, minify)
├── adapters/        # Integration modules for external systems
│   ├── app/         # Application configuration
│   ├── auth/        # Authentication adapters
│   ├── admin/       # Admin interface adapters
│   ├── routes/      # Routing adapters
│   ├── sitemap/     # Sitemap generation
│   └── templates/   # Template engine adapters
├── applications.py  # FastBlocks application class
├── middleware.py    # ASGI middleware components
├── caching.py       # Caching system
├── cli.py           # Command-line interface (with uvicorn logging fixes)
├── initializers.py  # Application initialization
├── exceptions.py    # Custom exception classes
└── main.py          # Lazy loading app and logger components
```

## Development Commands

### Essential Commands

```bash
# Quality verification (MANDATORY before task completion)
python -m crackerjack -t --ai-agent    # AI-optimized test and quality checks

# Testing
python -m pytest                       # Run all tests
python -m pytest --cov=fastblocks      # Run with coverage
python -m pytest -v                    # Verbose test output
python -m pytest -m unit               # Unit tests only
python -m pytest -m integration        # Integration tests only
python -m pytest tests/adapters/templates/  # Run specific test directory
python -m pytest --timeout=300         # Set test timeout (configured in pyproject.toml)

# Code quality
ruff check --fix                       # Lint with automatic fixes
ruff format                            # Format code
pyright                                # Type checking
pre-commit run --all-files             # Run all pre-commit hooks

# FastBlocks CLI
python -m fastblocks create            # Create new project
python -m fastblocks dev               # Development server with hot reload
python -m fastblocks dev --granian     # Development with Granian server
python -m fastblocks run               # Production server
python -m fastblocks run --granian     # Production with Granian server
python -m fastblocks components        # Show available components
python -m fastblocks version           # Show FastBlocks version

# Package management (UV-based)
uv sync                                # Sync dependencies from uv.lock
uv add <package>                       # Add new dependency
uv remove <package>                    # Remove dependency
uv build                               # Build package
uv pip install -e .                    # Development install
```

### AI-Optimized Tools

FastBlocks includes specialized configurations for AI assistants:

```bash
# Pre-commit hooks (standard configuration)
pre-commit run --all-files

# Development dependencies include AI tools
uv add crackerjack --group dev          # Comprehensive code quality
uv add session-mgmt-mcp --group dev     # Session management
uv add pydoll-mcp --group dev           # Python development tools
```

**Features**: Comprehensive code quality checks, session management, AI-optimized development tools.

## FastBlocks Native Features

### HTMX Integration (Native Implementation)

FastBlocks includes **native HTMX support** built directly into the framework:

```python
from fastblocks.htmx import HtmxDetails, HtmxRequest, HtmxResponse, is_htmx

# Check if request is from HTMX
if is_htmx(request):
    return HtmxResponse(content="<div>HTMX Content</div>")

# Response helpers
return htmx_trigger("refresh-list", content="Updated")
return htmx_redirect("/dashboard")
return htmx_refresh()
```

**Key Features**: Native implementation, HTMX middleware, enhanced request objects, response helpers, template integration.

### HTMY Component Integration

FastBlocks includes dedicated HTMY template adapter alongside Jinja2:

```python
# Component: templates/{variant}/components/user_card.py
from dataclasses import dataclass
from typing import Any


@dataclass
class UserCard:
    name: str
    email: str
    avatar_url: str = "/static/default-avatar.png"

    def htmy(self, context: dict[str, Any]) -> str:
        return f'''
        <div class="user-card">
            <img src="{self.avatar_url}" alt="{self.name}">
            <h3>{self.name}</h3>
            <p>{self.email}</p>
        </div>
        '''


# Usage in templates
# [[ render_component("user_card", {"name": "John", "email": "john@example.com"}) ]]
```

### Database Models and Query Interface

FastBlocks leverages ACB's universal model and query system:

**Supported Models**: SQLModel, SQLAlchemy, Pydantic, msgspec, attrs, Redis-OM
**Databases**: PostgreSQL, MySQL/MariaDB, SQLite, MongoDB, Firestore, Redis

```python
from acb.depends import depends

query = depends.get("query")

# Simple queries (Active Record-like)
users = await query.for_model(User).simple.all()
user = await query.for_model(User).simple.find(1)

# Advanced query builder
users = await (
    query.for_model(User)
    .advanced.where("active", True)
    .where_gt("age", 21)
    .order_by_desc("created_at")
    .limit(10)
    .all()
)
```

### Actions System

**Gather Actions**: Unified component discovery and orchestration

```python
from fastblocks.actions.gather import gather

routes_result = await gather.routes()
templates_result = await gather.templates(admin_mode=True)
```

**Query Actions**: Automatic URL query parameter to database query conversion

```python
from fastblocks.actions.query import UniversalQueryParser

parser = UniversalQueryParser(request, User)
results = await parser.parse_and_execute()
```

**Sync Actions**: Multi-layer synchronization for settings, templates, and static files

```python
from fastblocks.actions.sync import sync

await sync.settings(reload_config=True)
await sync.templates()
await sync.static()
```

### Sitemap Generation

Multiple strategies: native (routes), static (predefined), dynamic (database), cached (background refresh).

Configuration: `settings/sitemap.yml`

```yaml
module: "native"
domain: "example.com"
change_freq: "weekly"
cache_ttl: 3600
```

## Development Guidelines

### Critical Requirements

1. **Testing**: Tests must never create actual files. Use provided mocking framework (MockAsyncPath, MockAdapter, etc.)
1. **ACB Compliance**: Always use direct ACB imports (`from acb.depends import depends`)
1. **Python Version**: Target Python 3.13+ with modern syntax (set in pyproject.toml)
1. **Template System**: Use `[[` and `]]` delimiters, async rendering
1. **Error Handling**: Structured exceptions with HTMX-aware responses
1. **Package Management**: Use UV for all dependency management (not pip or PDM)
1. **Signal Handling**: CLI includes proper signal handlers for graceful shutdown

### Code Quality Standards

**Modern Python Patterns (Refurb compliance)**:

- Use `pathlib.Path` instead of `os.path`
- Use `str.removeprefix()` and `str.removesuffix()`
- Use `|` for union types instead of `Union`
- Use `dict1 | dict2` for merging
- Always use context managers for file operations

**Security Standards (Bandit compliance)**:

- Never use `eval()`, `exec()`, `subprocess.shell=True`
- Use `secrets` module for cryptography, never `random`
- Never hardcode secrets in source code
- Use parameterized queries, validate all inputs

**Pre-commit hooks**: Core file structure validators, UV dependency management, security checks (detect-secrets, bandit), Python quality tools (ruff, pyright, refurb, vulture, complexipy), and project formatting (pyproject-fmt, codespell).

### ACB Best Practices

**Critical Rules**:

- All adapter `__init__.py` files MUST remain empty (except docstrings)
- Use ACB dependency injection: `depends.get("adapter_name")`
- Register adapters with `depends.set(MyAdapter)` in `suppress(Exception)` block
- Include ACB 0.19.0 metadata: `MODULE_ID` (UUID7) and `MODULE_STATUS`

**Common Violations to Avoid**:

```python
# ❌ WRONG
from fastblocks.adapters.templates.jinja2 import Templates

templates = Templates()

# ✅ CORRECT
from acb.depends import depends

templates = depends.get("templates")
```

### Error Handling and Debugging

FastBlocks implements structured exception hierarchy with HTMX-aware responses:

```python
from fastblocks.exceptions import FastBlocksException, ConfigurationError


# HTMX requests get plain text, regular requests get HTML
class CustomErrorHandler(ErrorHandler):
    async def handle(self, exception, context, request):
        if hasattr(request, "scope") and request.scope.get("htmx"):
            return PlainTextResponse("Error message")
        return HTMLResponse(template_content)
```

### Recent Changes (v0.14.0+)

- **Direct ACB Imports**: Use `from acb.depends import depends` (no wrapper system)
- **Template System**: Null safety, enhanced error handling, Redis bytecode cache fixes
- **CLI Improvements**: Fixed uvicorn logging, signal handling, template reload exclusions, added Granian support
- **Lazy Loading**: App and logger initialize on first use for better performance
- **ACB 0.19.0 Compatibility**: Static adapter mappings, enhanced cache interface
- **UV Package Management**: Full migration from PDM to UV for dependency management
- **Middleware Management**: Enhanced position-based middleware system with caching

### Deployment and Production

**Server Options**: Uvicorn (default), Granian (high-performance)
**Optimizations**: Brotli compression, template caching, static file optimization, async everything, connection pooling
**Configuration**: `config.deployed = True/False` adjusts caching and debug features

## Task Completion Requirements

**MANDATORY: Before marking any task as complete, AI assistants MUST:**

1. **Run crackerjack verification**: Execute `python -m crackerjack -t --ai-agent`
1. **Fix any issues found**: Address all formatting, linting, type checking, and test failures
1. **Re-run verification**: Ensure crackerjack passes completely
1. **Document verification**: Mention that crackerjack verification was completed successfully

**Never skip crackerjack verification** - it's the project's standard quality gate.

## Development Workflow

### Project Structure Requirements

- **Python 3.13+**: Strictly enforced in pyproject.toml
- **UV Package Management**: All dependency operations use UV (uv.lock, not pdm.lock)
- **Test Configuration**: Comprehensive pytest setup with timeout, coverage, and markers
- **Quality Gates**: Pre-commit hooks with structured validation pipeline
- **CLI Integration**: FastBlocks CLI with Uvicorn and Granian server support

### Testing Framework

FastBlocks uses pytest with comprehensive configuration:

```bash
# Test markers (defined in pyproject.toml)
pytest -m unit          # Unit tests
pytest -m integration   # Integration tests
pytest -m benchmark     # Performance tests

# Coverage requirements
pytest --cov=fastblocks --cov-fail-under=42

# Timeout configuration
pytest --timeout=300    # 5-minute timeout per test
```

### Documentation Audit Requirements

AI assistants must regularly audit documentation for:

- Package manager consistency (UV, not PDM)
- Python 3.13+ requirement accuracy
- ACB integration accuracy
- Command and URL validation
- Template syntax correctness (`[[` `]]`)
- CLI command accuracy (dev/run with --granian option)
- Workflow currency

When completing audits, document files reviewed, issues found, changes made, ACB compliance verification, and example testing confirmation.
