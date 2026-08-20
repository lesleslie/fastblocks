"""Jinja2 Templates Adapter for FastBlocks.

Provides asynchronous Jinja2 template rendering with advanced features including:
- Multi-layer loader system (Redis cache, cloud storage, filesystem)
- Bidirectional integration with HTMY components via dedicated HTMY adapter
- Fragment and partial template support
- Bytecode caching with Redis backend
- Template synchronization across cache/storage/filesystem layers
- Custom delimiters ([[/]] instead of {{/}})
- Extensive template debugging and error handling

Requirements:
- jinja2-async-environment>=0.14.3
- starlette-async-jinja>=1.12.4
- jinja2>=3.1.6
- redis>=3.5.3 (for caching)

Usage:
```python
# ACB imports removed - using Oneiric equivalents
# templates = depends.resolve("fastblocks", "templates")
# Templates = import_adapter("templates")
# response = await templates.render_template(
#     request, "index.html", {"title": "FastBlocks"}
)
```

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-01-12
"""

from __future__ import annotations

import asyncio
import re
import typing as t
from ast import literal_eval
from contextlib import suppress
from functools import lru_cache
from html.parser import HTMLParser
from importlib import import_module
from importlib.util import find_spec
from inspect import isclass
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from oneiric.core.config import OneiricSettings
from oneiric.core.logging import get_logger
from oneiric.core.resolution import Resolver
from pydantic import Field

_log = get_logger("fastblocks.adapters.templates.jinja2")

from fastblocks.adapters.oneiric_helper import (
    register_candidate,
    register_instance,
    resolve_instance,
)

# Import event tracking decorator (with fallback if unavailable)
try:
    from ._events_wrapper import track_template_render
except ImportError:
    # Fallback no-op decorator if events integration unavailable
    def track_template_render(func: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:  # type: ignore[misc]
        return func


# Custom implementations for ACB compatibility
def get_adapter(adapter_name: str) -> t.Any:
    """Custom implementation for Oneiric compatibility."""
    # This will be implemented using Oneiric's adapter system
    return None


class AdapterStatus:
    """Custom AdapterStatus for Oneiric compatibility."""

    STABLE = "STABLE"
    BETA = "BETA"
    ALPHA = "ALPHA"
    EXPERIMENTAL = "EXPERIMENTAL"


def debug(msg: str) -> None:
    """Custom debug function for Oneiric compatibility."""
    print(f"[DEBUG] {msg}")


# Oneiric resolver for dependency injection
depends = Resolver()


from anyio import Path as AsyncPath
from jinja2 import TemplateNotFound
from jinja2.ext import Extension, i18n, loopcontrols
from jinja2.ext import debug as jinja_debug
from jinja2_async_environment import AsyncRedisBytecodeCache
from jinja2_async_environment.loaders import AsyncBaseLoader, SourceType
from starlette_async_jinja import AsyncJinja2Templates
from fastblocks.actions.sync.strategies import SyncDirection, SyncStrategy
from fastblocks.actions.sync.templates import sync_templates

from ._base import TemplatesBase, TemplatesBaseSettings

Cache, Storage, Models = None, None, None

_TEMPLATE_REPLACEMENTS = [
    (b"{{", b"[["),
    (b"}}", b"]]"),
    (b"{%", b"[%"),
    (b"%}", b"%]"),
]
_HTTP_TO_HTTPS = (b"http://", b"https://")

_ATTR_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


def _get_attr_pattern(attr: str) -> re.Pattern[str]:
    if attr not in _ATTR_PATTERN_CACHE:
        escaped_attr = re.escape(f"{attr}=")
        _ATTR_PATTERN_CACHE[attr] = re.compile(
            escaped_attr
        )  # REGEX OK: Template attribute pattern compilation for Jinja2
    return _ATTR_PATTERN_CACHE[attr]


def _try_resolve_sync(key: str) -> t.Any:
    """Resolve a Oneiric dependency synchronously for ``__init__`` paths.

    Oneiric's resolver is already synchronous; this helper exists only to
    surface a consistent ``logging`` warning when resolution fails (so the
    caller can fall back to the legacy ``get_adapter`` chain without
    propagating resolver exceptions).
    """
    try:
        return resolve_instance(depends, "fastblocks", key)
    except Exception as exc:  # noqa: BLE001
        _log.warning("jinja2._try_resolve_sync(%r): %s", key, exc)
        return None


def _apply_template_replacements(source: bytes, deployed: bool = False) -> bytes:
    for old_pattern, new_pattern in _TEMPLATE_REPLACEMENTS:
        source = source.replace(old_pattern, new_pattern)
    if deployed:
        source = source.replace(*_HTTP_TO_HTTPS)

    return source


class BaseTemplateLoader(AsyncBaseLoader):
    config: t.Any = None
    cache: t.Any = None
    storage: t.Any = None

    def __init__(
        self,
        searchpath: AsyncPath | t.Sequence[AsyncPath] | None = None,
    ) -> None:
        # Use current directory as default searchpath if none provided
        searchpath = searchpath or [AsyncPath(".")]
        super().__init__(searchpath)
        if self.storage is None:
            self.storage = _try_resolve_sync("storage")
        if self.storage is None:
            self.storage = get_adapter("storage")
        if self.cache is None:
            self.cache = _try_resolve_sync("cache")
        if self.cache is None:
            self.cache = get_adapter("cache")
        if not hasattr(self, "config"):
            self.config = _try_resolve_sync("config")
            if self.config is None:
                config_adapter = get_adapter("config")
                self.config = (
                    config_adapter
                    if hasattr(config_adapter, "model_config")
                    else OneiricSettings()
                )

    def get_supported_extensions(self) -> tuple[str, ...]:
        return ("html", "css", "js")

    async def _list_templates_for_extensions(
        self,
        extensions: tuple[str, ...],
    ) -> list[str]:
        found: set[str] = set()
        for searchpath in self.searchpath:
            for ext in extensions:
                async for p in searchpath.rglob(f"*.{ext}"):
                    found.add(str(p))
        return sorted(found)

    def _normalize_template(
        self,
        environment_or_template: t.Any,
        template: str | AsyncPath | None = None,
    ) -> str | AsyncPath:
        if template is None:
            template = environment_or_template
        assert template is not None
        return template

    async def _find_template_path_parallel(
        self,
        template: str | AsyncPath,
    ) -> AsyncPath | None:
        async def check_path(searchpath: AsyncPath) -> AsyncPath | None:
            path = searchpath / template
            if await path.is_file():
                return path
            return None

        tasks = [check_path(searchpath) for searchpath in self.searchpath]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, AsyncPath):
                return result
        return None

    async def _find_storage_path_parallel(
        self,
        template: str | AsyncPath,
    ) -> tuple[AsyncPath, AsyncPath] | None:
        async def check_storage_path(
            searchpath: AsyncPath,
        ) -> tuple[AsyncPath, AsyncPath] | None:
            path = searchpath / template
            storage_path = TemplatesBase.get_storage_path(path)
            if storage_path and await self.storage.templates.exists(storage_path):
                return path, storage_path
            return None

        tasks = [check_storage_path(searchpath) for searchpath in self.searchpath]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, tuple):
                return result
        return None

    async def _find_cache_path_parallel(
        self,
        template: str | AsyncPath,
    ) -> tuple[AsyncPath, AsyncPath, str] | None:
        async def check_cache_path(
            searchpath: AsyncPath,
        ) -> tuple[AsyncPath, AsyncPath, str] | None:
            path = searchpath / template if searchpath else AsyncPath(template)
            storage_path = TemplatesBase.get_storage_path(path)
            cache_key = Templates.get_cache_key(storage_path)
            if (
                storage_path
                and self.cache is not None
                and await self.cache.exists(cache_key)
            ):
                return path, storage_path, cache_key
            return None

        tasks = [check_cache_path(searchpath) for searchpath in self.searchpath]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, tuple):
                return result
        return None


class LoaderProtocol(t.Protocol):
    cache: t.Any
    config: t.Any
    storage: t.Any

    async def get_source_async(
        self,
        environment_or_template: t.Any,
        template: str | AsyncPath | None = None,
    ) -> tuple[
        str,
        str | None,
        t.Callable[[], bool] | t.Callable[[], t.Awaitable[bool]],
    ]: ...

    async def list_templates_async(self) -> list[str]: ...


class FileSystemLoader(BaseTemplateLoader):
    @staticmethod
    @lru_cache(maxsize=1000)
    def _read_through(path: str, mtime: int) -> bytes:
        """Read-through cache for template bytes, keyed by (path, mtime).

        Previously every read also issued a write back to remote storage,
        causing write amplification on hot templates. The cache hit path
        performs only the (cached) bytes return; no I/O.
        """
        return Path(path).read_bytes()

    @classmethod
    def invalidate(cls, path: str | AsyncPath) -> None:
        """Drop the cached read for a single path.

        Call after any write that mutates the on-disk content (e.g. sync
        from remote storage, admin write, or external editor save) so
        the next read picks up the new bytes.
        """
        cls._read_through.cache_clear()  # path-agnostic; full clear is safe

    @classmethod
    def invalidate_all(cls) -> None:
        """Drop all cached template reads."""
        cls._read_through.cache_clear()

    async def _check_storage_exists(self, storage_path: AsyncPath) -> bool:
        if self.storage is not None:
            return t.cast(bool, await self.storage.templates.exists(storage_path))
        return False

    async def _sync_template_file(
        self,
        path: AsyncPath,
        storage_path: AsyncPath,
    ) -> tuple[bytes, int]:
        if sync_templates is None or SyncDirection is None or SyncStrategy is None:
            return await self._sync_from_storage_fallback(path, storage_path)

        try:
            strategy = SyncStrategy(
                backup_on_conflict=False,
            )

            template_paths = [path]
            result = await sync_templates(
                template_paths=template_paths,
                strategy=strategy,
            )

            resp = await path.read_bytes()
            local_stat = await path.stat()
            local_mtime = int(local_stat.st_mtime)

            debug(f"Template sync result: {result.sync_status} for {path}")
            return resp, local_mtime

        except Exception as e:  # noqa: BLE001
            # The sync subsystem crashed (transient backend error,
            # permission failure, etc.). Log and fall through to the
            # primitive storage-fallback path so the renderer still
            # gets bytes for the template.
            _log.exception(
                "FileSystemLoader._sync_template_file: sync action failed for %s: %s",
                path,
                e,
            )
            return await self._sync_from_storage_fallback(path, storage_path)

    async def _sync_from_storage_fallback(
        self,
        path: AsyncPath,
        storage_path: AsyncPath,
    ) -> tuple[bytes, int]:
        local_stat = await path.stat()
        local_mtime = int(local_stat.st_mtime)
        local_size = local_stat.st_size
        storage_stat = await self.storage.templates.stat(storage_path)
        storage_mtime = round(storage_stat.get("mtime"))
        storage_size = storage_stat.get("size")

        if local_mtime < storage_mtime and local_size != storage_size:
            resp = await self.storage.templates.open(storage_path)
            await path.write_bytes(resp)
            # Local content changed — drop the cached read for this path.
            FileSystemLoader.invalidate(path)
        else:
            resp = await path.read_bytes()
            if local_size != storage_size:
                await self.storage.templates.write(storage_path, resp)
                # Remote content changed — drop the cached read for this path.
                FileSystemLoader.invalidate(path)
        return resp, local_mtime

    async def _read_and_store_template(
        self,
        path: AsyncPath,
        storage_path: AsyncPath,
    ) -> bytes:
        try:
            # Best-effort mtime for cache key; fall back to 0 if stat fails.
            try:
                local_stat = await path.stat()
                mtime = int(local_stat.st_mtime)
            except FileNotFoundError:
                mtime = 0
            # Read-through cache: hit path returns synchronously, no I/O.
            # Miss path reads once, caches, and returns. The previous
            # write-back-to-remote-storage on every read was removed to
            # eliminate write amplification; writes now happen only via
            # explicit sync paths, each of which calls invalidate().
            try:
                resp = FileSystemLoader._read_through(str(path), mtime)
            except FileNotFoundError:
                # Cache miss on a path that vanished — surface TemplateNotFound.
                if mtime == 0:
                    raise TemplateNotFound(path.name) from None
                # mtime was non-zero but the file is gone: re-raise.
                raise TemplateNotFound(path.name) from None
            # No unconditional write to remote storage on every read.
            return resp
        except FileNotFoundError:
            raise TemplateNotFound(path.name)

    async def _cache_template(self, storage_path: AsyncPath, resp: bytes) -> None:
        if self.cache is not None:
            await self.cache.set(Templates.get_cache_key(storage_path), resp)

    async def get_source_async(  # ty: ignore[invalid-method-override]
        self,
        environment_or_template: t.Any,
        template: str | AsyncPath | None = None,
    ) -> SourceType:
        template = self._normalize_template(environment_or_template, template)
        path = await self._find_template_path_parallel(template)
        if path is None:
            raise TemplateNotFound(str(template))
        storage_path = TemplatesBase.get_storage_path(path)
        debug(str(path))

        fs_exists = await path.exists()
        storage_exists = await self._check_storage_exists(storage_path)
        local_mtime = 0

        if storage_exists and fs_exists and (not self.config.deployed):
            resp, local_mtime = await self._sync_template_file(path, storage_path)
            # The sync path may have mutated the file; drop the cache entry.
            FileSystemLoader.invalidate(path)
        else:
            resp = await self._read_and_store_template(path, storage_path)
            if not local_mtime:
                try:
                    local_mtime = int((await path.stat()).st_mtime)
                except FileNotFoundError:
                    local_mtime = 0

        await self._cache_template(storage_path, resp)

        async def uptodate() -> bool:
            return int((await path.stat()).st_mtime) == local_mtime

        # The parent ``AsyncBaseLoader.get_source_async`` contract declares
        # the uptodate callable as ``Callable[[], bool]`` (sync), but the
        # async version here returns a coroutine. Cast to align with the
        # parent signature — at runtime the AsyncBaseLoader caller awaits
        # the returned value, so the coroutine is consumed correctly.
        return cast(
            "tuple[str | bytes, str | None, t.Callable[[], bool] | None]",
            (resp.decode(), str(storage_path), uptodate),
        )

    async def list_templates_async(self) -> list[str]:
        return await self._list_templates_for_extensions(
            self.get_supported_extensions(),
        )


config: t.Any = None


class StorageLoader(BaseTemplateLoader):
    async def _check_filesystem_sync_opportunity(
        self, template: str | AsyncPath, storage_path: AsyncPath
    ) -> AsyncPath | None:
        if not self.config or self.config.deployed:
            return None

        fs_result = await self._find_template_path_parallel(template)
        if fs_result and await fs_result.exists():
            return fs_result
        return None

    async def _sync_storage_with_filesystem(
        self,
        fs_path: AsyncPath,
        storage_path: AsyncPath,
    ) -> tuple[bytes, int]:
        if sync_templates is None or SyncDirection is None or SyncStrategy is None:
            resp = await self.storage.templates.open(storage_path)
            stat = await self.storage.templates.stat(storage_path)
            return resp, round(stat.get("mtime").timestamp())

        try:
            strategy = SyncStrategy(
                direction=SyncDirection.PULL,
                backup_on_conflict=False,
            )

            result = await sync_templates(
                template_paths=[fs_path],
                strategy=strategy,
            )

            resp = await fs_path.read_bytes()
            local_stat = await fs_path.stat()
            local_mtime = int(local_stat.st_mtime)

            debug(
                f"Storage-filesystem sync result: {result.sync_status} for {storage_path}"
            )
            return resp, local_mtime

        except Exception as e:  # noqa: BLE001
            # The sync subsystem could not reconcile the storage layer
            # with the filesystem copy. Logging then falling back to
            # "read storage directly" preserves the renderer contract:
            # it gets template bytes either way.
            _log.exception(
                "StorageLoader._sync_storage_with_filesystem: sync failed for %s: %s",
                storage_path,
                e,
            )
            resp = await self.storage.templates.open(storage_path)
            stat = await self.storage.templates.stat(storage_path)
            return resp, round(stat.get("mtime").timestamp())

    async def get_source_async(  # ty: ignore[invalid-method-override]
        self,
        environment_or_template: t.Any,
        template: str | AsyncPath | None = None,
    ) -> tuple[str, str, t.Callable[[], t.Awaitable[bool]]]:
        template = self._normalize_template(environment_or_template, template)
        result = await self._find_storage_path_parallel(template)
        if result is None:
            raise TemplateNotFound(str(template))
        _, storage_path = result
        debug(str(storage_path))

        try:
            fs_path = await self._check_filesystem_sync_opportunity(
                template, storage_path
            )

            if fs_path:
                resp, local_mtime = await self._sync_storage_with_filesystem(
                    fs_path, storage_path
                )
            else:
                resp = await self.storage.templates.open(storage_path)
                local_stat = await self.storage.templates.stat(storage_path)
                local_mtime = round(local_stat.get("mtime").timestamp())

            if self.cache is not None:
                await self.cache.set(Templates.get_cache_key(storage_path), resp)

            async def uptodate() -> bool:
                if fs_path and await fs_path.exists():
                    fs_stat = await fs_path.stat()
                    return int(fs_stat.st_mtime) == local_mtime
                else:
                    storage_stat = await self.storage.templates.stat(storage_path)
                    mtime = storage_stat.get("mtime")
                    if hasattr(mtime, "timestamp"):
                        timestamp = t.cast(float, mtime.timestamp())
                        return round(timestamp) == local_mtime
                    return False

            return (resp.decode(), str(storage_path), uptodate)
        except (FileNotFoundError, AttributeError):
            raise TemplateNotFound(str(template))

    async def list_templates_async(self) -> list[str]:
        found: list[str] = []
        # StorageLoader without a configured ``self.storage`` is
        # a no-op (test_list_templates_async_no_storage verifies
        # this). The prior code dereferenced ``self.storage.templates``
        # unconditionally and crashed with ``AttributeError`` when
        # storage was None.
        if self.storage is None:
            return found
        for searchpath in self.searchpath:
            with suppress(FileNotFoundError):
                paths = await self.storage.templates.list(
                    TemplatesBase.get_storage_path(searchpath),
                )
                found.extend(p for p in paths if p.endswith((".html", ".css", ".js")))
        found.sort()
        return found


config: t.Any = None


class RedisLoader(BaseTemplateLoader):
    async def get_source_async(  # ty: ignore[invalid-method-override]
        self,
        environment_or_template: t.Any,
        template: str | AsyncPath | None = None,
    ) -> tuple[
        str, str | None, t.Callable[[], bool] | t.Callable[[], t.Awaitable[bool]]
    ]:
        template = self._normalize_template(environment_or_template, template)
        result = await self._find_cache_path_parallel(template)
        if result is None:
            raise TemplateNotFound(str(template))
        path, _, cache_key = result
        debug(cache_key)
        resp = await self.cache.get(cache_key) if self.cache is not None else None
        if not resp:
            raise TemplateNotFound(path.name)

        def uptodate() -> bool:
            return True

        return (resp.decode(), None, uptodate)

    async def list_templates_async(self) -> list[str]:
        found: list[str] = []
        for ext in ("html", "css", "js"):
            scan_result: t.Any = (
                await self.cache.scan(f"*.{ext}") if self.cache is not None else []
            )
            if hasattr(scan_result, "__aiter__"):
                async for k in scan_result:
                    found.append(k)
            else:
                found.extend(scan_result)
        found.sort()
        return found


class PackageLoader(BaseTemplateLoader):
    _template_root: AsyncPath
    _adapter: str
    package_name: str
    _loader: t.Any

    def __init__(
        self,
        package_name: str,
        path: str = "templates",
        adapter: str = "admin",
    ) -> None:
        self.package_path = Path(package_name)
        self.path = self.package_path / path
        super().__init__(AsyncPath(self.path))
        self.package_name = package_name
        self._adapter = adapter
        self._template_root = AsyncPath(".")
        try:
            if package_name.startswith("/"):
                spec = None
                self._loader = None
                return
            import_module(package_name)
            spec = find_spec(package_name)
            if spec is None:
                msg = f"Could not find package {package_name}"
                raise ImportError(msg)
        except ModuleNotFoundError:
            spec = None
            self._loader = None
            return
        roots: list[Path] = []
        template_root = None
        loader = spec.loader
        self._loader = loader
        if spec.submodule_search_locations:
            roots.extend(Path(s) for s in spec.submodule_search_locations)
        elif spec.origin is not None:
            roots.append(Path(spec.origin))
        for root in roots:
            root = root / path
            if root.is_dir():
                template_root = root
                break
        if template_root is None:
            msg = f"The {package_name!r} package was not installed in a way that PackageLoader understands."
            raise ValueError(
                msg,
            )
        self._template_root = AsyncPath(template_root)

    async def get_source_async(  # ty: ignore[invalid-method-override]
        self,
        environment_or_template: t.Any,
        template: str | AsyncPath | None = None,
    ) -> tuple[str, str, t.Callable[[], t.Awaitable[bool]]]:
        if template is None:
            template = environment_or_template
        assert template is not None
        template_path: AsyncPath = AsyncPath(template)
        path = self._template_root / template_path
        debug(str(path))
        if not await path.is_file():
            raise TemplateNotFound(template_path.name)
        source = await path.read_bytes()
        mtime = (await path.stat()).st_mtime

        async def uptodate() -> bool:
            return await path.is_file() and (await path.stat()).st_mtime == mtime

        source = _apply_template_replacements(source, self.config.deployed)
        storage_path = TemplatesBase.get_storage_path(path)
        _storage_path: list[str] = list(storage_path.parts)
        _storage_path[0] = "_templates"
        _storage_path.insert(1, self._adapter)
        _storage_path.insert(2, getattr(self.config, self._adapter).style)
        storage_path = AsyncPath("/".join(_storage_path))
        cache_key = Templates.get_cache_key(storage_path)
        if self.cache is not None:
            await self.cache.set(cache_key, source)
        return (source.decode(), path.name, uptodate)

    async def list_templates_async(self) -> list[str]:
        found: set[str] = set()
        for ext in ("html", "css", "js"):
            found.update([str(p) async for p in self._template_root.rglob(f"*.{ext}")])
        return sorted(found)


config: t.Any = None


class ChoiceLoader(AsyncBaseLoader):  # type: ignore[misc]
    loaders: list[AsyncBaseLoader | LoaderProtocol]

    def __init__(
        self,
        loaders: list[AsyncBaseLoader | LoaderProtocol],
        searchpath: AsyncPath | t.Sequence[AsyncPath] | None = None,
    ) -> None:
        super().__init__(searchpath or AsyncPath("templates"))
        self.loaders = loaders

    async def get_source_async(  # ty: ignore[invalid-method-override]
        self,
        environment_or_template: t.Any,
        template: str | AsyncPath | None = None,
    ) -> SourceType:
        if template is None:
            template = environment_or_template
        assert template is not None
        for loader in self.loaders:
            try:
                # Call child loaders with the documented single-argument
                # contract: ``get_source_async(name)``. Passing two
                # positional args (environment, name) -- the
                # ``AsyncBaseLoader`` abstract signature -- bypasses the
                # child loader's own ``_normalize_template`` two-form
                # entry point and surfaces as a duplicate-name call at
                # the test boundary. The child classes already accept
                # a single-arg call via their ``_normalize_template``
                # fallback (used by the direct ``loader.get_source_async(
                # template_name)`` test paths), so the single-arg call
                # is the only contract that works uniformly across all
                # loaders in this hierarchy.
                result = await loader.get_source_async(str(template))
                return cast(SourceType, result)
            except TemplateNotFound:
                # The next loader may have it; only "missing template"
                # is a recoverable signal at this level. Loader
                # syntax errors, permission failures, and programming
                # mistakes must propagate to the renderer so they are
                # not silently swallowed.
                continue
        raise TemplateNotFound(str(template))

    async def list_templates_async(self) -> list[str]:
        found: set[str] = set()
        for loader in self.loaders:
            templates = await loader.list_templates_async()
            found.update(templates)
        return sorted(found)


@lru_cache(maxsize=16)
def _build_cached_loader(
    deployed: bool,
    production: bool,
    template_set_id: str,
    searchpaths: tuple[AsyncPath, ...],
    is_admin_set: bool,
    admin_spec: tuple[str, str, str] | None,
) -> ChoiceLoader:
    """Build and cache a ChoiceLoader for a given (config, template_set) key.

    Previously this happened on every get_loader() call, re-instantiating
    Redis/Storage/FileSystem loaders and re-running PackageLoader's import.
    The cache key must be a stable representation of all inputs that affect
    loader composition. Call reload_loader() to force a rebuild (e.g. on
    hot-reload or config mutation).
    """
    searchpath_list: list[AsyncPath] = list(searchpaths)
    loaders: list[AsyncBaseLoader] = [
        RedisLoader(searchpath_list),
        StorageLoader(searchpath_list),
    ]
    file_loaders: list[AsyncBaseLoader | LoaderProtocol] = [
        FileSystemLoader(searchpath_list),
    ]
    jinja_loaders: list[AsyncBaseLoader | LoaderProtocol] = loaders + file_loaders
    if not deployed and not production:
        jinja_loaders = file_loaders + loaders
    if is_admin_set and admin_spec is not None:
        pkg_name, pkg_path, adapter = admin_spec
        jinja_loaders.append(PackageLoader(pkg_name, pkg_path, adapter))
    debug(str(jinja_loaders))
    return ChoiceLoader(jinja_loaders)


def reload_loader() -> None:
    """Clear the cached loader.

    Call after configuration changes, hot-reload, or any event that should
    force a fresh ChoiceLoader build on the next get_loader() call.
    """
    _build_cached_loader.cache_clear()
    # Also drop any cached template reads so the next read reflects the
    # new loader composition immediately.
    FileSystemLoader.invalidate_all()


class TemplatesSettings(TemplatesBaseSettings):
    loader: str | None = None
    extensions: list[str] = Field(default_factory=list)
    delimiters: dict[str, str] = Field(
        default_factory=lambda: {
            "block_start_string": "[%",
            "block_end_string": "%]",
            "variable_start_string": "[[",
            "variable_end_string": "]]",
            "comment_start_string": "[#",
            "comment_end_string": "#]",
        }
    )
    globals: dict[str, t.Any] = Field(default_factory=dict)
    context_processors: list[str] = Field(default_factory=list)

    def __init__(self, **data: t.Any) -> None:
        from pydantic import BaseModel

        BaseModel.__init__(self, **data)
        if not hasattr(self, "cache_timeout"):
            self.cache_timeout = 300
        try:
            models = _try_resolve_sync("models")
            self.globals["models"] = models
        except Exception:  # noqa: BLE001
            self.globals["models"] = None


class Templates(TemplatesBase):
    app: AsyncJinja2Templates | None = None
    config: t.Any = None
    logger: t.Any = None

    def __init__(self, **kwargs: t.Any) -> None:
        super().__init__(**kwargs)
        self.filters: dict[str, t.Callable[..., t.Any]] = {}
        self.enabled_admin = get_adapter("admin")
        self.enabled_app = self._get_app_adapter()
        self._admin = None
        self._admin_initialized = False

    def _get_app_adapter(self) -> t.Any:
        app_adapter = get_adapter("app")
        if app_adapter is not None:
            return app_adapter
        with suppress(Exception):
            app_adapter = resolve_instance(depends, "fastblocks", "app")
            if app_adapter is not None:
                return app_adapter

        return None

    @property
    def admin(self) -> AsyncJinja2Templates | None:
        if not self._admin_initialized and self.enabled_admin:
            import asyncio

            loop = asyncio.get_event_loop()
            if (
                hasattr(self, "_admin_cache")
                and hasattr(self, "admin_searchpaths")
                and self.admin_searchpaths is not None
            ):
                debug("Initializing admin templates environment")
                self._admin = loop.run_until_complete(
                    self.init_envs(
                        self.admin_searchpaths,
                        admin=True,
                        cache=self._admin_cache,
                    ),
                )
            else:
                debug(
                    "Skipping admin templates initialization - missing cache or searchpaths"
                )
            self._admin_initialized = True
        return self._admin

    @admin.setter
    def admin(self, value: AsyncJinja2Templates | None) -> None:
        self._admin = value
        self._admin_initialized = True

    def get_loader(self, template_paths: list[AsyncPath]) -> ChoiceLoader:
        searchpaths: list[AsyncPath] = []
        for path in template_paths:
            searchpaths.extend([path, path / "blocks"])

        # Compute cache key inputs from instance state. Changing any of these
        # triggers a fresh loader build (via reload_loader()).
        deployed = bool(self.config.deployed)  # type: ignore[attr-defined]
        production = bool(self.config.debug.production)  # type: ignore[attr-defined]
        template_set_id = ",".join(str(p) for p in template_paths)
        is_admin_set = bool(
            self.enabled_admin and template_paths == self.admin_searchpaths
        )
        admin_spec: tuple[str, str, str] | None = None
        if is_admin_set and self.enabled_admin is not None:
            admin_spec = (
                getattr(self.enabled_admin, "name", "admin"),
                "templates",
                "admin",
            )

        return _build_cached_loader(
            deployed,
            production,
            template_set_id,
            tuple(searchpaths),
            is_admin_set,
            admin_spec,
        )

    async def init_envs(
        self,
        template_paths: list[AsyncPath],
        admin: bool = False,
        cache: t.Any | None = None,
    ) -> AsyncJinja2Templates:
        _extensions: list[t.Any] = [loopcontrols, i18n, jinja_debug]
        _imported_extensions = [
            import_module(e)
            for e in self.config.templates.extensions  # type: ignore[attr-defined]
        ]
        for e in _imported_extensions:
            _extensions.extend(
                [
                    v
                    for v in vars(e).values()
                    if isclass(v)
                    and v.__name__ != "Extension"
                    and issubclass(v, Extension)
                ],
            )
        bytecode_cache = None
        if cache is not None:
            bytecode_cache = AsyncRedisBytecodeCache(prefix="bccache", client=cache)
        context_processors: list[t.Callable[..., t.Any]] = []
        for processor_path in self.config.templates.context_processors:  # type: ignore[attr-defined]
            module_path, func_name = processor_path.rsplit(".", 1)
            module = import_module(module_path)
            processor = getattr(module, func_name)
            context_processors.append(processor)
        templates = AsyncJinja2Templates(
            directory=AsyncPath("templates"),
            context_processors=context_processors,
            extensions=_extensions,
            bytecode_cache=bytecode_cache,
            enable_async=True,
        )
        loader = self.get_loader(template_paths)
        if loader:
            templates.env.loader = loader
        elif self.config.templates.loader:  # type: ignore[attr-defined]
            templates.env.loader = literal_eval(self.config.templates.loader)  # type: ignore[attr-defined]
        for delimiter, value in self.config.templates.delimiters.items():  # type: ignore[attr-defined]
            setattr(templates.env, delimiter, value)
        # Type cast globals dict to avoid assignment type errors
        globals_dict: dict[str, t.Any] = templates.env.globals
        globals_dict["config"] = self.config  # type: ignore[attr-defined]
        globals_dict["render_block"] = templates.render_block
        globals_dict["render_component"] = self._get_htmy_component_renderer()
        with suppress(Exception):
            from fastblocks.core.style_registry import register_style_functions

            style_name = getattr(getattr(self.config, "app", None), "style", None)  # type: ignore[attr-defined]
            register_style_functions(templates.env, style_name)
        if admin:
            try:
                from sqladmin.helpers import (
                    get_object_identifier,
                )
            except ImportError:
                # sqladmin is not installed; fall back to ``str``. Declared
                # as ``Any`` because sqladmin's helper signature
                # ``def get_object_identifier(obj: Any) -> Any`` is
                # structurally compatible with ``str`` at runtime for the
                # single-arg use case, but strict type checkers reject the
                # ``str`` assignment. ``Any`` here documents the degraded
                # fallback contract without weakening the import-path type.
                get_object_identifier: Any = str
            globals_dict["min"] = min
            globals_dict["zip"] = zip
            globals_dict["admin"] = self
            globals_dict["is_list"] = lambda x: isinstance(x, list)
            globals_dict["get_object_identifier"] = get_object_identifier
        for k, v in self.config.templates.globals.items():  # type: ignore[attr-defined]
            globals_dict[k] = v
        return templates

    def _resolve_cache(self, cache: t.Any | None) -> t.Any | None:
        if cache is None:
            cache = _try_resolve_sync("cache")
        return cache

    async def _setup_admin_templates(self, cache: t.Any | None) -> None:
        if self.enabled_admin:
            self.admin_searchpaths = await self.get_searchpaths(self.enabled_admin)
            self._admin_cache = cache

    def _log_loader_info(self) -> None:
        if self.app and self.app.env.loader:
            loaders = getattr(self.app.env.loader, "loaders", None) or []
            for loader in loaders:
                self.logger.debug(f"{loader.__class__.__name__} initialized")

    def _log_extension_info(self) -> None:
        if self.app and hasattr(self.app.env, "extensions"):
            for ext in self.app.env.extensions:
                self.logger.debug(f"{ext.split('.')[-1]} loaded")  # type: ignore[attr-defined]

    async def _clear_debug_cache(self, cache: t.Any | None) -> None:
        if getattr(self.config.debug, "templates", False):  # type: ignore[attr-defined]
            try:
                for namespace in (
                    "templates",
                    "_templates",
                    "bccache",
                    "template",
                    "test",
                ):
                    if cache is not None:
                        await cache.clear(namespace)
                self.logger.debug("Template caches cleared")  # type: ignore[attr-defined]
                with suppress(Exception):
                    htmy_adapter = resolve_instance(depends, "fastblocks", "htmy")
                    if htmy_adapter:
                        await htmy_adapter.clear_component_cache()
                        self.logger.debug("HTMY component caches cleared via adapter")  # type: ignore[attr-defined]
            except (NotImplementedError, AttributeError) as e:
                self.logger.debug(f"Cache clear not supported: {e}")  # type: ignore[attr-defined]

    def _get_htmy_component_renderer(self) -> t.Callable[..., t.Any]:
        async def render_component(
            component_name: str,
            context: dict[str, t.Any] | None = None,
            **kwargs: t.Any,
        ) -> str:
            try:
                htmy_adapter = resolve_instance(depends, "fastblocks", "htmy")
                if htmy_adapter:
                    htmy_adapter.jinja_templates = self

                    response = await htmy_adapter.render_component(
                        request=None,
                        component=component_name,
                        context=context,
                        **kwargs,
                    )
                    return (
                        response.body.decode()
                        if hasattr(response.body, "decode")
                        else str(response.body)
                    )
                else:
                    debug(
                        f"HTMY adapter not available for component '{component_name}'"
                    )
                    return f"<!-- HTMY adapter not available for '{component_name}' -->"
            except Exception as e:  # noqa: BLE001
                # The renderer must not raise from inside Jinja2 eval --
                # log and return a comment stub. Different exceptions
                # mean different failure modes (HS lookup vs adapter
                # internal), so we record the type explicitly.
                _log.exception(
                    "Templates._get_htmy_component_renderer: HTMY "
                    "render_component(%r) raised %s",
                    component_name,
                    type(e).__name__,
                )
                debug(
                    f"Failed to render component '{component_name}' via HTMY adapter: {e}"
                )
                return f"<!-- Error rendering component '{component_name}': {e} -->"

        return render_component

    async def init(self, cache: t.Any | None = None) -> None:
        cache = self._resolve_cache(cache)
        app_adapter = self.enabled_app
        if app_adapter is None:
            app_adapter = _try_resolve_sync("app")
            if app_adapter:
                debug("Retrieved app adapter from dependency injection")
            else:
                try:
                    from ..app.default import App

                    app_adapter = _try_resolve_sync("app") or App()
                    debug("Created app adapter by direct import")
                    register_candidate(
                        depends,
                        domain="fastblocks",
                        key="app",
                        factory=lambda: app_adapter,
                        metadata={"name": "app", "category": "app"},
                    )
                except Exception as exc:  # noqa: BLE001
                    # Both the dependency resolver and the direct import
                    # failed. Fall back to a stub so init_envs has *some*
                    # adapter-like object to query. Logged so operators
                    # can tell the difference between a missing dependency
                    # and an unexpected impl failure.
                    _log.exception(
                        "Templates.init: app-adapter fallback failed: %s",
                        type(exc).__name__,
                    )
                    from types import SimpleNamespace

                    app_adapter = SimpleNamespace(name="app", category="app")
                    debug(
                        "Created fallback app adapter - discovery failed, direct import failed"
                    )
        self.app_searchpaths = await self.get_searchpaths(app_adapter)
        self.app = await self.init_envs(self.app_searchpaths, cache=cache)
        register_candidate(
            depends,
            domain="fastblocks",
            key="templates",
            factory=lambda: self,
            metadata={
                "class": "Templates",
                "module": "fastblocks.adapters.templates.jinja2",
            },
        )
        self._admin = None
        self._admin_initialized = False
        await self._setup_admin_templates(cache)
        self._log_loader_info()
        self._log_extension_info()
        await self._clear_debug_cache(cache)

    @staticmethod
    def get_attr(html: str, attr: str) -> str | None:
        parser = HTMLParser()
        parser.feed(html)
        soup = parser.get_starttag_text()
        if soup is None:
            return None
        attr_pattern = _get_attr_pattern(attr)
        _attr = f"{attr}="
        for s in soup.split():
            if attr_pattern.search(s):
                return s.replace(_attr, "").strip('"')
        return None

    def _add_filters(self, env: t.Any) -> None:
        if hasattr(self, "filters") and self.filters:
            for name, filter_func in self.filters.items():
                if hasattr(env, "add_filter"):
                    env.add_filter(filter_func, name)
                else:
                    env.filters[name] = filter_func

    @track_template_render
    async def render_template(
        self,
        request: t.Any,
        template: str,
        context: dict[str, t.Any] | None = None,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> t.Any:
        if context is None:
            context = {}
        if headers is None:
            headers = {}

        templates_env = self.app
        if templates_env:
            return await templates_env.TemplateResponse(
                request=request,
                name=template,
                context=context,
                status_code=status_code,
                headers=headers,
            )
        from starlette.responses import HTMLResponse

        return HTMLResponse(
            content=f"<html><body>Template {template} not found</body></html>",
            status_code=404,
            headers=headers,
        )

    @track_template_render
    async def render_component(
        self,
        request: t.Any,
        component: str,
        context: dict[str, t.Any] | None = None,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        **kwargs: t.Any,
    ) -> t.Any:
        try:
            htmy_adapter = resolve_instance(depends, "fastblocks", "htmy")
            if htmy_adapter:
                htmy_adapter.jinja_templates = self
                return await htmy_adapter.render_component(
                    request=request,
                    component=component,
                    context=context,
                    status_code=status_code,
                    headers=headers,
                    **kwargs,
                )
            else:
                from starlette.responses import HTMLResponse

                return HTMLResponse(
                    content=f"<html><body>HTMY adapter not available for component '{component}'</body></html>",
                    status_code=500,
                    headers=headers,
                )
        except Exception as e:  # noqa: BLE001
            # Last-resort safety net: never let an unhandled adapter
            # failure escape into the renderer. Return a 500 with the
            # exception name visible so operators can correlate.
            _log.exception(
                "Templates.render_component(%r): adapter raised %s",
                component,
                type(e).__name__,
            )
            from starlette.responses import HTMLResponse

            return HTMLResponse(
                content=f"<html><body>Component error: {e}</body></html>",
                status_code=500,
                headers=headers,
            )

    def filter(
        self,
        name: str | None = None,
    ) -> t.Callable[[t.Any], t.Any]:
        def decorator(f: t.Any) -> t.Any:
            if self.app and hasattr(self.app.env, "filters"):
                self.app.env.filters[name or f.__name__] = f
            if self.admin and hasattr(self.admin.env, "filters"):
                self.admin.env.filters[name or f.__name__] = f
            return f

        return decorator

    def _load_extensions(self) -> list[t.Any]:
        _extensions: list[t.Any] = [loopcontrols, i18n, jinja_debug]
        extensions_list = getattr(
            getattr(self, "settings", None),
            "extensions",
            self.config.templates.extensions,  # type: ignore[attr-defined]
        )
        _imported_extensions = [import_module(e) for e in extensions_list]  # type: ignore[union-attr]
        for e in _imported_extensions:
            _extensions.extend(
                [
                    v
                    for v in vars(e).values()
                    if isclass(v)
                    and v.__name__ != "Extension"
                    and issubclass(v, Extension)
                ],
            )
        return _extensions


config: t.Any = None
MODULE_ID = UUID("01937d86-4f2a-7b3c-8d9e-1234567890ab")
MODULE_STATUS = AdapterStatus.STABLE

with suppress(Exception):
    register_instance(depends, Templates)

# Oneiric migration indicator
_using_oneiric = True

__all__ = ["Templates", "TemplatesSettings"]
