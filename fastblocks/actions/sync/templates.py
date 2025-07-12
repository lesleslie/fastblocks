"""Template synchronization between filesystem, storage, and cache layers."""

import typing as t
from pathlib import Path

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


class TemplateSyncResult(SyncResult):
    def __init__(
        self,
        *,
        cache_invalidated: list[str] | None = None,
        bytecode_cleared: list[str] | None = None,
        **kwargs: t.Any,
    ) -> None:
        super().__init__(**kwargs)
        self.cache_invalidated = (
            cache_invalidated if cache_invalidated is not None else []
        )
        self.bytecode_cleared = bytecode_cleared if bytecode_cleared is not None else []
        self._direction: str | None = None
        self._conflict_strategy: str | None = None
        self._filters: dict[str, t.Any] | None = None
        self._dry_run: bool = False

    @property
    def synchronized_files(self) -> list[str]:
        return self.synced_items

    @property
    def sync_status(self) -> str:
        if self.has_errors:
            return "error"
        elif self.has_conflicts:
            return "conflict"
        elif self.synced_items:
            return "success"
        return "no_changes"

    @property
    def conflicts_resolved(self) -> list[dict[str, t.Any]]:
        return self.conflicts

    @property
    def direction(self) -> str | None:
        return getattr(self, "_direction", None)

    @property
    def conflict_strategy(self) -> str | None:
        return getattr(self, "_conflict_strategy", None)

    @property
    def conflicts_requiring_resolution(self) -> list[dict[str, t.Any]]:
        return self.conflicts

    @property
    def filtered_files(self) -> list[str]:
        return []

    @property
    def dry_run(self) -> bool:
        return getattr(self, "_dry_run", False)

    @property
    def would_sync_files(self) -> list[str]:
        if self.dry_run:
            return [item for item in self.synced_items if "dry-run" in item]
        return []

    @property
    def would_resolve_conflicts(self) -> list[dict[str, t.Any]]:
        if self.dry_run:
            return [conf for conf in self.conflicts if "dry-run" in str(conf)]
        return []


async def sync_templates(
    *,
    template_paths: list[AsyncPath] | None = None,
    patterns: list[str] | None = None,
    strategy: SyncStrategy | None = None,
    storage_bucket: str = "templates",
    direction: str | None = None,
    conflict_strategy: str | None = None,
    filters: dict[str, t.Any] | None = None,
    dry_run: bool = False,
) -> TemplateSyncResult:
    if filters and "include_patterns" in filters:
        patterns = filters["include_patterns"]

    config = _prepare_sync_config(
        template_paths, patterns, strategy, direction, conflict_strategy, dry_run
    )
    result = TemplateSyncResult()
    result._direction = config.get("direction")
    result._conflict_strategy = conflict_strategy
    result._filters = filters
    result._dry_run = dry_run

    try:
        adapters = await _initialize_adapters(result)
    except Exception as e:
        result.errors.append(e)
        debug(f"Error initializing adapters: {e}")
        return result

    if not adapters:
        return result

    template_files = await _discover_template_files(
        config["template_paths"],
        config["patterns"],
    )
    debug(f"Found {len(template_files)} template files to sync")

    await _sync_template_files(
        template_files,
        adapters,
        config["strategy"],
        storage_bucket,
        result,
    )

    debug(
        f"Template sync completed: {len(result.synced_items)} synced, {len(result.conflicts)} conflicts",
    )
    return result


def _prepare_sync_config(
    template_paths: list[AsyncPath] | None,
    patterns: list[str] | None,
    strategy: SyncStrategy | None,
    direction: str | None = None,
    conflict_strategy: str | None = None,
    dry_run: bool = False,
) -> dict[str, t.Any]:
    direction_mapping = {
        "cloud_to_local": SyncDirection.PULL,
        "local_to_cloud": SyncDirection.PUSH,
        "bidirectional": SyncDirection.BIDIRECTIONAL,
    }

    conflict_mapping = {
        "local_wins": ConflictStrategy.LOCAL_WINS,
        "remote_wins": ConflictStrategy.REMOTE_WINS,
        "cloud_wins": ConflictStrategy.REMOTE_WINS,
        "newest_wins": ConflictStrategy.NEWEST_WINS,
        "manual": ConflictStrategy.MANUAL,
        "backup_both": ConflictStrategy.BACKUP_BOTH,
    }

    if strategy is None:
        sync_direction = SyncDirection.BIDIRECTIONAL
        if direction and direction in direction_mapping:
            sync_direction = direction_mapping[direction]

        sync_conflict = ConflictStrategy.NEWEST_WINS
        if conflict_strategy and conflict_strategy in conflict_mapping:
            sync_conflict = conflict_mapping[conflict_strategy]

        strategy = SyncStrategy(
            direction=sync_direction, conflict_strategy=sync_conflict, dry_run=dry_run
        )

    return {
        "template_paths": template_paths or [AsyncPath("templates")],
        "patterns": patterns or ["*.html", "*.jinja2", "*.j2", "*.txt"],
        "strategy": strategy,
        "direction": direction,
    }


async def _initialize_adapters(result: TemplateSyncResult) -> dict[str, t.Any] | None:
    try:
        from acb.depends import depends

        storage = depends.get("storage")
        cache = depends.get("cache")
        if not storage:
            result.errors.append(Exception("Storage adapter not available"))
            return None

        return {"storage": storage, "cache": cache}
    except Exception as e:
        result.errors.append(e)
        return None


async def _discover_template_files(
    template_paths: list[AsyncPath],
    patterns: list[str],
) -> list[dict[str, t.Any]]:
    template_files = []

    for base_path in template_paths:
        if not await base_path.exists():
            debug(f"Template path does not exist: {base_path}")
            continue

        files = await _scan_path_for_templates(base_path, patterns)
        template_files.extend(files)

    return template_files


async def _scan_path_for_templates(
    base_path: AsyncPath,
    patterns: list[str],
) -> list[dict[str, t.Any]]:
    files = []

    for pattern in patterns:
        async for file_path in base_path.rglob(pattern):
            if await file_path.is_file():
                try:
                    rel_path = file_path.relative_to(base_path)
                    files.append(
                        {
                            "local_path": file_path,
                            "relative_path": rel_path,
                            "storage_path": str(rel_path),
                        },
                    )
                except ValueError:
                    debug(f"Could not get relative path for {file_path}")

    return files


async def _sync_template_files(
    template_files: list[dict[str, t.Any]],
    adapters: dict[str, t.Any],
    strategy: SyncStrategy,
    storage_bucket: str,
    result: TemplateSyncResult,
) -> None:
    for template_info in template_files:
        try:
            file_result = await _sync_single_template(
                template_info,
                adapters["storage"],
                adapters["cache"],
                strategy,
                storage_bucket,
            )
            _accumulate_sync_results(file_result, result)

        except Exception as e:
            result.errors.append(e)
            debug(f"Error syncing template {template_info['relative_path']}: {e}")


def _accumulate_sync_results(
    file_result: dict[str, t.Any],
    result: TemplateSyncResult,
) -> None:
    for key in (
        "synced",
        "conflicts",
        "errors",
        "skipped",
        "backed_up",
        "cache_invalidated",
        "bytecode_cleared",
    ):
        if file_result.get(key):
            getattr(result, f"{key}_items" if key == "synced" else key).extend(
                file_result[key],
            )


async def _sync_single_template(
    template_info: dict[str, t.Any],
    storage: t.Any,
    cache: t.Any,
    strategy: SyncStrategy,
    storage_bucket: str,
) -> dict[str, t.Any]:
    local_path = template_info["local_path"]
    storage_path = template_info["storage_path"]
    relative_path = template_info["relative_path"]

    result: dict[str, t.Any] = {
        "synced": [],
        "conflicts": [],
        "errors": [],
        "skipped": [],
        "backed_up": [],
        "cache_invalidated": [],
        "bytecode_cleared": [],
    }

    try:
        local_info = await get_file_info(Path(local_path))

        remote_info = await _get_storage_file_info(
            storage,
            storage_bucket,
            storage_path,
        )

        sync_needed, reason = should_sync(local_info, remote_info, strategy.direction)

        if not sync_needed:
            result["skipped"].append(f"{relative_path} ({reason})")
            return result

        debug(f"Syncing template {relative_path}: {reason}")

        if strategy.direction == SyncDirection.PULL or (
            strategy.direction == SyncDirection.BIDIRECTIONAL
            and remote_info["exists"]
            and (not local_info["exists"] or remote_info["mtime"] > local_info["mtime"])
        ):
            await _pull_template(
                local_path,
                storage,
                storage_bucket,
                storage_path,
                strategy,
                result,
            )

        elif strategy.direction == SyncDirection.PUSH or (
            strategy.direction == SyncDirection.BIDIRECTIONAL
            and local_info["exists"]
            and (
                not remote_info["exists"] or local_info["mtime"] > remote_info["mtime"]
            )
        ):
            await _push_template(
                local_path,
                storage,
                storage_bucket,
                storage_path,
                strategy,
                result,
            )

        elif (
            strategy.direction == SyncDirection.BIDIRECTIONAL
            and local_info["exists"]
            and remote_info["exists"]
        ):
            await _handle_template_conflict(
                local_path,
                storage,
                storage_bucket,
                storage_path,
                local_info,
                remote_info,
                strategy,
                result,
            )

        if result["synced"]:
            await _invalidate_template_cache(cache, str(relative_path), result)

    except Exception as e:
        result["errors"].append(e)
        debug(f"Error in _sync_single_template for {relative_path}: {e}")

    return result


async def _get_storage_file_info(
    storage: t.Any,
    bucket: str,
    file_path: str,
) -> dict[str, t.Any]:
    try:
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


async def _pull_template(
    local_path: AsyncPath,
    storage: t.Any,
    bucket: str,
    storage_path: str,
    strategy: SyncStrategy,
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
        debug(f"Pulled template from storage: {storage_path}")

    except Exception as e:
        result["errors"].append(e)
        debug(f"Error pulling template {storage_path}: {e}")


async def _push_template(
    local_path: AsyncPath,
    storage: t.Any,
    bucket: str,
    storage_path: str,
    strategy: SyncStrategy,
    result: dict[str, t.Any],
) -> None:
    try:
        bucket_obj = getattr(storage, bucket)

        if strategy.dry_run:
            debug(f"DRY RUN: Would push {local_path} to {storage_path}")
            result["synced"].append(f"PUSH(dry-run): {storage_path}")
            return

        content = await local_path.read_bytes()

        await bucket_obj.write(storage_path, content)

        result["synced"].append(f"PUSH: {storage_path}")
        debug(f"Pushed template to storage: {storage_path}")

    except Exception as e:
        result["errors"].append(e)
        debug(f"Error pushing template {storage_path}: {e}")


async def _handle_template_conflict(
    local_path: AsyncPath,
    storage: t.Any,
    bucket: str,
    storage_path: str,
    local_info: dict[str, t.Any],
    remote_info: dict[str, t.Any],
    strategy: SyncStrategy,
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
            await bucket_obj.write(storage_path, resolved_content)
            result["synced"].append(
                f"CONFLICT->LOCAL: {storage_path} - {resolution_reason}",
            )

        debug(f"Resolved template conflict: {storage_path} - {resolution_reason}")

    except Exception as e:
        result["errors"].append(e)
        result["conflicts"].append(
            {
                "path": storage_path,
                "error": str(e),
                "reason": "resolution_failed",
            },
        )


async def _invalidate_template_cache(
    cache: t.Any,
    template_path: str,
    result: dict[str, t.Any],
) -> None:
    if not cache:
        return

    try:
        template_key = f"template:{template_path}"
        await cache.delete(template_key)
        result["cache_invalidated"].append(template_key)

        bytecode_key = f"bccache:{template_path}"
        await cache.delete(bytecode_key)
        result["bytecode_cleared"].append(bytecode_key)

        await cache.delete_pattern(f"template:*:{template_path}")
        await cache.delete_pattern(f"bccache:*:{template_path}")

        debug(f"Invalidated cache for template: {template_path}")

    except Exception as e:
        debug(f"Error invalidating cache for {template_path}: {e}")


async def warm_template_cache(
    template_paths: list[str] | None = None,
    cache_namespace: str = "templates",
) -> dict[str, t.Any]:
    result: dict[str, t.Any] = {
        "warmed": [],
        "errors": [],
        "skipped": [],
    }

    if not template_paths:
        template_paths = [
            "base.html",
            "index.html",
            "layout.html",
            "404.html",
            "500.html",
        ]

    try:
        from acb.depends import depends

        cache = depends.get("cache")
        storage = depends.get("storage")

        if not cache or not storage:
            result["errors"].append(Exception("Cache or storage not available"))
            return result

        for template_path in template_paths:
            try:
                cache_key = f"{cache_namespace}:{template_path}"
                if await cache.exists(cache_key):
                    result["skipped"].append(template_path)
                    continue

                content = await storage.templates.read(template_path)

                await cache.set(cache_key, content, ttl=86400)
                result["warmed"].append(template_path)

                debug(f"Warmed cache for template: {template_path}")

            except Exception as e:
                result["errors"].append(f"{template_path}: {e}")
                debug(f"Error warming cache for {template_path}: {e}")

    except Exception as e:
        result["errors"].append(str(e))
        debug(f"Error in warm_template_cache: {e}")

    return result


async def get_template_sync_status(
    template_paths: list[AsyncPath] | None = None,
    storage_bucket: str = "templates",
) -> dict[str, t.Any]:
    if template_paths is None:
        template_paths = [AsyncPath("templates")]

    status: dict[str, t.Any] = {
        "total_templates": 0,
        "in_sync": 0,
        "out_of_sync": 0,
        "local_only": 0,
        "remote_only": 0,
        "conflicts": 0,
        "details": [],
    }

    try:
        from acb.depends import depends

        storage = depends.get("storage")

        if not storage:
            status["error"] = "Storage adapter not available"
            return status

        template_files = await _discover_template_files_for_status(template_paths)
        status["total_templates"] = len(template_files)

        await _process_template_files_for_status(
            template_files,
            storage,
            storage_bucket,
            status,
        )

    except Exception as e:
        status["error"] = str(e)
        debug(f"Error getting template sync status: {e}")

    return status


async def _discover_template_files_for_status(
    template_paths: list[AsyncPath],
) -> list[dict[str, t.Any]]:
    template_files = []
    for base_path in template_paths:
        if await base_path.exists():
            async for file_path in base_path.rglob("*.html"):
                if await file_path.is_file():
                    rel_path = file_path.relative_to(base_path)
                    template_files.append(
                        {
                            "local_path": file_path,
                            "storage_path": str(rel_path),
                        },
                    )
    return template_files


async def _process_template_files_for_status(
    template_files: list[dict[str, t.Any]],
    storage: t.Any,
    storage_bucket: str,
    status: dict[str, t.Any],
) -> None:
    for template_info in template_files:
        local_info = await get_file_info(Path(template_info["local_path"]))
        remote_info = await _get_storage_file_info(
            storage,
            storage_bucket,
            template_info["storage_path"],
        )

        file_status = _create_file_status_info(template_info, local_info, remote_info)
        _update_status_counters(local_info, remote_info, file_status, status)

        details_list = status["details"]
        assert isinstance(details_list, list)
        details_list.append(file_status)

    _calculate_out_of_sync_total(status)


def _create_file_status_info(
    template_info: dict[str, t.Any],
    local_info: dict[str, t.Any],
    remote_info: dict[str, t.Any],
) -> dict[str, t.Any]:
    return {
        "path": template_info["storage_path"],
        "local_exists": local_info["exists"],
        "remote_exists": remote_info["exists"],
    }


def _update_status_counters(
    local_info: dict[str, t.Any],
    remote_info: dict[str, t.Any],
    file_status: dict[str, t.Any],
    status: dict[str, t.Any],
) -> None:
    if local_info["exists"] and remote_info["exists"]:
        if local_info["content_hash"] == remote_info["content_hash"]:
            file_status["status"] = "in_sync"
            status["in_sync"] = status["in_sync"] + 1
        else:
            file_status["status"] = "conflict"
            file_status["local_mtime"] = local_info["mtime"]
            file_status["remote_mtime"] = remote_info["mtime"]
            status["conflicts"] = status["conflicts"] + 1
    elif local_info["exists"]:
        file_status["status"] = "local_only"
        status["local_only"] = status["local_only"] + 1
    elif remote_info["exists"]:
        file_status["status"] = "remote_only"
        status["remote_only"] = status["remote_only"] + 1
    else:
        file_status["status"] = "missing"


def _calculate_out_of_sync_total(status: dict[str, t.Any]) -> None:
    conflicts = status["conflicts"]
    local_only = status["local_only"]
    remote_only = status["remote_only"]
    assert isinstance(conflicts, int)
    assert isinstance(local_only, int)
    assert isinstance(remote_only, int)
    status["out_of_sync"] = conflicts + local_only + remote_only
