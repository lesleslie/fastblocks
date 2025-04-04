import typing as t

from acb.config import AdapterBase
from acb.config import AppSettings as AppConfigSettings
from fastblocks.applications import FastBlocks


class AppBaseSettings(AppConfigSettings):
    name: str = "fastblocks"
    style: str = "bulma"
    theme: str = "light"


class AppProtocol(t.Protocol):
    def __init__(self) -> None: ...

    async def lifespan(
        self, app: FastBlocks, auth: t.Any = ..., sql: t.Any = ...
    ) -> t.Any: ...


class AppBase(AdapterBase, AppProtocol): ...
