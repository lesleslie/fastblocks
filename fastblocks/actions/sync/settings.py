"""Settings file synchronization between filesystem and cloud storage."""

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


class SettingsSyncResult(SyncResult):
    def __init__(
        self,
        *,
        config_reloaded: list[str] | None = None,
        adapters_affected: list[str] | None = None,
        **kwargs: t.Any,
    ) -> None:
        super().__init__(**kwargs)
        self.config_reloaded = config_reloaded if config_reloaded is not None else []
        self.adapters_affected = (
            adapters_affected if adapters_affected is not None else []
        )


async def sync_settings(
    *,
    settings_path: AsyncPath | None = None,
    adapter_names: list[str] | None = None,
    strategy: SyncStrategy | None = None,
    storage_bucket: str = "settings",
    reload_config: bool = True,
) -> SettingsSyncResult:
    config = _prepare_settings_sync_config(settings_path, strategy)
    result = SettingsSyncResult()

    storage = await _initialize_settings_storage(result)
    if not storage:
        return result

    settings_files = await _discover_settings_files(
        config["settings_path"],
        adapter_names,
    )
    if not settings_files:
        debug("No settings files found to sync")
        return result

    debug(f"Found {len(settings_files)} settings files to sync")

    await _sync_settings_files(
        settings_files,
        storage,
        config["strategy"],
        storage_bucket,
        result,
    )

    await _handle_config_reload(reload_config, result)

    debug(
        f"Settings sync completed: {len(result.synced_items)} synced, {len(result.conflicts)} conflicts",
    )

    return result


def _prepare_settings_sync_config(
    settings_path: AsyncPath | None,
    strategy: SyncStrategy | None,
) -> dict[str, t.Any]:
    return {
        "settings_path": settings_path or AsyncPath("settings"),
        "strategy": strategy or SyncStrategy(),
    }


async def _initialize_settings_storage(result: SettingsSyncResult) -> t.Any | None:
    try:
        from acb.depends import depends

        storage = depends.get("storage")
        if not storage:
            result.errors.append(Exception("Storage adapter not available"))
            return None

        return storage
    except Exception as e:
        result.errors.append(e)
        return None


async def _sync_settings_files(
    settings_files: list[dict[str, t.Any]],
    storage: t.Any,
    strategy: SyncStrategy,
    storage_bucket: str,
    result: SettingsSyncResult,
) -> None:
    for settings_info in settings_files:
        try:
            file_result = await _sync_single_settings_file(
                settings_info,
                storage,
                strategy,
                storage_bucket,
            )
            _accumulate_settings_sync_results(file_result, result)

        except Exception as e:
            result.errors.append(e)
            debug(f"Error syncing settings {settings_info['relative_path']}: {e}")


def _accumulate_settings_sync_results(
    file_result: dict[str, t.Any],
    result: SettingsSyncResult,
) -> None:
    if file_result.get("synced"):
        result.synced_items.extend(file_result["synced"])
        result.adapters_affected.extend(file_result.get("adapters_affected", []))
    if file_result.get("conflicts"):
        result.conflicts.extend(file_result["conflicts"])
    if file_result.get("errors"):
        result.errors.extend(file_result["errors"])
    if file_result.get("skipped"):
        result.skipped.extend(file_result["skipped"])
    if file_result.get("backed_up"):
        result.backed_up.extend(file_result["backed_up"])


async def _handle_config_reload(
    reload_config: bool,
    result: SettingsSyncResult,
) -> None:
    if reload_config and result.synced_items:
        try:
            await _reload_configuration(result.adapters_affected)
            result.config_reloaded = result.adapters_affected.copy()
        except Exception as e:
            result.errors.append(e)
            debug(f"Error reloading configuration: {e}")


async def _discover_settings_files(
    settings_path: AsyncPath,
    adapter_names: list[str] | None = None,
) -> list[dict[str, t.Any]]:
    settings_files: list[dict[str, t.Any]] = []

    if not await settings_path.exists():
        debug(f"Settings path does not exist: {settings_path}")
        return settings_files

    for pattern in ("*.yml", "*.yaml"):
        await _discover_files_with_pattern(
            settings_path,
            pattern,
            adapter_names,
            settings_files,
        )

    return settings_files


async def _discover_files_with_pattern(
    settings_path: AsyncPath,
    pattern: str,
    adapter_names: list[str] | None,
    settings_files: list[dict[str, t.Any]],
) -> None:
    async for file_path in settings_path.rglob(pattern):
        if await file_path.is_file():
            await _process_settings_file(
                file_path,
                settings_path,
                adapter_names,
                settings_files,
            )


async def _process_settings_file(
    file_path: AsyncPath,
    settings_path: AsyncPath,
    adapter_names: list[str] | None,
    settings_files: list[dict[str, t.Any]],
) -> None:
    adapter_name = file_path.stem

    if adapter_names and adapter_name not in adapter_names:
        return

    try:
        rel_path = file_path.relative_to(settings_path)
        settings_files.append(
            {
                "local_path": file_path,
                "relative_path": rel_path,
                "storage_path": str(rel_path),
                "adapter_name": adapter_name,
            },
        )
    except ValueError:
        debug(f"Could not get relative path for {file_path}")


async def _sync_single_settings_file(
    settings_info: dict[str, t.Any],
    storage: t.Any,
    strategy: SyncStrategy,
    storage_bucket: str,
) -> dict[str, t.Any]:
    local_path = settings_info["local_path"]
    storage_path = settings_info["storage_path"]
    adapter_name = settings_info["adapter_name"]

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

        if not await _validate_local_yaml(local_info, storage_path, result):
            return result

        await _execute_sync_operation(
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
            result["adapters_affected"].append(adapter_name)

    except Exception as e:
        result["errors"].append(e)
        debug(f"Error in _sync_single_settings_file for {storage_path}: {e}")

    return result


def _create_sync_result() -> dict[str, t.Any]:
    return {
        "synced": [],
        "conflicts": [],
        "errors": [],
        "skipped": [],
        "backed_up": [],
        "adapters_affected": [],
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

    debug(f"Syncing settings {storage_path}: {reason}")
    return True


async def _validate_local_yaml(
    local_info: dict[str, t.Any],
    storage_path: str,
    result: dict[str, t.Any],
) -> bool:
    if local_info["exists"]:
        try:
            await _validate_yaml_content(local_info["content"])
        except Exception as e:
            result["errors"].append(f"Invalid YAML in {storage_path}: {e}")
            return False
    return True


async def _execute_sync_operation(
    local_path: t.Any,
    storage: t.Any,
    storage_bucket: str,
    storage_path: str,
    local_info: dict[str, t.Any],
    remote_info: dict[str, t.Any],
    strategy: SyncStrategy,
    result: dict[str, t.Any],
) -> None:
    if _should_pull_settings(strategy, local_info, remote_info):
        await _pull_settings(
            local_path,
            storage,
            storage_bucket,
            storage_path,
            strategy,
            result,
        )
    elif _should_push_settings(strategy, local_info, remote_info):
        await _push_settings(
            local_path,
            storage,
            storage_bucket,
            storage_path,
            strategy,
            result,
        )
    elif _has_bidirectional_conflict(strategy, local_info, remote_info):
        await _handle_settings_conflict(
            local_path,
            storage,
            storage_bucket,
            storage_path,
            local_info,
            remote_info,
            strategy,
            result,
        )


def _should_pull_settings(
    strategy: SyncStrategy,
    local_info: dict[str, t.Any],
    remote_info: dict[str, t.Any],
) -> bool:
    return strategy.direction == SyncDirection.PULL or (
        strategy.direction == SyncDirection.BIDIRECTIONAL
        and remote_info["exists"]
        and (not local_info["exists"] or remote_info["mtime"] > local_info["mtime"])
    )


def _should_push_settings(
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


async def _validate_yaml_content(content: bytes) -> None:
    try:
        import yaml

        yaml.safe_load(content.decode())
    except Exception as e:
        msg = f"Invalid YAML content: {e}"
        raise ValueError(msg)


async def _pull_settings(
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

        await _validate_yaml_content(content)

        await local_path.parent.mkdir(parents=True, exist_ok=True)

        await local_path.write_bytes(content)

        result["synced"].append(f"PULL: {storage_path}")
        debug(f"Pulled settings from storage: {storage_path}")

    except Exception as e:
        result["errors"].append(e)
        debug(f"Error pulling settings {storage_path}: {e}")


async def _push_settings(
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
        await _validate_yaml_content(content)

        await bucket_obj.write(storage_path, content)

        result["synced"].append(f"PUSH: {storage_path}")
        debug(f"Pushed settings to storage: {storage_path}")

    except Exception as e:
        result["errors"].append(e)
        debug(f"Error pushing settings {storage_path}: {e}")


async def _handle_settings_conflict(
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

        try:
            await _validate_yaml_content(local_info["content"])
            await _validate_yaml_content(remote_info["content"])
        except Exception as e:
            result["errors"].append(f"Invalid YAML during conflict resolution: {e}")
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

        debug(f"Resolved settings conflict: {storage_path} - {resolution_reason}")

    except Exception as e:
        result["errors"].append(e)
        result["conflicts"].append(
            {
                "path": storage_path,
                "error": str(e),
                "reason": "resolution_failed",
            },
        )


async def _reload_configuration(adapter_names: list[str]) -> None:
    try:
        from acb.config import reload_config  # type: ignore[attr-defined]
        from acb.depends import depends

        config = await reload_config()
        depends.set("config", config)
        debug(f"Reloaded configuration for adapters: {adapter_names}")
    except Exception as e:
        debug(f"Error reloading configuration: {e}")
        raise


async def backup_settings(
    settings_path: AsyncPath | None = None,
    backup_suffix: str | None = None,
) -> dict[str, t.Any]:
    settings_path = settings_path or AsyncPath("settings")
    backup_suffix = backup_suffix or _generate_backup_suffix()

    result = _create_backup_result()

    try:
        if not await settings_path.exists():
            result["errors"].append(f"Settings path does not exist: {settings_path}")
            return result

        await _backup_files_with_patterns(settings_path, backup_suffix, result)

    except Exception as e:
        result["errors"].append(str(e))
        debug(f"Error in backup_settings: {e}")

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


async def _backup_files_with_patterns(
    settings_path: AsyncPath,
    backup_suffix: str,
    result: dict[str, t.Any],
) -> None:
    patterns = ["*.yml", "*.yaml"]

    for pattern in patterns:
        await _backup_files_with_pattern(settings_path, pattern, backup_suffix, result)


async def _backup_files_with_pattern(
    settings_path: AsyncPath,
    pattern: str,
    backup_suffix: str,
    result: dict[str, t.Any],
) -> None:
    async for file_path in settings_path.rglob(pattern):
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


async def get_settings_sync_status(
    settings_path: AsyncPath | None = None,
    storage_bucket: str = "settings",
) -> dict[str, t.Any]:
    if settings_path is None:
        settings_path = AsyncPath("settings")

    status: dict[str, t.Any] = {
        "total_settings": 0,
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

        settings_files = await _discover_settings_files(settings_path)
        status["total_settings"] = len(settings_files)

        for settings_info in settings_files:
            local_info = await get_file_info(Path(settings_info["local_path"]))
            remote_info = await _get_storage_file_info(
                storage,
                storage_bucket,
                settings_info["storage_path"],
            )

            file_status: dict[str, t.Any] = {
                "path": settings_info["storage_path"],
                "adapter": settings_info["adapter_name"],
                "local_exists": local_info["exists"],
                "remote_exists": remote_info["exists"],
            }

            if local_info["exists"] and remote_info["exists"]:
                if local_info["content_hash"] == remote_info["content_hash"]:
                    file_status["status"] = "in_sync"
                    status["in_sync"] += 1
                else:
                    file_status["status"] = "conflict"
                    file_status["local_mtime"] = local_info["mtime"]
                    file_status["remote_mtime"] = remote_info["mtime"]
                    status["conflicts"] += 1
            elif local_info["exists"]:
                file_status["status"] = "local_only"
                status["local_only"] += 1
            elif remote_info["exists"]:
                file_status["status"] = "remote_only"
                status["remote_only"] += 1
            else:
                file_status["status"] = "missing"

            status["details"].append(file_status)

        status["out_of_sync"] = (
            status["conflicts"] + status["local_only"] + status["remote_only"]
        )

    except Exception as e:
        status["error"] = str(e)
        debug(f"Error getting settings sync status: {e}")

    return status


async def validate_all_settings(
    settings_path: AsyncPath | None = None,
) -> dict[str, t.Any]:
    if settings_path is None:
        settings_path = AsyncPath("settings")

    result: dict[str, t.Any] = {
        "valid": [],
        "invalid": [],
        "missing": [],
        "total_checked": 0,
    }

    try:
        settings_files = await _discover_settings_files(settings_path)
        result["total_checked"] = len(settings_files)

        for settings_info in settings_files:
            file_path = settings_info["local_path"]

            if not await file_path.exists():
                result["missing"].append(str(file_path))
                continue

            try:
                content = await file_path.read_bytes()
                await _validate_yaml_content(content)
                result["valid"].append(str(file_path))
            except Exception as e:
                result["invalid"].append(
                    {
                        "path": str(file_path),
                        "error": str(e),
                    },
                )

    except Exception as e:
        result["error"] = str(e)
        debug(f"Error validating settings: {e}")

    return result
