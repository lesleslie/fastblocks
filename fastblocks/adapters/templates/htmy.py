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
from acb.depends import Inject, depends

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
from typing import TYPE_CHECKING, Any
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
from ._htmy_components import (
    AdvancedHTMYComponentRegistry,
    ComponentLifecycleManager,
    ComponentMetadata,
    ComponentRenderError,
    ComponentStatus,
    ComponentType,
)

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
            return t.cast(Response, result)
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

        # Try to load from cached bytecode first
        if cached_bytecode:
            component_class = await self._load_from_cached_bytecode(
                cached_bytecode, source, component_path, component_name
            )
            if component_class:
                return component_class

        # Otherwise, load from source
        return await self._load_from_source(source, component_path, component_name)

    async def _load_from_cached_bytecode(
        self, cached_bytecode, source, component_path, component_name
    ):
        """Attempt to load component class from cached bytecode."""
        try:
            # Instead of using pickle, we'll compile the source directly
            # Pickle is a security risk as mentioned in the semgrep error
            compile(source, str(component_path), "exec")
            # Create a module-like namespace to execute the compiled code
            import importlib.util
            import os
            import tempfile

            # Create a temporary module to safely load the component
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(source)
                temp_module_path = f.name

            try:
                spec = importlib.util.spec_from_file_location(
                    component_path.stem, temp_module_path
                )
                if spec is None or spec.loader is None:
                    raise ComponentCompilationError(
                        f"Could not load module from {component_path}"
                    )

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                component_class = None
                for obj in vars(module).values():
                    if hasattr(obj, "htmy") and callable(getattr(obj, "htmy")):
                        component_class = obj
                        break
            finally:
                # Clean up the temporary file
                os.unlink(temp_module_path)

            # Cache the compiled form instead of pickle-able bytecode
            self._component_cache[component_name] = component_class
            return component_class
        except Exception as e:
            debug(f"Failed to load cached bytecode for {component_name}: {e}")
            return None

    async def _load_from_source(self, source, component_path, component_name):
        """Load component class from source file."""
        try:
            # Import and analyze component safely
            import importlib.util
            import os
            import tempfile

            # Create a temporary module to safely load the component
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(source)
                temp_module_path = f.name

            try:
                spec = importlib.util.spec_from_file_location(
                    component_path.stem, temp_module_path
                )
                if spec is None or spec.loader is None:
                    raise ComponentCompilationError(
                        f"Could not load module from {component_path}"
                    )

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                component_class = None
                for obj in vars(module).values():
                    if hasattr(obj, "htmy") and callable(getattr(obj, "htmy")):
                        component_class = obj
                        break
            finally:
                # Clean up the temporary file
                os.unlink(temp_module_path)

            self._component_cache[component_name] = component_class
            return component_class
        except Exception as e:
            raise ComponentCompilationError(
                f"Failed to compile component '{component_name}': {e}"
            ) from e


class HTMYTemplatesSettings(TemplatesBaseSettings):
    searchpaths: list[str] = []
    cache_timeout: int = 300
    enable_bidirectional: bool = True
    debug_components: bool = False
    enable_hot_reload: bool = True
    enable_lifecycle_hooks: bool = True
    enable_component_validation: bool = True
    enable_advanced_registry: bool = True


class HTMYTemplates(TemplatesBase):
    def __init__(self, **kwargs: t.Any) -> None:
        super().__init__(**kwargs)
        self.htmy_registry: HTMYComponentRegistry | None = None
        self.advanced_registry: AdvancedHTMYComponentRegistry | None = None
        self.component_searchpaths: list[AsyncPath] = []
        self.jinja_templates: t.Any = None
        self.settings = HTMYTemplatesSettings(**kwargs)

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
        if self.htmy_registry is not None and self.advanced_registry is not None:
            return

        app_adapter = get_adapter("app")
        if app_adapter is None:
            try:
                app_adapter = depends.get("app")
            except Exception:
                from types import SimpleNamespace

                app_adapter = SimpleNamespace(name="app", category="app")

        self.component_searchpaths = await self.get_component_searchpaths(app_adapter)

        # Initialize advanced registry if enabled
        if self.settings.enable_advanced_registry:
            self.advanced_registry = AdvancedHTMYComponentRegistry(
                searchpaths=self.component_searchpaths,
                cache=self.cache,
                storage=self.storage,
            )

            # Configure hot reload
            if self.settings.enable_hot_reload:
                self.advanced_registry.enable_hot_reload()

        # Keep legacy registry for backward compatibility
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

    async def render_component_advanced(
        self,
        request: t.Any,
        component: str,
        context: dict[str, t.Any] | None = None,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        **kwargs: t.Any,
    ) -> HTMLResponse:
        """Render component using advanced registry with lifecycle management."""
        if context is None:
            context = {}
        if headers is None:
            headers = {}

        if self.advanced_registry is None:
            await self._init_htmy_registry()

        if self.advanced_registry is None:
            raise ComponentRenderError(
                f"Advanced registry not initialized for '{component}'"
            )

        try:
            # Add kwargs to context
            enhanced_context = context | kwargs

            rendered_content = (
                await self.advanced_registry.render_component_with_lifecycle(
                    component, enhanced_context, request
                )
            )

            return HTMLResponse(
                content=rendered_content,
                status_code=status_code,
                headers=headers,
            )

        except Exception as e:
            error_content = (
                f"<html><body>Component {component} error: {e}</body></html>"
            )
            if self.settings.debug_components:
                import traceback

                error_content = f"<html><body><h3>Component {component} error:</h3><pre>{traceback.format_exc()}</pre></body></html>"

            return HTMLResponse(
                content=error_content,
                status_code=500,
                headers=headers,
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

        # Use advanced registry if available and enabled
        if (
            self.settings.enable_advanced_registry
            and self.advanced_registry is not None
        ):
            return await self.render_component_advanced(
                request, component, context, status_code, headers, **kwargs
            )

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

            template_context = context | kwargs

            if self.jinja_templates and hasattr(self.jinja_templates, "app"):
                try:
                    template = self.jinja_templates.app.get_template(template_name)
                    if asyncio.iscoroutinefunction(template.render):
                        rendered = await template.render(template_context)
                    else:
                        rendered = template.render(template_context)
                    return t.cast(str, rendered)
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

    async def discover_components(self) -> dict[str, ComponentMetadata]:
        """Discover all components and return metadata."""
        if self.advanced_registry is None:
            await self._init_htmy_registry()

        if self.advanced_registry is not None:
            return await self.advanced_registry.discover_components()

        # Fallback to basic discovery
        components = {}
        if self.htmy_registry is not None:
            discovered = await self.htmy_registry.discover_components()
            for name, path in discovered.items():
                components[name] = ComponentMetadata(
                    name=name,
                    path=path,
                    type=ComponentType.BASIC,
                    status=ComponentStatus.DISCOVERED,
                )
        return components

    async def scaffold_component(
        self,
        name: str,
        component_type: ComponentType = ComponentType.DATACLASS,
        props: dict[str, type] | None = None,
        htmx_enabled: bool = False,
        endpoint: str = "",
        trigger: str = "click",
        target: str = "#content",
        children: list[str] | None = None,
        target_path: AsyncPath | None = None,
    ) -> AsyncPath:
        """Scaffold a new component."""
        if self.advanced_registry is None:
            await self._init_htmy_registry()

        if self.advanced_registry is None:
            raise ComponentRenderError(
                "Advanced registry not available for scaffolding"
            )

        kwargs: dict[str, Any] = {}
        if props:
            kwargs["props"] = props
        if htmx_enabled:
            kwargs["htmx_enabled"] = True
        if endpoint:
            kwargs["endpoint"] = endpoint
            kwargs["trigger"] = trigger
            kwargs["target"] = target
        if children:
            kwargs["children"] = children

        return await self.advanced_registry.scaffold_component(
            name, component_type, target_path, **kwargs
        )

    async def validate_component(self, component_name: str) -> ComponentMetadata:
        """Validate a specific component."""
        components = await self.discover_components()
        if component_name not in components:
            raise ComponentNotFound(f"Component '{component_name}' not found")

        return components[component_name]

    def get_lifecycle_manager(self) -> ComponentLifecycleManager | None:
        """Get the component lifecycle manager."""
        if self.advanced_registry is not None:
            return self.advanced_registry.lifecycle_manager
        return None

    def register_lifecycle_hook(
        self, event: str, callback: t.Callable[..., Any]
    ) -> None:
        """Register a lifecycle hook."""
        lifecycle_manager = self.get_lifecycle_manager()
        if lifecycle_manager is not None:
            lifecycle_manager.register_hook(event, callback)

    def _create_block_renderer(self, request: t.Any = None) -> t.Callable[..., t.Any]:
        async def render_block(
            block_name: str, context: dict[str, t.Any] | None = None, **kwargs: t.Any
        ) -> str:
            if context is None:
                context = {}

            block_context = context | kwargs

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
                    return t.cast(str, rendered)
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

TemplatesSettings = HTMYTemplatesSettings
Templates = HTMYTemplates

with suppress(Exception):
    depends.set(Templates, "htmy")

__all__ = ["Templates", "TemplatesSettings", "HTMYTemplatesSettings", "HTMYTemplates"]
