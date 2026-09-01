from __future__ import annotations

import typing as t
from contextlib import suppress
from platform import system

from fastblocks.core.resolver import FastblocksRegistry, get_resolver

# Oneiric imports
from .adapters.oneiric_helper import resolve_instance


# Oneiric adapter structure. ``AdapterBase`` is a real class (not
# an ``object`` alias) so that subclasses' ``__bases__`` can be
# introspected for the literal name ``"AdapterBase"`` — the
# production contract documented in the remediation plan.
class AdapterBase:
    """Marker base for FastBlocks adapter settings classes.

    Subclasses of :class:`FastBlocksSettings` gain this base
    automatically via ``__init_subclass__``. Keeping it as a real
    class (rather than an ``object`` alias) lets downstream code
    introspect ``cls.__bases__`` and see the literal name
    ``"AdapterBase"`` instead of ``"object"``.
    """


# Oneiric resolver
depends = FastblocksRegistry(get_resolver())

from starception import add_link_template, set_editor
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.types import ASGIApp, ExceptionHandler, Lifespan

from .initializers import ApplicationInitializer
from .middleware import MiddlewarePosition


class FastBlocksSettings:
    # Phase 1.4: secure-by-default. SECURITY_HEADERS middleware is
    # registered unless a subclass opts out by setting this to False.
    # ``deployed=True`` or ``debug.production=True`` also force it on,
    # matching the old contract.
    security_headers_strict: bool = True

    def __init_subclass__(cls, **kwargs: t.Any) -> None:
        # Skip modifying __bases__ if AdapterBase is already in the MRO
        # or if it's the same as the current class (avoid self-reference)
        if (
            AdapterBase not in cls.__mro__
            and AdapterBase is not cls  # type: ignore[comparison-overlap]
            and AdapterBase not in cls.__bases__
        ):
            # Create new tuple of bases with AdapterBase included
            new_bases = (AdapterBase,) + cls.__bases__
            # Update the __bases__ attribute properly
            with suppress(TypeError):
                # If direct assignment fails, just continue without modification
                cls.__bases__ = new_bases
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


# Phase 6 Δ3/Δ45/Δ48: ExceptionMiddleware is no longer hardcoded into the
# middleware list at construction time. ``register_user_exception_middleware``
# attaches it to the system middleware dict at a boundary position so the
# stack ordering is observable through ``MiddlewareManager.get_middleware_stack()``.
# Default OUTERMOST preserves legacy behavior; INNERMOST is the opt-out for
# OtelMiddleware-true-outermost scenarios (Commit 11).
def register_user_exception_middleware(
    app: FastBlocks,
    *,
    position: t.Literal["outermost", "innermost"] = "outermost",
) -> None:
    """Register ``ExceptionMiddleware`` at a boundary position.

    Calling with the default ``position="outermost"`` preserves the legacy
    outermost-first ordering. Calling with ``position="innermost"`` registers
    it after every named system position so OtelMiddleware can be outermost.
    """
    enum_position = (
        MiddlewarePosition.OUTERMOST
        if position == "outermost"
        else MiddlewarePosition.INNERMOST
    )
    # Dedupe: remove any prior ``ExceptionMiddleware`` registration at
    # either boundary position before inserting at the new one. Without
    # this loop, a user calling with ``position="innermost"`` after the
    # default OUTERMOST registration would leave BOTH copies in the dict
    # (``add_system_middleware`` is an assign, not a dedupe), and the
    # resolved system_middleware list would contain ``ExceptionMiddleware``
    # twice — duplicating it in the Starlette wrapper chain.
    system = app.middleware_manager._system_middleware
    for k in (MiddlewarePosition.OUTERMOST, MiddlewarePosition.INNERMOST):
        entry = system.get(k)
        if entry is not None and entry[0] is ExceptionMiddleware:
            del system[k]
    app.add_system_middleware(ExceptionMiddleware, position=enum_position)


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
        lifespan: Lifespan[t.Self] | None = None,
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

        # Phase 6 Δ45: register ExceptionMiddleware at OUTERMOST by default.
        # This replaces the legacy hardcoded prepend in
        # ``FastBlocks.get_middleware_stack`` and the legacy hardcoded
        # append at the end of ``build_middleware_stack``. The position
        # is now part of the system_middleware dict and is observable via
        # ``MiddlewareManager.get_middleware_stack()``.
        register_user_exception_middleware(self, position="outermost")

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
        # Phase 6 Δ45: ExceptionMiddleware is no longer hardcoded at the
        # front. It is registered via ``register_user_exception_middleware``
        # at a boundary position (default OUTERMOST) and surfaces in the
        # system_middleware dict. The legacy list-of-tuples shape is
        # retained for backwards compatibility but will be normalized to
        # ``MiddlewareManager.get_middleware_stack()`` in a follow-up.
        middleware_list: list[tuple[str, type]] = []
        system_middleware = self._get_system_middleware_with_overrides()
        for middleware in system_middleware:
            info = self._extract_middleware_info(middleware)
            if info:
                middleware_list.append(info)
        for middleware in self.user_middleware:
            info = self._extract_middleware_info(middleware)
            if info:
                middleware_list.extend(
                    (
                        info,
                        (
                            "ServerErrorMiddleware",
                            t.cast("type", ServerErrorMiddleware),
                        ),
                    ),
                )
        return middleware_list

    def _get_dependencies(self, config: t.Any, logger: t.Any) -> tuple[t.Any, t.Any]:
        if config is None:
            try:
                config = resolve_instance(depends, "fastblocks", "config")
            except (ImportError, AttributeError, ValueError):
                config = None
        if logger is None:
            try:
                logger = resolve_instance(depends, "fastblocks", "logger")
            except (ImportError, AttributeError, ValueError):
                logger = None
        if logger is not None and not hasattr(logger, "debug"):
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

            # ``add_system_middleware`` stores ``(cls, kwargs)`` tuples
            # for compactness; the rest of the build path expects each
            # entry to be a ``Middleware`` instance so
            # ``_apply_middleware_to_app`` can unpack three elements
            # (``cls``, ``args``, ``kwargs``) from each entry. Convert
            # here — without this, the override list contains raw
            # 2-tuples and ``build_middleware_stack`` raises
            # ``ValueError: not enough values to unpack (expected 3,
            # got 2)`` when ``reversed(middleware_list)`` reaches the
            # 2-tuple entry (the test surface that exposed this is
            # ``tests/integration/test_csrf_htmx.py``).
            if isinstance(middleware, tuple) and not isinstance(middleware, Middleware):
                cls, kwargs = middleware
                middleware = Middleware(cls, **kwargs)

            # Phase 6 Δ45: boundary positions are handled before the
            # standard index-replace-or-append fallback. OUTERMOST
            # inserts at the front of the list; INNERMOST appends at
            # the end. Starlette's ``build_middleware_stack`` iterates
            # ``reversed(middleware_list)`` when wrapping, so the front
            # of the list wraps LAST and is the OUTERMOST in the runtime
            # ASGI chain — that is why the dict-key name ``OUTERMOST``
            # matches inserting at index 0 (and ``INNERMOST`` matches
            # appending at the end). This preserves the legacy outermost
            # behavior for ExceptionMiddleware and lets OtelMiddleware
            # (Commit 11) register later to land at the true outermost.
            if position_index == MiddlewarePosition.OUTERMOST.value:
                if logger:
                    logger.debug(
                        f"Inserting middleware at OUTERMOST position (index 0): {position.name}"
                    )
                modified_system_middleware.insert(0, middleware)
            elif position_index == MiddlewarePosition.INNERMOST.value:
                if logger:
                    logger.debug(
                        f"Appending middleware at INNERMOST position (end): {position.name}"
                    )
                modified_system_middleware.append(middleware)
            elif 0 <= position_index < len(modified_system_middleware):
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
            return self._middleware_stack_cache  # type: ignore[return-value]  # ty: ignore[invalid-return-type]  # Cached middleware stack

        config, logger = self._get_dependencies(config, logger)
        error_handler, _exception_handlers = self._separate_exception_handlers()

        from .middleware import middlewares

        middleware_list = self._build_base_middleware_list(error_handler)
        # Pass the config resolved just above: without it
        # MiddlewareStackManager cannot register the conditional security
        # stack (CSRF, session, security headers) and silently skips it.
        system_middleware = middlewares(config=config, logger=logger)
        system_middleware = self._apply_system_middleware_overrides(
            system_middleware,
            logger,
        )

        middleware_list.extend(system_middleware)
        # Phase 6 Δ45: ExceptionMiddleware is no longer appended at the
        # end here. It is registered via ``register_user_exception_middleware``
        # (called from ``__init__``) which adds it to ``_system_middleware``
        # at the OUTERMOST position by default. The override handler in
        # ``_apply_system_middleware_overrides`` then inserts it at the
        # front of the resolved system_middleware list, preserving the
        # legacy behavior. Opt-out via
        # ``register_user_exception_middleware(self, position="innermost")``.

        app = self._apply_middleware_to_app(middleware_list, logger)

        if logger:
            logger.info("Middleware stack built")

        object.__setattr__(self, "_middleware_stack_cache", app)
        return app
