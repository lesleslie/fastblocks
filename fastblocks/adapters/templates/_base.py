import typing as t
from abc import ABC

from acb import Adapter
from acb.adapters import get_enabled_adapters, root_path
from acb.config import AdapterBase, Config, Settings
from acb.depends import depends
from aiopath import AsyncPath


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

    @depends.inject
    def get_searchpath(self, adapter: Adapter, path: AsyncPath) -> list[AsyncPath]:
        style = getattr(self.config, adapter.category).style
        base_path = path / "base"
        base_adapter_path = base_path / adapter.name
        style_path = path / style
        style_adapter_path = path / style / adapter.name
        theme_path = style_path / "theme"
        theme_adapter_path = style_adapter_path / "theme"
        return [
            theme_adapter_path,
            theme_path,
            style_adapter_path,
            style_path,
            base_adapter_path,
            base_path,
        ]

    async def get_searchpaths(self, adapter: Adapter) -> list[AsyncPath]:
        searchpaths = []
        for path in (
            root_path / "templates" / adapter.category,
            adapter.path.parent / "_templates",
        ):
            searchpaths.extend(self.get_searchpath(adapter, path))
            for a in [
                a
                for a in get_enabled_adapters()
                if a.category not in ("app", "admin")
                and await (a.path.parent / "_templates").exists()
            ]:
                searchpaths.extend(self.get_searchpath(a, path))
        return searchpaths

    @staticmethod
    def get_storage_path(path: AsyncPath) -> AsyncPath:
        templates_path_name = "templates"
        if templates_path_name not in path.parts:
            templates_path_name = "_templates"
            depth = path.parts.index(templates_path_name) - 1
            _path = list(path.parts[depth:])
            _path.insert(1, _path.pop(0))
            return AsyncPath("/".join(_path))
        depth = path.parts.index(templates_path_name)
        return AsyncPath("/".join(path.parts[depth:]))

    @staticmethod
    def get_cache_key(path: AsyncPath) -> str:
        return ":".join(path.parts)
