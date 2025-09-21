"""FastBlocks Sync Action - Unified synchronization for templates, settings, static files, and cache.

This action provides semantic synchronization capabilities following ACB patterns,
enabling bidirectional sync between filesystem and cloud storage with intelligent
conflict resolution and cache consistency management.

The sync action consolidates scattered synchronization patterns throughout FastBlocks
and ACB, providing a unified interface for:
- Template file synchronization between filesystem, storage, and cache layers
- Settings YAML file synchronization with validation and config reload
- Static file synchronization between filesystem and storage (no cache)
- Cache layer consistency and optimization

Key features:
- Bidirectional sync with configurable conflict resolution
- Incremental sync based on modification times and content hashes
- Atomic operations with backup capability
- Parallel processing with retry logic
- Cache warming and invalidation coordination
- YAML validation for settings files
- MIME type detection for static files

Usage examples:
    from fastblocks.actions.sync import sync

    result = await sync.templates()

    result = await sync.settings(reload_config=True)

    result = await sync.static()

    result = await sync.cache(operation="refresh")
"""

from typing import Any

from .cache import sync_cache
from .settings import sync_settings
from .static import sync_static
from .templates import sync_templates

__all__ = ["sync"]


class Sync:
    @staticmethod
    async def templates(*args: Any, **kwargs: Any) -> Any:
        return await sync_templates(*args, **kwargs)

    @staticmethod
    async def settings(*args: Any, **kwargs: Any) -> Any:
        return await sync_settings(*args, **kwargs)

    @staticmethod
    async def static(*args: Any, **kwargs: Any) -> Any:
        return await sync_static(*args, **kwargs)

    @staticmethod
    async def cache(*args: Any, **kwargs: Any) -> Any:
        return await sync_cache(*args, **kwargs)


sync = Sync()
