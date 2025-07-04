import typing as t

from starlette.routing import Router

from ...dependencies import get_acb_subset

AdapterBase, AppConfigSettings = get_acb_subset("AdapterBase", "AppSettings")


class AppBaseSettings(AppConfigSettings):
    name: str = "fastblocks"
    style: str = "bulma"
    theme: str = "light"


class AppProtocol(t.Protocol):
    def __init__(self) -> None: ...

    async def lifespan(self) -> t.AsyncIterator[None]: ...


class AppBase(AdapterBase):
    router: Router | None
