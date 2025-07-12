"""Gather strategies for error handling, caching, and parallelization."""

import asyncio
import typing as t
from enum import Enum
from pathlib import Path

from acb.debug import debug


class ErrorStrategy(Enum):
    FAIL_FAST = "fail_fast"
    COLLECT_ERRORS = "collect_errors"
    IGNORE_ERRORS = "ignore_errors"
    PARTIAL_SUCCESS = "partial_success"


class CacheStrategy(Enum):
    NO_CACHE = "no_cache"
    MEMORY_CACHE = "memory_cache"
    PERSISTENT = "persistent"


class GatherStrategy:
    def __init__(
        self,
        *,
        parallel: bool = True,
        max_concurrent: int = 10,
        timeout: float = 30.0,
        error_strategy: ErrorStrategy = ErrorStrategy.PARTIAL_SUCCESS,
        cache_strategy: CacheStrategy = CacheStrategy.MEMORY_CACHE,
        retry_attempts: int = 2,
        retry_delay: float = 0.1,
    ) -> None:
        self.parallel = parallel
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.error_strategy = error_strategy
        self.cache_strategy = cache_strategy
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay


_memory_cache: dict[str, t.Any] = {}


class GatherResult:
    def __init__(
        self,
        *,
        success: list[t.Any] | None = None,
        errors: list[Exception] | None = None,
        cache_key: str | None = None,
    ) -> None:
        self.success = success if success is not None else []
        self.errors = errors if errors is not None else []
        self.cache_key = cache_key
        self.total_attempts = len(self.success) + len(self.errors)

    @property
    def is_success(self) -> bool:
        return len(self.success) > 0

    @property
    def is_partial(self) -> bool:
        return len(self.success) > 0 and len(self.errors) > 0

    @property
    def is_failure(self) -> bool:
        return len(self.success) == 0 and len(self.errors) > 0


async def gather_with_strategy(
    tasks: list[t.Coroutine[t.Any, t.Any, t.Any]],
    strategy: GatherStrategy,
    cache_key: str | None = None,
) -> GatherResult:
    if cached_result := _check_cache(cache_key, strategy):
        return cached_result

    success_results, error_results = await _execute_tasks_with_strategy(tasks, strategy)

    _handle_gather_errors(error_results, success_results, strategy)

    result = GatherResult(
        success=success_results,
        errors=error_results,
        cache_key=cache_key,
    )

    _cache_result_if_needed(result, cache_key, strategy)

    return result


def _check_cache(
    cache_key: str | None,
    strategy: GatherStrategy,
) -> GatherResult | None:
    if cache_key and strategy.cache_strategy != CacheStrategy.NO_CACHE:
        if cached_result := _memory_cache.get(cache_key):
            debug(f"Cache hit for {cache_key}")
            return cached_result
    return None


async def _execute_tasks_with_strategy(
    tasks: list[t.Coroutine[t.Any, t.Any, t.Any]],
    strategy: GatherStrategy,
) -> tuple[list[t.Any], list[Exception]]:
    if strategy.parallel and len(tasks) > 1:
        return await _execute_tasks_parallel(tasks, strategy)
    return await _execute_tasks_sequential(tasks, strategy)


async def _execute_tasks_parallel(
    tasks: list[t.Coroutine[t.Any, t.Any, t.Any]],
    strategy: GatherStrategy,
) -> tuple[list[t.Any], list[Exception]]:
    success_results = []
    error_results = []
    semaphore = asyncio.Semaphore(strategy.max_concurrent)

    async def execute_with_semaphore(task: t.Coroutine[t.Any, t.Any, t.Any]) -> t.Any:
        async with semaphore:
            return await _execute_with_retry(task, strategy)

    try:
        results = await asyncio.wait_for(
            asyncio.gather(
                *[execute_with_semaphore(task) for task in tasks],
                return_exceptions=True,
            ),
            timeout=strategy.timeout,
        )

        for result in results:
            if isinstance(result, Exception):
                error_results.append(result)
            else:
                success_results.append(result)

    except TimeoutError as e:
        error_results.append(e)

    return success_results, error_results


async def _execute_tasks_sequential(
    tasks: list[t.Coroutine[t.Any, t.Any, t.Any]],
    strategy: GatherStrategy,
) -> tuple[list[t.Any], list[Exception]]:
    success_results = []
    error_results = []

    for task in tasks:
        try:
            result = await asyncio.wait_for(
                _execute_with_retry(task, strategy),
                timeout=strategy.timeout,
            )
            success_results.append(result)

        except Exception as e:
            error_results.append(e)
            if strategy.error_strategy == ErrorStrategy.FAIL_FAST:
                break

    return success_results, error_results


def _handle_gather_errors(
    error_results: list[Exception],
    success_results: list[t.Any],
    strategy: GatherStrategy,
) -> None:
    if error_results:
        debug(f"Gathering completed with {len(error_results)} errors")

        if strategy.error_strategy == ErrorStrategy.FAIL_FAST:
            raise error_results[0]
        if strategy.error_strategy == ErrorStrategy.COLLECT_ERRORS:
            if not success_results:
                msg = f"All gathering operations failed: {error_results}"
                raise Exception(msg)


def _cache_result_if_needed(
    result: GatherResult,
    cache_key: str | None,
    strategy: GatherStrategy,
) -> None:
    if cache_key and strategy.cache_strategy == CacheStrategy.MEMORY_CACHE:
        _memory_cache[cache_key] = result
        debug(f"Cached result for {cache_key}")


async def _execute_with_retry(
    task: t.Coroutine[t.Any, t.Any, t.Any],
    strategy: GatherStrategy,
) -> t.Any:
    for attempt in range(strategy.retry_attempts + 1):
        try:
            return await task
        except Exception as e:
            if attempt == strategy.retry_attempts:
                raise

            debug(f"Retry attempt {attempt + 1} after error: {e}")
            await asyncio.sleep(strategy.retry_delay * (attempt + 1))

    msg = "Should not reach here"
    raise RuntimeError(msg)


async def gather_modules(
    module_patterns: list[str],
    strategy: GatherStrategy | None = None,
    cache_key: str | None = None,
) -> GatherResult:
    if strategy is None:
        strategy = GatherStrategy()

    tasks: list[t.Coroutine[t.Any, t.Any, t.Any]] = [
        _import_module_safe(pattern) for pattern in module_patterns
    ]

    return await gather_with_strategy(tasks, strategy, cache_key)


async def _import_module_safe(module_path: str) -> t.Any:
    from importlib import import_module

    if module_path.startswith("."):
        base_module = "fastblocks"
        module_path = base_module + module_path
    debug(f"Importing module: {module_path}")
    try:
        return import_module(module_path)
    except ModuleNotFoundError as e:
        debug(f"Module not found: {module_path} - {e}")
        raise
    except Exception as e:
        debug(f"Error importing {module_path}: {e}")
        raise


async def gather_files(
    file_patterns: list[str],
    base_path: Path | None = None,
    strategy: GatherStrategy | None = None,
    cache_key: str | None = None,
) -> GatherResult:
    if strategy is None:
        strategy = GatherStrategy()

    if base_path is None:
        from acb.adapters import root_path

        base_path = Path(root_path)

    tasks: list[t.Coroutine[t.Any, t.Any, t.Any]] = [
        _find_files_safe(pattern, base_path) for pattern in file_patterns
    ]

    return await gather_with_strategy(tasks, strategy, cache_key)


async def _find_files_safe(pattern: str, base_path: Path) -> list[Path]:
    from anyio import Path as AsyncPath

    async_base = AsyncPath(base_path)
    try:
        if "*" in pattern:
            async_files = [
                f async for f in async_base.rglob(pattern) if await f.is_file()
            ]
            files = [Path(f) for f in async_files]
        else:
            file_path = async_base / pattern
            files = [Path(file_path)] if await file_path.exists() else []
        debug(f"Found {len(files)} files for pattern: {pattern}")
        return files
    except Exception as e:
        debug(f"Error finding files for pattern {pattern}: {e}")
        raise


def clear_cache(cache_key: str | None = None) -> None:
    if cache_key:
        _memory_cache.pop(cache_key, None)
        debug(f"Cleared cache for {cache_key}")
    else:
        _memory_cache.clear()
        debug("Cleared all cache")


def get_cache_info() -> dict[str, t.Any]:
    return {
        "total_entries": len(_memory_cache),
        "cache_keys": list(_memory_cache.keys()),
        "memory_usage": sum(len(str(v)) for v in _memory_cache.values()),
    }
