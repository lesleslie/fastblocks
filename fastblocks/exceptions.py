import typing as t
from abc import ABC, abstractmethod
from contextlib import suppress
from dataclasses import dataclass
from enum import Enum
from operator import itemgetter

from acb.depends import depends
from asgi_htmx import HtmxRequest
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

_templates_cache = None


class ErrorSeverity(Enum):
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ErrorCategory(Enum):
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    CACHING = "caching"
    TEMPLATE = "template"
    MIDDLEWARE = "middleware"
    APPLICATION = "application"


@dataclass
class ErrorContext:
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: dict[str, t.Any] | None = None
    request_id: str | None = None
    user_id: str | None = None


class ErrorHandler(ABC):
    @abstractmethod
    async def can_handle(self, exception: Exception, context: ErrorContext) -> bool:
        pass

    @abstractmethod
    async def handle(
        self,
        exception: Exception,
        context: ErrorContext,
        request: Request,
    ) -> Response:
        pass


class ErrorHandlerRegistry:
    def __init__(self) -> None:
        self._handlers: list[tuple[int, ErrorHandler]] = []
        self._fallback_handler: ErrorHandler | None = None

    def register(self, handler: ErrorHandler, priority: int = 0) -> None:
        self._handlers.append((priority, handler))
        self._handlers.sort(key=itemgetter(0), reverse=True)

    def set_fallback(self, handler: ErrorHandler) -> None:
        self._fallback_handler = handler

    async def handle_error(
        self,
        exception: Exception,
        context: ErrorContext,
        request: Request,
    ) -> Response:
        for _, handler in self._handlers:
            if await handler.can_handle(exception, context):
                return await handler.handle(exception, context, request)

        if self._fallback_handler:
            return await self._fallback_handler.handle(exception, context, request)

        return PlainTextResponse("Internal Server Error", status_code=500)


class DefaultErrorHandler(ErrorHandler):
    async def can_handle(self, exception: Exception, context: ErrorContext) -> bool:
        return True

    async def handle(
        self,
        exception: Exception,
        context: ErrorContext,
        request: Request,
    ) -> Response:
        status_code = getattr(exception, "status_code", 500)
        message = {404: "Content not found", 500: "Server error"}.get(
            status_code,
            "An error occurred",
        )

        if hasattr(request, "scope") and request.scope.get("htmx"):
            return PlainTextResponse(content=message, status_code=status_code)

        templates = safe_depends_get("templates", _exception_cache)
        if templates:
            with suppress(Exception):
                return await templates.app.render_template(
                    request,
                    "index.html",
                    status_code=status_code,
                    context={"page": str(status_code)},
                )

        return PlainTextResponse(content=message, status_code=status_code)


_error_registry = ErrorHandlerRegistry()
_error_registry.set_fallback(DefaultErrorHandler())


def register_error_handler(handler: ErrorHandler, priority: int = 0) -> None:
    _error_registry.register(handler, priority)


def safe_depends_get(
    key: str,
    cache_dict: dict[str, t.Any],
    default: t.Any = None,
) -> t.Any:
    if key not in cache_dict:
        try:
            cache_dict[key] = depends.get(key)
        except Exception:
            cache_dict[key] = default
    return cache_dict[key]


_exception_cache = {}


async def handle_exception(request: HtmxRequest, exc: HTTPException) -> Response:
    status_code = getattr(exc, "status_code", 500)
    error_context = ErrorContext(
        error_id=f"http_{status_code}",
        category=ErrorCategory.APPLICATION,
        severity=ErrorSeverity.ERROR if status_code >= 500 else ErrorSeverity.WARNING,
        message=str(exc.detail) if hasattr(exc, "detail") else f"HTTP {status_code}",
        details={"status_code": status_code, "request_path": str(request.url.path)},
    )

    return await _error_registry.handle_error(exc, error_context, request)


class FastBlocksException(Exception):
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.APPLICATION,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: dict[str, t.Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.details = details if details is not None else {}

    def to_error_context(self, error_id: str | None = None) -> ErrorContext:
        return ErrorContext(
            error_id=error_id or str(self.__class__.__name__.lower()),
            category=self.category,
            severity=self.severity,
            message=self.message,
            details=self.details,
        )


class ConfigurationError(FastBlocksException):
    def __init__(self, message: str, config_key: str | None = None) -> None:
        details = {"config_key": config_key} if config_key else {}
        super().__init__(
            message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.CRITICAL,
            details=details,
        )


class DependencyError(FastBlocksException):
    def __init__(self, message: str, dependency_key: str | None = None) -> None:
        details = {"dependency_key": dependency_key} if dependency_key else {}
        super().__init__(
            message,
            category=ErrorCategory.DEPENDENCY,
            severity=ErrorSeverity.ERROR,
            details=details,
        )


class StarletteCachesException(FastBlocksException):
    def __init__(self, message: str = "Cache operation failed") -> None:
        super().__init__(message, category=ErrorCategory.CACHING)


class DuplicateCaching(StarletteCachesException):
    def __init__(self, message: str = "Duplicate cache middleware detected") -> None:
        super().__init__(message)


class MissingCaching(StarletteCachesException):
    def __init__(self, message: str = "Cache middleware not found") -> None:
        super().__init__(message)


class RequestNotCachable(StarletteCachesException):
    def __init__(self, request: Request) -> None:
        self.request = request
        super().__init__(
            f"Request {request.method} {request.url.path} is not cacheable",
        )


class ResponseNotCachable(StarletteCachesException):
    def __init__(self, response: Response) -> None:
        self.response = response
        super().__init__(
            f"Response with status {response.status_code} is not cacheable",
        )
