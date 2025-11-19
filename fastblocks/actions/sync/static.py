"""Static files synchronization between filesystem, cloud storage, and selective caching.

Static sync uses selective caching based on file type:
- Text-based files (CSS, JS, MD, TXT) are cached for performance
- Binary files (images, fonts, media) sync to storage only to avoid cache bloat
"""

import typing as t
from pathlib import Path

import yaml
from acb.debug import debug
from anyio import Path as AsyncPath

from .strategies import (
    ConflictStrategy,
    SyncDirection,
    SyncResult,
    SyncStrategy,
    create_backup,
    get_file_info,
    resolve_conflict,
    should_sync,
)


class StaticSyncResult(SyncResult):
    def __init__(
        self,
        *,
        assets_processed: list[str] | None = None,
        mime_types_detected: dict[str, str] | None = None,
        cache_invalidated: list[str] | None = None,
        cache_cleared: list[str] | None = None,
        cacheable_assets: list[str] | None = None,
        non_cacheable_assets: list[str] | None = None,
        **kwargs: t.Any,
    ) -> None:
        super().__init__(**kwargs)
        self.assets_processed = assets_processed if assets_processed is not None else []
        self.mime_types_detected = (
            mime_types_detected if mime_types_detected is not None else {}
        )
        self.cache_invalidated = (
            cache_invalidated if cache_invalidated is not None else []
        )
        self.cache_cleared = cache_cleared if cache_cleared is not None else []
        self.cacheable_assets = cacheable_assets if cacheable_assets is not None else []
        self.non_cacheable_assets = (
            non_cacheable_assets if non_cacheable_assets is not None else []
        )


CACHEABLE_EXTENSIONS = {".css", ".js", ".md", ".txt"}
NON_CACHEABLE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".webp",
    ".avif",
    ".mp4",
    ".mov",
    ".mp3",
    ".wav",
    ".pdf",
    ".zip",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".otf",
}


def _is_cacheable_file(file_path: AsyncPath) -> bool:
    return file_path.suffix.lower() in CACHEABLE_EXTENSIONS


async def sync_static(
    *,
    static_path: AsyncPath | None = None,
    file_patterns: list[str] | None = None,
    strategy: SyncStrategy | None = None,
    storage_bucket: str | None = None,
    exclude_patterns: list[str] | None = None,
) -> StaticSyncResult:
    config = _prepare_static_sync_config(
        static_path, file_patterns, strategy, exclude_patterns
    )
    result = StaticSyncResult()

    if storage_bucket is None:
        storage_bucket = await _get_default_static_bucket()

    adapters = await _initialize_adapters(result)
    if not adapters:
        return result

    static_files = await _discover_static_files(
        config["static_path"],
        config["file_patterns"],
        config["exclude_patterns"],
    )
    if not static_files:
        debug("No static files found to sync")
        return result

    debug(f"Found {len(static_files)} static files to sync")

    await _sync_static_files(
        static_files,
        adapters,
        config["strategy"],
        storage_bucket,
        result,
    )

    debug(
        f"Static sync completed: {len(result.synced_items)} synced, {len(result.conflicts)} conflicts",
    )

    return result


def _prepare_static_sync_config(
    static_path: AsyncPath | None,
    file_patterns: list[str] | None,
    strategy: SyncStrategy | None,
    exclude_patterns: list[str] | None,
) -> dict[str, t.Any]:
    return {
        "static_path": static_path or AsyncPath("static"),
        "file_patterns": file_patterns
        or [
            "*.css",
            "*.js",
            "*.png",
            "*.jpg",
            "*.jpeg",
            "*.gif",
            "*.svg",
            "*.ico",
            "*.woff",
            "*.woff2",
            "*.ttf",
            "*.eot",
            "*.otf",
            "*.webp",
            "*.avif",
            "*.pdf",
            "*.zip",
            "*.tar.gz",
        ],
        "strategy": strategy or SyncStrategy(),
        "exclude_patterns": exclude_patterns or ["*.tmp", "*.log", ".*", "__pycache__"],
    }


async def _initialize_adapters(result: StaticSyncResult) -> dict[str, t.Any] | None:
    try:
        from acb.depends import depends

        storage = await depends.get("storage")
        cache = await depends.get("cache")
        if not storage:
            result.errors.append(Exception("Storage adapter not available"))
            return None

        return {"storage": storage, "cache": cache}
    except Exception as e:
        result.errors.append(e)
        return None


async def _get_default_static_bucket() -> str:
    try:
        storage_config_path = AsyncPath("settings/storage.yml")
        if await storage_config_path.exists():
            content = await storage_config_path.read_text()
            config = yaml.safe_load(content)
            if isinstance(config, dict):
                bucket_name = t.cast(
                    str, config.get("buckets", {}).get("static", "static")
                )
            else:
                bucket_name = "static"
            debug(f"Using static bucket from config: {bucket_name}")
            return bucket_name
    except Exception as e:
        debug(f"Could not load storage config, using default: {e}")
    debug("Using fallback static bucket: static")
    return "static"


async def _discover_static_files(
    static_path: AsyncPath,
    file_patterns: list[str],
    exclude_patterns: list[str],
) -> list[dict[str, t.Any]]:
    static_files: list[dict[str, t.Any]] = []

    if not await static_path.exists():
        debug(f"Static path does not exist: {static_path}")
        return static_files

    for pattern in file_patterns:
        await _discover_files_with_pattern(
            static_path,
            pattern,
            exclude_patterns,
            static_files,
        )

    return static_files


async def _discover_files_with_pattern(
    static_path: AsyncPath,
    pattern: str,
    exclude_patterns: list[str],
    static_files: list[dict[str, t.Any]],
) -> None:
    async for file_path in static_path.rglob(pattern):
        if await file_path.is_file():
            if _should_exclude_file(file_path, exclude_patterns):
                continue

            await _process_static_file(
                file_path,
                static_path,
                static_files,
            )


def _should_exclude_file(file_path: AsyncPath, exclude_patterns: list[str]) -> bool:
    import fnmatch

    file_name = file_path.name
    relative_path = str(file_path)
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(
            relative_path, pattern
        ):
            return True

    return False


async def _process_static_file(
    file_path: AsyncPath,
    static_path: AsyncPath,
    static_files: list[dict[str, t.Any]],
) -> None:
    try:
        rel_path = file_path.relative_to(static_path)
        mime_type = _detect_mime_type(file_path)
        is_cacheable = _is_cacheable_file(file_path)

        static_files.append(
            {
                "local_path": file_path,
                "relative_path": rel_path,
                "storage_path": str(rel_path),
                "mime_type": mime_type,
                "is_cacheable": is_cacheable,
            },
        )
    except ValueError:
        debug(f"Could not get relative path for {file_path}")


def _detect_mime_type(file_path: AsyncPath) -> str:
    import mimetypes

    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type or "application/octet-stream"


async def _sync_static_files(
    static_files: list[dict[str, t.Any]],
    adapters: dict[str, t.Any],
    strategy: SyncStrategy,
    storage_bucket: str,
    result: StaticSyncResult,
) -> None:
    for static_info in static_files:
        try:
            file_result = await _sync_single_static_file(
                static_info,
                adapters["storage"],
                adapters["cache"],
                strategy,
                storage_bucket,
            )
            _accumulate_static_sync_results(file_result, result)

            if file_result.get("synced"):
                result.assets_processed.append(static_info["storage_path"])
                result.mime_types_detected[static_info["storage_path"]] = static_info[
                    "mime_type"
                ]

                if static_info["is_cacheable"]:
                    result.cacheable_assets.append(static_info["storage_path"])
                else:
                    result.non_cacheable_assets.append(static_info["storage_path"])

        except Exception as e:
            result.errors.append(e)
            debug(f"Error syncing static file {static_info['relative_path']}: {e}")


def _accumulate_static_sync_results(
    file_result: dict[str, t.Any],
    result: StaticSyncResult,
) -> None:
    if file_result.get("synced"):
        result.synced_items.extend(file_result["synced"])
    if file_result.get("conflicts"):
        result.conflicts.extend(file_result["conflicts"])
    if file_result.get("errors"):
        result.errors.extend(file_result["errors"])
    if file_result.get("skipped"):
        result.skipped.extend(file_result["skipped"])
    if file_result.get("backed_up"):
        result.backed_up.extend(file_result["backed_up"])
    if file_result.get("cache_invalidated"):
        result.cache_invalidated.extend(file_result["cache_invalidated"])
    if file_result.get("cache_cleared"):
        result.cache_cleared.extend(file_result["cache_cleared"])


async def _sync_single_static_file(
    static_info: dict[str, t.Any],
    storage: t.Any,
    cache: t.Any,
    strategy: SyncStrategy,
    storage_bucket: str,
) -> dict[str, t.Any]:
    local_path = static_info["local_path"]
    storage_path = static_info["storage_path"]
    mime_type = static_info["mime_type"]
    is_cacheable = static_info["is_cacheable"]

    result = _create_sync_result()

    try:
        local_info, remote_info = await _get_file_infos(
            local_path,
            storage,
            storage_bucket,
            storage_path,
        )

        if not await _should_sync_file(
            local_info,
            remote_info,
            strategy,
            storage_path,
            result,
        ):
            return result

        await _execute_sync_operation(
            local_path,
            storage,
            cache,
            storage_bucket,
            storage_path,
            local_info,
            remote_info,
            strategy,
            mime_type,
            is_cacheable,
            result,
        )

    except Exception as e:
        result["errors"].append(e)
        debug(f"Error in _sync_single_static_file for {storage_path}: {e}")

    return result


def _create_sync_result() -> dict[str, t.Any]:
    return {
        "synced": [],
        "conflicts": [],
        "errors": [],
        "skipped": [],
        "backed_up": [],
        "cache_invalidated": [],
        "cache_cleared": [],
    }


async def _get_file_infos(
    local_path: t.Any,
    storage: t.Any,
    storage_bucket: str,
    storage_path: str,
) -> tuple[dict[str, t.Any], dict[str, t.Any]]:
    local_info = await get_file_info(Path(local_path))
    remote_info = await _get_storage_file_info(storage, storage_bucket, storage_path)
    return local_info, remote_info


async def _should_sync_file(
    local_info: dict[str, t.Any],
    remote_info: dict[str, t.Any],
    strategy: SyncStrategy,
    storage_path: str,
    result: dict[str, t.Any],
) -> bool:
    sync_needed, reason = should_sync(local_info, remote_info, strategy.direction)
    if not sync_needed:
        result["skipped"].append(f"{storage_path} ({reason})")
        return False

    debug(f"Syncing static file {storage_path}: {reason}")
    return True


async def _execute_sync_operation(
    local_path: t.Any,
    storage: t.Any,
    cache: t.Any,
    storage_bucket: str,
    storage_path: str,
    local_info: dict[str, t.Any],
    remote_info: dict[str, t.Any],
    strategy: SyncStrategy,
    mime_type: str,
    is_cacheable: bool,
    result: dict[str, t.Any],
) -> None:
    if _should_pull_static(strategy, local_info, remote_info):
        await _pull_static(
            local_path,
            storage,
            cache,
            storage_bucket,
            storage_path,
            strategy,
            is_cacheable,
            result,
        )
    elif _should_push_static(strategy, local_info, remote_info):
        await _push_static(
            local_path,
            storage,
            cache,
            storage_bucket,
            storage_path,
            strategy,
            mime_type,
            is_cacheable,
            result,
        )
    elif _has_bidirectional_conflict(strategy, local_info, remote_info):
        await _handle_static_conflict(
            local_path,
            storage,
            cache,
            storage_bucket,
            storage_path,
            local_info,
            remote_info,
            strategy,
            mime_type,
            is_cacheable,
            result,
        )


def _should_pull_static(
    strategy: SyncStrategy,
    local_info: dict[str, t.Any],
    remote_info: dict[str, t.Any],
) -> bool:
    return strategy.direction == SyncDirection.PULL or (
        strategy.direction == SyncDirection.BIDIRECTIONAL
        and remote_info["exists"]
        and (not local_info["exists"] or remote_info["mtime"] > local_info["mtime"])
    )


def _should_push_static(
    strategy: SyncStrategy,
    local_info: dict[str, t.Any],
    remote_info: dict[str, t.Any],
) -> bool:
    return strategy.direction == SyncDirection.PUSH or (
        strategy.direction == SyncDirection.BIDIRECTIONAL
        and local_info["exists"]
        and (not remote_info["exists"] or local_info["mtime"] > remote_info["mtime"])
    )


def _has_bidirectional_conflict(
    strategy: SyncStrategy,
    local_info: dict[str, t.Any],
    remote_info: dict[str, t.Any],
) -> bool:
    return (
        strategy.direction == SyncDirection.BIDIRECTIONAL
        and local_info["exists"]
        and remote_info["exists"]
    )


async def _get_storage_file_info(
    storage: t.Any,
    bucket: str,
    file_path: str,
) -> dict[str, t.Any]:
    try:
        bucket_obj = getattr(storage, bucket, None)

        if not bucket_obj:
            await storage._create_bucket(bucket)
            bucket_obj = getattr(storage, bucket)

        exists = await bucket_obj.exists(file_path)

        if not exists:
            return {
                "exists": False,
                "size": 0,
                "mtime": 0,
                "content_hash": None,
            }

        content = await bucket_obj.read(file_path)
        metadata = await bucket_obj.stat(file_path)

        import hashlib

        content_hash = hashlib.blake2b(content).hexdigest()

        return {
            "exists": True,
            "size": len(content),
            "mtime": metadata.get("mtime", 0),
            "content_hash": content_hash,
            "content": content,
        }

    except Exception as e:
        debug(f"Error getting storage file info for {file_path}: {e}")
        return {
            "exists": False,
            "size": 0,
            "mtime": 0,
            "content_hash": None,
            "error": str(e),
        }


async def _pull_static(
    local_path: AsyncPath,
    storage: t.Any,
    cache: t.Any,
    bucket: str,
    storage_path: str,
    strategy: SyncStrategy,
    is_cacheable: bool,
    result: dict[str, t.Any],
) -> None:
    try:
        bucket_obj = getattr(storage, bucket)

        if strategy.dry_run:
            debug(f"DRY RUN: Would pull {storage_path} to {local_path}")
            result["synced"].append(f"PULL(dry-run): {storage_path}")
            return

        if await local_path.exists() and strategy.backup_on_conflict:
            backup_path = await create_backup(Path(local_path))
            result["backed_up"].append(str(backup_path))

        content = await bucket_obj.read(storage_path)

        await local_path.parent.mkdir(parents=True, exist_ok=True)
        await local_path.write_bytes(content)

        result["synced"].append(f"PULL: {storage_path}")
        debug(f"Pulled static file from storage: {storage_path}")

        if is_cacheable and cache:
            await _cache_static_file(cache, storage_path, content, result)

    except Exception as e:
        result["errors"].append(e)
        debug(f"Error pulling static file {storage_path}: {e}")


async def _push_static(
    local_path: AsyncPath,
    storage: t.Any,
    cache: t.Any,
    bucket: str,
    storage_path: str,
    strategy: SyncStrategy,
    mime_type: str,
    is_cacheable: bool,
    result: dict[str, t.Any],
) -> None:
    try:
        bucket_obj = getattr(storage, bucket)

        if strategy.dry_run:
            debug(f"DRY RUN: Would push {local_path} to {storage_path}")
            result["synced"].append(f"PUSH(dry-run): {storage_path}")
            return

        content = await local_path.read_bytes()

        metadata = {"content_type": mime_type}
        await bucket_obj.write(storage_path, content, metadata=metadata)

        result["synced"].append(f"PUSH: {storage_path}")
        debug(f"Pushed static file to storage: {storage_path} (MIME: {mime_type})")

        if is_cacheable and cache:
            await _cache_static_file(cache, storage_path, content, result)

    except Exception as e:
        result["errors"].append(e)
        debug(f"Error pushing static file {storage_path}: {e}")


async def _handle_static_conflict(
    local_path: AsyncPath,
    storage: t.Any,
    cache: t.Any,
    bucket: str,
    storage_path: str,
    local_info: dict[str, t.Any],
    remote_info: dict[str, t.Any],
    strategy: SyncStrategy,
    mime_type: str,
    is_cacheable: bool,
    result: dict[str, t.Any],
) -> None:
    try:
        if strategy.conflict_strategy == ConflictStrategy.MANUAL:
            result["conflicts"].append(
                {
                    "path": storage_path,
                    "local_mtime": local_info["mtime"],
                    "remote_mtime": remote_info["mtime"],
                    "reason": "manual_resolution_required",
                },
            )
            return

        resolved_content, resolution_reason = await resolve_conflict(
            Path(local_path),
            remote_info["content"],
            local_info["content"],
            strategy.conflict_strategy,
            local_info["mtime"],
            remote_info["mtime"],
        )

        if strategy.dry_run:
            debug(
                f"DRY RUN: Would resolve conflict for {storage_path}: {resolution_reason}",
            )
            result["synced"].append(
                f"CONFLICT(dry-run): {storage_path} - {resolution_reason}",
            )
            return

        if (
            strategy.backup_on_conflict
            or strategy.conflict_strategy == ConflictStrategy.BACKUP_BOTH
        ):
            backup_path = await create_backup(Path(local_path), "conflict")
            result["backed_up"].append(str(backup_path))

        if resolved_content == remote_info["content"]:
            await local_path.write_bytes(resolved_content)
            result["synced"].append(
                f"CONFLICT->REMOTE: {storage_path} - {resolution_reason}",
            )
        else:
            bucket_obj = getattr(storage, bucket)
            metadata = {"content_type": mime_type}
            await bucket_obj.write(storage_path, resolved_content, metadata=metadata)
            result["synced"].append(
                f"CONFLICT->LOCAL: {storage_path} - {resolution_reason}",
            )

        if is_cacheable and cache:
            await _cache_static_file(cache, storage_path, resolved_content, result)

        debug(f"Resolved static conflict: {storage_path} - {resolution_reason}")

    except Exception as e:
        result["errors"].append(e)
        result["conflicts"].append(
            {
                "path": storage_path,
                "error": str(e),
                "reason": "resolution_failed",
            },
        )


async def _cache_static_file(
    cache: t.Any,
    storage_path: str,
    content: bytes,
    result: dict[str, t.Any],
) -> None:
    if not cache:
        return

    try:
        cache_key = f"static:{storage_path}"
        await cache.set(cache_key, content, ttl=86400)
        result["cache_invalidated"].append(cache_key)
        debug(f"Cached static file: {storage_path}")
    except Exception as e:
        debug(f"Error caching static file {storage_path}: {e}")

    pass


async def _validate_cache_dependencies() -> tuple[t.Any, t.Any, dict[str, t.Any]]:
    """Validate and return cache and storage dependencies."""
    from acb.depends import depends

    cache = await depends.get("cache")
    storage = await depends.get("storage")
    result: dict[str, t.Any] = {
        "warmed": [],
        "errors": [],
        "skipped": [],
    }

    if not cache or not storage:
        result["errors"].append(Exception("Cache or storage not available"))
        return None, None, result

    return cache, storage, result


async def _warm_single_static_file(
    static_path: str,
    cache: t.Any,
    storage: t.Any,
    cache_namespace: str,
    result: dict[str, t.Any],
) -> None:
    """Warm cache for a single static file."""
    try:
        if not _is_cacheable_file(AsyncPath(static_path)):
            result["skipped"].append(f"{static_path} (not cacheable)")
            return

        cache_key = f"{cache_namespace}:{static_path}"
        if await cache.exists(cache_key):
            result["skipped"].append(static_path)
            return

        content = await storage.static.read(static_path)
        await cache.set(cache_key, content, ttl=86400)
        result["warmed"].append(static_path)

        debug(f"Warmed cache for static file: {static_path}")

    except Exception as e:
        result["errors"].append(f"{static_path}: {e}")
        debug(f"Error warming cache for static file {static_path}: {e}")


async def warm_static_cache(
    static_paths: list[str] | None = None,
    cache_namespace: str = "static",
) -> dict[str, t.Any]:
    result: dict[str, t.Any] = {
        "warmed": [],
        "errors": [],
        "skipped": [],
    }

    if not static_paths:
        static_paths = [
            "css/main.css",
            "css/app.css",
            "js/main.js",
            "js/app.js",
        ]

    try:
        cache, storage, dep_result = await _validate_cache_dependencies()
        if not cache or not storage:
            return dep_result

        result = dep_result

        for static_path in static_paths:
            await _warm_single_static_file(
                static_path, cache, storage, cache_namespace, result
            )

    except Exception as e:
        result["errors"].append(str(e))
        debug(f"Error in warm_static_cache: {e}")

    return result


async def get_static_sync_status(
    static_path: AsyncPath | None = None,
    storage_bucket: str = "static",
) -> dict[str, t.Any]:
    if static_path is None:
        static_path = AsyncPath("static")

    status: dict[str, t.Any] = {
        "total_static_files": 0,
        "in_sync": 0,
        "out_of_sync": 0,
        "local_only": 0,
        "remote_only": 0,
        "conflicts": 0,
        "details": [],
    }

    try:
        storage = await _get_storage_adapter()
        if not storage:
            status["error"] = "Storage adapter not available"
            return status

        static_files = await _discover_static_files(
            static_path,
            ["*.css", "*.js", "*.png", "*.jpg", "*.jpeg", "*.gif", "*.svg", "*.ico"],
            ["*.tmp", "*.log", ".*"],
        )
        status["total_static_files"] = len(static_files)

        await _process_static_files(static_files, storage, storage_bucket, status)

        status["out_of_sync"] = (
            status["conflicts"] + status["local_only"] + status["remote_only"]
        )

    except Exception as e:
        status["error"] = str(e)
        debug(f"Error getting static sync status: {e}")

    return status


async def _get_storage_adapter() -> t.Any:
    """Get the storage adapter."""
    from acb.depends import depends

    return depends.get("storage")


async def _process_static_files(
    static_files: list[dict[str, t.Any]],
    storage: t.Any,
    storage_bucket: str,
    status: dict[str, t.Any],
) -> None:
    """Process all static files and update status."""
    for static_info in static_files:
        local_info = await get_file_info(Path(static_info["local_path"]))
        remote_info = await _get_storage_file_info(
            storage,
            storage_bucket,
            static_info["storage_path"],
        )

        file_status = _create_file_status(static_info, local_info, remote_info)
        _update_status_counters(local_info, remote_info, file_status, status)
        status["details"].append(file_status)


def _create_file_status(
    static_info: dict[str, t.Any],
    local_info: dict[str, t.Any],
    remote_info: dict[str, t.Any],
) -> dict[str, t.Any]:
    """Create file status dictionary."""
    file_status: dict[str, t.Any] = {
        "path": static_info["storage_path"],
        "mime_type": static_info["mime_type"],
        "local_exists": local_info["exists"],
        "remote_exists": remote_info["exists"],
    }

    # Determine sync status
    if local_info["exists"] and remote_info["exists"]:
        if local_info["content_hash"] == remote_info["content_hash"]:
            file_status["status"] = "in_sync"
        else:
            file_status["status"] = "conflict"
            file_status["local_mtime"] = local_info["mtime"]
            file_status["remote_mtime"] = remote_info["mtime"]
    elif local_info["exists"]:
        file_status["status"] = "local_only"
    elif remote_info["exists"]:
        file_status["status"] = "remote_only"
    else:
        file_status["status"] = "missing"

    return file_status


def _update_status_counters(
    local_info: dict[str, t.Any],
    remote_info: dict[str, t.Any],
    file_status: dict[str, t.Any],
    status: dict[str, t.Any],
) -> None:
    """Update status counters based on file status."""
    if local_info["exists"] and remote_info["exists"]:
        if local_info["content_hash"] == remote_info["content_hash"]:
            status["in_sync"] += 1
        else:
            status["conflicts"] += 1
    elif local_info["exists"]:
        status["local_only"] += 1
    elif remote_info["exists"]:
        status["remote_only"] += 1


async def backup_static_files(
    static_path: AsyncPath | None = None,
    backup_suffix: str | None = None,
) -> dict[str, t.Any]:
    static_path = static_path or AsyncPath("static")
    backup_suffix = backup_suffix or _generate_backup_suffix()

    result = _create_backup_result()

    try:
        if not await static_path.exists():
            result["errors"].append(f"Static path does not exist: {static_path}")
            return result

        await _backup_static_files_with_patterns(static_path, backup_suffix, result)

    except Exception as e:
        result["errors"].append(str(e))
        debug(f"Error in backup_static_files: {e}")

    return result


def _generate_backup_suffix() -> str:
    import time

    timestamp = int(time.time())
    return f"backup_{timestamp}"


def _create_backup_result() -> dict[str, t.Any]:
    return {
        "backed_up": [],
        "errors": [],
        "skipped": [],
    }


async def _backup_static_files_with_patterns(
    static_path: AsyncPath,
    backup_suffix: str,
    result: dict[str, t.Any],
) -> None:
    patterns = [
        "*.css",
        "*.js",
        "*.png",
        "*.jpg",
        "*.jpeg",
        "*.gif",
        "*.svg",
        "*.ico",
        "*.woff",
        "*.woff2",
        "*.ttf",
        "*.eot",
        "*.otf",
        "*.webp",
        "*.avif",
    ]

    for pattern in patterns:
        await _backup_files_with_pattern(static_path, pattern, backup_suffix, result)


async def _backup_files_with_pattern(
    static_path: AsyncPath,
    pattern: str,
    backup_suffix: str,
    result: dict[str, t.Any],
) -> None:
    async for file_path in static_path.rglob(pattern):
        if await file_path.is_file():
            await _backup_single_file(file_path, backup_suffix, result)


async def _backup_single_file(
    file_path: AsyncPath,
    backup_suffix: str,
    result: dict[str, t.Any],
) -> None:
    try:
        backup_path = await create_backup(Path(file_path), backup_suffix)
        result["backed_up"].append(str(backup_path))
    except Exception as e:
        result["errors"].append(f"{file_path}: {e}")
