import typing as t
from contextvars import ContextVar

route_registry: ContextVar[list[t.Any]] = ContextVar("route_registry", default=[])
