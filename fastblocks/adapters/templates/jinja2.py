import typing as t
from ast import literal_eval
from contextlib import suppress
from html.parser import HTMLParser
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path
from re import search

from acb import base_path
from acb.adapters import import_adapter
from acb.config import Config
from acb.debug import debug
from acb.depends import depends
from starlette_async_jinja import AsyncJinja2Templates

from aiopath import AsyncPath
from jinja2 import TemplateNotFound
from jinja2.ext import debug as jinja_debug
from jinja2.ext import Extension
from jinja2.ext import i18n
from jinja2.ext import loopcontrols
from jinja2_async_environment.loaders import AsyncBaseLoader
from pydantic import BaseModel
from ._base import TemplatesBase
from ._base import TemplatesBaseSettings

Logger = import_adapter()
Cache = import_adapter()
Storage = import_adapter()


class FileSystemLoader(AsyncBaseLoader):
    config: Config = depends()
    cache: Cache = depends()  # type: ignore
    storage: Storage = depends()  # type: ignore

    async def get_source(
        self, template: AsyncPath
    ) -> tuple[t.Any, t.Any, t.Callable[[], t.Coroutine[t.Any, t.Any, bool]]]:
        path = None
        for searchpath in self.searchpath:  # type: ignore
            path = searchpath / template
            if await path.is_file():
                debug(path)
                break
        debug("File Loader")
        storage_path = AsyncPath("/".join(path.parts[-3:]))
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
                await storage_path.write_bytes(resp)
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
        await self.cache.set(path.name, resp)

        async def uptodate() -> bool:
            return int((await path.stat()).st_mtime) == local_mtime

        return resp.decode(), path.name, uptodate


class CloudLoader(AsyncBaseLoader):
    cache: Cache = depends()  # type: ignore
    storage: Storage = depends()  # type: ignore

    async def get_source(
        self, template: AsyncPath
    ) -> tuple[t.Any, t.Any, t.Callable[[], t.Coroutine[t.Any, t.Any, bool]]]:
        path = None
        for searchpath in self.searchpath:  # type: ignore
            path = searchpath / template
            debug(path)
            if await path.is_file():
                break
        debug("Cloud Loader")
        storage_path = AsyncPath("/".join(path.parts[-3:]))
        debug(await self.storage.templates.exists(storage_path))
        try:
            resp = await self.storage.templates.open(storage_path)
            await self.cache.set(storage_path, resp)
            local_stat = await self.storage.templates.stat(storage_path)
            local_mtime = int(round(local_stat.get("mtime").timestamp()))

            async def uptodate() -> bool:
                debug("cloud uptodate")
                debug(local_mtime)
                cloud_stat = await self.storage.templates.stat(storage_path)
                return int(round(cloud_stat.get("mtime").timestamp())) == local_mtime

            return resp.decode(), path.name, uptodate
        except (FileNotFoundError, AttributeError):
            raise TemplateNotFound(path.name)

    async def list_templates(self) -> list[str]:
        found = set()
        path = self.storage.templates.list(self.searchpath)
        found.update(
            [p.name async for p in await path.iterdir() if p.suffix == ".html"]
        )
        return sorted(found)


class RedisLoader(AsyncBaseLoader):
    cache: Cache = depends()  # type: ignore

    async def get_source(
        self, template: AsyncPath
    ) -> tuple[t.Any, t.Any, t.Callable[[], t.Coroutine[t.Any, t.Any, bool]]]:
        path = None
        for searchpath in self.searchpath:  # type: ignore
            path = searchpath / template if searchpath else template
            debug(path)
            if await path.is_file():
                break
        debug("Redis Loader")
        resp = await self.cache.get(path.name)
        if not resp:
            raise TemplateNotFound(path.name)

        async def uptodate() -> bool:
            return True

        return resp.decode(), None, uptodate

    async def list_templates(self) -> list[str]:
        found = set()
        found.update([k async for k in await self.cache.all() if k.suffix == ".html"])
        return sorted(found)


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
        self._template_root = template_root

    async def get_source(
        self, template: AsyncPath
    ) -> tuple[t.Any, t.Any, t.Callable[[], t.Coroutine[t.Any, t.Any, bool]]]:
        p = AsyncPath(self._template_root) / template
        if not await p.is_file():
            raise TemplateNotFound(template.name)
        debug("Package Loader")
        debug(template)
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

    async def list_templates(self) -> t.List[str]:
        results: t.List[str] = []
        offset = self._template_root
        for path in [p async for p in AsyncPath(self._template_root).rglob("*.html")]:
            dirpath = Path("/".join(path.parts[offset:]))
            results.append(str(dirpath / path.name))
        results.sort()
        return results


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
    extensions: list[Extension] = []
    delimiters: t.Optional[dict[str, str]] = dict(
        block_start_string="[%",
        block_end_string="%]",
        variable_start_string="[[",
        variable_end_string="]]",
        comment_start_string="[#",
        comment_end_string="#]",
    )
    globals: dict[str, t.Any] = {}


class Templates(TemplatesBase):
    app: t.Optional[AsyncJinja2Templates] = None
    admin: t.Optional[AsyncJinja2Templates] = None

    def get_loader(
        self, template_paths: EnvTemplatePaths, admin: bool = False
    ) -> ChoiceLoader:
        loaders: list[AsyncBaseLoader] = [
            RedisLoader(
                [template_paths.theme, template_paths.style, template_paths.base]
            ),
            CloudLoader(
                [template_paths.theme, template_paths.style, template_paths.base]
            ),
        ]
        file_loaders: list[AsyncBaseLoader] = [
            FileSystemLoader(
                [template_paths.theme, template_paths.style, template_paths.base]
            ),
        ]
        if admin:
            file_loaders.append(PackageLoader("sqladmin"))
        # if debug.toolbar and not deployed:
        #     file_loaders.append(PackageLoader("debug_toolbar"))
        jinja_loaders = loaders + file_loaders  # type: ignore[override]
        if not self.config.deployed and not self.config.debug.production:
            jinja_loaders = file_loaders + loaders  # type: ignore[override]
        return ChoiceLoader(jinja_loaders, base_path)

    def init_envs(
        self, template_paths: EnvTemplatePaths, admin: bool = False
    ) -> AsyncJinja2Templates:
        env_configs = dict(
            extensions=[loopcontrols, i18n, jinja_debug]
            + self.config.templates.extensions,
        )
        templates = AsyncJinja2Templates(template_paths.root, **env_configs)
        templates.env.loader = self.get_loader(template_paths, admin) or literal_eval(
            self.config.templates.loader
        )
        for delimiter, value in self.config.templates.delimiters.items():
            setattr(templates.env, delimiter, value)
        templates.env.globals["config"] = self.config  # type: ignore
        for k, v in self.config.templates.globals.items():
            templates.env.globals[k] = v
        return templates

    @depends.inject
    async def init(self, logger: Logger = depends()) -> None:  # type: ignore
        self.app = self.init_envs(EnvTemplatePaths(root=AsyncPath("app")))
        self.admin = self.init_envs(
            EnvTemplatePaths(root=AsyncPath("admin")), admin=True
        )
        for loader in self.admin.env.loader.loaders + self.app.env.loader.loaders:
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
