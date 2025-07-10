# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastBlocks is an asynchronous web application framework, inspired by FastAPI and built on Starlette, specifically designed for the rapid delivery of server-side rendered HTMX/Jinja template blocks. It combines modern Python async capabilities with server-side rendering to create dynamic, interactive web applications with minimal JavaScript.

## Key Architecture Components

- **Starlette Foundation**: FastBlocks extends Starlette's application class and middleware system
- **ACB Integration**: Built on [Asynchronous Component Base (ACB)](https://github.com/lesleslie/acb), providing dependency injection, configuration management, and pluggable components
- **Template-Focused**: Advanced asynchronous Jinja2 template system with fragments and partials support using jinja2-async-environment
- **Adapters Pattern**: Pluggable components for authentication, admin interfaces, routing, templates, etc.
- **HTMX Integration**: First-class support for HTMX to create dynamic interfaces with server-side rendering
- **Direct ACB Imports** (v0.13.2+): Simplified dependency injection using direct ACB imports instead of wrapper system

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
├── caching.py       # Caching system
├── cli.py           # Command-line interface (with uvicorn logging fixes)
├── initializers.py  # Application initialization
├── exceptions.py    # Custom exception classes
└── main.py          # Lazy loading app and logger components
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

### FastBlocks CLI Commands

```bash
# Create a new FastBlocks project
python -m fastblocks create

# Run development server with hot reload
python -m fastblocks dev

# Run production server
python -m fastblocks run

# Show available components and adapters
python -m fastblocks components
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

## Code Quality Compliance

When generating code, AI assistants MUST follow these standards to ensure compliance with Refurb and Bandit pre-commit hooks:

### Refurb Standards (Modern Python Patterns)

**Use modern syntax and built-ins:**
- Use `pathlib.Path` instead of `os.path` operations
- Use `str.removeprefix()` and `str.removesuffix()` instead of string slicing
- Use `itertools.batched()` for chunking sequences (Python 3.12+)
- Prefer `match` statements over complex `if/elif` chains
- Use `|` for union types instead of `Union` from typing
- Use `dict1 | dict2` for merging instead of `{**dict1, **dict2}`

**Use efficient built-in functions:**
- Use `any()` and `all()` instead of manual boolean loops
- Use list/dict comprehensions over manual loops when appropriate
- Use `enumerate()` instead of manual indexing with `range(len())`
- Use `zip()` for parallel iteration instead of manual indexing

**Resource management:**
- Always use context managers (`with` statements) for file operations
- Use `tempfile` module for temporary files instead of manual paths
- Prefer `subprocess.run()` over `subprocess.Popen()` when possible

### Bandit Security Standards

**Never use dangerous functions:**
- Avoid `eval()`, `exec()`, or `compile()` with any user input
- Never use `subprocess.shell=True` or `os.system()`
- Don't use `pickle` with untrusted data
- Avoid `yaml.load()` - use `yaml.safe_load()` instead

**Cryptography and secrets:**
- Use `secrets` module for cryptographic operations, never `random`
- Never hardcode passwords, API keys, or secrets in source code
- Use environment variables or secure configuration for sensitive data
- Use `hashlib` with explicit algorithms, avoid MD5/SHA1 for security

**File and path security:**
- Always validate file paths to prevent directory traversal
- Use `tempfile.mkstemp()` instead of predictable temporary file names
- Always specify encoding when opening files
- Validate all external inputs before processing

**Database and injection prevention:**
- Use parameterized queries, never string concatenation for SQL
- Validate and sanitize all user inputs
- Use prepared statements for database operations

### Integration with Pre-commit Hooks

These standards align with the project's pre-commit hooks:
- **Refurb**: Automatically suggests modern Python patterns
- **Bandit**: Scans for security vulnerabilities
- **Pyright**: Enforces type safety
- **Ruff**: Handles formatting and additional linting

By following these guidelines during code generation, AI assistants will produce code that passes all quality checks without requiring manual fixes.

## Recent Changes and Best Practices (v0.13.2+)

### Dependency Management (Breaking Change)
FastBlocks now uses **direct ACB imports** instead of the wrapper system:

```python
# OLD pattern (removed in v0.13.2)
from ...dependencies import get_acb_subset
get_adapter, import_adapter, Config, depends = get_acb_subset(...)

# NEW pattern (current)
from acb.adapters import get_adapter, import_adapter
from acb.config import Config
from acb.depends import depends
```

### Template System Enhancements
- **Null Safety**: Template adapters now gracefully handle None dependencies with automatic fallbacks
- **Enhanced Error Handling**: Better error messages and recovery in template loading
- **Redis Bytecode Cache**: Fixed string/bytes handling in jinja2-async-environment integration

### CLI and Development Experience
- **Uvicorn Logging**: Fixed duplicate logging with `log_config=None` and `propagate=False`
- **Template Reload Exclusions**: Templates directory excluded from file watching to prevent conflicts
- **Signal Handling**: Improved graceful shutdown with proper SIGINT/SIGTERM handling

### Lazy Loading Pattern
FastBlocks uses lazy loading for improved startup performance:

```python
from fastblocks import app, logger  # These are LazyApp and LazyLogger instances

# They initialize on first use
@app.get("/")  # Triggers app initialization
async def index():
    logger.info("Request handled")  # Triggers logger initialization
```

### Integration with Latest ACB (0.16.17+)
- Compatible with ACB's static adapter mappings
- Works with enhanced memory cache aiocache interface
- Supports library mode detection for better configuration

### Template Uptodate Fix
After recent jinja2-async-environment fixes, template reloading no longer produces RuntimeWarnings about unawaited coroutines. The uptodate functions now properly return coroutines when called.

### Best Practices for Development
1. **Always use direct ACB imports** - no more wrapper functions
2. **Handle None dependencies** - template loaders should fallback gracefully
3. **Use lazy loading** - import app and logger from fastblocks main module
4. **Configure uvicorn properly** - set log_config=None in production
5. **Exclude templates from reload** - prevents file watching conflicts

## Task Completion Requirements

**MANDATORY: Before marking any task as complete, AI assistants MUST:**

1. **Run crackerjack verification**: Execute `python -m crackerjack -t --ai-agent` to run all quality checks and tests with AI-optimized output
2. **Fix any issues found**: Address all formatting, linting, type checking, and test failures
3. **Re-run verification**: Ensure crackerjack passes completely (all hooks pass, all tests pass)
4. **Document verification**: Mention that crackerjack verification was completed successfully

**Why this is critical:**
- Ensures all code meets project quality standards
- Prevents broken code from being committed
- Maintains consistency with project development workflow
- Catches issues early before they become problems

**Never skip crackerjack verification** - it's the project's standard quality gate.
