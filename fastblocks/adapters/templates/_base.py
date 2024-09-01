import typing as t
from abc import ABC

from acb.adapters import AdapterBase, base_path, import_adapter
from acb.config import Config, Settings
from acb.depends import depends
from aiopath import AsyncPath

Logger = import_adapter()


class TemplatesBaseSettings(Settings):
    cache_timeout: int = 300

    @depends.inject
    def __init__(self, config: Config = depends(), **values: t.Any) -> None:
        super().__init__(**values)
        self.cache_timeout = self.cache_timeout if config.deployed else 1


class TemplatesBase(AdapterBase, ABC):
    app: t.Optional[t.Any] = None
    admin: t.Optional[t.Any] = None
    app_searchpaths: t.Optional[list[AsyncPath]] = None
    admin_searchpaths: t.Optional[list[AsyncPath]] = None

    @staticmethod
    def get_searchpaths(
        root: AsyncPath = base_path,
        name: str = "templates",
        adapter: str = "app",
        style: str = "bulma",
    ) -> list[AsyncPath]:
        adapter_path = root / name / adapter
        base_path = adapter_path / "base"
        style_path = adapter_path / style
        # theme_path = style_path / "css"
        return [style_path, base_path]

    @staticmethod
    def get_storage_path(path: AsyncPath) -> AsyncPath:
        templates_path_name = "templates"
        if templates_path_name not in path.parts:
            templates_path_name = "_templates"
        depth = path.parts.index(templates_path_name) + 1
        return AsyncPath("/".join(path.parts[depth:]))

    @staticmethod
    def get_cache_key(path: AsyncPath) -> str:
        return ":".join(path.parts)
