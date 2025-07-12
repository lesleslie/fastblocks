import typing as t
from platform import system

from acb.config import AdapterBase
from acb.depends import depends
from starception import add_link_template, set_editor
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.types import ASGIApp, ExceptionHandler, Lifespan

from .initializers import ApplicationInitializer
from .middleware import MiddlewarePosition


class FastBlocksSettings:
    def __init_subclass__(cls, **kwargs: t.Any) -> None:
        if AdapterBase not in cls.__bases__:
            cls.__bases__ = (AdapterBase, *cls.__bases__)
        super().__init_subclass__(**kwargs)


AppType = t.TypeVar("AppType", bound="FastBlocks")

match system():
    case "Windows":
        add_link_template("pycharm", "pycharm64.exe --line {lineno} {path}")
    case "Darwin":
        add_link_template("pycharm", "pycharm --line {lineno} {path}")
    case "Linux":
        add_link_template("pycharm", "pycharm.sh --line {lineno} {path}")
    case _:
        ...


class MiddlewareManager:
    def __init__(self) -> None:
        self._system_middleware: dict[MiddlewarePosition, t.Any] = {}
        self._middleware_stack_cache: list[Middleware] | None = None
        self.user_middleware: list[Middleware] = []

    def add_user_middleware(
        self,
        middleware_class: t.Any,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> None:
        position = kwargs.pop("position", None)

        middleware = Middleware(middleware_class, *args, **kwargs)

        if not hasattr(self, "user_middleware"):
            self.user_middleware = []

        if position is not None and isinstance(position, int):
            self.user_middleware.insert(position, middleware)
        else:
            self.user_middleware.append(middleware)

        self._middleware_stack_cache = None

    def add_system_middleware(
        self,
        middleware_class: t.Any,
        position: MiddlewarePosition,
        **kwargs: t.Any,
    ) -> None:
        self._system_middleware[position] = (middleware_class, kwargs)
        self._middleware_stack_cache = None

    def get_middleware_stack(self) -> dict[str, t.Any]:
        return {
            "user_middleware": [
                self._extract_middleware_info(middleware)
                for middleware in self.user_middleware
            ],
            "system_middleware": {
                pos.name: self._extract_middleware_info(middleware)
                for pos, middleware in self._system_middleware.items()
            },
        }

    def _extract_middleware_info(self, middleware: t.Any) -> dict[str, t.Any]:
        if isinstance(middleware, Middleware):
            return {
                "class": getattr(middleware.cls, "__name__", str(middleware.cls)),
                "args": middleware.args,
                "kwargs": middleware.kwargs,
            }
        if isinstance(middleware, tuple) and len(middleware) >= 2:
            cls, kwargs = middleware[0], middleware[1]
            return {
                "class": cls.__name__ if hasattr(cls, "__name__") else str(cls),
                "kwargs": kwargs,
            }
        return {
            "class": middleware.__class__.__name__,
            "raw": str(middleware),
        }


class FastBlocks(Starlette):
    middleware_manager: MiddlewareManager
    templates: t.Any
    models: t.Any
    _middleware_position_map: dict[MiddlewarePosition, int]

    def __init__(
        self,
        middleware: t.Sequence[Middleware] | None = None,
        exception_handlers: t.Mapping[t.Any, ExceptionHandler] | None = None,
        lifespan: Lifespan["t.Self"] | None = None,
        config: t.Any | None = None,
        logger: t.Any | None = None,
    ) -> None:
        initializer = ApplicationInitializer(
            self,
            middleware=middleware,
            exception_handlers=exception_handlers,
            lifespan=lifespan,
            config=config,
            logger=logger,
        )

        object.__setattr__(self, "middleware_manager", MiddlewareManager())

        self._middleware_position_map = {pos: pos.value for pos in MiddlewarePosition}
        self.templates = None
        self.models = None

        initializer.initialize()

        set_editor("pycharm")

    def add_middleware(
        self,
        middleware_class: t.Any,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> None:
        self.middleware_manager.add_user_middleware(middleware_class, *args, **kwargs)

    @property
    def user_middleware(self) -> list[Middleware]:
        return self.middleware_manager.user_middleware

    @user_middleware.setter
    def user_middleware(self, value: list[Middleware]) -> None:
        self.middleware_manager.user_middleware = value

    @property
    def _system_middleware(self) -> dict[MiddlewarePosition, t.Any]:
        return self.middleware_manager._system_middleware

    @_system_middleware.setter
    def _system_middleware(self, value: dict[MiddlewarePosition, t.Any]) -> None:
        self.middleware_manager._system_middleware = value

    @property
    def _middleware_stack_cache(self) -> list[Middleware] | None:
        return self.middleware_manager._middleware_stack_cache

    @_middleware_stack_cache.setter
    def _middleware_stack_cache(self, value: list[Middleware] | None) -> None:
        self.middleware_manager._middleware_stack_cache = value

    def add_system_middleware(
        self,
        middleware_class: type,
        *,
        position: MiddlewarePosition,
        **options: t.Any,
    ) -> None:
        self.middleware_manager.add_system_middleware(
            middleware_class,
            position,
            **options,
        )

    def _extract_middleware_info(self, middleware: t.Any) -> tuple[str, type] | None:
        try:
            if hasattr(middleware, "cls"):
                cls = middleware.cls
            elif isinstance(middleware, tuple) and len(middleware) > 0:
                cls = middleware[0]
            else:
                return None
            cls_name = str(getattr(cls, "__name__", cls))
            return cls_name, cls
        except (AttributeError, IndexError, TypeError):
            return None

    def _get_system_middleware_with_overrides(self) -> list[t.Any]:
        from .middleware import middlewares

        modified_system_middleware = middlewares().copy()
        for position, middleware in self._system_middleware.items():
            position_index = position.value
            if 0 <= position_index < len(modified_system_middleware):
                modified_system_middleware[position_index] = middleware
            else:
                modified_system_middleware.append(middleware)

        return modified_system_middleware

    def get_middleware_stack(self) -> list[tuple[str, type]]:
        middleware_list = [("ExceptionMiddleware", ExceptionMiddleware)]
        system_middleware = self._get_system_middleware_with_overrides()
        for middleware in system_middleware:
            info = self._extract_middleware_info(middleware)
            if info:
                middleware_list.append(info)
        for middleware in self.user_middleware:
            info = self._extract_middleware_info(middleware)
            if info:
                middleware_list.append(info)
        middleware_list.append(
            ("ServerErrorMiddleware", t.cast("type", ServerErrorMiddleware)),
        )
        return middleware_list

    def _get_dependencies(self, config: t.Any, logger: t.Any) -> tuple[t.Any, t.Any]:
        if config is None:
            config = depends.get("config")
        if logger is None:
            try:
                logger = depends.get("logger")
            except Exception:
                logger = None
        return config, logger

    def _separate_exception_handlers(
        self,
    ) -> tuple[t.Any, dict[t.Any, ExceptionHandler]]:
        error_handler = None
        exception_handlers: dict[t.Any, ExceptionHandler] = {}
        for key, value in self.exception_handlers.items():
            if key in (500, Exception):
                error_handler = value
            else:
                exception_handlers[key] = value
        return error_handler, exception_handlers

    def _build_base_middleware_list(self, error_handler: t.Any) -> list[Middleware]:
        middleware_list = [
            Middleware(
                ServerErrorMiddleware,
                handler=error_handler,
                debug=self.debug,
            ),
        ]
        middleware_list.extend(self.user_middleware)
        return middleware_list

    def _apply_system_middleware_overrides(
        self,
        system_middleware: list[t.Any],
        logger: t.Any,
    ) -> list[t.Any]:
        if not (hasattr(self, "_system_middleware") and self._system_middleware):
            return system_middleware

        modified_system_middleware = system_middleware.copy()

        for position, middleware in self._system_middleware.items():
            position_index = self._middleware_position_map[position]

            if 0 <= position_index < len(modified_system_middleware):
                if logger:
                    logger.debug(f"Replacing middleware at position {position.name}")
                modified_system_middleware[position_index] = middleware
            else:
                if logger:
                    logger.debug(f"Adding middleware at position {position.name}")
                modified_system_middleware.append(middleware)

        return modified_system_middleware

    def _apply_middleware_to_app(
        self,
        middleware_list: list[t.Any],
        logger: t.Any,
    ) -> ASGIApp:
        app = self.router
        for cls, args, kwargs in reversed(middleware_list):
            if logger:
                logger.debug(f"Adding middleware: {cls.__name__}")
            app = cls(*args, app=app, **kwargs)
        return app

    def build_middleware_stack(
        self,
        config: t.Any | None = None,
        logger: t.Any | None = None,
    ) -> ASGIApp:
        if self._middleware_stack_cache is not None:
            return t.cast(t.Any, self._middleware_stack_cache)

        config, logger = self._get_dependencies(config, logger)
        error_handler, exception_handlers = self._separate_exception_handlers()

        from .middleware import middlewares

        middleware_list = self._build_base_middleware_list(error_handler)
        system_middleware = middlewares()
        system_middleware = self._apply_system_middleware_overrides(
            system_middleware,
            logger,
        )

        middleware_list.extend(system_middleware)
        middleware_list.append(
            Middleware(
                ExceptionMiddleware,
                handlers=exception_handlers,
                debug=self.debug,
            ),
        )

        app = self._apply_middleware_to_app(middleware_list, logger)

        if logger:
            logger.info("Middleware stack built")

        object.__setattr__(self, "_middleware_stack_cache", app)
        return app
