"""Sync strategies for handling synchronization operations with conflict resolution."""

from __future__ import annotations

import asyncio
import typing as t
from enum import Enum
from pathlib import Path

from oneiric.core.logging import get_logger

_log = get_logger("fastblocks.actions.sync.strategies")


def debug(msg: str) -> None:
    """Log a sync-strategy debug message."""
    _log.debug(msg)


class SyncDirection(Enum):
    PULL = "pull"
    PUSH = "push"
    BIDIRECTIONAL = "bidirectional"


class ConflictStrategy(Enum):
    REMOTE_WINS = "remote_wins"
    LOCAL_WINS = "local_wins"
    NEWEST_WINS = "newest_wins"
    MANUAL = "manual"
    BACKUP_BOTH = "backup_both"


class SyncStrategy:
    def __init__(
        self,
        *,
        direction: SyncDirection = SyncDirection.BIDIRECTIONAL,
        conflict_strategy: ConflictStrategy = ConflictStrategy.NEWEST_WINS,
        dry_run: bool = False,
        backup_on_conflict: bool = True,
        parallel: bool = True,
        max_concurrent: int = 5,
        timeout: float = 30.0,
        retry_attempts: int = 2,
        retry_delay: float = 0.5,
    ) -> None:
        self.direction = direction
        self.conflict_strategy = conflict_strategy
        self.dry_run = dry_run
        self.backup_on_conflict = backup_on_conflict
        self.parallel = parallel
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay


class SyncResult:
    def __init__(
        self,
        *,
        synced_items: list[str] | None = None,
        conflicts: list[dict[str, t.Any]] | None = None,
        errors: list[Exception | str] | None = None,
        skipped: list[str] | None = None,
        backed_up: list[str] | None = None,
        completed: dict[str, bool] | None = None,
        item_errors: dict[str, str] | None = None,
        primary_error: str | None = None,
        cleanup_errors: list[str] | None = None,
    ) -> None:
        self.synced_items = synced_items if synced_items is not None else []
        self.conflicts = conflicts if conflicts is not None else []
        self.errors = errors if errors is not None else []
        self.skipped = skipped if skipped is not None else []
        self.backed_up = backed_up if backed_up is not None else []
        self.completed = completed if completed is not None else {}
        self.item_errors = item_errors if item_errors is not None else {}
        self.primary_error = primary_error
        self.cleanup_errors = cleanup_errors if cleanup_errors is not None else []

    def record_completed(self, item: str) -> None:
        """Record a successfully completed independent sync item."""
        self.completed[item] = True

    def record_item_error(self, item: str, error: Exception) -> None:
        """Record an independent item failure without aborting its batch."""
        self.completed[item] = False
        self.item_errors[item] = str(error)
        self.errors.append(error)

    def record_primary_error(self, error: Exception) -> None:
        """Retain the first transfer or write failure as the primary error."""
        if self.primary_error is None:
            self.primary_error = str(error)
        self.errors.append(error)

    @property
    def total_processed(self) -> int:
        return (
            len(self.synced_items)
            + len(self.conflicts)
            + len(self.errors)
            + len(self.skipped)
        )

    @property
    def success_count(self) -> int:
        return len(self.synced_items)

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0

    @property
    def has_errors(self) -> bool:
        return bool(self.errors or self.item_errors or self.cleanup_errors)

    @property
    def is_success(self) -> bool:
        return not self.has_errors and not self.has_conflicts


async def sync_with_strategy(
    sync_tasks: list[t.Coroutine[t.Any, t.Any, t.Any]],
    strategy: SyncStrategy,
) -> SyncResult:
    result = SyncResult()

    if strategy.parallel and len(sync_tasks) > 1:
        await _execute_parallel_sync(sync_tasks, strategy, result)
    else:
        await _execute_sequential_sync(sync_tasks, strategy, result)

    debug(
        f"Sync completed: {result.success_count} synced, {len(result.conflicts)} conflicts, {len(result.errors)} errors",
    )

    return result


async def _execute_parallel_sync(
    sync_tasks: list[t.Coroutine[t.Any, t.Any, t.Any]],
    strategy: SyncStrategy,
    result: SyncResult,
) -> None:
    semaphore = asyncio.Semaphore(strategy.max_concurrent)

    async def execute_with_semaphore(
        task: t.Coroutine[t.Any, t.Any, t.Any],
    ) -> t.Any:
        async with semaphore:
            return await _execute_with_retry(task, strategy)

    try:
        results = await asyncio.wait_for(
            asyncio.gather(
                *[execute_with_semaphore(task) for task in sync_tasks],
                return_exceptions=True,
            ),
            timeout=strategy.timeout,
        )

        _process_parallel_results(results, result)

    except TimeoutError as e:
        result.errors.append(e)
        debug(f"Sync timeout after {strategy.timeout}s")


def _process_parallel_results(results: list[t.Any], result: SyncResult) -> None:
    for task_result in results:
        if isinstance(task_result, Exception):
            result.errors.append(task_result)
        elif isinstance(task_result, dict):
            _merge_sync_result(result, task_result)


async def _execute_sequential_sync(
    sync_tasks: list[t.Coroutine[t.Any, t.Any, t.Any]],
    strategy: SyncStrategy,
    result: SyncResult,
) -> None:
    for task in sync_tasks:
        try:
            task_result = await asyncio.wait_for(
                _execute_with_retry(task, strategy),
                timeout=strategy.timeout,
            )

            if isinstance(task_result, dict):
                _merge_sync_result(result, task_result)

        # Sync tasks may execute pluggable storage/cache implementations.
        except Exception as e:  # noqa: BLE001, RUF100
            result.errors.append(e)
            _log.exception("Sync item failed: %s", task)


async def _execute_with_retry(
    task: t.Coroutine[t.Any, t.Any, t.Any],
    strategy: SyncStrategy,
) -> t.Any:
    for attempt in range(strategy.retry_attempts + 1):
        try:
            return await task
        except Exception as e:
            if attempt == strategy.retry_attempts:
                raise

            debug(f"Sync retry attempt {attempt + 1} after error: {e}")
            await asyncio.sleep(strategy.retry_delay * (attempt + 1))

    msg = "Should not reach here"
    raise RuntimeError(msg)


def _merge_sync_result(main_result: SyncResult, task_result: dict[str, t.Any]) -> None:
    main_result.synced_items.extend(task_result.get("synced", []))
    main_result.conflicts.extend(task_result.get("conflicts", []))
    main_result.errors.extend(task_result.get("errors", []))
    main_result.skipped.extend(task_result.get("skipped", []))
    main_result.backed_up.extend(task_result.get("backed_up", []))


async def resolve_conflict(
    local_path: Path,
    remote_content: bytes,
    local_content: bytes,
    strategy: ConflictStrategy,
    local_mtime: float | None = None,
    remote_mtime: float | None = None,
) -> tuple[bytes, str]:
    if strategy == ConflictStrategy.REMOTE_WINS:
        return remote_content, "remote_wins"

    if strategy == ConflictStrategy.LOCAL_WINS:
        return local_content, "local_wins"

    if strategy == ConflictStrategy.NEWEST_WINS:
        if local_mtime and remote_mtime:
            if remote_mtime > local_mtime:
                return remote_content, f"remote_newer({remote_mtime} > {local_mtime})"
            return local_content, f"local_newer({local_mtime} >= {remote_mtime})"
        return remote_content, "newest_wins_fallback_remote"

    if strategy == ConflictStrategy.BACKUP_BOTH:
        return remote_content, "backup_both"

    if strategy == ConflictStrategy.MANUAL:
        msg = f"Manual conflict resolution required for {local_path}"
        raise ValueError(msg)

    msg = f"Unknown conflict strategy: {strategy}"
    raise ValueError(msg)


async def create_backup(file_path: Path, suffix: str | None = None) -> Path:
    if suffix is None:
        import time

        timestamp = int(time.time())
        suffix = f"backup_{timestamp}"
    backup_path = file_path.with_suffix(f"{file_path.suffix}.{suffix}")
    try:
        if file_path.exists():
            import shutil

            shutil.copy2(file_path, backup_path)
            debug(f"Created backup: {backup_path}")

        return backup_path
    except OSError:
        _log.exception("Error creating backup for %s", file_path)
        raise


def compare_content(
    content1: bytes,
    content2: bytes,
    use_hash: bool = True,
) -> bool:
    if len(content1) != len(content2):
        return False

    if use_hash and len(content1) > 1024:
        import hashlib

        hash1 = hashlib.blake2b(content1).hexdigest()
        hash2 = hashlib.blake2b(content2).hexdigest()
        return hash1 == hash2

    return content1 == content2


async def get_file_info(file_path: Path) -> dict[str, t.Any]:
    try:
        if not file_path.exists():
            return {
                "exists": False,
                "size": 0,
                "mtime": 0,
                "content_hash": None,
            }
        stat = file_path.stat()
        content = file_path.read_bytes()
        import hashlib

        content_hash = hashlib.blake2b(content).hexdigest()

        return {
            "exists": True,
            "size": stat.st_size,
            "mtime": stat.st_mtime,
            "content_hash": content_hash,
            "content": content,
        }
    except OSError as e:
        _log.exception("Error getting file info for %s", file_path)
        return {
            "exists": False,
            "size": 0,
            "mtime": 0,
            "content_hash": None,
            "error": str(e),
        }


def should_sync(
    local_info: dict[str, t.Any],
    remote_info: dict[str, t.Any],
    direction: SyncDirection,
) -> tuple[bool, str]:
    local_exists = local_info["exists"]
    remote_exists = remote_info["exists"]

    if missing_result := _check_missing_files(local_exists, remote_exists, direction):
        return missing_result

    if local_exists and remote_exists:
        return _check_content_differences(local_info, remote_info, direction)

    return False, "content_identical"


def _check_missing_files(
    local_exists: bool,
    remote_exists: bool,
    direction: SyncDirection,
) -> tuple[bool, str] | None:
    if (
        not local_exists
        and remote_exists
        and direction in (SyncDirection.PULL, SyncDirection.BIDIRECTIONAL)
    ):
        return True, "local_missing"

    if (
        local_exists
        and not remote_exists
        and direction in (SyncDirection.PUSH, SyncDirection.BIDIRECTIONAL)
    ):
        return True, "remote_missing"

    if not local_exists and not remote_exists:
        return False, "both_missing"

    return None


def _check_content_differences(
    local_info: dict[str, t.Any],
    remote_info: dict[str, t.Any],
    direction: SyncDirection,
) -> tuple[bool, str]:
    if local_info["content_hash"] == remote_info["content_hash"]:
        return False, "content_identical"

    direction_reasons = {
        SyncDirection.PULL: "content_differs_pull",
        SyncDirection.PUSH: "content_differs_push",
        SyncDirection.BIDIRECTIONAL: "content_differs_bidirectional",
    }

    return True, direction_reasons.get(direction, "content_differs")


def get_sync_summary(result: SyncResult) -> dict[str, t.Any]:
    return {
        "total_processed": result.total_processed,
        "synced": result.success_count,
        "conflicts": len(result.conflicts),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "backed_up": len(result.backed_up),
        "success_rate": result.success_count / max(result.total_processed, 1),
        "has_conflicts": result.has_conflicts,
        "has_errors": result.has_errors,
        "is_success": result.is_success,
    }


# Migration status indicator
# Note: Partial migration - ACB debug system still in use
_using_oneiric = True  # Oneiric resolver available
_requires_further_migration = True  # ACB debug system needs migration
