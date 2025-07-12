# Sync Action

The Sync action provides bidirectional synchronization between filesystem and cloud storage with intelligent conflict resolution, cache consistency management, and atomic operations. It ensures data consistency across development, staging, and production environments.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Usage](#usage)
  - [Templates](#templates)
  - [Settings](#settings)
  - [Cache](#cache)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Examples](#examples)
- [Conflict Resolution](#conflict-resolution)
- [Performance Considerations](#performance-considerations)
- [Related Actions](#related-actions)

## Overview

The Sync action consolidates synchronization patterns throughout FastBlocks and ACB, providing unified interfaces for keeping templates, settings, and cache layers consistent across environments. It handles complex scenarios like bidirectional sync, conflict resolution, and cache invalidation.

## Features

- **Bidirectional synchronization** with configurable conflict resolution
- **Incremental sync** based on modification times and content hashes
- **Atomic operations** with backup capability and rollback support
- **Cache coordination** with invalidation and warming
- **YAML validation** for settings files with syntax checking
- **Parallel processing** with concurrency control and retry logic
- **Dry-run mode** for testing sync operations without changes

## Usage

Import the sync action from FastBlocks:

```python
from fastblocks.actions.sync import sync
```

### Templates

Synchronize templates between filesystem, cloud storage, and cache layers:

```python
# Basic template sync
templates_result = await sync.templates()
print(f"Synced {len(templates_result.synced_items)} templates")

# Custom template sync
templates_result = await sync.templates(
    template_paths=[AsyncPath("templates"), AsyncPath("custom_templates")],
    patterns=["*.html", "*.jinja2", "*.j2"],
    strategy=SyncStrategy(
        direction=SyncDirection.BIDIRECTIONAL,
        conflict_strategy=ConflictStrategy.NEWEST_WINS,
        backup_on_conflict=True
    ),
    storage_bucket="templates"
)

# Check sync results
if templates_result.has_conflicts:
    print(f"Resolved {len(templates_result.conflicts)} conflicts")

for item in templates_result.synced_items:
    print(f"Synced: {item}")

# Cache was also updated
print(f"Invalidated {len(templates_result.cache_invalidated)} cache entries")
print(f"Cleared {len(templates_result.bytecode_cleared)} bytecode entries")
```

### Settings

Synchronize YAML settings files with validation and config reload:

```python
# Basic settings sync with config reload
settings_result = await sync.settings(reload_config=True)
print(f"Synced settings for {len(settings_result.adapters_affected)} adapters")

# Custom settings sync
settings_result = await sync.settings(
    settings_path=AsyncPath("config"),
    adapter_names=["database", "cache", "email"],
    strategy=SyncStrategy(
        direction=SyncDirection.PULL,
        conflict_strategy=ConflictStrategy.REMOTE_WINS,
        dry_run=False
    ),
    storage_bucket="config",
    reload_config=True
)

# Check results
print(f"Synced: {len(settings_result.synced_items)}")
print(f"Conflicts: {len(settings_result.conflicts)}")
print(f"Backed up: {len(settings_result.backed_up)}")
print(f"Config reloaded: {settings_result.config_reloaded}")
```

### Cache

Synchronize cache layers for consistency and performance:

```python
# Refresh all cache layers
cache_result = await sync.cache(operation="refresh")
print(f"Refreshed {len(cache_result.invalidated_keys)} cache entries")

# Invalidate specific namespaces
cache_result = await sync.cache(
    operation="invalidate",
    namespaces=["templates", "bccache"],
    warm_templates=True
)

# Warm cache after deployment
cache_result = await sync.cache(
    operation="warm",
    namespaces=["templates", "responses", "gather"]
)

# Clear cache namespaces
cache_result = await sync.cache(
    operation="clear",
    namespaces=["templates"]
)

# Check results
print(f"Invalidated: {len(cache_result.invalidated_keys)}")
print(f"Warmed: {len(cache_result.warmed_keys)}")
print(f"Cleared: {len(cache_result.cleared_namespaces)}")
```

## API Reference

### Core Methods

#### `sync.templates()`

Synchronize templates between filesystem, storage, and cache.

```python
async def templates(
    *,
    template_paths: list[AsyncPath] = None,
    patterns: list[str] = None,
    strategy: SyncStrategy = None,
    storage_bucket: str = "templates",
) -> TemplateSyncResult
```

**Parameters:**
- `template_paths` (list[AsyncPath], optional): Template directories to sync
- `patterns` (list[str], optional): File patterns ["*.html", "*.jinja2", "*.j2"]
- `strategy` (SyncStrategy, optional): Sync strategy configuration
- `storage_bucket` (str, default="templates"): Storage bucket name

**Returns:**
- `TemplateSyncResult`: Sync results with cache invalidation details

#### `sync.settings()`

Synchronize settings files with validation and config reload.

```python
async def settings(
    *,
    settings_path: AsyncPath = None,
    adapter_names: list[str] = None,
    strategy: SyncStrategy = None,
    storage_bucket: str = "settings",
    reload_config: bool = True,
) -> SettingsSyncResult
```

**Parameters:**
- `settings_path` (AsyncPath, optional): Settings directory path
- `adapter_names` (list[str], optional): Specific adapters to sync (None = all)
- `strategy` (SyncStrategy, optional): Sync strategy configuration
- `storage_bucket` (str, default="settings"): Storage bucket name
- `reload_config` (bool, default=True): Reload config after sync

**Returns:**
- `SettingsSyncResult`: Sync results with affected adapters

#### `sync.cache()`

Synchronize cache layers for consistency.

```python
async def cache(
    *,
    operation: str = "refresh",
    namespaces: list[str] = None,
    keys: list[str] = None,
    warm_templates: bool = True,
    strategy: SyncStrategy = None,
) -> CacheSyncResult
```

**Parameters:**
- `operation` (str, default="refresh"): Operation type ["refresh", "invalidate", "warm", "clear"]
- `namespaces` (list[str], optional): Cache namespaces ["templates", "bccache", "responses"]
- `keys` (list[str], optional): Specific cache keys to operate on
- `warm_templates` (bool, default=True): Warm template cache after invalidation
- `strategy` (SyncStrategy, optional): Sync strategy configuration

**Returns:**
- `CacheSyncResult`: Cache operation results

## Configuration

### SyncStrategy

Configure sync behavior with comprehensive options:

```python
from fastblocks.actions.sync import SyncStrategy, SyncDirection, ConflictStrategy

strategy = SyncStrategy(
    direction=SyncDirection.BIDIRECTIONAL,     # Sync direction
    conflict_strategy=ConflictStrategy.NEWEST_WINS,  # Conflict resolution
    dry_run=False,                             # Test mode without changes
    backup_on_conflict=True,                   # Create backups
    parallel=True,                             # Enable parallel processing
    max_concurrent=5,                          # Concurrent operations limit
    timeout=30.0,                              # Operation timeout
    retry_attempts=2,                          # Retry failed operations
    retry_delay=0.5                            # Delay between retries
)
```

### Sync Directions

- `PULL`: Download from remote to local
- `PUSH`: Upload from local to remote
- `BIDIRECTIONAL`: Sync both directions based on timestamps

### Conflict Strategies

- `REMOTE_WINS`: Remote version always takes precedence
- `LOCAL_WINS`: Local version always takes precedence
- `NEWEST_WINS`: Most recently modified version wins
- `MANUAL`: Require manual conflict resolution
- `BACKUP_BOTH`: Keep both versions with suffixes

## Examples

### Complete Environment Sync

```python
from fastblocks.actions.sync import sync, SyncStrategy, SyncDirection

async def sync_environment():
    """Complete environment synchronization."""

    # Pull latest from production
    pull_strategy = SyncStrategy(
        direction=SyncDirection.PULL,
        conflict_strategy=ConflictStrategy.REMOTE_WINS,
        backup_on_conflict=True
    )

    # Sync settings first
    settings_result = await sync.settings(
        strategy=pull_strategy,
        reload_config=True
    )

    # Sync templates
    templates_result = await sync.templates(
        strategy=pull_strategy
    )

    # Refresh cache
    cache_result = await sync.cache(operation="refresh")

    print(f"Environment sync complete:")
    print(f"- Settings: {len(settings_result.synced_items)} synced")
    print(f"- Templates: {len(templates_result.synced_items)} synced")
    print(f"- Cache: {len(cache_result.warmed_keys)} warmed")
```

### Deployment Sync

```python
async def deployment_sync():
    """Sync for production deployment."""

    # Push local changes to production
    push_strategy = SyncStrategy(
        direction=SyncDirection.PUSH,
        conflict_strategy=ConflictStrategy.LOCAL_WINS,
        dry_run=False  # Set to True for testing
    )

    # Sync templates and settings
    templates_result = await sync.templates(strategy=push_strategy)
    settings_result = await sync.settings(
        strategy=push_strategy,
        reload_config=False  # Don't reload during deployment
    )

    # Warm cache for production
    cache_result = await sync.cache(operation="warm")

    return {
        "templates": len(templates_result.synced_items),
        "settings": len(settings_result.synced_items),
        "cache_warmed": len(cache_result.warmed_keys)
    }
```

### Conflict Resolution Example

```python
from fastblocks.actions.sync import ConflictStrategy, SyncStrategy

async def handle_conflicts():
    """Example of handling sync conflicts."""

    # Strategy that creates backups for conflicts
    backup_strategy = SyncStrategy(
        direction=SyncDirection.BIDIRECTIONAL,
        conflict_strategy=ConflictStrategy.BACKUP_BOTH,
        backup_on_conflict=True
    )

    result = await sync.templates(strategy=backup_strategy)

    if result.has_conflicts:
        print(f"Found {len(result.conflicts)} conflicts:")

        for conflict in result.conflicts:
            print(f"Conflict: {conflict['path']}")
            print(f"Local time: {conflict.get('local_mtime')}")
            print(f"Remote time: {conflict.get('remote_mtime')}")

    if result.backed_up:
        print(f"Created backups: {result.backed_up}")

    return result
```

### Dry Run Testing

```python
async def test_sync():
    """Test sync operations without making changes."""

    dry_run_strategy = SyncStrategy(
        direction=SyncDirection.BIDIRECTIONAL,
        dry_run=True  # No actual changes
    )

    # Test template sync
    templates_result = await sync.templates(strategy=dry_run_strategy)

    print("Dry run results:")
    for item in templates_result.synced_items:
        print(f"Would sync: {item}")

    print(f"Would sync {len(templates_result.synced_items)} templates")
    print(f"Found {len(templates_result.conflicts)} conflicts")

    return templates_result
```

## Conflict Resolution

The sync action provides several strategies for handling conflicts when the same file has been modified in both locations:

### Automatic Resolution

```python
# Newest file wins
strategy = SyncStrategy(conflict_strategy=ConflictStrategy.NEWEST_WINS)

# Remote always wins (good for pulling production config)
strategy = SyncStrategy(conflict_strategy=ConflictStrategy.REMOTE_WINS)

# Local always wins (good for deploying changes)
strategy = SyncStrategy(conflict_strategy=ConflictStrategy.LOCAL_WINS)
```

### Backup Strategies

```python
# Create backups and use one version
strategy = SyncStrategy(
    conflict_strategy=ConflictStrategy.BACKUP_BOTH,
    backup_on_conflict=True
)

# Always create backups on conflicts
strategy = SyncStrategy(backup_on_conflict=True)
```

### Manual Resolution

```python
# Require manual intervention
strategy = SyncStrategy(conflict_strategy=ConflictStrategy.MANUAL)

try:
    result = await sync.templates(strategy=strategy)
except ValueError as e:
    if "Manual conflict resolution required" in str(e):
        print("Manual resolution needed for conflicts")
        # Handle manually or use different strategy
```

## Performance Considerations

### Parallel Processing
- **I/O Bound**: Template and settings sync benefit from parallel processing
- **Concurrency**: Adjust `max_concurrent` based on storage backend limits
- **Network**: Cloud storage operations may have rate limits

### Cache Operations
- **Memory Usage**: Cache warming loads data into memory
- **Invalidation Speed**: Clearing cache is fast, warming takes time
- **Hit Rates**: Warm frequently accessed templates and routes

### File Operations
- **Incremental Sync**: Only syncs changed files based on timestamps/hashes
- **Backup Storage**: Backups consume additional storage space
- **Validation**: YAML validation adds processing time but prevents errors

### Best Practices
- Use incremental sync for large template collections
- Warm cache during low-traffic periods
- Monitor storage costs with backup strategies
- Test sync operations with dry-run mode first

## Related Actions

- [Gather Action](../gather/README.md): Discover components before syncing
- [Minify Action](../minify/README.md): Optimize assets before syncing
- [ACB Actions](https://github.com/fastblocks/acb/tree/main/acb/actions): Core utility actions
