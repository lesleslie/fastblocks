import typing as t
from abc import ABC

from acb.adapters import AdapterBase, base_path, import_adapter
from acb.config import Config, Settings
from acb.depends import depends
from aiopath import AsyncPath
from pydantic import BaseModel

Logger = import_adapter()


class TemplatePaths(BaseModel, arbitrary_types_allowed=True):
    root: AsyncPath
    base: AsyncPath = AsyncPath("templates/base")
    style: t.Optional[AsyncPath] = AsyncPath("templates/style")
    theme: t.Optional[AsyncPath] = AsyncPath("templates/style/css")

    @depends.inject
    def __init__(
        self,
        config: Config = depends(),  # type: ignore
        **values: t.Any,
    ) -> None:
        super().__init__(**values)
        self.root = base_path / "templates" / self.root
        self.base = self.root / "base"
        self.style = self.root / config.app.style
        self.theme = self.style / "css"  # type: ignore


class TemplatesBaseSettings(Settings): ...


class TemplatesBase(AdapterBase, ABC):
    app: t.Optional[t.Any] = None
    admin: t.Optional[t.Any] = None
    app_paths: t.Optional[TemplatePaths] = TemplatePaths(root=AsyncPath("app"))
    admin_paths: t.Optional[TemplatePaths] = TemplatePaths(root=AsyncPath("admin"))

    def set_path_attrs(self) -> None:
        for attr in ((self.app, self.app_paths), (self.admin, self.admin_paths)):
            if attr[0] is not None:
                for name, path in {
                    n: p for n, p in vars(attr[1]).items() if isinstance(p, AsyncPath)
                }.items():
                    setattr(attr[0], name, path)

    @staticmethod
    def get_storage_path(path: AsyncPath) -> AsyncPath:
        depth = path.parts.index("templates") + 1
        return AsyncPath("/".join(path.parts[depth:]))

    @staticmethod
    def get_cache_key(path: AsyncPath) -> str:
        return "-".join(path.parts)
