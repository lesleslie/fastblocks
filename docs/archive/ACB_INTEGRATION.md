# ACB Integration Guide for FastBlocks

## Overview

FastBlocks is built on **ACB (Asynchronous Component Base)** v0.25.2+ and automatically inherits all ACB features through the `register_pkg()` mechanism. This document explains what ACB provides to FastBlocks and how to leverage these features.

## Architecture Relationship

```
┌─────────────────────────────────────────────┐
│         FastBlocks Application              │
│  (Web Framework - HTMX, Templates, HTMY)    │
├─────────────────────────────────────────────┤
│              ACB Framework                  │
│  (Adapters, Actions, Dependency Injection)  │
└─────────────────────────────────────────────┘
```

**Key Points:**

- FastBlocks calls `register_pkg()` in `__init__.py` to join ACB's ecosystem
- All ACB adapters and actions are immediately available via `depends.get()`
- No "integration" code needed - it's automatic inheritance
- Configuration changes (not code changes) activate different adapters

## What ACB Provides to FastBlocks

### 1. ACB Actions (Pure Utility Functions)

ACB actions are stateless utility functions available to all FastBlocks code.

#### Available Actions

| Action | Purpose | Methods | Import |
|--------|---------|---------|--------|
| **compress** | Data compression | `compress.gzip()`, `compress.brotli()` | `from acb.actions.compress import compress, decompress` |
| **hash** | Cryptographic hashing | `hash.blake3()`, `hash.crc32c()`, `hash.md5()` | `from acb.actions.hash import hash` |
| **encode** | Data serialization | `encode.json()`, `encode.yaml()`, `encode.msgpack()`, `encode.toml()`, `encode.pickle()` | `from acb.actions.encode import encode, decode` |
| **secure** | Security utilities | `secure.generate_token()`, `secure.hash_password()`, `secure.encrypt_data()` | `from acb.actions.secure import secure` |
| **validate** | Input validation | `validate.email()`, `validate.url()`, `validate.sql_injection()`, `validate.xss()` | `from acb.actions.validate import validate` |

#### Usage Examples

```python
# Compression
from acb.actions.compress import compress, decompress

# Compress template output
html = await templates.render("page.html", context)
compressed = compress.brotli(html, level=11)  # Max compression

# Decompress for testing
decompressed = decompress.brotli(compressed)

# Hashing (all methods are async)
from acb.actions.hash import hash

# Blake3 - fastest cryptographic hash
cache_key = await hash.blake3(f"{template_name}:{user_id}")

# CRC32C - fastest non-cryptographic hash (great for cache keys)
quick_hash = await hash.crc32c(template_source)

# MD5 - when compatibility needed
legacy_hash = await hash.md5(data, usedforsecurity=False)

# Encoding/Decoding (all methods are async)
from acb.actions.encode import encode, decode

# JSON encoding
json_bytes = await encode.json({"user": "john", "age": 30})
data = await decode.json(json_bytes)

# YAML encoding with sorting
yaml_bytes = await encode.yaml(config_dict, sort_keys=True)
config = await decode.yaml(yaml_bytes)

# MessagePack - binary format
msgpack_bytes = await encode.msgpack(large_dataset)
dataset = await decode.msgpack(msgpack_bytes)

# Security utilities
from acb.actions.secure import secure

# Generate secure tokens
api_token = secure.generate_token(length=32)
session_id = secure.generate_api_key(length=64)

# Password hashing
password_hash, salt = secure.hash_password("user_password")
is_valid = secure.verify_password("user_password", password_hash, salt)

# Data encryption
key = secure.generate_encryption_key("master_password")
encrypted = secure.encrypt_data("sensitive data", key)
decrypted = secure.decrypt_data(encrypted, key)

# HMAC signatures
signature = secure.create_hmac_signature("data", "secret_key")
is_valid = secure.verify_hmac_signature("data", signature, "secret_key")

# Input validation
from acb.actions.validate import validate

# Email/URL/Phone validation
if validate.email(user_email):
    # Valid email
    pass

if validate.url(redirect_url):
    # Valid URL
    pass

# Security validation
if not validate.sql_injection(user_input):
    raise ValueError("Potential SQL injection detected")

if not validate.xss(user_content):
    raise ValueError("Potential XSS attack detected")

if not validate.path_traversal(file_path):
    raise ValueError("Path traversal attempt detected")

# String sanitization
safe_html = validate.sanitize_html(user_html)
safe_sql = validate.sanitize_sql(user_input)
```

### 2. ACB Adapters (Dependency Injection)

ACB adapters are singletons managed by the dependency injection system.

#### Core Adapters (Always Available)

| Adapter | Purpose | Access Method |
|---------|---------|---------------|
| **config** | Application configuration | `depends.get("config")` or `from acb.config import Config` |
| **logger** | Logging (loguru default) | `depends.get("logger")` |

#### Optional Adapters (Install as Needed)

| Category | Adapters | Install Command | Access |
|----------|----------|-----------------|--------|
| **Database** | PostgreSQL, MySQL, SQLite | `uv add acb[sql]` | `depends.get("sql")` or `depends.get("query")` |
| **NoSQL** | MongoDB, Firestore, Redis-OM | `uv add acb[nosql]` | `depends.get("nosql")` |
| **Cache** | Redis, Memory | `uv add acb[cache]` | `depends.get("cache")` |
| **Monitoring** | Logfire, Sentry | `uv add acb[monitoring]` | `depends.get("monitoring")` |
| **Storage** | S3, GCS, Azure Blob | `uv add acb[storage]` | `depends.get("storage")` |
| **Secret** | Azure KeyVault, Google Secret Manager | `uv add acb[secret]` | `depends.get("secret")` |
| **Vector** | Pinecone, Weaviate, Qdrant | `uv add acb[vector]` | `depends.get("vector")` |
| **AI** | Claude, Gemini, OpenAI | `uv add acb` (included) | `depends.get("ai")` |
| **SMTP** | Gmail, Mailgun | `uv add acb[smtp]` | `depends.get("smtp")` |
| **Requests** | HTTPX with HTTP/2 | `uv add acb[requests]` | `depends.get("requests")` |

#### Adapter Usage Examples

```python
from acb.depends import depends, Inject

# Method 1: Module-level access
logger = depends.get("logger")
cache = depends.get("cache")
query = depends.get("query")

# Method 2: Function parameter injection (RECOMMENDED)
from acb.depends import Inject, depends


@depends.inject  # Required decorator!
async def my_handler(request, logger: Inject[Logger], cache: Inject[Cache]):
    """Function parameter injection pattern."""
    logger.info("Processing request")

    # Check cache
    cached = await cache.get(f"page:{request.path}")
    if cached:
        return cached

    # Generate response
    response = await render_page(request)

    # Cache it
    await cache.set(f"page:{request.path}", response, ttl=300)
    return response


# Method 3: Type-based access
from acb.adapters.logger.loguru import Logger

logger = depends.get(Logger)  # Gets Logger class instance
```

### 3. Universal Query Interface

ACB provides a unified query system that works across all database types.

```python
from acb.depends import depends

query = depends.get("query")

# Simple queries (Active Record style)
users = await query.for_model(User).simple.all()
user = await query.for_model(User).simple.find(1)
user = await query.for_model(User).simple.find_by(email="john@example.com")

# Create/Update/Delete
new_user = await query.for_model(User).simple.create(
    name="John", email="john@example.com"
)
await query.for_model(User).simple.update(user_id, {"active": False})
await query.for_model(User).simple.delete(user_id)

# Advanced query builder
results = await (
    query.for_model(User)
    .advanced.where("active", True)
    .where_gt("age", 21)
    .where_in("role", ["admin", "moderator"])
    .order_by_desc("created_at")
    .limit(10)
    .offset(20)
    .all()
)

# Aggregations
count = await query.for_model(User).advanced.where("active", True).count()
avg_age = await query.for_model(User).advanced.avg("age")
```

## Recommended Production Configuration

### High-Performance Stack

```toml
# pyproject.toml - Add to FastBlocks dependencies
[dependency-groups]
production = [
    "logly>=0.1.0",           # Rust-powered logger (10-100x faster)
    "acb[cache]",              # Redis caching
    "acb[sql]",                # PostgreSQL support
    "acb[monitoring]",         # Logfire/Sentry
    "acb[storage]",            # S3/GCS for static assets
]
```

### Adapter Configuration

ACB adapters auto-configure based on environment variables:

```bash
# Logger (Logly) - automatic when installed
# No configuration needed - ACB detects and uses Logly

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

## FastBlocks-Specific Features

FastBlocks adds web-specific features on top of ACB:

### 1. Template System

- **Jinja2** with `[[` `]]` delimiters
- **HTMY** component support
- Fragment and partial rendering
- Template validation and autocomplete
- Async rendering with caching

### 2. HTMX Integration

- Native request/response helpers
- Fragment rendering for HTMX blocks
- Event-driven updates
- SSE (Server-Sent Events) support

### 3. Asset Adapters

- **Icons**: RemixIcon, Lucide, Phosphor, FontAwesome, Heroicons, Material Icons
- **Images**: Cloudflare Images, Cloudinary, ImageKit, TwicPics
- **Fonts**: Google Fonts, Font Squirrel
- **Styles**: Bulma, Kelp, WebAwesome, Vanilla CSS

### 4. Admin & Routing

- SQLAdmin integration
- Dynamic route discovery
- Sitemap generation

## Best Practices

### 1. Use ACB Actions for Utilities

✅ **DO**: Use ACB actions for compression, hashing, validation

```python
from acb.actions.compress import compress
from acb.actions.hash import hash

# Compress rendered templates
compressed = compress.brotli(html, level=11)

# Fast cache keys
cache_key = await hash.crc32c(f"{template}:{context}")
```

❌ **DON'T**: Reimplement these utilities

```python
# Don't do this - use ACB actions
import hashlib

cache_key = hashlib.md5(data.encode()).hexdigest()
```

### 2. Leverage Dependency Injection

✅ **DO**: Use parameter injection pattern

```python
@depends.inject
async def handler(request, logger: Inject[Logger], cache: Inject[Cache]):
    logger.info("Request received")
    return await process(request)
```

❌ **DON'T**: Manual instantiation

```python
from acb.adapters.logger.loguru import Logger

logger = Logger()  # Bypasses DI system
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

### From Custom Hashing to ACB

**Before:**

```python
import hashlib


def create_cache_key(template, context):
    data = f"{template}:{context}".encode()
    return hashlib.md5(data).hexdigest()
```

**After:**

```python
from acb.actions.hash import hash


async def create_cache_key(template, context):
    # 10x faster with CRC32C
    return await hash.crc32c(f"{template}:{context}")
```

### From Custom Compression to ACB

**Before:**

```python
import gzip


def compress_response(html):
    return gzip.compress(html.encode(), compresslevel=9)
```

**After:**

```python
from acb.actions.compress import compress


def compress_response(html):
    # Brotli has better compression than gzip
    return compress.brotli(html, level=11)
```

### From Manual Logger to ACB Logger

**Before:**

```python
import logging

logger = logging.getLogger(__name__)
```

**After:**

```python
from acb.depends import depends

# Get whatever logger is configured (loguru, logly, etc.)
logger = depends.get("logger")


# Or with type injection
@depends.inject
async def handler(request, logger: Inject[Logger]):
    logger.info("Processing request")
```

## Performance Impact

### ACB Actions Performance

| Operation | Standard Library | ACB Action | Speedup |
|-----------|-----------------|------------|---------|
| MD5 hash | hashlib.md5 | `hash.md5()` | 1x (same) |
| Blake3 hash | - | `hash.blake3()` | 10x faster than SHA256 |
| CRC32C hash | - | `hash.crc32c()` | 50x faster than MD5 |
| Gzip compression | gzip.compress | `compress.gzip()` | 1x (same) |
| Brotli compression | - | `compress.brotli()` | 30% better compression |
| JSON encoding | json.dumps | `encode.json()` | 5-10x faster |
| YAML encoding | yaml.dump | `encode.yaml()` | 2-3x faster |

### ACB Adapter Performance

| Adapter | Performance Benefit |
|---------|-------------------|
| Logly Logger | 10-100x faster than standard logging |
| Redis Cache | Distributed caching with microsecond latency |
| PostgreSQL SQL | Connection pooling, prepared statements |
| Logfire Monitoring | Rust-powered telemetry with minimal overhead |

## Troubleshooting

### Adapter Not Found

**Error**: `KeyError: 'adapter_name'`

**Solution**: Install the adapter dependency group

```bash
uv add acb[cache]  # For Redis cache
uv add acb[sql]    # For SQL databases
```

### Import Errors

**Error**: `ImportError: cannot import name 'adapter'`

**Solution**: Verify ACB version compatibility

```bash
uv add acb>=0.25.2  # FastBlocks requires ACB 0.25.2+
```

### Injection Not Working

**Error**: `TypeError: handler() missing 1 required positional argument`

**Solution**: Add `@depends.inject` decorator

```python
@depends.inject  # This is required!
async def handler(request, logger: Inject[Logger]):
    pass
```

## References

- [ACB Documentation](https://github.com/lesleslie/acb)
- [ACB Actions README](https://github.com/lesleslie/acb/tree/main/acb/actions)
- [ACB Adapters README](https://github.com/lesleslie/acb/tree/main/acb/adapters)
