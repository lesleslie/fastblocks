"""HTMY Templates Adapter for FastBlocks.

Provides native HTMY component rendering with advanced features including:
- Component discovery and caching system
- Multi-layer caching (Redis, cloud storage, filesystem)
- Bidirectional integration with Jinja2 templates
- Async component rendering with context sharing
- Template synchronization across cache/storage/filesystem layers
- Enhanced debugging and error handling

Requirements:
- htmy>=0.1.0
- redis>=3.5.3 (for caching)

Usage:
```python
from acb.depends import depends

htmy = depends.get("htmy")

HTMYTemplates = import_adapter("htmy")

response = await htmy.render_component(request, "my_component", {"data": data})

component_class = await htmy.get_component_class("my_component")
```

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-01-13
"""

import asyncio
import typing as t
from contextlib import suppress
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

# Handle imports with fallback for different ACB versions
# Import all names in a single try-except block
imports_successful = False
try:
    from acb.adapters import AdapterStatus as _AdapterStatus
    from acb.adapters import get_adapter as _get_adapter
    from acb.adapters import import_adapter as _import_adapter
    from acb.adapters import root_path as _root_path

    imports_successful = True
except ImportError:
    _AdapterStatus = None
    _get_adapter = None
    _import_adapter = None
    _root_path = None

# Assign the imported names or fallbacks
if imports_successful:
    AdapterStatus = _AdapterStatus
    get_adapter = _get_adapter
    import_adapter = _import_adapter
    root_path = _root_path
else:
    # Define fallbacks
    class _FallbackAdapterStatus(Enum):
        ALPHA = "alpha"
        BETA = "beta"
        STABLE = "stable"
        DEPRECATED = "deprecated"
        EXPERIMENTAL = "experimental"

    AdapterStatus = _FallbackAdapterStatus
    get_adapter = None
    import_adapter = None
    root_path = None
from acb.debug import debug
from acb.depends import depends
from anyio import Path as AsyncPath
from starlette.responses import HTMLResponse

from ._base import TemplatesBase, TemplatesBaseSettings

if TYPE_CHECKING:
    from fastblocks.actions.sync.strategies import SyncDirection, SyncStrategy
    from fastblocks.actions.sync.templates import sync_templates

try:
    from fastblocks.actions.sync.strategies import SyncDirection, SyncStrategy
    from fastblocks.actions.sync.templates import sync_templates
except ImportError:
    sync_templates: t.Callable[..., t.Any] | None = None  # type: ignore[no-redef]
    SyncDirection: type[Enum] | None = None  # type: ignore[no-redef]
    SyncStrategy: type[object] | None = None  # type: ignore[no-redef]

try:
    Cache, Storage, Models = import_adapter()
except Exception:
    Cache = Storage = Models = None


class ComponentNotFound(Exception):
    pass


class ComponentCompilationError(Exception):
    pass


class HTMYComponentRegistry:
    def __init__(
        self,
        searchpaths: list[AsyncPath] | None = None,
        cache: t.Any = None,
        storage: t.Any = None,
    ) -> None:
        self.searchpaths = searchpaths or []
        self.cache = cache
        self.storage = storage
        self._component_cache: dict[str, t.Any] = {}
        self._source_cache: dict[str, str] = {}

    @staticmethod
    def get_cache_key(component_path: AsyncPath, cache_type: str = "source") -> str:
        return f"htmy_component_{cache_type}:{component_path}"

    @staticmethod
    def get_storage_path(component_path: AsyncPath) -> AsyncPath:
        return component_path

    async def discover_components(self) -> dict[str, AsyncPath]:
        components = {}
        for search_path in self.searchpaths:
            if not await search_path.exists():
                continue
            async for component_file in search_path.rglob("*.py"):
                if component_file.name == "__init__.py":
                    continue
                component_name = component_file.stem
                components[component_name] = component_file

        return components

    async def _cache_component_source(
        self, component_path: AsyncPath, source: str
    ) -> None:
        if self.cache is not None:
            cache_key = self.get_cache_key(component_path)
            await self.cache.set(cache_key, source.encode())

    async def _cache_component_bytecode(
        self, component_path: AsyncPath, bytecode: bytes
    ) -> None:
        if self.cache is not None:
            cache_key = self.get_cache_key(component_path, "bytecode")
            await self.cache.set(cache_key, bytecode)

    async def _get_cached_source(self, component_path: AsyncPath) -> str | None:
        if self.cache is not None:
            cache_key = self.get_cache_key(component_path)
            cached = await self.cache.get(cache_key)
            if cached:
                return t.cast(str, cached.decode())
        return None

    async def _get_cached_bytecode(self, component_path: AsyncPath) -> bytes | None:
        if self.cache is not None:
            cache_key = self.get_cache_key(component_path, "bytecode")
            result = await self.cache.get(cache_key)
            return result  # type: ignore[no-any-return]
        return None

    async def _sync_component_file(
        self,
        path: AsyncPath,
        storage_path: AsyncPath,
    ) -> tuple[str, int]:
        if sync_templates is None or SyncDirection is None or SyncStrategy is None:
            return await self._sync_from_storage_fallback(path, storage_path)

        try:
            strategy = SyncStrategy(backup_on_conflict=False)
            component_paths = [path]
            result = await sync_templates(
                template_paths=component_paths,
                strategy=strategy,
            )

            source = await path.read_text()
            local_stat = await path.stat()
            local_mtime = int(local_stat.st_mtime)

            debug(f"Component sync result: {result.sync_status} for {path}")
            return source, local_mtime

        except Exception as e:
            debug(f"Sync action failed for {path}: {e}, falling back to primitive sync")
            return await self._sync_from_storage_fallback(path, storage_path)

    async def _sync_from_storage_fallback(
        self,
        path: AsyncPath,
        storage_path: AsyncPath,
    ) -> tuple[str, int]:
        local_stat = await path.stat()
        local_mtime = int(local_stat.st_mtime)

        if self.storage is not None:
            try:
                local_size = local_stat.st_size
                storage_stat = await self.storage.templates.stat(storage_path)
                storage_mtime = round(storage_stat.get("mtime", 0))
                storage_size = storage_stat.get("size", 0)

                if local_mtime < storage_mtime and local_size != storage_size:
                    resp = await self.storage.templates.open(storage_path)
                    await path.write_bytes(resp)
                    source = resp.decode()
                    return source, storage_mtime
            except Exception as e:
                debug(f"Storage fallback failed for {path}: {e}")

        source = await path.read_text()
        return source, local_mtime

    async def get_component_source(self, component_name: str) -> tuple[str, AsyncPath]:
        components = await self.discover_components()
        if component_name not in components:
            raise ComponentNotFound(f"Component '{component_name}' not found")
        component_path = components[component_name]
        cache_key = str(component_path)
        if cache_key in self._source_cache:
            return self._source_cache[cache_key], component_path
        cached_source = await self._get_cached_source(component_path)
        if cached_source:
            self._source_cache[cache_key] = cached_source
            return cached_source, component_path
        storage_path = self.get_storage_path(component_path)
        source, _ = await self._sync_component_file(component_path, storage_path)
        self._source_cache[cache_key] = source
        await self._cache_component_source(component_path, source)

        return source, component_path

    async def get_component_class(self, component_name: str) -> t.Any:
        if component_name in self._component_cache:
            return self._component_cache[component_name]
        source, component_path = await self.get_component_source(component_name)
        cached_bytecode = await self._get_cached_bytecode(component_path)
        try:
            if cached_bytecode:
                try:
                    import pickle

                    component_class = pickle.loads(cached_bytecode)
                    self._component_cache[component_name] = component_class
                    return component_class
                except Exception as e:
                    debug(f"Failed to load cached bytecode for {component_name}: {e}")

            namespace: dict[str, t.Any] = {}
            compiled_code = compile(source, str(component_path), "exec")
            # nosec B102 - This exec is used for loading trusted HTMY component files
            # In a production environment, these files should be validated/sanitized
            exec(compiled_code, namespace)
            component_class = None
            for obj in namespace.values():
                if hasattr(obj, "htmy") and callable(getattr(obj, "htmy")):
                    component_class = obj
                    break
        except Exception as e:
            raise ComponentCompilationError(
                f"Failed to compile component '{component_name}': {e}"
            ) from e


class HTMYTemplatesSettings(TemplatesBaseSettings):
    searchpaths: list[str] = []
    cache_timeout: int = 300
    enable_bidirectional: bool = True
    debug_components: bool = False


class HTMYTemplates(TemplatesBase):
    def __init__(self, **kwargs: t.Any) -> None:
        super().__init__(**kwargs)
        self.htmy_registry: HTMYComponentRegistry | None = None
        self.component_searchpaths: list[AsyncPath] = []
        self.jinja_templates: t.Any = None

    async def get_component_searchpaths(self, app_adapter: t.Any) -> list[AsyncPath]:
        searchpaths = []
        if callable(root_path):
            base_root = AsyncPath(root_path())
        else:
            base_root = AsyncPath(root_path)
        debug(f"get_component_searchpaths: app_adapter={app_adapter}")
        if app_adapter:
            category = getattr(app_adapter, "category", "app")
            debug(f"get_component_searchpaths: using category={category}")
            template_paths = self.get_searchpath(
                app_adapter, base_root / "templates" / category
            )
            debug(f"get_component_searchpaths: template_paths={template_paths}")
            for template_path in template_paths:
                component_path = template_path / "components"
                searchpaths.append(component_path)
                debug(
                    f"get_component_searchpaths: added component_path={component_path}"
                )
        debug(f"get_component_searchpaths: final searchpaths={searchpaths}")
        return searchpaths

    async def _init_htmy_registry(self) -> None:
        if self.htmy_registry is not None:
            return
        app_adapter = get_adapter("app")
        if app_adapter is None:
            try:
                app_adapter = depends.get("app")
            except Exception:
                from types import SimpleNamespace

                app_adapter = SimpleNamespace(name="app", category="app")
        self.component_searchpaths = await self.get_component_searchpaths(app_adapter)
        self.htmy_registry = HTMYComponentRegistry(
            searchpaths=self.component_searchpaths,
            cache=self.cache,
            storage=self.storage,
        )

    async def clear_component_cache(self, component_name: str | None = None) -> None:
        if self.htmy_registry is None:
            return
        if component_name:
            self.htmy_registry._component_cache.pop(component_name, None)
            if self.cache:
                components = await self.htmy_registry.discover_components()
                if component_name in components:
                    component_path = components[component_name]
                    source_key = HTMYComponentRegistry.get_cache_key(component_path)
                    bytecode_key = HTMYComponentRegistry.get_cache_key(
                        component_path, "bytecode"
                    )
                    await self.cache.delete(source_key)
                    await self.cache.delete(bytecode_key)
            debug(f"HTMY component cache cleared for: {component_name}")
        else:
            self.htmy_registry._component_cache.clear()
            self.htmy_registry._source_cache.clear()
            if self.cache:
                with suppress(NotImplementedError, AttributeError):
                    await self.cache.clear("htmy_component_source")
                    await self.cache.clear("htmy_component_bytecode")
            debug("All HTMY component caches cleared")

    async def get_component_class(self, component_name: str) -> t.Any:
        if self.htmy_registry is None:
            await self._init_htmy_registry()

        if self.htmy_registry is not None:
            return await self.htmy_registry.get_component_class(component_name)
        raise ComponentNotFound(
            f"Component registry not initialized for '{component_name}'"
        )

    async def render_component(
        self,
        request: t.Any,
        component: str,
        context: dict[str, t.Any] | None = None,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        **kwargs: t.Any,
    ) -> HTMLResponse:
        if context is None:
            context = {}
        if headers is None:
            headers = {}

        if self.htmy_registry is None:
            await self._init_htmy_registry()

        if self.htmy_registry is None:
            raise ComponentNotFound(
                f"Component registry not initialized for '{component}'"
            )

        try:
            component_class = await self.htmy_registry.get_component_class(component)

            component_instance = component_class(**context, **kwargs)

            htmy_context = {
                "request": request,
                **context,
                "render_template": self._create_template_renderer(request),
                "render_block": self._create_block_renderer(request),
                "_template_system": "htmy",
                "_request": request,
            }

            if asyncio.iscoroutinefunction(component_instance.htmy):
                rendered_content = await component_instance.htmy(htmy_context)
            else:
                rendered_content = component_instance.htmy(htmy_context)

            html_content = str(rendered_content)

            return HTMLResponse(
                content=html_content,
                status_code=status_code,
                headers=headers,
            )

        except (ComponentNotFound, ComponentCompilationError) as e:
            return HTMLResponse(
                content=f"<html><body>Component {component} error: {e}</body></html>",
                status_code=404,
                headers=headers,
            )

    def _create_template_renderer(
        self, request: t.Any = None
    ) -> t.Callable[..., t.Any]:
        async def render_template(
            template_name: str,
            context: dict[str, t.Any] | None = None,
            inherit_context: bool = True,  # noqa: ARG001
            **kwargs: t.Any,
        ) -> str:
            if context is None:
                context = {}

            template_context = {**context, **kwargs}

            if self.jinja_templates and hasattr(self.jinja_templates, "app"):
                try:
                    template = self.jinja_templates.app.get_template(template_name)
                    if asyncio.iscoroutinefunction(template.render):
                        rendered = await template.render(template_context)
                    else:
                        rendered = template.render(template_context)
                    return rendered  # type: ignore[no-any-return]
                except Exception as e:
                    debug(
                        f"Failed to render template '{template_name}' in HTMY component: {e}"
                    )
                    return f"<!-- Error rendering template '{template_name}': {e} -->"
            else:
                debug(
                    f"No Jinja2 adapter available to render template '{template_name}' in HTMY component"
                )
                return f"<!-- No template renderer available for '{template_name}' -->"

        return render_template

    def _create_block_renderer(self, request: t.Any = None) -> t.Callable[..., t.Any]:
        async def render_block(
            block_name: str, context: dict[str, t.Any] | None = None, **kwargs: t.Any
        ) -> str:
            if context is None:
                context = {}

            block_context = {**context, **kwargs}

            if (
                self.jinja_templates
                and hasattr(self.jinja_templates, "app")
                and hasattr(self.jinja_templates.app, "render_block")
            ):
                try:
                    if asyncio.iscoroutinefunction(
                        self.jinja_templates.app.render_block
                    ):
                        rendered = await self.jinja_templates.app.render_block(
                            block_name, block_context
                        )
                    else:
                        rendered = self.jinja_templates.app.render_block(
                            block_name, block_context
                        )
                    return rendered  # type: ignore[no-any-return]
                except Exception as e:
                    debug(
                        f"Failed to render block '{block_name}' in HTMY component: {e}"
                    )
                    return f"<!-- Error rendering block '{block_name}': {e} -->"
            else:
                debug(
                    f"No block renderer available for '{block_name}' in HTMY component"
                )
                return f"<!-- No block renderer available for '{block_name}' -->"

        return render_block

    async def init(self, cache: t.Any | None = None) -> None:
        if cache is None:
            try:
                cache = depends.get("cache")
            except Exception:
                cache = None
        self.cache = cache
        try:
            self.storage = depends.get("storage")
        except Exception:
            self.storage = None
        await self._init_htmy_registry()
        try:
            self.jinja_templates = depends.get("templates")
        except Exception:
            self.jinja_templates = None
        depends.set("htmy", self)
        debug("HTMY Templates adapter initialized")

    async def render_template(
        self,
        request: t.Any,
        template: str,
        context: dict[str, t.Any] | None = None,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> HTMLResponse:
        return await self.render_component(
            request=request,
            component=template,
            context=context,
            status_code=status_code,
            headers=headers,
        )


MODULE_ID = UUID("01937d86-e1f2-7890-abcd-ef1234567890")
MODULE_STATUS = AdapterStatus.STABLE if AdapterStatus is not None else None

with suppress(Exception):
    depends.set(HTMYTemplates)
