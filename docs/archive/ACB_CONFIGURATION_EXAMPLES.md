# ACB Adapter Configuration Examples for FastBlocks

## Overview

FastBlocks automatically inherits all ACB adapters through the `register_pkg()` mechanism. This document provides practical configuration examples for common production scenarios.

## Configuration Methods

ACB adapters can be configured through three methods:

1. **Environment Variables** (Recommended for production)
1. **Configuration Files** (`config.yml`, `settings/adapters.yml`)
1. **Programmatic Configuration** (For advanced use cases)

## Core Adapters (Always Available)

### Logger Configuration

#### Option 1: Loguru (Default)

```bash
# No configuration needed - enabled by default
```

#### Option 2: Logly (High-Performance Rust Logger)

**Installation:**

```bash
uv add logly>=0.1.0
```

**Environment Variable:**

```bash
# ACB automatically detects and uses Logly when installed
# No additional configuration needed
```

**Configuration File (`settings/adapters.yml`):**

```yaml
logger:
  module: "logly"  # Switches from loguru to logly
  level: "INFO"
  format: "json"  # Options: text, json
  output: "stdout"  # Options: stdout, stderr, file
```

**Benefits**: 10-100x faster than standard Python logging

### Config Adapter

The config adapter is always available and reads from:

- `config.yml` (root directory)
- `settings/*.yml` (settings directory)
- Environment variables (prefixed with `FASTBLOCKS_`)

**Example `config.yml`:**

```yaml
app:
  name: "my-fastblocks-app"
  debug: false
  deployed: true

server:
  host: "0.0.0.0"
  port: 8000
  workers: 4

caching:
  enabled: true
  ttl: 3600
  use_acb_hashing: true  # Use ACB hash actions
```

**Environment Variable Overrides:**

```bash
FASTBLOCKS_APP_NAME="production-app"
FASTBLOCKS_APP_DEBUG="false"
FASTBLOCKS_SERVER_PORT="8080"
```

## Optional Adapters (Install as Needed)

### Cache Adapter (Redis)

**Installation:**

```bash
uv add acb[cache]
```

**Environment Variables:**

```bash
REDIS_URL="redis://localhost:6379/0"
REDIS_PASSWORD="your-password"  # Optional
REDIS_MAX_CONNECTIONS="50"
```

**Configuration File (`settings/cache.yml`):**

```yaml
cache:
  module: "redis"
  url: "redis://localhost:6379/0"
  max_connections: 50
  socket_timeout: 5
  socket_connect_timeout: 5
  decode_responses: true
  key_prefix: "fastblocks:"
```

**Usage in FastBlocks:**

```python
from acb.depends import depends, Inject


@depends.inject
async def my_handler(request, cache: Inject[Cache]):
    # Check cache
    cached = await cache.get(f"page:{request.path}")
    if cached:
        return cached

    # Generate and cache response
    response = await render_page(request)
    await cache.set(f"page:{request.path}", response, ttl=300)
    return response
```

### SQL Adapter (PostgreSQL)

**Installation:**

```bash
uv add acb[sql]
```

**Environment Variables:**

```bash
DATABASE_URL="postgresql://user:password@localhost:5432/mydb"
POSTGRES_POOL_SIZE="20"
POSTGRES_MAX_OVERFLOW="10"
```

**Configuration File (`settings/sql.yml`):**

```yaml
sql:
  module: "postgresql"
  url: "postgresql://user:password@localhost:5432/mydb"
  pool_size: 20
  max_overflow: 10
  pool_pre_ping: true
  echo: false  # Set to true for SQL query logging
```

**Usage in FastBlocks:**

```python
from acb.depends import depends
from sqlmodel import select


query = depends.get("query")

# Simple queries
users = await query.for_model(User).simple.all()
user = await query.for_model(User).simple.find(user_id)

# Advanced queries
active_users = await (
    query.for_model(User)
    .advanced.where("active", True)
    .where_gt("created_at", "2024-01-01")
    .order_by_desc("last_login")
    .limit(100)
    .all()
)
```

### Monitoring Adapter (Logfire)

**Installation:**

```bash
uv add acb[monitoring]
```

**Environment Variables:**

```bash
LOGFIRE_TOKEN="your-logfire-token"
LOGFIRE_SERVICE_NAME="fastblocks-production"
LOGFIRE_ENVIRONMENT="production"
```

**Configuration File (`settings/monitoring.yml`):**

```yaml
monitoring:
  module: "logfire"
  token: "${LOGFIRE_TOKEN}"  # Use environment variable
  service_name: "fastblocks-production"
  environment: "production"
  send_to_logfire: true
  trace_sample_rate: 1.0  # Sample 100% of traces
  console_output: false  # Set to true for local development
```

**Integration with FastBlocks:**

```python
# Logfire automatically instruments Starlette/FastAPI applications
# No additional code needed - just install and configure
```

### Storage Adapter (S3)

**Installation:**

```bash
uv add acb[storage]
```

**Environment Variables:**

```bash
AWS_ACCESS_KEY_ID="your-access-key"
AWS_SECRET_ACCESS_KEY="your-secret-key"
AWS_DEFAULT_REGION="us-east-1"
AWS_S3_BUCKET="my-fastblocks-assets"
```

**Configuration File (`settings/storage.yml`):**

```yaml
storage:
  module: "s3"
  bucket: "my-fastblocks-assets"
  region: "us-east-1"
  access_key: "${AWS_ACCESS_KEY_ID}"
  secret_key: "${AWS_SECRET_ACCESS_KEY}"
  endpoint_url: null  # For S3-compatible services (MinIO, DigitalOcean Spaces)
```

**Usage in FastBlocks:**

```python
from acb.depends import depends, Inject


@depends.inject
async def upload_template(request, storage: Inject[Storage]):
    bucket = await storage.get_bucket("my-fastblocks-assets")

    # Upload template
    await bucket.write("templates/user_card.html", template_content.encode())

    # Read template
    content = await bucket.read("templates/user_card.html")
    return content.decode()
```

### AI Adapter (Claude/Gemini)

**Installation:**

```bash
# AI adapters are included in base ACB
uv add acb
```

**Environment Variables:**

```bash
# For Claude
ANTHROPIC_API_KEY="your-claude-api-key"

# For Gemini
GOOGLE_API_KEY="your-gemini-api-key"
```

**Configuration File (`settings/ai.yml`):**

```yaml
ai:
  module: "claude"  # or "gemini"
  model: "claude-3-5-sonnet-20241022"  # or "gemini-2.0-flash"
  max_tokens: 4096
  temperature: 0.7
```

**Usage in FastBlocks:**

```python
from acb.depends import depends, Inject


@depends.inject
async def generate_content(request, ai: Inject[AI]):
    response = await ai.generate(
        prompt="Generate a product description for: {request.form['product']}",
        max_tokens=500,
    )
    return {"description": response.text}
```

## Production Configuration Examples

### High-Performance Stack

**Dependencies (`pyproject.toml`):**

```toml
[dependency-groups]
production = [
    "logly>=0.1.0",           # 10-100x faster logger
    "acb[cache]",              # Redis caching
    "acb[sql]",                # PostgreSQL support
    "acb[monitoring]",         # Logfire monitoring
    "acb[storage]",            # S3 for static assets
]
```

**Environment Variables (`.env.production`):**

```bash
# Application
FASTBLOCKS_APP_NAME="production-app"
FASTBLOCKS_APP_DEBUG="false"
FASTBLOCKS_APP_DEPLOYED="true"

# Redis Cache
REDIS_URL="redis://redis-cluster.internal:6379/0"
REDIS_MAX_CONNECTIONS="100"

# PostgreSQL
DATABASE_URL="postgresql://app_user:secure_password@db.internal:5432/app_db"
POSTGRES_POOL_SIZE="50"
POSTGRES_MAX_OVERFLOW="20"

# Logfire Monitoring
LOGFIRE_TOKEN="your-logfire-token"
LOGFIRE_SERVICE_NAME="fastblocks-production"
LOGFIRE_ENVIRONMENT="production"

# AWS S3
AWS_ACCESS_KEY_ID="your-access-key"
AWS_SECRET_ACCESS_KEY="your-secret-key"
AWS_DEFAULT_REGION="us-east-1"
AWS_S3_BUCKET="production-assets"
```

### Development Stack

**Dependencies:**

```bash
# Development uses SQLite and memory cache
uv add acb[sql]
```

**Environment Variables (`.env.development`):**

```bash
# Application
FASTBLOCKS_APP_NAME="dev-app"
FASTBLOCKS_APP_DEBUG="true"
FASTBLOCKS_APP_DEPLOYED="false"

# SQLite
DATABASE_URL="sqlite:///./dev.db"

# Memory Cache (no Redis needed)
# Cache adapter automatically falls back to memory cache
```

## Configuration File Structure

FastBlocks supports modular configuration files:

```
config/
├── config.yml              # Main application config
├── settings/
│   ├── adapters.yml       # Adapter selection (logger, cache, etc.)
│   ├── cache.yml          # Cache-specific settings
│   ├── sql.yml            # Database settings
│   ├── monitoring.yml     # Monitoring configuration
│   ├── storage.yml        # Storage configuration
│   └── ai.yml             # AI provider settings
```

**Example `settings/adapters.yml`:**

```yaml
# Select which ACB adapters to use
logger: "logly"       # Options: loguru (default), logly
cache: "redis"        # Options: redis, memory (default)
sql: "postgresql"     # Options: postgresql, mysql, sqlite
monitoring: "logfire" # Options: logfire, sentry
storage: "s3"         # Options: s3, gcs, azure
```

## Adapter Priority and Fallbacks

ACB adapters follow a priority system:

1. **Environment Variables** (highest priority)
1. **Configuration Files** (`settings/*.yml`)
1. **Default Values** (lowest priority)

**Example Priority:**

```bash
# Environment variable (HIGHEST PRIORITY)
REDIS_URL="redis://prod-redis:6379/0"

# settings/cache.yml (MEDIUM PRIORITY)
cache:
  url: "redis://dev-redis:6379/0"

# Default (LOWEST PRIORITY)
# Falls back to memory cache if no Redis configuration
```

## Testing Configuration

For testing, use environment variable overrides:

```python
import pytest


@pytest.fixture
def test_config(monkeypatch):
    """Override config for tests."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "")  # Disable Redis, use memory cache
    yield


async def test_caching(test_config):
    """Test with memory cache instead of Redis."""
    cache = depends.get("cache")  # Gets memory cache
    await cache.set("test_key", "test_value")
    assert await cache.get("test_key") == "test_value"
```

## Troubleshooting

### Adapter Not Found

**Error**: `KeyError: 'adapter_name'`

**Solution**: Install the adapter dependency group

```bash
uv add acb[cache]  # For Redis cache
uv add acb[sql]    # For SQL databases
uv add acb[monitoring]  # For Logfire/Sentry
```

### Configuration Not Loading

**Error**: Adapter using default values instead of configuration

**Solution**: Check configuration file path and environment variables

```bash
# Verify config files exist
ls -la settings/*.yml

# Check environment variables
env | grep REDIS
env | grep DATABASE
```

### Import Errors

**Error**: `ImportError: cannot import name 'adapter'`

**Solution**: Verify ACB version compatibility

```bash
uv add acb>=0.25.2  # FastBlocks requires ACB 0.25.2+
```

## Migration from Custom Implementations

### From Custom Logger to ACB Logger

**Before:**

```python
import logging

logger = logging.getLogger(__name__)
```

**After:**

```python
from acb.depends import depends

logger = depends.get("logger")  # Gets configured logger (loguru/logly)
```

### From Custom Cache to ACB Cache

**Before:**

```python
import redis

redis_client = redis.Redis(host="localhost", port=6379)
```

**After:**

```python
from acb.depends import depends

cache = depends.get("cache")  # Gets configured cache (redis/memory)
```

### From Custom Database to ACB Query

**Before:**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("postgresql://localhost/mydb")
Session = sessionmaker(bind=engine)
```

**After:**

```python
from acb.depends import depends

query = depends.get("query")  # Gets universal query interface
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

### ACB Adapter Performance

| Adapter | Performance Benefit |
|---------|-------------------|
| Logly Logger | 10-100x faster than standard logging |
| Redis Cache | Distributed caching with microsecond latency |
| PostgreSQL SQL | Connection pooling, prepared statements |
| Logfire Monitoring | Rust-powered telemetry with minimal overhead |

## References

- [ACB Documentation](https://github.com/lesleslie/acb)
- [ACB Actions README](https://github.com/lesleslie/acb/tree/main/acb/actions)
- [ACB Adapters README](https://github.com/lesleslie/acb/tree/main/acb/adapters)
- [FastBlocks ACB Integration Guide](./ACB_INTEGRATION.md)
- [FastBlocks ACB Refactoring Guide](./ACB_REFACTORING.md)
