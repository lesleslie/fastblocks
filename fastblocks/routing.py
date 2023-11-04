import typing as t
from abc import ABC
from contextvars import ContextVar

from acb.config import Config
from acb.depends import depends
from fastblocks.adapters.templates import Templates


class BaseRouter(ABC):
    config: Config = depends()  # type: ignore
    templates: Templates = depends()  # type: ignore


router_registry: ContextVar[list[t.Any]] = ContextVar("routers", default=[])
