import typing as t

from acb.config import AdapterBase
from acb.config import AppSettings as AppConfigSettings


class AppBaseSettings(AppConfigSettings):
    name: str = "fastblocks"
    style: str = "bulma"
    theme: str = "light"


class AppProtocol(t.Protocol):
    def __init__(self) -> None: ...
    async def lifespan(self) -> t.AsyncIterator[None]: ...


class AppBase(AdapterBase): ...
