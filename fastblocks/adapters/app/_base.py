import typing as t

from acb.config import AdapterBase
from acb.config import AppSettings as AppConfigSettings
from starlette.routing import Router


class AppBaseSettings(AppConfigSettings):
    name: str = "fastblocks"
    style: str = "bulma"
    theme: str = "light"


class AppProtocol(t.Protocol):
    def __init__(self) -> None: ...

    async def lifespan(self) -> t.AsyncIterator[None]: ...


class AppBase(AdapterBase):
    router: Router | None

    def __init__(self) -> None:
        super().__init__()
        self.router = None
