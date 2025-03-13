import typing as t
from ast import literal_eval
from contextlib import suppress
from html.parser import HTMLParser
from importlib import import_module
from importlib.util import find_spec
from inspect import isclass
from pathlib import Path
from re import search

from acb.adapters import get_adapter, import_adapter
from acb.config import Config
from acb.debug import debug
from acb.depends import depends
from aiopath import AsyncPath
from jinja2 import TemplateNotFound
from jinja2.ext import Extension, i18n, loopcontrols
from jinja2.ext import debug as jinja_debug
from jinja2_async_environment.bccache import AsyncRedisBytecodeCache
from jinja2_async_environment.loaders import AsyncBaseLoader, SourceType
from starlette_async_jinja import AsyncJinja2Templates

from ._base import TemplatesBase, TemplatesBaseSettings

Cache, Storage, Models = import_adapter()  # type: ignore


class FileSystemLoader(AsyncBaseLoader):
    config: Config = depends()
    cache: Cache = depends()
    storage: Storage = depends()

    async def get_source_async(self, template: str | AsyncPath) -> SourceType:
        debug("File Loader")
        path: t.Optional[AsyncPath] = None
        for searchpath in self.searchpath:
            path = searchpath / template
            debug(path)
            if await path.is_file():
                break

        if path is None:
            raise TemplateNotFound(str(template))

        storage_path = Templates.get_storage_path(path)
        fs_exists = await path.exists()
        storage_exists = await self.storage.templates.exists(storage_path)
        debug(fs_exists)
        debug(storage_exists)
        local_mtime = 0
        resp: bytes

        if storage_exists and fs_exists and not self.config.deployed:
            debug(storage_path)
            local_stat = await path.stat()
            local_mtime = int(local_stat.st_mtime)
            local_size = local_stat.st_size
            cloud_stat = await self.storage.templates.stat(storage_path)
            cloud_mtime = int(round(cloud_stat.get("mtime").timestamp()))
            cloud_size = cloud_stat.get("size")
            debug(local_mtime, cloud_mtime)
            debug(local_size, cloud_size)
            if local_mtime < cloud_mtime and local_size != cloud_size:
                resp = await self.storage.templates.open(storage_path)
                await path.write_bytes(resp)
            else:
                resp = await path.read_bytes()
                if local_size != cloud_size:
                    await self.storage.templates.write(storage_path, resp)
        else:
            try:
                resp = await path.read_bytes()
                if resp and not storage_exists:
                    await self.storage.templates.write(storage_path, resp)
            except FileNotFoundError:
                raise TemplateNotFound(path.name)

        await self.cache.set(Templates.get_cache_key(storage_path), resp)

        path_final = path  # Create a final variable for the closure

        async def uptodate() -> bool:
            return int((await path_final.stat()).st_mtime) == local_mtime

        return resp.decode(), str(storage_path), uptodate

    async def list_templates_async(self) -> list[str]:
        found: set[str] = set()
        for searchpath in self.searchpath:
            for ext in ("html", "css", "js"):
                found.update([str(p) async for p in searchpath.rglob(f"*.{ext}")])
        return sorted(found)


class CloudLoader(AsyncBaseLoader):
    cache: Cache = depends()
    storage: Storage = depends()

    async def get_source_async(
        self, template: str | AsyncPath
    ) -> tuple[str, str, t.Callable[[], t.Awaitable[bool]]]:
        debug("Cloud Loader")
        path: t.Optional[AsyncPath] = None
        storage_path: t.Optional[AsyncPath] = None

        for searchpath in self.searchpath:
            path = searchpath / template
            storage_path = Templates.get_storage_path(path)  # type: ignore
            debug(storage_path)
            if storage_path and await self.storage.templates.exists(storage_path):
                break

        if path is None or storage_path is None:
            raise TemplateNotFound(str(template))

        try:
            resp = await self.storage.templates.open(storage_path)
            await self.cache.set(Templates.get_cache_key(storage_path), resp)
            local_stat = await self.storage.templates.stat(storage_path)
            local_mtime = int(round(local_stat.get("mtime").timestamp()))

            storage_path_final = storage_path  # Create a final variable for the closure

            async def uptodate() -> bool:
                debug("cloud uptodate")
                debug(local_mtime)
                cloud_stat = await self.storage.templates.stat(storage_path_final)
                return int(round(cloud_stat.get("mtime").timestamp())) == local_mtime

            return resp.decode(), str(storage_path), uptodate
        except (FileNotFoundError, AttributeError):
            if path is not None:
                raise TemplateNotFound(path.name)
            raise TemplateNotFound(str(template))

    async def list_templates_async(self) -> list[str]:
        found: list[str] = []
        for searchpath in self.searchpath:
            with suppress(FileNotFoundError):
                paths = await self.storage.templates.list(
                    Templates.get_storage_path(searchpath)  # type: ignore
                )
                found.extend([p for p in paths if p.endswith((".html", ".css", ".js"))])
        found.sort()
        return found


class RedisLoader(AsyncBaseLoader):
    cache: Cache = depends()
    storage: Storage = depends()

    async def get_source_async(
        self, template: str | AsyncPath
    ) -> tuple[str, t.Optional[str], t.Callable[[], t.Awaitable[bool]]]:
        debug("Redis Loader")
        path: t.Optional[AsyncPath] = None
        cache_key: t.Optional[str] = None
        storage_path: t.Optional[AsyncPath] = None

        for searchpath in self.searchpath:
            path = searchpath / template if searchpath else AsyncPath(template)
            storage_path = Templates.get_storage_path(path)  # type: ignore
            cache_key = Templates.get_cache_key(storage_path)
            debug(storage_path)
            debug(cache_key)
            if storage_path and await self.cache.exists(cache_key):
                debug(path)
                break

        if path is None or cache_key is None or storage_path is None:
            raise TemplateNotFound(str(template))

        resp = await self.cache.get(cache_key)
        if not resp:
            raise TemplateNotFound(path.name)

        async def uptodate() -> bool:
            return True

        return resp.decode(), None, uptodate

    async def list_templates_async(self) -> list[str]:
        found: list[str] = []
        for ext in ("html", "css", "js"):
            found.extend([k async for k in self.cache.scan(f"*.{ext}")])
        found.sort()
        return found


class PackageLoader(AsyncBaseLoader):
    config: Config = depends()
    cache: Cache = depends()
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
        import_module(package_name)
        spec = find_spec(package_name)
        if spec is None:
            raise ImportError(f"Could not find package {package_name}")

        loader = spec.loader
        self._loader = loader
        template_root = None
        roots: list[Path] = []

        if spec.submodule_search_locations:
            roots.extend([Path(s) for s in spec.submodule_search_locations])
        elif spec.origin is not None:
            roots.append(Path(spec.origin))

        for root in roots:
            root = root / path
            if root.is_dir():
                template_root = root
                break

        if template_root is None:
            raise ValueError(
                f"The {package_name!r} package was not installed in a"
                " way that PackageLoader understands."
            )

        self._template_root = AsyncPath(template_root)
        self._adapter = adapter

    async def get_source_async(
        self, template: str | AsyncPath
    ) -> tuple[str, str, t.Callable[[], t.Awaitable[bool]]]:
        debug("Package Loader")
        template = AsyncPath(template)
        path = self._template_root / template
        if not await path.is_file():
            raise TemplateNotFound(template.name)

        debug(path)
        source = await path.read_bytes()
        mtime = (await path.stat()).st_mtime

        path_final = path  # Create a final variable for the closure

        async def uptodate() -> bool:
            return (
                await path_final.is_file()
                and (await path_final.stat()).st_mtime == mtime
            )

        replace = [("{{", "[["), ("}}", "]]"), ("{%", "[%"), ("%}", "%]")]
        if self.config.deployed:
            replace.append(("http://", "https://"))

        for r in replace:
            source = source.replace(
                bytes(r[0], encoding="utf8"), bytes(r[1], encoding="utf8")
            )

        storage_path = Templates.get_storage_path(path)  # type: ignore
        _storage_path: list[str] = list(storage_path.parts)
        _storage_path[0] = "_templates"
        _storage_path.insert(1, self._adapter)
        _storage_path.insert(2, getattr(self.config, self._adapter).style)
        storage_path = AsyncPath("/".join(_storage_path))
        cache_key = Templates.get_cache_key((storage_path))
        debug(cache_key)
        await self.cache.set(cache_key, source)

        return source.decode(), path.name, uptodate

    async def list_templates_async(self) -> list[str]:
        found: set[str] = set()
        for ext in ("html", "css", "js"):
            found.update([str(p) async for p in self._template_root.rglob(f"*.{ext}")])
        return sorted(found)


class ChoiceLoader(AsyncBaseLoader):
    loaders: list[AsyncBaseLoader]

    def __init__(
        self,
        loaders: list[AsyncBaseLoader],
        searchpath: t.Optional[AsyncPath | t.Sequence[AsyncPath]] = None,
    ) -> None:
        super().__init__(searchpath or AsyncPath("templates"))
        self.loaders = loaders

    async def get_source_async(self, template: str | AsyncPath) -> SourceType:
        for loader in self.loaders:
            with suppress(TemplateNotFound):
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
    loader: t.Optional[str] = None
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

    @depends.inject
    def __init__(
        self,
        models: Models = depends(),
        **data: t.Any,
    ) -> None:
        super().__init__(**data)
        self.globals["models"] = models


class Templates(TemplatesBase):
    app: t.Optional[AsyncJinja2Templates] = None
    admin: t.Optional[AsyncJinja2Templates] = None
    enabled_admin: t.Any = get_adapter("admin")
    enabled_app: t.Any = get_adapter("app")

    def get_loader(self, template_paths: list[AsyncPath]) -> ChoiceLoader:
        searchpaths: list[AsyncPath] = []
        for path in template_paths:
            searchpaths.extend([path, path / "blocks"])

        loaders: list[AsyncBaseLoader] = [
            RedisLoader(searchpaths),
            CloudLoader(searchpaths),
        ]

        debug(searchpaths)
        file_loaders: list[AsyncBaseLoader] = [FileSystemLoader(searchpaths)]

        # In development, prioritize file system loaders for easier template editing
        jinja_loaders: list[AsyncBaseLoader] = loaders + file_loaders
        if not self.config.deployed and not self.config.debug.production:
            jinja_loaders = file_loaders + loaders

        # Add package loader for admin templates if needed
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
        cache: Cache = depends(),
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
        bytecode_cache = AsyncRedisBytecodeCache(
            prefix="bccache",
            client=cache,
        )
        context_processors: list[t.Callable[..., t.Any]] = []
        for processor_path in self.config.templates.context_processors:
            module_path, func_name = processor_path.rsplit(".", 1)
            module = import_module(module_path)
            processor = getattr(module, func_name)
            context_processors.append(processor)
        env_configs = dict(
            extensions=_extensions,
            bytecode_cache=bytecode_cache,
            context_processors=context_processors,
            enable_async=True,
        )
        templates = AsyncJinja2Templates(
            AsyncPath("templates"), context_processors=None, **env_configs
        )
        loader = self.get_loader(template_paths)
        if loader:
            templates.env.loader = loader
        elif self.config.templates.loader:
            templates.env.loader = literal_eval(self.config.templates.loader)
        for delimiter, value in self.config.templates.delimiters.items():
            setattr(templates.env, delimiter, value)
        templates.env.globals["config"] = self.config  # type: ignore
        templates.env.globals["render_block"] = templates.render_block  # type: ignore
        if self.enabled_admin:
            from sqladmin.helpers import get_object_identifier  # type: ignore

            templates.env.globals.update(  # type: ignore
                dict(  # type: ignore
                    min=min,
                    zip=zip,
                    admin=self,
                    is_list=lambda x: isinstance(x, list),
                    get_object_identifier=get_object_identifier,
                )
            )

        for k, v in self.config.templates.globals.items():
            templates.env.globals[k] = v

        return templates

    @depends.inject
    async def init(self, cache: Cache = depends()) -> None:
        self.app_searchpaths = await self.get_searchpaths(self.enabled_app)
        self.app = await self.init_envs(self.app_searchpaths)
        if self.enabled_admin:
            self.admin_searchpaths = await self.get_searchpaths(self.enabled_admin)
            self.admin = await self.init_envs(self.admin_searchpaths)
        if self.app and self.app.env.loader and hasattr(self.app.env.loader, "loaders"):
            for loader in self.app.env.loader.loaders:
                self.logger.debug(f"{loader.__class__.__name__} initialized")
        if self.app and hasattr(self.app.env, "extensions"):
            for ext in self.app.env.extensions:
                self.logger.debug(f"{ext.split('.')[-1]} loaded")

        # Clear template cache in debug mode
        if self.config.debug.templates:
            for namespace in ("templates", "_templates", "bccache"):
                await cache.clear(namespace)
            self.logger.debug("Templates cache cleared")

    @staticmethod
    def get_attr(html: str, attr: str) -> t.Optional[str]:
        parser = HTMLParser()
        parser.feed(html)
        soup = parser.get_starttag_text()
        _attr = f"{attr}="
        for s in soup.split():
            if search(_attr, s):
                attr_value = s.replace(_attr, "").strip('"')
                return attr_value
        return None

    def filter(
        self, name: t.Optional[str] = None
    ) -> t.Callable[[t.Callable[..., t.Any]], t.Callable[..., t.Any]]:
        def decorator(f: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:
            if self.app and hasattr(self.app.env, "filters"):
                self.app.env.filters[name or f.__name__] = f
            if self.admin and hasattr(self.admin.env, "filters"):
                self.admin.env.filters[name or f.__name__] = f
            return f

        return decorator


depends.set(Templates)
