import typing as t
from ast import literal_eval
from contextlib import suppress
from html.parser import HTMLParser
from importlib import import_module
from importlib.util import find_spec
from inspect import isclass
from pathlib import Path
from re import search

from acb import base_path
from acb.adapters import get_adapter
from acb.adapters import import_adapter
from acb.config import Config
from acb.debug import debug
from acb.depends import depends
from aiopath import AsyncPath
from jinja2 import TemplateNotFound
from jinja2.ext import debug as jinja_debug
from jinja2.ext import Extension
from jinja2.ext import i18n
from jinja2.ext import loopcontrols
from jinja2_async_environment.loaders import AsyncBaseLoader
from jinja2_async_environment.bccache import AsyncRedisBytecodeCache
from pydantic import BaseModel
from starlette_async_jinja import AsyncJinja2Templates
from ._base import TemplatesBase
from ._base import TemplatesBaseSettings

Logger = import_adapter()
Cache = import_adapter()
Storage = import_adapter()
Models = import_adapter()


def get_storage_path(path: AsyncPath) -> AsyncPath:
    depth = path.parts.index("templates") + 1
    return AsyncPath("/".join(path.parts[depth:]))


def get_cache_key(path: AsyncPath) -> str:
    return "-".join(path.parts)


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
            if await path.is_file():
                debug(path)
                break
        storage_path = get_storage_path(path)  # type: ignore
        fs_exists = await path.exists()
        storage_exists = await self.storage.templates.exists(storage_path)
        debug(fs_exists)
        debug(storage_exists)
        local_mtime = 0
        if storage_exists and fs_exists and not self.config.deployed:
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
        await self.cache.set(get_cache_key(storage_path), resp)

        async def uptodate() -> bool:
            return int((await path.stat()).st_mtime) == local_mtime

        return resp.decode(), str(storage_path), uptodate

    async def list_templates(self) -> list[str]:
        found = set()
        for searchpath in self.searchpath:  # type: ignore
            paths = searchpath.rglob("*.html")
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
            storage_path = get_storage_path(path)
            debug(await self.storage.templates.exists(storage_path))
            if await self.storage.templates.exists(storage_path):
                debug(path)
                break
        try:
            resp = await self.storage.templates.open(storage_path)
            await self.cache.set(get_cache_key(storage_path), resp)  # type: ignore
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
                paths = await self.storage.templates.list(get_storage_path(searchpath))
                found.extend([p for p in paths if p.endswith(".html")])
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
            storage_path = get_storage_path(path)
            cache_key = get_cache_key(storage_path)
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
        found.extend([k async for k in self.cache.scan("*.html")])
        found.sort()
        return found


class PackageLoader(AsyncBaseLoader):
    def __init__(self, package_name: str, path: "str" = "templates") -> None:
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

    async def get_source(
        self, template: AsyncPath
    ) -> tuple[t.Any, t.Any, t.Callable[[], t.Coroutine[t.Any, t.Any, bool]]]:
        p = self._template_root / template
        if not await p.is_file():
            raise TemplateNotFound(template.name)
        debug("Package Loader")
        source = await p.read_bytes()
        mtime = (await p.stat()).st_mtime

        async def uptodate() -> bool:
            return await p.is_file() and (await p.stat()).st_mtime == mtime

        replace = (("{{", "[["), ("}}", "]]"), ("{%", "[%"), ("%}", "%]"))
        for r in replace:
            source = source.replace(
                bytes(r[0], encoding="utf8"), bytes(r[1], encoding="utf8")
            )
        return source.decode(), p.name, uptodate

    async def list_templates(self) -> list[str]:
        found = []
        paths = self._template_root.rglob("*.html")
        found.extend([str(p) async for p in paths])
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


class EnvTemplatePaths(BaseModel, arbitrary_types_allowed=True):
    root: AsyncPath
    base: AsyncPath = AsyncPath("templates/base")
    style: AsyncPath = AsyncPath("templates/style")
    theme: AsyncPath = AsyncPath("templates/theme")

    @depends.inject
    def __init__(self, config: Config = depends(), **values: t.Any) -> None:
        super().__init__(**values)
        self.root = base_path / "templates" / self.root
        self.base = self.root / "base"
        self.style = self.root / config.app.style
        self.theme = self.style / config.app.theme


class TemplatesSettings(TemplatesBaseSettings):
    loader: t.Optional[str] = None
    cache_db: t.Optional[int] = 0
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
        self, models: Models = depends(), **data: t.Any  # type: ignore
    ) -> None:
        super().__init__(**data)
        self.globals["models"] = models


class Templates(TemplatesBase):
    app: t.Optional[AsyncJinja2Templates] = None
    admin: t.Optional[AsyncJinja2Templates] = None

    def get_loader(
        self, template_paths: EnvTemplatePaths, admin: bool = False
    ) -> ChoiceLoader:
        searchpaths = []
        for path in (template_paths.theme, template_paths.style, template_paths.base):
            searchpaths.extend([path, path / "blocks"])
        loaders: list[AsyncBaseLoader] = [
            RedisLoader(searchpaths),
            CloudLoader(searchpaths),
        ]
        file_loaders: list[AsyncBaseLoader] = [FileSystemLoader(searchpaths)]
        if admin:
            file_loaders.append(PackageLoader("sqladmin"))
        jinja_loaders = loaders + file_loaders  # type: ignore[override]
        if not self.config.deployed and not self.config.debug.production:
            jinja_loaders = file_loaders + loaders  # type: ignore[override]
        return ChoiceLoader(jinja_loaders, template_paths.style)

    async def init_envs(
        self, template_paths: EnvTemplatePaths, admin: bool = False
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
            prefix=self.config.app.name,
            password=self.config.cache.password.get_secret_value(),
            host=self.config.cache.host.get_secret_value(),
            port=self.config.cache.port,
            db=self.config.templates.cache_db,
        )
        env_configs = dict(extensions=_extensions, bytecode_cache=bytecode_cache)
        templates = AsyncJinja2Templates(template_paths.root, **env_configs)
        templates.env.loader = self.get_loader(
            template_paths, admin=admin
        ) or literal_eval(self.config.templates.loader)
        for ext in templates.env.extensions:
            self.logger.debug(f"{ext.split('.')[-1]} loaded")
        for delimiter, value in self.config.templates.delimiters.items():
            setattr(templates.env, delimiter, value)
        templates.env.globals["config"] = self.config  # type: ignore
        for k, v in self.config.templates.globals.items():
            templates.env.globals[k] = v
        return templates

    @depends.inject
    async def init(self, logger: Logger = depends()) -> None:  # type: ignore
        self.app = await self.init_envs(EnvTemplatePaths(root=AsyncPath("app")))
        if get_adapter("admin").enabled:
            self.admin = await self.init_envs(
                EnvTemplatePaths(root=AsyncPath("admin")), admin=True
            )
        for loader in self.app.env.loader.loaders:
            logger.debug(f"{loader.__class__.__name__} initialized")

    @staticmethod
    def get_attr(html: str, attr: str) -> str | None:
        parser = HTMLParser()
        parser.feed(html)
        soup = parser.get_starttag_text()
        attr = f"{attr}="
        for s in soup.split():
            if search(attr, s):
                attr_value = s.replace(attr, "").strip('"')
                return attr_value

    def filter(self, name: t.Optional[str] = None):
        def decorator(f: t.Callable[..., t.Any]):
            self.app.env.filters[name or f.__name__] = f
            self.admin.env.filters[name or f.__name__] = f
            return f

        return decorator


depends.set(Templates)
