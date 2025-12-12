# Sync Action

> **FastBlocks Documentation**: [Main](../../../README.md) | [Core Features](../../../README.md) | [Actions](../README.md) | [Adapters](../../adapters/README.md)

The Sync action provides bidirectional synchronization between filesystem and cloud storage with intelligent conflict resolution, cache consistency management, and atomic operations. It ensures data consistency across development, staging, and production environments.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Usage](#usage)
  - [Templates](#templates)
  - [Settings](#settings)
  - [Static Files](#static-files)
  - [Cache](#cache)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Examples](#examples)
- [Conflict Resolution](#conflict-resolution)
- [Performance Considerations](#performance-considerations)
- [Related Actions](#related-actions)

## Overview

The Sync action consolidates synchronization patterns throughout FastBlocks and ACB, providing unified interfaces for keeping templates, settings, static files, and cache layers consistent across environments. It handles complex scenarios like bidirectional sync, conflict resolution, and cache invalidation.

## Features

- **Bidirectional synchronization** with configurable conflict resolution
- **Incremental sync** based on modification times and content hashes
- **Atomic operations** with backup capability and rollback support
- **Cache coordination** with invalidation and warming
- **YAML validation** for settings files with syntax checking
- **MIME type detection** for static files with proper metadata
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
        backup_on_conflict=True,
    ),
    storage_bucket="templates",
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
        dry_run=False,
    ),
    storage_bucket="config",
    reload_config=True,
)

# Check results
print(f"Synced: {len(settings_result.synced_items)}")
print(f"Conflicts: {len(settings_result.conflicts)}")
print(f"Backed up: {len(settings_result.backed_up)}")
print(f"Config reloaded: {settings_result.config_reloaded}")
```

### Static Files

Synchronize static assets between filesystem and cloud storage with selective caching:

```python
# Basic static files sync
static_result = await sync.static()
print(f"Synced {len(static_result.synced_items)} static files")

# Custom static files sync
static_result = await sync.static(
    static_path=AsyncPath("static"),
    file_patterns=["*.css", "*.js", "*.png", "*.jpg", "*.svg"],
    strategy=SyncStrategy(
        direction=SyncDirection.BIDIRECTIONAL,
        conflict_strategy=ConflictStrategy.NEWEST_WINS,
        backup_on_conflict=True,
    ),
    storage_bucket="static",
    exclude_patterns=["*.tmp", "*.log", ".*"],
)

# Check results
print(f"Synced: {len(static_result.synced_items)}")
print(f"Assets processed: {len(static_result.assets_processed)}")
print(f"MIME types detected: {len(static_result.mime_types_detected)}")

# Show processed assets by type
for asset_path, mime_type in static_result.mime_types_detected.items():
    print(f"Asset: {asset_path} (MIME: {mime_type})")

# Check selective caching results
print(f"Cacheable assets: {len(static_result.cacheable_assets)}")
print(f"Non-cacheable assets: {len(static_result.non_cacheable_assets)}")
print(f"Cache invalidated: {len(static_result.cache_invalidated)}")

# Show assets by caching behavior
for asset in static_result.cacheable_assets:
    print(f"Cached: {asset}")
for asset in static_result.non_cacheable_assets:
    print(f"Storage only: {asset}")
```

### Cache

Synchronize cache layers for consistency and performance:

```python
# Refresh all cache layers
cache_result = await sync.cache(operation="refresh")
print(f"Refreshed {len(cache_result.invalidated_keys)} cache entries")

# Invalidate specific namespaces
cache_result = await sync.cache(
    operation="invalidate", namespaces=["templates", "bccache"], warm_templates=True
)

# Warm cache after deployment
cache_result = await sync.cache(
    operation="warm", namespaces=["templates", "responses", "gather"]
)

# Clear cache namespaces
cache_result = await sync.cache(operation="clear", namespaces=["templates"])

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
- `patterns` (list[str], optional): File patterns \["*.html", "*.jinja2", "\*.j2"\]
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

#### `sync.static()`

Synchronize static files between filesystem and cloud storage with selective caching.

```python
async def static(
    *,
    static_path: AsyncPath = None,
    file_patterns: list[str] = None,
    strategy: SyncStrategy = None,
    storage_bucket: str = "static",
    exclude_patterns: list[str] = None,
) -> StaticSyncResult
```

**Parameters:**

- `static_path` (AsyncPath, optional): Static files directory path
- `file_patterns` (list[str], optional): File patterns to include (CSS, JS, images, etc.)
- `strategy` (SyncStrategy, optional): Sync strategy configuration
- `storage_bucket` (str, default="static"): Storage bucket name
- `exclude_patterns` (list[str], optional): File patterns to exclude

**Returns:**

- `StaticSyncResult`: Sync results with MIME type detection, asset processing, and selective caching details

**Selective Caching Behavior:**

- **Cacheable files** (CSS, JS, MD, TXT): Synced to storage AND cached for performance
- **Non-cacheable files** (images, fonts, media): Synced to storage only to avoid cache bloat
- Cache TTL: 24 hours for all cached static files
- Cache keys: `static:{relative_path}` pattern

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
    direction=SyncDirection.BIDIRECTIONAL,  # Sync direction
    conflict_strategy=ConflictStrategy.NEWEST_WINS,  # Conflict resolution
    dry_run=False,  # Test mode without changes
    backup_on_conflict=True,  # Create backups
    parallel=True,  # Enable parallel processing
    max_concurrent=5,  # Concurrent operations limit
    timeout=30.0,  # Operation timeout
    retry_attempts=2,  # Retry failed operations
    retry_delay=0.5,  # Delay between retries
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

## Selective Caching for Static Files

Static file synchronization uses intelligent caching based on file type to optimize performance while avoiding cache bloat:

### Cacheable Files (Cached for Performance)

These text-based files are cached for fast delivery:

- **CSS files** (`.css`): Stylesheets cached for instant theme switching
- **JavaScript files** (`.js`): Scripts cached for rapid interactive features
- **Markdown files** (`.md`): Documentation cached for quick reference
- **Text files** (`.txt`): Configuration and data files cached for speed

### Non-Cacheable Files (Storage Only)

These binary files are synchronized to storage only to prevent cache bloat:

- **Images** (`.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.ico`, `.webp`, `.avif`): Large files that would consume excessive cache memory
- **Fonts** (`.woff`, `.woff2`, `.ttf`, `.eot`, `.otf`): Binary assets loaded infrequently
- **Media files** (`.mp4`, `.mov`, `.mp3`, `.wav`): Large media files best served from storage
- **Archives** (`.pdf`, `.zip`): Binary documents that don't benefit from caching

### Cache Management

```python
# Check caching results after sync
static_result = await sync.static()

print(f"Cached assets: {len(static_result.cacheable_assets)}")
for asset in static_result.cacheable_assets:
    print(f"  ✓ {asset} (cached)")

print(f"Storage-only assets: {len(static_result.non_cacheable_assets)}")
for asset in static_result.non_cacheable_assets:
    print(f"  → {asset} (storage only)")

# Cache invalidation tracking
print(f"Cache keys invalidated: {len(static_result.cache_invalidated)}")
for key in static_result.cache_invalidated:
    print(f"  ⚡ {key}")
```

### Performance Benefits

- **Faster CSS/JS delivery**: Cached stylesheets and scripts load instantly
- **Reduced storage costs**: Large binaries don't consume cache memory
- **Optimal cache hit rates**: Only frequently accessed text files are cached
- **Automatic cache warming**: New cacheable files are immediately available

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
        backup_on_conflict=True,
    )

    # Sync settings first
    settings_result = await sync.settings(strategy=pull_strategy, reload_config=True)

    # Sync templates
    templates_result = await sync.templates(strategy=pull_strategy)

    # Sync static files
    static_result = await sync.static(strategy=pull_strategy)

    # Refresh cache
    cache_result = await sync.cache(operation="refresh")

    print(f"Environment sync complete:")
    print(f"- Settings: {len(settings_result.synced_items)} synced")
    print(f"- Templates: {len(templates_result.synced_items)} synced")
    print(f"- Static files: {len(static_result.synced_items)} synced")
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
        dry_run=False,  # Set to True for testing
    )

    # Sync templates, static files, and settings
    templates_result = await sync.templates(strategy=push_strategy)
    static_result = await sync.static(strategy=push_strategy)
    settings_result = await sync.settings(
        strategy=push_strategy,
        reload_config=False,  # Don't reload during deployment
    )

    # Warm cache for production
    cache_result = await sync.cache(operation="warm")

    return {
        "templates": len(templates_result.synced_items),
        "static_files": len(static_result.synced_items),
        "settings": len(settings_result.synced_items),
        "cache_warmed": len(cache_result.warmed_keys),
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
        backup_on_conflict=True,
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
        dry_run=True,  # No actual changes
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

### Selective Caching Example

```python
async def demonstrate_selective_caching():
    """Demonstrate selective caching behavior for static files."""

    # Sync static files with various types
    static_result = await sync.static(
        static_path=AsyncPath("static"),
        file_patterns=[
            "*.css",
            "*.js",
            "*.md",
            "*.txt",  # Cacheable
            "*.png",
            "*.jpg",
            "*.woff",
            "*.mp4",  # Non-cacheable
        ],
    )

    print("Static File Sync Results:")
    print(f"Total assets processed: {len(static_result.assets_processed)}")

    # Show cacheable assets (cached for performance)
    print(f"\nCacheable assets ({len(static_result.cacheable_assets)}):")
    for asset in static_result.cacheable_assets:
        mime_type = static_result.mime_types_detected.get(asset, "unknown")
        print(f"  ✓ {asset} (MIME: {mime_type}) - CACHED")

    # Show non-cacheable assets (storage only)
    print(f"\nNon-cacheable assets ({len(static_result.non_cacheable_assets)}):")
    for asset in static_result.non_cacheable_assets:
        mime_type = static_result.mime_types_detected.get(asset, "unknown")
        print(f"  → {asset} (MIME: {mime_type}) - STORAGE ONLY")

    # Show cache operations
    print(f"\nCache operations:")
    print(f"  Cache keys invalidated: {len(static_result.cache_invalidated)}")
    for key in static_result.cache_invalidated:
        print(f"    ⚡ {key}")

    # Performance summary
    cacheable_count = len(static_result.cacheable_assets)
    total_count = len(static_result.assets_processed)
    cache_ratio = (cacheable_count / total_count * 100) if total_count > 0 else 0

    print(f"\nPerformance Summary:")
    print(f"  Cache hit optimization: {cache_ratio:.1f}% of assets cached")
    print(f"  Storage efficiency: {100 - cache_ratio:.1f}% of assets storage-only")

    return static_result
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
    conflict_strategy=ConflictStrategy.BACKUP_BOTH, backup_on_conflict=True
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
- **Selective Caching**: Intelligent caching based on file type optimizes performance

### Static File Caching

- **Cache Efficiency**: Only text-based files (CSS, JS, MD, TXT) are cached
- **Storage Optimization**: Binary files (images, fonts, media) bypass cache
- **Memory Management**: Cache bloat prevented by excluding large binary assets
- **Performance**: Cacheable files delivered instantly, non-cacheable from storage

### Best Practices

- Use incremental sync for large template collections
- Warm cache during low-traffic periods
- Monitor storage costs with backup strategies
- Test sync operations with dry-run mode first
- Leverage selective caching for optimal performance
- Place frequently accessed CSS/JS files in static directory for caching

## Related Actions

- [Gather Action](../gather/README.md): Discover components before syncing
- [Minify Action](../minify/README.md): Optimize assets before syncing
- [ACB Actions](https://github.com/lesleslie/acb/tree/main/acb/actions): Core utility actions
