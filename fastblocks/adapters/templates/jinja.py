import typing as t
from ast import literal_eval
from contextlib import suppress
from html.parser import HTMLParser
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path
from re import search

from jinja_partials import register_starlette_extensions  # type: ignore

# from acb import adapters_path
from acb import base_path
from acb.adapters.cache import Cache
from acb.adapters.logger import Logger
from acb.adapters.storage import Storage
from acb.config import Config
from acb.debug import debug
from acb.depends import depends
from aiopath import AsyncPath
from fastblocks import AsyncJinja2Templates
from jinja2 import TemplateNotFound
from jinja2.ext import debug as jinja_debug
from jinja2.ext import Extension
from jinja2.ext import i18n
from jinja2.ext import loopcontrols
from jinja2_async_environment.loaders import AsyncBaseLoader
from pydantic import BaseModel
from ._base import TemplatesBase
from ._base import TemplatesBaseSettings


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
        fs_exists = await path.exists()
        gc_exists = self.storage.theme.exists(path)
        debug(fs_exists)
        debug(gc_exists)
        local_mtime = 0
        if gc_exists and fs_exists and not self.config.deployed:
            local_stat = await path.stat()
            local_mtime = int(local_stat.st_mtime)
            local_size = local_stat.st_size
            # local_hash = await hash.crc32c(path)
            cloud_stat = self.storage.theme.stat(path)
            cloud_mtime = cloud_stat.last_modified
            cloud_size = cloud_stat.size
            # cloud_hash = await hash.crc32c(resp)
            # debug(type(resp))
            debug(cloud_stat)
            debug(local_mtime, cloud_mtime)
            debug(local_size, cloud_size)
            # debug(local_hash, cloud_hash)
            # if local_hash != cloud_hash:
            # if local_size != cloud_size:
            if local_mtime < cloud_mtime and local_size != cloud_size:
                resp = self.storage.theme.get(path)
                if isinstance(resp, bytes):
                    await path.write_bytes(resp)
                else:
                    await path.write_text(resp)
            else:
                resp = await path.read_text()
                if local_size != cloud_size:
                    self.storage.theme.save(path, resp)
        else:
            try:
                resp = await path.read_text()
                if resp and not gc_exists:
                    self.storage.theme.save(path, resp)
            except FileNotFoundError:
                raise TemplateNotFound(path.name)
        await self.cache.set(path, resp)

        async def uptodate() -> bool:
            return int((await path.stat()).st_mtime) == local_mtime

        return resp, path.name, uptodate


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
        try:
            resp = self.storage.theme.get(path)
            await self.cache.set(path, resp)
            local_stat = self.storage.theme.stat(path)
            local_mtime = local_stat.last_modified

            async def uptodate() -> bool:
                debug("cloud uptodate")
                debug(local_mtime)
                stat = self.storage.theme.stat(path)
                debug(stat.last_modified)
                return stat.last_modified == local_mtime

            return resp, path.name, uptodate
        except (FileNotFoundError, AttributeError):
            raise TemplateNotFound(path.name)

    async def list_templates(self) -> list[str]:
        found = set()
        path = self.storage.theme.list(self.searchpath)
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
        resp = await self.cache.get(path)
        if not resp:
            raise TemplateNotFound(path.name)

        async def uptodate() -> bool:
            return True

        return resp, None, uptodate

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
        # uptodate: t.Optional[t.Callable[[], bool]]
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
        loaders: list[RedisLoader | CloudLoader | AsyncBaseLoader],
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
    base: AsyncPath
    style: AsyncPath
    theme: AsyncPath

    @depends.inject
    def __init__(
        self, root: AsyncPath, config: Config = depends(), **data: t.Any
    ) -> None:
        super().__init__(**data)
        self.root = root / "templates"
        self.base = self.root / "base"
        self.style = self.root / config.app.style
        self.theme = self.style / config.app.theme


class TemplatesSettings(TemplatesBaseSettings):
    requires: t.Optional[list[str]] = ["cache", "storage"]
    app: t.Optional[EnvTemplatePaths] = EnvTemplatePaths(root=base_path)
    admin: t.Optional[EnvTemplatePaths] = EnvTemplatePaths(
        root=base_path.parent / "admin" / "_templates"
    )
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
    config: Config = depends()  # type: ignore

    def get_loader(self, template_paths: EnvTemplatePaths):
        print(template_paths)
        loaders = [
            RedisLoader(template_paths.theme),
            RedisLoader(template_paths.style),
            RedisLoader(template_paths.base),
            CloudLoader(template_paths.theme),
            CloudLoader(template_paths.style),
            CloudLoader(template_paths.base),
        ]
        file_loaders: list[AsyncBaseLoader] = [
            FileSystemLoader(template_paths.theme),
            FileSystemLoader(template_paths.style),
            FileSystemLoader(template_paths.base),
        ]
        if template_paths.__name__ == "admin":
            file_loaders.append(PackageLoader("sqladmin"))
        # if debug.toolbar and not deployed:
        #     file_loaders.append(PackageLoader("debug_toolbar"))
        jinja_loaders = loaders + file_loaders  # type: ignore[override]
        if not self.config.deployed or not self.config.debug.production:
            jinja_loaders = file_loaders + loaders  # type: ignore[override]
        return ChoiceLoader(jinja_loaders, base_path)

    def init_envs(self, template_paths: EnvTemplatePaths):
        env_configs = dict(extensions=[loopcontrols, i18n, jinja_debug])
        templates = AsyncJinja2Templates(template_paths.root, **env_configs)
        templates.env.loader = self.get_loader(template_paths) or literal_eval(
            self.config.templates.loader
        )
        for ext in [literal_eval(ext) for ext in self.config.templates.extensions]:
            templates.env.add_extension(ext)
        templates.env.globals["config"] = self.config  # type: ignore
        for k, v in self.config.templates.globals.items():
            templates.env.globals[k] = v
        register_starlette_extensions(templates)  # type: ignore
        return templates

    @depends.inject
    async def init(self, logger: Logger = depends()) -> None:  # type: ignore
        self.app = self.init_envs(self.config.templates.app)
        self.admin = self.init_envs(self.config.templates.admin)
        for loader in self.admin.env.loader.loaders + self.app.env.loader.loaders:
            name = loader.__class__.__name__
            logger.debug(f"{name} ({loader.path}) initialized")

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
