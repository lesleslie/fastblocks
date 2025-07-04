import asyncio
import re
import typing as t
from ast import literal_eval
from contextlib import suppress
from html.parser import HTMLParser
from importlib import import_module
from importlib.util import find_spec
from inspect import isclass
from pathlib import Path

from ...dependencies import get_acb_subset

Adapter, get_adapter, import_adapter, Config, debug, depends = get_acb_subset(
    "Adapter", "get_adapter", "import_adapter", "Config", "debug", "depends"
)
from anyio import Path as AsyncPath
from jinja2 import TemplateNotFound
from jinja2.ext import Extension, i18n, loopcontrols
from jinja2.ext import debug as jinja_debug
from jinja2_async_environment.bccache import AsyncRedisBytecodeCache
from jinja2_async_environment.loaders import AsyncBaseLoader, SourceType
from starlette_async_jinja import AsyncJinja2Templates

from ._base import TemplatesBase, TemplatesBaseSettings

try:
    Cache, Storage, Models = import_adapter()
except Exception:
    Cache = Storage = Models = None

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
        _ATTR_PATTERN_CACHE[attr] = re.compile(escaped_attr)
    return _ATTR_PATTERN_CACHE[attr]


def _apply_template_replacements(source: bytes, deployed: bool = False) -> bytes:
    for old_pattern, new_pattern in _TEMPLATE_REPLACEMENTS:
        source = source.replace(old_pattern, new_pattern)
    if deployed:
        source = source.replace(*_HTTP_TO_HTTPS)

    return source


class BaseTemplateLoader(AsyncBaseLoader):
    config: Config = depends()
    cache: Cache = depends()
    storage: Storage = depends()

    def get_supported_extensions(self) -> tuple[str, ...]:
        return ("html", "css", "js")

    async def _list_templates_for_extensions(
        self, extensions: tuple[str, ...]
    ) -> list[str]:
        found: set[str] = set()
        for searchpath in self.searchpath:
            for ext in extensions:
                async for p in searchpath.rglob(f"*.{ext}"):
                    found.add(str(p))
        return sorted(found)

    def _normalize_template(
        self, environment_or_template: t.Any, template: str | AsyncPath | None = None
    ) -> str | AsyncPath:
        if template is None:
            template = environment_or_template
        assert template is not None
        return template

    async def _find_template_path_parallel(
        self, template: str | AsyncPath
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
        self, template: str | AsyncPath
    ) -> tuple[AsyncPath, AsyncPath] | None:
        async def check_storage_path(
            searchpath: AsyncPath,
        ) -> tuple[AsyncPath, AsyncPath] | None:
            path = searchpath / template
            storage_path = Templates.get_storage_path(path)
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
        self, template: str | AsyncPath
    ) -> tuple[AsyncPath, AsyncPath, str] | None:
        async def check_cache_path(
            searchpath: AsyncPath,
        ) -> tuple[AsyncPath, AsyncPath, str] | None:
            path = searchpath / template if searchpath else AsyncPath(template)
            storage_path = Templates.get_storage_path(path)
            cache_key = Templates.get_cache_key(storage_path)
            if storage_path and await self.cache.exists(cache_key):
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
        self, environment_or_template: t.Any, template: str | AsyncPath | None = None
    ) -> tuple[
        str, str | None, t.Callable[[], bool] | t.Callable[[], t.Awaitable[bool]]
    ]: ...

    async def list_templates_async(self) -> list[str]: ...


class FileSystemLoader(BaseTemplateLoader):
    async def get_source_async(
        self, environment_or_template: t.Any, template: str | AsyncPath | None = None
    ) -> SourceType:
        template = self._normalize_template(environment_or_template, template)
        path = await self._find_template_path_parallel(template)
        if path is None:
            raise TemplateNotFound(str(template))
        storage_path = Templates.get_storage_path(path)
        fs_exists = await path.exists()
        storage_exists = await self.storage.templates.exists(storage_path)
        debug(fs_exists)
        debug(storage_exists)
        local_mtime = 0
        resp: bytes
        if storage_exists and fs_exists and (not self.config.deployed):
            debug(storage_path)
            local_stat = await path.stat()
            local_mtime = int(local_stat.st_mtime)
            local_size = local_stat.st_size
            storage_stat = await self.storage.templates.stat(storage_path)
            debug(storage_stat)
            storage_mtime = int(round(storage_stat.get("mtime")))
            storage_size = storage_stat.get("size")
            debug(local_mtime, storage_mtime)
            debug(local_size, storage_size)
            if local_mtime < storage_mtime and local_size != storage_size:
                resp = await self.storage.templates.open(storage_path)
                await path.write_bytes(resp)
            else:
                resp = await path.read_bytes()
                if local_size != storage_size:
                    await self.storage.templates.write(storage_path, resp)
        else:
            try:
                resp = await path.read_bytes()
                await self.storage.templates.write(storage_path, resp)
            except FileNotFoundError:
                raise TemplateNotFound(path.name)
        await self.cache.set(Templates.get_cache_key(storage_path), resp)

        async def uptodate() -> bool:
            return int((await path.stat()).st_mtime) == local_mtime

        return (resp.decode(), str(storage_path), uptodate)

    async def list_templates_async(self) -> list[str]:
        return await self._list_templates_for_extensions(
            self.get_supported_extensions()
        )


class StorageLoader(BaseTemplateLoader):
    async def get_source_async(
        self, environment_or_template: t.Any, template: str | AsyncPath | None = None
    ) -> tuple[str, str, t.Callable[[], t.Awaitable[bool]]]:
        template = self._normalize_template(environment_or_template, template)
        result = await self._find_storage_path_parallel(template)
        if result is None:
            raise TemplateNotFound(str(template))
        _, storage_path = result
        try:
            resp = await self.storage.templates.open(storage_path)
            await self.cache.set(Templates.get_cache_key(storage_path), resp)
            local_stat = await self.storage.templates.stat(storage_path)
            local_mtime = int(round(local_stat.get("mtime").timestamp()))

            async def uptodate() -> bool:
                debug("cloud uptodate")
                debug(local_mtime)
                storage_stat = await self.storage.templates.stat(storage_path)
                return int(round(storage_stat.get("mtime").timestamp())) == local_mtime

            return (resp.decode(), str(storage_path), uptodate)
        except (FileNotFoundError, AttributeError):
            raise TemplateNotFound(str(template))

    async def list_templates_async(self) -> list[str]:
        found: list[str] = []
        for searchpath in self.searchpath:
            with suppress(FileNotFoundError):
                paths = await self.storage.templates.list(
                    Templates.get_storage_path(searchpath)
                )
                found.extend(p for p in paths if p.endswith((".html", ".css", ".js")))
        found.sort()
        return found


class RedisLoader(BaseTemplateLoader):
    async def get_source_async(
        self, environment_or_template: t.Any, template: str | AsyncPath | None = None
    ) -> tuple[str, str | None, t.Callable[[], t.Awaitable[bool]]]:
        template = self._normalize_template(environment_or_template, template)
        result = await self._find_cache_path_parallel(template)
        if result is None:
            raise TemplateNotFound(str(template))
        path, _, cache_key = result
        resp = await self.cache.get(cache_key)
        if not resp:
            raise TemplateNotFound(path.name)

        async def uptodate() -> bool:
            return True

        return (resp.decode(), None, uptodate)

    async def list_templates_async(self) -> list[str]:
        found: list[str] = []
        for ext in ("html", "css", "js"):
            scan_result = await self.cache.scan(f"*.{ext}")
            if hasattr(scan_result, "__aiter__"):
                found.extend([k async for k in scan_result])
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
        self, package_name: str, path: str = "templates", adapter: str = "admin"
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
            else:
                import_module(package_name)
                spec = find_spec(package_name)
                if spec is None:
                    raise ImportError(f"Could not find package {package_name}")
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
            raise ValueError(
                f"The {package_name!r} package was not installed in a way that PackageLoader understands."
            )
        self._template_root = AsyncPath(template_root)

    async def get_source_async(
        self, environment_or_template: t.Any, template: str | AsyncPath | None = None
    ) -> tuple[str, str, t.Callable[[], t.Awaitable[bool]]]:
        if template is None:
            template = environment_or_template
        assert template is not None
        template_path: AsyncPath = AsyncPath(template)
        path = self._template_root / template_path
        if not await path.is_file():
            raise TemplateNotFound(template_path.name)
        debug(path)
        source = await path.read_bytes()
        mtime = (await path.stat()).st_mtime

        async def uptodate() -> bool:
            return await path.is_file() and (await path.stat()).st_mtime == mtime

        source = _apply_template_replacements(source, self.config.deployed)
        storage_path = Templates.get_storage_path(path)
        _storage_path: list[str] = list(storage_path.parts)
        _storage_path[0] = "_templates"
        _storage_path.insert(1, self._adapter)
        _storage_path.insert(2, getattr(self.config, self._adapter).style)
        storage_path = AsyncPath("/".join(_storage_path))
        cache_key = Templates.get_cache_key(storage_path)
        debug(cache_key)
        await self.cache.set(cache_key, source)
        return (source.decode(), path.name, uptodate)

    async def list_templates_async(self) -> list[str]:
        found: set[str] = set()
        for ext in ("html", "css", "js"):
            found.update([str(p) async for p in self._template_root.rglob(f"*.{ext}")])
        return sorted(found)


class ChoiceLoader(AsyncBaseLoader):
    loaders: list[AsyncBaseLoader | LoaderProtocol]

    def __init__(
        self,
        loaders: list[AsyncBaseLoader | LoaderProtocol],
        searchpath: AsyncPath | t.Sequence[AsyncPath] | None = None,
    ) -> None:
        super().__init__(searchpath or AsyncPath("templates"))
        self.loaders = loaders

    async def get_source_async(
        self, environment_or_template: t.Any, template: str | AsyncPath | None = None
    ) -> SourceType:
        if template is None:
            template = environment_or_template
        assert template is not None
        for loader in self.loaders:
            with suppress(TemplateNotFound):
                debug(loader.__class__.__name__, template)
                return await loader.get_source_async(template)
        raise TemplateNotFound(str(template))

    async def list_templates_async(self) -> list[str]:
        found: set[str] = set()
        for loader in self.loaders:
            templates = await loader.list_templates_async()
            for template in templates:
                debug(template, loader.__class__.__name__)
            found.update(templates)
        return sorted(found)


class TemplatesSettings(TemplatesBaseSettings):
    loader: str | None = None
    extensions: list[str] = []
    delimiters: dict[str, str] = dict(
        block_start_string="[%",
        block_end_string="%]",
        variable_start_string="[[",
        variable_end_string="]]",
        comment_start_string="[#",
        comment_end_string="#]",
    )
    globals: dict[str, t.Any] = {}
    context_processors: list[str] = []

    def __init__(self, **data: t.Any) -> None:
        super().__init__(**data)
        try:
            models = depends.get("models")
            self.globals["models"] = models
        except Exception:
            self.globals["models"] = None


class Templates(TemplatesBase):
    app: AsyncJinja2Templates | None = None

    def __init__(self, **kwargs: t.Any) -> None:
        super().__init__(**kwargs)
        self.filters: dict[str, t.Callable[..., t.Any]] = {}
        self.enabled_admin = get_adapter("admin")
        self.enabled_app = get_adapter("app")
        self._admin = None
        self._admin_initialized = False

    @property
    def admin(self) -> AsyncJinja2Templates | None:
        if not self._admin_initialized and self.enabled_admin:
            import asyncio

            loop = asyncio.get_event_loop()
            if hasattr(self, "_admin_cache") and hasattr(self, "admin_searchpaths"):
                self._admin = loop.run_until_complete(
                    self.init_envs(
                        self.admin_searchpaths, admin=True, cache=self._admin_cache
                    )
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
        loaders: list[AsyncBaseLoader] = [
            RedisLoader(searchpaths),
            StorageLoader(searchpaths),
        ]
        debug(searchpaths)
        file_loaders: list[AsyncBaseLoader | LoaderProtocol] = [
            FileSystemLoader(searchpaths)
        ]
        jinja_loaders: list[AsyncBaseLoader | LoaderProtocol] = loaders + file_loaders
        if not self.config.deployed and (not self.config.debug.production):
            jinja_loaders = file_loaders + loaders
        if self.enabled_admin and template_paths == self.admin_searchpaths:
            jinja_loaders.append(
                PackageLoader(self.enabled_admin.name, "templates", "admin")
            )
        debug(jinja_loaders)
        return ChoiceLoader(jinja_loaders)

    @depends.inject
    async def init_envs(
        self,
        template_paths: list[AsyncPath],
        admin: bool = False,
        cache: t.Any | None = None,
    ) -> AsyncJinja2Templates:
        _extensions: list[t.Any] = [loopcontrols, i18n, jinja_debug]
        _imported_extensions = [
            import_module(e) for e in self.config.templates.extensions
        ]
        for e in _imported_extensions:
            _extensions.extend(
                [
                    v
                    for v in vars(e).values()
                    if isclass(v)
                    and v.__name__ != "Extension"
                    and issubclass(v, Extension)
                ]
            )
        bytecode_cache = AsyncRedisBytecodeCache(prefix="bccache", client=cache)
        context_processors: list[t.Callable[..., t.Any]] = []
        for processor_path in self.config.templates.context_processors:
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
        elif self.config.templates.loader:
            templates.env.loader = literal_eval(self.config.templates.loader)
        for delimiter, value in self.config.templates.delimiters.items():
            setattr(templates.env, delimiter, value)
        templates.env.globals["config"] = self.config  # type: ignore[assignment]
        templates.env.globals["render_block"] = templates.render_block  # type: ignore[assignment]
        if admin:
            try:
                from sqladmin.helpers import (  # type: ignore[import-not-found,import-untyped]
                    get_object_identifier,
                )
            except ImportError:
                get_object_identifier = str
            templates.env.globals["min"] = min  # type: ignore[assignment]
            templates.env.globals["zip"] = zip  # type: ignore[assignment]
            templates.env.globals["admin"] = self  # type: ignore[assignment]
            templates.env.globals["is_list"] = lambda x: isinstance(x, list)  # type: ignore[assignment]
            templates.env.globals["get_object_identifier"] = get_object_identifier  # type: ignore[assignment]
        for k, v in self.config.templates.globals.items():
            templates.env.globals[k] = v  # type: ignore[assignment]
        return templates

    async def init(self, cache: t.Any | None = None) -> None:
        if cache is None:
            try:
                cache = depends.get("cache")
            except Exception:
                cache = None
        app_adapter = t.cast(Adapter, self.enabled_app)
        self.app_searchpaths = await self.get_searchpaths(app_adapter)
        self.app = await self.init_envs(self.app_searchpaths, cache=cache)
        self._admin = None
        self._admin_initialized = False
        if self.enabled_admin:
            self.admin_searchpaths = await self.get_searchpaths(self.enabled_admin)
            self._admin_cache = cache
        if self.app and self.app.env.loader and hasattr(self.app.env.loader, "loaders"):
            for loader in self.app.env.loader.loaders:
                self.logger.debug(f"{loader.__class__.__name__} initialized")
        if self.app and hasattr(self.app.env, "extensions"):
            for ext in self.app.env.extensions:
                self.logger.debug(f"{ext.split('.')[-1]} loaded")
        if getattr(self.config.debug, "templates", False):
            for namespace in ("templates", "_templates", "bccache", "template", "test"):
                await cache.clear(namespace)
            self.logger.debug("Templates cache cleared")

    @staticmethod
    def get_attr(html: str, attr: str) -> str | None:
        parser = HTMLParser()
        parser.feed(html)
        soup = parser.get_starttag_text()
        attr_pattern = _get_attr_pattern(attr)
        _attr = f"{attr}="
        for s in soup.split():
            if attr_pattern.search(s):
                attr_value = s.replace(_attr, "").strip('"')
                return attr_value
        return None

    def _add_filters(self, env: t.Any) -> None:
        if hasattr(self, "filters") and self.filters:
            for name, filter_func in self.filters.items():
                if hasattr(env, "add_filter"):
                    env.add_filter(filter_func, name)
                else:
                    env.filters[name] = filter_func

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
                name=template,
                context=context,
                status_code=status_code,
                headers=headers,
            )
        else:
            from starlette.responses import HTMLResponse

            return HTMLResponse(
                content=f"<html><body>Template {template} not found</body></html>",
                status_code=404,
                headers=headers,
            )

    def filter(
        self, name: str | None = None
    ) -> t.Callable[[t.Callable[..., t.Any]], t.Callable[..., t.Any]]:
        def decorator(f: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:
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
            self.config.templates.extensions,
        )
        _imported_extensions = [import_module(e) for e in extensions_list]
        for e in _imported_extensions:
            _extensions.extend(
                [
                    v
                    for v in vars(e).values()
                    if isclass(v)
                    and v.__name__ != "Extension"
                    and issubclass(v, Extension)
                ]
            )
        return _extensions


with suppress(Exception):
    depends.set(Templates)
