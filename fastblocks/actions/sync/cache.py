"""Cache synchronization and consistency management across layers."""

import typing as t

from acb.debug import debug

from .strategies import SyncResult, SyncStrategy


class CacheSyncResult(SyncResult):
    def __init__(
        self,
        *,
        invalidated_keys: list[str] | None = None,
        warmed_keys: list[str] | None = None,
        cleared_namespaces: list[str] | None = None,
        **kwargs: t.Any,
    ) -> None:
        super().__init__(**kwargs)
        self.invalidated_keys = invalidated_keys if invalidated_keys is not None else []
        self.warmed_keys = warmed_keys if warmed_keys is not None else []
        self.cleared_namespaces = (
            cleared_namespaces if cleared_namespaces is not None else []
        )


async def sync_cache(
    *,
    operation: str = "refresh",
    namespaces: list[str] | None = None,
    keys: list[str] | None = None,
    warm_templates: bool = True,
    strategy: SyncStrategy | None = None,
) -> CacheSyncResult:
    if strategy is None:
        strategy = SyncStrategy()

    if namespaces is None:
        namespaces = ["templates", "bccache", "responses"]

    debug(f"Starting cache sync: operation={operation}, namespaces={namespaces}")

    result = CacheSyncResult()

    try:
        from acb.depends import depends

        cache = depends.get("cache")

        if not cache:
            result.errors.append(Exception("Cache adapter not available"))
            return result

    except Exception as e:
        result.errors.append(e)
        return result

    try:
        if operation == "refresh":
            await _refresh_cache(cache, namespaces, strategy, result)
        elif operation == "invalidate":
            await _invalidate_cache(cache, namespaces, keys, strategy, result)
        elif operation == "warm":
            await _warm_cache(cache, namespaces, strategy, result)
        elif operation == "clear":
            await _clear_cache(cache, namespaces, strategy, result)
        else:
            result.errors.append(ValueError(f"Unknown cache operation: {operation}"))
            return result

        if (
            warm_templates
            and operation in ("refresh", "invalidate")
            and result.invalidated_keys
        ):
            await _warm_template_cache(cache, strategy, result)

    except Exception as e:
        result.errors.append(e)
        debug(f"Error in cache sync operation {operation}: {e}")

    debug(
        f"Cache sync completed: {len(result.invalidated_keys)} invalidated, {len(result.warmed_keys)} warmed",
    )

    return result


async def _refresh_cache(
    cache: t.Any,
    namespaces: list[str],
    strategy: SyncStrategy,
    result: CacheSyncResult,
) -> None:
    await _invalidate_cache(cache, namespaces, None, strategy, result)

    await _warm_cache(cache, namespaces, strategy, result)


async def _invalidate_cache(
    cache: t.Any,
    namespaces: list[str],
    keys: list[str] | None,
    strategy: SyncStrategy,
    result: CacheSyncResult,
) -> None:
    if strategy.dry_run:
        debug("DRY RUN: Would invalidate cache entries")
        result.invalidated_keys.append("DRY_RUN_INVALIDATION")
        return

    if keys:
        for key in keys:
            try:
                await cache.delete(key)
                result.invalidated_keys.append(key)
                debug(f"Invalidated cache key: {key}")
            except Exception as e:
                result.errors.append(e)

    for namespace in namespaces:
        try:
            if namespace == "templates":
                pattern = "template:*"
                deleted_keys = await cache.delete_pattern(pattern)
                result.invalidated_keys.extend(deleted_keys or [pattern])
                debug(f"Invalidated template cache: {pattern}")

            elif namespace == "bccache":
                pattern = "bccache:*"
                deleted_keys = await cache.delete_pattern(pattern)
                result.invalidated_keys.extend(deleted_keys or [pattern])
                debug(f"Invalidated bytecode cache: {pattern}")

            elif namespace == "responses":
                pattern = "response:*"
                deleted_keys = await cache.delete_pattern(pattern)
                result.invalidated_keys.extend(deleted_keys or [pattern])
                debug(f"Invalidated response cache: {pattern}")

            elif namespace == "gather":
                pattern = "routes:*"
                deleted_keys = await cache.delete_pattern(pattern)
                result.invalidated_keys.extend(deleted_keys or [pattern])

                pattern = "templates:*"
                deleted_keys = await cache.delete_pattern(pattern)
                result.invalidated_keys.extend(deleted_keys or [pattern])

                pattern = "middleware:*"
                deleted_keys = await cache.delete_pattern(pattern)
                result.invalidated_keys.extend(deleted_keys or [pattern])

                debug("Invalidated gather cache")

            else:
                pattern = f"{namespace}:*"
                deleted_keys = await cache.delete_pattern(pattern)
                result.invalidated_keys.extend(deleted_keys or [pattern])
                debug(f"Invalidated namespace {namespace}: {pattern}")

        except Exception as e:
            result.errors.append(e)
            debug(f"Error invalidating namespace {namespace}: {e}")


async def _warm_cache(
    cache: t.Any,
    namespaces: list[str],
    strategy: SyncStrategy,
    result: CacheSyncResult,
) -> None:
    if strategy.dry_run:
        debug("DRY RUN: Would warm cache entries")
        result.warmed_keys.append("DRY_RUN_WARMING")
        return

    for namespace in namespaces:
        try:
            if namespace == "templates":
                await _warm_template_cache(cache, strategy, result)
            elif namespace == "responses":
                await _warm_response_cache(cache, strategy, result)
            elif namespace == "gather":
                await _warm_gather_cache(cache, strategy, result)

        except Exception as e:
            result.errors.append(e)
            debug(f"Error warming namespace {namespace}: {e}")


async def _clear_cache(
    cache: t.Any,
    namespaces: list[str],
    strategy: SyncStrategy,
    result: CacheSyncResult,
) -> None:
    if strategy.dry_run:
        debug("DRY RUN: Would clear cache namespaces")
        result.cleared_namespaces.extend(namespaces)
        return

    for namespace in namespaces:
        try:
            await cache.clear(namespace)
            result.cleared_namespaces.append(namespace)
            debug(f"Cleared cache namespace: {namespace}")

        except Exception as e:
            result.errors.append(e)
            debug(f"Error clearing namespace {namespace}: {e}")


async def _warm_template_cache(
    cache: t.Any,
    strategy: SyncStrategy,
    result: CacheSyncResult,
) -> None:
    common_templates = [
        "base.html",
        "layout.html",
        "index.html",
        "404.html",
        "500.html",
        "login.html",
        "dashboard.html",
    ]

    try:
        from acb.depends import depends

        storage = depends.get("storage")

        if not storage:
            debug("Storage not available for template warming")
            return

        for template_path in common_templates:
            try:
                if await storage.templates.exists(template_path):
                    content = await storage.templates.read(template_path)

                    cache_key = f"template:{template_path}"
                    await cache.set(cache_key, content, ttl=86400)
                    result.warmed_keys.append(cache_key)

                    debug(f"Warmed template cache: {template_path}")

            except Exception as e:
                debug(f"Error warming template {template_path}: {e}")

    except Exception as e:
        debug(f"Error in template cache warming: {e}")


async def _warm_response_cache(
    cache: t.Any,
    strategy: SyncStrategy,
    result: CacheSyncResult,
) -> None:
    debug("Response cache warming not implemented - requires HTTP client")


async def _warm_gather_cache(
    cache: t.Any,
    strategy: SyncStrategy,
    result: CacheSyncResult,
) -> None:
    try:
        from fastblocks.actions.gather import (
            gather_middleware,
            gather_routes,
            gather_templates,
        )

        try:
            routes_result = await gather_routes()
            if routes_result.total_routes > 0:
                result.warmed_keys.append("gather:routes")
                debug("Warmed gather routes cache")
        except Exception as e:
            debug(f"Error warming routes cache: {e}")

        try:
            templates_result = await gather_templates()
            if templates_result.total_components > 0:
                result.warmed_keys.append("gather:templates")
                debug("Warmed gather templates cache")
        except Exception as e:
            debug(f"Error warming templates cache: {e}")

        try:
            middleware_result = await gather_middleware()
            if middleware_result.total_middleware > 0:
                result.warmed_keys.append("gather:middleware")
                debug("Warmed gather middleware cache")
        except Exception as e:
            debug(f"Error warming middleware cache: {e}")

    except Exception as e:
        debug(f"Error warming gather cache: {e}")


async def invalidate_template_cache(
    template_paths: list[str] | None = None,
    cache_namespace: str = "templates",
) -> dict[str, t.Any]:
    result: dict[str, t.Any] = {
        "invalidated": [],
        "errors": [],
    }

    try:
        from acb.depends import depends

        cache = depends.get("cache")

        if not cache:
            result["errors"].append("Cache adapter not available")
            return result

        if not template_paths:
            pattern = f"{cache_namespace}:*"
            deleted_keys = await cache.delete_pattern(pattern)
            result["invalidated"].extend(deleted_keys or [pattern])
        else:
            for template_path in template_paths:
                try:
                    template_key = f"{cache_namespace}:{template_path}"
                    await cache.delete(template_key)
                    result["invalidated"].append(template_key)

                    bytecode_key = f"bccache:{template_path}"
                    await cache.delete(bytecode_key)
                    result["invalidated"].append(bytecode_key)

                    await cache.delete_pattern(f"{cache_namespace}:*:{template_path}")
                    await cache.delete_pattern(f"bccache:*:{template_path}")

                    debug(f"Invalidated cache for template: {template_path}")

                except Exception as e:
                    result["errors"].append(f"{template_path}: {e}")

    except Exception as e:
        result["errors"].append(str(e))
        debug(f"Error invalidating template cache: {e}")

    return result


async def get_cache_stats(
    namespaces: list[str] | None = None,
) -> dict[str, t.Any]:
    if namespaces is None:
        namespaces = ["templates", "bccache", "responses", "gather"]

    stats: dict[str, t.Any] = {
        "total_keys": 0,
        "namespaces": {},
        "memory_usage": 0,
        "hit_rate": 0.0,
        "errors": [],
    }

    try:
        cache = await _get_cache_adapter(stats)
        if not cache:
            return stats

        await _collect_cache_info(cache, stats)
        await _collect_namespace_stats(cache, namespaces, stats)

    except Exception as e:
        stats["errors"].append(str(e))
        debug(f"Error getting cache stats: {e}")

    return stats


async def _get_cache_adapter(stats: dict[str, t.Any]) -> t.Any:
    from acb.depends import depends

    cache = depends.get("cache")
    if not cache:
        stats["errors"].append("Cache adapter not available")
    return cache


async def _collect_cache_info(cache: t.Any, stats: dict[str, t.Any]) -> None:
    try:
        info = await cache.info()
        stats["memory_usage"] = info.get("used_memory", 0)
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        stats["hit_rate"] = hits / max(hits + misses, 1)
    except Exception as e:
        stats["errors"].append(f"Error getting cache info: {e}")


async def _collect_namespace_stats(
    cache: t.Any,
    namespaces: list[str],
    stats: dict[str, t.Any],
) -> None:
    for namespace in namespaces:
        try:
            pattern = f"{namespace}:*"
            keys = await cache.keys(pattern)
            key_count = len(keys) if keys else 0

            stats["namespaces"][namespace] = {
                "key_count": key_count,
                "sample_keys": keys[:5] if keys else [],
            }

            stats["total_keys"] += key_count

        except Exception as e:
            stats["errors"].append(f"Error checking namespace {namespace}: {e}")


async def optimize_cache(
    max_memory_mb: int = 512,
    eviction_policy: str = "allkeys-lru",
) -> dict[str, t.Any]:
    result: dict[str, t.Any] = {
        "optimizations": [],
        "warnings": [],
        "errors": [],
    }

    try:
        from acb.depends import depends

        cache = depends.get("cache")

        if not cache:
            result["errors"].append("Cache adapter not available")
            return result

        try:
            max_memory_bytes = max_memory_mb * 1024 * 1024
            await cache.config_set("maxmemory", max_memory_bytes)
            result["optimizations"].append(f"Set max memory to {max_memory_mb}MB")
        except Exception as e:
            result["errors"].append(f"Error setting max memory: {e}")

        try:
            await cache.config_set("maxmemory-policy", eviction_policy)
            result["optimizations"].append(f"Set eviction policy to {eviction_policy}")
        except Exception as e:
            result["errors"].append(f"Error setting eviction policy: {e}")

        stats = await get_cache_stats()

        if stats["hit_rate"] < 0.8:
            result["warnings"].append(f"Low cache hit rate: {stats['hit_rate']:.2%}")

        if stats["total_keys"] > 10000:
            result["warnings"].append(f"High key count: {stats['total_keys']}")

        for namespace, info in stats["namespaces"].items():
            if info["key_count"] > 5000:
                result["warnings"].append(
                    f"Namespace {namespace} has {info['key_count']} keys",
                )

    except Exception as e:
        result["errors"].append(str(e))
        debug(f"Error optimizing cache: {e}")

    return result


def get_cache_sync_summary(result: CacheSyncResult) -> dict[str, t.Any]:
    return {
        "invalidated_count": len(result.invalidated_keys),
        "warmed_count": len(result.warmed_keys),
        "cleared_namespaces": len(result.cleared_namespaces),
        "errors": len(result.errors),
        "success": len(result.errors) == 0,
        "operation_summary": {
            "invalidated": result.invalidated_keys[:10],
            "warmed": result.warmed_keys[:10],
            "cleared": result.cleared_namespaces,
        },
    }
