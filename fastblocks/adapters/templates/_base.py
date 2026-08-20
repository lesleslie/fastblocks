from __future__ import annotations

import typing as t
from abc import ABC

from anyio import Path as AsyncPath
from oneiric.core.config import OneiricSettings
from oneiric.core.logging import get_logger
from oneiric.core.resolution import Resolver
from starlette.requests import Request
from starlette.responses import Response

# Oneiric resolver for dependency injection
depends = Resolver()

_log = get_logger("fastblocks.adapters.templates._base")


class SafeAwaitError:
    """Sentinel returned by ``safe_await`` when the callable raised.

    Distinct from ``True`` (the historical accidental-success value) and
    from any genuine result. Callers that need to treat validator
    implementation failures differently from validator ``False`` answers
    should compare against ``SafeAwaitError``.
    """

    __slots__ = ("exception",)

    def __init__(self, exception: BaseException) -> None:
        self.exception = exception

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"SafeAwaitError({type(self.exception).__name__}: {self.exception!r})"


async def safe_await(func_or_value: t.Any) -> t.Any:
    """Resolve ``func_or_value`` to a concrete (possibly awaited) result.

    Three branches:

    1. ``func_or_value`` is not callable -- return it verbatim.
    2. ``func_or_value`` is callable and the result is awaitable -- await it.
    3. ``func_or_value`` is callable and returns a plain value -- return it.

    When the callable raises ``Exception`` we return
    :class:`SafeAwaitError` instead of ``True``. The previous behavior
    silently treated "the validator implementation crashed" as "the
    validator said yes", which made every downstream caller (templates
    that check ``if safe_await(... )``) silently render whatever the
    validator would have rendered had it succeeded.
    """
    if not callable(func_or_value):
        return func_or_value

    try:
        result = func_or_value()
    except Exception as exc:  # noqa: BLE001
        _log.warning(
            "safe_await: callable raised %s: %s",
            type(exc).__name__,
            exc,
        )
        return SafeAwaitError(exc)

    if hasattr(result, "__await__") and callable(result.__await__):
        return await t.cast("t.Awaitable[t.Any]", result)
    return result


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


class TemplatesBaseSettings(OneiricSettings, ABC):  # type: ignore[misc]
    cache_timeout: int = 300

    def __init__(self, **values: t.Any) -> None:
        # Extract cache_timeout from values before passing to parent
        cache_timeout = values.pop("cache_timeout", 300)
        super().__init__(**values)
        self.cache_timeout = cache_timeout


class TemplatesProtocol(t.Protocol):
    def get_searchpath(self, adapter: t.Any, path: AsyncPath) -> None: ...

    async def get_searchpaths(self, adapter: t.Any) -> list[AsyncPath]: ...

    @staticmethod
    def get_storage_path(path: AsyncPath) -> AsyncPath: ...

    @staticmethod
    def get_cache_key(path: AsyncPath) -> str: ...


class TemplatesBase:
    app: t.Any | None = None
    admin: t.Any | None = None
    app_searchpaths: list[AsyncPath] | None = None
    admin_searchpaths: list[AsyncPath] | None = None

    # Injected by the Oneiric adapter framework at registration time.
    # Declared (without a value) so type checkers can resolve `self.config` /
    # `self.logger` in subclasses; a bare annotation creates no runtime class
    # attribute, so dependency injection behaviour is unchanged.
    config: t.Any
    logger: t.Any

    def __init__(self, **kwargs: t.Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get_searchpath(self, adapter: t.Any, path: AsyncPath) -> list[AsyncPath]:
        style = getattr(self.config.app, "style", "vanilla")  # type: ignore[attr-defined]
        base_path = path / "base"
        style_path = path / style
        style_adapter_path = path / style / adapter.name
        theme_adapter_path = style_adapter_path / "theme"
        return [theme_adapter_path, style_adapter_path, style_path, base_path]

    async def get_searchpaths(self, adapter: t.Any) -> list[AsyncPath]:
        searchpaths: list[AsyncPath] = []
        base_root = (
            AsyncPath(str(depends.root_path))
            if hasattr(depends, "root_path")
            else AsyncPath("/")
        )

        if adapter and hasattr(adapter, "category"):
            searchpaths.extend(
                self.get_searchpath(
                    adapter, base_root / "templates" / adapter.category
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
