"""Middleware gathering and stack building functionality."""

import typing as t
from contextlib import suppress
from enum import Enum

from acb.debug import debug
from starlette.middleware import Middleware
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.middleware.exceptions import ExceptionMiddleware

from .strategies import GatherStrategy, gather_with_strategy


class MiddlewarePosition(Enum):
    SECURITY = 0
    CORS = 1
    COMPRESSION = 2
    SESSIONS = 3
    AUTHENTICATION = 4
    CACHING = 5
    CUSTOM = 6


class MiddlewareGatherResult:
    def __init__(
        self,
        *,
        user_middleware: list[Middleware] | None = None,
        system_middleware: dict[MiddlewarePosition, t.Any] | None = None,
        middleware_stack: list[Middleware] | None = None,
        errors: list[Exception] | None = None,
    ) -> None:
        self.user_middleware = user_middleware if user_middleware is not None else []
        self.system_middleware = (
            system_middleware if system_middleware is not None else {}
        )
        self.middleware_stack = middleware_stack if middleware_stack is not None else []
        self.errors = errors if errors is not None else []

    @property
    def total_middleware(self) -> int:
        return len(self.user_middleware) + len(self.system_middleware)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


async def gather_middleware(
    *,
    user_middleware: list[Middleware] | None = None,
    system_overrides: dict[MiddlewarePosition, t.Any] | None = None,
    include_defaults: bool = True,
    debug_mode: bool = False,
    error_handler: t.Any | None = None,
    strategy: GatherStrategy | None = None,
) -> MiddlewareGatherResult:
    if strategy is None:
        strategy = GatherStrategy()

    if user_middleware is None:
        user_middleware = []

    if system_overrides is None:
        system_overrides = {}

    result = MiddlewareGatherResult(
        user_middleware=user_middleware,
        system_middleware=system_overrides,
    )

    tasks = []

    if include_defaults:
        tasks.append(_gather_default_middleware())

    tasks.extend(
        (
            _gather_custom_middleware(),
            _build_middleware_stack(
                user_middleware,
                system_overrides,
                include_defaults,
                debug_mode,
                error_handler,
            ),
        ),
    )

    gather_result = await gather_with_strategy(
        tasks,
        strategy,
        cache_key=f"middleware:{include_defaults}:{debug_mode}",
    )

    for i, success in enumerate(gather_result.success):
        if i == 0 and include_defaults:
            result.system_middleware.update(success)
        elif i == 1:
            result.user_middleware.extend(success)
        elif i == 2:
            result.middleware_stack = success

    result.errors.extend(gather_result.errors)

    debug(f"Gathered {result.total_middleware} middleware components")

    return result


async def _gather_default_middleware() -> dict[MiddlewarePosition, t.Any]:
    try:
        from fastblocks.middleware import middlewares

        default_middleware_list = middlewares()
        middleware_map = {}
        for i, middleware in enumerate(default_middleware_list):
            if i < len(MiddlewarePosition):
                position = list(MiddlewarePosition)[i]
                middleware_map[position] = middleware
        debug(f"Gathered {len(middleware_map)} default middleware components")
        return middleware_map
    except Exception as e:
        debug(f"Error gathering default middleware: {e}")
        return {}


async def _gather_custom_middleware() -> list[Middleware]:
    custom_middleware = []
    with suppress(Exception):
        from acb.depends import depends

        config = depends.get("config")
        if hasattr(config, "middleware") and hasattr(config.middleware, "custom"):
            for middleware_path in config.middleware.custom:
                try:
                    module_path, class_name = middleware_path.rsplit(".", 1)
                    module = __import__(module_path, fromlist=[class_name])
                    middleware_class = getattr(module, class_name)
                    middleware = Middleware(middleware_class)
                    custom_middleware.append(middleware)
                    debug(f"Added custom middleware: {class_name}")
                except Exception as e:
                    debug(f"Error loading custom middleware {middleware_path}: {e}")

    return custom_middleware


async def _build_middleware_stack(
    user_middleware: list[Middleware],
    system_overrides: dict[MiddlewarePosition, t.Any],
    include_defaults: bool,
    debug_mode: bool,
    error_handler: t.Any,
) -> list[Middleware]:
    stack = []

    stack.append(Middleware(ExceptionMiddleware, debug=debug_mode))

    stack.extend(user_middleware)

    if include_defaults:
        _add_system_middleware(stack, system_overrides)

    _add_error_handler_middleware(stack, error_handler, debug_mode)

    debug(f"Built middleware stack with {len(stack)} components")
    return stack


def _add_system_middleware(
    stack: list[Middleware],
    system_overrides: dict[MiddlewarePosition, t.Any],
) -> None:
    try:
        from fastblocks.middleware import middlewares

        system_middleware = middlewares()

        for position, override in system_overrides.items():
            position_index = position.value
            if 0 <= position_index < len(system_middleware):
                system_middleware[position_index] = override
                debug(f"Override middleware at position {position.name}")

        for middleware_def in system_middleware:
            if isinstance(middleware_def, tuple):
                cls, kwargs = middleware_def
                stack.append(Middleware(cls, **kwargs))
            else:
                stack.append(middleware_def)

    except Exception as e:
        debug(f"Error building system middleware: {e}")


def _add_error_handler_middleware(
    stack: list[Middleware],
    error_handler: t.Any,
    debug_mode: bool,
) -> None:
    if error_handler:
        stack.append(
            Middleware(
                ServerErrorMiddleware,
                handler=error_handler,
                debug=debug_mode,
            ),
        )
    else:
        stack.append(
            Middleware(
                ServerErrorMiddleware,
                debug=debug_mode,
            ),
        )


def extract_middleware_info(middleware: t.Any) -> dict[str, t.Any]:
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


def get_middleware_stack_info(
    middleware_stack: list[Middleware],
) -> dict[str, t.Any]:
    info: dict[str, t.Any] = {
        "total_middleware": len(middleware_stack),
        "middleware_list": [],
        "execution_order": [],
    }

    for i, middleware in enumerate(middleware_stack):
        middleware_info = extract_middleware_info(middleware)
        middleware_info["position"] = i
        info["middleware_list"].append(middleware_info)
        info["execution_order"].append(middleware_info["class"])

    return info


def validate_middleware_stack(
    middleware_stack: list[Middleware],
) -> dict[str, t.Any]:
    validation: dict[str, t.Any] = {
        "valid": True,
        "warnings": [],
        "errors": [],
        "recommendations": [],
    }

    middleware_classes = [extract_middleware_info(m)["class"] for m in middleware_stack]

    if middleware_classes and middleware_classes[0] != "ExceptionMiddleware":
        validation["warnings"].append(
            "ExceptionMiddleware should be first in the stack",
        )

    if middleware_classes and middleware_classes[-1] != "ServerErrorMiddleware":
        validation["warnings"].append(
            "ServerErrorMiddleware should be last in the stack",
        )

    security_middleware = [
        "CORSMiddleware",
        "TrustedHostMiddleware",
        "HTTPSRedirectMiddleware",
    ]

    found_security = any(
        any(sec in cls for sec in security_middleware) for cls in middleware_classes
    )

    if not found_security:
        validation["recommendations"].append(
            "Consider adding security middleware (CORS, TrustedHost, etc.)",
        )

    session_index = -1
    auth_index = -1

    for i, cls in enumerate(middleware_classes):
        if "Session" in cls:
            session_index = i
        if "Auth" in cls or "Login" in cls:
            auth_index = i

    if session_index > -1 and auth_index > -1 and session_index > auth_index:
        validation["warnings"].append(
            "SessionMiddleware should come before authentication middleware",
        )

    validation["valid"] = len(validation["errors"]) == 0

    return validation


async def create_middleware_manager(
    gather_result: MiddlewareGatherResult,
) -> t.Any:
    from fastblocks.applications import MiddlewareManager

    manager = MiddlewareManager()

    manager.user_middleware = gather_result.user_middleware

    manager._system_middleware = gather_result.system_middleware  # type: ignore[misc]

    manager._middleware_stack_cache = gather_result.middleware_stack

    debug(
        f"Created middleware manager with {gather_result.total_middleware} components",
    )

    return manager


def add_middleware_at_position(
    middleware_stack: list[Middleware],
    new_middleware: Middleware,
    position: MiddlewarePosition,
) -> list[Middleware]:
    stack = middleware_stack.copy()

    insert_index = 1

    if position == MiddlewarePosition.SECURITY:
        insert_index = 1
    elif position == MiddlewarePosition.CORS:
        insert_index = 2
    elif position == MiddlewarePosition.COMPRESSION:
        insert_index = 3
    elif position == MiddlewarePosition.SESSIONS:
        insert_index = 4
    elif position == MiddlewarePosition.AUTHENTICATION:
        insert_index = 5
    elif position == MiddlewarePosition.CACHING:
        insert_index = 6
    elif position == MiddlewarePosition.CUSTOM:
        insert_index = len(stack) - 1

    insert_index = min(insert_index, len(stack) - 1)

    stack.insert(insert_index, new_middleware)
    debug(f"Added middleware at position {position.name}")

    return stack
