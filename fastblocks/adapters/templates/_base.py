import typing as t
from abc import ABC

from acb.adapters import get_adapters, root_path
from acb.config import AdapterBase, Config
from acb.depends import Inject, depends
from anyio import Path as AsyncPath
from starlette.requests import Request
from starlette.responses import Response

try:
    # For newer versions of ACB where pkg_registry is in context
    from acb import get_context

    context = get_context()
    pkg_registry = context.pkg_registry
except (ImportError, AttributeError):
    # Fallback for older versions or if context is not available
    pkg_registry = None


async def safe_await(func_or_value: t.Any) -> t.Any:
    if callable(func_or_value):
        try:
            result = func_or_value()
            if hasattr(result, "__await__") and callable(result.__await__):
                return await t.cast("t.Awaitable[t.Any]", result)
            return result
        except Exception:
            return True
    return func_or_value


TemplateContext: t.TypeAlias = dict[str, t.Any]
TemplateResponse: t.TypeAlias = Response
TemplateStr: t.TypeAlias = str
TemplatePath: t.TypeAlias = str
T = t.TypeVar("T")


class TemplateRenderer(t.Protocol):
    async def render_template(
        self,
        request: Request,
        template: TemplatePath,
        _: TemplateContext | None = None,
    ) -> TemplateResponse: ...


class TemplateLoader(t.Protocol):
    async def get_template(self, name: TemplatePath) -> t.Any: ...

    async def list_templates(self) -> list[TemplatePath]: ...


class TemplatesBaseSettings(Config, ABC):
    cache_timeout: int = 300

    @depends.inject
    def __init__(self, config: Inject[Config], **values: t.Any) -> None:
        # Extract cache_timeout from values before passing to parent
        cache_timeout = values.pop("cache_timeout", 300)
        super().__init__(**values)
        self.cache_timeout = cache_timeout if config.deployed else 1


class TemplatesProtocol(t.Protocol):
    def get_searchpath(self, adapter: t.Any, path: AsyncPath) -> None: ...

    async def get_searchpaths(self, adapter: t.Any) -> list[AsyncPath]: ...

    @staticmethod
    def get_storage_path(path: AsyncPath) -> AsyncPath: ...

    @staticmethod
    def get_cache_key(path: AsyncPath) -> str: ...


class TemplatesBase(AdapterBase):
    app: t.Any | None = None
    admin: t.Any | None = None
    app_searchpaths: list[AsyncPath] | None = None
    admin_searchpaths: list[AsyncPath] | None = None

    def get_searchpath(self, adapter: t.Any, path: AsyncPath) -> list[AsyncPath]:
        style = getattr(self.config.app, "style", "bulma")
        base_path = path / "base"
        style_path = path / style
        style_adapter_path = path / style / adapter.name
        theme_adapter_path = style_adapter_path / "theme"
        return [theme_adapter_path, style_adapter_path, style_path, base_path]

    async def get_searchpaths(self, adapter: t.Any) -> list[AsyncPath]:
        searchpaths = []
        base_root = self._get_base_root()

        if adapter and hasattr(adapter, "category"):
            searchpaths.extend(
                self.get_searchpath(
                    adapter, base_root / "templates" / adapter.category
                ),
            )

        if adapter and hasattr(adapter, "category") and adapter.category == "app":
            searchpaths.extend(await self._get_app_searchpaths(adapter))

        # Only use pkg_registry if it's available
        if pkg_registry:
            searchpaths.extend(await self._get_pkg_registry_searchpaths(adapter))

        return searchpaths

    def _get_base_root(self) -> AsyncPath:
        if callable(root_path):
            return AsyncPath(root_path())
        return AsyncPath(root_path)

    async def _get_app_searchpaths(self, adapter: t.Any) -> list[AsyncPath]:
        searchpaths = []
        for a in (
            a
            for a in get_adapters()
            if a
            and hasattr(a, "category")
            and a.category not in ("app", "admin", "secret")
        ):
            exists_result = await safe_await((a.path / "_templates").exists)
            if exists_result:
                searchpaths.append(a.path / "_templates")
        return searchpaths

    async def _get_pkg_registry_searchpaths(self, adapter: t.Any) -> list[AsyncPath]:
        searchpaths = []
        for pkg in pkg_registry.get():
            if (
                pkg
                and hasattr(pkg, "path")
                and adapter
                and hasattr(adapter, "category")
            ):
                searchpaths.extend(
                    self.get_searchpath(
                        adapter,
                        pkg.path / "adapters" / adapter.category / "_templates",
                    ),
                )
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
