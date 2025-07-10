import typing as t

from acb.config import AdapterBase
from acb.depends import depends
from starlette.routing import Router

try:
    AppConfigSettings = depends.get("config").app.__class__
except Exception:
    AppConfigSettings = object


class AppBaseSettings(AppConfigSettings):  # type: ignore[misc]
    name: str = "fastblocks"
    style: str = "bulma"
    theme: str = "light"


class AppProtocol(t.Protocol):
    def __init__(self) -> None: ...

    async def lifespan(self) -> t.AsyncIterator[None]: ...


class AppBase(AdapterBase):
    router: Router | None
