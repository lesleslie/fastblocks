# FastBlocks Oneiric Guide

**Complete guide to using [Oneiric](https://github.com/lesleslie/oneiric) with FastBlocks**

> **Note:** This guide was rewritten during the Phase 4 doc-remediation
> pass (0.20.0). FastBlocks no longer depends on the legacy
> [ACB](https://github.com/lesleslie/acb) framework; the ACB extra was
> removed from `pyproject.toml` entirely in Phase 3.1 (0.8.0). Use the
> Oneiric integration patterns described below
> (`fastblocks.core.resolver.get_resolver()`,
> `fastblocks.core.patterns.SingletonMeta`) and see
> `docs/ONEIRIC_DEPENDS_PATTERNS.md` for the current canonical surface.

## Table of Contents

- [Overview](#overview)
- [Architecture Relationship](#architecture-relationship)
- [FastBlocks Actions](#fastblocks-actions)
- [FastBlocks Adapters](#fastblocks-adapters)
- [Configuration](#configuration)
- [Plugin Development](#plugin-development)
- [Best Practices](#best-practices)
- [Migration Guide](#migration-guide)
- [Troubleshooting](#troubleshooting)

## Overview

FastBlocks is built on [Oneiric](https://github.com/lesleslie/oneiric) v0.x and inherits the shared resolver, configuration system, and candidate-factory patterns. Oneiric provides:

- **Actions**: Modular utility packages under `fastblocks.actions/` (minify, gather, sync, query).
- **Adapters**: Pluggable components with resolver-based dependency injection (templates, cache, auth, admin, etc.).
- **Configuration**: Layered settings via `oneiric.core.config.OneiricSettings` (defaults → YAML → env vars).
- **Plugin System**: MCP server surface (`fastblocks.mcp.create_fastblocks_mcp_server`).

## Architecture Relationship

```
┌─────────────────────────────────────────────┐
│         FastBlocks Application              │
│  (Web Framework - HTMX, Templates, HTMY)    │
├─────────────────────────────────────────────┤
│              Oneiric Framework              │
│  (Adapters, Actions, Dependency Injection)  │
└─────────────────────────────────────────────┘
```

**Key Points:**

- FastBlocks uses `get_resolver()` (`fastblocks.core.resolver`) to share a single process-wide `oneiric.core.resolution.Resolver`.
- All FastBlocks adapters and actions are resolved through `await resolve_component_async(resolver, "fastblocks", "<name>")`.
- No legacy `register_pkg` call — Oneiric candidates register themselves as part of the adapter's module load.
- Configuration changes (not code changes) activate different adapters.

## FastBlocks Actions

FastBlocks actions live under `fastblocks.actions/`. They are modular,
self-contained utility functions for common web tasks. See
`fastblocks/actions/README.md` for the canonical reference.

### Available Actions

| Action | Module | Key Methods |
|--------|--------|-------------|
| **Gather** | `fastblocks.actions.gather` | `gather.routes()`, `gather.templates()`, `gather.middleware()`, `gather.models()`, `gather.application()` |
| **Sync** | `fastblocks.actions.sync` | `sync.templates()`, `sync.settings()`, `sync.cache()` |
| **Minify** | `fastblocks.actions.minify` | `minify.html()`, `minify.css()`, `minify.js()` |
| **Query** | `fastblocks.actions.query` | `UniversalQueryParser`, `create_query_context()` |

### Usage Examples

#### HTML/CSS/JS Minification

```python
from fastblocks.actions.minify import minify

# Minify HTML content
html_content = "<html><body>  <h1>Hello</h1>  </body></html>"
minified_html = minify.html(html_content)

# Minify CSS
css_content = "body { margin: 0; padding: 0; }"
minified_css = minify.css(css_content)

# Minify JavaScript
js_content = "function hello() { console.log('Hello, World!'); }"
minified_js = minify.js(js_content)
```

#### Gathering Components

```python
from fastblocks.actions.gather import gather

# Gather routes from adapters and base files
routes_result = await gather.routes()
print(f"Found {routes_result.total_routes} routes")

# Gather template components
templates_result = await gather.templates()
print(f"Loaded {len(templates_result.loaders)} template loaders")
```

#### Sync and Query

```python
from fastblocks.actions.sync import sync
from fastblocks.actions.query import create_query_context

# Sync templates between filesystem and storage
templates_result = await sync.templates()

# Convert URL query parameters into a database query context
context = create_query_context(request.query_params)
```

### Notes on the Former `acb.actions` Surface

The legacy ACB actions (`compress`, `hash`, `encode`, `secure`,
`validate`) do not have direct FastBlocks equivalents. Use the
following Python standard-library / third-party substitutes:

- **Compression / hashing / encoding**: `hashlib`, `gzip`, `json`,
  `pyyaml`, `msgpack`. For Brotli, install `brotli` directly.
- **Security primitives**: `secrets` (token generation), `bcrypt` or
  `argon2-cffi` (password hashing), `cryptography` (encryption /
  HMAC).
- **Validation**: Pydantic models, `email-validator`, `sqlparse`, or
  the FastBlocks-specific `fastblocks._validation_integration`.

## FastBlocks Adapters

FastBlocks adapters are registered as Oneiric candidates and resolved
through the shared resolver. See `fastblocks/adapters/README.md` for
the canonical adapter catalogue.

### Core Adapters (Always Available)

| Adapter | Purpose | Access Method |
|---------|---------|---------------|
| **templates** | Template rendering (Jinja2, HTMY, etc.) | `await resolve_component_async(resolver, "fastblocks", "templates")` |
| **app** | FastBlocks application instance | `await resolve_component_async(resolver, "fastblocks", "app")` |
| **cache** | Caching backend (Redis, in-memory) | `await resolve_component_async(resolver, "fastblocks", "cache")` |
| **auth** | Authentication adapter | `await resolve_component_async(resolver, "fastblocks", "auth")` |
| **admin** | Admin interface adapter | `await resolve_component_async(resolver, "fastblocks", "admin")` |

### Dependency Injection Patterns

#### Method 1: Resolver + resolve_component_async (RECOMMENDED)

```python
from fastblocks.core.resolver import get_resolver, resolve_component_async

resolver = get_resolver()


async def my_handler(request):
    templates = await resolve_component_async(resolver, "fastblocks", "templates")
    cache = await resolve_component_async(resolver, "fastblocks", "cache")

    cached = await cache.get(f"page:{request.path}")
    if cached:
        return cached

    response = await templates.app.render_template(request, "home.html")
    await cache.set(f"page:{request.path}", response, ttl=300)
    return response
```

For synchronous code, use `resolve_component(resolver, "fastblocks", "<name>")` instead — it invokes sync factories and raises `TypeError` if the factory is async.

#### Method 2: Module-Level Singleton (rare)

```python
from fastblocks.core.resolver import get_resolver, resolve_component_async

# At module load:
resolver = get_resolver()
# Then in async functions:
templates = await resolve_component_async(resolver, "fastblocks", "templates")
```

Use this pattern sparingly — resolver-level singletons can mask
async-context bugs in tests.

## Configuration

### Configuration Methods

Oneiric adapters can be configured through three methods:

1. **Environment Variables** (Recommended for production)
1. **Configuration Files** (`settings/*.yml`)
1. **Programmatic Configuration** (For advanced use cases)

### Environment Variables

```bash
# Cache (Redis)
REDIS_URL=redis://localhost:6379/0

# SQL (PostgreSQL)
DATABASE_URL=postgresql://user:pass@localhost/dbname

# Monitoring (Logfire)
LOGFIRE_TOKEN=your-token-here

# Storage (S3)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_DEFAULT_REGION=us-east-1
```

### Configuration Files

**settings/adapters.yml:**

```yaml
# Cache configuration
cache:
  module: "redis"
  url: "redis://localhost:6379/0"
  ttl: 3600

# Database configuration
sql:
  module: "postgresql"
  url: "${DATABASE_URL}"
  pool_size: 20
  max_overflow: 10

# Monitoring configuration
monitoring:
  logfire:
    enabled: true
    token: "${LOGFIRE_TOKEN}"
  sentry:
    enabled: false
    dsn: "${SENTRY_DSN}"
```

### Recommended Production Configuration

**pyproject.toml - Add to FastBlocks dependencies:**

```toml
[dependency-groups]
production = [
    "logly>=0.1.0",           # Rust-powered logger (10-100x faster)
    "redis>=5.0",             # Redis caching
    "asyncpg>=0.29",          # PostgreSQL support
    "logfire>=0.0",           # Logfire observability
    "boto3>=1.34",            # S3/GCS for static assets
]
```

## Plugin Development

FastBlocks ships an MCP plugin surface at `fastblocks.mcp`. Use it as
a template for building your own plugins.

### Minimal Plugin Example

```python
"""minimal_plugin.py - Simplest FastBlocks MCP plugin possible"""

from fastblocks.mcp import create_fastblocks_mcp_server, FastBlocksMCPServer


# Define Tools (MCP actions)
async def hello(name: str) -> dict[str, str]:
    """Say hello to someone."""
    return {"message": f"Hello, {name}!"}


async def add(a: int, b: int) -> dict[str, int]:
    """Add two numbers together."""
    return {"result": a + b}


# Register and create server
async def main() -> FastBlocksMCPServer:
    server = await create_fastblocks_mcp_server()
    # Additional registration via fastblocks.mcp.tools / .resources
    await server.initialize()
    return server


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```

For more details on plugin development, see `fastblocks/mcp/README.md`.

## Best Practices

### 1. Use FastBlocks Actions for Utilities

✅ **DO**: Use FastBlocks actions where they exist

```python
from fastblocks.actions.minify import minify

# Minify rendered templates
minified_html = minify.html(html)
```

❌ **DON'T**: Reimplement what actions already provide

```python
# Don't do this - use minify
import re

html = re.sub(r"\s+", " ", html)
```

### 2. Resolve Components Lazily

✅ **DO**: Resolve inside the async handler

```python
async def handler(request):
    templates = await resolve_component_async(resolver, "fastblocks", "templates")
    return await templates.app.render_template(request, "home.html")
```

❌ **DON'T**: Bypass the resolver

```python
from fastblocks.adapters.templates.jinja2 import Jinja2Templates  # Bypasses DI

templates = Jinja2Templates()  # Wrong - skips the configured adapter
```

### 3. Configure via Environment

✅ **DO**: Use environment variables for adapter configuration

```bash
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql://localhost/mydb
```

❌ **DON'T**: Hardcode configuration in code

```python
# Don't do this
cache = RedisCache(host="localhost", port=6379)
```

## Migration Guide

### From legacy ACB hashing helpers to Python `hashlib`

**Before** (legacy ACB API — package removed in 0.8.0):

```python
# Legacy: import hash actions from the acb.actions package,
# then await the hash method (e.g. crc32c, blake3, md5).
async def create_cache_key(template, context):
    return await <hash-helper>.crc32c(f"{template}:{context}")
```

**After** (stdlib — no extra dependency):

```python
import hashlib


def create_cache_key(template, context):
    data = f"{template}:{context}".encode()
    return hashlib.blake2b(data, digest_size=16).hexdigest()
```

### From legacy ACB compression helpers to Brotli

**Before** (legacy ACB API — package removed in 0.8.0):

```python
# Legacy: import compress actions from the acb.actions package,
# then call compress.brotli(html, level=11).
def compress_response(html):
    return <compress-helper>.brotli(html, level=11)
```

**After:**

```python
import brotli


def compress_response(html: bytes) -> bytes:
    return brotli.compress(html, quality=11)
```

### From legacy ACB logger to Oneiric logger

**Before** (legacy ACB API — package removed in 0.8.0):

```python
# Legacy: resolved a "logger" key via the ACB depends registry.
logger = <legacy-resolver>.get("logger")
```

**After:**

```python
from oneiric.core.logging import get_logger

logger = get_logger(__name__)
```

### Cache Key Migration Notes

**IMPORTANT**: Switching from CRC32C to blake2b will generate **different** cache keys than the previous MD5-based keys.

**Impact**: All existing cache entries will be invalidated on deployment.

**Mitigation:**

1. Deploy during low-traffic period
1. Pre-warm cache with critical routes
1. Monitor cache hit rates post-deployment
1. Consider gradual rollout with feature flag

## Troubleshooting

### Component Not Found

**Error**: `None` returned from `resolve_component_async`

**Solution**: Verify the candidate is registered for the given domain/key

```python
from fastblocks.core.resolver import get_resolver, resolve_component_async

resolver = get_resolver()
templates = await resolve_component_async(resolver, "fastblocks", "templates")
if templates is None:
    raise RuntimeError("templates adapter not registered")
```

### Import Errors

**Error**: `ImportError: cannot import name 'foo' from 'fastblocks.actions'`

**Solution**: Check the canonical surface in `fastblocks/actions/README.md` — not every legacy `acb.actions.*` symbol has a FastBlocks equivalent.

### Async-Factory Errors

**Error**: `TypeError: Async factory requires resolve_component_async`

**Solution**: You called the sync `resolve_component()` on an async factory. Use `resolve_component_async()` from the async handler.

## References

- [Oneiric Documentation](https://github.com/lesleslie/oneiric)
- [FastBlocks CLAUDE.md](../CLAUDE.md)
- [FastBlocks Actions README](../fastblocks/actions/README.md)
- [FastBlocks Adapters README](../fastblocks/adapters/README.md)
