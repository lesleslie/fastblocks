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
from jinja2_async_environment.loaders import AsyncBaseLoader
from starlette_async_jinja import AsyncJinja2Templates
from ._base import TemplatesBase, TemplatesBaseSettings

Logger, Cache, Storage, Models = import_adapter()


class FileSystemLoader(AsyncBaseLoader):
    config: Config = depends()
    cache: Cache = depends()  # type: ignore
    storage: Storage = depends()  # type: ignore

    async def get_source(
        self, template: AsyncPath
    ) -> tuple[t.Any, t.Any, t.Callable[[], t.Coroutine[t.Any, t.Any, bool]]]:
        debug("File Loader")
        path = None
        for searchpath in self.searchpath:  # type: ignore
            path = searchpath / template
            debug(path)
            if await path.is_file():
                break
        storage_path = Templates.get_storage_path(path)  # type: ignore
        fs_exists = await path.exists()
        storage_exists = await self.storage.templates.exists(storage_path)
        debug(fs_exists)
        debug(storage_exists)
        local_mtime = 0
        if storage_exists and fs_exists and not self.config.deployed:
            debug(storage_path)
            local_stat = await path.stat()
            local_mtime = int(local_stat.st_mtime)
            local_size = local_stat.st_size
            # local_hash = await hash.crc32c(path)
            cloud_stat = await self.storage.templates.stat(storage_path)
            cloud_mtime = int(round(cloud_stat.get("mtime").timestamp()))
            cloud_size = cloud_stat.get("size")
            # cloud_hash = await hash.crc32c(resp)
            debug(local_mtime, cloud_mtime)
            debug(local_size, cloud_size)
            # debug(local_hash, cloud_hash)
            # if local_hash != cloud_hash:
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

        async def uptodate() -> bool:
            return int((await path.stat()).st_mtime) == local_mtime

        return resp.decode(), str(storage_path), uptodate

    async def list_templates(self) -> list[str]:
        found = set()
        for searchpath in self.searchpath:  # type: ignore
            paths = searchpath.rglob("*.html") + searchpath.rglob("*.css")
            found.update([str(p) async for p in paths])
        return sorted(found)


class CloudLoader(AsyncBaseLoader):
    cache: Cache = depends()  # type: ignore
    storage: Storage = depends()  # type: ignore

    async def get_source(
        self, template: AsyncPath
    ) -> tuple[t.Any, t.Any, t.Callable[[], t.Coroutine[t.Any, t.Any, bool]]]:
        debug("Cloud Loader")
        path = None
        storage_path = None
        for searchpath in self.searchpath:  # type: ignore
            path = searchpath / template
            storage_path = Templates.get_storage_path(path)
            debug(storage_path)
            if await self.storage.templates.exists(storage_path):
                break
        try:
            resp = await self.storage.templates.open(storage_path)
            await self.cache.set(Templates.get_cache_key(storage_path), resp)  # type: ignore
            local_stat = await self.storage.templates.stat(storage_path)
            local_mtime = int(round(local_stat.get("mtime").timestamp()))

            async def uptodate() -> bool:
                debug("cloud uptodate")
                debug(local_mtime)
                cloud_stat = await self.storage.templates.stat(storage_path)
                return int(round(cloud_stat.get("mtime").timestamp())) == local_mtime

            return resp.decode(), str(storage_path), uptodate
        except (FileNotFoundError, AttributeError):
            raise TemplateNotFound(path.name)

    async def list_templates(self) -> list[str]:
        found = []
        for searchpath in self.searchpath:  # type: ignore
            with suppress(FileNotFoundError):
                paths = await self.storage.templates.list(
                    Templates.get_storage_path(searchpath)
                )
                found.extend(
                    [p for p in paths if p.endswith(".html") or p.endswith(".css")]
                )
        found.sort()
        return found


class RedisLoader(AsyncBaseLoader):
    cache: Cache = depends()  # type: ignore
    storage: Storage = depends()  # type: ignore

    async def get_source(
        self, template: AsyncPath
    ) -> tuple[t.Any, t.Any, t.Callable[[], t.Coroutine[t.Any, t.Any, bool]]]:
        debug("Redis Loader")
        path = None
        cache_key = None
        for searchpath in self.searchpath:  # type: ignore
            path = searchpath / template if searchpath else template
            storage_path = Templates.get_storage_path(path)
            cache_key = Templates.get_cache_key(storage_path)
            debug(storage_path)
            debug(cache_key)
            if await self.cache.exists(cache_key):
                debug(path)
                break
        resp = await self.cache.get(cache_key)
        if not resp:
            raise TemplateNotFound(path.name)

        async def uptodate() -> bool:
            return True

        return resp.decode(), None, uptodate

    async def list_templates(self) -> list[str]:
        found = []
        for ext in ("html", "css"):
            found.extend([k async for k in self.cache.scan(f"*.{ext}")])
        found.sort()
        return found


class PackageLoader(AsyncBaseLoader):
    config: Config = depends()
    cache: Cache = depends()  # type: ignore

    def __init__(
        self, package_name: str, path: str = "templates", adapter: str = "admin"
    ) -> None:
        self.package_path = Path(package_name)
        self.path = self.package_path / path
        super().__init__(AsyncPath(self.path))
        self.package_name = package_name
        import_module(package_name)
        spec = find_spec(package_name)
        loader = spec.loader
        self._loader = loader
        self._archive = None
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

    async def get_source(
        self, template: AsyncPath
    ) -> tuple[t.Any, t.Any, t.Callable[[], t.Coroutine[t.Any, t.Any, bool]]]:
        debug("Package Loader")
        path = self._template_root / template
        if not await path.is_file():
            raise TemplateNotFound(template.name)

        debug(path)
        source = await path.read_bytes()
        mtime = (await path.stat()).st_mtime

        async def uptodate() -> bool:
            return await path.is_file() and (await path.stat()).st_mtime == mtime

        replace = [("{{", "[["), ("}}", "]]"), ("{%", "[%"), ("%}", "%]")]
        if self.config.deployed:
            replace.append(("http://", "https://"))
        for r in replace:
            source = source.replace(
                bytes(r[0], encoding="utf8"), bytes(r[1], encoding="utf8")
            )
        storage_path = Templates.get_storage_path(path)
        _storage_path = list(storage_path.parts)
        _storage_path[0] = "_templates"
        _storage_path.insert(1, self._adapter)
        _storage_path.insert(2, getattr(self.config, self._adapter).style)
        storage_path = AsyncPath("/".join(_storage_path))
        cache_key = Templates.get_cache_key((storage_path))
        debug(cache_key)
        await self.cache.set(cache_key, source)
        return source.decode(), path.name, uptodate

    async def list_templates(self) -> list[str]:
        paths = self._template_root.rglob("*.html")
        found = [str(p) async for p in paths]
        found.sort()
        return found


class ChoiceLoader(AsyncBaseLoader):
    def __init__(
        self,
        loaders: list[AsyncBaseLoader],
        searchpath: AsyncPath | t.Sequence[AsyncPath],
    ) -> None:
        super().__init__(searchpath)
        self.loaders = loaders

    async def get_source(
        self, template: AsyncPath
    ) -> tuple[t.Any, t.Any, t.Callable[[], t.Coroutine[t.Any, t.Any, bool]]]:
        for loader in self.loaders:
            with suppress(TemplateNotFound):
                return await loader.get_source(template)
        raise TemplateNotFound(str(template))

    async def list_templates(self) -> list[str]:
        found = set()
        for loader in self.loaders:
            templates = await loader.list_templates()
            for template in templates:
                debug(template, loader.__class__.__name__)
            found.update(templates)
        return sorted(found)


class TemplatesSettings(TemplatesBaseSettings):
    loader: t.Optional[str] = None
    extensions: list[str] = []
    delimiters: t.Optional[dict[str, str]] = dict(
        block_start_string="[%",
        block_end_string="%]",
        variable_start_string="[[",
        variable_end_string="]]",
        comment_start_string="[#",
        comment_end_string="#]",
    )
    globals: dict[str, t.Any] = {}

    @depends.inject
    def __init__(
        self,
        models: Models = depends(),  # type: ignore
        **data: t.Any,  # type: ignore
    ) -> None:
        super().__init__(**data)
        self.globals["models"] = models


class Templates(TemplatesBase):
    app: t.Optional[AsyncJinja2Templates] = None
    admin: t.Optional[AsyncJinja2Templates] = None
    enabled_admin: t.Any = get_adapter("admin")
    enabled_app: t.Any = get_adapter("app")

    def get_loader(self, template_paths: list[AsyncPath]) -> ChoiceLoader:
        searchpaths = []
        for path in template_paths:
            searchpaths.extend([path, path / "blocks"])  # type: ignore
        loaders: list[AsyncBaseLoader] = [
            RedisLoader(searchpaths),
            CloudLoader(searchpaths),
        ]
        debug(searchpaths)
        file_loaders: list[AsyncBaseLoader] = [FileSystemLoader(searchpaths)]
        jinja_loaders = loaders + file_loaders  # type: ignore
        if not self.config.deployed and not self.config.debug.production:
            jinja_loaders = file_loaders + loaders  # type: ignore
        if self.enabled_admin and template_paths == self.admin_searchpaths:
            jinja_loaders.append(PackageLoader(self.enabled_admin.name, "templates"))
        debug(jinja_loaders)
        return ChoiceLoader(jinja_loaders, "templates")  # type: ignore

    @depends.inject
    async def init_envs(
        self,
        template_paths: list[AsyncPath],
        cache: Cache = depends(),  # type: ignore
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
        env_configs = dict(extensions=_extensions, bytecode_cache=bytecode_cache)
        templates = AsyncJinja2Templates(AsyncPath("templates"), **env_configs)
        templates.env.loader = self.get_loader(template_paths) or literal_eval(
            self.config.templates.loader
        )
        for delimiter, value in self.config.templates.delimiters.items():
            setattr(templates.env, delimiter, value)
        templates.env.globals["config"] = self.config  # type: ignore
        for k, v in self.config.templates.globals.items():
            templates.env.globals[k] = v
        return templates

    @depends.inject
    async def init(self, cache: Cache = depends()) -> None:  # type: ignore
        self.app_searchpaths = await self.get_searchpaths(self.enabled_app)
        self.app = await self.init_envs(self.app_searchpaths)
        for loader in self.app.env.loader.loaders:
            self.logger.debug(f"{loader.__class__.__name__} initialized")
        for ext in self.app.env.extensions:
            self.logger.debug(f"{ext.split('.')[-1]} loaded")
        if self.config.debug.templates and self.config.debug.cache:
            for namespace in ("templates", "_templates", "bccache"):
                await cache.clear(namespace)
            self.logger.debug("Templates cache cleared")

    @staticmethod
    def get_attr(html: str, attr: str) -> str | None:
        parser = HTMLParser()
        parser.feed(html)
        soup = parser.get_starttag_text()
        _attr = f"{attr}="
        for s in soup.split():
            if search(_attr, s):
                attr_value = s.replace(_attr, "").strip('"')
                return attr_value

    def filter(self, name: t.Optional[str] = None):
        def decorator(f: t.Callable[..., t.Any]):
            self.app.env.filters[name or f.__name__] = f
            self.admin.env.filters[name or f.__name__] = f
            return f

        return decorator


depends.set(Templates)
