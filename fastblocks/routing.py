import typing as t
from contextvars import ContextVar

# from acb.config import Config
# from acb.depends import depends
#
# from starlette.routing import Route
# from starlette.routing import Router


router_registry: ContextVar[list[t.Any]] = ContextVar("routers", default=[])
